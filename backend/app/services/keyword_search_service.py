import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.document_chunk import DocumentChunk
from app.models.document import Document
from app.services.normalization_service import normalize_subsidiary_scope

logger = logging.getLogger(__name__)


def search_keyword_store(
    db: Session,
    query_text: str,
    top_k: int = 5,
    subsidiary_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Executes PostgreSQL full-text/keyword search over document_chunks table.
    Filters query terms and ranks matched chunks by keyword frequency.
    Preserves document and page provenance.
    """
    if not query_text or not query_text.strip():
        return []

    # Extract distinct keywords (>2 chars)
    keywords = [kw.lower() for kw in query_text.split() if len(kw) > 2]
    if not keywords:
        return []

    query = db.query(DocumentChunk, Document.filename, Document.subsidiary).\
        join(Document, DocumentChunk.document_id == Document.id)

    norm_sub = normalize_subsidiary_scope(subsidiary_filter)
    if norm_sub:
        query = query.filter(Document.subsidiary == norm_sub)

    # Build ILIKE filters for keywords
    ilike_filters = [DocumentChunk.chunk_text.ilike(f"%{kw}%") for kw in keywords]
    results = query.filter(or_(*ilike_filters)).limit(top_k * 3).all()

    results_list = []
    for chunk, filename, sub in results:
        # Score chunk by keyword occurrence count
        text_lower = chunk.chunk_text.lower()
        matched_count = sum(1 for kw in keywords if kw in text_lower)
        keyword_score = round(matched_count / len(keywords), 4)

        results_list.append({
            "chunk_id": chunk.id,
            "document_id": chunk.document_id,
            "filename": filename,
            "page_number": chunk.page_number,
            "chunk_index": chunk.chunk_index,
            "text": chunk.chunk_text,
            "keyword_score": keyword_score
        })

    # Sort descending by keyword score and trim to top_k
    results_list.sort(key=lambda x: x["keyword_score"], reverse=True)
    return results_list[:top_k]
