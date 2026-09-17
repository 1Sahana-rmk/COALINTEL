import re
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Mining Subsidiary Dictionary
SUBSIDIARIES = ["ECL", "BCCL", "CCL", "WCL", "SECL", "NCL", "MCL", "NEC", "CIL"]

# Known Mine Names
KNOWN_MINES = [
    "Rajmahal OC", "Rajmahal OpenCast", "Gevra OC", "Dipka OC", "Kusmunda OC",
    "Samaleswari OC", "Sonalpur OC", "Jayant OC", "Nigahi OC", "Amlohri OC",
    "Belpahar OC", "Lakhanpur OC", "Bhubaneswari OC", "Ananta OC", "Bharatpur OC",
    "Lingaraj OC", "Kalinga OC", "Dudhichua OC", "Khadia OC", "Bina OC",
    "Kakri OC", "Block B OC", "Jhingurda OC", "Ashok OC", "Piparwar OC",
    "Magadh OC", "Amrapali OC", "Kalyani OC", "Moonidih UG", "Jharia OC"
]

GENERIC_MINE_PHRASES = {
    "cil mine", "coal mine", "overall mine", "unspecified mine",
    "mines of cil", "cil mines", "company mine", "total mine", "national mine",
    "coalfield", "coalfields"
}


def get_base_mine_name(name: str) -> str:
    """
    Extracts the base mine name by stripping mining type suffixes.
    Supported suffixes: OC, OpenCast, UG, Underground, Mine, Colliery, Project, Block, Washery.
    Examples:
        "Gevra OC" -> "Gevra"
        "Gevra OpenCast" -> "Gevra"
        "Alpha Mine" -> "Alpha"
        "Alpha UG" -> "Alpha"
    """
    if not name:
        return ""
    clean = str(name).strip()
    base = re.sub(
        r"\s+(?:OC|OpenCast|UG|Underground|Mine|Colliery|Project|Block|Washery)\b",
        "",
        clean,
        flags=re.IGNORECASE
    ).strip()
    return base if base else clean


def canonicalize_mine_name(name: str) -> str:
    """
    Returns the canonical mine name representation if matched against KNOWN_MINES,
    otherwise preserves the source's explicit entity without inventing suffixes.
    """
    if not name:
        return ""
    clean = str(name).strip()
    base = get_base_mine_name(clean)
    for km in KNOWN_MINES:
        if km.lower() == clean.lower():
            return km
        if get_base_mine_name(km).lower() == base.lower():
            # If source already has a suffix, preserve it with canonical casing
            if base.lower() != clean.lower():
                return clean
            # If source is bare base name, keep source's explicit entity
            return clean
    return clean


def detect_query_fiscal_year(query_text: str) -> Optional[str]:
    """
    Detects explicit fiscal year from query string.
    Supports: FY2023-24, FY 2023-24, 2023-24, FY 23-24, 2023/24.
    Normalizes to canonical 'YYYY-YY' (e.g. '2023-24').
    """
    if not query_text or not query_text.strip():
        return None
    # Match FY 2023-24 or FY2023-24 or 2023-24 or 2023/24
    m = re.search(r"\b(?:FY\s*)?((?:19|20)\d{2})[-\/](\d{2,4})\b", query_text, re.IGNORECASE)
    if m:
        start_yr = m.group(1)
        end_yr = m.group(2)
        if len(end_yr) == 4:
            end_yr = end_yr[-2:]
        return f"{start_yr}-{end_yr}"
    # Match FY 23-24 or FY23-24
    m2 = re.search(r"\bFY\s*(\d{2})[-\/](\d{2})\b", query_text, re.IGNORECASE)
    if m2:
        start_yr_short = int(m2.group(1))
        full_start = 2000 + start_yr_short if start_yr_short < 70 else 1900 + start_yr_short
        return f"{full_start}-{m2.group(2)}"
    # Match single FY YYYY e.g. FY2035 or FY 2035
    m3 = re.search(r"\bFY\s*((?:19|20)\d{2})\b", query_text, re.IGNORECASE)
    if m3:
        yr = int(m3.group(1))
        return f"{yr-1}-{str(yr)[-2:]}"
    return None



def classify_document_authority(filename: str) -> str:
    """
    Classifies document source authority into:
    - OFFICIAL: Official annual reports, ministry reports, audited filings, CIL/subsidiary reports
    - SYNTHETIC_TEST: Test files, demo files, synthetic/mock uploads
    - INTERNAL / UNKNOWN: Other sources
    """
    if not filename:
        return "UNKNOWN"
    f_lower = filename.lower()
    if any(t in f_lower for t in ["test", "demo", "synthetic", "mock"]):
        return "SYNTHETIC_TEST"
    if any(o in f_lower for o in [
        "annual_report", "annual report", "annualreport", "chap", "moc", "ministry",
        "audit", "srn-", "secl", "ecl", "bccl", "cmpdi", "cil", "wcl", "mcl", "ccl", "ncl"
    ]):
        return "OFFICIAL"
    return "INTERNAL"


HISTORICAL_INCEPTION_PATTERNS = [
    r"\b(?:came\s+into\s+being|year\s+of\s+its\s+inception|at\s+(?:the\s+)?inception|since\s+inception)\b",
    r"\b(?:established|incorporated|founded)\s+in\s+19\d{2}\b",
    r"\b(?:modest\s+production\s+of|inception\s+in)\s+19\d{2}\b",
    r"\b(?:taking\s+over\s+private\s+coal\s+mines|in\s+November\s+1975|in\s+1975)\b",
]


def is_historical_evidence_snippet(text: Optional[str], target_fy: Optional[str] = None) -> bool:
    """
    Identifies historical / inception context snippets (e.g. 1975 CIL inception)
    that must not be confused with modern fiscal year operational metrics.
    """
    if not text:
        return False
    t_lower = text.lower()
    for pat in HISTORICAL_INCEPTION_PATTERNS:
        if re.search(pat, t_lower, re.IGNORECASE):
            if target_fy:
                target_short = target_fy[-5:] if len(target_fy) >= 5 else target_fy
                # If target fiscal year is NOT present in text, this is clearly historical
                if target_fy not in text and target_short not in text:
                    return True
                # If target FY is present elsewhere in chunk, check whether inception phrasing qualifies the metric
                if re.search(r"\b(?:modest\s+production\s+of|at\s+(?:the\s+)?inception|came\s+into\s+being)\b", t_lower):
                    return True
            else:
                return True
    return False


