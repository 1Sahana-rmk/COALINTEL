from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ReportGenerateRequest(BaseModel):
    report_type: str  # 'PARLIAMENTARY_REPLY', 'ANNUAL_SUMMARY', 'SUBSIDIARY_COMPARISON', 'PRODUCTION_AUDIT'
    fiscal_year: Optional[str] = "2023-24"
    subsidiary: Optional[str] = "ECL"
    title: Optional[str] = None


class ReportResponse(BaseModel):
    id: int
    title: str
    report_type: str
    subsidiary: Optional[str] = None
    fiscal_year: Optional[str] = None
    file_path: str
    approval_status: str
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
