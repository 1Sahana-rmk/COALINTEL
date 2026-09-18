import os
import re
import hashlib
import logging
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from config import settings
from app.models.document import Document
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

# Constants
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB Limit
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".csv"}


def sanitize_filename(filename: str) -> str:
    """
    Sanitizes user-provided filename to prevent path traversal attacks.
    Strips directory components (../, ..\\, etc.) and retains standard characters.
    """
    if not filename:
        return "unnamed_document.pdf"
    
    # Strip any directory path components
    basename = os.path.basename(filename).replace("\\", "/").split("/")[-1]
    
    # Remove path traversal characters and unsafe symbols
    clean = re.sub(r"[^\w\.\-]", "_", basename)
    
    # Ensure non-empty filename
    if not clean or clean.startswith("."):
        clean = f"document_{clean}"
    
    return clean[:200]  # Limit length


def validate_file_upload(filename: str, file_size: int) -> str:
    """
    Enforces maximum file size limit (50MB) and file extension whitelist.
    Returns normalized uppercase file type ('PDF', 'DOCX', 'XLSX', 'CSV').
    Raises HTTP 400 Bad Request on validation failure.
    """
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size ({file_size / (1024*1024):.2f} MB) exceeds maximum allowed limit of 50 MB."
        )

    _, ext = os.path.splitext(filename)
    ext_lower = ext.lower()

    if ext_lower not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{ext}' is not supported. Supported extensions: {sorted(list(ALLOWED_EXTENSIONS))}"
        )

    return ext_lower[1:].upper()


def calculate_sha256(file_bytes: bytes) -> str:
    """Calculates standard SHA-256 hex digest of file contents."""
    return hashlib.sha256(file_bytes).hexdigest()


def process_file_ingestion(
    db: Session,
    file_bytes: bytes,
    original_filename: str,
    user_id: int,
    subsidiary: Optional[str] = None,
    fiscal_year: Optional[str] = None
) -> Document:
    """
    Executes secure document ingestion:
    1. Sanitizes filename and validates file size / extension.
    2. Computes SHA-256 digest and checks for duplicate ingestion.
    3. Flushes Document DB record to allocate unique document_id.
    4. Persists binary via StorageProvider (Local or Supabase).
    5. Updates Document.file_path with canonical storage reference.
    6. Writes audit log entry and commits transaction.
    7. Ensures transactional consistency (compensating deletion if DB commit fails).
    """
    sanitized_name = sanitize_filename(original_filename)
    file_size = len(file_bytes)
    file_type = validate_file_upload(sanitized_name, file_size)
    file_hash = calculate_sha256(file_bytes)

    # 1. Check for duplicate SHA-256 digest in database
    existing_doc = db.query(Document).filter(Document.file_hash == file_hash).first()
    if existing_doc:
        logger.warning(f"Duplicate document upload blocked for SHA-256: {file_hash}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Duplicate document detected. Document '{existing_doc.filename}' with identical content (SHA-256: {file_hash[:16]}...) already exists in database (ID #{existing_doc.id})."
        )

    content_type_map = {
        "PDF": "application/pdf",
        "DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "XLSX": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "CSV": "text/csv",
    }
    content_type = content_type_map.get(file_type, "application/octet-stream")

    from app.services.storage_service import save_document_binary, delete_document_binary

    target_storage_ref = None

    try:
        # 2. Create initial Document record in transaction to allocate document_id
        new_doc = Document(
            filename=sanitized_name,
            file_path="",
            file_hash=file_hash,
            file_type=file_type,
            file_size_bytes=file_size,
            subsidiary=subsidiary,
            fiscal_year=fiscal_year,
            status="PENDING",
            uploaded_by=user_id
        )
        db.add(new_doc)
        db.flush()  # Allocates new_doc.id

        # 3. Persist file bytes via storage provider abstraction
        target_storage_ref = save_document_binary(
            file_bytes=file_bytes,
            document_id=new_doc.id,
            filename=sanitized_name,
            file_hash=file_hash,
            content_type=content_type
        )
        new_doc.file_path = target_storage_ref

        # 4. Insert Audit Log
        audit_entry = AuditLog(
            user_id=user_id,
            action="DOCUMENT_UPLOAD",
            resource_type="Document",
            resource_id=new_doc.id,
            details=f"Uploaded file '{sanitized_name}' ({file_type}, {file_size} bytes, SHA-256: {file_hash[:12]}...)",
            details_json={
                "filename": sanitized_name,
                "file_hash": file_hash,
                "file_size": file_size,
                "storage_ref": target_storage_ref,
                "subsidiary": subsidiary,
                "fiscal_year": fiscal_year
            }
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(new_doc)

        logger.info(f"Document ID #{new_doc.id} successfully created and committed with storage ref '{target_storage_ref}'.")
        return new_doc

    except HTTPException:
        db.rollback()
        if target_storage_ref:
            try:
                delete_document_binary(target_storage_ref)
            except Exception as clean_err:
                logger.warning(f"Compensating storage cleanup note for '{target_storage_ref}': {clean_err}")
        raise

    except Exception as e:
        db.rollback()
        if target_storage_ref:
            try:
                delete_document_binary(target_storage_ref)
            except Exception as clean_err:
                logger.warning(f"Compensating storage cleanup note for '{target_storage_ref}': {clean_err}")
        logger.error(f"Error during document ingestion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist document to storage or database."
        )
