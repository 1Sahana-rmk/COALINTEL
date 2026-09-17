from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, ConfigDict


class ParliamentaryBriefingRequest(BaseModel):
    question_text: str
    fiscal_year: Optional[str] = "2023-24"
    subsidiary_filter: Optional[str] = "ALL CIL"
    question_type: Optional[str] = "GENERAL"  # TARGETS, OVERBURDEN, SUBSIDIARIES, DISCREPANCIES, GENERAL


class SubsidiaryMetricItem(BaseModel):
    mine_name: str
    subsidiary: str
    metric_name: str
    numeric_value: float
    unit: str
    standard_value: Optional[float] = None
    standard_unit: Optional[str] = "MT"
    fiscal_year: str
    page_number: Optional[int] = None
    document_filename: Optional[str] = None


class FlaggedDiscrepancyItem(BaseModel):
    entity: str
    metric_name: str
    fiscal_year: str
    doc_a_filename: str
    doc_a_value: float
    doc_b_filename: str
    doc_b_value: float
    unit: str
    variance_percentage: float
    status: str  # DISCREPANCY DETECTED
    is_seeded_demo: bool = False
    provenance_label: str  # e.g. "Seeded Mine-Level Discrepancy" or "Verified High-Precision Conflict"


class BriefingEvidenceItem(BaseModel):
    chunk_id: Optional[Union[int, str]] = None
    document_id: int
    document_name: str
    page_number: int
    chunk_index: int
    text_snippet: str
    rrf_score: float
    subsidiary: str


class ParliamentaryBriefingResponse(BaseModel):
    question: str
    question_type: str
    fiscal_year: str
    selected_scope: str
    executive_summary: str
    key_findings: List[str]
    subsidiary_metrics: List[SubsidiaryMetricItem]
    discrepancies: List[FlaggedDiscrepancyItem]
    evidence: List[BriefingEvidenceItem]
    confidence: float
    confidence_rating: str  # HIGH, MEDIUM, LOW, DEGRADED, INSUFFICIENT_EVIDENCE
    has_sufficient_evidence: bool = True
    limitations: List[str]
    generated_at: str

    model_config = ConfigDict(from_attributes=True)
