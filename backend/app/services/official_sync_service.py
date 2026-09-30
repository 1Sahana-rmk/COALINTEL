"""Persistent, versioned synchronization for official documents."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.official_source import OfficialDocument, OfficialSource
from app.services.ingestion_service import calculate_sha256, process_file_ingestion, sanitize_filename
from app.services.processing_pipeline import execute_document_processing_pipeline

logger = logging.getLogger(__name__)

SUCCESSFUL_PROCESSING_STATES = {"READY", "REVIEW_RECOMMENDED", "VALIDATION_WARNING"}


def _isoformat_or_none(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def _document_processing_succeeded(db: Session, document_id: Optional[int]) -> bool:
    """Return true only when the common pipeline completed validation."""
    if not document_id:
        return False
    document = db.get(Document, document_id)
    return bool(
        document
        and document.status in {"PARSED", "INDEXED"}
        and document.processing_status in SUCCESSFUL_PROCESSING_STATES
    )


def _process_document(db: Session, document_id: int) -> None:
    """Run and verify the common processing pipeline for an acquired file."""
    if not execute_document_processing_pipeline(db, document_id):
        document = db.get(Document, document_id)
        detail = (document.error_message if document else None) or (document.processing_status if document else "unknown")
        raise RuntimeError(f"Official document processing failed: {detail}")
    db.expire_all()
    if not _document_processing_succeeded(db, document_id):
        document = db.get(Document, document_id)
        detail = (document.error_message if document else None) or (document.processing_status if document else "unknown")
        raise RuntimeError(f"Official document did not reach a validated state: {detail}")


def ensure_ministry_source(db: Session) -> OfficialSource:
    source = db.query(OfficialSource).filter(OfficialSource.base_url == "https://coal.nic.in/major-statistics-page").first()
    if source:
        return source
    source = OfficialSource(name="Ministry of Coal", organization="Ministry of Coal", base_url="https://coal.nic.in/major-statistics-page", source_type="OFFICIAL_WEBSITE", sync_frequency="24h", status="CONNECTED")
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def try_claim_source_sync(db: Session, source_id: int) -> bool:
    """Atomically claim a source for one manual or scheduled sync run."""
    source = db.query(OfficialSource).filter(OfficialSource.id == source_id).with_for_update().first()
    if not source or source.status == "SYNCING":
        db.rollback()
        return False
    source.status = "SYNCING"
    source.last_sync_at = datetime.now(timezone.utc)
    source.last_error = None
    db.commit()
    return True


def recover_interrupted_source_syncs(db: Session) -> int:
    """Surface worker claims orphaned by a backend restart as explicit errors."""
    sources = db.query(OfficialSource).filter(OfficialSource.status == "SYNCING").all()
    for source in sources:
        source.status = "ERROR"
        source.last_error = "Synchronization was interrupted by a backend restart before completion."
    if sources:
        db.commit()
    return len(sources)


def _current_record(db: Session, source_id: int, url: str) -> Optional[OfficialDocument]:
    return db.query(OfficialDocument).filter(
        OfficialDocument.source_id == source_id,
        OfficialDocument.document_url == url,
        OfficialDocument.is_current.is_(True),
    ).order_by(OfficialDocument.version.desc()).first()


def _metadata(connector: Any, item: Any) -> str:
    return json.dumps(connector.extract_source_metadata(item), default=str)


def _failed_record(db: Session, source: OfficialSource, item: Any, current: Optional[OfficialDocument], now: datetime, error: Exception) -> None:
    record = OfficialDocument(
        source_id=source.id, document_url=item.url, title=item.title, category=item.category,
        published_at=item.publication_date, download_status="FAILED", version=(current.version + 1) if current else 1,
        is_current=False, last_seen_at=now, last_error=str(error)[:500], source_metadata=None,
    )
    # Metadata extraction is deliberately optional: a failed URL must remain auditable even if its
    # connector cannot derive metadata for it.
    db.add(record)
    db.commit()


def sync_official_source(
    db: Session,
    source: OfficialSource,
    connector: Any,
    *,
    user_id: Optional[int] = None,
    already_claimed: bool = False,
) -> Dict[str, Any]:
    attempt_started_at = datetime.now(timezone.utc)
    if not already_claimed:
        if not try_claim_source_sync(db, source.id):
            current = db.get(OfficialSource, source.id)
            return {
                "source_id": source.id,
                "status": current.status if current else "SYNCING",
                "already_running": True,
                "last_sync_at": current.last_sync_at if current else attempt_started_at.isoformat(),
            }
        source = db.get(OfficialSource, source.id)
    else:
        source = db.get(OfficialSource, source.id)
        source.status = "SYNCING"
        source.last_error = None
        db.commit()
    counts: Dict[str, Any] = {"discovered": 0, "new": 0, "updated": 0, "unchanged": 0, "duplicates": 0, "failed": 0, "pages_checked": 0, "page_failures": 0}

    try:
        if hasattr(connector, "discover_documents_with_report"):
            discovery = connector.discover_documents_with_report()
            discovered = discovery.documents
            counts["pages_checked"] = discovery.pages_checked
            counts["page_failures"] = len(discovery.page_failures)
        else:
            discovered = connector.discover_documents()
            discovery = None
        counts["discovered"] = len(discovered)
    except Exception as exc:
        db.rollback()
        source = db.get(OfficialSource, source.id)
        source.status = "ERROR"
        source.last_error = str(exc)[:500]
        db.commit()
        return {"source_id": source.id, **counts, "status": source.status, "last_sync_at": _isoformat_or_none(source.last_sync_at), "last_success_at": _isoformat_or_none(source.last_success_at), "error": str(exc)[:500]}

    for item in discovered:
        current = _current_record(db, source.id, item.url)
        try:
            content = connector.download_document(item)
            checksum = calculate_sha256(content)
            if current and current.checksum == checksum:
                current.last_seen_at = attempt_started_at
                # Previous syncs recorded DOWNLOADED/INGESTED before running
                # the parser. Revisit linked documents that never completed
                # validation instead of silently treating them as unchanged.
                if current.document_id and not _document_processing_succeeded(db, current.document_id):
                    try:
                        _process_document(db, current.document_id)
                        current.download_status = "INGESTED"
                        current.last_error = None
                        db.commit()
                        counts["unchanged"] += 1
                    except Exception as exc:
                        db.rollback()
                        current = db.get(OfficialDocument, current.id)
                        current.download_status = "PROCESSING_FAILED"
                        current.last_error = str(exc)[:500]
                        db.commit()
                        counts["failed"] += 1
                else:
                    current.download_status = "UNCHANGED"
                    current.last_error = None
                    db.commit()
                    counts["unchanged"] += 1
                continue

            state = "updated" if current else "new"
            version = (current.version + 1) if current else 1
            existing_doc = db.query(Document).filter(Document.file_hash == checksum).first()
            record = OfficialDocument(
                source_id=source.id, document_url=item.url, title=item.title, category=item.category,
                published_at=item.publication_date, checksum=checksum, download_status="DUPLICATE" if existing_doc else "DOWNLOADED",
                document_id=existing_doc.id if existing_doc else None, version=version, is_current=not bool(existing_doc),
                last_seen_at=attempt_started_at, source_metadata=_metadata(connector, item),
            )
            db.add(record)
            db.commit()  # Registry state survives any later ingestion rollback.
            db.refresh(record)

            if existing_doc:
                if current:
                    current.is_current = False
                    db.commit()
                counts[state] += 1
                counts["duplicates"] += 1
                continue

            candidate_name = item.title if item.title and "." in item.title.rsplit("/", 1)[-1] else item.url.split("?", 1)[0].rsplit("/", 1)[-1]
            try:
                doc = process_file_ingestion(
                    db, content, sanitize_filename(candidate_name), user_id,
                    source_type="OFFICIAL", source_url=item.url, source_organization=source.organization,
                    title=item.title, publication_date=item.publication_date,
                    source_document_id=record.id, document_version=version,
                )
                # Keep the registry-to-document link even when parsing fails;
                # the failed document and its error state remain auditable.
                record.document_id = doc.id if doc else None
                db.commit()
                # Official acquisition and manual upload must converge on the
                # same persisted parser/validation pipeline. A registry row is
                # not considered INGESTED until this completes successfully.
                _process_document(db, doc.id)
            except Exception as exc:
                db.rollback()
                failed = db.get(OfficialDocument, record.id)
                if failed:
                    failed.download_status = "PROCESSING_FAILED"
                    failed.last_error = str(exc)[:500]
                    failed.is_current = False
                    db.commit()
                raise
            record = db.get(OfficialDocument, record.id)
            record.document_id = doc.id if doc else None
            record.download_status = "INGESTED" if doc and _document_processing_succeeded(db, doc.id) else "PROCESSING_FAILED"
            record.is_current = True
            if current:
                old = db.get(OfficialDocument, current.id)
                if old:
                    old.is_current = False
            db.commit()
            counts[state] += 1
        except Exception as exc:
            logger.warning("Official source document failed (%s): %s", item.url, exc)
            db.rollback()
            # A failed download has no registry row yet; retain an explicit failed attempt while
            # keeping the prior successful version current.
            existing_failed = db.query(OfficialDocument).filter(
                OfficialDocument.source_id == source.id,
                OfficialDocument.document_url == item.url,
                OfficialDocument.last_error == str(exc)[:500],
            ).first()
            if not existing_failed:
                try:
                    _failed_record(db, source, item, current, attempt_started_at, exc)
                except Exception:
                    db.rollback()
            counts["failed"] += 1

    source = db.get(OfficialSource, source.id)
    if counts["failed"] or counts["page_failures"]:
        source.status = "PARTIAL"
        errors = []
        if counts["page_failures"]:
            errors.append(f"{counts['page_failures']} category page(s) failed")
        if counts["failed"]:
            errors.append(f"{counts['failed']} document(s) failed")
        source.last_error = "; ".join(errors)
    else:
        source.status = "CONNECTED"
        source.last_error = None
    if source.status == "CONNECTED":
        # last_sync_at is the attempt/claim time. last_success_at is the
        # terminal successful completion time, never the request-acceptance
        # time or the beginning of discovery.
        source.last_success_at = datetime.now(timezone.utc)
    db.commit()
    return {"source_id": source.id, **counts, "status": source.status, "last_sync_at": _isoformat_or_none(source.last_sync_at), "last_success_at": _isoformat_or_none(source.last_success_at)}


def run_due_syncs(db: Session, connector_factory, *, user_id: Optional[int] = None, force: bool = False) -> Dict[str, Any]:
    """Scheduler-friendly entrypoint; default cadence is one run per 24 hours."""
    sources = db.query(OfficialSource).filter(OfficialSource.enabled.is_(True)).all()
    results = []
    now = datetime.now(timezone.utc)
    for source in sources:
        due = force or source.last_sync_at is None or (now - source.last_sync_at).total_seconds() >= 86400
        if not due:
            continue
        try:
            results.append(sync_official_source(db, source, connector_factory(source), user_id=user_id))
        except Exception as exc:
            logger.exception("Official source sync failed for source %s", source.id)
            results.append({"source_id": source.id, "status": "ERROR", "failed": 1, "error": str(exc)[:500]})
    return {"checked_at": now.isoformat(), "results": results, "due_count": len(results)}