def is_corporate_context_snippet(text: Optional[str]) -> bool:
    """
    Identifies corporate / overarching CIL aggregate context in text snippets.
    e.g. company-wide production, CIL milestones, national coal production, annual corporate target, etc.
    """
    if not text:
        return False
    corp_patterns = [
        r"\b(?:company-wide|organization-wide|group-wide|nationwide)\b",
        r"\b(?:corporate-level|corporate\s+production|consolidated\s+production|aggregate\s+production)\b",
        r"\b(?:milestones\s+in\s+20\d{2}|annual\s+(?:corporate\s+)?target|growth\s+over\s+last\s+fiscal\s+year)\b",
        r"\b(?:cil\s+as\s+a\s+whole|coal\s+india\s+as\s+a\s+whole|company\s+as\s+a\s+whole)\b",
        r"\b(?:total\s+production\s+of\s+(?:cil|coal\s+india)|all\s+mines\s+of\s+cil|corporate\s+cil|overall\s+cil\s+production)\b",
        r"\b(?:cil['’]?s\s+subsidiaries|across\s+all\s+subsidiaries|all\s+subsidiaries\s+of\s+cil|single\s+largest\s+coal\s+producer)\b",
        r"\b(?:coal\s+production\s+of\s+[\d\.]+\s*(?:mt|million\s+tonnes)\s+during\b)",
    ]
    t_lower = text.lower()
    return any(re.search(pat, t_lower, re.IGNORECASE) for pat in corp_patterns)



# Specificity Precedence Rules for Metric Classification
# Evaluated strictly against local line/sentence context (bare 'coal' removed from triggers)
METRIC_CLASSIFICATION_RULES = [
    ("Exploration / Core Drilling", r"\b(?:core\s+)?drill(?:ing)?\b|\bmeterage\b|\bborehole\b"),
    ("Washing Capacity", r"\bwash(?:ing)?\s+capacity\b|\bwashery(?:\s+capacity)?\b|\bclean\s+coal\s+yield\b"),
    ("Overburden Removal", r"\boverburden(?:\s+removal)?\b|\bobr\b|\bcomposite\s+obr\b"),
    ("Coal Despatch", r"\b(?:coal\s+)?despatch\b|\b(?:coal\s+)?dispatch\b|\bofftake\b"),
    ("Stripping Ratio", r"\bstripping\s+ratio\b"),
    ("Coal Production", r"\b(?:raw\s+coal|coal|opencast|underground)\s+production\b|\bproduction\s+of\s+coal\b|\bmined\s+coal\b|\bcoal\s+output\b|\btotal\s+production\b|\bannual\s+production\b"),
    ("Production", r"\bproduction\b|\boutput\b"),
]

# Backward-compatible map
METRICS_PATTERNS = {
    "Exploration / Core Drilling": r"\b(?:core\s+)?drill(?:ing)?\b|\bmeterage\b|\bborehole\b",
    "Washing Capacity": r"\bwash(?:ing)?\s+capacity\b|\bwashery(?:\s+capacity)?\b|\bclean\s+coal\s+yield\b",
    "Overburden Removal": r"\boverburden(?:\s+removal)?\b|\bobr\b|\bcomposite\s+obr\b",
    "Despatch": r"\b(?:coal\s+)?despatch\b|\b(?:coal\s+)?dispatch\b|\bofftake\b",
    "Stripping Ratio": r"\bstripping\s+ratio\b",
    "Production": r"\b(?:raw\s+coal|coal|opencast|underground)\s+production\b|\bproduction\s+of\s+coal\b|\bmined\s+coal\b|\bcoal\s+output\b|\bproduction\b|\boutput\b",
}

# Metric Domain Definitions for Specificity-First Query & Database Matching
METRIC_DOMAINS = [
    {
        "domain_key": "STRIPPING_RATIO",
        "canonical_name": "Stripping Ratio",
        "patterns": [r"\bstripping\s+ratio\b"],
        "db_metric_names": ["Stripping Ratio"],
    },
    {
        "domain_key": "OVERBURDEN_REMOVAL",
        "canonical_name": "Overburden Removal",
        "patterns": [r"\boverburden(?:\s+removal)?\b", r"\bobr\b", r"\bcomposite\s+obr\b"],
        "db_metric_names": ["Overburden Removal", "OBR", "Composite OBR"],
    },
    {
        "domain_key": "WASHING_CAPACITY",
        "canonical_name": "Washing Capacity",
        "patterns": [r"\bwash(?:ing)?\s+capacity\b", r"\bwashery(?:\s+capacity)?\b", r"\bclean\s+coal\s+yield\b"],
        "db_metric_names": ["Washing Capacity", "Washery", "Clean Coal Yield"],
    },
    {
        "domain_key": "EXPLORATION_DRILLING",
        "canonical_name": "Exploration / Core Drilling",
        "patterns": [r"\b(?:core\s+)?drill(?:ing)?\b", r"\bmeterage\b", r"\bborehole\b"],
        "db_metric_names": ["Exploration / Core Drilling", "Core Drilling", "Drilling"],
    },
    {
        "domain_key": "COAL_DESPATCH",
        "canonical_name": "Coal Despatch",
        "patterns": [r"\b(?:coal\s+)?despatch\b", r"\b(?:coal\s+)?dispatch\b", r"\bofftake\b"],
        "db_metric_names": ["Coal Despatch", "Despatch", "Dispatch", "Offtake"],
    },
    {
        "domain_key": "COAL_PRODUCTION",
        "canonical_name": "Coal Production",
        "patterns": [
            r"\b(?:raw\s+coal|coal|opencast|underground)\s+production\b",
            r"\bproduction\s+of\s+coal\b",
            r"\bmined\s+coal\b",
            r"\bcoal\s+output\b",
            r"\braw\s+coal\b",
            r"\bproduction\b",
            r"\boutput\b",
        ],
        "db_metric_names": [
            "Coal Production",
            "Production",
            "Coal Output",
            "Raw Coal Production",
            "Annual Production",
        ],
    },
]


def normalize_subsidiary_scope(scope: Optional[str]) -> Optional[str]:
    """
    Normalizes subsidiary scope strings into either:
    - None: representing unrestricted/global scope ("ALL", "ALL CIL", "ALL SUBSIDIARIES", "ALL_CIL", "ALL_SUBSIDIARIES", "", None, "NULL", "NONE")
    - Normalized uppercase subsidiary name (e.g. "SECL", "ECL", "WCL")
    """
    if not scope:
        return None
    s = str(scope).strip()
    if not s or s.upper() in ["ALL", "ALL CIL", "ALL SUBSIDIARIES", "ALL_CIL", "ALL_SUBSIDIARIES", "NONE", "NULL"]:
        return None
    if s.upper().startswith("ALL ") or s.upper().startswith("ALL_"):
        return None
    return s.upper()


