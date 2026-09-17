import re
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.extracted_metric import ExtractedMetric
from app.models.document import Document
from app.services.vector_store_service import search_vector_store
from app.services.keyword_search_service import search_keyword_store
from app.services.normalization_service import (
    KNOWN_MINES,
    SUBSIDIARIES,
    GENERIC_MINE_PHRASES,
    normalize_subsidiary_scope,
    detect_query_metric_domain,
    get_base_mine_name,
    detect_query_fiscal_year,
    classify_document_authority,
    is_historical_evidence_snippet,
    is_corporate_context_snippet,
)

logger = logging.getLogger(__name__)

RRF_K_CONSTANT = 60  # Frozen RRF Constant k=60
OPERATING_SUBSIDIARIES = ["ECL", "BCCL", "CCL", "WCL", "SECL", "NCL", "MCL", "NEC"]


CALENDAR_MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"
]
MONTH_ABBREVIATIONS = [
    "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec"
]
MINING_UNIT_TOKENS = {
    "cu", "cum", "mcum", "m.cu.m.", "m.cu.m", "mt", "mtpa", "lcum", "lakh", "million",
    "tonnes", "tons", "tonne", "crore", "cr", "cr.", "m", "ocp"
}
REPORT_KEYWORDS = {
    "document", "documents", "report", "reports", "ingested", "source", "sources", "official",
    "figures", "figure", "table", "tables", "projects", "project", "mines", "mine",
    "subsidiary", "subsidiaries", "highest", "lowest", "exceeding", "between", "page", "number",
    "numbers", "data", "statistics", "statistical", "all", "each", "every", "target", "achievement"
}


