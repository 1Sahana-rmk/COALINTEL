"""Step 4A query analysis, evidence retrieval, and grounded answer orchestration.

This layer deliberately keeps query policy separate from the LLM.  Structured
facts and pgvector chunks are retrieved first; the language model receives only
the resulting evidence packet and cannot create evidence or authoritative
numeric facts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.services.hybrid_search_service import detect_query_entities
from app.services.knowledge_retrieval_service import hybrid_search, search_structured_facts, semantic_search
from app.services.llm_provider import DegradedLLMProvider, get_llm_provider
from app.services.rag_service import build_isolated_prompt, extract_and_validate_citations


ROUTES = {"STRUCTURED", "SEMANTIC", "HYBRID"}
STRUCTURED_TERMS = (
    "how much", "what was", "what is the", "value", "amount", "figure",
    "production", "dispatch", "despatch", "overburden", "obr", "target",
    "achievement", "variance", "reserve", "resource", "thickness", "depth",
    "stripping ratio", "growth", "percentage", "%",
)
SEMANTIC_TERMS = (
    "explain", "describe", "summary", "summarize", "what is the policy",
    "why", "how does", "overview", "observation", "trend", "context",
)
HYBRID_TERMS = (
    "compare", "comparison", "versus", " vs ", "difference", "why did",
    "explain the production", "summarize the figures", "context for",
)
# Exact threshold should be calibrated with a labelled retrieval set in the
# next acceptance pass; below it, the assistant must not claim support.
SEMANTIC_MIN_SCORE = 0.20


def _has_step3_tables(db: Session) -> bool:
    try:
        bind = db.get_bind()
        return bind.dialect.name == "postgresql" and "knowledge_chunks" in inspect(bind).get_table_names()
    except Exception:
        return False


def _period_filter(query: str, entities: Dict[str, Any]) -> Optional[str]:
    fiscal_year = entities.get("fiscal_year")
    if fiscal_year:
        return fiscal_year
    scope = entities.get("temporal_scope") or {}
    periods = scope.get("periods") or []
    if periods:
        return periods[0].get("raw")
    return None


def analyze_query(query_text: str) -> Dict[str, Any]:
    """Deterministically classify a user question and extract retrieval filters."""
    text = (query_text or "").strip()
    lower = text.lower()
    entities = detect_query_entities(text) if text else {}
    has_metric = bool(entities.get("metric") or entities.get("metric_domain"))
    has_period = bool(_period_filter(text, entities))
    has_entity = bool(entities.get("mines") or entities.get("subsidiary") or entities.get("is_corporate_query"))
    asks_explanation = any(term in lower for term in SEMANTIC_TERMS) or "policy" in lower
    asks_exact = bool(
        has_metric
        and not asks_explanation
        and (has_period or has_entity or any(term in lower for term in STRUCTURED_TERMS))
    )
    is_hybrid = any(term in lower for term in HYBRID_TERMS) or (
        has_metric and has_entity and any(term in lower for term in SEMANTIC_TERMS)
    )
    is_semantic = any(term in lower for term in SEMANTIC_TERMS) and not asks_exact

    if is_hybrid:
        route = "HYBRID"
    elif asks_exact:
        route = "STRUCTURED"
    elif is_semantic:
        route = "SEMANTIC"
    else:
        # Ambiguous mining/document questions are safer with contextual
        # retrieval than with unrestricted general-model generation.
        route = "SEMANTIC" if text else "STRUCTURED"

    metric_domain = entities.get("metric_domain") or {}
    metric = entities.get("metric")
    if metric_domain:
        metric = metric_domain.get("canonical_name") or metric

    return {
        "route": route,
        "query": text,
        "filters": {
            "entity": (entities.get("mines") or [None])[0],
            "subsidiary": entities.get("subsidiary"),
            "metric": metric,
            "period": _period_filter(text, entities),
        },
        "entities": entities,
        "signals": {
            "has_metric": has_metric,
            "has_period": has_period,
            "has_entity": has_entity,
            "asks_exact": asks_exact,
        },
    }


def _source_reference(item: Dict[str, Any], filename: Optional[str] = None) -> Dict[str, Any]:
    return {
        "document_id": item.get("document_id"),
        "filename": filename or item.get("filename"),
        "source_url": item.get("source_url"),
        "source_type": item.get("source_type"),
        "file_type": item.get("file_type"),
        "page_number": item.get("page_number"),
        "page_id": item.get("page_id"),
        "table_id": item.get("table_id"),
        "evidence_type": item.get("evidence_type") or item.get("chunk_type"),
        "locator": item.get("evidence_locator") or item.get("source_locator") or {},
        "excerpt": item.get("text") or item.get("raw_value_text"),
        "extraction_method": item.get("extraction_method"),
        "confidence": item.get("extraction_confidence"),
        "validation_state": item.get("validation_status") or item.get("fact_status"),
    }


def _fact_conflict_groups(facts: Iterable[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    groups: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = {}
    for fact in facts:
        entity = fact.get("entity") or {}
        metric = fact.get("metric") or {}
        period = fact.get("period") or {}
        value = fact.get("value") or {}
        key = (
            entity.get("canonical") or entity.get("raw"),
            metric.get("canonical") or metric.get("raw"),
            period.get("normalized") or period.get("raw"),
            value.get("normalized_unit") or value.get("raw_unit"),
        )
        groups.setdefault(key, []).append(fact)
    return [rows for rows in groups.values() if len({(r.get("value") or {}).get("normalized") for r in rows}) > 1]


def _conflict_states(db: Session, groups: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Attach existing persisted conflict status when a legacy conflict matches."""
    if not groups:
        return []
    try:
        from app.models.data_conflict import DataConflict

        states = []
        for group in groups:
            first = group[0]
            entity = (first.get("entity") or {}).get("canonical") or (first.get("entity") or {}).get("raw")
            metric = (first.get("metric") or {}).get("canonical") or (first.get("metric") or {}).get("raw")
            period = (first.get("period") or {}).get("normalized") or (first.get("period") or {}).get("raw")
            doc_ids = {fact.get("document_id") for fact in group if fact.get("document_id") is not None}
            query = db.query(DataConflict).filter(DataConflict.metric_name.ilike(f"%{metric or ''}%"))
            if entity:
                query = query.filter(DataConflict.mine_name.ilike(f"%{entity}%"))
            if period:
                query = query.filter(DataConflict.fiscal_year.ilike(f"%{period}%"))
            records = query.all()
            if doc_ids:
                records = [record for record in records if {record.doc_a_id, record.doc_b_id} & doc_ids]
            states.append({
                "status": "RESOLVED" if records and all((record.status or "OPEN").upper() == "RESOLVED" for record in records) else "UNRESOLVED",
                "conflict_ids": [record.id for record in records],
                "candidate_count": len(group),
            })
        return states
    except Exception:
        return [{"status": "UNRESOLVED", "conflict_ids": [], "candidate_count": len(group)} for group in groups]


