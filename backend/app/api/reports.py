import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db
from app.models.user import User
from app.models.report import Report
from app.models.audit_log import AuditLog
from app.core.rbac import get_current_user, require_roles
from app.schemas.report import ReportGenerateRequest, ReportResponse
from app.services.report_service import create_report_assembly

router = APIRouter(tags=["Report Generation Subsystem"])


@router.post("/reports/generate", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def generate_report_endpoint(
    payload: ReportGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Admin", "Analyst", "Reviewer"]))
):
    """
    Generates an official institutional PDF report using ReportLab engine.
    Persists Report database record and writes an audit event.
    """
    report = create_report_assembly(
        db=db,
        user_id=current_user.id,
        report_type=payload.report_type,
        subsidiary=payload.subsidiary or current_user.subsidiary or "ECL",
        fiscal_year=payload.fiscal_year or "2023-24",
        title=payload.title
    )
    return ReportResponse.model_validate(report)


@router.get("/reports", response_model=List[ReportResponse])
def list_reports(
    subsidiary_filter: Optional[str] = None,
    approval_status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves paginated list of generated institutional reports."""
    query = db.query(Report)
    if subsidiary_filter and subsidiary_filter != "ALL":
        query = query.filter(Report.subsidiary == subsidiary_filter)
    if approval_status_filter:
        query = query.filter(Report.approval_status == approval_status_filter.upper())

    reports = query.order_by(Report.created_at.desc()).all()
    return [ReportResponse.model_validate(r) for r in reports]


@router.get("/reports/{id}/download")
def download_report_pdf(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Streams generated PDF report file for download.
    Supports legacy local files, new local StorageProvider files, and remote Supabase Storage objects.
    """
    from fastapi.responses import Response
    from app.services.storage_service import (
        report_binary_exists,
        read_report_binary,
        parse_storage_reference,
    )

    report = db.query(Report).filter(Report.id == id).first()
    if not report or not report.file_path or not report_binary_exists(report.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report file for ID #{id} not found on server storage."
        )

    filename = os.path.basename(report.file_path)
    ref_type, bucket, path = parse_storage_reference(report.file_path)

    # If local filesystem file exists at path, return FileResponse
    if ref_type == "local" and os.path.exists(os.path.abspath(report.file_path)):
        return FileResponse(
            path=os.path.abspath(report.file_path),
            media_type="application/pdf",
            filename=filename
        )

    # Supabase or non-local storage: retrieve binary bytes securely through StorageProvider
    pdf_bytes = read_report_binary(report.file_path)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.post("/reports/{id}/approve", response_model=ReportResponse)
def approve_report_endpoint(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Admin", "Reviewer"]))
):
    """
    Approves a report draft (status -> 'APPROVED'). Requires Admin or Reviewer RBAC role.
    """
    report = db.query(Report).filter(Report.id == id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report ID #{id} not found."
        )

    report.approval_status = "APPROVED"
    
    # Audit log
    audit_entry = AuditLog(
        user_id=current_user.id,
        action="REPORT_APPROVE",
        resource_type="Report",
        resource_id=report.id,
        details=f"Approved report #{report.id} ('{report.title}'). Status -> APPROVED."
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(report)

    return ReportResponse.model_validate(report)

