from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_path: str
    file_hash: str
    file_type: str
    file_size_bytes: Optional[int] = 0
    subsidiary: Optional[str] = None
    fiscal_year: Optional[str] = None
    status: str
    processing_status: Optional[str] = None
    source_type: Optional[str] = None
    source_url: Optional[str] = None
    source_organization: Optional[str] = None
    title: Optional[str] = None
    reporting_period: Optional[str] = None
    publication_date: Optional[datetime] = None
    extraction_method: Optional[str] = None
    extraction_confidence: Optional[float] = None
    metadata_json: Optional[dict] = None
    processing_warnings: Optional[list] = None
    document_version: Optional[int] = 1
    source_document_id: Optional[int] = None
    total_pages: Optional[int] = 0
    uploaded_by: Optional[int] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    total: int
    items: List[DocumentResponse]


class DocumentPageItem(BaseModel):
    page_number: int
    text_snippet: str
    extraction_method: Optional[str] = None
    confidence: Optional[float] = None
    classification: Optional[str] = None
    blocks: Optional[list] = None


class DocumentPagesResponse(BaseModel):
    document_id: int
    filename: str
    total_pages: int
    pages: List[DocumentPageItem]


class DocumentDeleteResponse(BaseModel):
    message: str
    document_id: int
    filename: str


class DocumentTableResponse(BaseModel):
    id: int
    document_id: int
    page_number: int
    table_number: int
    title: Optional[str] = None
    headers: list = []
    rows: list = []
    bounding_box: Optional[list] = None
    extraction_confidence: Optional[float] = None
    extraction_method: Optional[str] = None
    sheet_name: Optional[str] = None
    cells: list = []
    merged_cells: list = []
    formulas: dict = {}
    displayed_values: dict = {}
    warnings: list = []
