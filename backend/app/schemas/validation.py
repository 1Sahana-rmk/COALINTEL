from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ValidationItemResponse(BaseModel):
    id: int
    mine_name: str
    subsidiary: str
    metric_name: str
    fiscal_year: str
    reported_value: Optional[float] = None
    calculated_value: Optional[float] = None
    standard_unit: str
    percentage_difference: Optional[float] = None
    discrepancy_available: bool = False
    validation_status: str
    message: str
    document_id: int
    filename: str
    # This is extraction evidence quality, not the result of the arithmetic
    # validation check.  Keep it nullable: older metrics may not have a
    # defensible persisted extraction score.
    extraction_confidence: Optional[float] = None
    page_number: Optional[int] = None
    data_origin: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ConflictEvidenceResponse(BaseModel):
    """Persisted extraction provenance for one side of a conflict.

    ``metric_id`` is the stable extracted-metric record that supplied the
    comparison value.  The current metric schema stores page provenance but
    does not store a metric-level bounding box, so the API deliberately
    leaves ``bounding_box`` null rather than inventing geometry.
    """

    document_id: Optional[int] = None
    metric_id: Optional[int] = None
    page_number: Optional[int] = None
    bounding_box: Optional[dict] = None
    provenance_available: bool = False
    warning: Optional[str] = None


class ConflictResponse(BaseModel):
    id: int
    # Stable API identity. The legacy numeric id remains for compatibility,
    # while namespaced keys prevent generated and official records colliding.
    conflict_key: Optional[str] = None
    mine_name: str
    subsidiary: str
    metric_name: str
    fiscal_year: str
    document_a_id: Optional[int] = None
    document_a_source_id: Optional[str] = None
    document_a_filename: str
    document_a_value: float
    document_a_unit: str
    evidence_a: Optional[ConflictEvidenceResponse] = None
    document_b_id: Optional[int] = None
    document_b_source_id: Optional[str] = None
    document_b_filename: str
    document_b_value: float
    document_b_unit: str
    evidence_b: Optional[ConflictEvidenceResponse] = None
    discrepancy_percentage: float
    status: str
    resolved_by: Optional[int] = None
    resolution_notes: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ConflictListResponse(BaseModel):
    """Bounded conflict-list response used by the Conflict Resolver UI."""

    items: List[ConflictResponse]
    total: int
    skip: int
    limit: int
    has_next: bool


class ConflictRecomputeResponse(BaseModel):
    """Explicit conflict-detector result; list retrieval does not recompute."""

    status: str
    stats: dict


class ConflictResolveRequest(BaseModel):
    resolution_action: str  # 'ACCEPT_DOC_A', 'ACCEPT_DOC_B', 'MANUAL_OVERRIDE'
    override_value: Optional[float] = None
    notes: Optional[str] = None
