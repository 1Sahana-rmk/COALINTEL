from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from app.models.user import User
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.core.rbac import get_current_user, require_roles
from app.schemas.query import QueryRequest, QueryResponse, CitationItem, EvidenceChunkItem
from app.services.rag_service import execute_rag_query
from app.services.vector_store_service import add_chunks_to_vector_store
from app.services.normalization_service import normalize_subsidiary_scope

router = APIRouter(tags=["Q&A & Vector Retrieval"])


@router.post("/query/ask", response_model=QueryResponse)
def ask_question(
    payload: QueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Evidence-Grounded Q&A Endpoint:
    - Performs Hybrid Search (ChromaDB Vector + PostgreSQL BM25 Keyword fused via RRF k=60).
    - Enforces XML Prompt Isolation (<untrusted_document_context>).
    - Queries LLM Provider (Gemini / OpenAI / Degraded Mode).
    - Enforces Citation Gate verification ([Doc_Name.pdf, Page X]).
    """
    if not payload.query or not payload.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query string cannot be empty."
        )

    # Resolve subsidiary filter with RBAC enforcement (BUG-01, BUG-07)
    normalized_sub = normalize_subsidiary_scope(payload.subsidiary_filter)

    # Check if user has global query privileges
    is_global_user = (
        current_user.role in ["Admin", "Analyst"]
        or not current_user.subsidiary
        or current_user.subsidiary.strip().upper() in ["CIL HQ", "CIL", "MINISTRY OF COAL"]
    )

    if is_global_user:
        effective_subsidiary = normalized_sub
    else:
        # Subsidiary-scoped user: restrict to user's assigned subsidiary
        effective_subsidiary = current_user.subsidiary

    result = execute_rag_query(
        db=db,
        query_text=payload.query,
        top_k=payload.top_k or 5,
        subsidiary_filter=effective_subsidiary
    )

    evidence_items = [
        EvidenceChunkItem(
            chunk_id=c["chunk_id"] if isinstance(c.get("chunk_id"), int) else None,
            document_id=c["document_id"],
            filename=c["filename"],
            page_number=c["page_number"],
            chunk_index=c["chunk_index"],
            text=c["text"],
            rrf_score=c["rrf_score"],
            vector_score=c.get("vector_score", 0.0),
            keyword_score=c.get("keyword_score", 0.0)
        )
        for c in result["evidence_chunks"]
    ]

    citation_items = [
        CitationItem(
            document_name=c["document_name"],
            page_number=c["page_number"],
            citation_tag=c["citation_tag"]
        )
        for c in result["citations"]
    ]

    return QueryResponse(
        query=result["query"],
        answer=result["answer"],
        citations=citation_items,
        evidence_chunks=evidence_items,
        provider=result["provider"],
        degraded_mode=result["degraded_mode"],
        mode=result.get("mode", "EVIDENCE_GROUNDED")
    )


@router.post("/query/index-document/{id}", status_code=status.HTTP_200_OK)
def index_document_vectors(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Admin", "Analyst"]))
):
    """
    Indexes or re-indexes an existing document's 500-token chunks into persistent ChromaDB.
    """
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document ID #{id} not found."
        )

    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == id).all()
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document ID #{id} has no chunks to index. Ensure processing pipeline has executed."
        )

    success = add_chunks_to_vector_store(chunks, filename=doc.filename, subsidiary=doc.subsidiary)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to index document chunks into ChromaDB."
        )

    return {
        "status": "success",
        "message": f"Successfully indexed {len(chunks)} chunks into ChromaDB for Document '{doc.filename}'."
    }
