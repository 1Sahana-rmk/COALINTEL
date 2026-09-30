"""Authenticated Step 3 knowledge/retrieval inspection APIs.

These endpoints expose evidence candidates only.  They do not generate an
answer, invoke an LLM, or implement the future Step 4 question router.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import get_db
from app.core.rbac import INGESTION_ROLES, get_current_user, require_roles
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.user import User
from app.services.embedding_service import embedding_runtime_status
from app.services.knowledge_retrieval_service import (
    hybrid_search,
    index_document_knowledge,
    search_structured_facts,
    semantic_search,
)

router = APIRouter(prefix="/knowledge", tags=["Step 3 Knowledge Retrieval"])
READ_ROLES = ["Admin", "Analyst", "Reviewer", "Viewer"]


def _reader(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in READ_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role is not authorized to inspect knowledge retrieval.")
    return current_user


@router.get("/health")
def knowledge_health(db: Session = Depends(get_db), current_user: User = Depends(_reader)):
    try:
        table_exists = "knowledge_chunks" in inspect(db.get_bind()).get_table_names()
        chunk_count = db.query(func.count(KnowledgeChunk.id)).scalar() if table_exists else 0
        ready_count = db.query(func.count(KnowledgeChunk.id)).filter(KnowledgeChunk.embedding_status == "READY").scalar() if table_exists else 0
    except SQLAlchemyError as exc:
        table_exists = False
        chunk_count = ready_count = 0
        error = f"knowledge storage unavailable: {type(exc).__name__}"
    else:
        error = None
    return {
        "status": "READY" if table_exists else "MIGRATION_REQUIRED",
        "storage": "POSTGRESQL_PGVECTOR" if table_exists else "NOT_AVAILABLE",
        "knowledge_chunks_table": table_exists,
        "chunk_count": chunk_count,
        "embedded_chunk_count": ready_count,
        "embedding": embedding_runtime_status(initialize=False),
        "error": error,
    }


@router.get("/stats")
def knowledge_stats(db: Session = Depends(get_db), current_user: User = Depends(_reader)):
    if "knowledge_chunks" not in inspect(db.get_bind()).get_table_names():
        return {"status": "MIGRATION_REQUIRED", "counts": {"total": 0, "ready": 0, "unavailable": 0, "failed": 0}}
    rows = db.query(KnowledgeChunk.embedding_status, func.count(KnowledgeChunk.id)).group_by(KnowledgeChunk.embedding_status).all()
    counts = {str(state): int(count) for state, count in rows}
    return {"status": "OK", "counts": {"total": sum(counts.values()), **counts}}


@router.post("/index-document/{document_id}")
def index_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(INGESTION_ROLES)),
):
    try:
        return index_document_knowledge(db, document_id)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Knowledge storage is unavailable: {type(exc).__name__}") from exc


@router.get("/structured-facts/search")
def structured_fact_search(
    entity: Optional[str] = None,
    metric: Optional[str] = None,
    period: Optional[str] = None,
    document_id: Optional[int] = None,
    subsidiary: Optional[str] = None,
    validation_status: Optional[str] = None,
    fact_status: Optional[str] = None,
    exact_value: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(_reader),
):
    return search_structured_facts(
        db,
        entity=entity,
        metric=metric,
        period=period,
        document_id=document_id,
        subsidiary=subsidiary,
        validation_status=validation_status,
        fact_status=fact_status,
        exact_value=exact_value,
        limit=limit,
    )


@router.get("/semantic/search")
def semantic_search_endpoint(
    q: str = Query(..., min_length=1),
    top_k: int = Query(5, ge=1, le=100),
    document_id: Optional[int] = None,
    page_number: Optional[int] = None,
    chunk_type: Optional[str] = None,
    subsidiary: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(_reader),
):
    return semantic_search(
        db,
        q,
        top_k=top_k,
        document_id=document_id,
        page_number=page_number,
        chunk_type=chunk_type,
        subsidiary=subsidiary,
    )


@router.get("/hybrid/search")
def hybrid_search_endpoint(
    q: str = Query(..., min_length=1),
    top_k: int = Query(5, ge=1, le=100),
    entity: Optional[str] = None,
    metric: Optional[str] = None,
    period: Optional[str] = None,
    document_id: Optional[int] = None,
    subsidiary: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(_reader),
):
    return hybrid_search(
        db,
        q,
        top_k=top_k,
        structured_filters={
            "entity": entity,
            "metric": metric,
            "period": period,
            "document_id": document_id,
            "subsidiary": subsidiary,
            "limit": top_k,
        },
        semantic_filters={"document_id": document_id, "subsidiary": subsidiary},
    )
