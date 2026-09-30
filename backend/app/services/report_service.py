import os
import time
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from config import settings
from app.models.report import Report
from app.models.audit_log import AuditLog
from app.services.ingestion_service import sanitize_filename

logger = logging.getLogger(__name__)


def _locator_label(locator: Any) -> str:
    if not isinstance(locator, dict):
        return ""
    parts = []
    if locator.get("document_table_id") or locator.get("table_number"):
        parts.append(f"table {locator.get('document_table_id', locator.get('table_number'))}")
    if locator.get("row_index") is not None:
        parts.append(f"row {locator['row_index']}")
    if locator.get("column_index") is not None:
        parts.append(f"column {locator['column_index']}")
    return "(" + ", ".join(parts) + ")" if parts else ""

# Try importing ReportLab
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    logger.warning("ReportLab library not installed on host environment. PDF generation will fall back to text PDF writer.")


def generate_report_pdf_bytes(
    title: str,
    report_type: str,
    subsidiary: str,
    fiscal_year: str,
    metrics_summary: Optional[List[Dict[str, Any]]] = None,
    validation_state: str = "REVIEW_REQUIRED",
    warnings: Optional[List[str]] = None,
) -> bytes:
    """Generates an official institutional PDF report document using ReportLab entirely in memory."""
    import io

    if not HAS_REPORTLAB:
        # Fallback text PDF content if reportlab is absent on host Python
        fallback_text = (
            f"%PDF-1.4\n1 0 obj << >> endobj\n"
            f"COALINTEL Report: {title}\nSubsidiary: {subsidiary}\nFY: {fiscal_year}\n"
        )
        return fallback_text.encode("utf-8")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#20262B'),
        spaceAfter=12
    )

    meta_style = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#5E6B73'),
        spaceAfter=18
    )

    body_style = styles['Normal']

    story = []

    # Title & Header Block
    story.append(Paragraph(f"<b>{title}</b>", title_style))
    story.append(Paragraph(f"<b>Organization:</b> Ministry of Coal / CIL HQ | <b>Subsidiary:</b> {subsidiary} | <b>Fiscal Year:</b> {fiscal_year}", meta_style))
    story.append(Spacer(1, 12))

    # Executive Summary Paragraph
    exec_text = (
        f"This evidence-grounded Institutional Mining & Operational Intelligence Report was compiled "
        f"by COALINTEL for <b>{subsidiary}</b> ({fiscal_year}). Numeric content is copied from persisted "
        f"structured evidence and is labelled with its validation state: <b>{validation_state}</b>."
    )
    story.append(Paragraph(exec_text, body_style))
    story.append(Spacer(1, 18))

    # Metrics Summary Table
    table_data = [["Entity", "Metric", "Value", "Unit", "Period", "Validation", "Source"]]
    if metrics_summary:
        for m in metrics_summary:
            metric_value = m.get("value") if m.get("value") is not None else m.get("standard_value")
            table_data.append([
                str(m.get("entity") or m.get("mine_name") or "Unavailable"),
                str(m.get("metric") or m.get("metric_name") or "Unavailable"),
                "Unavailable" if metric_value is None else f"{float(metric_value):.2f}",
                str(m.get("unit") or m.get("standard_unit") or "Unavailable"),
                str(m.get("period") or m.get("fiscal_year") or "Unavailable"),
                str(m.get("validation_status") or m.get("fact_status") or validation_state),
                f"{m.get('source', {}).get('document_name', m.get('document_filename', 'Unavailable'))} "
                f"p.{m.get('source', {}).get('page_number', m.get('page_number', '—'))} "
                f"{_locator_label(m.get('source', {}).get('locator', {}))}",
            ])
    else:
        table_data.append(["Unavailable", "No persisted structured facts", "Unavailable", "—", fiscal_year, validation_state, "—"])

    t = Table(table_data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#171A1F')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F5F7F8')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD3D8')),
    ]))

    story.append(t)
    story.append(Spacer(1, 24))
    for warning in warnings or []:
        story.append(Paragraph(f"<b>Warning:</b> {warning}", meta_style))
    story.append(Paragraph("<b>End of Evidence-Grounded Report.</b> Generated by COALINTEL Platform.", meta_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_pdf_reportlab(
    file_path: str,
    title: str,
    report_type: str,
    subsidiary: str,
    fiscal_year: str,
    metrics_summary: Optional[List[Dict[str, Any]]] = None
):
    """Generates an official institutional PDF report document using ReportLab to a local file."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    pdf_bytes = generate_report_pdf_bytes(
        title=title,
        report_type=report_type,
        subsidiary=subsidiary,
        fiscal_year=fiscal_year,
        metrics_summary=metrics_summary
    )
    with open(file_path, "wb") as f:
        f.write(pdf_bytes)
    logger.info(f"ReportLab PDF generated successfully at '{file_path}'.")


def create_report_assembly(
    db: Session,
    user_id: int,
    report_type: str,
    subsidiary: str = "ECL",
    fiscal_year: str = "2023-24",
    title: Optional[str] = None
) -> Report:
    """
    Assembles institutional report, generates ReportLab PDF in memory,
    persists Report record through StorageProvider with defensive compensation,
    and logs audit event.
    """
    from fastapi import HTTPException, status
    from app.services.storage_service import save_report_binary, delete_report_binary

    clean_subsidiary = sanitize_filename(subsidiary)
    clean_type = sanitize_filename(report_type)
    timestamp_str = str(int(time.time()))

    doc_title = title or f"Official Report ({clean_type}) — {clean_subsidiary} ({fiscal_year})"

    from app.services.report_grounding_service import (
        build_report_spec,
        collect_evidence_packet,
        deterministic_narrative,
        packet_fingerprint,
        validate_evidence_packet,
    )

    # 1. Collect bounded persisted evidence before rendering.  There are no
    # hard-coded fallback metrics and no LLM-generated numeric values.
    spec = build_report_spec(report_type=report_type, subsidiary=subsidiary, fiscal_year=fiscal_year, title=title)
    packet = collect_evidence_packet(db, spec=spec)
    validation = validate_evidence_packet(packet)
    narrative = deterministic_narrative(packet, validation)

    # 2. Generate ReportLab PDF entirely in memory (0 temporary disk I/O)
    pdf_bytes = generate_report_pdf_bytes(
        title=doc_title,
        report_type=report_type,
        subsidiary=subsidiary,
        fiscal_year=fiscal_year,
        metrics_summary=packet.get("structured_facts", []),
        validation_state=validation["state"],
        warnings=validation.get("warnings", []),
    )

    target_storage_ref = None

    try:
        # 3. Create initial Report DB model and flush to obtain report_id
        new_report = Report(
            title=doc_title,
            report_type=report_type,
            subsidiary=subsidiary,
            fiscal_year=fiscal_year,
            file_path="",  # Populated after storage persistence
            content_json={
                "title": doc_title, "report_type": report_type, "subsidiary": subsidiary, "fiscal_year": fiscal_year,
                "spec": spec, "evidence_packet": packet, "validation": validation,
                "narrative": narrative, "packet_fingerprint": packet_fingerprint(packet),
            },
            approval_status="DRAFT",
            created_by=user_id
        )
        db.add(new_report)
        db.flush()  # Allocates new_report.id

        # 4. Persist PDF bytes via StorageProvider
        storage_filename = f"Report_{clean_type}_{clean_subsidiary}_{timestamp_str}_{new_report.id}.pdf"
        target_storage_ref = save_report_binary(
            file_bytes=pdf_bytes,
            report_id=new_report.id,
            filename=storage_filename,
            content_type="application/pdf"
        )
        new_report.file_path = target_storage_ref

        # 5. Insert Audit Log
        audit_entry = AuditLog(
            user_id=user_id,
            action="REPORT_GENERATE",
            resource_type="Report",
            resource_id=new_report.id,
            details=f"Generated report '{doc_title}' ({report_type}, {subsidiary}). Storage ref: {target_storage_ref}",
            details_json={
                "report_id": new_report.id,
                "title": doc_title,
                "report_type": report_type,
                "subsidiary": subsidiary,
                "file_path": target_storage_ref
            }
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(new_report)

        logger.info(f"Report ID #{new_report.id} successfully created and committed with storage ref '{target_storage_ref}'.")
        return new_report

    except HTTPException:
        db.rollback()
        if target_storage_ref:
            try:
                delete_report_binary(target_storage_ref)
            except Exception as clean_err:
                logger.warning(f"Compensating report storage cleanup note for '{target_storage_ref}': {clean_err}")
        raise

    except Exception as e:
        db.rollback()
        if target_storage_ref:
            try:
                delete_report_binary(target_storage_ref)
            except Exception as clean_err:
                logger.warning(f"Compensating report storage cleanup note for '{target_storage_ref}': {clean_err}")
        logger.error(f"Error during report creation assembly: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report and persist to storage."
        )
