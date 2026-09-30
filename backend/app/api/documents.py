import mimetypes
import os
from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database import get_db
from app.models.user import User
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.extracted_metric import ExtractedMetric
from app.models.document_artifacts import DocumentPage, DocumentTable
from app.models.structured_fact import StructuredFact
from app.models.data_conflict import DataConflict
from app.core.rbac import ADMIN_ONLY_ROLES, INGESTION_ROLES, get_current_user, require_roles
from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    DocumentPagesResponse,
    DocumentPageItem,
    DocumentDeleteResponse,
)
from app.models.audit_log import AuditLog
from app.services.storage_service import (
    StorageError,
    StorageNotFoundError,
    delete_uploaded_file,
    delete_document_binary,
    parse_storage_reference,
    read_document_binary,
)
from config import settings
from app.services.vector_store_service import delete_document_vectors
from app.services.ingestion_service import process_file_ingestion
from app.services.processing_pipeline import execute_document_processing_pipeline

router = APIRouter(tags=["Documents"])


def run_background_document_processing(document_id: int) -> None:
    """Executes document processing in background with an isolated database session."""
    import logging
    from database import SessionLocal
    bg_db = SessionLocal()
    try:
        execute_document_processing_pipeline(bg_db, document_id)
    except Exception as e:
        logging.getLogger(__name__).error(f"Background processing task failed for Document #{document_id}: {e}")
    finally:
        bg_db.close()


@router.post("/documents/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    subsidiary: Optional[str] = Form(None),
    fiscal_year: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(INGESTION_ROLES))
):
    """
    Ingests a raw document file (.pdf, .docx, .xlsx, .csv, or image up to 50MB).
    - Enforces max size limit (50MB) and extension whitelist.
    - Computes SHA-256 digest and blocks duplicate uploads with HTTP 409 Conflict.
    - Saves file safely via storage abstraction.
    - Inserts document record with status 'PENDING' and logs audit event.
    - Dispatches Document Processing Pipeline (parsing, chunking, extraction, vector indexing)
      asynchronously via BackgroundTasks, returning HTTP 201 immediately.
    """
    file_bytes = await file.read()
    
    doc = process_file_ingestion(
        db=db,
        file_bytes=file_bytes,
        original_filename=file.filename or "uploaded_file.pdf",
        user_id=current_user.id,
        subsidiary=subsidiary,
        fiscal_year=fiscal_year
    )

    # Schedule background processing decoupled from HTTP request lifecycle
    background_tasks.add_task(run_background_document_processing, doc.id)
    
    return DocumentResponse.model_validate(doc)


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(
    status_filter: Optional[str] = None,
    subsidiary_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves paginated list of uploaded documents with status and subsidiary filter options.
    Pure read operation with zero side-effects or mutations.
    """
    query = db.query(Document)
    
    if status_filter and status_filter.upper() != "ALL":
        query = query.filter(Document.status == status_filter.upper())
    if subsidiary_filter and subsidiary_filter.upper() not in ["ALL", "ALL CIL"]:
        query = query.filter(Document.subsidiary == subsidiary_filter)
        
    total = query.count()
    items = query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()
    
    return DocumentListResponse(
        total=total,
        items=[DocumentResponse.model_validate(d) for d in items]
    )


@router.get("/documents/{id}", response_model=DocumentResponse)
def get_document_by_id(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves document metadata by ID."""
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID #{id} not found."
        )
    return DocumentResponse.model_validate(doc)


