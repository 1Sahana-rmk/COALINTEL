"""Evidence-linked Step 2C structured fact extraction.

This module is intentionally conservative and generic.  It reads the common
DocumentResult/table/page representation, preserves raw evidence, and emits
candidate facts only when the source context supports a metric and value.
The existing domain adapter remains the compatibility path for legacy
``ExtractedMetric`` consumers; this service does not rewrite those records.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from app.models.structured_fact import StructuredFact
from app.services.document_models import DocumentResult, PageResult, TableResult
from app.services.normalization_service import normalize_unit_to_mt


SUBSIDIARY_ALIASES = {
    "central coalfields limited": "CCL",
    "central coalfields ltd": "CCL",
    "eastern coalfields limited": "ECL",
    "eastern coalfields ltd": "ECL",
    "bharat coking coal limited": "BCCL",
    "bharat coking coal ltd": "BCCL",
    "mahanadi coalfields limited": "MCL",
    "mahanadi coalfields ltd": "MCL",
    "northern coalfields limited": "NCL",
    "northern coalfields ltd": "NCL",
    "south eastern coalfields limited": "SECL",
    "south eastern coalfields ltd": "SECL",
    "western coalfields limited": "WCL",
    "western coalfields ltd": "WCL",
    "coal india limited": "CIL",
    "coal india ltd": "CIL",
    "central mine planning and design institute": "CMPDI",
    "cmpdi": "CMPDI",
}
SUBSIDIARIES = {"BCCL", "CCL", "ECL", "MCL", "NCL", "SECL", "WCL", "CMPDI", "CIL"}
KNOWN_MINE_NAMES = {
    "rajmahal oc": "Rajmahal OC",
    "rajmahal opencast": "Rajmahal OpenCast",
    "gevra oc": "Gevra OC",
    "dipka oc": "Dipka OC",
    "kusmunda oc": "Kusmunda OC",
    "moonidih ug": "Moonidih UG",
    "jhingurda oc": "Jhingurda OC",
}
STRUCTURAL_ENTITY_LABELS = {
    "sl no", "sl. no", "s no", "sr no", "sr. no", "serial no", "serial number",
    "row", "column", "mine", "subsidiary", "entity", "metric", "value",
}
AGGREGATE_LABELS = {"grand total", "total", "all india", "all india prod", "cil total", "overall total"}

METRIC_RULES: Sequence[Tuple[str, str, str]] = (
    ("BOREHOLE_DEPTH", r"\b(?:borehole|depth)\b", "BOREHOLE_DEPTH"),
    ("SEAM_THICKNESS", r"\b(?:seam\s+thickness|thickness)\b", "SEAM_THICKNESS"),
    ("GRADE", r"\bgrade\b", "GRADE"),
    ("COORDINATES", r"\b(?:latitude|longitude|coordinates?|lat\.?|long\.?)\b", "COORDINATES"),
    ("EXPLORATION_DRILLING", r"\b(?:borehole|drill(?:ing)?|meterage)\b", "EXPLORATION_DRILLING"),
    ("OVERBURDEN_REMOVAL", r"\b(?:overburden|obr|over\s*burden)\b", "OVERBURDEN_REMOVAL"),
    ("STRIPPING_RATIO", r"\bstripping\s+ratio\b", "STRIPPING_RATIO"),
    ("COAL_DISPATCH", r"\b(?:dispatch|despatch|offtake)\b", "COAL_DISPATCH"),
    ("PRODUCTION_TARGET", r"\b(?:production\s+)?target\b|\btarget\s+production\b", "PRODUCTION_TARGET"),
    ("ACHIEVEMENT_PERCENT", r"\bachievement\b|\btarget\s+achievement\b", "ACHIEVEMENT_PERCENT"),
    ("EFFICIENCY_PERCENT", r"\befficiency\b", "EFFICIENCY_PERCENT"),
    ("GROWTH_PERCENT", r"\bgrowth\b", "GROWTH_PERCENT"),
    ("RESERVE", r"\breserve\b", "RESERVE"),
    ("RESOURCE", r"\bresource\b", "RESOURCE"),
    ("CAPACITY", r"\bcapacity\b", "CAPACITY"),
    ("COAL_PRODUCTION", r"\b(?:coal\s+)?production\b|\boutput\b|\bmined\s+coal\b", "COAL_PRODUCTION"),
)

UNIT_PATTERNS: Sequence[Tuple[str, str]] = (
    ("Lakh Tonnes", r"\blakh\s+ton(?:nes?|s)\b"),
    ("Million Tonnes", r"\bmillion\s+ton(?:nes?|s)\b"),
    ("Thousand Tonnes", r"\bthousand\s+ton(?:nes?|s)\b"),
    ("M.Cu.M", r"\bm\.?\s*cu\.?\s*m\.?\b|\bmcum\b"),
    ("INR/MWh", r"\binr\s*/\s*mwh\b"),
    ("MT", r"\bmt\b"),
    ("KT", r"\bkt\b"),
    ("Tonnes", r"\bton(?:nes?|s)\b"),
    ("MU", r"\bmu\b"),
    ("BU", r"\bbu\b"),
    ("%", r"%|\bpercent(?:age)?\b"),
    ("m", r"(?<![A-Za-z])m\b"),
)

NUMBER_RE = re.compile(
    r"(?<![A-Za-z0-9])(?P<number>[+-]?(?:(?:\d{1,3}(?:,\d{3})+)|\d+)(?:\.\d+)?)(?P<percent>\s*%)?"
)
FY_RE = re.compile(r"\b(?:FY\s*)?((?:19|20)\d{2})[-/]((?:\d{2})|(?:\d{4}))\b", re.IGNORECASE)
MONTH_RE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[\s'/-]+(20\d{2})\b",
    re.IGNORECASE,
)
MONTH_NAMES = {
    "jan": "January", "january": "January", "feb": "February", "february": "February",
    "mar": "March", "march": "March", "apr": "April", "april": "April",
    "may": "May", "jun": "June", "june": "June", "jul": "July", "july": "July",
    "aug": "August", "august": "August", "sep": "September", "sept": "September",
    "september": "September", "oct": "October", "october": "October",
    "nov": "November", "november": "November", "dec": "December", "december": "December",
}
QUARTER_RE = re.compile(r"\b(Q[1-4])\s*(?:FY\s*)?((?:19|20)\d{2}[-/]\d{2,4})\b", re.IGNORECASE)
PAGE_REFERENCE_RE = re.compile(r"^\s*\d+(?:\s*[-–]\s*\d+)?\s*$")
BOREHOLE_ID_RE = re.compile(r"\bBH(?:[-\s/#:]?\d+[A-Z0-9-]*)\b", re.IGNORECASE)


@dataclass
class StructuredFactCandidate:
    document_id: Optional[int]
    page_number: Optional[int]
    entity_type: str
    entity_id: Optional[str]
    entity_name_raw: Optional[str]
    entity_name_canonical: Optional[str]
    entity_resolution_method: str
    entity_resolution_confidence: Optional[float]
    metric_type: str
    metric_name_raw: Optional[str]
    metric_name_canonical: Optional[str]
    metric_resolution_method: str
    metric_resolution_confidence: Optional[float]
    raw_value_text: Optional[str]
    raw_value_numeric: Optional[float]
    normalized_value: Optional[float]
    raw_unit: Optional[str]
    normalized_unit: Optional[str]
    period_raw: Optional[str]
    period_normalized: Optional[str]
    period_type: Optional[str]
    qualifiers: Dict[str, Any] = field(default_factory=dict)
    extraction_method: str = "RULE_BASED"
    extraction_confidence: float = 0.0
    evidence_type: str = "PAGE"
    evidence_locator: Dict[str, Any] = field(default_factory=dict)
    validation_status: str = "REVIEW_REQUIRED"
    validation_warnings: List[str] = field(default_factory=list)
    fact_status: str = "CANDIDATE"
    fact_key: str = ""
    duplicate_group_key: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _is_blank(value: Any) -> bool:
    return value is None or not _clean(value)


def _numeric(value: Any) -> Tuple[Optional[Decimal], Optional[str], Optional[str]]:
    if value is None or isinstance(value, bool):
        return None, None, None
    text = _clean(value)
    if not text:
        return None, None, None
    match = NUMBER_RE.search(text)
    if not match:
        return None, None, None
    raw = match.group("number")
    try:
        number = Decimal(raw.replace(",", ""))
    except InvalidOperation:
        return None, None, None
    return number, raw, "%" if match.group("percent") else None


def _unit(text: str) -> Optional[str]:
    clean = _clean(text)
    for canonical, pattern in UNIT_PATTERNS:
        if re.search(pattern, clean, re.IGNORECASE):
            return canonical
    return None


def _direct_unit_after(text: str) -> Optional[str]:
    """Return a unit only when it is directly attached to a value.

    A page line can contain several unrelated numbers.  Searching the whole
    line would incorrectly apply a later percent/unit marker to earlier
    values, so text extraction uses this adjacent-token helper instead.
    """
    clean = str(text or "")
    match = re.match(
        r"^\s*(?:\(?\s*)(lakh\s+ton(?:nes?|s)|million\s+ton(?:nes?|s)|"
        r"thousand\s+ton(?:nes?|s)|m\.?\s*cu\.?\s*m\.?|inr\s*/\s*mwh|"
        r"mt|kt|ton(?:nes?|s)|mu|bu|m)\b",
        clean,
        re.IGNORECASE,
    )
    return _unit(match.group(0)) if match else None


def _normalize_value(value: Optional[Decimal], raw_unit: Optional[str]) -> Tuple[Optional[float], Optional[str]]:
    if value is None:
        return None, None
    if not raw_unit:
        return float(value), None
    if raw_unit == "%":
        return float(value), "%"
    if raw_unit in {"MU", "BU", "INR/MWh", "m", "KT", "M.Cu.M"}:
        # These are not interchangeable with physical coal mass.  Preserve
        # the source unit until a domain-specific conversion is justified.
        return float(value), raw_unit
    normalized, unit = normalize_unit_to_mt(float(value), raw_unit)
    return float(normalized), unit


def resolve_entity(raw: Any) -> Tuple[str, Optional[str], Optional[str], str, float]:
    text = _clean(raw)
    lower = text.casefold()
    if not text or lower in STRUCTURAL_ENTITY_LABELS or re.fullmatch(r"[+-]?\d+(?:\.\d+)?", text):
        return "STRUCTURAL", None, text or None, "STRUCTURAL_LABEL_REJECTED", 1.0
    if lower in AGGREGATE_LABELS or lower.startswith("all india") or lower.startswith("grand total"):
        return "AGGREGATE", None, text, "AGGREGATE_LABEL", 0.95
    if text.upper() in SUBSIDIARIES:
        return "SUBSIDIARY", text.upper(), text, "SUBSIDIARY_ALIAS_EXACT", 1.0
    alias = SUBSIDIARY_ALIASES.get(lower)
    if alias:
        return "SUBSIDIARY", alias, text, "SUBSIDIARY_ALIAS_DICTIONARY", 0.98
    if lower in KNOWN_MINE_NAMES:
        return "MINE", KNOWN_MINE_NAMES[lower], text, "MINE_DICTIONARY", 0.98
    if re.search(r"\b(?:mine|oc|opencast|ug|underground|colliery|washery|project)\b", lower):
        return "MINE", None, text, "MINE_UNRESOLVED", 0.55
    if re.search(r"\b(?:limited|ltd|coalfields|corporation|institute|company)\b", lower):
        return "ORGANIZATION", None, text, "ORGANIZATION_UNRESOLVED", 0.60
    return "UNKNOWN", None, text, "UNRESOLVED", 0.30


def resolve_metric(context: str, raw_metric: Optional[str] = None) -> Tuple[str, str, float]:
    # A column header is the narrowest available semantic context for a table
    # cell.  Prefer it over the whole row, where a label such as "DRILLING"
    # can otherwise override a specific "Growth" or "Achievement" header.
    header = _clean(raw_metric)
    if header:
        for _, pattern, canonical in METRIC_RULES:
            if re.search(pattern, header, re.IGNORECASE):
                return canonical, "HEADER_RULE", 0.95
    text = _clean(context)
    for _, pattern, canonical in METRIC_RULES:
        if re.search(pattern, text, re.IGNORECASE):
            return canonical, "CONTEXT_RULE", 0.92
    return "UNCLASSIFIED", "UNCLASSIFIED", 0.20


def resolve_period(context: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    text = _clean(context)
    quarter = QUARTER_RE.search(text)
    if quarter:
        fy = quarter.group(2).replace("/", "-")
        if len(fy.split("-")[-1]) == 4:
            fy = f"{fy.split('-')[0]}-{fy.split('-')[-1][-2:]}"
        return quarter.group(0), f"{quarter.group(1).upper()} FY {fy}", "quarter"
    fy = FY_RE.search(text)
    month = MONTH_RE.search(text)
    if month:
        raw = month.group(0)
        month_name = MONTH_NAMES.get(month.group(1).casefold(), month.group(1).title())
        return raw, f"{month_name} {month.group(2)}", "monthly"
    if fy:
        end = fy.group(2)[-2:]
        normalized = f"FY {fy.group(1)}-{end}"
        return fy.group(0), normalized, "fiscal_year"
    if re.search(r"\bytd\b", text, re.IGNORECASE):
        return "YTD", "YTD", "ytd"
    if re.search(r"\bannual(?:ly)?\b", text, re.IGNORECASE):
        return "Annual", "Annual", "annual"
    return None, None, None


def _method_for_page(page: PageResult) -> str:
    engine = str(page.metadata.get("ocr_engine") or "").lower()
    source = str(page.metadata.get("ocr_source") or "").lower()
    if "paddle" in engine or "paddle" in source:
        return "PADDLE_OCR"
    if "tesseract" in engine or "tesseract" in source or "fallback" in source:
        return "TESSERACT_FALLBACK"
    if page.extraction_method == "NATIVE+OCR":
        return "TESSERACT_FALLBACK"
    return "NATIVE_TEXT"


def _table_method(table: TableResult) -> str:
    method = str(table.extraction_method or "").upper()
    if "PADDLE" in method:
        return "PADDLE_PPSTRUCTUREV3"
    if "OCR" in method:
        return "TESSERACT_FALLBACK"
    return "NATIVE_TABLE"


def _cell_map(table: TableResult) -> Dict[Tuple[int, int], Dict[str, Any]]:
    mapped: Dict[Tuple[int, int], Dict[str, Any]] = {}
    for cell in table.cells or []:
        if not isinstance(cell, dict):
            continue
        try:
            row = int(cell.get("row_index"))
            column = int(cell.get("column_index"))
        except (TypeError, ValueError):
            continue
        mapped[(row, column)] = cell
    return mapped


def _header_for_column(headers: Sequence[Any], column: int) -> str:
    return _clean(headers[column]) if column < len(headers) else ""


def _is_serial_number_header(header: str) -> bool:
    """Return whether a header explicitly labels a structural serial column."""
    normalized = re.sub(r"[^a-z0-9]+", " ", (header or "").casefold()).strip()
    return normalized in {
        "sl no",
        "sl number",
        "sr no",
        "sr number",
        "s no",
        "s number",
        "serial no",
        "serial number",
    }


def _is_period_label_cell(value: Any) -> bool:
    """Return whether a cell is an explicit period label, not a measurement."""
    text = _clean(value)
    return bool(
        re.fullmatch(r"(?:FY\s*\d{2,4}(?:\s*[-/]\s*\d{2,4})?|Q[1-4](?:\s+FY)?\s*\d{2,4}(?:\s*[-/]\s*\d{2,4})?)", text, re.IGNORECASE)
    )


def _is_numbered_label_cell(value: Any) -> bool:
    """Return whether a cell is a numbered section/row label."""
    text = _clean(value)
    return bool(re.search(r"(?:^|\s)\d+[.)]\s+[A-Za-z]", text))


def _row_entity(row: Sequence[Any], headers: Sequence[Any]) -> Tuple[Any, Optional[int]]:
    preferred = []
    for index, header in enumerate(headers):
        if re.search(r"\b(?:mine|subsidiary|company|entity|colliery|project)\b", _clean(header), re.IGNORECASE):
            preferred.append(index)
    for index in preferred + list(range(len(row))):
        if index >= len(row) or _is_blank(row[index]):
            continue
        number, _, _ = _numeric(row[index])
        if number is not None:
            continue
        text = _clean(row[index])
        if text.casefold() in STRUCTURAL_ENTITY_LABELS or re.fullmatch(r"\d+[.)]?", text):
            continue
        return row[index], index
    return None, None


def _is_navigation_table(table: TableResult) -> bool:
    """Identify TOC/index-like tables before domain fact generation.

    This is deliberately structural rather than document-specific.  A table
    must have an explicit page/navigation signal and a high proportion of
    complete page-reference cells.  A sparse legitimate measurement table is
    therefore not rejected merely because it contains blanks or numbers.
    """
    headers = [_clean(value) for value in (table.headers or [])]
    rows = list(table.rows or [])
    if len(rows) < 2 or not headers:
        return False
    title_and_headers = " ".join([_clean(table.title), *headers]).casefold()
    page_columns = [
        index for index, header in enumerate(headers)
        if re.search(r"\b(?:page|page\s*(?:no|number)|pg\.?|folio)\b", header, re.IGNORECASE)
    ]
    navigation_signal = bool(re.search(r"\b(?:contents|content|chapter|section|table|index|page|folio)\b", title_and_headers, re.IGNORECASE))
    if not page_columns or not navigation_signal:
        return False
    page_column = page_columns[-1]
    references = [
        _clean(row[page_column])
        for row in rows
        if isinstance(row, (list, tuple)) and page_column < len(row) and not _is_blank(row[page_column])
    ]
    if len(references) < 2:
        return False
    reference_ratio = sum(bool(PAGE_REFERENCE_RE.fullmatch(value)) for value in references) / len(references)
    return reference_ratio >= 0.75


def _confidence(method: str, structure: Optional[float], entity: float, metric: float, numeric: float, period: float) -> float:
    method_score = {
        "NATIVE_TABLE": 1.0,
        "NATIVE_TEXT": 0.90,
        "PADDLE_PPSTRUCTUREV3": 0.78,
        "PADDLE_OCR": 0.72,
        "TESSERACT_FALLBACK": 0.62,
    }.get(method, 0.55)
    structure_score = max(0.0, min(1.0, float(structure if structure is not None else 0.45)))
    score = (
        0.25 * method_score
        + 0.20 * structure_score
        + 0.20 * entity
        + 0.20 * metric
        + 0.10 * numeric
        + 0.05 * period
    )
    return round(max(0.0, min(0.99, score)), 4)


def _keys(candidate: StructuredFactCandidate) -> Tuple[str, str]:
    semantic = "|".join([
        str(candidate.entity_name_canonical or candidate.entity_name_raw or "").casefold(),
        str(candidate.metric_name_canonical or candidate.metric_name_raw or "").casefold(),
        str(candidate.period_normalized or "").casefold(),
        str(candidate.normalized_unit or candidate.raw_unit or "").casefold(),
        str(candidate.raw_value_text or ""),
    ])
    evidence = "|".join([
        str(candidate.document_id or ""), str(candidate.page_number or ""),
        str(candidate.evidence_type), str(candidate.evidence_locator.get("table_number", "")),
        str(candidate.evidence_locator.get("row_index", "")),
        str(candidate.evidence_locator.get("column_index", "")),
        str(candidate.evidence_locator.get("cell_ref", "")),
        semantic,
    ])
    return hashlib.sha256(evidence.encode("utf-8")).hexdigest(), hashlib.sha256(semantic.encode("utf-8")).hexdigest()


def _finish(candidate: StructuredFactCandidate) -> StructuredFactCandidate:
    warnings = list(candidate.validation_warnings)
    if candidate.entity_type in {"STRUCTURAL", "UNKNOWN"}:
        warnings.append("Entity is structural or unresolved; not authoritative.")
    if candidate.metric_name_canonical == "UNCLASSIFIED":
        warnings.append("Metric semantics are not sufficiently explicit.")
    if candidate.raw_value_numeric is None:
        warnings.append("Numeric value could not be safely parsed.")
    if not candidate.raw_unit:
        warnings.append("Unit is unavailable.")
    if candidate.metric_type in {"COAL_PRODUCTION", "PRODUCTION_TARGET", "COAL_DISPATCH", "OVERBURDEN_REMOVAL"} and not candidate.period_normalized:
        warnings.append("Reporting period is unavailable for a period-sensitive metric.")
    candidate.validation_warnings = list(dict.fromkeys(warnings))
    candidate.validation_status = "ACCEPTED" if not warnings and candidate.evidence_type != "PAGE" else "REVIEW_REQUIRED"
    candidate.fact_status = "ACCEPTED" if candidate.validation_status == "ACCEPTED" else "CANDIDATE"
    candidate.fact_key, candidate.duplicate_group_key = _keys(candidate)
    return candidate


def _candidate(
    *, document_id: Optional[int], page_number: Optional[int], context: str, entity_raw: Any,
    raw_value: Any, raw_unit: Optional[str], method: str, evidence_type: str,
    locator: Dict[str, Any], structure: Optional[float], metric_raw: Optional[str] = None,
    qualifiers: Optional[Dict[str, Any]] = None,
) -> Optional[StructuredFactCandidate]:
    number, raw_number, percent_marker = _numeric(raw_value)
    if number is None:
        return None
    # Do not infer a cell's unit from the whole row/context.  A neighbouring
    # percentage or physical-unit cell can otherwise contaminate this value.
    # Table callers provide the current header/title unit explicitly; text
    # callers provide the unit parsed directly after the number.
    unit = raw_unit or _unit(_clean(raw_value))
    if percent_marker:
        unit = "%"
    entity_type, entity_canonical, entity_text, entity_method, entity_conf = resolve_entity(entity_raw)
    metric_type, metric_method, metric_conf = resolve_metric(context, metric_raw)
    period_raw, period_normalized, period_type = resolve_period(context)
    normalized, normalized_unit = _normalize_value(number, unit)
    period_conf = 1.0 if period_normalized else 0.0
    numeric_conf = 1.0 if raw_number is not None else 0.0
    confidence = _confidence(method, structure, entity_conf, metric_conf, numeric_conf, period_conf)
    candidate = StructuredFactCandidate(
        document_id=document_id,
        page_number=page_number,
        entity_type=entity_type,
        entity_id=entity_canonical,
        entity_name_raw=entity_text,
        entity_name_canonical=entity_canonical,
        entity_resolution_method=entity_method,
        entity_resolution_confidence=entity_conf,
        metric_type=metric_type,
        metric_name_raw=_clean(metric_raw or context) or None,
        metric_name_canonical=metric_type,
        metric_resolution_method=metric_method,
        metric_resolution_confidence=metric_conf,
        raw_value_text=raw_number,
        raw_value_numeric=float(number),
        normalized_value=normalized,
        raw_unit=unit,
        normalized_unit=normalized_unit or unit,
        period_raw=period_raw,
        period_normalized=period_normalized,
        period_type=period_type,
        qualifiers=dict(qualifiers or {}),
        extraction_method=method,
        extraction_confidence=confidence,
        evidence_type=evidence_type,
        evidence_locator=dict(locator),
    )
    if percent_marker:
        candidate.qualifiers["percent_marker"] = True
    return _finish(candidate)


def _table_candidates(document_id: Optional[int], table: TableResult) -> List[StructuredFactCandidate]:
    if _is_navigation_table(table):
        # The persisted DocumentTable remains available for audit/evidence
        # review.  Its page-reference rows are not measurement facts.
        return []
    headers = list(table.headers or [])
    rows = list(table.rows or [])
    if not headers and rows:
        headers, rows = rows[0], rows[1:]
    cells = _cell_map(table)
    method = _table_method(table)
    candidates: List[StructuredFactCandidate] = []
    for row_offset, row in enumerate(rows, start=1):
        entity_raw, entity_col = _row_entity(row, headers)
        for column, value in enumerate(row):
            if _is_blank(value):
                continue
            if _is_period_label_cell(value):
                # Layout extraction can place a repeated fiscal-year label in
                # a numeric-looking cell.  It is context, not a measurement.
                continue
            if _is_numbered_label_cell(value):
                # Numbered section labels such as "1. DRILLING BY CMPDI" are
                # structural text, not the numeric value one in the label.
                continue
            number, _, _ = _numeric(value)
            if number is None:
                continue
            header = _header_for_column(headers, column)
            if _is_serial_number_header(header):
                # Preserve the source table, but do not emit a serial number
                # as an unclassified domain fact.
                continue
            row_context = " ".join(_clean(value) for value in row if not _is_blank(value))
            title_context = _clean(table.title)
            context = " | ".join(part for part in [title_context, header, row_context] if part)
            unit = _unit(header) or _unit(_clean(value)) or _unit(title_context)
            cell = cells.get((row_offset, column), {})
            locator = {
                "page_number": table.page_number,
                "table_number": table.table_number,
                "row_index": row_offset,
                "column_index": column,
                "cell_text": _clean(value),
                "header_context": header,
                "bounding_box": cell.get("bounding_box") or cell.get("bbox"),
                "sheet_name": table.sheet_name,
            }
            if cell.get("coordinate"):
                locator["cell_ref"] = cell.get("coordinate")
            if cell.get("value") is not None:
                locator["raw_cell_value"] = cell.get("value")
            if cell.get("displayed_value") is not None:
                locator["displayed_value"] = cell.get("displayed_value")
            if table.formulas:
                cell_ref = locator.get("cell_ref")
                if cell_ref and cell_ref in table.formulas:
                    locator["formula"] = table.formulas[cell_ref]
            candidate = _candidate(
                document_id=document_id,
                page_number=table.page_number,
                context=context,
                entity_raw=entity_raw,
                raw_value=value,
                raw_unit=unit,
                method=method,
                evidence_type="TABLE_CELL",
                locator=locator,
                structure=table.extraction_confidence,
                metric_raw=header,
                qualifiers={
                    "table_title": title_context,
                    "header_context": header,
                    "sheet_name": table.sheet_name,
                    "table_warnings": list(table.warnings or []),
                    "entity_column_index": entity_col,
                },
            )
            if candidate:
                if table.warnings:
                    candidate.validation_warnings.extend(table.warnings)
                    candidate = _finish(candidate)
                candidates.append(candidate)
    return candidates


def _text_candidates(document_id: Optional[int], page: PageResult) -> List[StructuredFactCandidate]:
    method = _method_for_page(page)
    candidates: List[StructuredFactCandidate] = []
    lines = [line.strip() for line in (page.text or "").splitlines() if line.strip()]
    for line_index, line in enumerate(lines):
        for match in NUMBER_RE.finditer(line):
            unit = _direct_unit_after(line[match.end():])
            if match.group("percent"):
                unit = "%"
            if not unit:
                continue
            context = line
            entity_raw = None
            known = re.search(r"\b(?:[A-Z][A-Za-z0-9.-]+(?:\s+[A-Za-z0-9.-]+){0,4})\s+(?:OC|OpenCast|UG|Mine|Colliery|Project)\b", line)
            if known:
                entity_raw = known.group(0)
            else:
                prefix = line[:match.start()].split(":", 1)[0].strip()
                if prefix and len(prefix.split()) <= 8:
                    prefix_lower = prefix.casefold()
                    if prefix.upper() in SUBSIDIARIES:
                        entity_raw = prefix
                    elif prefix.split() and prefix.split()[0].upper() in SUBSIDIARIES:
                        entity_raw = prefix.split()[0]
                    else:
                        for alias in sorted(SUBSIDIARY_ALIASES, key=len, reverse=True):
                            if prefix_lower.startswith(alias + " "):
                                entity_raw = alias
                                break
            block = next((block for block in page.blocks if match.group("number") in (block.text or "")), None)
            locator = {
                "page_number": page.page_number,
                "line_index": line_index,
                "text_snippet": line,
                "bounding_box": block.bbox if block else None,
                "block_confidence": block.confidence if block else None,
            }
            candidate = _candidate(
                document_id=document_id,
                page_number=page.page_number,
                context=context,
                entity_raw=entity_raw,
                raw_value=match.group(0),
                raw_unit=unit,
                method=method,
                evidence_type="TEXT_BLOCK" if block else "PAGE_TEXT",
                locator=locator,
                structure=block.confidence if block else page.confidence,
                qualifiers={"line_index": line_index},
            )
            if candidate:
                candidates.append(candidate)

    # Preserve explicit non-numeric identifiers that are facts in their own
    # right. They remain reviewable candidates until domain validation accepts
    # their semantics; no numeric zero is fabricated for them.
    identifier_patterns = (
        (BOREHOLE_ID_RE, "BOREHOLE_ID"),
        (r"\b(?:coal\s+)?seam\s*[:#-]\s*([A-Za-z0-9 IVX-]+)", "SEAM_ID"),
        (r"\bgrade\s*[:#-]\s*([A-Z][0-9]+)\b", "GRADE"),
    )
    for pattern, metric_type in identifier_patterns:
        matches = pattern.finditer(page.text or "") if hasattr(pattern, "finditer") else re.finditer(
            pattern, page.text or "", re.IGNORECASE
        )
        for match in matches:
            raw_value = _clean(match.group(1) if match.lastindex else match.group(0))
            start_line = (page.text or "")[:match.start()].count("\n")
            line = lines[start_line] if start_line < len(lines) else match.group(0)
            if metric_type == "BOREHOLE_ID":
                surrounding = (page.text or "")[max(0, match.start() - 120):min(len(page.text or ""), match.end() + 120)]
                if not re.search(r"\bborehole\b|\bbh\s*(?:id|no|number)\b", surrounding, re.IGNORECASE):
                    continue
            block = next((block for block in page.blocks if raw_value in (block.text or "")), None)
            locator = {
                "page_number": page.page_number,
                "line_index": start_line,
                "text_snippet": line,
                "bounding_box": block.bbox if block else None,
                "block_confidence": block.confidence if block else None,
            }
            entity_raw = "Borehole" if metric_type == "BOREHOLE_ID" else None
            candidate = StructuredFactCandidate(
                document_id=document_id,
                page_number=page.page_number,
                entity_type="UNKNOWN" if entity_raw is None else "GEOLOGICAL_FEATURE",
                entity_id=None,
                entity_name_raw=entity_raw,
                entity_name_canonical=None,
                entity_resolution_method="UNRESOLVED" if entity_raw is None else "FEATURE_LABEL",
                entity_resolution_confidence=0.30 if entity_raw is None else 0.80,
                metric_type=metric_type,
                metric_name_raw=metric_type,
                metric_name_canonical=metric_type,
                metric_resolution_method="EXPLICIT_LABEL",
                metric_resolution_confidence=0.90,
                raw_value_text=raw_value,
                raw_value_numeric=None,
                normalized_value=None,
                raw_unit=None,
                normalized_unit=None,
                period_raw=None,
                period_normalized=None,
                period_type=None,
                qualifiers={},
                extraction_method=method,
                extraction_confidence=_confidence(method, page.confidence, 0.80, 0.90, 1.0, 0.0),
                evidence_type="TEXT_BLOCK" if block else "PAGE_TEXT",
                evidence_locator=locator,
                validation_warnings=["Identifier fact has no numeric value; domain validation is required."],
            )
            candidates.append(_finish(candidate))
    return candidates


def extract_structured_fact_candidates(result: DocumentResult, document_id: Optional[int] = None) -> List[StructuredFactCandidate]:
    """Extract conservative, evidence-linked candidates from the common model."""
    candidates: List[StructuredFactCandidate] = []
    for table in result.tables:
        candidates.extend(_table_candidates(document_id, table))
    for page in result.pages:
        # Tables are the preferred evidence source. Text candidates on a table
        # page are still emitted only as candidates; persistence deduplication
        # keeps the two evidence paths distinct and auditable.
        candidates.extend(_text_candidates(document_id, page))

    unique: Dict[str, StructuredFactCandidate] = {}
    for candidate in candidates:
        if candidate.fact_key not in unique:
            unique[candidate.fact_key] = candidate
    return list(unique.values())


def validate_ai_fact_proposal(proposal: Dict[str, Any], result: DocumentResult) -> Dict[str, Any]:
    """Validate an AI proposal against supplied persisted evidence.

    This is a proposal gate, not an AI implementation and it never persists a
    proposal by itself.  A future model adapter may call it, but unsupported
    values, units, entities, periods, pages, or table cells are rejected before
    they can become structured facts.
    """
    warnings: List[str] = []
    page_number = proposal.get("page_number")
    page = next((item for item in result.pages if item.page_number == page_number), None)
    if page is None:
        return {"accepted": False, "warnings": ["Evidence page is not present in the supplied document result."]}

    raw_value = _clean(proposal.get("raw_value_text"))
    if not raw_value:
        warnings.append("AI proposal has no source value token.")
    evidence_type = str(proposal.get("evidence_type") or "PAGE_TEXT").upper()
    locator = proposal.get("evidence_locator") or {}
    context_parts: List[str] = []
    if evidence_type == "TABLE_CELL":
        table_number = locator.get("table_number")
        table = next((item for item in result.tables if item.page_number == page_number and item.table_number == table_number), None)
        if table is None:
            warnings.append("Claimed table evidence does not exist.")
        else:
            row_index = locator.get("row_index")
            column_index = locator.get("column_index")
            if row_index is None or column_index is None:
                warnings.append("Table-cell row/column coordinates are missing.")
            else:
                cell = _cell_map(table).get((int(row_index), int(column_index)))
                rows = table.rows or []
                row_offset = int(row_index) - 1
                row_value = rows[row_offset][int(column_index)] if 0 <= row_offset < len(rows) and int(column_index) < len(rows[row_offset]) else None
                source_value = cell.get("value") if cell and cell.get("value") is not None else row_value
                source_text = _clean(source_value)
                if not source_text or (raw_value and source_text != raw_value):
                    source_number, _, _ = _numeric(source_text)
                    proposed_number, _, _ = _numeric(raw_value)
                    if source_number is None or proposed_number is None or source_number != proposed_number:
                        warnings.append("Proposed value cannot be located in the claimed table cell.")
                context_parts.extend([_clean(table.title), _clean(table.headers[int(column_index)] if int(column_index) < len(table.headers) else ""), " ".join(_clean(value) for value in (rows[row_offset] if 0 <= row_offset < len(rows) else []))])
    else:
        source_text = page.text or ""
        if raw_value and raw_value not in source_text:
            warnings.append("Proposed value token is not present in supplied page text.")
        context_parts.append(source_text)

    context = " | ".join(part for part in context_parts if part)
    for key, label in (("entity_name_raw", "entity"), ("metric_name_raw", "metric"), ("period_raw", "period"), ("raw_unit", "unit")):
        value = _clean(proposal.get(key))
        if value and value.casefold() not in context.casefold():
            warnings.append(f"Proposed {label} is not supported by the supplied evidence context.")
    return {"accepted": not warnings, "warnings": list(dict.fromkeys(warnings))}


def persist_structured_fact_candidates(
    db: Session,
    document_id: int,
    candidates: Iterable[StructuredFactCandidate],
    table_ids_by_number: Optional[Dict[Tuple[int, int], int]] = None,
    page_ids_by_number: Optional[Dict[int, int]] = None,
) -> int:
    """Idempotently persist candidates without changing legacy metrics."""
    table_ids_by_number = table_ids_by_number or {}
    page_ids_by_number = page_ids_by_number or {}
    existing = {
        row.fact_key
        for row in db.query(StructuredFact.fact_key).filter(StructuredFact.document_id == document_id).all()
    }
    inserted = 0
    for candidate in candidates:
        if candidate.fact_key in existing:
            continue
        locator = dict(candidate.evidence_locator)
        table_id = None
        if candidate.evidence_type == "TABLE_CELL":
            table_id = table_ids_by_number.get((candidate.page_number or 0, int(locator.get("table_number") or 0)))
        db.add(StructuredFact(
            document_id=document_id,
            document_page_id=page_ids_by_number.get(candidate.page_number or 0),
            page_number=candidate.page_number,
            document_table_id=table_id,
            entity_type=candidate.entity_type,
            entity_id=candidate.entity_id,
            entity_name_raw=candidate.entity_name_raw,
            entity_name_canonical=candidate.entity_name_canonical,
            entity_resolution_method=candidate.entity_resolution_method,
            entity_resolution_confidence=candidate.entity_resolution_confidence,
            metric_type=candidate.metric_type,
            metric_name_raw=candidate.metric_name_raw,
            metric_name_canonical=candidate.metric_name_canonical,
            metric_resolution_method=candidate.metric_resolution_method,
            metric_resolution_confidence=candidate.metric_resolution_confidence,
            raw_value_text=candidate.raw_value_text,
            raw_value_numeric=candidate.raw_value_numeric,
            normalized_value=candidate.normalized_value,
            raw_unit=candidate.raw_unit,
            normalized_unit=candidate.normalized_unit,
            period_raw=candidate.period_raw,
            period_normalized=candidate.period_normalized,
            period_type=candidate.period_type,
            qualifiers_json=candidate.qualifiers,
            extraction_method=candidate.extraction_method,
            extraction_confidence=candidate.extraction_confidence,
            evidence_type=candidate.evidence_type,
            evidence_locator_json=locator,
            validation_status=candidate.validation_status,
            validation_warnings_json=candidate.validation_warnings,
            fact_status=candidate.fact_status,
            fact_key=candidate.fact_key,
            duplicate_group_key=candidate.duplicate_group_key,
        ))
        existing.add(candidate.fact_key)
        inserted += 1
    return inserted
