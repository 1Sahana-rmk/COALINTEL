from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database import get_db
from app.models.user import User
from app.models.data_conflict import DataConflict
from app.models.data_provenance import DataConflictRecord
from app.models.mine import MineMaster
from app.models.document import Document
from app.models.audit_log import AuditLog
from app.core.rbac import get_current_user, require_roles
from app.schemas.validation import ValidationItemResponse, ConflictResponse, ConflictResolveRequest
from app.services.validation_service import run_deterministic_validation_feed
from app.services.conflict_service import detect_and_register_cross_document_conflicts, resolve_data_conflict
from app.services.normalization_service import normalize_subsidiary_scope

router = APIRouter(tags=["Validation & Conflict Resolver"])


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


@router.get("/conflicts", response_model=List[ConflictResponse])
def list_conflicts(
    status_filter: Optional[str] = None,
    subsidiary_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Triggers cross-document conflict detection engine (> 1% threshold) and returns conflicts
    from both ingested document extraction and authoritative government data records.
    """
    # Trigger conflict engine scan for uploaded document extractions
    detect_and_register_cross_document_conflicts(db)

    query = db.query(DataConflict)
    if status_filter and status_filter.upper() not in ["ALL", "ANY", ""]:
        query = query.filter(DataConflict.status == status_filter.upper())
    
    norm_sub = normalize_subsidiary_scope(subsidiary_filter)
    if norm_sub and norm_sub.upper() not in ["ALL", "ALL CIL"]:
        query = query.outerjoin(Document, DataConflict.doc_a_id == Document.id).filter(
            or_(
                Document.subsidiary == norm_sub,
                DataConflict.mine_name.ilike(f"%{norm_sub}%")
            )
        )
    
    conflicts = query.order_by(DataConflict.created_at.desc()).all()

    response_list = []
    seen_conflicts = set()

    for c in conflicts:
        doc_a = db.query(Document).filter(Document.id == c.doc_a_id).first() if c.doc_a_id else None
        doc_b = db.query(Document).filter(Document.id == c.doc_b_id).first() if c.doc_b_id else None
        
        subsidiary = doc_a.subsidiary if doc_a and doc_a.subsidiary else "CIL HQ"
        if not doc_a:
            # Fallback lookup from MineMaster
            m_lookup = db.query(MineMaster).filter(MineMaster.mine_name.ilike(c.mine_name)).first()
            if m_lookup and m_lookup.subsidiary_name:
                subsidiary = m_lookup.subsidiary_name

        key = (c.mine_name.strip().lower(), (c.fiscal_year or "").strip().lower(), (c.metric_name or "").strip().lower())
        seen_conflicts.add(key)

        response_list.append(ConflictResponse(
            id=c.id,
            mine_name=c.mine_name,
            subsidiary=subsidiary,
            metric_name=c.metric_name,
            fiscal_year=c.fiscal_year,
            document_a_id=c.doc_a_id or 0,
            document_a_filename=doc_a.filename if doc_a else (f"Doc #{c.doc_a_id}" if c.doc_a_id else "Primary Source"),
            document_a_value=float(c.doc_a_value) if c.doc_a_value is not None else 0.0,
            document_a_unit="MT",
            document_b_id=c.doc_b_id or 0,
            document_b_filename=doc_b.filename if doc_b else (f"Doc #{c.doc_b_id}" if c.doc_b_id else "Comparison Source"),
            document_b_value=float(c.doc_b_value) if c.doc_b_value is not None else 0.0,
            document_b_unit="MT",
            discrepancy_percentage=float(c.discrepancy_pct) if c.discrepancy_pct is not None else 0.0,
            status=c.status,
            resolved_by=c.resolved_by,
            resolution_notes=c.resolution_notes,
            created_at=c.created_at
        ))

    # Also incorporate authoritative Government of India records from DataConflictRecord
    cr_query = db.query(DataConflictRecord)
    cr_records = cr_query.order_by(DataConflictRecord.created_at.desc()).all()

    for cr in cr_records:
        mine = db.query(MineMaster).filter(MineMaster.mine_id == cr.entity_id).first()
        mine_name = mine.mine_name if mine else cr.entity_id
        subsidiary = (mine.subsidiary_name or mine.company_name) if mine else "Ministry of Coal / CIL"
        metric_name = "Coal Production" if (cr.metric or "").lower() == "production" else (cr.metric or "Metric").title()
        cr_status = (cr.resolution_status or "OPEN").upper()

        if status_filter and status_filter.upper() not in ["ALL", "ANY", ""]:
            if cr_status != status_filter.upper():
                continue

        if norm_sub and norm_sub.upper() not in ["ALL", "ALL CIL"]:
            if norm_sub.upper() not in subsidiary.upper() and norm_sub.upper() not in mine_name.upper():
                continue

        key = (mine_name.strip().lower(), (cr.financial_year or "").strip().lower(), metric_name.strip().lower())
        if key in seen_conflicts:
            continue
        seen_conflicts.add(key)

        response_list.append(ConflictResponse(
            id=10000 + cr.conflict_id,
            mine_name=mine_name,
            subsidiary=subsidiary,
            metric_name=metric_name,
            fiscal_year=cr.financial_year,
            document_a_id=0,
            document_a_filename=cr.source_a,
            document_a_value=float(cr.value_a),
            document_a_unit="MT",
            document_b_id=0,
            document_b_filename=cr.source_b,
            document_b_value=float(cr.value_b),
            document_b_unit="MT",
            discrepancy_percentage=float(cr.difference_percent),
            status=cr_status,
            resolved_by=None,
            resolution_notes=cr.resolution_method or cr.possible_reason,
            created_at=cr.created_at
        ))

    return response_list


@router.get("/conflicts/{id}", response_model=ConflictResponse)
def get_conflict_by_id(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns a single cross-document conflict record by ID.
    Supports both document extraction conflicts and government discrepancy records.
    """
    if id < 10000:
        c = db.query(DataConflict).filter(DataConflict.id == id).first()
        if c:
            doc_a = db.query(Document).filter(Document.id == c.doc_a_id).first() if c.doc_a_id else None
            doc_b = db.query(Document).filter(Document.id == c.doc_b_id).first() if c.doc_b_id else None
            subsidiary = doc_a.subsidiary if doc_a and doc_a.subsidiary else "CIL HQ"
            if not doc_a:
                m_lookup = db.query(MineMaster).filter(MineMaster.mine_name.ilike(c.mine_name)).first()
                if m_lookup and m_lookup.subsidiary_name:
                    subsidiary = m_lookup.subsidiary_name

            return ConflictResponse(
                id=c.id,
                mine_name=c.mine_name,
                subsidiary=subsidiary,
                metric_name=c.metric_name,
                fiscal_year=c.fiscal_year,
                document_a_id=c.doc_a_id or 0,
                document_a_filename=doc_a.filename if doc_a else (f"Doc #{c.doc_a_id}" if c.doc_a_id else "Primary Source"),
                document_a_value=float(c.doc_a_value) if c.doc_a_value is not None else 0.0,
                document_a_unit="MT",
                document_b_id=c.doc_b_id or 0,
                document_b_filename=doc_b.filename if doc_b else (f"Doc #{c.doc_b_id}" if c.doc_b_id else "Comparison Source"),
                document_b_value=float(c.doc_b_value) if c.doc_b_value is not None else 0.0,
                document_b_unit="MT",
                discrepancy_percentage=float(c.discrepancy_pct) if c.discrepancy_pct is not None else 0.0,
                status=c.status,
                resolved_by=c.resolved_by,
                resolution_notes=c.resolution_notes,
                created_at=c.created_at
            )

    # Check DataConflictRecord
    cr_id = id - 10000 if id >= 10000 else id
    cr = db.query(DataConflictRecord).filter(DataConflictRecord.conflict_id == cr_id).first()
    if cr:
        mine = db.query(MineMaster).filter(MineMaster.mine_id == cr.entity_id).first()
        mine_name = mine.mine_name if mine else cr.entity_id
        subsidiary = (mine.subsidiary_name or mine.company_name) if mine else "Ministry of Coal / CIL"
        metric_name = "Coal Production" if (cr.metric or "").lower() == "production" else (cr.metric or "Metric").title()

        return ConflictResponse(
            id=10000 + cr.conflict_id,
            mine_name=mine_name,
            subsidiary=subsidiary,
            metric_name=metric_name,
            fiscal_year=cr.financial_year,
            document_a_id=0,
            document_a_filename=cr.source_a,
            document_a_value=float(cr.value_a),
            document_a_unit="MT",
            document_b_id=0,
            document_b_filename=cr.source_b,
            document_b_value=float(cr.value_b),
            document_b_unit="MT",
            discrepancy_percentage=float(cr.difference_percent),
            status=(cr.resolution_status or "OPEN").upper(),
            resolved_by=None,
            resolution_notes=cr.resolution_method or cr.possible_reason,
            created_at=cr.created_at
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Conflict with ID {id} not found."
    )


@router.post("/conflicts/{id}/resolve", response_model=ConflictResponse)
def resolve_conflict_endpoint(
    id: int,
    payload: ConflictResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Admin", "Reviewer"]))
):
    """
    Resolves an open cross-document conflict record.
    Requires Admin or Reviewer RBAC role. Appends immutable audit log.
    """
    if id < 10000:
        c = db.query(DataConflict).filter(DataConflict.id == id).first()
        if c:
            updated = resolve_data_conflict(
                db=db,
                conflict_id=id,
                user_id=current_user.id,
                resolution_action=payload.resolution_action,
                override_value=payload.override_value,
                notes=payload.notes
            )
            doc_a = db.query(Document).filter(Document.id == updated.doc_a_id).first() if updated.doc_a_id else None
            doc_b = db.query(Document).filter(Document.id == updated.doc_b_id).first() if updated.doc_b_id else None
            subsidiary = doc_a.subsidiary if doc_a and doc_a.subsidiary else "CIL HQ"

            return ConflictResponse(
                id=updated.id,
                mine_name=updated.mine_name,
                subsidiary=subsidiary,
                metric_name=updated.metric_name,
                fiscal_year=updated.fiscal_year,
                document_a_id=updated.doc_a_id or 0,
                document_a_filename=doc_a.filename if doc_a else (f"Doc #{updated.doc_a_id}" if updated.doc_a_id else "Primary Source"),
                document_a_value=float(updated.doc_a_value) if updated.doc_a_value is not None else 0.0,
                document_a_unit="MT",
                document_b_id=updated.doc_b_id or 0,
                document_b_filename=doc_b.filename if doc_b else (f"Doc #{updated.doc_b_id}" if updated.doc_b_id else "Comparison Source"),
                document_b_value=float(updated.doc_b_value) if updated.doc_b_value is not None else 0.0,
                document_b_unit="MT",
                discrepancy_percentage=float(updated.discrepancy_pct) if updated.discrepancy_pct is not None else 0.0,
                status=updated.status,
                resolved_by=updated.resolved_by,
                resolution_notes=updated.resolution_notes,
                created_at=updated.created_at
            )

    # Check DataConflictRecord
    cr_id = id - 10000 if id >= 10000 else id
    cr = db.query(DataConflictRecord).filter(DataConflictRecord.conflict_id == cr_id).first()
    if not cr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conflict with ID {id} not found."
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
        mine_name=mine_name,
        subsidiary=subsidiary,
        metric_name=metric_name,
        fiscal_year=cr.financial_year,
        document_a_id=0,
        document_a_filename=cr.source_a,
        document_a_value=float(cr.value_a),
        document_a_unit="MT",
        document_b_id=0,
        document_b_filename=cr.source_b,
        document_b_value=float(cr.value_b),
        document_b_unit="MT",
        discrepancy_percentage=float(cr.difference_percent),
        status="RESOLVED",
        resolved_by=current_user.id,
        resolution_notes=cr.resolution_method,
        created_at=cr.created_at
    )