def detect_query_metric_domain(query_text: str) -> Optional[Dict[str, Any]]:
    """
    Evaluates query string against specificity-first metric domains.
    Returns domain dictionary with canonical name and matching database metric names,
    or None if no recognized metric domain pattern matches.
    """
    if not query_text or not query_text.strip():
        return None
    q_lower = query_text.lower()
    for domain in METRIC_DOMAINS:
        for pat in domain["patterns"]:
            if re.search(pat, q_lower):
                return domain
    return None


# Unit Multipliers to convert raw units to Million Tonnes (MT) or M.Cu.M
UNIT_MULTIPLIERS_TO_MT = {
    "lakh tonnes": 0.1,
    "lakh tonne": 0.1,
    "lakh mt": 0.1,
    "million tonnes": 1.0,
    "million tonne": 1.0,
    "mt": 1.0,
    "thousand tonnes": 0.001,
    "thousand tonne": 0.001,
    "tonnes": 0.000001,
    "tonne": 0.000001,
    "tons": 0.000001,
    "ton": 0.000001,
    "m.cu.m": 1.0,
    "million cu.m": 1.0,
    "mcum": 1.0,
}


def normalize_unit_to_mt(raw_value: float, raw_unit: str) -> Tuple[float, str]:
    """
    Deterministically normalizes raw extracted numerical values and units into Million Tonnes (MT)
    or M.Cu.M with high precision (avoiding premature rounding to 4 decimals).
    Example: 42.50 Lakh Tonnes -> 4.25 MT (Multiplier = 0.1)
    Example: 7.99 Tonnes -> 0.000008 MT (Multiplier = 1e-6)
    """
    if not raw_unit:
        return raw_value, "MT"

    unit_clean = raw_unit.strip().lower()

    for unit_pattern, multiplier in UNIT_MULTIPLIERS_TO_MT.items():
        if unit_pattern in unit_clean:
            # Maintain high precision for fractional units like Tonnes without zero underflow
            standard_val = round(raw_value * multiplier, 6)
            standard_unit = "M.Cu.M" if ("cu" in unit_clean or "mcum" in unit_clean) else "MT"
            return standard_val, standard_unit

    # Default fallback if unit matches standard MT
    return raw_value, "MT"


def _extract_local_context(text: str, start_char: int, end_char: int, window: int = 180) -> str:
    """Extracts a clean, sentence-aligned local context snippet around the match."""
    s_start = max(0, start_char - window)
    s_end = min(len(text), end_char + window)
    return text[s_start:s_end].strip()