def _citation_from_reference(ref: Dict[str, Any]) -> Dict[str, Any]:
    page = ref.get("page_number") or 1
    filename = ref.get("filename") or "Document"
    return {
        "document_name": filename,
        "document_id": ref.get("document_id"),
        "page_number": page,
        "citation_tag": f"[{filename}, Page {page}]",
        "evidence_type": ref.get("evidence_type"),
        "table_id": ref.get("table_id"),
        "locator": ref.get("locator") or {},
        "source_url": ref.get("source_url"),
        "source_type": ref.get("source_type"),
        "excerpt": ref.get("excerpt"),
        "extraction_method": ref.get("extraction_method"),
        "confidence": ref.get("confidence"),
        "validation_state": ref.get("validation_state"),
    }


def _fact_answer(facts: List[Dict[str, Any]], query: str, conflicts: List[List[Dict[str, Any]]]) -> str:
    if not facts:
        return "Insufficient evidence in the indexed documents for this structured question."
    lines = ["Structured facts supported by indexed evidence:"]
    for fact in facts[:50]:
        entity = fact.get("entity") or {}
        metric = fact.get("metric") or {}
        value = fact.get("value") or {}
        period = fact.get("period") or {}
        label = entity.get("canonical") or entity.get("raw") or "Entity unavailable"
        metric_label = metric.get("canonical") or metric.get("raw") or "Metric unavailable"
        amount = value.get("raw") or value.get("normalized")
        unit = value.get("raw_unit") or value.get("normalized_unit") or ""
        source = _source_reference(fact)
        citation = f"[{source.get('filename') or 'Document'}, Page {source.get('page_number') or 1}]"
        period_label = period.get("raw") or period.get("normalized") or "period unavailable"
        lines.append(f"- {label}: {metric_label} = {amount} {unit} ({period_label}) {citation}")
    if conflicts:
        lines.append("\nConflicting supported candidates were found; no value was selected silently.")
    return "\n".join(lines)


