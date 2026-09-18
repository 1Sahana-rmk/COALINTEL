from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ValidationItemResponse(BaseModel):
    id: int
    mine_name: str
    subsidiary: str
    metric_name: str
    fiscal_year: str
    reported_value: float
    calculated_value: Optional[float] = None
    standard_unit: str
    percentage_difference: float
    validation_status: str
    message: str
    document_id: int
    filename: str

    model_config = ConfigDict(from_attributes=True)


class ConflictResponse(BaseModel):
    id: int
    mine_name: str
    subsidiary: str
    metric_name: str
    fiscal_year: str
    document_a_id: int
    document_a_filename: str
    document_a_value: float
    document_a_unit: str
    document_b_id: int
    document_b_filename: str
    document_b_value: float
    document_b_unit: str
    discrepancy_percentage: float
    status: str
    resolved_by: Optional[int] = None
    resolution_notes: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ConflictResolveRequest(BaseModel):
    resolution_action: str  # 'ACCEPT_DOC_A', 'ACCEPT_DOC_B', 'MANUAL_OVERRIDE'
    override_value: Optional[float] = None
    notes: Optional[str] = None