def detect_query_temporal_scope(query_text: str) -> Dict[str, Any]:
    """
    Extracts month names, calendar years, and comparative period pairs.
    e.g. 'March 2025' -> primary_month='March', primary_year='2025'
         'between November 2024 and March 2025' -> periods=[{'month': 'November', 'year': '2024'}, {'month': 'March', 'year': '2025'}]
    """
    q_clean = query_text.strip()
    month_year_pattern = re.compile(
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[’']?\s*(20\d{2})\b",
        re.IGNORECASE
    )
    periods = []
    for m in month_year_pattern.finditer(q_clean):
        month_str = m.group(1).capitalize()
        year_str = m.group(2)
        periods.append({"month": month_str, "year": year_str, "raw": f"{month_str} {year_str}"})

    standalone_months = []
    for m_name in CALENDAR_MONTHS:
        if re.search(r"\b" + m_name + r"\b", q_clean, re.IGNORECASE):
            standalone_months.append(m_name.capitalize())

    years = re.findall(r"\b(20\d{2})\b", q_clean)

    return {
        "periods": periods,
        "months": standalone_months,
        "years": years,
        "primary_month": periods[0]["month"] if periods else (standalone_months[0] if standalone_months else None),
        "primary_year": periods[0]["year"] if periods else (years[0] if years else None),
    }


def detect_query_entities(query_text: str) -> Dict[str, Any]:
    """Extracts target mine names, subsidiaries, temporal scope, and metric types from query text."""
    q_lower = query_text.lower()
    temporal_scope = detect_query_temporal_scope(query_text)
    
    # Explicitly recognize parent corporate identity before generic mine candidate extraction
    has_parent_corporate = bool(re.search(r"\b(?:coal\s+india(?:\s+limited)?|cil['’]?s?)\b", q_lower))

    # Mask corporate terms so "India" or "CIL" are not extracted as generic mine names
    text_for_mines = re.sub(r"\b(?:coal\s+india(?:\s+limited)?|cil['’]?s?)\b", "", query_text, flags=re.IGNORECASE)

    # Mask fiscal year expressions (e.g. "FY 2023-24", "FY2023-24", "2023-24") from mine candidate text
    text_for_mines = re.sub(
        r"\b(?:FY\s*\d{2,4}(?:[-\/]\d{2,4})?|20\d{2}[-\/]\d{2,4})\b",
        "",
        text_for_mines,
        flags=re.IGNORECASE
    )

    # Mask out temporal expressions (e.g. "March 2025", "November 2024") and units from mine candidate text
    text_for_mines = re.sub(
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[’']?\s*(20\d{2})?\b",
        "",
        text_for_mines,
        flags=re.IGNORECASE
    )
    text_for_mines = re.sub(
        r"\b\d+(?:\.\d+)?\s*(?:M\.Cu\.M|MCuM|MT|Mtpa|Lakh|Million|Tonnes|Cum|Cu|Cr)\b",
        "",
        text_for_mines,
        flags=re.IGNORECASE
    )
    text_for_mines = re.sub(
        r"\b(?:M\.Cu\.M|MCuM|MTPA|LCuM)\b",
        "",
        text_for_mines,
        flags=re.IGNORECASE
    )

    target_mines = []
    for km in KNOWN_MINES:
        if km.lower() in text_for_mines.lower():
            target_mines.append(km)
    
    # Generic mine name regex check (e.g. "Rajmahal", "Gevra", "Samaleswari")
    if not target_mines:
        exclude_from_mines = {
            "what", "where", "how", "why", "when", "who", "which", "is", "are", "can", "will", "does", "do",
            "give", "show", "tell", "explain", "describe", "define", "list", "compare", "provide", "difference",
            "total", "coal", "production", "overburden", "fiscal", "year", "annual", "open", "cast", "mining",
            "underground", "report", "reports", "document", "documents", "ingested", "source", "sources",
            "ministry", "provisional", "please", "hello", "official", "figures", "figure", "table", "tables",
            "projects", "project", "mines", "mine", "subsidiary", "subsidiaries", "highest", "lowest", "exceeding",
            "between", "page", "number", "numbers", "data", "statistics", "statistical", "all", "each", "every",
            "cu", "cum", "mcum", "m.cu.m.", "m.cu.m", "mt", "mtpa", "lcum", "lakh", "million", "tonnes", "tons",
            "tonne", "crore", "cr", "cr.", "m", "ocp", "india", "fy", "q1", "q2", "q3", "q4",
            "cmpdi", "sccl", "iicm", "dgms"
        }
        exclude_from_mines.update(CALENDAR_MONTHS)
        exclude_from_mines.update(MONTH_ABBREVIATIONS)
        for sub in OPERATING_SUBSIDIARIES:
            exclude_from_mines.add(sub.lower())

        # Explicit "mine <NAME>" check (e.g. "mine XYZ", "mine Rajmahal")
        explicit_mine_m = re.findall(r"\bmine\s+([A-Za-z0-9\-_]+)\b", text_for_mines, re.IGNORECASE)
        for em in explicit_mine_m:
            clean_em = em.strip()
            if (
                clean_em.lower() not in exclude_from_mines
                and not clean_em.lower().startswith("fy")
                and len(clean_em) >= 2
                and clean_em not in target_mines
            ):
                target_mines.append(clean_em)

        if not target_mines:
            mine_match = re.findall(r"\b([A-Z][a-zA-Z0-9]+(?:\s+(?:OC|OpenCast|Mine|Colliery))?)\b", text_for_mines)
            for mm in mine_match:
                base_word = mm.split()[0].lower()
                clean_mm = mm.lower().strip()
                if clean_mm.startswith("fy") or base_word.startswith("fy"):
                    continue
                if clean_mm not in exclude_from_mines and base_word not in exclude_from_mines and mm not in target_mines:
                    target_mines.append(mm)

    target_subsidiary = None
    for sub in OPERATING_SUBSIDIARIES:
        if re.search(r"\b" + sub + r"\b", query_text, re.IGNORECASE):
            target_subsidiary = sub
            break

    # Specificity-first metric domain detection
    domain_info = detect_query_metric_domain(query_text)
    target_metric = domain_info["canonical_name"] if domain_info else None

    # Fallback to legacy triggers if no domain matched
    if not target_metric:
        if "production" in q_lower or "coal" in q_lower or "output" in q_lower:
            target_metric = "Coal Production"
        elif "overburden" in q_lower or "obr" in q_lower:
            target_metric = "Overburden Removal"

    is_comparison = "compare" in q_lower or "versus" in q_lower or "vs" in q_lower or ("total" in q_lower and len(target_mines) > 0)
    is_subsidiary_total_only = "total" in q_lower and not target_mines
    target_fy = detect_query_fiscal_year(query_text)

    # Corporate query intent: CIL corporate / ALL CIL without specific mine or operating subsidiary
    is_corporate = False
    if not target_mines and not target_subsidiary:
        corp_keywords = [
            r"\bcil\b", r"\bcoal\s+india\b", r"\bcorporate\b", r"\bcompany\b",
            r"\borganization\b", r"\bpan-india\b", r"\bnational\b",
            r"\ball\s+subsidiaries\b", r"\boverall\b", r"\ball\s+cil\b"
        ]
        if has_parent_corporate or any(re.search(pat, q_lower, re.IGNORECASE) for pat in corp_keywords) or is_subsidiary_total_only:
            is_corporate = True

    return {
        "mines": target_mines,
        "subsidiary": target_subsidiary,
        "metric": target_metric,
        "metric_domain": domain_info,
        "fiscal_year": target_fy,
        "temporal_scope": temporal_scope,
        "is_comparison": is_comparison,
        "is_subsidiary_total_only": is_subsidiary_total_only,
        "is_corporate_query": is_corporate,
    }


def execute_hybrid_search(
    db: Session,
    query_text: str,
    top_k: int = 5,
    subsidiary_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Executes Entity-Aware Hybrid Retrieval combining:
    1. Structured PostgreSQL ExtractedMetric table queries
    2. ChromaDB Cosine Vector Search (Semantic)
    3. PostgreSQL Keyword Search (BM25)

    Applies Reciprocal Rank Fusion (RRF k=60) with entity, temporal, and authority-aware rank boosting:
    Prioritizes exact mine/entity matches, exact fiscal years, and official publications.
    """
    if not query_text or not query_text.strip():
        return []

    entities = detect_query_entities(query_text)
    target_mines = entities["mines"]
    target_metric = entities["metric"]
    metric_domain = entities.get("metric_domain")
    target_fy = entities.get("fiscal_year")

    # Scope normalization: "ALL", "ALL CIL", "", None -> None
    norm_sub = normalize_subsidiary_scope(subsidiary_filter)

    # 1. Fetch Top-K candidate results from Vector and Keyword channels
    vector_results = search_vector_store(query_text, top_k=top_k * 2, subsidiary_filter=norm_sub)
    keyword_results = search_keyword_store(db, query_text, top_k=top_k * 2, subsidiary_filter=norm_sub)

    # 2. Query ExtractedMetric table for structured evidence
    metric_results = []
    try:
        metric_query = db.query(ExtractedMetric, Document.filename).\
            join(Document, ExtractedMetric.document_id == Document.id)

        if norm_sub:
            metric_query = metric_query.filter(Document.subsidiary == norm_sub)

        if target_mines:
            mine_filters = []
            for m in target_mines:
                base_name = get_base_mine_name(m)
                if base_name and base_name.lower() != m.lower():
                    mine_filters.append(or_(
                        ExtractedMetric.mine_name.ilike(f"%{m}%"),
                        ExtractedMetric.mine_name.ilike(f"%{base_name}%")
                    ))
                else:
                    mine_filters.append(ExtractedMetric.mine_name.ilike(f"%{m}%"))
            metric_query = metric_query.filter(*mine_filters)

        if metric_domain:
            metric_names = metric_domain["db_metric_names"]
            metric_filters = [ExtractedMetric.metric_name.ilike(f"%{mn}%") for mn in metric_names]
            metric_query = metric_query.filter(or_(*metric_filters))
        elif target_metric:
            metric_query = metric_query.filter(ExtractedMetric.metric_name.ilike(f"%{target_metric}%"))

        temporal_scope = entities.get("temporal_scope", {})
        target_periods = temporal_scope.get("periods", [])
        target_months = temporal_scope.get("months", [])

        # Prioritize exact target fiscal year in structured metrics if specified (deterministic SQL ordering before limit)
        if target_fy:
            exact_fy_query = metric_query.filter(ExtractedMetric.fiscal_year == target_fy).order_by(ExtractedMetric.id.desc())
            metric_records = exact_fy_query.limit(top_k * 6).all()
            if not metric_records:
                metric_records = metric_query.order_by(ExtractedMetric.id.desc()).limit(top_k * 6).all()
        elif target_periods:
            p_filters = []
            for p in target_periods:
                pm = p["month"]
                py = p["year"]
                p_filters.append(Document.filename.ilike(f"%{pm}%{py}%"))
                p_filters.append(Document.filename.ilike(f"%{pm[:3]}%{py}%"))
            temporal_query = metric_query.filter(or_(*p_filters)).order_by(ExtractedMetric.id.desc())
            temporal_records = temporal_query.limit(top_k * 6).all()
            if temporal_records:
                metric_records = temporal_records + metric_query.order_by(ExtractedMetric.id.desc()).limit(top_k * 4).all()
            else:
                metric_records = metric_query.order_by(ExtractedMetric.id.desc()).limit(top_k * 6).all()
        else:
            metric_records = metric_query.order_by(ExtractedMetric.id.desc()).limit(top_k * 6).all()

        is_corp = entities.get("is_corporate_query", False)

        def is_conflated_subsidiary_total(m) -> bool:
            snippet = (m.raw_snippet or "").lower()
            unit = (m.unit or "").lower()
            if re.search(r"(?:as a whole|total\s+(?:coal\s+)?production\s+for\s+[a-z]+)\s+reached\s+[\d\.]+\s*(?:million\s+tonnes|mt)", snippet):
                if "million" in unit or unit == "mt":
                    return True
            return False

        def rank_metric_record(rec) -> tuple:
            m, filename = rec
            snippet = (m.raw_snippet or "").lower()
            m_name = (m.mine_name or "").lower()

            # 1. Historical inception penalty (disqualify/demote historical inception for requested FY)
            is_hist = is_historical_evidence_snippet(m.raw_snippet, target_fy=target_fy)

            # 2. Temporal filename / snippet match
            temporal_match = 0
            if target_periods:
                for p in target_periods:
                    pm = p["month"].lower()
                    py = p["year"]
                    if (pm in filename.lower() or pm[:3] in filename.lower()) and py in filename.lower():
                        temporal_match += 3
                    elif pm in snippet and py in snippet:
                        temporal_match += 1
            elif target_months:
                for tm in target_months:
                    if tm.lower() in filename.lower() or tm.lower()[:3] in filename.lower():
                        temporal_match += 2
                    elif tm.lower() in snippet:
                        temporal_match += 1

            # 3. Summary table / Page 5 boost (only when not querying a specific target mine)
            page_boost = 1 if (not target_mines and m.page_number and m.page_number <= 10 and (m.subsidiary in OPERATING_SUBSIDIARIES or is_corp)) else 0

            # 4. Target mine matching
            mine_match = 0
            conflated_penalty = 0
            if target_mines:
                mine_terms = set()
                for tm in target_mines:
                    mine_terms.add(tm.lower())
                    base_name = re.sub(r"\s+(?:OC|OpenCast|UG|Mine|Colliery)\b", "", tm, flags=re.IGNORECASE).strip()
                    if base_name:
                        mine_terms.add(base_name.lower())
                if any(term in snippet for term in mine_terms) or any(term in m_name for term in mine_terms):
                    mine_match = 1
                if not entities.get("is_comparison") and not entities.get("is_subsidiary_total_only"):
                    if is_conflated_subsidiary_total(m):
                        conflated_penalty = -1

            # 5. Corporate context scoring
            corp_score = 0
            if is_corp:
                if is_corporate_context_snippet(m.raw_snippet) or "cil" in snippet or "coal india" in snippet:
                    corp_score += 2
                if m_name in GENERIC_MINE_PHRASES or m_name in ["cil", "cil corporate", "corporate", "overall mine", "unspecified mine"]:
                    corp_score += 1
                elif any(km.lower() in m_name for km in KNOWN_MINES):
                    corp_score -= 1

            # 6. Valid non-zero value boost
            has_val = 1 if (m.standard_value is not None and float(m.standard_value) > 0) else 0

            # 7. Authority
            auth_score = 1 if classify_document_authority(filename) == "OFFICIAL" else 0

            # 8. Sub-to-doc match
            sub_match = 1 if (m.subsidiary or "") in (filename or "") else 0

            # 9. Base confidence
            conf_val = float(m.confidence_score or 0.0)

            return (
                not is_hist,
                temporal_match,
                mine_match if target_mines else 0,
                conflated_penalty if target_mines else 0,
                corp_score if is_corp else 0,
                page_boost,
                has_val,
                auth_score,
                sub_match,
                conf_val,
                int(m.id or 0)
            )

        metric_records.sort(key=rank_metric_record, reverse=True)
        metric_records = metric_records[:top_k * 4]

        for m, filename in metric_records:
            num_val_str = f"{float(m.numeric_value):.2f}" if m.numeric_value is not None else "N/A"
            std_val_str = f"{float(m.standard_value):.2f}" if m.standard_value is not None else "N/A"
            display_mine = m.mine_name
            # Corporate relabeling is allowed ONLY when raw evidence supports corporate/aggregate context
            is_generic_unattached = (
                m.mine_name.lower() in GENERIC_MINE_PHRASES and
                (not m.subsidiary or m.subsidiary.upper() in ["CIL", "CIL HQ", "MINISTRY OF COAL"])
            )
            if is_corp and (is_corporate_context_snippet(m.raw_snippet) or is_generic_unattached):
                display_mine = "CIL Corporate"

            formatted_text = (
                f"Mine Entity: {display_mine} | Metric: {m.metric_name} | "
                f"Raw Extracted Value: {num_val_str} {m.unit} | "
                f"Normalized Value: {std_val_str} {m.standard_unit or 'MT'} | "
                f"Fiscal Year: {m.fiscal_year}\n"
                f"Raw Evidence Snippet: {m.raw_snippet or ''}"
            )
            metric_results.append({
                "chunk_id": None,
                "document_id": m.document_id,
                "filename": filename,
                "page_number": m.page_number or 1,
                "chunk_index": -int(m.id),  # Negative unique index to preserve metric identity
                "text": formatted_text,
                "vector_score": 0.95,
                "keyword_score": 0.95,
                "is_metric": True,
                "mine_name": display_mine,
                "fiscal_year": m.fiscal_year,
                "authority": classify_document_authority(filename)
            })
    except Exception as err:
        logger.warning(f"ExtractedMetric search query note: {err}")

    # 3. Fuse and deduplicate candidate chunks using canonical key (BUG-06)
    fused_candidates: Dict[tuple, Dict[str, Any]] = {}

    def get_candidate_key(item: Dict[str, Any]) -> tuple:
        """Canonical candidate identity: (document_id, page_number, chunk_index)."""
        return (
            int(item.get("document_id") or 0),
            int(item.get("page_number") or 1),
            int(item.get("chunk_index") or 0)
        )

    # Process Metric Results (Priority Rank 1..N)
    for rank, item in enumerate(metric_results, start=1):
        key = get_candidate_key(item)
        rrf_score_component = 1.0 / (RRF_K_CONSTANT + rank)
        fused_candidates[key] = {
            "chunk_id": item.get("chunk_id"),
            "document_id": item["document_id"],
            "filename": item["filename"],
            "page_number": item["page_number"],
            "chunk_index": item["chunk_index"],
            "text": item["text"],
            "vector_score": item.get("vector_score", 0.0),
            "keyword_score": item.get("keyword_score", 0.0),
            "rrf_score": rrf_score_component + 0.05,  # Base boost for verified structured metric
            "fiscal_year": item.get("fiscal_year"),
            "authority": item.get("authority", classify_document_authority(item["filename"]))
        }

    # Process Vector Results
    for rank, item in enumerate(vector_results, start=1):
        key = get_candidate_key(item)
        rrf_score_component = 1.0 / (RRF_K_CONSTANT + rank)

        if key not in fused_candidates:
            fused_candidates[key] = {
                "chunk_id": item.get("chunk_id"),
                "document_id": item["document_id"],
                "filename": item["filename"],
                "page_number": item["page_number"],
                "chunk_index": item.get("chunk_index", 0),
                "text": item["text"],
                "vector_score": item.get("vector_score", 0.0),
                "keyword_score": 0.0,
                "rrf_score": rrf_score_component,
                "fiscal_year": detect_query_fiscal_year(item["text"]),
                "authority": classify_document_authority(item["filename"])
            }
        else:
            if not fused_candidates[key].get("chunk_id") and item.get("chunk_id"):
                fused_candidates[key]["chunk_id"] = item.get("chunk_id")
            fused_candidates[key]["vector_score"] = item.get("vector_score", 0.0)
            fused_candidates[key]["rrf_score"] += rrf_score_component

    # Process Keyword Results
    for rank, item in enumerate(keyword_results, start=1):
        key = get_candidate_key(item)
        rrf_score_component = 1.0 / (RRF_K_CONSTANT + rank)

        if key not in fused_candidates:
            fused_candidates[key] = {
                "chunk_id": item.get("chunk_id"),
                "document_id": item["document_id"],
                "filename": item["filename"],
                "page_number": item["page_number"],
                "chunk_index": item["chunk_index"],
                "text": item["text"],
                "vector_score": 0.0,
                "keyword_score": item.get("keyword_score", 0.0),
                "rrf_score": rrf_score_component,
                "fiscal_year": detect_query_fiscal_year(item["text"]),
                "authority": classify_document_authority(item["filename"])
            }
        else:
            if not fused_candidates[key].get("chunk_id") and item.get("chunk_id"):
                fused_candidates[key]["chunk_id"] = item.get("chunk_id")
            fused_candidates[key]["keyword_score"] = item.get("keyword_score", 0.0)
            fused_candidates[key]["rrf_score"] += rrf_score_component

    # 4. Entity, Temporal, and Authority-Aware Rank Boosting
    metric_domain_terms = []
    if metric_domain:
        metric_domain_terms = [t.lower() for t in metric_domain["db_metric_names"]]
    elif target_metric:
        metric_domain_terms = [target_metric.lower()]

    target_mine_terms = set()
    if target_mines:
        for tm in target_mines:
            target_mine_terms.add(tm.lower())
            base_name = get_base_mine_name(tm)
            if base_name:
                target_mine_terms.add(base_name.lower())

    for cand in fused_candidates.values():
        text_lower = cand["text"].lower()

        # A. Mine entity relevance
        if target_mine_terms:
            snippet_part = text_lower.split("raw evidence snippet:")[-1] if "raw evidence snippet:" in text_lower else text_lower
            if any(term in snippet_part for term in target_mine_terms):
                cand["rrf_score"] += 0.12
            elif any(term in text_lower for term in target_mine_terms):
                cand["rrf_score"] += 0.08

        # B. Metric domain relevance
        if metric_domain_terms and any(term in text_lower for term in metric_domain_terms):
            cand["rrf_score"] += 0.06

        # C. Temporal relevance (Component 4)
        temporal_scope = entities.get("temporal_scope", {})
        target_periods = temporal_scope.get("periods", [])
        target_months = temporal_scope.get("months", [])
        fname_lower = cand["filename"].lower()

        if target_periods:
            for p in target_periods:
                p_m = p["month"].lower()
                p_y = p["year"]
                if (p_m in fname_lower or p_m[:3] in fname_lower) and p_y in fname_lower:
                    cand["rrf_score"] += 0.22
                elif p_m in text_lower and p_y in text_lower:
                    cand["rrf_score"] += 0.12
        elif target_months:
            for tm in target_months:
                if tm.lower() in fname_lower or tm.lower()[:3] in fname_lower:
                    cand["rrf_score"] += 0.18
                elif tm.lower() in text_lower:
                    cand["rrf_score"] += 0.08

        if target_fy:
            cand_fy = cand.get("fiscal_year")
            fy_short = target_fy[-5:]  # e.g. "23-24"
            if cand_fy == target_fy or target_fy in text_lower or fy_short in text_lower:
                cand["rrf_score"] += 0.10
            elif cand_fy and cand_fy != target_fy:
                # Explicit conflicting fiscal year: demote
                cand["rrf_score"] -= 0.15

        # D. Summary & Subsidiary Tables Boost (Page 5, multiple subsidiaries)
        is_sub_or_summary = (
            not target_mine_terms and (
                "subsidiary" in query_text.lower()
                or "subsidiaries" in query_text.lower()
                or "highest" in query_text.lower()
                or "compare" in query_text.lower()
                or "all cil" in query_text.lower()
                or "total" in query_text.lower()
            )
        )
        if is_sub_or_summary:
            sub_count = sum(1 for sub in OPERATING_SUBSIDIARIES if re.search(r"\b" + sub + r"\b", cand["text"]))
            if sub_count >= 3:
                cand["rrf_score"] += 0.20
            elif sub_count >= 1:
                cand["rrf_score"] += 0.05
            if re.search(r"\b(?:fig\.\s+in\s+mt|total\s+coal\s+production|table\s+(?:1|2|of\s+contents))\b", text_lower):
                cand["rrf_score"] += 0.10

        # E. Source Authority relevance (Component 5)
        auth = cand.get("authority") or classify_document_authority(cand.get("filename", ""))
        cand["authority"] = auth
        if auth == "OFFICIAL":
            cand["rrf_score"] += 0.08
        elif auth == "SYNTHETIC_TEST":
            cand["rrf_score"] -= 0.05

    # 5. Sort candidates descending by RRF score
    sorted_chunks = sorted(fused_candidates.values(), key=lambda x: x["rrf_score"], reverse=True)

    # Format RRF scores
    for sc in sorted_chunks:
        sc["rrf_score"] = round(sc["rrf_score"], 6)

    logger.info(f"Hybrid search returned {len(sorted_chunks)} fused candidate chunks for query: '{query_text[:40]}...'")
    return sorted_chunks[:top_k]

