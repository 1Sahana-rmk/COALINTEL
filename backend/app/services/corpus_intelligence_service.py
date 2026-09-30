"""Deterministic corpus topics and historical intelligence.

This module deliberately uses persisted COALINTEL content only.  It does not
call an LLM, create embeddings, or invent domain terms.  The bounded term/topic
analysis is intentionally lightweight so dashboard requests do not require a
new ML runtime.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter, defaultdict
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.extracted_metric import ExtractedMetric
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.structured_fact import StructuredFact


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "in", "into", "is", "it", "of", "on", "or", "that", "the", "their",
    "this", "to", "was", "were", "with", "which", "during", "has", "have",
    "had", "also", "than", "not", "our", "its", "all", "up", "per", "over",
}
NOISE_TERMS = {
    "page", "pages", "table", "tables", "figure", "fig", "contents", "content",
    "index", "serial", "number", "numbers", "sl", "sr", "no", "sno", "item",
    "items", "annexure", "chapter", "section", "report", "source", "total",
    "value", "values", "unit", "units", "entity", "entities", "metric", "metrics",
    "period", "periods", "comment", "comments", "expected", "behaviour", "behavior",
    "acceptance", "identifier", "identifiers", "test", "should", "blank", "cell",
    "cells", "header", "headers", "document", "documents", "coalintel", "docx",
}
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:[-/][A-Za-z0-9]+)*")


def _canonical_token(token: str) -> str:
    token = token.casefold().strip("-_")
    if len(token) > 4 and token.endswith("ies"):
        token = token[:-3] + "y"
    elif len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        token = token[:-1]
    return token


def _usable_tokens(text: str) -> List[str]:
    tokens: List[str] = []
    for raw in TOKEN_RE.findall(text or ""):
        token = _canonical_token(raw)
        if len(token) < 3 or token in STOPWORDS or token in NOISE_TERMS or token.isdigit():
            continue
        if not any(character.isalpha() for character in token):
            continue
        tokens.append(token)
    return tokens


def _source_ref(document_id: int, page_number: Optional[int], *, chunk_id: Optional[int] = None,
                chunk_type: Optional[str] = None, locator: Optional[dict] = None,
                document: Optional[Document] = None) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "document_id": document_id,
        "page_number": page_number,
        "chunk_id": chunk_id,
        "chunk_type": chunk_type,
        "locator": locator or {},
    }
    if document is not None:
        result.update({
            "document_title": document.title or document.filename,
            "filename": document.filename,
            "source_url": document.source_url,
        })
    return result


def _corpus_rows(db: Session, *, subsidiary: Optional[str] = None,
                 document_id: Optional[int] = None,
                 period: Optional[str] = None,
                 limit: int = 10000) -> List[Dict[str, Any]]:
    """Load a bounded corpus from indexed chunks, falling back to persisted metrics."""
    limit = max(1, min(int(limit), 10000))
    query = db.query(KnowledgeChunk, Document).join(Document, Document.id == KnowledgeChunk.document_id)
    if subsidiary and subsidiary.upper() not in {"ALL", "ALL CIL"}:
        query = query.filter(Document.subsidiary == subsidiary)
    if document_id is not None:
        query = query.filter(KnowledgeChunk.document_id == document_id)
    if period:
        query = query.filter((Document.fiscal_year == period) | (Document.reporting_period == period))
    chunks = query.order_by(KnowledgeChunk.id).limit(limit).all()
    if chunks:
        return [{
            "text": chunk.chunk_text or "",
            "document_id": chunk.document_id,
            "page_number": chunk.page_number,
            "chunk_id": chunk.id,
            "chunk_type": chunk.chunk_type,
            "locator": chunk.source_locator_json or {},
            "document": document,
        } for chunk, document in chunks if chunk.chunk_text]

    # A document can be persisted before Step 3 indexing.  Metric names and
    # mine labels are still real corpus content, so expose them honestly rather
    # than falling back to a fabricated topic list.
    metric_query = db.query(ExtractedMetric, Document).join(Document, Document.id == ExtractedMetric.document_id)
    if subsidiary and subsidiary.upper() not in {"ALL", "ALL CIL"}:
        metric_query = metric_query.filter(Document.subsidiary == subsidiary)
    if document_id is not None:
        metric_query = metric_query.filter(ExtractedMetric.document_id == document_id)
    if period:
        metric_query = metric_query.filter((ExtractedMetric.fiscal_year == period) | (Document.reporting_period == period))
    metrics = metric_query.order_by(ExtractedMetric.id).limit(limit).all()
    return [{
        "text": " ".join(value for value in [metric.metric_name, metric.mine_name, metric.unit] if value),
        "document_id": metric.document_id,
        "page_number": None,
        "chunk_id": None,
        "chunk_type": "EXTRACTED_METRIC",
        "locator": {"extracted_metric_id": metric.id, "metric_name": metric.metric_name},
        "document": document,
    } for metric, document in metrics]


def word_cloud(db: Session, *, subsidiary: Optional[str] = None,
               document_id: Optional[int] = None, period: Optional[str] = None,
               top_n: int = 50) -> Dict[str, Any]:
    rows = _corpus_rows(db, subsidiary=subsidiary, document_id=document_id, period=period)
    occurrences: Counter[str] = Counter()
    documents: defaultdict[str, set[int]] = defaultdict(set)
    # Preserve meaningful persisted multi-word metric names as phrases.
    phrases: Counter[str] = Counter()
    for row in rows:
        tokens = _usable_tokens(row["text"])
        occurrences.update(tokens)
        for token in set(tokens):
            documents[token].add(row["document_id"])
        metric_name = row["locator"].get("metric_name") if isinstance(row["locator"], dict) else None
        if metric_name and len(_usable_tokens(metric_name)) > 1:
            phrases[metric_name.strip()] += 1
    for phrase, count in phrases.items():
        occurrences[phrase] += count
        documents[phrase].update(row["document_id"] for row in rows if phrase.casefold() in row["text"].casefold())
    top_n = max(1, min(int(top_n), 200))
    items = []
    for term, count in occurrences.most_common(top_n):
        items.append({
            "word": term,
            "weight": int(count),
            "occurrence_count": int(count),
            "document_count": len(documents[term]),
            "score": float(count),
            "category": "Corpus-derived",
        })
    return {"status": "OK" if rows else "EMPTY", "topics": items,
            "corpus_items": len(rows), "method": "persisted_content_frequency"}


def topics(db: Session, *, subsidiary: Optional[str] = None,
           document_id: Optional[int] = None, period: Optional[str] = None,
           top_n: int = 12) -> Dict[str, Any]:
    rows = _corpus_rows(db, subsidiary=subsidiary, document_id=document_id, period=period)
    if not rows:
        return {"status": "EMPTY", "topics": [], "method": "deterministic_cooccurrence"}
    term_docs: defaultdict[str, set[int]] = defaultdict(set)
    pair_counts: Counter[Tuple[str, str]] = Counter()
    for row in rows:
        terms = sorted(set(_usable_tokens(row["text"])))
        for term in terms:
            term_docs[term].add(row["document_id"])
        for left_index, left in enumerate(terms):
            for right in terms[left_index + 1:]:
                pair_counts[(left, right)] += 1
    ranked = [term for term, docs in sorted(term_docs.items(), key=lambda item: (-len(item[1]), item[0])) if len(term) >= 3]
    used: set[frozenset[str]] = set()
    result = []
    for seed in ranked[: max(1, min(top_n * 3, 60))]:
        related = [term for term in ranked if term != seed and pair_counts.get(tuple(sorted((seed, term))), 0)]
        terms = [seed] + related[:4]
        signature = frozenset(terms)
        if signature in used:
            continue
        used.add(signature)
        supporting = [row for row in rows if seed in _usable_tokens(row["text"])]
        evidence = [_source_ref(row["document_id"], row["page_number"], chunk_id=row["chunk_id"],
                                chunk_type=row["chunk_type"], locator=row["locator"], document=row["document"])
                    for row in supporting[:10]]
        topic_id = "topic-" + hashlib.sha256("|".join(sorted(terms)).encode("utf-8")).hexdigest()[:12]
        result.append({"topic_id": topic_id, "name": " / ".join(term.replace("-", " ").title() for term in terms[:3]),
                       "representative_terms": terms, "chunk_count": len(supporting),
                       "document_count": len({row["document_id"] for row in supporting}), "score": len(supporting),
                       "evidence": evidence})
        if len(result) >= top_n:
            break
    return {"status": "OK", "topics": result, "method": "deterministic_cooccurrence", "corpus_items": len(rows)}


def _fact_value(fact: StructuredFact) -> Optional[float]:
    value = fact.normalized_value if fact.normalized_value is not None else fact.raw_value_numeric
    return float(value) if value is not None else None


def _fact_ref(fact: StructuredFact, document: Optional[Document]) -> Dict[str, Any]:
    return _source_ref(fact.document_id, fact.page_number, locator=fact.evidence_locator_json or {}, document=document) | {
        "fact_id": fact.id, "table_id": fact.document_table_id, "evidence_type": fact.evidence_type,
        "validation_status": fact.validation_status,
    }


def trend_series(db: Session, *, metric: str, entity: Optional[str] = None,
                 subsidiary: Optional[str] = None, period: Optional[str] = None,
                 limit: int = 500) -> Dict[str, Any]:
    query = db.query(StructuredFact, Document).join(Document, Document.id == StructuredFact.document_id)
    query = query.filter((StructuredFact.metric_name_canonical.ilike(f"%{metric}%")) |
                         (StructuredFact.metric_type.ilike(f"%{metric}%")) |
                         (StructuredFact.metric_name_raw.ilike(f"%{metric}%")))
    if entity:
        query = query.filter((StructuredFact.entity_name_canonical.ilike(f"%{entity}%")) |
                             (StructuredFact.entity_name_raw.ilike(f"%{entity}%")))
    if subsidiary and subsidiary.upper() not in {"ALL", "ALL CIL"}:
        query = query.filter(Document.subsidiary == subsidiary)
    if period:
        query = query.filter((StructuredFact.period_normalized == period) | (StructuredFact.period_raw == period))
    # Pending candidates remain visible as UNVERIFIED observations for audit,
    # but only accepted facts receive status OK and participate in derived
    # comparisons.  This prevents a trend view from hiding the corpus while
    # also preventing unvalidated values from becoming authoritative.
    facts = query.order_by(StructuredFact.id).limit(max(1, min(limit, 1000))).all()
    groups: defaultdict[Tuple[str, str, str], list[Tuple[StructuredFact, Document, Optional[float]]]] = defaultdict(list)
    for fact, document in facts:
        if fact.fact_status == "REJECTED" or _fact_value(fact) is None:
            continue
        key = (fact.entity_name_canonical or fact.entity_name_raw or "UNSPECIFIED",
               fact.period_normalized or fact.period_raw or "UNSPECIFIED",
               fact.normalized_unit or fact.raw_unit or "UNSPECIFIED")
        groups[key].append((fact, document, _fact_value(fact)))
    points = []
    for (entity_name, period_name, unit), candidates in sorted(groups.items(), key=lambda item: item[0][1]):
        values = {candidate[2] for candidate in candidates}
        accepted = all(candidate[0].fact_status == "ACCEPTED" and candidate[0].validation_status == "ACCEPTED"
                       for candidate in candidates)
        status = "CONFLICTING" if len(values) > 1 else ("OK" if accepted else "UNVERIFIED")
        points.append({"entity": entity_name, "period": period_name, "unit": unit, "value": next(iter(values)) if len(values) == 1 else None,
                      "status": status, "validation_states": [candidate[0].validation_status for candidate in candidates],
                      "fact_ids": [candidate[0].id for candidate in candidates],
                      "candidates": [{"value": candidate[2], "fact_id": candidate[0].id, "source": _fact_ref(candidate[0], candidate[1])} for candidate in candidates],
                      "source": _fact_ref(candidates[0][0], candidates[0][1])})
    return {"status": "OK" if points else "EMPTY", "metric": metric, "points": points,
            "count": len(points), "all_years_not_summed": True}


def historical_comparison(db: Session, *, metric: str, entity: Optional[str] = None,
                          comparison_entity: Optional[str] = None,
                          period: Optional[str] = None, subsidiary: Optional[str] = None) -> Dict[str, Any]:
    series = trend_series(db, metric=metric, entity=entity, period=period, subsidiary=subsidiary)
    if comparison_entity:
        other = trend_series(db, metric=metric, entity=comparison_entity, period=period, subsidiary=subsidiary)
        comparable = [item for item in series["points"] for candidate in other["points"]
                      if item["period"] == candidate["period"] and item["unit"] == candidate["unit"]
                      and item["status"] == candidate["status"] == "OK" and item["value"] is not None and candidate["value"] is not None]
        if not comparable:
            return {"status": "UNAVAILABLE", "reason": "No comparable validated observations with matching period and unit.",
                    "observations": [], "provenance_fact_ids": []}
        results = []
        for item in comparable:
            match = next(candidate for candidate in other["points"] if candidate["period"] == item["period"] and candidate["unit"] == item["unit"])
            delta = match["value"] - item["value"]
            results.append({"period": item["period"], "unit": item["unit"], "left_value": item["value"], "right_value": match["value"],
                            "absolute_change": delta, "percentage_change": None if item["value"] == 0 else delta / item["value"] * 100,
                            "fact_ids": item["fact_ids"] + match["fact_ids"]})
        return {"status": "OK", "observations": results, "provenance_fact_ids": [fact_id for item in results for fact_id in item["fact_ids"]]}
    return {"status": series["status"], "observations": series["points"], "all_years_not_summed": True,
            "provenance_fact_ids": [fact_id for point in series["points"] for fact_id in point["fact_ids"]]}