def _structured_claims(facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    claims = []
    for index, fact in enumerate(facts[:50], start=1):
        ref = _source_reference(fact)
        claims.append({
            "claim_id": f"fact-{fact.get('fact_id') or index}",
            "claim_type": "STRUCTURED_FACT",
            "text": f"{(fact.get('entity') or {}).get('canonical') or (fact.get('entity') or {}).get('raw') or 'Entity'} "
                     f"{(fact.get('metric') or {}).get('canonical') or (fact.get('metric') or {}).get('raw') or 'metric'} "
                     f"{(fact.get('value') or {}).get('raw') or (fact.get('value') or {}).get('normalized')}",
            "evidence": [ref],
        })
    return claims


def _semantic_items_with_filenames(db: Session, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not items:
        return []
    from app.models.document import Document

    ids = {item.get("document_id") for item in items if item.get("document_id") is not None}
    names = {doc.id: doc.filename for doc in db.query(Document).filter(Document.id.in_(ids)).all()} if ids else {}
    metadata = {doc.id: {"source_url": doc.source_url, "source_type": doc.source_type, "file_type": doc.file_type} for doc in db.query(Document).filter(Document.id.in_(ids)).all()} if ids else {}
    result = []
    for item in items:
        enriched = dict(item)
        enriched["filename"] = names.get(item.get("document_id"), item.get("filename") or "Document")
        enriched.update(metadata.get(item.get("document_id"), {}))
        enriched["rrf_score"] = item.get("retrieval_score") or 0.0
        enriched["vector_score"] = item.get("retrieval_score") or 0.0
        if enriched["vector_score"] >= SEMANTIC_MIN_SCORE:
            result.append(enriched)
    return result


def _structured_items_with_filenames(db: Session, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not items:
        return []
    from app.models.document import Document

    ids = {item.get("document_id") for item in items if item.get("document_id") is not None}
    names = {doc.id: doc.filename for doc in db.query(Document).filter(Document.id.in_(ids)).all()} if ids else {}
    metadata = {doc.id: {"source_url": doc.source_url, "source_type": doc.source_type, "file_type": doc.file_type} for doc in db.query(Document).filter(Document.id.in_(ids)).all()} if ids else {}
    result = []
    for item in items:
        enriched = dict(item)
        enriched["filename"] = names.get(item.get("document_id"), "Document")
        enriched.update(metadata.get(item.get("document_id"), {}))
        result.append(enriched)
    return result


def _semantic_answer(query: str, evidence: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]], str, bool, List[Dict[str, Any]]]:
    legacy_chunks = [
        {
            "filename": item.get("filename", "Document"),
            "page_number": item.get("page_number") or 1,
            "text": item.get("text") or "",
            "document_id": item.get("document_id"),
            "chunk_id": item.get("chunk_id"),
            "rrf_score": item.get("rrf_score", 0.0),
            "vector_score": item.get("vector_score", 0.0),
            "keyword_score": 0.0,
        }
        for item in evidence
    ]
    prompt = build_isolated_prompt(query, legacy_chunks)
    provider = get_llm_provider()
    degraded = isinstance(provider, DegradedLLMProvider) or getattr(provider, "provider_name", "") == "degraded"
    try:
        raw = provider.generate(prompt)
    except Exception:
        return "LLM answer generation is unavailable; retrieved evidence is available for inspection.", [], "UNAVAILABLE", True, []
    citations, passed = extract_and_validate_citations(raw, legacy_chunks, query_text=query)
    if not passed or not citations:
        return "Insufficient grounded evidence found for this query.", [], "UNSUPPORTED", degraded, []
    claim = {
        "claim_id": "answer-1",
        "claim_type": "SEMANTIC_SYNTHESIS",
        "text": raw.strip(),
        "evidence": [],
    }
    for citation in citations:
        for item in evidence:
            if item.get("filename", "").lower() == citation["document_name"].lower() and item.get("page_number") == citation["page_number"]:
                claim["evidence"].append(_source_reference(item))
                break
    return raw.strip(), citations, "SUPPORTED", degraded, [claim]


def execute_assistant_query(
    db: Session,
    query_text: str,
    *,
    top_k: int = 5,
    subsidiary_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """Run Step 4A route analysis and evidence-first answer generation."""
    analysis = analyze_query(query_text)
    route = analysis["route"]
    filters = dict(analysis["filters"])
    if subsidiary_filter and not filters.get("subsidiary"):
        filters["subsidiary"] = subsidiary_filter

    empty_packet: Dict[str, Any] = {
        "route": route,
        "structured_facts": [],
        "semantic_evidence": [],
        "conflicts": [],
        "conflict_states": [],
        "claims": [],
        "source_references": [],
    }

    if not _has_step3_tables(db):
        return {
            "query": query_text,
            "answer": "Step 3 knowledge retrieval is not available in this database.",
            "citations": [],
            "evidence_chunks": [],
            "provider": "step4a",
            "degraded_mode": True,
            "mode": "INSUFFICIENT_EVIDENCE",
            "support_state": "UNAVAILABLE",
            "generation_status": "KNOWLEDGE_STORE_UNAVAILABLE",
            **empty_packet,
            "analysis": analysis,
        }

    structured: Dict[str, Any] = {"status": "NOT_REQUESTED", "results": [], "count": 0}
    semantic: Dict[str, Any] = {"status": "NOT_REQUESTED", "results": [], "count": 0}
    if route in {"STRUCTURED", "HYBRID"}:
        structured = search_structured_facts(db, **filters, limit=max(1, min(top_k * 10, 100)))
    if route in {"SEMANTIC", "HYBRID"}:
        semantic = semantic_search(db, query_text, top_k=top_k, subsidiary=filters.get("subsidiary"))

    facts = _structured_items_with_filenames(db, structured.get("results", []))
    semantic_items = _semantic_items_with_filenames(db, semantic.get("results", []))
    conflicts = _fact_conflict_groups(facts)
    conflict_states = _conflict_states(db, conflicts)
    claims = _structured_claims(facts)
    packet = {
        "route": route,
        "structured_facts": facts,
        "semantic_evidence": semantic_items,
        "conflicts": conflicts,
        "conflict_states": conflict_states,
        "claims": claims,
        "source_references": [_source_reference(fact) for fact in facts]
        + [_source_reference(item) for item in semantic_items],
    }

    if route == "STRUCTURED":
        answer = _fact_answer(facts, query_text, conflicts)
        supported = "SUPPORTED" if facts else "UNSUPPORTED"
        return {
            "query": query_text, "answer": answer, "citations": [_citation_from_reference(ref) for ref in packet["source_references"][:50]],
            "evidence_chunks": [], "provider": "structured_facts", "degraded_mode": False,
            "mode": "EVIDENCE_GROUNDED" if facts else "INSUFFICIENT_EVIDENCE",
            "support_state": "CONFLICTING" if conflicts else supported,
            "generation_status": "NOT_REQUIRED", "analysis": analysis, **packet,
        }

    if route == "HYBRID" and not facts and semantic.get("status") != "OK":
        return {
            "query": query_text, "answer": "Insufficient evidence in the indexed documents for this hybrid question.",
            "citations": [], "evidence_chunks": [], "provider": "none", "degraded_mode": semantic.get("status") != "OK",
            "mode": "INSUFFICIENT_EVIDENCE", "support_state": "UNSUPPORTED",
            "generation_status": semantic.get("status", "UNAVAILABLE"), "analysis": analysis, **packet,
        }

    if semantic.get("status") != "OK" or not semantic_items:
        return {
            "query": query_text, "answer": "Semantic evidence retrieval is currently unavailable or returned no supported evidence.",
            "citations": [], "evidence_chunks": [], "provider": "none", "degraded_mode": True,
            "mode": "INSUFFICIENT_EVIDENCE", "support_state": "UNSUPPORTED",
            "generation_status": semantic.get("status", "UNAVAILABLE"), "analysis": analysis, **packet,
        }

    answer, citations, support_state, degraded, llm_claims = _semantic_answer(query_text, semantic_items)
    packet["claims"] = llm_claims
    normalized_citations = []
    for citation in citations:
        matching = next((ref for ref in packet["source_references"] if ref.get("filename", "").lower() == citation["document_name"].lower() and ref.get("page_number") == citation["page_number"]), None)
        normalized_citations.append(_citation_from_reference(matching) if matching else citation)
    return {
        "query": query_text, "answer": answer, "citations": normalized_citations,
        "evidence_chunks": semantic_items, "provider": "degraded" if degraded else "llm",
        "degraded_mode": degraded, "mode": "EVIDENCE_GROUNDED" if citations else "INSUFFICIENT_EVIDENCE",
        "support_state": support_state, "generation_status": "DEGRADED" if degraded else "READY",
        "analysis": analysis, **packet,
    }
