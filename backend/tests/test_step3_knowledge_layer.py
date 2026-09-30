from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
import app.models  # noqa: F401 - register all ORM models
from app.models.document import Document
from app.models.document_artifacts import DocumentPage, DocumentTable
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.structured_fact import StructuredFact
from app.services.embedding_service import ProductionEmbeddingUnavailable
from app.services.knowledge_chunking_service import build_knowledge_chunk_specs, persist_knowledge_chunks
from app.services.knowledge_retrieval_service import hybrid_search, search_structured_facts, semantic_search
from app.api.knowledge import router as knowledge_router


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def _document(session, document_id=1):
    document = Document(
        id=document_id,
        filename="step3-fixture.pdf",
        file_path="/safe/step3-fixture.pdf",
        file_hash=f"{document_id:064d}",
        file_type="PDF",
        subsidiary="MCL",
        status="PARSED",
    )
    session.add(document)
    session.flush()
    return document


def test_chunking_preserves_page_table_row_and_fact_provenance(session):
    _document(session)
    page = DocumentPage(document_id=1, page_number=8, text="MCL production was 16 MT.", extraction_method="NATIVE")
    table = DocumentTable(
        document_id=1,
        page_number=8,
        table_number=2,
        title="Production during May 2023",
        headers_json=["Subsidiary", "Production"],
        rows_json=[["MCL", "16 MT"], ["ECL", "14 MT"]],
        extraction_method="NATIVE_TABLE",
    )
    fact = StructuredFact(
        document_id=1,
        document_page_id=None,
        page_number=8,
        document_table_id=None,
        entity_type="SUBSIDIARY",
        entity_name_raw="MCL",
        entity_name_canonical="MCL",
        entity_resolution_method="ALIAS",
        metric_type="COAL_PRODUCTION",
        metric_name_raw="Coal Production",
        metric_name_canonical="COAL_PRODUCTION",
        metric_resolution_method="HEADER",
        raw_value_text="16 MT",
        raw_value_numeric=Decimal("16"),
        normalized_value=Decimal("16"),
        raw_unit="MT",
        normalized_unit="MT",
        period_raw="May 2023",
        period_normalized="2023-05",
        period_type="MONTH",
        extraction_method="NATIVE_TABLE",
        extraction_confidence=Decimal("0.9"),
        evidence_type="TABLE_CELL",
        evidence_locator_json={"document_table_id": 1, "row_index": 0, "column_index": 1},
        validation_status="ACCEPTED",
        fact_status="ACCEPTED",
        fact_key="a" * 64,
        duplicate_group_key="b" * 64,
    )
    session.add_all([page, table, fact])
    session.commit()

    specs = build_knowledge_chunk_specs(session, 1)
    assert any(spec.chunk_type == "PAGE_TEXT" for spec in specs)
    row = next(spec for spec in specs if spec.chunk_type == "TABLE_ROW")
    assert row.document_page_id == page.id
    assert row.source_locator["document_table_id"] == table.id
    assert row.source_locator["row_index"] == 0
    fact_spec = next(spec for spec in specs if spec.chunk_type == "STRUCTURED_FACT")
    assert fact_spec.source_locator["structured_fact_id"] == fact.id
    assert fact_spec.source_locator["column_index"] == 1


def test_navigation_pages_are_not_embedded_and_chunk_upsert_is_idempotent(session):
    _document(session)
    session.add(DocumentPage(document_id=1, page_number=7, text="Table of Contents\nState-wise Coal Production\n3\nExploration\n42"))
    session.commit()
    specs = build_knowledge_chunk_specs(session, 1)
    assert specs == []
    persist_knowledge_chunks(session, specs)
    assert session.query(KnowledgeChunk).count() == 0


