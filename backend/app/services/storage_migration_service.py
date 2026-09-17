import os
import hashlib
import logging
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from config import settings
from app.models.document import Document
from app.models.report import Report
from app.models.audit_log import AuditLog
from app.services.storage_service import (
    StorageError,
    StorageNotFoundError,
    StorageAuthenticationError,
    StoragePermissionError,
    StorageConnectionError,
    parse_storage_reference,
    sanitize_storage_path,
    validate_bucket_name,
    SupabaseStorageProvider,
    get_storage_provider,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# Status Enums & Result Dataclasses
# ==============================================================================

class MigrationStatus(str, Enum):
    MIGRATED = "MIGRATED"
    ALREADY_MIGRATED = "ALREADY_MIGRATED"
    DRY_RUN_ELIGIBLE = "DRY_RUN_ELIGIBLE"
    MISSING_SOURCE_BINARY = "MISSING_SOURCE_BINARY"
    INTEGRITY_HASH_MISMATCH = "INTEGRITY_HASH_MISMATCH"
    UPLOAD_FAILED = "UPLOAD_FAILED"
    DB_COMMIT_FAILED = "DB_COMMIT_FAILED"
    NOT_FOUND = "NOT_FOUND"
    ERROR = "ERROR"


class ReconciliationStatus(str, Enum):
    HEALTHY_LOCAL = "HEALTHY_LOCAL"
    HEALTHY_SUPABASE = "HEALTHY_SUPABASE"
    MISSING_LOCAL_BINARY = "MISSING_LOCAL_BINARY"
    MISSING_SUPABASE_OBJECT = "MISSING_SUPABASE_OBJECT"
    INVALID_REFERENCE = "INVALID_REFERENCE"
    INTEGRITY_MISMATCH = "INTEGRITY_MISMATCH"
    NOT_FOUND = "NOT_FOUND"
    ERROR = "ERROR"


@dataclass
class MigrationResult:
    resource_type: str  # "Document" or "Report"
    resource_id: int
    status: MigrationStatus
    old_file_path: Optional[str] = None
    new_file_path: Optional[str] = None
    file_hash: Optional[str] = None
    file_size_bytes: int = 0
    message: str = ""
    error_details: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "status": self.status.value,
            "old_file_path": self.old_file_path,
            "new_file_path": self.new_file_path,
            "file_hash": self.file_hash,
            "file_size_bytes": self.file_size_bytes,
            "message": self.message,
            "error_details": self.error_details,
        }


@dataclass
class ReconciliationResult:
    resource_type: str  # "Document" or "Report"
    resource_id: int
    status: ReconciliationStatus
    file_path: Optional[str] = None
    provider_type: Optional[str] = None
    bucket: Optional[str] = None
    object_path: Optional[str] = None
    exists_in_storage: bool = False
    file_size_bytes: int = 0
    file_hash: Optional[str] = None
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "status": self.status.value,
            "file_path": self.file_path,
            "provider_type": self.provider_type,
            "bucket": self.bucket,
            "object_path": self.object_path,
            "exists_in_storage": self.exists_in_storage,
            "file_size_bytes": self.file_size_bytes,
            "file_hash": self.file_hash,
            "message": self.message,
        }


@dataclass
class BatchMigrationSummary:
    resource_type: str
    total_inspected: int = 0
    migrated: int = 0
    already_migrated: int = 0
    dry_run_eligible: int = 0
    missing_source: int = 0
    integrity_mismatch: int = 0
    failed: int = 0
    results: List[MigrationResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource_type": self.resource_type,
            "total_inspected": self.total_inspected,
            "migrated": self.migrated,
            "already_migrated": self.already_migrated,
            "dry_run_eligible": self.dry_run_eligible,
            "missing_source": self.missing_source,
            "integrity_mismatch": self.integrity_mismatch,
            "failed": self.failed,
            "results": [r.to_dict() for r in self.results],
        }


@dataclass
class BatchReconciliationSummary:
    total_inspected: int = 0
    healthy_local: int = 0
    healthy_supabase: int = 0
    missing_local: int = 0
    missing_supabase: int = 0
    invalid_reference: int = 0
    integrity_mismatch: int = 0
    errors: int = 0
    results: List[ReconciliationResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_inspected": self.total_inspected,
            "healthy_local": self.healthy_local,
            "healthy_supabase": self.healthy_supabase,
            "missing_local": self.missing_local,
            "missing_supabase": self.missing_supabase,
            "invalid_reference": self.invalid_reference,
            "integrity_mismatch": self.integrity_mismatch,
            "errors": self.errors,
            "results": [r.to_dict() for r in self.results],
        }


