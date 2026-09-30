"""Common, format-neutral document representation used by Step 1 ingestion.

The parser adapters intentionally return these small dataclasses instead of
format-specific objects.  Database persistence is handled separately by the
processing pipeline, so callers can test parsing without a database.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EvidenceBlock:
    text: str
    bbox: Optional[List[float]] = None
    confidence: Optional[float] = None
    method: str = "NATIVE"
    block_type: str = "TEXT"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PageResult:
    page_number: int
    text: str = ""
    extraction_method: str = "NATIVE"
    confidence: Optional[float] = None
    classification: str = "DIGITAL"
    blocks: List[EvidenceBlock] = field(default_factory=list)
    width: Optional[float] = None
    height: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TableResult:
    page_number: int
    table_number: int
    title: Optional[str] = None
    headers: List[Any] = field(default_factory=list)
    rows: List[List[Any]] = field(default_factory=list)
    bounding_box: Optional[List[float]] = None
    extraction_confidence: Optional[float] = None
    extraction_method: str = "NATIVE"
    sheet_name: Optional[str] = None
    cells: List[Dict[str, Any]] = field(default_factory=list)
    merged_cells: List[str] = field(default_factory=list)
    formulas: Dict[str, Any] = field(default_factory=dict)
    displayed_values: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ImageResult:
    image_number: int
    page_number: Optional[int] = None
    source: str = "embedded"
    mime_type: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    text: str = ""
    bounding_box: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    ocr_confidence: Optional[float] = None


@dataclass
class DocumentResult:
    document_id: Optional[int]
    filename: str
    file_type: str
    source_type: str = "MANUAL"
    source_url: Optional[str] = None
    source_organization: Optional[str] = None
    title: Optional[str] = None
    reporting_period: Optional[str] = None
    publication_date: Optional[str] = None
    checksum: Optional[str] = None
    pages: List[PageResult] = field(default_factory=list)
    tables: List[TableResult] = field(default_factory=list)
    images: List[ImageResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    extraction_method: str = "NATIVE"
    extraction_confidence: Optional[float] = None
    processing_status: str = "DISCOVERED"
    warnings: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def page_to_legacy_dict(page: PageResult, tables: List[TableResult]) -> Dict[str, Any]:
    """Preserve the old parser contract for downstream callers during migration."""
    page_tables = [
        {
            "table_index": t.table_number,
            "bbox": t.bounding_box or [],
            "row_count": len(t.rows),
            "col_count": max((len(row) for row in t.rows), default=0),
            # The legacy normalization adapter expects the header row to be
            # part of raw_rows.  The common model keeps headers separately,
            # so reconstruct the lossless row sequence at this boundary.
            "raw_rows": ([t.headers] if t.headers else []) + t.rows,
            "header_names": t.headers,
            "title": t.title,
            "extraction_confidence": t.extraction_confidence,
            "extraction_method": t.extraction_method,
            "warnings": t.warnings,
            "sheet_name": t.sheet_name,
        }
        for t in tables
        if t.page_number == page.page_number
    ]
    return {
        "page_number": page.page_number,
        "text": page.text,
        "is_ocr": page.extraction_method in {"OCR", "NATIVE+OCR"} or bool(page.metadata.get("ocr_engine")),
        "extraction_method": page.extraction_method,
        "confidence": page.confidence,
        "classification": page.classification,
        "blocks": [asdict(block) for block in page.blocks],
        "tables": page_tables,
        "metadata": page.metadata,
    }