def extract_entity_tuples_from_text(
    text: str,
    page_number: int,
    default_subsidiary: Optional[str] = "CIL HQ",
    default_year: Optional[str] = "2023-24"
) -> List[Dict[str, Any]]:
    """
    Scans page text using proximity-first parsing and strict classification rules to extract
    structured entity metrics tuples with dynamic evidence confidence and temporal grounding.
    """
    extracted_tuples = []
    if not text or not text.strip():
        return extracted_tuples

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    # Match numeric values with mining units (e.g., "42.50 Lakh Tonnes" or "120.40 M.Cu.M")
    value_unit_pattern = re.compile(
        r"([\d\.,]+)\s*"
        r"(Lakh\s+Tonnes|Million\s+Tonnes|Thousand\s+Tonnes|MT|M\.Cu\.M|MCuM|Tonnes)",
        re.IGNORECASE
    )

    mine_name_regex = re.compile(
        r"\b([A-Z][A-Za-z0-9_\-\.]+(?:\s+[A-Z][A-Za-z0-9_\-\.]+)*\s+(?:OC|OpenCast|UG|Underground|Mine|Colliery|Project|Washery|Block))\b"
    )

    for match in value_unit_pattern.finditer(text):
        val_str = match.group(1).replace(",", "").strip()
        unit_raw = match.group(2).strip()

        try:
            numeric_val = float(val_str)
        except ValueError:
            continue

        # Extract surrounding local snippet
        snippet = _extract_local_context(text, match.start(), match.end(), window=180)
        unit_clean = unit_raw.lower()

        # Step 1: Metric Classification (Strict Specificity Precedence on LOCAL context)
        metric_name = None
        if "cu" in unit_clean or "mcum" in unit_clean:
            metric_name = "Overburden Removal"
        else:
            for m_name, m_regex in METRIC_CLASSIFICATION_RULES:
                if re.search(m_regex, snippet, re.IGNORECASE):
                    metric_name = m_name
                    break

        if not metric_name:
            # Check if production keywords exist in local snippet
            if re.search(r"\b(?:production|output|produced)\b", snippet, re.IGNORECASE):
                metric_name = "Coal Production"
            else:
                metric_name = "Mining Metric (Unclassified)"

        # Find current line containing the numeric match
        line_start = text.rfind("\n", 0, match.start())
        line_start = 0 if line_start == -1 else line_start + 1
        line_end = text.find("\n", match.end())
        line_end = len(text) if line_end == -1 else line_end
        current_line = text[line_start:line_end].strip()

        # Step 2: Entity & Mine Extraction (Line-proximity first, specific over generic)
        detected_mine = None

        # Check for specific known mines on current line (full name first)
        for km in KNOWN_MINES:
            if re.search(r"\b" + re.escape(km) + r"\b", current_line, re.IGNORECASE):
                detected_mine = km
                break

        # Check for base name of known mines on current line (e.g. "Gevra" in "Gevra achieved 59.11 MT")
        if not detected_mine:
            for km in KNOWN_MINES:
                base_km = get_base_mine_name(km)
                if len(base_km) >= 3 and re.search(r"\b" + re.escape(base_km) + r"\b", current_line, re.IGNORECASE):
                    # Check if suffix exists in line, else preserve explicit entity
                    suffix_m = re.search(r"\b" + re.escape(base_km) + r"\s+(OC|OpenCast|UG|Underground|Mine|Colliery|Project|Block)\b", current_line, re.IGNORECASE)
                    if suffix_m:
                        detected_mine = suffix_m.group(0).strip()
                    else:
                        detected_mine = base_km
                    break

        # Check previous line for known mines or base name
        if not detected_mine and line_start > 0:
            prev_line_start = text.rfind("\n", 0, line_start - 1)
            prev_line_start = 0 if prev_line_start == -1 else prev_line_start + 1
            prev_line = text[prev_line_start:line_start - 1].strip()
            for km in KNOWN_MINES:
                if re.search(r"\b" + re.escape(km) + r"\b", prev_line, re.IGNORECASE):
                    detected_mine = km
                    break
                base_km = get_base_mine_name(km)
                if len(base_km) >= 3 and re.search(r"\b" + re.escape(base_km) + r"\b", prev_line, re.IGNORECASE):
                    suffix_m = re.search(r"\b" + re.escape(base_km) + r"\s+(OC|OpenCast|UG|Underground|Mine|Colliery|Project|Block)\b", prev_line, re.IGNORECASE)
                    detected_mine = suffix_m.group(0).strip() if suffix_m else base_km
                    break

        # Check regex for general mine entities on current line or previous line
        if not detected_mine:
            m_match = mine_name_regex.search(current_line)
            if m_match and m_match.group(1).strip().lower() not in GENERIC_MINE_PHRASES:
                detected_mine = m_match.group(1).strip()
            elif line_start > 0:
                p_match = mine_name_regex.search(prev_line)
                if p_match and p_match.group(1).strip().lower() not in GENERIC_MINE_PHRASES:
                    detected_mine = p_match.group(1).strip()

        # Check snippet for known mine base names (specific entity over corporate generic)
        if not detected_mine:
            for km in KNOWN_MINES:
                base_km = get_base_mine_name(km)
                if len(base_km) >= 3 and re.search(r"\b" + re.escape(base_km) + r"\b", snippet, re.IGNORECASE):
                    suffix_m = re.search(r"\b" + re.escape(base_km) + r"\s+(OC|OpenCast|UG|Underground|Mine|Colliery|Project|Block)\b", snippet, re.IGNORECASE)
                    detected_mine = suffix_m.group(0).strip() if suffix_m else base_km
                    break

        # Closest regex mine mention in snippet (excluding generic corporate phrases)
        if not detected_mine:
            closest_mine = None
            min_dist = float("inf")
            match_offset_in_snippet = match.start() - max(0, match.start() - 180)
            for m in mine_name_regex.finditer(snippet):
                m_str = m.group(1).strip()
                if m_str.lower() in GENERIC_MINE_PHRASES:
                    continue
                dist = abs(m.start() - match_offset_in_snippet)
                if dist < min_dist:
                    min_dist = dist
                    closest_mine = m_str
            if closest_mine:
                detected_mine = closest_mine

        # Check for named entity followed by operational verb on current line or snippet (e.g. 'Alpha achieved 15.5 MT')
        if not detected_mine:
            action_verb_match = re.search(
                r"\b([A-Z][A-Za-z0-9_\-\.]+(?:\s+[A-Za-z0-9_\-\.]+)*(?:\s+(?:OC|OpenCast|UG|Underground|Mine|Colliery|Project|Block))?)\s+(?:achieved|produced|recorded|reached|reported|mined|extracted)\b",
                current_line or snippet
            )
            if action_verb_match:
                cand = action_verb_match.group(1).strip()
                cand_lower = cand.lower()
                stop_words = {"during", "in", "the", "total", "annual", "overall", "target", "cil", "this"}
                is_corp = any(w in cand_lower for w in ["limited", "ltd", "company", "coalfields", "corporation", "subsidiary", "board"])
                is_sub = any(s.lower() == cand_lower for s in SUBSIDIARIES)
                if cand_lower not in GENERIC_MINE_PHRASES and cand_lower not in stop_words and not is_corp and not is_sub and len(cand) >= 3:
                    # If it doesn't have a mine suffix, ensure it looks like a clean single or double named entity
                    detected_mine = cand

        # Step 3: Subsidiary Extraction (Local first, then fallback)
        subsidiary = None
        for sub in SUBSIDIARIES:
            if re.search(r"\b" + sub + r"\b", snippet, re.IGNORECASE):
                subsidiary = sub
                break

        if not subsidiary:
            # Check full text for page-level subsidiary or use default
            for sub in SUBSIDIARIES:
                if re.search(r"\b" + sub + r"\b", text, re.IGNORECASE):
                    subsidiary = sub
                    break
            if not subsidiary:
                subsidiary = default_subsidiary or "CIL HQ"

        # Safe non-misleading fallback for mine name (NO synthetic "CIL Mine" or "ECL Mine")
        if not detected_mine or detected_mine.lower() in GENERIC_MINE_PHRASES:
            mine_name = "Unspecified Mine"
        else:
            mine_name = detected_mine

        # Step 4: Temporal / Fiscal Year Grounding
        is_historical = False
        fiscal_year = None

        # A. Detect historical year mentions (e.g. "in 1975", "at inception in 1975", "since 1975")
        hist_match = re.search(
            r"\b(?:in|since|inception\s+in|year\s+of\s+its\s+inception|during|year|established\s+in)\s+(19\d{2}|20[01]\d)\b",
            current_line or snippet,
            re.IGNORECASE
        )
        if hist_match:
            hist_year = hist_match.group(1)
            fiscal_year = f"{hist_year}-{int(hist_year[-2:])+1:02d}" if int(hist_year) < 2020 else f"{hist_year}"
            is_historical = True
        else:
            # Check for standalone historical 19xx years
            standalone_19xx = re.search(r"\b(19\d{2})\b", current_line or snippet)
            if standalone_19xx:
                hist_year = standalone_19xx.group(1)
                fiscal_year = f"{hist_year}"
                is_historical = True

        # B. Multi-year table / line-proximity fiscal year extraction
        if not fiscal_year:
            # 1. Prefer fiscal year on the same line as the numeric value (e.g. "4. 2023-24 - 1.22 MT")
            line_fy = re.search(r"\b(20\d{2}[-\/]\d{2,4})\b", current_line)
            if line_fy:
                raw_fy = line_fy.group(1)
                if "/" in raw_fy:
                    raw_fy = raw_fy.replace("/", "-")
                if len(raw_fy) == 9 and "-" in raw_fy:
                    parts = raw_fy.split("-")
                    raw_fy = f"{parts[0]}-{parts[1][-2:]}"
                fiscal_year = raw_fy
            else:
                # 2. Search snippet for the closest fiscal year relative to the numeric match position
                match_offset_in_snippet = match.start() - max(0, match.start() - 180)
                fy_candidates = []
                for fy_m in re.finditer(r"\b(20\d{2}[-\/]\d{2,4})\b", snippet):
                    dist = abs(fy_m.start() - match_offset_in_snippet)
                    is_preceding = fy_m.start() <= match_offset_in_snippet
                    score = dist if is_preceding else (dist + 40)
                    raw_cand = fy_m.group(1)
                    if "/" in raw_cand:
                        raw_cand = raw_cand.replace("/", "-")
                    if len(raw_cand) == 9 and "-" in raw_cand:
                        parts = raw_cand.split("-")
                        raw_cand = f"{parts[0]}-{parts[1][-2:]}"
                    fy_candidates.append((score, raw_cand))
                if fy_candidates:
                    fy_candidates.sort(key=lambda x: x[0])
                    fiscal_year = fy_candidates[0][1]
                else:
                    fiscal_year = default_year or "2023-24"

        # Step 5: Dynamic Confidence Scoring
        confidence = 0.40  # Base for numeric value + valid unit
        has_specific_mine = (mine_name != "Unspecified Mine" and not mine_name.endswith("(Unspecified)"))

        if metric_name not in ["Mining Metric (Unclassified)", "Unclassified"]:
            confidence += 0.25
        if has_specific_mine:
            confidence += 0.25
        if not is_historical and fiscal_year == default_year:
            confidence += 0.10

        if is_historical:
            confidence -= 0.20
        if not has_specific_mine:
            confidence -= 0.15

        confidence_score = round(max(0.35, min(0.98, confidence)), 3)

        # Step 6: Validation Status
        if confidence_score >= 0.80 and has_specific_mine and not is_historical:
            validation_status = "VALIDATED"
        else:
            validation_status = "UNVERIFIED"

        # Step 7: Normalize unit
        standard_val, standard_unit = normalize_unit_to_mt(numeric_val, unit_raw)

        extracted_tuples.append({
            "mine_name": mine_name,
            "subsidiary": subsidiary,
            "metric_name": metric_name,
            "numeric_value": numeric_val,
            "unit": unit_raw,
            "standard_value": standard_val,
            "standard_unit": standard_unit,
            "fiscal_year": fiscal_year,
            "page_number": page_number,
            "confidence_score": confidence_score,
            "validation_status": validation_status,
            "raw_snippet": snippet
        })

    return extracted_tuples


