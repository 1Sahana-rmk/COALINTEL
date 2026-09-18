import os
import io
import time
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from database import get_db
from app.models.user import User
from app.models.document import Document
from app.models.extracted_metric import ExtractedMetric
from app.models.data_conflict import DataConflict
from app.core.rbac import get_current_user
from app.schemas.parliamentary import (
    ParliamentaryBriefingRequest,
    ParliamentaryBriefingResponse,
    SubsidiaryMetricItem,
    FlaggedDiscrepancyItem,
    BriefingEvidenceItem,
)
from app.services.rag_service import execute_rag_query
from app.services.hybrid_search_service import detect_query_entities
from app.services.normalization_service import (
    get_base_mine_name,
    detect_query_fiscal_year,
    classify_document_authority,
    is_historical_evidence_snippet,
    is_corporate_context_snippet,
    GENERIC_MINE_PHRASES,
    KNOWN_MINES,
)
from app.services.conflict_service import (
    get_metric_domain,
    are_units_compatible,
    is_generic_mine_name,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Parliamentary & Executive Briefing Intelligence"])


# Try importing ReportLab for PDF generation
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


@router.post("/parliamentary/briefing", response_model=ParliamentaryBriefingResponse)
def generate_parliamentary_briefing(
    payload: ParliamentaryBriefingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Parliamentary Question & Executive Briefing Intelligence Engine.
    Orchestrates query-aware RAG retrieval, structured metric extractions, deterministic validation,
    and cross-document conflict detection into an auditable institutional briefing.
    """
    question_text = payload.question_text.strip()
    if not question_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question text cannot be empty."
        )

    scope = payload.subsidiary_filter or "ALL CIL"
    fy = payload.fiscal_year or "2023-24"
    q_type = (payload.question_type or "GENERAL").upper()

    # 1. Parse question intent, target entities, and temporal context
    q_entities = detect_query_entities(question_text)
    target_mines = q_entities.get("mines", [])
    target_metric = q_entities.get("metric")
    metric_domain = q_entities.get("metric_domain")
    detected_fy = q_entities.get("fiscal_year")
    detected_sub = q_entities.get("subsidiary")

    effective_fy = detected_fy or fy
    effective_sub = scope
    if scope.upper() in ["ALL", "ALL CIL"] and detected_sub and detected_sub.upper() not in ["CIL", "CIL HQ", "ALL", "ALL CIL"]:
        effective_sub = detected_sub

    # Component 5: Resolve selected_scope with priority:
    # 1. Explicit UI/user scope when supplied and not "ALL" / "ALL CIL"
    # 2. Detected specific target mine/entity (e.g. "Gevra OC")
    # 3. Detected operating subsidiary when applicable (e.g. SECL, ECL, BCCL, WCL, MCL, CCL, NCL)
    # 4. Otherwise "ALL CIL"
    if payload.subsidiary_filter and payload.subsidiary_filter.upper() not in ["ALL", "ALL CIL"]:
        resolved_selected_scope = payload.subsidiary_filter
    elif target_mines:
        resolved_selected_scope = target_mines[0]
    elif detected_sub and detected_sub.upper() not in ["CIL", "CIL HQ", "ALL", "ALL CIL"]:
        resolved_selected_scope = detected_sub
    else:
        resolved_selected_scope = "ALL CIL"

    is_corporate_query = q_entities.get("is_corporate_query", False) or (
        resolved_selected_scope in ["ALL", "ALL CIL"]
        and not target_mines
        and not (detected_sub and detected_sub.upper() not in ["CIL", "CIL HQ", "ALL", "ALL CIL"])
    )

    def rank_parliamentary_metric(rec) -> tuple:
        m, doc = rec
        snippet = (m.raw_snippet or "").lower()
        m_name = (m.mine_name or "").lower()
        doc_sub = (doc.subsidiary or "").upper()

        # 1. Historical inception penalty
        is_hist = is_historical_evidence_snippet(m.raw_snippet, effective_fy)

        # 2. Mine matching
        mine_match = 0
        if target_mines:
            for tm in target_mines:
                if tm.lower() in m_name or get_base_mine_name(tm).lower() in m_name:
                    mine_match = 1
                    break

        # 3. Subsidiary matching
        sub_match = 0
        if effective_sub.upper() not in ["ALL", "ALL CIL"]:
            if doc_sub == effective_sub.upper() or (m.subsidiary and m.subsidiary.upper() == effective_sub.upper()):
                sub_match = 1

        # 4. Corporate relevance
        corp_score = 0
        if is_corporate_query:
            if is_corporate_context_snippet(m.raw_snippet) or "cil" in snippet or "coal india" in snippet:
                corp_score += 2
            if m_name in GENERIC_MINE_PHRASES or m_name in ["cil", "cil corporate", "corporate", "overall mine", "unspecified mine"]:
                corp_score += 1
            elif any(km.lower() in m_name for km in KNOWN_MINES):
                corp_score -= 1

        has_val = 1 if (m.standard_value is not None and float(m.standard_value) > 0) else 0
        auth_score = 1 if classify_document_authority(doc.filename) == "OFFICIAL" else 0
        conf_val = float(m.confidence_score or 0.0)

        return (
            not is_hist,
            mine_match if target_mines else 0,
            sub_match if effective_sub.upper() not in ["ALL", "ALL CIL"] else 0,
            corp_score if is_corporate_query else 0,
            has_val,
            auth_score,
            conf_val,
            int(m.id or 0)
        )

    # 2. Query structured DB metrics with entity, metric, and fiscal year grounding (Component 6 Failure Safety)
    try:
        metric_query = db.query(ExtractedMetric, Document).join(
            Document, ExtractedMetric.document_id == Document.id
        )

        if effective_sub.upper() not in ["ALL", "ALL CIL"]:
            metric_query = metric_query.filter(Document.subsidiary == effective_sub)

        if effective_fy and effective_fy.upper() != "ALL":
            metric_query = metric_query.filter(ExtractedMetric.fiscal_year == effective_fy)

        # Specific mine question: filter for target mine / base mine
        if target_mines:
            mine_conds = []
            for tm in target_mines:
                mine_conds.append(ExtractedMetric.mine_name.ilike(f"%{tm}%"))
                base_tm = get_base_mine_name(tm)
                if base_tm and base_tm.lower() != tm.lower():
                    mine_conds.append(ExtractedMetric.mine_name.ilike(f"%{base_tm}%"))
            metric_query = metric_query.filter(or_(*mine_conds))

        # Metric domain filtering
        if metric_domain:
            domain_terms = metric_domain.get("db_metric_names", [])
            if domain_terms:
                metric_conds = [ExtractedMetric.metric_name.ilike(f"%{dm}%") for dm in domain_terms]
                metric_query = metric_query.filter(or_(*metric_conds))
        elif target_metric:
            metric_query = metric_query.filter(ExtractedMetric.metric_name.ilike(f"%{target_metric}%"))

        candidate_records = metric_query.order_by(ExtractedMetric.id.desc()).limit(60).all()
        candidate_records.sort(key=rank_parliamentary_metric, reverse=True)
        extracted_records = candidate_records[:20]

        # If entity/metric filtering returned nothing for a broad question, fallback to broader query
        # ONLY if neither specific mine NOR specific metric was queried (prevent falling back to unrelated metrics!)
        if not extracted_records and not target_mines and not metric_domain and not target_metric:
            broad_query = db.query(ExtractedMetric, Document).join(
                Document, ExtractedMetric.document_id == Document.id
            )
            if effective_sub.upper() not in ["ALL", "ALL CIL"]:
                broad_query = broad_query.filter(Document.subsidiary == effective_sub)
            if effective_fy and effective_fy.upper() != "ALL":
                broad_query = broad_query.filter(ExtractedMetric.fiscal_year == effective_fy)
            b_candidates = broad_query.order_by(ExtractedMetric.id.desc()).limit(60).all()
            b_candidates.sort(key=rank_parliamentary_metric, reverse=True)
            extracted_records = b_candidates[:20]
    except Exception as db_err:
        logger.error(f"Database query or schema integrity error in parliamentary briefing: {db_err}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database schema or query integrity failure during parliamentary briefing extraction: {str(db_err)}"
        )

    # 3. Execute Hybrid RAG Search for context & citations
    rag_result = execute_rag_query(
        db=db,
        query_text=question_text,
        top_k=6,
        subsidiary_filter=effective_sub if effective_sub.upper() not in ["ALL", "ALL CIL"] else None
    )

    evidence_chunks = rag_result.get("evidence_chunks", [])
    
    # 4. Handle Insufficient Evidence Case
    if not extracted_records and not evidence_chunks:
        return ParliamentaryBriefingResponse(
            question=question_text,
            question_type=q_type,
            fiscal_year=effective_fy,
            selected_scope=resolved_selected_scope,
            executive_summary=(
                f"No official document records or extracted evidence were found in the database "
                f"matching target scope '{resolved_selected_scope}' for Fiscal Year {effective_fy}."
            ),
            key_findings=[
                "Insufficient evidence available in ingested repository.",
                f"No indexed documents found for target scope '{scope}'."
            ],
            subsidiary_metrics=[],
            discrepancies=[],
            evidence=[],
            confidence=0.0,
            confidence_rating="INSUFFICIENT_EVIDENCE",
            has_sufficient_evidence=False,
            limitations=[
                f"Zero source documents available in repository for '{scope}'.",
                "Cannot generate synthetic answers without verified source backing."
            ],
            generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        )

    # 5. Format Subsidiary Metrics
    subsidiary_metrics: List[SubsidiaryMetricItem] = []
    for m, doc in extracted_records:
        display_sub = doc.subsidiary or "CIL"
        display_mine = m.mine_name
        # Grounded entity naming: relabel to CIL Corporate ONLY when evidence actually supports corporate context
        is_generic_unattached = (
            m.mine_name.lower() in GENERIC_MINE_PHRASES and
            (not doc.subsidiary or doc.subsidiary.upper() in ["CIL", "CIL HQ", "MINISTRY OF COAL"])
        )
        if is_corporate_query and (is_corporate_context_snippet(m.raw_snippet) or is_generic_unattached):
            display_mine = "CIL Corporate"
            display_sub = "CIL"

        subsidiary_metrics.append(
            SubsidiaryMetricItem(
                mine_name=display_mine,
                subsidiary=display_sub,
                metric_name=m.metric_name,
                numeric_value=float(m.numeric_value or 0.0),
                unit=m.unit,
                standard_value=float(m.standard_value) if m.standard_value is not None else float(m.numeric_value or 0.0),
                standard_unit=m.standard_unit or m.unit or "MT",
                fiscal_year=m.fiscal_year or effective_fy,
                page_number=m.page_number,
                document_filename=doc.filename
            )
        )

    # 6. Filter Cross-Document Discrepancies relevant to question entities, domain & scope
    discrepancies: List[FlaggedDiscrepancyItem] = []
    try:
        conflicts_query = db.query(DataConflict).filter(DataConflict.status.in_(["ACTIVE", "OPEN"]))
        active_conflicts = conflicts_query.order_by(DataConflict.id.desc()).all()
    except Exception as conflict_err:
        logger.error(f"Database conflict query error in parliamentary briefing: {conflict_err}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query error during conflict retrieval: {str(conflict_err)}"
        )

    for c in active_conflicts:
        doc_a_name = c.doc_a.filename if c.doc_a else f"Document #{c.doc_a_id}"
        doc_b_name = c.doc_b.filename if c.doc_b else f"Document #{c.doc_b_id}"
        sub_a = c.doc_a.subsidiary if c.doc_a else "CIL"
        sub_b = c.doc_b.subsidiary if c.doc_b else "CIL"

        # Scope filtering if specific subsidiary requested
        if effective_sub.upper() not in ["ALL", "ALL CIL"] and effective_sub not in [sub_a, sub_b]:
            continue

        # Entity filtering: if specific mine queried, conflict must match target mine / base mine
        if target_mines:
            c_mine = (c.mine_name or "").lower()
            c_base = get_base_mine_name(c_mine).lower()
            mine_matched = False
            for tm in target_mines:
                base_tm = get_base_mine_name(tm).lower()
                if tm.lower() in c_mine or base_tm in c_mine or tm.lower() in c_base or base_tm in c_base:
                    mine_matched = True
                    break
            if not mine_matched:
                continue

        # Metric domain filtering
        if metric_domain:
            c_domain = get_metric_domain(c.metric_name)
            d_key = metric_domain.get("domain_key", "")
            if d_key == "COAL_PRODUCTION" and c_domain != "PRODUCTION":
                continue
            elif d_key == "OVERBURDEN_REMOVAL" and c_domain != "OVERBURDEN":
                continue
            elif d_key == "STRIPPING_RATIO" and c_domain != "OVERBURDEN":
                continue
            elif d_key == "COAL_DESPATCH" and c_domain != "OFFTAKE_DISPATCH":
                continue
            elif d_key == "WASHING_CAPACITY" and c_domain != "CAPACITY":
                continue
            elif d_key == "EXPLORATION_DRILLING" and c_domain not in ["DRILLING", "EXPLORATION"]:
                continue

        # Fiscal year filtering
        if effective_fy and effective_fy.upper() != "ALL":
            if c.fiscal_year and c.fiscal_year != effective_fy:
                continue

        is_seeded = "BCCL_Production_Audit_Q4.pdf" in [doc_a_name, doc_b_name]
        prov_label = "Seeded Mine-Level Discrepancy" if is_seeded else "Verified High-Precision Conflict"
        
        discrepancies.append(
            FlaggedDiscrepancyItem(
                entity=c.mine_name,
                metric_name=c.metric_name,
                fiscal_year=c.fiscal_year or effective_fy,
                doc_a_filename=doc_a_name,
                doc_a_value=float(c.doc_a_value or 0.0),
                doc_b_filename=doc_b_name,
                doc_b_value=float(c.doc_b_value or 0.0),
                unit="MT",
                variance_percentage=float(round(c.discrepancy_pct or 0.0, 2)),
                status="DISCREPANCY DETECTED",
                is_seeded_demo=is_seeded,
                provenance_label=prov_label
            )
        )

    # 7. Format Evidence Lineage Items
    evidence_list: List[BriefingEvidenceItem] = []
    for chunk in evidence_chunks:
        evidence_list.append(
            BriefingEvidenceItem(
                chunk_id=chunk.get("chunk_id"),
                document_id=chunk.get("document_id", 0),
                document_name=chunk.get("filename", "Document.pdf"),
                page_number=chunk.get("page_number", 1),
                chunk_index=chunk.get("chunk_index", 0),
                text_snippet=chunk.get("text", "")[:300],
                rrf_score=round(chunk.get("rrf_score", 0.0), 4),
                subsidiary=scope
            )
        )

    # 8. Synthesize Executive Summary & Question-Specific Key Findings
    rag_answer = rag_result.get("answer", "")
    exec_summary = (
        f"Parliamentary Briefing Note compiled for target scope '{resolved_selected_scope}' ({effective_fy}). "
        f"{rag_answer}"
    )

    key_findings = []
    if target_mines and subsidiary_metrics:
        # Find metric matching target mine
        matching_m = next(
            (m for m in subsidiary_metrics if any(get_base_mine_name(tm).lower() in m.mine_name.lower() for tm in target_mines)),
            subsidiary_metrics[0]
        )
        key_findings.append(
            f"Recorded {matching_m.metric_name} for {matching_m.mine_name} ({matching_m.subsidiary}) in FY {matching_m.fiscal_year}: {matching_m.standard_value:.2f} {matching_m.standard_unit}."
        )
    elif is_corporate_query and subsidiary_metrics:
        # For corporate CIL query, look for a corporate-relevant metric
        corp_m = next(
            (m for m in subsidiary_metrics if m.mine_name == "CIL Corporate" or m.subsidiary == "CIL"),
            None
        )
        if corp_m and corp_m.standard_value > 0:
            key_findings.append(
                f"Recorded {corp_m.metric_name} for {corp_m.mine_name} in FY {corp_m.fiscal_year}: {corp_m.standard_value:.2f} {corp_m.standard_unit}."
            )
        else:
            key_findings.append(
                f"Retrieved {len(subsidiary_metrics)} verified operational metrics across CIL entities for FY {effective_fy}."
            )
    elif subsidiary_metrics:
        # Specific subsidiary query
        sub_m = next(
            (m for m in subsidiary_metrics if m.subsidiary.upper() == effective_sub.upper()),
            subsidiary_metrics[0]
        )
        key_findings.append(
            f"Recorded {sub_m.metric_name} for {sub_m.mine_name} ({sub_m.subsidiary}) in FY {sub_m.fiscal_year}: {sub_m.standard_value:.2f} {sub_m.standard_unit}."
        )

    if len(subsidiary_metrics) > 1:
        if target_mines:
            key_findings.append(f"Identified {len(subsidiary_metrics)} verified operational metrics matching {', '.join(target_mines)}.")
        elif not is_corporate_query and effective_sub.upper() not in ["ALL", "ALL CIL"]:
            key_findings.append(f"Total {len(subsidiary_metrics)} verified operational metrics extracted across official {effective_sub} documents.")
        else:
            key_findings.append(f"Total {len(subsidiary_metrics)} verified operational metrics extracted across official CIL documents.")

    if discrepancies:
        d_first = discrepancies[0]
        key_findings.append(
            f"Discrepancy Flagged: {d_first.entity} ({d_first.metric_name}) variance of {d_first.variance_percentage}% between {d_first.doc_a_filename} and {d_first.doc_b_filename} [{d_first.provenance_label}]."
        )
    else:
        key_findings.append("No active metric discrepancies detected across requested scope documents.")

    # Deterministic explainable confidence calculation
    if not evidence_list:
        confidence_val = 0.0
        confidence_rating = "INSUFFICIENT_EVIDENCE"
    else:
        conf_calc = 0.50
        if len(evidence_list) >= 3:
            conf_calc += 0.10

        # Fiscal year grounding check
        top_ev = evidence_list[0]
        top_text = top_ev.text_snippet.lower()
        if effective_fy and (effective_fy in top_text or effective_fy[-5:] in top_text):
            conf_calc += 0.15

        # Metric domain match check
        if metric_domain:
            canonical_m = metric_domain.get("canonical_name", "").lower()
            d_terms = [t.lower() for t in metric_domain.get("db_metric_names", [])]
            if canonical_m in top_text or any(dt in top_text for dt in d_terms):
                conf_calc += 0.15

        # Scope / Entity match check
        if target_mines:
            if any(tm.lower() in top_text or get_base_mine_name(tm).lower() in top_text for tm in target_mines):
                conf_calc += 0.10
            else:
                conf_calc -= 0.20
        elif is_corporate_query:
            if is_corporate_context_snippet(top_text) or "cil" in top_text or "corporate" in top_text:
                conf_calc += 0.10
            elif any(km.lower() in top_text for km in KNOWN_MINES):
                # Subsidiary mine evidence for corporate query reduces confidence
                conf_calc -= 0.15
        elif effective_sub.upper() not in ["ALL", "ALL CIL"]:
            if effective_sub.lower() in top_text:
                conf_calc += 0.10
            else:
                conf_calc -= 0.15

        # Historical inception contamination penalty
        if is_historical_evidence_snippet(top_text, effective_fy):
            conf_calc -= 0.30

        # Discrepancy penalty
        if discrepancies:
            conf_calc -= 0.10

        # Insufficient evidence penalty in synthesized answer
        if "insufficient" in rag_answer.lower():
            conf_calc = min(conf_calc, 0.40)

        # Clamp between 0.10 and 0.95
        confidence_val = round(max(0.10, min(0.95, conf_calc)), 2)
        confidence_rating = "HIGH" if confidence_val >= 0.85 else ("MEDIUM" if confidence_val >= 0.65 else "LOW")

    limitations = [
        "Analysis relies exclusively on ingested official reports and indexed database metrics.",
        "Deterministic arithmetic validation threshold set at >5.0%; conflict threshold set at >1.0%."
    ]

    return ParliamentaryBriefingResponse(
        question=question_text,
        question_type=q_type,
        fiscal_year=fy,
        selected_scope=resolved_selected_scope,
        executive_summary=exec_summary,
        key_findings=key_findings,
        subsidiary_metrics=subsidiary_metrics,
        discrepancies=discrepancies,
        evidence=evidence_list,
        confidence=confidence_val,
        confidence_rating=confidence_rating,
        has_sufficient_evidence=True,
        limitations=limitations,
        generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    )


@router.post("/parliamentary/export-pdf")
def export_parliamentary_pdf(
    payload: ParliamentaryBriefingResponse,
    current_user: User = Depends(get_current_user)
):
    """
    Generates and streams an official-styled Parliamentary Briefing Note PDF document.
    Disclaims explicitly: "AI-generated evidence-backed Parliamentary Briefing Note (Not an official Ministry issued document)".
    """
    pdf_buffer = io.BytesIO()

    if HAS_REPORTLAB:
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'HeaderTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#20262B'),
            spaceAfter=4
        )
        sub_style = ParagraphStyle(
            'HeaderSub',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#5E6B73'),
            spaceAfter=12
        )
        heading2_style = ParagraphStyle(
            'SectionHead',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#171A1F'),
            spaceBefore=10,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#20262B'),
            leading=13
        )

        story = []

        # Document Header
        story.append(Paragraph("<b>COALINTEL — Parliamentary Briefing Note</b>", title_style))
        story.append(Paragraph("<i>AI-generated evidence-backed Parliamentary Briefing Note (Not an official Ministry issued document)</i>", sub_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CBD3D8'), spaceAfter=10))

        # Metadata Table
        meta_data = [
            ["Question:", payload.question],
            ["Target Scope:", payload.selected_scope],
            ["Fiscal Year:", payload.fiscal_year],
            ["Confidence Rating:", f"{payload.confidence_rating} ({payload.confidence * 100:.0f}%)"],
            ["Generated Timestamp:", payload.generated_at]
        ]
        meta_table = Table(meta_data, colWidths=[120, 400])
        meta_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#20262B')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 10))

        # Executive Summary
        story.append(Paragraph("<b>Executive Summary</b>", heading2_style))
        story.append(Paragraph(payload.executive_summary, body_style))
        story.append(Spacer(1, 10))

        # Key Findings
        story.append(Paragraph("<b>Key Findings & Operational Highlights</b>", heading2_style))
        for finding in payload.key_findings:
            story.append(Paragraph(f"• {finding}", body_style))
        story.append(Spacer(1, 10))

        # Subsidiary Metrics Table
        if payload.subsidiary_metrics:
            story.append(Paragraph("<b>Verified Operational Metrics</b>", heading2_style))
            m_table_data = [["Mine Entity", "Subsidiary", "Metric Name", "Value", "Unit", "FY"]]
            for m in payload.subsidiary_metrics:
                m_table_data.append([
                    m.mine_name,
                    m.subsidiary,
                    m.metric_name,
                    f"{m.standard_value:.2f}",
                    m.standard_unit,
                    m.fiscal_year
                ])
            m_table = Table(m_table_data, colWidths=[100, 70, 150, 60, 50, 60])
            m_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#171A1F')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD3D8')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(m_table)
            story.append(Spacer(1, 10))

        # Discrepancies Section
        if payload.discrepancies:
            story.append(Paragraph("<b>Flagged Cross-Document Discrepancies</b>", heading2_style))
            d_table_data = [["Entity", "Metric", "Doc A (Val)", "Doc B (Val)", "Variance", "Provenance Status"]]
            for d in payload.discrepancies:
                d_table_data.append([
                    d.entity,
                    d.metric_name,
                    f"{d.doc_a_filename} ({d.doc_a_value:.2f})",
                    f"{d.doc_b_filename} ({d.doc_b_value:.2f})",
                    f"{d.variance_percentage}%",
                    d.provenance_label
                ])
            d_table = Table(d_table_data, colWidths=[90, 80, 130, 130, 50, 100])
            d_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#C2413B')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD3D8')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(d_table)
            story.append(Spacer(1, 10))

        # Limitations Footer
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD3D8'), spaceBefore=10, spaceAfter=8))
        story.append(Paragraph("<b>Limitations & System Disclaimers:</b>", body_style))
        for lim in payload.limitations:
            story.append(Paragraph(f"• {lim}", sub_style))

        doc.build(story)
        pdf_bytes = pdf_buffer.getvalue()
    else:
        # Fallback PDF writer if reportlab missing
        text_content = (
            f"%PDF-1.4\nCOALINTEL Parliamentary Briefing Note\n"
            f"Question: {payload.question}\nScope: {payload.selected_scope}\n"
            f"Summary: {payload.executive_summary}\n"
        )
        pdf_bytes = text_content.encode("utf-8")

    filename = f"Parliamentary_Briefing_{payload.selected_scope}_{payload.fiscal_year}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
