"""Step 3 structured, semantic and hybrid retrieval primitives.

This module deliberately does not answer questions or invoke an LLM.  It
returns candidates plus evidence so a later assistant can apply policy and
ground every claim.
"""

from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import Float, inspect
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.structured_fact import StructuredFact
from app.services.embedding_service import (
    EMBEDDING_MODEL_NAME,
    ProductionEmbeddingUnavailable,
    embedding_runtime_status,
    generate_production_embedding,
    generate_production_embeddings,
)
from app.services.knowledge_chunking_service import build_knowledge_chunk_specs, persist_knowledge_chunks


def _table_available(db: Session) -> bool:
    bind = db.get_bind()
    return "knowledge_chunks" in inspect(bind).get_table_names()


def _fact_result(fact: StructuredFact) -> Dict[str, Any]:
    return {
        "fact_id": fact.id,
        "document_id": fact.document_id,
        "page_id": fact.document_page_id,
        "page_number": fact.page_number,
        "table_id": fact.document_table_id,
        "entity": {
            "type": fact.entity_type,
            "raw": fact.entity_name_raw,
            "canonical": fact.entity_name_canonical,
            "resolution_method": fact.entity_resolution_method,
            "resolution_confidence": float(fact.entity_resolution_confidence) if fact.entity_resolution_confidence is not None else None,
        },
        "metric": {
            "type": fact.metric_type,
            "raw": fact.metric_name_raw,
            "canonical": fact.metric_name_canonical,
            "resolution_method": fact.metric_resolution_method,
            "resolution_confidence": float(fact.metric_resolution_confidence) if fact.metric_resolution_confidence is not None else None,
        },
        "value": {
            "raw": fact.raw_value_text,
            "raw_numeric": float(fact.raw_value_numeric) if fact.raw_value_numeric is not None else None,
            "normalized": float(fact.normalized_value) if fact.normalized_value is not None else None,
            "raw_unit": fact.raw_unit,
            "normalized_unit": fact.normalized_unit,
        },
        "period": {
            "raw": fact.period_raw,
            "normalized": fact.period_normalized,
            "type": fact.period_type,
        },
        "extraction_method": fact.extraction_method,
        "extraction_confidence": float(fact.extraction_confidence) if fact.extraction_confidence is not None else None,
        "evidence_type": fact.evidence_type,
        "evidence_locator": fact.evidence_locator_json or {},
        "validation_status": fact.validation_status,
        "fact_status": fact.fact_status,
        "validation_warnings": fact.validation_warnings_json or [],
    }


def search_structured_facts(
    db: Session,
    *,
    entity: Optional[str] = None,
    metric: Optional[str] = None,
    period: Optional[str] = None,
    document_id: Optional[int] = None,
    subsidiary: Optional[str] = None,
    validation_status: Optional[str] = None,
    fact_status: Optional[str] = None,
    exact_value: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """Filter canonical Step 2C facts without semantic similarity."""
    limit = max(1, min(limit, 500))
    query = db.query(StructuredFact).join(Document, Document.id == StructuredFact.document_id)
    if entity:
        term = f"%{entity.strip()}%"
        query = query.filter(
            StructuredFact.entity_name_canonical.ilike(term) |
            StructuredFact.entity_name_raw.ilike(term)
        )
    if metric:
        term = f"%{metric.strip()}%"
        query = query.filter(
            StructuredFact.metric_name_canonical.ilike(term) |
            StructuredFact.metric_name_raw.ilike(term) |
            StructuredFact.metric_type.ilike(term)
        )
    if period:
        term = f"%{period.strip()}%"
        query = query.filter(
            StructuredFact.period_normalized.ilike(term) |
            StructuredFact.period_raw.ilike(term)
        )
    if document_id is not None:
        query = query.filter(StructuredFact.document_id == document_id)
    if subsidiary:
        query = query.filter(Document.subsidiary.ilike(f"%{subsidiary.strip()}%"))
    if validation_status:
        query = query.filter(StructuredFact.validation_status == validation_status)
    if fact_status:
        query = query.filter(StructuredFact.fact_status == fact_status)
    if exact_value is not None:
        try:
            numeric = Decimal(str(exact_value).replace(",", "").strip())
        except (InvalidOperation, ValueError):
            numeric = None
        if numeric is not None:
            query = query.filter(
                (StructuredFact.raw_value_numeric == numeric) |
                (StructuredFact.normalized_value == numeric)
            )
        else:
            query = query.filter(StructuredFact.raw_value_text == exact_value)
    facts = query.order_by(StructuredFact.id).limit(limit).all()
    return {
        "status": "OK",
        "retrieval_mode": "STRUCTURED",
        "count": len(facts),
        "results": [_fact_result(fact) for fact in facts],
    }


def _cosine(left: Iterable[float], right: Iterable[float]) -> float:
    left = list(left)
    right = list(right)
    denominator = math.sqrt(sum(x * x for x in left)) * math.sqrt(sum(x * x for x in right))
    return sum(a * b for a, b in zip(left, right)) / denominator if denominator else 0.0


def _chunk_result(chunk: KnowledgeChunk, score: Optional[float]) -> Dict[str, Any]:
    return {
        "chunk_id": chunk.id,
        "chunk_key": chunk.chunk_key,
        "document_id": chunk.document_id,
        "page_id": chunk.document_page_id,
        "page_number": chunk.page_number,
        "table_id": chunk.document_table_id,
        "chunk_index": chunk.chunk_index,
        "chunk_type": chunk.chunk_type,
        "text": chunk.chunk_text,
        "retrieval_score": score,
        "embedding_provider": chunk.embedding_provider,
        "embedding_model": chunk.embedding_model,
        "source_locator": chunk.source_locator_json or {},
        "metadata": chunk.metadata_json or {},
        "content_hash": chunk.content_hash,
    }


def index_document_knowledge(
    db: Session,
    document_id: int,
    *,
    include_fact_candidates: bool = False,
    replace_existing: bool = False,
) -> Dict[str, Any]:
    """Persist evidence chunks and real embeddings when the model is ready."""
    specs = build_knowledge_chunk_specs(db, document_id, include_fact_candidates=include_fact_candidates)
    counts = persist_knowledge_chunks(
        db,
        specs,
        replace_document_id=document_id if replace_existing else None,
    )
    rows = db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == document_id).order_by(KnowledgeChunk.id).all()
    texts = [row.chunk_text for row in rows]
    try:
        vectors = generate_production_embeddings(texts)
        for row, vector in zip(rows, vectors):
            row.embedding = vector
            row.embedding_status = "READY"
            row.embedding_provider = embedding_runtime_status(initialize=False).get("provider")
            row.embedding_model = EMBEDDING_MODEL_NAME
        embedding_status = "READY"
    except ProductionEmbeddingUnavailable as exc:
        for row in rows:
            row.embedding = None
            row.embedding_status = "UNAVAILABLE"
            row.embedding_provider = None
            row.embedding_model = EMBEDDING_MODEL_NAME
            metadata = dict(row.metadata_json or {})
            metadata["embedding_unavailable_reason"] = str(exc)
            row.metadata_json = metadata
        embedding_status = "UNAVAILABLE"
    db.commit()
    return {**counts, "embedding_status": embedding_status, "chunk_count": len(rows)}