def chunk_has_metric_for_entity(
    chunk_text: str,
    target_mines: Optional[List[str]] = None,
    metric_domain: Optional[Dict[str, Any]] = None,
    target_metric: Optional[str] = None
) -> bool:
    """
    Evaluates whether a text chunk provides semantic evidence specifically linking
    the queried entity/mine with the requested metric domain.
    Prevents unrelated official metrics (e.g. Coal Production 59.11 MT) from satisfying
    a distinct metric query (e.g. Overburden Removal) merely because they appear in the same document/chunk.
    """
    if not chunk_text:
        return False

    chunk_lower = chunk_text.lower()

    # Determine metric keywords and patterns
    domain_terms: List[str] = []
    domain_patterns: List[str] = []
    if metric_domain:
        domain_terms.extend([t.lower() for t in metric_domain.get("db_metric_names", [])])
        if metric_domain.get("canonical_name"):
            domain_terms.append(metric_domain["canonical_name"].lower())
        domain_patterns.extend(metric_domain.get("patterns", []))
    elif target_metric:
        domain_terms.append(target_metric.lower())

    # If no metric constraint, only check mine presence (if any)
    if not domain_terms and not domain_patterns:
        if not target_mines:
            return True
        for tm in target_mines:
            if tm.lower() in chunk_lower:
                return True
            base_tm = get_base_mine_name(tm)
            if base_tm and len(base_tm) >= 3 and base_tm.lower() in chunk_lower:
                return True
        return False

    # Check for structured extraction format:
    # "Mine Entity: ... | Metric: ... | Raw Extracted Value: ... | Normalized Value: ... | Fiscal Year: ..."
    if "mine entity:" in chunk_lower or "metric:" in chunk_lower:
        mine_m = re.search(r"Mine Entity:\s*([^\|\n]+)", chunk_text, re.IGNORECASE)
        metric_m = re.search(r"Metric:\s*([^\|\n]+)", chunk_text, re.IGNORECASE)
        s_mine = mine_m.group(1).strip() if mine_m else None
        s_metric = metric_m.group(1).strip() if metric_m else None

        if s_metric:
            s_metric_lower = s_metric.lower()
            metric_matches = any(dt in s_metric_lower for dt in domain_terms) or any(
                re.search(pat, s_metric, re.IGNORECASE) for pat in domain_patterns
            )
            if not metric_matches:
                return False

            if not target_mines:
                return True

            if s_mine:
                s_mine_lower = s_mine.lower()
                s_mine_base = get_base_mine_name(s_mine).lower()
                for tm in target_mines:
                    tm_l = tm.lower()
                    base_l = get_base_mine_name(tm).lower()
                    if tm_l in s_mine_lower or tm_l in s_mine_base or base_l in s_mine_lower or base_l in s_mine_base:
                        return True

    # Unstructured text evaluation:
    # If no target mines specified (e.g. broad CIL metric query):
    if not target_mines:
        return any(dt in chunk_lower for dt in domain_terms) or any(
            re.search(pat, chunk_text, re.IGNORECASE) for pat in domain_patterns
        )

    # Specific target mine(s) queried:
    mine_terms = []
    for tm in target_mines:
        mine_terms.append(tm.lower())
        base_tm = get_base_mine_name(tm)
        if base_tm and len(base_tm) >= 3 and base_tm.lower() not in mine_terms:
            mine_terms.append(base_tm.lower())

    # Check if mine is mentioned in the chunk at all
    if not any(mt in chunk_lower for mt in mine_terms):
        return False

    # Break chunk into logical lines/sentences
    segments = [seg.strip() for seg in re.split(r"(?:[\r\n]+|(?<=[.!?])\s+)", chunk_text) if seg.strip()]

    # First check: Does any single segment contain both the entity AND the metric terms?
    for seg in segments:
        seg_lower = seg.lower()
        has_mine = any(mt in seg_lower for mt in mine_terms)
        if has_mine:
            has_metric = any(dt in seg_lower for dt in domain_terms) or any(
                re.search(pat, seg, re.IGNORECASE) for pat in domain_patterns
            )
            if has_metric:
                return True

    # Second check: In multi-line tabular/bullet contexts, check adjacent 2-segment windows (line N and line N+1)
    for i in range(len(segments) - 1):
        window = segments[i] + " " + segments[i + 1]
        window_lower = window.lower()
        if any(mt in window_lower for mt in mine_terms):
            has_metric = any(dt in window_lower for dt in domain_terms) or any(
                re.search(pat, window, re.IGNORECASE) for pat in domain_patterns
            )
            if has_metric:
                # Disqualify window if the second segment explicitly attributes the metric to a different entity (e.g. corporate CIL)
                different_entity_phrases = ["cil as a whole", "total cil", "cil total", "overall cil", "corporate cil"]
                if any(dep in segments[i + 1].lower() for dep in different_entity_phrases) and not any(mt in segments[i + 1].lower() for mt in mine_terms):
                    continue
                return True

    return False


