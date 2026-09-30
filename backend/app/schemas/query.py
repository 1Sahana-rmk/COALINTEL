from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    subsidiary_filter: Optional[str] = None


class CitationItem(BaseModel):
    document_name: str
    page_number: int
    citation_tag: str
    document_id: Optional[int] = None
    evidence_type: Optional[str] = None
    table_id: Optional[int] = None
    locator: Dict[str, Any] = Field(default_factory=dict)
    source_url: Optional[str] = None
    source_type: Optional[str] = None
    file_type: Optional[str] = None
    excerpt: Optional[str] = None
    extraction_method: Optional[str] = None
    confidence: Optional[float] = None
    validation_state: Optional[str] = None


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
    route: Optional[str] = None
    support_state: Optional[str] = None
    generation_status: Optional[str] = None
    analysis: Optional[Dict[str, Any]] = None
    structured_facts: List[Dict[str, Any]] = Field(default_factory=list)
    semantic_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    conflicts: List[List[Dict[str, Any]]] = Field(default_factory=list)
    conflict_states: List[Dict[str, Any]] = Field(default_factory=list)
    claims: List[Dict[str, Any]] = Field(default_factory=list)
    source_references: List[Dict[str, Any]] = Field(default_factory=list)