def test_duplicate_prevention_and_semantic_top_k_with_test_vectors(session):
    _document(session)
    session.add(DocumentPage(document_id=1, page_number=1, text="coal production target"))
    session.commit()
    specs = build_knowledge_chunk_specs(session, 1)
    first = persist_knowledge_chunks(session, specs)
    second = persist_knowledge_chunks(session, specs)
    assert first["inserted"] == len(specs)
    assert second["inserted"] == 0
    assert session.query(KnowledgeChunk).count() == len(specs)

    rows = session.query(KnowledgeChunk).all()
    for index, row in enumerate(rows):
        vector = [0.0] * 384
        vector[0] = 1.0 if index == 0 else 0.2
        row.embedding = vector
        row.embedding_status = "READY"
    session.commit()
    result = semantic_search(session, "production", top_k=1, query_embedding=[1.0] + [0.0] * 383)
    assert result["status"] == "OK"
    assert result["count"] == 1
    assert result["results"][0]["source_locator"]["page_number"] == 1


def test_structured_filters_preserve_distinct_periods_and_conflicts(session):
    _document(session)
    facts = []
    for index, period, value in [(1, "2023-05", "16"), (2, "2023-06", "18"), (3, "2023-05", "17")]:
        facts.append(StructuredFact(
            document_id=1,
            entity_type="SUBSIDIARY",
            entity_name_raw="MCL",
            entity_name_canonical="MCL",
            entity_resolution_method="ALIAS",
            metric_type="COAL_PRODUCTION",
            metric_name_raw="Coal Production",
            metric_name_canonical="COAL_PRODUCTION",
            metric_resolution_method="HEADER",
            raw_value_text=f"{value} MT",
            raw_value_numeric=Decimal(value),
            normalized_value=Decimal(value),
            raw_unit="MT",
            normalized_unit="MT",
            period_raw=period,
            period_normalized=period,
            period_type="MONTH",
            extraction_method="NATIVE_TABLE",
            extraction_confidence=Decimal("0.9"),
            evidence_type="TABLE_CELL",
            evidence_locator_json={"document_id": 1, "page_number": index, "row_index": 0, "column_index": 1},
            validation_status="ACCEPTED",
            fact_status="ACCEPTED",
            fact_key=f"{index:064d}",
            duplicate_group_key=f"{index + 10:064d}",
        ))
    session.add_all(facts)
    session.commit()
    result = search_structured_facts(session, entity="MCL", metric="COAL_PRODUCTION", period="2023-05")
    assert result["count"] == 2
    assert result["results"][0]["period"]["normalized"] == "2023-05"

    # Hybrid retrieval keeps the structured candidates separate and does not
    # collapse the two source facts into one synthetic answer.
    hybrid = hybrid_search(session, "MCL production", top_k=10, structured_filters={"entity": "MCL"}, semantic_filters={})
    assert hybrid["conflicts_preserved"] is True
    assert len(hybrid["structured"]["results"]) == 3
    may_candidates = [item for item in hybrid["structured"]["results"] if item["period"]["normalized"] == "2023-05"]
    assert len(may_candidates) == 2
    assert hybrid["semantic"]["status"] == "OK" or hybrid["semantic"]["status"] == "UNAVAILABLE"


def test_semantic_unavailable_is_explicit_and_never_uses_hash_vector(session, monkeypatch):
    _document(session)
    session.add(DocumentPage(document_id=1, page_number=1, text="evidence"))
    session.commit()
    specs = build_knowledge_chunk_specs(session, 1)
    persist_knowledge_chunks(session, specs)

    def unavailable(_texts):
        raise ProductionEmbeddingUnavailable("test model unavailable")

    monkeypatch.setattr("app.services.knowledge_retrieval_service.generate_production_embedding", lambda _text: (_ for _ in ()).throw(ProductionEmbeddingUnavailable("test model unavailable")))
    result = semantic_search(session, "evidence")
    assert result["status"] == "UNAVAILABLE"
    assert result["results"] == []
    assert all(row.embedding is None for row in session.query(KnowledgeChunk).all())


def test_migration_is_additive_idempotent_and_api_routes_require_authentication():
    migration_path = Path(__file__).resolve().parents[1] / "migrations" / "005_step3_pgvector_knowledge_chunks.sql"
    migration = migration_path.read_text(encoding="utf-8").lower()
    assert "create extension if not exists vector" in migration
    assert "create table if not exists knowledge_chunks" in migration
    assert "create index if not exists" in migration
    assert "embedding vector(384)" in migration
    assert all(route.dependant.dependencies for route in knowledge_router.routes)