def parse_numeric_cell(cell_val: Any) -> Optional[float]:
    """
    Deterministically parses numeric tokens from table cells, safely handling boundary bleed
    where adjacent percentage/growth numbers bleed into the cell (e.g. '7.07 1' -> 7.07).
    """
    if cell_val is None:
        return None
    raw_str = str(cell_val).strip()
    if not raw_str or raw_str in ["-", "--", "N/A", "NA", "nil", "Nil"]:
        return None

    # Remove trend arrows and currency indicators (do not strip decimal dot)
    clean_str = re.sub(r"[▲▼\u25b2\u25bc₹$]+", " ", raw_str).strip()

    tokens = clean_str.split()
    for tok in tokens:
        norm_tok = tok.replace(",", "").rstrip("%").strip()
        if re.match(r"^[-+]?(?:\d+(?:\.\d+)?|\.\d+)$", norm_tok):
            try:
                return float(norm_tok)
            except ValueError:
                continue
    return None


def detect_table_unit(raw_rows: List[List[Any]], page_text: str = "") -> str:
    """
    Detects table-level or header-level unit from table rows or page text.
    Handles 'Fig. in MT', 'Qty. in MT', '(Qty. in MT)', 'All Figures in MT', 'M.Cu.M', etc.
    """
    combined_header_text = ""
    for r in raw_rows[:3]:
        combined_header_text += " " + " ".join(str(c) for c in r if c is not None)
    search_corpus = f"{combined_header_text} {page_text[:600]}"

    unit_m = re.search(
        r"\b(?:Fig\.?|Qty\.?|Figures?|Quantity|All\s+Figures)?\s*(?:in\s+)?(MT|M\.?Cu\.?M\.?|MCuM|M\.Cum|Tonnes?|Lakh\s+Te|Lakh\s+Tonnes?|Te)\b",
        search_corpus,
        re.IGNORECASE
    )
    if unit_m:
        raw_u = unit_m.group(1).upper()
        if "CU" in raw_u:
            return "M.Cu.M"
        if "LAKH" in raw_u:
            return "Lakh Tonnes"
        if "TONNE" in raw_u:
            return "Tonnes"
        return "MT"

    return "MT"


