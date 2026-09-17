from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    subsidiary_filter: Optional[str] = None


class CitationItem(BaseModel):
    document_name: str
    page_number: int
    citation_tag: str


class EvidenceChunkItem(BaseModel):
    chunk_id: Optional[int] = None
    document_id: int
    filename: str
    page_number: int
    chunk_index: int
    text: str
    rrf_score: float
    vector_score: Optional[float] = 0.0
    keyword_score: Optional[float] = 0.0

    model_config = ConfigDict(from_attributes=True)


class QueryResponse(BaseModel):
    query: str
    answer: str
    citations: List[CitationItem]
    evidence_chunks: List[EvidenceChunkItem]
    provider: str
    degraded_mode: bool = False
    mode: Optional[str] = "EVIDENCE_GROUNDED"
