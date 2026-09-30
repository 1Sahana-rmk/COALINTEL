from typing import Any, Dict, List, Optional, Tuple
import logging
from datetime import datetime, timezone
from time import perf_counter
import re
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, event, func, or_, select

from database import get_db
from app.models.user import User
from app.models.data_conflict import DataConflict
from app.models.data_provenance import DataConflictRecord
from app.models.mine import MineMaster
from app.models.document import Document
from app.models.extracted_metric import ExtractedMetric
from app.models.audit_log import AuditLog
from app.core.rbac import ADMIN_ONLY_ROLES, REVIEW_ROLES, get_current_user, require_roles
from app.schemas.validation import (
    ValidationItemResponse,
    ConflictResponse,
    ConflictListResponse,
    ConflictRecomputeResponse,
    ConflictResolveRequest,
)
from app.services.validation_service import run_deterministic_validation_feed
from app.services.conflict_service import detect_and_register_cross_document_conflicts, resolve_data_conflict
from app.services.normalization_service import normalize_subsidiary_scope

router = APIRouter(tags=["Validation & Conflict Resolver"])
logger = logging.getLogger(__name__)


@router.get("/validation/feed", response_model=List[ValidationItemResponse])
def get_validation_feed(
    subsidiary_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns deterministic arithmetic validation warnings (> 5% discrepancy) and data quality feed items.
    """
    norm_sub = normalize_subsidiary_scope(subsidiary_filter)
    items = run_deterministic_validation_feed(
        db=db,
        subsidiary_filter=norm_sub or current_user.subsidiary
    )
    return [ValidationItemResponse.model_validate(i) for i in items]


MAX_CONFLICT_PAGE_SIZE = 100
# Keep offset pagination bounded while allowing direct navigation through the
# current persisted conflict corpus (65k+ rows) without silently returning a
# different page than the client requested.
MAX_CONFLICT_OFFSET = 100_000


def _is_unfiltered(value: Optional[str]) -> bool:
    return not value or value.upper() in {"ALL", "ANY", "ALL CIL", "ALL SUBSIDIARIES"}


def _apply_data_conflict_filters(query, status_filter, subsidiary_filter, mine_filter, metric_filter, fiscal_year_filter):
    if not _is_unfiltered(status_filter):
        query = query.filter(DataConflict.status == status_filter.upper())
    if not _is_unfiltered(subsidiary_filter):
        norm_sub = normalize_subsidiary_scope(subsidiary_filter)
        query = query.outerjoin(Document, DataConflict.doc_a_id == Document.id).filter(
            or_(Document.subsidiary == norm_sub, DataConflict.mine_name.ilike(f"%{norm_sub}%"))
        )
    if mine_filter:
        query = query.filter(DataConflict.mine_name.ilike(f"%{mine_filter}%"))
    if metric_filter:
        query = query.filter(DataConflict.metric_name.ilike(f"%{metric_filter}%"))
    if fiscal_year_filter:
        query = query.filter(DataConflict.fiscal_year == fiscal_year_filter)
    return query


def _official_is_already_represented(
    status_filter: Optional[str] = None,
    subsidiary_filter: Optional[str] = None,
    mine_filter: Optional[str] = None,
    metric_filter: Optional[str] = None,
    fiscal_year_filter: Optional[str] = None,
):
    """SQL equivalent of the legacy list deduplication rule.

    Official records are hidden only when a generated DataConflict has the same
    mine, fiscal year and metric. Document-pair identity remains available on
    DataConflict itself and is not discarded.
    """
    mine_name = func.coalesce(MineMaster.mine_name, DataConflictRecord.entity_id)
    metric_match = or_(
        and_(
            func.lower(DataConflictRecord.metric) == "production",
            func.lower(DataConflict.metric_name) == "coal production",
        ),
        func.lower(DataConflict.metric_name) == func.lower(DataConflictRecord.metric),
    )
    conditions = [
        func.lower(DataConflict.mine_name) == func.lower(mine_name),
        func.lower(DataConflict.fiscal_year) == func.lower(DataConflictRecord.financial_year),
        metric_match,
    ]
    if not _is_unfiltered(status_filter):
        conditions.append(DataConflict.status == status_filter.upper())
    if not _is_unfiltered(subsidiary_filter):
        norm_sub = normalize_subsidiary_scope(subsidiary_filter)
        conditions.append(or_(Document.subsidiary == norm_sub, DataConflict.mine_name.ilike(f"%{norm_sub}%")))
    if mine_filter:
        conditions.append(DataConflict.mine_name.ilike(f"%{mine_filter}%"))
    if metric_filter:
        conditions.append(DataConflict.metric_name.ilike(f"%{metric_filter}%"))
    if fiscal_year_filter:
        conditions.append(DataConflict.fiscal_year == fiscal_year_filter)
    return select(1).select_from(DataConflict).outerjoin(
        Document, DataConflict.doc_a_id == Document.id
    ).where(and_(*conditions)).exists()


def _apply_official_filters(query, status_filter, subsidiary_filter, mine_filter, metric_filter, fiscal_year_filter):
    if not _is_unfiltered(status_filter):
        query = query.filter(DataConflictRecord.resolution_status == status_filter.upper())
    if not _is_unfiltered(subsidiary_filter):
        norm_sub = normalize_subsidiary_scope(subsidiary_filter)
        query = query.filter(or_(
            MineMaster.subsidiary_name.ilike(f"%{norm_sub}%"),
            MineMaster.company_name.ilike(f"%{norm_sub}%"),
            MineMaster.mine_name.ilike(f"%{norm_sub}%"),
        ))
    if mine_filter:
        query = query.filter(or_(
            MineMaster.mine_name.ilike(f"%{mine_filter}%"),
            DataConflictRecord.entity_id.ilike(f"%{mine_filter}%"),
        ))
    if metric_filter:
        query = query.filter(DataConflictRecord.metric.ilike(f"%{metric_filter}%"))
    if fiscal_year_filter:
        query = query.filter(DataConflictRecord.financial_year == fiscal_year_filter)
    return query


def _unavailable_evidence(document_id: Optional[int], warning: str) -> dict:
    return {
        "document_id": document_id,
        "metric_id": None,
        "page_number": None,
        "bounding_box": None,
        "provenance_available": False,
        "warning": warning,
    }


def _metric_evidence_map(db: Session, conflicts: List[DataConflict]) -> Dict[Tuple[int, str, str, str], List[ExtractedMetric]]:
    """Load candidate extracted metrics once for a bounded conflict window.

    Matching uses the persisted conflict dimensions and the persisted numeric
    value.  It never searches page text or infers a page from a filename.
    """
    document_ids = {
        document_id
        for conflict in conflicts
        for document_id in (conflict.doc_a_id, conflict.doc_b_id)
        if document_id
    }
    if not document_ids:
        return {}
    metrics = db.query(ExtractedMetric).filter(ExtractedMetric.document_id.in_(document_ids)).all()
    grouped: Dict[Tuple[int, str, str, str], List[ExtractedMetric]] = {}
    for metric in metrics:
        key = (
            metric.document_id,
            (metric.mine_name or "").strip().lower(),
            (metric.metric_name or "").strip().lower(),
            (metric.fiscal_year or "").strip().lower(),
        )
        grouped.setdefault(key, []).append(metric)
    return grouped


def _metric_evidence(
    conflict: DataConflict,
    document_id: Optional[int],
    value: Optional[float],
    evidence_map: Dict[Tuple[int, str, str, str], List[ExtractedMetric]],
):
    if not document_id:
        return _unavailable_evidence(None, "Source document is not linked to this conflict side.")
    key = (
        document_id,
        (conflict.mine_name or "").strip().lower(),
        (conflict.metric_name or "").strip().lower(),
        (conflict.fiscal_year or "").strip().lower(),
    )
    candidates = evidence_map.get(key, [])
    if not candidates:
        return _unavailable_evidence(document_id, "Page-level provenance unavailable for this conflict side.")

    target = float(value) if value is not None else None
    ranked = sorted(
        candidates,
        key=lambda metric: (
            abs(float((metric.standard_value if metric.standard_value is not None else metric.numeric_value)) - target)
            if target is not None else 0.0,
            metric.id,
        ),
    )
    selected = ranked[0]
    best_distance = abs(
        float((selected.standard_value if selected.standard_value is not None else selected.numeric_value)) - target
    ) if target is not None else 0.0
    if target is not None and best_distance > 1e-6:
        return _unavailable_evidence(
            document_id,
            "No exact persisted metric value matches this conflict side; page-level provenance is unavailable.",
        )
    tied = [
        metric for metric in ranked
        if abs(
            float((metric.standard_value if metric.standard_value is not None else metric.numeric_value)) - target
        ) <= best_distance + 1e-9
    ] if target is not None else ranked
    if len({metric.page_number for metric in tied}) > 1:
        return _unavailable_evidence(
            document_id,
            "Multiple persisted metrics match this conflict side on different pages; exact page provenance is ambiguous.",
        )
    page_number = selected.page_number
    if page_number is None or page_number < 1:
        return {
            "document_id": document_id,
            "metric_id": selected.id,
            "page_number": None,
            "bounding_box": None,
            "provenance_available": False,
            "warning": "Extracted metric is linked, but valid one-based page-level provenance is unavailable.",
        }
    return {
        "document_id": document_id,
        "metric_id": selected.id,
        "page_number": page_number,
        "bounding_box": None,
        "provenance_available": True,
        "warning": "Exact evidence geometry unavailable for this extracted metric.",
    }


def _data_conflict_response(conflict, documents_by_id, mines_by_name, evidence_map=None) -> ConflictResponse:
    evidence_map = evidence_map or {}
    doc_a = documents_by_id.get(conflict.doc_a_id) if conflict.doc_a_id else None
    doc_b = documents_by_id.get(conflict.doc_b_id) if conflict.doc_b_id else None
    subsidiary = doc_a.subsidiary if doc_a and doc_a.subsidiary else "CIL HQ"
    if not doc_a:
        mine = mines_by_name.get(conflict.mine_name.strip().lower())
        if mine and mine.subsidiary_name:
            subsidiary = mine.subsidiary_name
    return ConflictResponse(
        id=conflict.id,
        conflict_key=f"data:{conflict.id}",
        mine_name=conflict.mine_name,
        subsidiary=subsidiary,
        metric_name=conflict.metric_name,
        fiscal_year=conflict.fiscal_year,
        document_a_id=conflict.doc_a_id,
        document_a_source_id=None,
        document_a_filename=doc_a.filename if doc_a else (f"Doc #{conflict.doc_a_id}" if conflict.doc_a_id else "Primary Source"),
        document_a_value=float(conflict.doc_a_value) if conflict.doc_a_value is not None else 0.0,
        document_a_unit="MT",
        evidence_a=_metric_evidence(conflict, conflict.doc_a_id, conflict.doc_a_value, evidence_map),
        document_b_id=conflict.doc_b_id,
        document_b_source_id=None,
        document_b_filename=doc_b.filename if doc_b else (f"Doc #{conflict.doc_b_id}" if conflict.doc_b_id else "Comparison Source"),
        document_b_value=float(conflict.doc_b_value) if conflict.doc_b_value is not None else 0.0,
        document_b_unit="MT",
        evidence_b=_metric_evidence(conflict, conflict.doc_b_id, conflict.doc_b_value, evidence_map),
        discrepancy_percentage=float(conflict.discrepancy_pct) if conflict.discrepancy_pct is not None else 0.0,
        status=conflict.status,
        resolved_by=conflict.resolved_by,
        resolution_notes=conflict.resolution_notes,
        created_at=conflict.created_at,
    )


def _official_conflict_response(record, mine) -> ConflictResponse:
    mine_name = mine.mine_name if mine else record.entity_id
    subsidiary = (mine.subsidiary_name or mine.company_name) if mine else "Ministry of Coal / CIL"
    metric_name = "Coal Production" if (record.metric or "").lower() == "production" else (record.metric or "Metric").title()
    return ConflictResponse(
        id=10000 + record.conflict_id,
        conflict_key=f"official:{record.conflict_id}",
        mine_name=mine_name,
        subsidiary=subsidiary,
        metric_name=metric_name,
        fiscal_year=record.financial_year,
        document_a_id=None,
        document_a_source_id=record.source_a,
        document_a_filename=record.source_a,
        document_a_value=float(record.value_a),
        document_a_unit="MT",
        evidence_a=_unavailable_evidence(None, "Page-level provenance unavailable for this official conflict record."),
        document_b_id=None,
        document_b_source_id=record.source_b,
        document_b_filename=record.source_b,
        document_b_value=float(record.value_b),
        document_b_unit="MT",
        evidence_b=_unavailable_evidence(None, "Page-level provenance unavailable for this official conflict record."),
        discrepancy_percentage=float(record.difference_percent),
        status=(record.resolution_status or "OPEN").upper(),
        resolved_by=None,
        resolution_notes=record.resolution_method or record.possible_reason,
        created_at=record.created_at,
    )


def _fetch_conflict_page(
    db: Session,
    status_filter: Optional[str] = None,
    subsidiary_filter: Optional[str] = None,
    mine_filter: Optional[str] = None,
    metric_filter: Optional[str] = None,
    fiscal_year_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    enforce_bounds: bool = True,
) -> Tuple[List[ConflictResponse], int, Dict[str, int]]:
    if enforce_bounds:
        skip = min(max(skip, 0), MAX_CONFLICT_OFFSET)
        limit = min(max(limit, 1), MAX_CONFLICT_PAGE_SIZE)
    else:
        skip = max(skip, 0)
        limit = max(limit, 1)

    data_query = _apply_data_conflict_filters(
        db.query(DataConflict), status_filter, subsidiary_filter,
        mine_filter, metric_filter, fiscal_year_filter,
    )
    data_total = data_query.count()

    official_query = _apply_official_filters(
        db.query(DataConflictRecord, MineMaster).outerjoin(
            MineMaster, MineMaster.mine_id == DataConflictRecord.entity_id
        ), status_filter, subsidiary_filter, mine_filter, metric_filter, fiscal_year_filter,
    ).filter(~_official_is_already_represented(
        status_filter=status_filter,
        subsidiary_filter=subsidiary_filter,
        mine_filter=mine_filter,
        metric_filter=metric_filter,
        fiscal_year_filter=fiscal_year_filter,
    ))
    official_total = official_query.with_entities(DataConflictRecord.conflict_id).count()
    total = data_total + official_total

    window = skip + limit
    data_rows = data_query.order_by(DataConflict.created_at.desc(), DataConflict.id.desc()).offset(0).limit(window).all()
    official_rows = official_query.order_by(
        DataConflictRecord.created_at.desc(), DataConflictRecord.conflict_id.desc()
    ).offset(0).limit(window).all()

    doc_ids = {doc_id for row in data_rows for doc_id in (row.doc_a_id, row.doc_b_id) if doc_id}
    documents_by_id = {
        document.id: document
        for document in db.query(Document).filter(Document.id.in_(doc_ids)).all()
    } if doc_ids else {}
    fallback_mine_names = {row.mine_name.strip().lower() for row in data_rows if not row.doc_a_id}
    mines_by_name = {
        mine.mine_name.strip().lower(): mine
        for mine in db.query(MineMaster).filter(func.lower(MineMaster.mine_name).in_(fallback_mine_names)).all()
    } if fallback_mine_names else {}

    evidence_map = _metric_evidence_map(db, data_rows)

    combined: List[ConflictResponse] = [
        _data_conflict_response(row, documents_by_id, mines_by_name, evidence_map) for row in data_rows
    ]
    combined.extend(_official_conflict_response(record, mine) for record, mine in official_rows)
    combined.sort(key=lambda item: (item.created_at or datetime.min.replace(tzinfo=timezone.utc), item.id), reverse=True)
    items = combined[skip:skip + limit]
    return items, total, {
        "data_conflict_rows": data_total,
        "official_non_overlapping_rows": official_total,
        "window_rows_loaded": len(data_rows) + len(official_rows),
    }


def list_conflicts(
    status_filter: Optional[str] = None,
    subsidiary_filter: Optional[str] = None,
    db: Session = None,
    current_user: User = None,
):
    """Compatibility helper for existing service-level callers/tests.

    The HTTP endpoint is bounded; this helper intentionally retains the old
    list-shaped return contract for in-process callers only.
    """
    items, _total, _stats = _fetch_conflict_page(
        db=db,
        status_filter=status_filter,
        subsidiary_filter=subsidiary_filter,
        skip=0,
        limit=1_000_000,
        enforce_bounds=False,
    )
    return items


@router.get("/conflicts", response_model=ConflictListResponse)
def get_conflict_page(
    status_filter: Optional[str] = None,
    subsidiary_filter: Optional[str] = None,
    mine_filter: Optional[str] = None,
    metric_filter: Optional[str] = None,
    fiscal_year_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return persisted conflicts in a bounded page; detection is explicit."""
    request_started = perf_counter()
    sql_count = 0
    sql_timings = []
    logger.info("CONFLICT_REQUEST_ENTER elapsed_ms=0.00 mode=list page_limit=%s", limit)
    connection = db.connection()

    def before_sql(_connection, _cursor, statement, _parameters, context, _executemany):
        context._coalintel_conflict_sql_started = perf_counter()
        match = re.match(r"\s*([A-Za-z]+)", statement)
        context._coalintel_conflict_sql_kind = match.group(1).upper() if match else "SQL"

    def after_sql(_connection, _cursor, _statement, _parameters, context, _executemany):
        nonlocal sql_count
        sql_count += 1
        elapsed_ms = (perf_counter() - getattr(context, "_coalintel_conflict_sql_started", perf_counter())) * 1000
        sql_timings.append((elapsed_ms, getattr(context, "_coalintel_conflict_sql_kind", "SQL")))

    event.listen(connection, "before_cursor_execute", before_sql)
    event.listen(connection, "after_cursor_execute", after_sql)
    try:
        items, total, stats = _fetch_conflict_page(
            db=db,
            status_filter=status_filter,
            subsidiary_filter=subsidiary_filter,
            mine_filter=mine_filter,
            metric_filter=metric_filter,
            fiscal_year_filter=fiscal_year_filter,
            skip=skip,
            limit=limit,
        )
        actual_skip = min(max(skip, 0), MAX_CONFLICT_OFFSET)
        actual_limit = min(max(limit, 1), MAX_CONFLICT_PAGE_SIZE)
        logger.info(
            "CONFLICT_LIST_COUNTS data_conflict_rows=%s official_non_overlapping_rows=%s total=%s window_rows_loaded=%s",
            stats["data_conflict_rows"], stats["official_non_overlapping_rows"], total, stats["window_rows_loaded"],
        )
        logger.info(
            "CONFLICT_SQL_SUMMARY elapsed_ms=%.2f query_count=%s slowest=%s",
            (perf_counter() - request_started) * 1000, sql_count, sorted(sql_timings, reverse=True)[:5],
        )
        return ConflictListResponse(
            items=items,
            total=total,
            skip=actual_skip,
            limit=actual_limit,
            has_next=actual_skip + actual_limit < total,
        )
    finally:
        event.remove(connection, "before_cursor_execute", before_sql)
        event.remove(connection, "after_cursor_execute", after_sql)


@router.post("/conflicts/recompute", response_model=ConflictRecomputeResponse)
def recompute_conflicts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(ADMIN_ONLY_ROLES)),
):
    """Explicitly run the expensive detector; normal list reads never do this."""
    started = perf_counter()
    logger.info("CONFLICT_DETECTION_START mode=explicit_recompute")
    stats = detect_and_register_cross_document_conflicts(db)
    logger.info(
        "CONFLICT_DETECTION_DONE mode=explicit_recompute elapsed_ms=%.2f candidate_pairs=%s discrepancies=%s new_conflicts=%s",
        (perf_counter() - started) * 1000,
        stats.get("candidate_pair_count", 0), stats.get("discrepancy_count", 0), stats.get("new_conflicts_count", 0),
    )
    return ConflictRecomputeResponse(status="COMPLETED", stats=stats)