# ==============================================================================
# Helper Functions
# ==============================================================================

def _get_supabase_provider(explicit_provider: Optional[SupabaseStorageProvider] = None) -> SupabaseStorageProvider:
    """Returns an instantiated SupabaseStorageProvider using explicit injection or settings."""
    if explicit_provider is not None:
        return explicit_provider
    provider = get_storage_provider("supabase")
    if not isinstance(provider, SupabaseStorageProvider):
        raise StorageAuthenticationError("Failed to obtain SupabaseStorageProvider instance.")
    return provider


def _calculate_sha256(data: bytes) -> str:
    """Computes hexadecimal SHA-256 digest of bytes."""
    return hashlib.sha256(data).hexdigest()


# ==============================================================================
# Document Migration Logic
# ==============================================================================

def migrate_document(
    db: Session,
    document_id: int,
    dry_run: bool = False,
    provider: Optional[SupabaseStorageProvider] = None,
    user_id: Optional[int] = None
) -> MigrationResult:
    """
    Safely migrates a single document binary from local storage to Supabase Storage.
    Non-destructive: original local file is NEVER deleted.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        return MigrationResult(
            resource_type="Document",
            resource_id=document_id,
            status=MigrationStatus.NOT_FOUND,
            message=f"Document ID #{document_id} not found in database."
        )

    ref_type, bucket, path = parse_storage_reference(doc.file_path)

    # 1. Check if already migrated to Supabase
    if ref_type == "supabase":
        supa_provider = _get_supabase_provider(provider)
        obj_exists = False
        try:
            obj_exists = supa_provider.file_exists(bucket=bucket, path=path)
        except Exception as e:
            logger.warning(f"Error checking Supabase object existence for Doc #{doc.id}: {e}")

        if obj_exists:
            return MigrationResult(
                resource_type="Document",
                resource_id=doc.id,
                status=MigrationStatus.ALREADY_MIGRATED,
                old_file_path=doc.file_path,
                new_file_path=doc.file_path,
                file_hash=doc.file_hash,
                file_size_bytes=doc.file_size_bytes or 0,
                message=f"Document #{doc.id} already stored in Supabase Storage ('{doc.file_path}')."
            )
        else:
            return MigrationResult(
                resource_type="Document",
                resource_id=doc.id,
                status=MigrationStatus.MISSING_SOURCE_BINARY,
                old_file_path=doc.file_path,
                new_file_path=None,
                file_hash=doc.file_hash,
                file_size_bytes=doc.file_size_bytes or 0,
                message=f"Document #{doc.id} points to Supabase object '{doc.file_path}' but object is missing in bucket."
            )

    # 2. Inspect local source file
    local_path = os.path.abspath(doc.file_path)
    if not os.path.exists(local_path):
        return MigrationResult(
            resource_type="Document",
            resource_id=doc.id,
            status=MigrationStatus.MISSING_SOURCE_BINARY,
            old_file_path=doc.file_path,
            new_file_path=None,
            file_hash=doc.file_hash,
            file_size_bytes=doc.file_size_bytes or 0,
            message=f"Local source binary not found on disk at '{doc.file_path}'."
        )

    # Read binary bytes
    try:
        with open(local_path, "rb") as f:
            file_bytes = f.read()
    except Exception as read_err:
        return MigrationResult(
            resource_type="Document",
            resource_id=doc.id,
            status=MigrationStatus.ERROR,
            old_file_path=doc.file_path,
            file_hash=doc.file_hash,
            message=f"Failed reading local source file '{doc.file_path}': {read_err}",
            error_details=str(read_err)
        )

    # 3. Hash integrity verification
    calculated_hash = _calculate_sha256(file_bytes)
    if doc.file_hash and calculated_hash.lower() != doc.file_hash.lower():
        logger.error(
            f"Integrity mismatch for Document #{doc.id}: DB hash={doc.file_hash}, Disk hash={calculated_hash}"
        )
        return MigrationResult(
            resource_type="Document",
            resource_id=doc.id,
            status=MigrationStatus.INTEGRITY_HASH_MISMATCH,
            old_file_path=doc.file_path,
            file_hash=doc.file_hash,
            file_size_bytes=len(file_bytes),
            message=(
                f"SHA-256 mismatch for Doc #{doc.id}. Expected: {doc.file_hash}, Calculated: {calculated_hash}. "
                "Migration aborted."
            )
        )

    # 4. Construct canonical Supabase object key
    clean_filename = sanitize_storage_path(doc.filename or os.path.basename(doc.file_path))
    target_bucket = getattr(settings, "SUPABASE_DOCUMENTS_BUCKET", "documents")
    target_object_path = f"{doc.id}/{clean_filename}"
    canonical_key = f"{target_bucket}/{target_object_path}"

    # 5. Handle Dry-Run Mode
    if dry_run:
        return MigrationResult(
            resource_type="Document",
            resource_id=doc.id,
            status=MigrationStatus.DRY_RUN_ELIGIBLE,
            old_file_path=doc.file_path,
            new_file_path=canonical_key,
            file_hash=doc.file_hash,
            file_size_bytes=len(file_bytes),
            message=f"[DRY-RUN] Document #{doc.id} eligible for migration: '{doc.file_path}' -> '{canonical_key}'."
        )

    # 6. Live Upload to Supabase Storage
    supa_provider = _get_supabase_provider(provider)
    content_type = "application/pdf" if doc.file_type == "PDF" else "application/octet-stream"

    uploaded_key = None
    try:
        uploaded_key = supa_provider.save_file(
            bucket=target_bucket,
            path=target_object_path,
            file_bytes=file_bytes,
            content_type=content_type
        )
    except Exception as up_err:
        logger.error(f"Supabase upload failed for Document #{doc.id}: {up_err}")
        return MigrationResult(
            resource_type="Document",
            resource_id=doc.id,
            status=MigrationStatus.UPLOAD_FAILED,
            old_file_path=doc.file_path,
            new_file_path=canonical_key,
            file_hash=doc.file_hash,
            file_size_bytes=len(file_bytes),
            message=f"Supabase storage upload failed: {up_err}",
            error_details=str(up_err)
        )

    # Verify upload existence
    try:
        if not supa_provider.file_exists(bucket=target_bucket, path=target_object_path):
            raise StorageError("Uploaded object verification check returned False.")
    except Exception as verify_err:
        logger.error(f"Upload verification check failed for Document #{doc.id}: {verify_err}")
        # Compensating delete
        try:
            supa_provider.delete_file(bucket=target_bucket, path=target_object_path)
        except Exception as clean_err:
            logger.warning(f"Compensating delete failed for '{target_object_path}': {clean_err}")
        return MigrationResult(
            resource_type="Document",
            resource_id=doc.id,
            status=MigrationStatus.UPLOAD_FAILED,
            old_file_path=doc.file_path,
            new_file_path=canonical_key,
            file_hash=doc.file_hash,
            file_size_bytes=len(file_bytes),
            message=f"Supabase upload verification failed: {verify_err}",
            error_details=str(verify_err)
        )

    # 7. Update Database Reference & Write Audit Log
    old_file_path = doc.file_path
    try:
        doc.file_path = canonical_key
        doc.file_size_bytes = len(file_bytes)

        audit_entry = AuditLog(
            user_id=user_id,
            action="DOCUMENT_STORAGE_MIGRATE",
            resource_type="Document",
            resource_id=doc.id,
            details=f"Migrated document #{doc.id} ('{doc.filename}') from '{old_file_path}' to '{canonical_key}'.",
            details_json={
                "document_id": doc.id,
                "filename": doc.filename,
                "old_file_path": old_file_path,
                "new_file_path": canonical_key,
                "file_hash": doc.file_hash,
                "file_size_bytes": len(file_bytes),
                "migrated_at": datetime.now(timezone.utc).isoformat()
            }
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(doc)
        logger.info(f"Successfully migrated Document #{doc.id} to '{canonical_key}'.")

        return MigrationResult(
            resource_type="Document",
            resource_id=doc.id,
            status=MigrationStatus.MIGRATED,
            old_file_path=old_file_path,
            new_file_path=canonical_key,
            file_hash=doc.file_hash,
            file_size_bytes=len(file_bytes),
            message=f"Document #{doc.id} successfully migrated to '{canonical_key}'."
        )

    except Exception as db_err:
        db.rollback()
        logger.error(f"DB commit failed during Document #{doc.id} migration. Attempting compensation: {db_err}")
        # Compensating delete of uploaded Supabase object
        try:
            supa_provider.delete_file(bucket=target_bucket, path=target_object_path)
            logger.info(f"Compensating delete succeeded for '{canonical_key}'.")
        except Exception as clean_err:
            logger.warning(f"Compensating delete failed for '{canonical_key}': {clean_err}")

        return MigrationResult(
            resource_type="Document",
            resource_id=doc.id,
            status=MigrationStatus.DB_COMMIT_FAILED,
            old_file_path=old_file_path,
            new_file_path=canonical_key,
            file_hash=doc.file_hash,
            file_size_bytes=len(file_bytes),
            message=f"Database update failed after upload; transaction rolled back: {db_err}",
            error_details=str(db_err)
        )


# ==============================================================================
# Report Migration Logic
# ==============================================================================

def migrate_report(
    db: Session,
    report_id: int,
    dry_run: bool = False,
    provider: Optional[SupabaseStorageProvider] = None,
    user_id: Optional[int] = None
) -> MigrationResult:
    """
    Safely migrates a single generated report PDF binary from local storage to Supabase Storage.
    Non-destructive: original local file is NEVER deleted.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        return MigrationResult(
            resource_type="Report",
            resource_id=report_id,
            status=MigrationStatus.NOT_FOUND,
            message=f"Report ID #{report_id} not found in database."
        )

    if not report.file_path or not report.file_path.strip():
        return MigrationResult(
            resource_type="Report",
            resource_id=report.id,
            status=MigrationStatus.MISSING_SOURCE_BINARY,
            old_file_path=None,
            new_file_path=None,
            message=f"Report #{report.id} has empty file_path."
        )

    ref_type, bucket, path = parse_storage_reference(report.file_path)

    # 1. Check if already migrated to Supabase
    if ref_type == "supabase":
        supa_provider = _get_supabase_provider(provider)
        obj_exists = False
        try:
            obj_exists = supa_provider.file_exists(bucket=bucket, path=path)
        except Exception as e:
            logger.warning(f"Error checking Supabase object existence for Report #{report.id}: {e}")

        if obj_exists:
            return MigrationResult(
                resource_type="Report",
                resource_id=report.id,
                status=MigrationStatus.ALREADY_MIGRATED,
                old_file_path=report.file_path,
                new_file_path=report.file_path,
                message=f"Report #{report.id} already stored in Supabase Storage ('{report.file_path}')."
            )
        else:
            return MigrationResult(
                resource_type="Report",
                resource_id=report.id,
                status=MigrationStatus.MISSING_SOURCE_BINARY,
                old_file_path=report.file_path,
                new_file_path=None,
                message=f"Report #{report.id} points to Supabase object '{report.file_path}' but object is missing in bucket."
            )

    # 2. Inspect local source file
    local_path = os.path.abspath(report.file_path)
    if not os.path.exists(local_path):
        return MigrationResult(
            resource_type="Report",
            resource_id=report.id,
            status=MigrationStatus.MISSING_SOURCE_BINARY,
            old_file_path=report.file_path,
            new_file_path=None,
            message=f"Local report PDF file not found on disk at '{report.file_path}'."
        )

    # Read binary bytes
    try:
        with open(local_path, "rb") as f:
            file_bytes = f.read()
    except Exception as read_err:
        return MigrationResult(
            resource_type="Report",
            resource_id=report.id,
            status=MigrationStatus.ERROR,
            old_file_path=report.file_path,
            message=f"Failed reading local report file '{report.file_path}': {read_err}",
            error_details=str(read_err)
        )

    calculated_hash = _calculate_sha256(file_bytes)

    # 3. Construct canonical Supabase object key
    raw_filename = os.path.basename(report.file_path)
    clean_filename = sanitize_storage_path(raw_filename)
    target_bucket = getattr(settings, "SUPABASE_REPORTS_BUCKET", "reports")
    target_object_path = f"{report.id}/{clean_filename}"
    canonical_key = f"{target_bucket}/{target_object_path}"

    # 4. Handle Dry-Run Mode
    if dry_run:
        return MigrationResult(
            resource_type="Report",
            resource_id=report.id,
            status=MigrationStatus.DRY_RUN_ELIGIBLE,
            old_file_path=report.file_path,
            new_file_path=canonical_key,
            file_hash=calculated_hash,
            file_size_bytes=len(file_bytes),
            message=f"[DRY-RUN] Report #{report.id} eligible for migration: '{report.file_path}' -> '{canonical_key}'."
        )

    # 5. Live Upload to Supabase Storage
    supa_provider = _get_supabase_provider(provider)

    try:
        supa_provider.save_file(
            bucket=target_bucket,
            path=target_object_path,
            file_bytes=file_bytes,
            content_type="application/pdf"
        )
    except Exception as up_err:
        logger.error(f"Supabase upload failed for Report #{report.id}: {up_err}")
        return MigrationResult(
            resource_type="Report",
            resource_id=report.id,
            status=MigrationStatus.UPLOAD_FAILED,
            old_file_path=report.file_path,
            new_file_path=canonical_key,
            file_hash=calculated_hash,
            file_size_bytes=len(file_bytes),
            message=f"Supabase storage upload failed: {up_err}",
            error_details=str(up_err)
        )

    # Verify upload existence
    try:
        if not supa_provider.file_exists(bucket=target_bucket, path=target_object_path):
            raise StorageError("Uploaded object verification check returned False.")
    except Exception as verify_err:
        logger.error(f"Upload verification check failed for Report #{report.id}: {verify_err}")
        try:
            supa_provider.delete_file(bucket=target_bucket, path=target_object_path)
        except Exception as clean_err:
            logger.warning(f"Compensating delete failed for '{target_object_path}': {clean_err}")
        return MigrationResult(
            resource_type="Report",
            resource_id=report.id,
            status=MigrationStatus.UPLOAD_FAILED,
            old_file_path=report.file_path,
            new_file_path=canonical_key,
            file_hash=calculated_hash,
            file_size_bytes=len(file_bytes),
            message=f"Supabase upload verification failed: {verify_err}",
            error_details=str(verify_err)
        )

    # 6. Update Database Reference & Write Audit Log
    old_file_path = report.file_path
    try:
        report.file_path = canonical_key

        audit_entry = AuditLog(
            user_id=user_id,
            action="REPORT_STORAGE_MIGRATE",
            resource_type="Report",
            resource_id=report.id,
            details=f"Migrated report #{report.id} ('{report.title}') from '{old_file_path}' to '{canonical_key}'.",
            details_json={
                "report_id": report.id,
                "title": report.title,
                "old_file_path": old_file_path,
                "new_file_path": canonical_key,
                "file_hash": calculated_hash,
                "file_size_bytes": len(file_bytes),
                "migrated_at": datetime.now(timezone.utc).isoformat()
            }
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(report)
        logger.info(f"Successfully migrated Report #{report.id} to '{canonical_key}'.")

        return MigrationResult(
            resource_type="Report",
            resource_id=report.id,
            status=MigrationStatus.MIGRATED,
            old_file_path=old_file_path,
            new_file_path=canonical_key,
            file_hash=calculated_hash,
            file_size_bytes=len(file_bytes),
            message=f"Report #{report.id} successfully migrated to '{canonical_key}'."
        )

    except Exception as db_err:
        db.rollback()
        logger.error(f"DB commit failed during Report #{report.id} migration. Attempting compensation: {db_err}")
        try:
            supa_provider.delete_file(bucket=target_bucket, path=target_object_path)
            logger.info(f"Compensating delete succeeded for '{canonical_key}'.")
        except Exception as clean_err:
            logger.warning(f"Compensating delete failed for '{canonical_key}': {clean_err}")

        return MigrationResult(
            resource_type="Report",
            resource_id=report.id,
            status=MigrationStatus.DB_COMMIT_FAILED,
            old_file_path=old_file_path,
            new_file_path=canonical_key,
            file_hash=calculated_hash,
            file_size_bytes=len(file_bytes),
            message=f"Database update failed after upload; transaction rolled back: {db_err}",
            error_details=str(db_err)
        )


# ==============================================================================
# Batch Migration Operations
# ==============================================================================

def migrate_all_documents(
    db: Session,
    dry_run: bool = False,
    provider: Optional[SupabaseStorageProvider] = None,
    limit: Optional[int] = None,
    subsidiary: Optional[str] = None,
    user_id: Optional[int] = None
) -> BatchMigrationSummary:
    """
    Sequentially iterates through eligible documents and migrates them.
    Continues processing on individual record failure.
    """
    query = db.query(Document)
    if subsidiary and subsidiary != "ALL":
        query = query.filter(Document.subsidiary == subsidiary)
    query = query.order_by(Document.id.asc())
    if limit and limit > 0:
        query = query.limit(limit)

    documents = query.all()
    summary = BatchMigrationSummary(resource_type="Document", total_inspected=len(documents))

    for doc in documents:
        try:
            res = migrate_document(db=db, document_id=doc.id, dry_run=dry_run, provider=provider, user_id=user_id)
            summary.results.append(res)
            if res.status == MigrationStatus.MIGRATED:
                summary.migrated += 1
            elif res.status == MigrationStatus.ALREADY_MIGRATED:
                summary.already_migrated += 1
            elif res.status == MigrationStatus.DRY_RUN_ELIGIBLE:
                summary.dry_run_eligible += 1
            elif res.status == MigrationStatus.MISSING_SOURCE_BINARY:
                summary.missing_source += 1
            elif res.status == MigrationStatus.INTEGRITY_HASH_MISMATCH:
                summary.integrity_mismatch += 1
            else:
                summary.failed += 1
        except Exception as e:
            logger.error(f"Unexpected error migrating Document #{doc.id}: {e}")
            summary.failed += 1
            summary.results.append(MigrationResult(
                resource_type="Document",
                resource_id=doc.id,
                status=MigrationStatus.ERROR,
                old_file_path=doc.file_path,
                message=f"Unexpected error: {e}",
                error_details=str(e)
            ))

    return summary


def migrate_all_reports(
    db: Session,
    dry_run: bool = False,
    provider: Optional[SupabaseStorageProvider] = None,
    limit: Optional[int] = None,
    subsidiary: Optional[str] = None,
    user_id: Optional[int] = None
) -> BatchMigrationSummary:
    """
    Sequentially iterates through eligible reports and migrates them.
    Continues processing on individual record failure.
    """
    query = db.query(Report)
    if subsidiary and subsidiary != "ALL":
        query = query.filter(Report.subsidiary == subsidiary)
    query = query.order_by(Report.id.asc())
    if limit and limit > 0:
        query = query.limit(limit)

    reports = query.all()
    summary = BatchMigrationSummary(resource_type="Report", total_inspected=len(reports))

    for report in reports:
        try:
            res = migrate_report(db=db, report_id=report.id, dry_run=dry_run, provider=provider, user_id=user_id)
            summary.results.append(res)
            if res.status == MigrationStatus.MIGRATED:
                summary.migrated += 1
            elif res.status == MigrationStatus.ALREADY_MIGRATED:
                summary.already_migrated += 1
            elif res.status == MigrationStatus.DRY_RUN_ELIGIBLE:
                summary.dry_run_eligible += 1
            elif res.status == MigrationStatus.MISSING_SOURCE_BINARY:
                summary.missing_source += 1
            elif res.status == MigrationStatus.INTEGRITY_HASH_MISMATCH:
                summary.integrity_mismatch += 1
            else:
                summary.failed += 1
        except Exception as e:
            logger.error(f"Unexpected error migrating Report #{report.id}: {e}")
            summary.failed += 1
            summary.results.append(MigrationResult(
                resource_type="Report",
                resource_id=report.id,
                status=MigrationStatus.ERROR,
                old_file_path=report.file_path,
                message=f"Unexpected error: {e}",
                error_details=str(e)
            ))

    return summary


# ==============================================================================
# Diagnostic Reconciliation Logic
# ==============================================================================

def reconcile_document(
    db: Session,
    document_id: int,
    provider: Optional[SupabaseStorageProvider] = None
) -> ReconciliationResult:
    """
    Non-destructively inspects and verifies a Document's storage reference.
    NEVER deletes database rows or storage objects.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        return ReconciliationResult(
            resource_type="Document",
            resource_id=document_id,
            status=ReconciliationStatus.NOT_FOUND,
            message=f"Document ID #{document_id} not found."
        )

    if not doc.file_path or not doc.file_path.strip():
        return ReconciliationResult(
            resource_type="Document",
            resource_id=doc.id,
            status=ReconciliationStatus.INVALID_REFERENCE,
            file_path=doc.file_path,
            message="Document file_path is empty."
        )

    ref_type, bucket, path = parse_storage_reference(doc.file_path)

    if ref_type == "local":
        abs_path = os.path.abspath(doc.file_path)
        if os.path.exists(abs_path):
            file_size = os.path.getsize(abs_path)
            try:
                with open(abs_path, "rb") as f:
                    data = f.read()
                calc_hash = _calculate_sha256(data)
                if doc.file_hash and calc_hash.lower() != doc.file_hash.lower():
                    return ReconciliationResult(
                        resource_type="Document",
                        resource_id=doc.id,
                        status=ReconciliationStatus.INTEGRITY_MISMATCH,
                        file_path=doc.file_path,
                        provider_type="local",
                        bucket=bucket,
                        object_path=path,
                        exists_in_storage=True,
                        file_size_bytes=file_size,
                        file_hash=calc_hash,
                        message=f"Local binary hash mismatch. DB: {doc.file_hash}, Disk: {calc_hash}."
                    )
                return ReconciliationResult(
                    resource_type="Document",
                    resource_id=doc.id,
                    status=ReconciliationStatus.HEALTHY_LOCAL,
                    file_path=doc.file_path,
                    provider_type="local",
                    bucket=bucket,
                    object_path=path,
                    exists_in_storage=True,
                    file_size_bytes=file_size,
                    file_hash=calc_hash,
                    message="Healthy legacy local file reference."
                )
            except Exception as e:
                return ReconciliationResult(
                    resource_type="Document",
                    resource_id=doc.id,
                    status=ReconciliationStatus.ERROR,
                    file_path=doc.file_path,
                    provider_type="local",
                    bucket=bucket,
                    message=f"Error reading local file: {e}"
                )
        else:
            return ReconciliationResult(
                resource_type="Document",
                resource_id=doc.id,
                status=ReconciliationStatus.MISSING_LOCAL_BINARY,
                file_path=doc.file_path,
                provider_type="local",
                bucket=bucket,
                object_path=path,
                exists_in_storage=False,
                message=f"Local binary file is missing from disk at '{doc.file_path}'."
            )

    elif ref_type == "supabase":
        supa_provider = _get_supabase_provider(provider)
        try:
            exists = supa_provider.file_exists(bucket=bucket, path=path)
            if exists:
                size = supa_provider.get_file_size(bucket=bucket, path=path)
                return ReconciliationResult(
                    resource_type="Document",
                    resource_id=doc.id,
                    status=ReconciliationStatus.HEALTHY_SUPABASE,
                    file_path=doc.file_path,
                    provider_type="supabase",
                    bucket=bucket,
                    object_path=path,
                    exists_in_storage=True,
                    file_size_bytes=size,
                    file_hash=doc.file_hash,
                    message="Healthy persistent Supabase Storage object."
                )
            else:
                return ReconciliationResult(
                    resource_type="Document",
                    resource_id=doc.id,
                    status=ReconciliationStatus.MISSING_SUPABASE_OBJECT,
                    file_path=doc.file_path,
                    provider_type="supabase",
                    bucket=bucket,
                    object_path=path,
                    exists_in_storage=False,
                    file_hash=doc.file_hash,
                    message=f"Supabase object '{path}' is missing in bucket '{bucket}'."
                )
        except Exception as e:
            return ReconciliationResult(
                resource_type="Document",
                resource_id=doc.id,
                status=ReconciliationStatus.ERROR,
                file_path=doc.file_path,
                provider_type="supabase",
                bucket=bucket,
                object_path=path,
                message=f"Error querying Supabase Storage: {e}"
            )

    return ReconciliationResult(
        resource_type="Document",
        resource_id=doc.id,
        status=ReconciliationStatus.INVALID_REFERENCE,
        file_path=doc.file_path,
        message=f"Unrecognized or unsupported storage reference format: '{doc.file_path}'."
    )


def reconcile_report(
    db: Session,
    report_id: int,
    provider: Optional[SupabaseStorageProvider] = None
) -> ReconciliationResult:
    """
    Non-destructively inspects and verifies a Report's storage reference.
    NEVER deletes database rows or storage objects.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        return ReconciliationResult(
            resource_type="Report",
            resource_id=report_id,
            status=ReconciliationStatus.NOT_FOUND,
            message=f"Report ID #{report_id} not found."
        )

    if not report.file_path or not report.file_path.strip():
        return ReconciliationResult(
            resource_type="Report",
            resource_id=report.id,
            status=ReconciliationStatus.INVALID_REFERENCE,
            file_path=report.file_path,
            message="Report file_path is empty."
        )

    ref_type, bucket, path = parse_storage_reference(report.file_path)

    if ref_type == "local":
        abs_path = os.path.abspath(report.file_path)
        if os.path.exists(abs_path):
            file_size = os.path.getsize(abs_path)
            return ReconciliationResult(
                resource_type="Report",
                resource_id=report.id,
                status=ReconciliationStatus.HEALTHY_LOCAL,
                file_path=report.file_path,
                provider_type="local",
                bucket=bucket,
                object_path=path,
                exists_in_storage=True,
                file_size_bytes=file_size,
                message="Healthy legacy local report PDF file."
            )
        else:
            return ReconciliationResult(
                resource_type="Report",
                resource_id=report.id,
                status=ReconciliationStatus.MISSING_LOCAL_BINARY,
                file_path=report.file_path,
                provider_type="local",
                bucket=bucket,
                object_path=path,
                exists_in_storage=False,
                message=f"Local report PDF file is missing from disk at '{report.file_path}'."
            )

    elif ref_type == "supabase":
        supa_provider = _get_supabase_provider(provider)
        try:
            exists = supa_provider.file_exists(bucket=bucket, path=path)
            if exists:
                size = supa_provider.get_file_size(bucket=bucket, path=path)
                return ReconciliationResult(
                    resource_type="Report",
                    resource_id=report.id,
                    status=ReconciliationStatus.HEALTHY_SUPABASE,
                    file_path=report.file_path,
                    provider_type="supabase",
                    bucket=bucket,
                    object_path=path,
                    exists_in_storage=True,
                    file_size_bytes=size,
                    message="Healthy persistent Supabase Storage report PDF."
                )
            else:
                return ReconciliationResult(
                    resource_type="Report",
                    resource_id=report.id,
                    status=ReconciliationStatus.MISSING_SUPABASE_OBJECT,
                    file_path=report.file_path,
                    provider_type="supabase",
                    bucket=bucket,
                    object_path=path,
                    exists_in_storage=False,
                    message=f"Supabase report object '{path}' is missing in bucket '{bucket}'."
                )
        except Exception as e:
            return ReconciliationResult(
                resource_type="Report",
                resource_id=report.id,
                status=ReconciliationStatus.ERROR,
                file_path=report.file_path,
                provider_type="supabase",
                bucket=bucket,
                object_path=path,
                message=f"Error querying Supabase Storage: {e}"
            )

    return ReconciliationResult(
        resource_type="Report",
        resource_id=report.id,
        status=ReconciliationStatus.INVALID_REFERENCE,
        file_path=report.file_path,
        message=f"Unrecognized or unsupported storage reference format: '{report.file_path}'."
    )


def reconcile_all(
    db: Session,
    provider: Optional[SupabaseStorageProvider] = None,
    limit: Optional[int] = None
) -> BatchReconciliationSummary:
    """
    Performs comprehensive diagnostic reconciliation across all Document and Report records.
    """
    doc_query = db.query(Document).order_by(Document.id.asc())
    rep_query = db.query(Report).order_by(Report.id.asc())

    if limit and limit > 0:
        doc_query = doc_query.limit(limit)
        rep_query = rep_query.limit(limit)

    documents = doc_query.all()
    reports = rep_query.all()

    summary = BatchReconciliationSummary(total_inspected=len(documents) + len(reports))

    for doc in documents:
        res = reconcile_document(db=db, document_id=doc.id, provider=provider)
        summary.results.append(res)
        if res.status == ReconciliationStatus.HEALTHY_LOCAL:
            summary.healthy_local += 1
        elif res.status == ReconciliationStatus.HEALTHY_SUPABASE:
            summary.healthy_supabase += 1
        elif res.status == ReconciliationStatus.MISSING_LOCAL_BINARY:
            summary.missing_local += 1
        elif res.status == ReconciliationStatus.MISSING_SUPABASE_OBJECT:
            summary.missing_supabase += 1
        elif res.status == ReconciliationStatus.INTEGRITY_MISMATCH:
            summary.integrity_mismatch += 1
        elif res.status == ReconciliationStatus.INVALID_REFERENCE:
            summary.invalid_reference += 1
        else:
            summary.errors += 1

    for rep in reports:
        res = reconcile_report(db=db, report_id=rep.id, provider=provider)
        summary.results.append(res)
        if res.status == ReconciliationStatus.HEALTHY_LOCAL:
            summary.healthy_local += 1
        elif res.status == ReconciliationStatus.HEALTHY_SUPABASE:
            summary.healthy_supabase += 1
        elif res.status == ReconciliationStatus.MISSING_LOCAL_BINARY:
            summary.missing_local += 1
        elif res.status == ReconciliationStatus.MISSING_SUPABASE_OBJECT:
            summary.missing_supabase += 1
        elif res.status == ReconciliationStatus.INTEGRITY_MISMATCH:
            summary.integrity_mismatch += 1
        elif res.status == ReconciliationStatus.INVALID_REFERENCE:
            summary.invalid_reference += 1
        else:
            summary.errors += 1

    return summary
