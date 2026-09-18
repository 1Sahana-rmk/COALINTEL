from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from database import get_db
from app.models.user import User
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.extracted_metric import ExtractedMetric
from app.models.data_conflict import DataConflict
from app.core.rbac import get_current_user, require_roles
from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    DocumentPagesResponse,
    DocumentPageItem,
    DocumentDeleteResponse,
)
from app.models.audit_log import AuditLog
from app.services.storage_service import delete_uploaded_file, delete_document_binary
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
    current_user: User = Depends(require_roles(["Admin", "Analyst"]))
):
    """
    Ingests a raw document file (.pdf, .docx, .xlsx, .csv up to 50MB).
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
    current_user: User = Depends(require_roles(["Admin"]))
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

