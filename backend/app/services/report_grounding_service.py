"""Evidence packet and validation primitives for Step 4D reports.

The packet is intentionally plain data.  It can be persisted in the existing
Report.content_json field and passed to a narrative renderer without making
the renderer a source of facts.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.structured_fact import StructuredFact
from app.services.knowledge_retrieval_service import semantic_search


ACCEPTED_FACT_STATUSES = {"ACCEPTED"}
ACCEPTED_VALIDATION_STATUSES = {"ACCEPTED", "VALIDATED", "CHECK_EXECUTED_PASSED"}


def build_report_spec(*, report_type: str, subsidiary: Optional[str], fiscal_year: Optional[str],
                      title: Optional[str] = None, question: Optional[str] = None,
                      metrics: Optional[list[str]] = None) -> Dict[str, Any]:
    return {
        "report_type": report_type,
        "subsidiary": subsidiary or "ALL CIL",
        "fiscal_year": fiscal_year or "ALL",
        "title": title,
        "question": question,
        "metrics": metrics or [],
    }


def _fact_source(fact: StructuredFact, document: Document) -> Dict[str, Any]:
    return {
        "fact_id": fact.id,
        "document_id": fact.document_id,
        "document_name": document.filename,
        "page_number": fact.page_number,
        "table_id": fact.document_table_id,
        "evidence_type": fact.evidence_type,
        "locator": fact.evidence_locator_json or {},
        "source_url": document.source_url,
        "extraction_method": fact.extraction_method,
        "extraction_confidence": float(fact.extraction_confidence) if fact.extraction_confidence is not None else None,
        "validation_status": fact.validation_status,
        "fact_status": fact.fact_status,
    }


def collect_evidence_packet(db: Session, *, spec: Dict[str, Any], include_semantic: bool = False) -> Dict[str, Any]:
    query = db.query(StructuredFact, Document).join(Document, Document.id == StructuredFact.document_id)
    subsidiary = (spec.get("subsidiary") or "ALL CIL").strip()
    fiscal_year = (spec.get("fiscal_year") or "ALL").strip()
    if subsidiary.upper() not in {"ALL", "ALL CIL", "CIL", "CIL HQ"}:
        query = query.filter(Document.subsidiary == subsidiary)
    if fiscal_year.upper() not in {"ALL", "ALL FISCAL YEARS"}:
        query = query.filter((StructuredFact.period_normalized.ilike(f"%{fiscal_year}%")) |
                             (StructuredFact.period_raw.ilike(f"%{fiscal_year}%")) |
                             (Document.fiscal_year == fiscal_year))
    metrics = [item.strip() for item in (spec.get("metrics") or []) if item and item.strip()]
    if metrics:
        metric_filter = None
        for metric in metrics:
            condition = StructuredFact.metric_type.ilike(f"%{metric}%") | StructuredFact.metric_name_canonical.ilike(f"%{metric}%") | StructuredFact.metric_name_raw.ilike(f"%{metric}%")
            metric_filter = condition if metric_filter is None else metric_filter | condition
        query = query.filter(metric_filter)
    facts = query.order_by(StructuredFact.id).limit(500).all()
    structured = []
    for fact, document in facts:
        value = fact.normalized_value if fact.normalized_value is not None else fact.raw_value_numeric
        structured.append({
            "fact_id": fact.id,
            "entity": fact.entity_name_canonical or fact.entity_name_raw,
            "metric": fact.metric_name_canonical or fact.metric_name_raw or fact.metric_type,
            "value": float(value) if value is not None else None,
            "raw_value": fact.raw_value_text,
            "unit": fact.normalized_unit or fact.raw_unit,
            "period": fact.period_normalized or fact.period_raw,
            "validation_status": fact.validation_status,
            "fact_status": fact.fact_status,
            "source": _fact_source(fact, document),
        })
    semantic = {"status": "NOT_REQUESTED", "results": []}
    if include_semantic and spec.get("question"):
        semantic = semantic_search(db, spec["question"], top_k=8)
    return {"spec": spec, "structured_facts": structured, "semantic_chunks": semantic.get("results", []),
            "semantic_status": semantic.get("status", "NOT_REQUESTED")}


def validate_evidence_packet(packet: Dict[str, Any]) -> Dict[str, Any]:
    facts = packet.get("structured_facts", [])
    semantic = packet.get("semantic_chunks", [])
    if not facts and not semantic:
        return {"state": "INSUFFICIENT_EVIDENCE", "warnings": ["No persisted evidence matched the report specification."]}
    warnings = []
    has_unverified = any(item.get("fact_status") not in ACCEPTED_FACT_STATUSES or item.get("validation_status") not in ACCEPTED_VALIDATION_STATUSES for item in facts)
    identity = {}
    conflicts = []
    for fact in facts:
        key = (fact.get("entity"), fact.get("metric"), fact.get("period"), fact.get("unit"))
        if key in identity and identity[key].get("value") != fact.get("value"):
            conflicts.append({"key": key, "facts": [identity[key], fact]})
        else:
            identity[key] = fact
    if has_unverified:
        warnings.append("Some structured facts are candidate or review-required evidence.")
    if conflicts:
        warnings.append("Contradictory structured facts were preserved and not averaged.")
    if conflicts or has_unverified:
        state = "REVIEW_REQUIRED"
    else:
        state = "SUPPORTED_WITH_WARNINGS" if warnings else "SUPPORTED"
    return {"state": state, "warnings": warnings, "conflicts": conflicts,
            "structured_fact_count": len(facts), "semantic_chunk_count": len(semantic)}


def packet_fingerprint(packet: Dict[str, Any]) -> str:
    import json
    return hashlib.sha256(json.dumps(packet, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def deterministic_narrative(packet: Dict[str, Any], validation: Dict[str, Any]) -> Dict[str, Any]:
    facts = packet.get("structured_facts", [])
    if not facts:
        summary = "No supported structured facts were found for this report specification."
    else:
        summary = f"The report contains {len(facts)} persisted structured fact(s)."
        if validation["state"] == "REVIEW_REQUIRED":
            summary += " Candidate, review-required, or conflicting evidence is labelled for review."
    return {"executive_summary": summary, "narrative_provider": "DETERMINISTIC_EVIDENCE_ONLY",
            "claims": [{"text": summary, "fact_ids": [fact["fact_id"] for fact in facts]}]}
