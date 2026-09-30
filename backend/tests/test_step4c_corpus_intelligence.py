from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
import app.models  # noqa: F401
from app.models.document import Document
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.structured_fact import StructuredFact
from app.services.corpus_intelligence_service import (
    historical_comparison,
    topics,
    trend_series,
    word_cloud,
)
from app.api.analytics import router as analytics_router


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def _document(session, document_id, subsidiary="MCL"):
    document = Document(
        id=document_id,
        filename=f"corpus-{document_id}.pdf",
        file_path=f"/safe/corpus-{document_id}.pdf",
        file_hash=f"{document_id:064d}",
        file_type="PDF",
        subsidiary=subsidiary,
        status="INDEXED",
        fiscal_year="2023-24",
    )
    session.add(document)
    session.flush()
    return document


def _fact(session, document_id, fact_id, *, entity, metric, value, period, unit="MT"):
    fact = StructuredFact(
        id=fact_id,
        document_id=document_id,
        page_number=fact_id,
        entity_type="SUBSIDIARY",
        entity_name_raw=entity,
        entity_name_canonical=entity,
        entity_resolution_method="TEST",
        metric_type=metric,
        metric_name_raw=metric,
        metric_name_canonical=metric,
        metric_resolution_method="TEST",
        raw_value_text=f"{value} {unit}",
        raw_value_numeric=Decimal(str(value)),
        normalized_value=Decimal(str(value)),
        raw_unit=unit,
        normalized_unit=unit,
        period_raw=period,
        period_normalized=period,
        period_type="FISCAL_YEAR" if "FY" in period else "MONTH",
        extraction_method="NATIVE_TABLE",
        extraction_confidence=Decimal("0.9000"),
        evidence_type="TABLE_CELL",
        evidence_locator_json={"document_table_id": fact_id, "row_index": 0, "column_index": 1},
        validation_status="ACCEPTED",
        fact_status="ACCEPTED",
        fact_key=f"{fact_id:064d}",
        duplicate_group_key=f"{fact_id + 100:064d}",
    )
    session.add(fact)
    return fact


def test_word_cloud_is_corpus_derived_and_suppresses_noise(session):
    _document(session, 1)
    session.add(KnowledgeChunk(
        chunk_key="a" * 64,
        document_id=1,
        page_number=8,
        chunk_index=0,
        chunk_type="PAGE_TEXT",
        chunk_text="Table of Contents Page 7 Coal production production dispatch",
        content_hash="b" * 64,
        source_locator_json={"page_number": 8},
        metadata_json={},
        embedding_status="UNAVAILABLE",
    ))
    session.commit()
    result = word_cloud(session, top_n=20)
    words = {item["word"] for item in result["topics"]}
    assert "production" in words
    assert "coal" in words
    assert "page" not in words
    assert "contents" not in words
    assert all(item["weight"] >= 1 for item in result["topics"])


def test_topics_link_to_persisted_chunk_evidence(session):
    _document(session, 1)
    session.add(KnowledgeChunk(
        chunk_key="c" * 64,
        document_id=1,
        page_number=4,
        chunk_index=0,
        chunk_type="TABLE_ROW",
        chunk_text="MCL coal production target achievement",
        content_hash="d" * 64,
        source_locator_json={"document_table_id": 3, "row_index": 2},
        metadata_json={},
        embedding_status="UNAVAILABLE",
    ))
    session.commit()
    result = topics(session)
    assert result["topics"]
    assert result["topics"][0]["evidence"][0]["document_id"] == 1
    assert result["topics"][0]["evidence"][0]["page_number"] == 4


def test_empty_corpus_is_explicit(session):
    assert word_cloud(session)["status"] == "EMPTY"
    assert topics(session)["topics"] == []


def test_trend_preserves_periods_and_does_not_sum_all_years(session):
    _document(session, 1)
    _fact(session, 1, 1, entity="MCL", metric="COAL_PRODUCTION", value="10", period="2022-23")
    _fact(session, 1, 2, entity="MCL", metric="COAL_PRODUCTION", value="15", period="2023-24")
    session.commit()
    result = trend_series(session, metric="COAL_PRODUCTION", entity="MCL")
    assert [point["value"] for point in result["points"]] == [10.0, 15.0]
    assert result["all_years_not_summed"] is True


def test_same_period_comparison_and_provenance(session):
    _document(session, 1)
    _fact(session, 1, 1, entity="MCL", metric="COAL_PRODUCTION", value="10", period="2023-24")
    _fact(session, 1, 2, entity="ECL", metric="COAL_PRODUCTION", value="12", period="2023-24")
    session.commit()
    result = historical_comparison(session, metric="COAL_PRODUCTION", entity="MCL",
                                   comparison_entity="ECL", period="2023-24")
    assert result["status"] == "OK"
    assert result["observations"][0]["absolute_change"] == 2.0
    assert set(result["provenance_fact_ids"]) == {1, 2}


def test_conflicting_observations_are_not_averaged(session):
    _document(session, 1)
    _fact(session, 1, 1, entity="MCL", metric="COAL_PRODUCTION", value="10", period="2023-24")
    _fact(session, 1, 2, entity="MCL", metric="COAL_PRODUCTION", value="12", period="2023-24")
    session.commit()
    result = trend_series(session, metric="COAL_PRODUCTION", entity="MCL")
    assert result["points"][0]["status"] == "CONFLICTING"
    assert result["points"][0]["value"] is None
    assert {item["value"] for item in result["points"][0]["candidates"]} == {10.0, 12.0}


def test_unit_mismatch_is_kept_separate(session):
    _document(session, 1)
    _fact(session, 1, 1, entity="MCL", metric="COAL_PRODUCTION", value="10", period="2023-24", unit="MT")
    _fact(session, 1, 2, entity="MCL", metric="COAL_PRODUCTION", value="100", period="2023-24", unit="KT")
    session.commit()
    result = trend_series(session, metric="COAL_PRODUCTION", entity="MCL")
    assert len(result["points"]) == 2
    assert {point["unit"] for point in result["points"]} == {"MT", "KT"}


def test_analytics_routes_require_authenticated_user():
    paths = {route.path for route in analytics_router.routes}
    assert {"/analytics/wordcloud", "/analytics/topics", "/analytics/trends", "/analytics/historical"} <= paths
    for route in analytics_router.routes:
        assert route.dependant.dependencies