@router.get("/documents/{id}/source")
def download_document_source(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the exact persisted source bytes for an authorized reader.

    This endpoint never accepts a client-supplied path.  It resolves only the
    storage reference already persisted on the document and, for local legacy
    references, requires the resolved file to remain inside the configured
    upload directory.
    """
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID #{id} not found.",
        )
    if not doc.file_path or not doc.file_path.strip():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original source file is no longer available.",
        )

    ref_type, _bucket, _path = parse_storage_reference(doc.file_path)
    if ref_type == "local":
        upload_root = os.path.abspath(settings.UPLOAD_DIR)
        candidate = os.path.abspath(doc.file_path)
        try:
            inside_uploads = os.path.commonpath([upload_root, candidate]) == upload_root
        except ValueError:
            inside_uploads = False
        if not inside_uploads:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Original source file is not available in document storage.",
            )

    try:
        source_bytes = read_document_binary(doc.file_path)
    except (StorageNotFoundError, FileNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original source file is no longer available.",
        )
    except StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original source file is not available.",
        ) from exc

    media_type = {
        "PDF": "application/pdf",
        "DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "XLSX": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "CSV": "text/csv",
    }.get((doc.file_type or "").upper()) or mimetypes.guess_type(doc.filename or "")[0] or "application/octet-stream"
    safe_filename = os.path.basename(doc.filename or "source-document")
    safe_filename = safe_filename.replace("\r", "").replace("\n", "") or "source-document"
    from urllib.parse import quote
    disposition = f"attachment; filename*=UTF-8''{quote(safe_filename)}"
    return Response(
        content=source_bytes,
        media_type=media_type,
        headers={"Content-Disposition": disposition},
    )


@router.get("/documents/{id}/pages", response_model=DocumentPagesResponse)
def get_document_pages(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves document page breakdown and extracted text snippets for document page viewer.
    """
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID #{id} not found."
        )
        
    stored_pages = db.query(DocumentPage).filter(DocumentPage.document_id == id).order_by(DocumentPage.page_number).all()
    if stored_pages:
        pages = [DocumentPageItem(page_number=page.page_number, text_snippet=page.text, extraction_method=page.extraction_method, confidence=page.extraction_confidence, classification=page.classification, blocks=page.blocks_json or []) for page in stored_pages]
        return DocumentPagesResponse(document_id=doc.id, filename=doc.filename, total_pages=doc.total_pages or len(pages), pages=pages)

    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == id).order_by(DocumentChunk.page_number, DocumentChunk.chunk_index).all()
    
    # Group text snippets per page
    page_map = {}
    for chunk in chunks:
        pg = chunk.page_number
        if pg not in page_map:
            page_map[pg] = []
        page_map[pg].append(chunk.chunk_text)
        
    pages = [
        DocumentPageItem(page_number=pg, text_snippet="\n\n".join(snippets))
        for pg, snippets in sorted(page_map.items())
    ]
    
    return DocumentPagesResponse(
        document_id=doc.id,
        filename=doc.filename,
        total_pages=doc.total_pages or len(pages),
        pages=pages
    )