def semantic_search(
    db: Session,
    query_text: str,
    *,
    top_k: int = 5,
    document_id: Optional[int] = None,
    page_number: Optional[int] = None,
    chunk_type: Optional[str] = None,
    subsidiary: Optional[str] = None,
    query_embedding: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """Search pgvector evidence chunks; never substitutes hash vectors."""
    if not query_text or not query_text.strip():
        return {"status": "INVALID", "retrieval_mode": "SEMANTIC", "count": 0, "results": []}
    if not _table_available(db):
        return {
            "status": "UNAVAILABLE",
            "retrieval_mode": "SEMANTIC",
            "count": 0,
            "results": [],
            "reason": "Step 3 knowledge_chunks migration has not been applied.",
        }
    try:
        vector = query_embedding or generate_production_embedding(query_text)
    except ProductionEmbeddingUnavailable as exc:
        return {
            "status": "UNAVAILABLE",
            "retrieval_mode": "SEMANTIC",
            "count": 0,
            "results": [],
            "reason": str(exc),
        }

    top_k = max(1, min(top_k, 100))
    query = db.query(KnowledgeChunk).filter(KnowledgeChunk.embedding_status == "READY")
    if document_id is not None:
        query = query.filter(KnowledgeChunk.document_id == document_id)
    if page_number is not None:
        query = query.filter(KnowledgeChunk.page_number == page_number)
    if chunk_type:
        query = query.filter(KnowledgeChunk.chunk_type == chunk_type)
    if subsidiary:
        query = query.join(Document, Document.id == KnowledgeChunk.document_id).filter(Document.subsidiary.ilike(f"%{subsidiary.strip()}%"))

    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        # Use the pgvector cosine-distance operator directly.  The model uses
        # a dialect-switching TypeDecorator so SQLite tests can store JSON;
        # relying on the pgvector comparator would make that wrapper lose the
        # comparator methods at import time.
        distance = KnowledgeChunk.embedding.op("<=>", return_type=Float)(vector).label("distance")
        # Re-read the small result set with distances so the response retains
        # the exact pgvector score without making a second full scan.
        scored = db.query(KnowledgeChunk, distance).filter(KnowledgeChunk.embedding_status == "READY")
        if document_id is not None:
            scored = scored.filter(KnowledgeChunk.document_id == document_id)
        if page_number is not None:
            scored = scored.filter(KnowledgeChunk.page_number == page_number)
        if chunk_type:
            scored = scored.filter(KnowledgeChunk.chunk_type == chunk_type)
        if subsidiary:
            scored = scored.join(Document, Document.id == KnowledgeChunk.document_id).filter(Document.subsidiary.ilike(f"%{subsidiary.strip()}%"))
        pairs = scored.order_by(distance).limit(top_k).all()
        results = [_chunk_result(row, 1.0 - float(dist)) for row, dist in pairs]
    else:
        # SQLite is test-only.  It stores vectors as JSON and uses the same
        # cosine definition to validate ranking without masquerading as pgvector.
        rows = query.limit(5000).all()
        results = sorted((_chunk_result(row, _cosine(vector, row.embedding)) for row in rows if row.embedding), key=lambda item: item["retrieval_score"], reverse=True)[:top_k]
    return {"status": "OK", "retrieval_mode": "SEMANTIC", "count": len(results), "results": results}


def hybrid_search(
    db: Session,
    query_text: str,
    *,
    top_k: int = 5,
    structured_filters: Optional[Dict[str, Any]] = None,
    semantic_filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return separate structured and semantic candidates without collapsing conflicts."""
    filters = dict(structured_filters or {})
    filters.setdefault("limit", top_k)
    structured = search_structured_facts(db, **filters)
    semantic = semantic_search(db, query_text, top_k=top_k, **(semantic_filters or {}))
    return {
        "status": "OK" if semantic["status"] == "OK" else "DEGRADED",
        "retrieval_mode": "HYBRID",
        "structured": structured,
        "semantic": semantic,
        "conflicts_preserved": True,
        "results": {
            "structured": structured["results"],
            "semantic": semantic["results"],
        },
    }