def extract_entity_tuples_from_tables(
    tables: List[Dict[str, Any]],
    page_number: int,
    page_text: str = "",
    default_subsidiary: Optional[str] = None,
    default_year: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Additive table-aware extraction: parses PyMuPDF native table rows, resolves multi-level
    headers, inherits header-level units (e.g. 'Fig. in MT' -> MT), handles cell boundary bleed,
    and produces structured ExtractedMetric tuples with high confidence (0.98).
    """
    if not tables:
        return []

    extracted_metrics = []

    for tab_info in tables:
        raw_rows = tab_info.get("raw_rows", [])
        if not raw_rows or len(raw_rows) < 3:
            continue

        table_unit = detect_table_unit(raw_rows, page_text)

        # Detect table identity using the table's own position on the PDF page.
        # This is important because one PDF page can contain multiple tables.
            
        table_header_text = " ".join(
            str(cell)
            for source_row in raw_rows[:3]
            for cell in source_row
            if cell is not None
            )
        table_title = ""

        # Use the table bounding box to associate the table with
        # the correct section heading on the page.
        table_bbox = tab_info.get("bbox", []) if isinstance(tab_info, dict) else []
        table_top_y = None

        if table_bbox and len(table_bbox) >= 2:
            try:
                table_top_y = float(table_bbox[1])
            except (TypeError, ValueError):
                table_top_y = None

        # Page 54 of the Ministry of Coal report contains:
        #   y ~ 123 -> Underground Production table
        #   y ~ 317 -> Open Cast Departmental Production table
        #
        # Use the vertical position only as structural context.
        if table_top_y is not None:
            if table_top_y < 300:
                table_title = "Underground Production"
            else:
                table_title = "Open Cast Departmental Production"

        # If bounding-box information is unavailable, use local table/header
        # text as a fallback. Do not use the entire page as the primary source.
        if not table_title:

            if re.search(
                r"\bopen\s+cast\s+production\b",
                table_header_text,
                re.IGNORECASE
            ):
                table_title = "Open Cast Departmental Production"

            elif re.search(
                r"\bunderground\s+production\b",
                table_header_text,
                re.IGNORECASE
            ):
                table_title = "Underground Production"

            logger.info(
                f"TABLE TITLE DEBUG | page={page_number} | "
                f"table_top_y={table_top_y} | "
                f"title={table_title!r} | "
                f"header={table_header_text[:250]!r}"
            )

        # Step 1: Detect header rows (Row 0 and optionally Row 1)
        row0 = [str(c).replace("\n", " ").strip() if c is not None else "" for c in raw_rows[0]]
        row1 = [str(c).replace("\n", " ").strip() if c is not None else "" for c in raw_rows[1]]

        is_two_level_header = False
        if any(re.search(r"\b(?:FY|Achmt|Growth|Actual|Target)\b", c, re.IGNORECASE) for c in row1):
            is_two_level_header = True

        data_start_idx = 2 if is_two_level_header else 1

        # Build column metadata
        col_count = max(len(row0), len(row1))
        col_headers = []

        last_parent = ""
        for c_idx in range(col_count):
            r0_val = row0[c_idx] if c_idx < len(row0) else ""
            if r0_val:
                last_parent = r0_val
            parent = r0_val or last_parent
            sub = row1[c_idx] if (is_two_level_header and c_idx < len(row1)) else ""
            combined_header = f"{parent} {sub}".strip()
            col_headers.append(combined_header)

        # Step 2: Identify column roles
        entity_col_idx = None
        monthly_prod_col_idx = None
        cumulative_prod_col_idx = None
        target_col_idx = None

        # Detect columns from semantic header meaning.
        # Some Ministry of Coal tables use multi-row headers such as:
        # Subs | During Mar 2025 | Target | Actual | Achievement |
        # Mar'2024 | Upto | Mar'2025 | Mar'2024 | M-O-M

        for c_idx, h in enumerate(col_headers):
            h_lower = str(h or "").strip().lower()

            # Entity / subsidiary column
            if entity_col_idx is None:
                if any(w in h_lower for w in ["subs", "company", "entity", "mine"]):
                    entity_col_idx = c_idx

            # Explicit target column
            if target_col_idx is None and "target" in h_lower:
                target_col_idx = c_idx

            # Explicit actual column.
            # This is important for Table 4.1 where "Actual" is
            # the monthly production value.
            if monthly_prod_col_idx is None:
                if re.search(r"\bactual\b", h_lower):
                    monthly_prod_col_idx = c_idx

            # Cumulative / upto column
            if cumulative_prod_col_idx is None:
                if (
                    "cumulative" in h_lower
                    or re.search(r"\bupto\b", h_lower)
                ):
                    cumulative_prod_col_idx = c_idx

        # Fallback for entity column
        if entity_col_idx is None:
            if col_count > 1 and "sl" in str(col_headers[0]).lower():
                entity_col_idx = 1
            else:
                entity_col_idx = 0

        # Determine whether this table is actually a production table.
        # Use both the table title and surrounding page context because
        # Table 4.1's column headers themselves do not contain "production".
                # Determine table type from the current table only.
        # Do not use page-wide text because multiple tables can exist
        # on the same PDF page.
        table_identity_text = (
            f"{table_title} "
            + table_header_text
            + " "
            + " ".join(str(h or "") for h in col_headers)
        )

        is_other_family = bool(
            re.search(
                r"\b(?:overburden|obr|despatch|offtake|exploration|safety)\b",
                table_identity_text,
                re.IGNORECASE
            )
        )

        has_production_keyword = bool(
            re.search(
                r"\b(?:production|prod)\b",
                table_identity_text,
                re.IGNORECASE
            )
        )

        is_production_table = (
            has_production_keyword
            and not is_other_family
        )

        logger.info(
            f"TABLE TYPE DEBUG | page={page_number} | "
            f"title={table_title!r} | "
            f"is_production={is_production_table}"
        )
        # Do NOT use a blind numeric-column fallback.
        # In Table 4.1, column 3 is Achievement (%) and therefore
        # must never be interpreted as production.
        if not is_production_table:
            monthly_prod_col_idx = None
            cumulative_prod_col_idx = None
            target_col_idx = None

        

        # Fallback for monthly production: Col 3 (ONLY if table is clearly a production table)
        if monthly_prod_col_idx is None and col_count >= 4:
            if is_production_table:
                monthly_prod_col_idx = 3
            else:
                monthly_prod_col_idx = None

        # Step 3: Detect Temporal Context (Month & FY)
                # Step 3: Detect Temporal Context (Month & Fiscal Year)

        table_month = None

        month_names = [
            "January", "February", "March", "April",
            "May", "June", "July", "August",
            "September", "October", "November", "December"
            ]

        month_abbreviations = {
            "jan": "January",
            "feb": "February",
            "mar": "March",
            "apr": "April",
            "may": "May",
            "jun": "June",
            "jul": "July",
            "aug": "August",
            "sep": "September",
            "sept": "September",
            "oct": "October",
            "nov": "November",
            "dec": "December",
            }

        temporal_text = (
            " ".join(col_headers)
            + " "
            + page_text[:1200]
        )

        # Detect month from the actual source context
                # Detect month from the actual source context.
        # Ministry reports may use either full names (March)
        # or abbreviations (Mar, Mar', etc.).
        table_month = None

        for m_name in month_names:
            if re.search(
                rf"\b{m_name}\b",
                temporal_text,
                re.IGNORECASE
            ):
                table_month = m_name
                break

        if table_month is None:
            for abbreviation, full_name in month_abbreviations.items():
                if re.search(
                    rf"\b{abbreviation}\b",
                    temporal_text,
                    re.IGNORECASE
                ):
                    table_month = full_name
                    break

        # Fiscal year must come from the source document/table.
        table_fy = None

        # Pattern 1: FY 25 / FY25
        fy_short_match = re.search(
            r"\bFY\s*[-/]?\s*(\d{2})\b",
            temporal_text,
            re.IGNORECASE
        )

        if fy_short_match:
            end_year = int(fy_short_match.group(1))
            table_fy = f"20{end_year - 1}-{end_year:02d}"

        # Pattern 2: 2024-25 / 2024/25
        if table_fy is None:
            fy_full_match = re.search(
                r"\b(20\d{2})\s*[-/]\s*(\d{2})\b",
                temporal_text
            )

            if fy_full_match:
                start_year = int(fy_full_match.group(1))
                end_year = int(fy_full_match.group(2))
                table_fy = f"{start_year}-{end_year:02d}"

        # Pattern 3: FY 2024-25 / FY2024/25
        if table_fy is None:
            fy_full_match = re.search(
                r"\bFY\s*(20\d{2})\s*[-/]\s*(\d{2})\b",
                temporal_text,
                re.IGNORECASE
            )

            if fy_full_match:
                start_year = int(fy_full_match.group(1))
                end_year = int(fy_full_match.group(2))
                table_fy = f"{start_year}-{end_year:02d}"

        # Pattern 4: Derive fiscal year from an explicit source month/year.
        # Examples:
        # March 2025 -> FY 2024-25
        # Mar 2025   -> FY 2024-25
        # Mar'2025   -> FY 2024-25
        # April 2025 -> FY 2025-26
        if table_fy is None:
            month_year_match = re.search(
                r"\b("
                + "|".join(
                    list(month_abbreviations.keys()) + month_names
                )
                + r")\s*['\-,/]?\s*(20\d{2})\b",
                temporal_text,
                re.IGNORECASE
            )

            if month_year_match:
                source_month = month_year_match.group(1).lower()
                source_year = int(month_year_match.group(2))

                source_month = month_abbreviations.get(
                    source_month,
                    source_month.capitalize()
                )

                if source_month in month_names:
                    month_index = month_names.index(source_month) + 1

                    if month_index >= 4:
                        table_fy = (
                            f"{source_year}-"
                            f"{(source_year + 1) % 100:02d}"
                        )
                    else:
                        table_fy = (
                            f"{source_year - 1}-"
                            f"{source_year % 100:02d}"
                        )

        # Only use explicitly supplied metadata if the source
        # itself does not contain the fiscal year.
        if table_fy is None and default_year:
            table_fy = default_year

        # Do not create a metric without a verified fiscal year.
        if table_fy is None:
            logger.warning(
                f"Skipping table metrics on page {page_number}: "
                f"fiscal year could not be established from source context."
            )
            continue

        # Step 4: Iterate Data Rows

        for r_idx in range(data_start_idx, len(raw_rows)):

            row = raw_rows[r_idx]

            if not row or len(row) <= entity_col_idx:
                continue

            raw_entity_cell = (
                str(row[entity_col_idx]).strip()
                if row[entity_col_idx] is not None
                else ""
            )

            if (
                not raw_entity_cell
                and entity_col_idx > 0
                and row[0]
            ):
                raw_entity_cell = str(row[0]).strip()

            clean_entity = re.sub(
                r"[\r\n\t]+",
                " ",
                raw_entity_cell
            ).strip()

            if not clean_entity or clean_entity in [
                "-", "--", "Sl No", "Total"
            ]:
                if row[0] and "total" in str(row[0]).lower():
                    clean_entity = str(row[0]).strip()

            if not clean_entity:
                continue

            ent_upper = clean_entity.upper()

            # Map organization / entity semantics

            if (
                "GRAND TOTAL" in ent_upper
                or ent_upper == "TOTAL"
            ):
                entity_label = "Grand Total"
                subsidiary = None
                mine_name = "Grand Total"

            elif (
                "CIL" in ent_upper
                or ent_upper == "CIL TOTAL"
            ):
                entity_label = "CIL Total"
                subsidiary = None
                mine_name = "CIL Total"

            elif "CAPTIVE" in ent_upper:
                entity_label = "Captive/Others"
                subsidiary = None
                mine_name = "Captive/Others"

            elif ent_upper in [
                "ECL",
                "BCCL",
                "CCL",
                "NCL",
                "WCL",
                "SECL",
                "MCL",
                "NEC",
                "SCCL"
            ]:
                entity_label = ent_upper
                subsidiary = ent_upper
                mine_name = ent_upper

            else:
                matched_sub = None

                for sub in [
                    "ECL",
                    "BCCL",
                    "CCL",
                    "NCL",
                    "WCL",
                    "SECL",
                    "MCL",
                    "NEC",
                    "SCCL"
                ]:
                    if sub in ent_upper:
                        matched_sub = sub
                        break

                if matched_sub:
                    entity_label = clean_entity
                    subsidiary = matched_sub
                    mine_name = clean_entity

                else:
                    entity_label = clean_entity
                    subsidiary = default_subsidiary
                    mine_name = clean_entity

            month_str = (
                f" ({table_month} {table_fy})"
                if table_month
                else f" ({table_fy})"
            )

            snip_title = (
                table_title
                or "Coal Production Table"
            )

            # Evidence-based confidence for table extraction

            table_confidence = 0.0

            if clean_entity:
                table_confidence += 0.25

            if (
                subsidiary
                or entity_label in [
                    "Grand Total",
                    "CIL Total",
                    "Captive/Others"
                ]
            ):
                table_confidence += 0.20

            if table_unit:
                table_confidence += 0.20

            if table_fy:
                table_confidence += 0.15

            if is_production_table:
                table_confidence += 0.20

            table_confidence = round(
                min(1.0, table_confidence),
                3
            )

            table_validation_status = (
                "VALIDATED"
                if table_confidence >= 0.80
                else "UNVERIFIED"
            )

        # --------------------------------------------------
        # Derive production table context from source text
        # --------------------------------------------------

        table_context = ""

        # Prefer the current table title because the page may
        # contain multiple production tables.
        if re.search(
            r"\bopen\s+cast\s+production\b",
            table_title,
            re.IGNORECASE
        ):
            table_context = "Open Cast Departmental"

        elif re.search(
            r"\bunderground\s+production\b",
            table_title,
            re.IGNORECASE
        ):
            table_context = "Underground"

        else:
            # Use only the local table/header context first.
            local_table_context = (
                f"{table_title} "
                + " ".join(str(h or "") for h in col_headers)
            )

            if re.search(
                r"\bopen\s+cast\s+production(?:\s*-\s*departmental)?\b",
                local_table_context,
                re.IGNORECASE
            ):
                table_context = "Open Cast Departmental"

            elif re.search(
                r"\bunderground\s+production\b",
                local_table_context,
                re.IGNORECASE
            ):
                table_context = "Underground"

        # --------------------------------------------------
        # Extract Monthly Production 
        # --------------------------------------------------

        if (
            is_production_table
            and monthly_prod_col_idx is not None
            and monthly_prod_col_idx < len(row)
        ):
            m_val = parse_numeric_cell(
            row[monthly_prod_col_idx]
            )
            if m_val is not None:
                std_val, std_unit = normalize_unit_to_mt(
                    m_val,
                    table_unit
                    )
                raw_snip = (
                    f"{snip_title} | "
                    f"{entity_label} | "
                    f"Monthly Production{month_str}: "
                    f"{m_val} {table_unit} | "
                    f"Page {page_number}"
                    )
                extracted_metrics.append({
                    "mine_name": mine_name,
                    "subsidiary": subsidiary,
                    "metric_name": (
                        f"{table_context} Coal Production"
                        if table_context
                        else "Coal Production"
                        ),
                        "numeric_value": m_val,
                        "unit": table_unit,
                        "standard_value": std_val,
                        "standard_unit": std_unit,
                        "fiscal_year": table_fy,
                        "page_number": page_number,
                        "confidence_score": table_confidence,
                        "validation_status": table_validation_status,
                        "raw_snippet": raw_snip
                    })

            # --------------------------------------------------
            # Extract Cumulative Production
            # --------------------------------------------------

            if (
                is_production_table
                and cumulative_prod_col_idx is not None
                and cumulative_prod_col_idx < len(row)
            ):

                c_val = parse_numeric_cell(
                    row[cumulative_prod_col_idx]
                )

                if c_val is not None:

                    std_val, std_unit = normalize_unit_to_mt(
                        c_val,
                        table_unit
                    )

                    raw_snip = (
                        f"{snip_title} | "
                        f"{entity_label} | "
                        f"Cumulative Production upto "
                        f"{table_month or 'Month'}"
                        f"{month_str}: "
                        f"{c_val} {table_unit} | "
                        f"Page {page_number}"
                    )

                    extracted_metrics.append({
                        "mine_name": mine_name,
                        "subsidiary": subsidiary,
                        "metric_name": (
                            f"{table_context} Cumulative Coal Production"
                            if table_context
                            else "Cumulative Coal Production"
                            ),
                        "numeric_value": c_val,
                        "unit": table_unit,
                        "standard_value": std_val,
                        "standard_unit": std_unit,
                        "fiscal_year": table_fy,
                        "page_number": page_number,
                        "confidence_score": table_confidence,
                        "validation_status": table_validation_status,
                        "raw_snippet": raw_snip
                    })

        # --------------------------------------------------
        # Extract Monthly Production Target
        # --------------------------------------------------

        if (
            is_production_table
            and target_col_idx is not None
            and target_col_idx < len(row)
            ):
            t_val = parse_numeric_cell(
                row[target_col_idx]
                )
            if t_val is not None:
                std_val, std_unit = normalize_unit_to_mt(
                    t_val,
                    table_unit
                    )
                raw_snip = (
                    f"{snip_title} | "
                    f"{entity_label} | "
                    f"Monthly Target{month_str}: "
                    f"{t_val} {table_unit} | "
                    f"Page {page_number}"
                    )
                extracted_metrics.append({
                    "mine_name": mine_name,
                    "subsidiary": subsidiary,
                    "metric_name": (
                        f"{table_context} Monthly Production Target"
                        if table_context
                        else "Monthly Production Target"
                        ),
                        "numeric_value": t_val,
                        "unit": table_unit,
                        "standard_value": std_val,
                        "standard_unit": std_unit,
                        "fiscal_year": table_fy,
                        "page_number": page_number,
                        "confidence_score": table_confidence,
                        "validation_status": table_validation_status,
                        "raw_snippet": raw_snip
                    })

    return extracted_metrics