@router.get("/documents/{id}/tables")
def get_document_tables(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns generic tables with page/sheet/cell provenance."""
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document with ID #{id} not found.")
    tables = db.query(DocumentTable).filter(DocumentTable.document_id == id).order_by(DocumentTable.page_number, DocumentTable.table_number).all()
    return {
        "document_id": doc.id,
        "filename": doc.filename,
        "tables": [{
            "id": table.id, "document_id": table.document_id, "page_number": table.page_number,
            "table_number": table.table_number, "title": table.title, "headers": table.headers_json or [],
            "rows": table.rows_json or [], "bounding_box": table.bounding_box_json,
            "extraction_confidence": table.extraction_confidence, "extraction_method": table.extraction_method,
            "sheet_name": table.sheet_name, "cells": table.cells_json or [],
            "merged_cells": table.merged_cells_json or [], "formulas": table.formulas_json or {},
            "displayed_values": table.displayed_values_json or {}, "warnings": table.warnings_json or [],
        } for table in tables]
    }


@router.get("/documents/{id}/warnings")
def get_document_warnings(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document with ID #{id} not found.")
    return {"document_id": doc.id, "processing_status": doc.processing_status, "warnings": doc.processing_warnings or [], "error": doc.error_message}


@router.get("/documents/{id}/structured-facts")
def get_document_structured_facts(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return Step 2C facts with their persisted evidence locators.

    This is an additive read surface.  It intentionally does not replace the
    legacy ``/lineage`` response, because existing dashboards and validation
    consumers still depend on ``extracted_metrics``.
    """
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document with ID #{id} not found.")
    facts = (
        db.query(StructuredFact)
        .filter(StructuredFact.document_id == id)
        .order_by(StructuredFact.page_number, StructuredFact.id)
        .all()
    )

    def decimal_value(value):
        return float(value) if value is not None else None

    return {
        "document_id": doc.id,
        "filename": doc.filename,
        "count": len(facts),
        "facts": [
            {
                "fact_id": fact.id,
                "document_id": fact.document_id,
                "document_page_id": fact.document_page_id,
                "page_number": fact.page_number,
                "document_table_id": fact.document_table_id,
                "source_metric_id": fact.source_metric_id,
                "entity_type": fact.entity_type,
                "entity_id": fact.entity_id,
                "entity_name_raw": fact.entity_name_raw,
                "entity_name_canonical": fact.entity_name_canonical,
                "entity_resolution_method": fact.entity_resolution_method,
                "entity_resolution_confidence": decimal_value(fact.entity_resolution_confidence),
                "metric_type": fact.metric_type,
                "metric_name_raw": fact.metric_name_raw,
                "metric_name_canonical": fact.metric_name_canonical,
                "metric_resolution_method": fact.metric_resolution_method,
                "metric_resolution_confidence": decimal_value(fact.metric_resolution_confidence),
                "raw_value_text": fact.raw_value_text,
                "raw_value_numeric": decimal_value(fact.raw_value_numeric),
                "normalized_value": decimal_value(fact.normalized_value),
                "raw_unit": fact.raw_unit,
                "normalized_unit": fact.normalized_unit,
                "period_raw": fact.period_raw,
                "period_normalized": fact.period_normalized,
                "period_type": fact.period_type,
                "qualifiers": fact.qualifiers_json or {},
                "extraction_method": fact.extraction_method,
                "extraction_confidence": decimal_value(fact.extraction_confidence),
                "evidence_type": fact.evidence_type,
                "evidence_locator": fact.evidence_locator_json or {},
                "validation_status": fact.validation_status,
                "validation_warnings": fact.validation_warnings_json or [],
                "fact_status": fact.fact_status,
                "fact_key": fact.fact_key,
                "duplicate_group_key": fact.duplicate_group_key,
            }
            for fact in facts
        ],
    }


@router.get("/documents/{id}/history")
def get_document_history(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Returns persisted audit events for an ingestion without exposing storage paths."""
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document with ID #{id} not found.")
    events = db.query(AuditLog).filter(AuditLog.resource_type == "Document", AuditLog.resource_id == id).order_by(AuditLog.timestamp.asc()).all()
    return {"document_id": id, "events": [{"action": event.action, "details": event.details, "details_json": event.details_json, "created_at": event.timestamp} for event in events]}


@router.get("/documents/{id}/lineage")
def get_document_lineage(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves document metric lineage and normalization traceability."""
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID #{id} not found."
        )
        
    metrics = db.query(ExtractedMetric).filter(ExtractedMetric.document_id == id).order_by(ExtractedMetric.id).all()
    return {
        "document_id": doc.id,
        "filename": doc.filename,
        "subsidiary": doc.subsidiary,
        "fiscal_year": doc.fiscal_year,
        "file_hash": doc.file_hash,
        "metrics": [
            {
                "id": m.id,
                "page_number": m.page_number,
                "mine_name": m.mine_name,
                "metric_name": m.metric_name,
                "numeric_value": float(m.numeric_value) if m.numeric_value is not None else 0.0,
                "unit": m.unit,
                "standard_value": float(m.standard_value) if m.standard_value is not None else 0.0,
                "standard_unit": m.standard_unit or "MT",
                "fiscal_year": m.fiscal_year,
                "confidence_score": (
                    float(m.confidence_score)
                    if m.confidence_score is not None
                    else 0.95
                ),
                "validation_status": m.validation_status or "VALIDATED",
                "raw_snippet": m.raw_snippet or ""
            }
            for m in metrics
        ]
    }


@router.delete(
    "/documents/{id}",
    response_model=DocumentDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Deletes a document and its entire ingestion footprint (Admin only)"
)
def delete_document(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(ADMIN_ONLY_ROLES))
):
    """
    Permanently deletes a document and cleans its entire ingestion footprint:
    1. Requires Admin authentication (Analyst / Reviewer receive HTTP 403 Forbidden).
    2. Validates document existence (returns HTTP 404 Not Found if missing).
    3. Cleans ChromaDB vector embeddings via delete_document_vectors(id).
    4. Removes stored source file from storage via delete_uploaded_file(file_path).
    5. Disassociates conflict records referencing this document (preserves conflict history).
    6. Transactionally deletes all document-owned DB records (DocumentChunk, ExtractedMetric, Document).
    7. Records an immutable audit event (DOCUMENT_DELETED).
    """
    import logging
    logger = logging.getLogger(__name__)

    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID #{id} not found."
        )

    # 1. Capture metadata before DB deletion
    doc_id = doc.id
    doc_filename = doc.filename
    doc_file_path = doc.file_path
    doc_file_hash = doc.file_hash
    doc_subsidiary = doc.subsidiary
    doc_fiscal_year = doc.fiscal_year

    # 2. Delete ChromaDB vector embeddings
    try:
        delete_document_vectors(doc_id)
    except Exception as vec_err:
        logger.warning(f"Vector cleanup note for Document #{doc_id}: {vec_err}")

    # 3. Delete physical source file from storage abstraction (idempotent)
    try:
        delete_document_binary(doc_file_path)
    except Exception as file_err:
        logger.warning(f"Storage file cleanup note for Document #{doc_id} ('{doc_file_path}'): {file_err}")

    # 4. Transactional PostgreSQL Cleanup
    try:
        # Disassociate conflict records referencing this document to preserve conflict history and avoid FK violation
        db.query(DataConflict).filter(DataConflict.doc_a_id == doc_id).update(
            {DataConflict.doc_a_id: None}, synchronize_session=False
        )
        db.query(DataConflict).filter(DataConflict.doc_b_id == doc_id).update(
            {DataConflict.doc_b_id: None}, synchronize_session=False
        )

        # Delete document chunks and extracted metrics owned by this document
        db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).delete(synchronize_session=False)
        db.query(ExtractedMetric).filter(ExtractedMetric.document_id == doc_id).delete(synchronize_session=False)
        db.delete(doc)
        db.flush()

        # 5. Insert Audit Log
        audit_entry = AuditLog(
            user_id=current_user.id,
            action="DOCUMENT_DELETED",
            resource_type="Document",
            resource_id=doc_id,
            details=f"Deleted document #{doc_id} '{doc_filename}' (SHA-256: {doc_file_hash[:12]}...)",
            details_json={
                "document_id": doc_id,
                "filename": doc_filename,
                "file_hash": doc_file_hash,
                "subsidiary": doc_subsidiary,
                "fiscal_year": doc_fiscal_year,
                "deleted_by": current_user.username
            }
        )
        db.add(audit_entry)
        db.commit()
        logger.info(f"Document #{doc_id} ('{doc_filename}') and complete ingestion footprint deleted successfully by Admin '{current_user.username}'.")
    except Exception as db_err:
        db.rollback()
        logger.error(f"Database error while deleting Document #{doc_id}: {db_err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document from database."
        )

    return DocumentDeleteResponse(
        message=f"Document #{doc_id} ('{doc_filename}') and all associated vectors, metrics, chunks, and storage files successfully deleted.",
        document_id=doc_id,
        filename=doc_filename
    )
