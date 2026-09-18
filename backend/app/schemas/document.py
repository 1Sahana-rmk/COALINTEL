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


class DocumentPagesResponse(BaseModel):
    document_id: int
    filename: str
    total_pages: int
    pages: List[DocumentPageItem]


class DocumentDeleteResponse(BaseModel):
    message: str
    document_id: int
    filename: str