def _parse_conflict_reference(reference: str) -> Tuple[str, int]:
    """Parse namespaced API identities while retaining numeric URL compatibility."""
    value = str(reference).strip()
    if value.startswith("data:"):
        return "data", int(value.split(":", 1)[1])
    if value.startswith("official:"):
        return "official", int(value.split(":", 1)[1])
    return "legacy", int(value)


def _serialize_data_conflict_detail(db: Session, conflict: DataConflict) -> ConflictResponse:
    documents = {}
    for document_id in (conflict.doc_a_id, conflict.doc_b_id):
        if document_id:
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                documents[document.id] = document
    mine = db.query(MineMaster).filter(MineMaster.mine_name.ilike(conflict.mine_name)).first()
    mines = {mine.mine_name.strip().lower(): mine} if mine else {}
    return _data_conflict_response(conflict, documents, mines, _metric_evidence_map(db, [conflict]))


def _get_conflict_records(db: Session, reference: str):
    try:
        kind, numeric_id = _parse_conflict_reference(reference)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Conflict with ID {reference} not found.")

    # Namespaced references are authoritative. Legacy numeric references first
    # try DataConflict, which fixes generated IDs above the old 10,000 cutoff.
    if kind in {"data", "legacy"}:
        data_conflict = db.query(DataConflict).filter(DataConflict.id == numeric_id).first()
        if data_conflict:
            return "data", data_conflict, numeric_id
        if kind == "data":
            return "data", None, numeric_id

    official_id = numeric_id - 10000 if kind == "legacy" and numeric_id >= 10000 else numeric_id
    official = db.query(DataConflictRecord).filter(DataConflictRecord.conflict_id == official_id).first()
    return "official", official, official_id


@router.get("/conflicts/{id}", response_model=ConflictResponse)
def get_conflict_by_id(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Return one conflict using a stable `data:<id>` or `official:<id>` key."""
    kind, record, _numeric_id = _get_conflict_records(db, id)
    if record is not None:
        if kind == "data":
            return _serialize_data_conflict_detail(db, record)
        mine = db.query(MineMaster).filter(MineMaster.mine_id == record.entity_id).first()
        return _official_conflict_response(record, mine)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Conflict with ID {id} not found.")


@router.post("/conflicts/{id}/resolve", response_model=ConflictResponse)
def resolve_conflict_endpoint(
    id: str,
    payload: ConflictResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(REVIEW_ROLES))
):
    """
    Resolves an open cross-document conflict record.
    Requires Admin or Reviewer RBAC role. Appends immutable audit log.
    """
    kind, record, numeric_id = _get_conflict_records(db, id)
    if kind == "data" and record is not None:
        updated = resolve_data_conflict(
            db=db,
            conflict_id=record.id,
            user_id=current_user.id,
            resolution_action=payload.resolution_action,
            override_value=payload.override_value,
            notes=payload.notes,
        )
        return _serialize_data_conflict_detail(db, updated)

    cr = record if kind == "official" else None
    if not cr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conflict with ID {id} not found."
        )

    if cr.resolution_status == "RESOLVED":
        mine = db.query(MineMaster).filter(MineMaster.mine_id == cr.entity_id).first()
        mine_name = mine.mine_name if mine else cr.entity_id
        subsidiary = (mine.subsidiary_name or mine.company_name) if mine else "Ministry of Coal / CIL"
        metric_name = "Coal Production" if (cr.metric or "").lower() == "production" else (cr.metric or "Metric").title()
        return ConflictResponse(
            id=10000 + cr.conflict_id,
            conflict_key=f"official:{cr.conflict_id}",
            mine_name=mine_name,
            subsidiary=subsidiary,
            metric_name=metric_name,
            fiscal_year=cr.financial_year,
            document_a_id=None,
            document_a_source_id=cr.source_a,
            document_a_filename=cr.source_a,
            document_a_value=float(cr.value_a),
            document_a_unit="MT",
            document_b_id=None,
            document_b_source_id=cr.source_b,
            document_b_filename=cr.source_b,
            document_b_value=float(cr.value_b),
            document_b_unit="MT",
            discrepancy_percentage=float(cr.difference_percent),
            status="RESOLVED",
            resolved_by=None,
            resolution_notes=cr.resolution_method,
            created_at=cr.created_at
        )

    resolved_val = payload.override_value
    if payload.resolution_action == "ACCEPT_DOC_A":
        resolved_val = float(cr.value_a)
    elif payload.resolution_action == "ACCEPT_DOC_B":
        resolved_val = float(cr.value_b)

    cr.resolution_status = "RESOLVED"
    cr.resolved_value = resolved_val
    cr.resolution_method = payload.notes or f"Resolved via '{payload.resolution_action}' by User #{current_user.id}"

    audit_entry = AuditLog(
        user_id=current_user.id,
        action="CONFLICT_RESOLVE",
        resource_type="DataConflictRecord",
        resource_id=cr.conflict_id,
        details=f"Resolved government conflict #{cr.conflict_id} for {cr.entity_id} ({cr.metric}). Action: {payload.resolution_action}.",
        details_json={
            "conflict_id": cr.conflict_id,
            "entity_id": cr.entity_id,
            "metric": cr.metric,
            "resolution_action": payload.resolution_action,
            "override_value": payload.override_value,
            "resolved_value": resolved_val
        }
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(cr)

    mine = db.query(MineMaster).filter(MineMaster.mine_id == cr.entity_id).first()
    mine_name = mine.mine_name if mine else cr.entity_id
    subsidiary = (mine.subsidiary_name or mine.company_name) if mine else "Ministry of Coal / CIL"
    metric_name = "Coal Production" if (cr.metric or "").lower() == "production" else (cr.metric or "Metric").title()

    return ConflictResponse(
        id=10000 + cr.conflict_id,
        conflict_key=f"official:{cr.conflict_id}",
        mine_name=mine_name,
        subsidiary=subsidiary,
        metric_name=metric_name,
        fiscal_year=cr.financial_year,
        document_a_id=None,
        document_a_source_id=cr.source_a,
        document_a_filename=cr.source_a,
        document_a_value=float(cr.value_a),
        document_a_unit="MT",
        document_b_id=None,
        document_b_source_id=cr.source_b,
        document_b_filename=cr.source_b,
        document_b_value=float(cr.value_b),
        document_b_unit="MT",
        discrepancy_percentage=float(cr.difference_percent),
        status="RESOLVED",
        resolved_by=current_user.id,
        resolution_notes=cr.resolution_method,
        created_at=cr.created_at
    )
