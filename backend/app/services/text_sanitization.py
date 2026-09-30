"""Sanitize untrusted extracted text before persistence or downstream processing.

Document and OCR parsers consume untrusted bytes. PostgreSQL rejects embedded
NUL characters in text values, and other control characters can make logs,
JSON, or downstream parsing unsafe. This module is the single normalization
boundary for the common ``DocumentResult`` representation.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from app.services.document_models import DocumentResult


def _is_unsafe_control(character: str) -> bool:
    codepoint = ord(character)
    # Preserve normal whitespace used by extracted documents.
    if character in {"\t", "\n", "\r"}:
        return False
    # Remove C0 controls, DEL, and C1 controls. Valid Unicode letters, symbols,
    # combining marks, and emoji are retained unchanged.
    return codepoint < 0x20 or codepoint == 0x7F or 0x80 <= codepoint <= 0x9F


def sanitize_text_value(value: Any) -> Tuple[Any, Optional[Dict[str, Any]]]:
    """Return a text value with unsafe controls removed and change metadata.

    ``original_offsets`` refer to positions in the original field value. No
    existing COALINTEL provenance field uses character offsets; PDF/OCR
    geometry remains unchanged. The offsets are retained so a future textual
    citation layer can account for the normalization explicitly.
    """
    if not isinstance(value, str):
        return value, None

    removed_offsets: List[int] = []
    removed_codepoints: List[str] = []
    cleaned: List[str] = []
    for offset, character in enumerate(value):
        if _is_unsafe_control(character):
            removed_offsets.append(offset)
            codepoint = f"U+{ord(character):04X}"
            if codepoint not in removed_codepoints:
                removed_codepoints.append(codepoint)
            continue
        cleaned.append(character)

    if not removed_offsets:
        return value, None

    return "".join(cleaned), {
        "removed_count": len(removed_offsets),
        "removed_codepoints": removed_codepoints,
        "original_offsets": removed_offsets[:100],
        "offsets_truncated": len(removed_offsets) > 100,
    }


def _sanitize_nested(value: Any, location: str, changes: List[Dict[str, Any]]) -> Any:
    if isinstance(value, str):
        sanitized, change = sanitize_text_value(value)
        if change:
            changes.append({"location": location, **change})
        return sanitized
    if isinstance(value, list):
        return [_sanitize_nested(item, f"{location}[{index}]", changes) for index, item in enumerate(value)]
    if isinstance(value, tuple):
        return tuple(_sanitize_nested(item, f"{location}[{index}]", changes) for index, item in enumerate(value))
    if isinstance(value, dict):
        sanitized_dict: Dict[Any, Any] = {}
        for key, item in value.items():
            sanitized_key = key
            if isinstance(key, str):
                sanitized_key, key_change = sanitize_text_value(key)
                if key_change:
                    changes.append({"location": f"{location}.<key>", **key_change})
            sanitized_dict[sanitized_key] = _sanitize_nested(item, f"{location}.{sanitized_key}", changes)
        return sanitized_dict
    return value


def sanitize_document_result(result: DocumentResult) -> DocumentResult:
    """Sanitize every text-bearing field in a common document result in place."""
    changes: List[Dict[str, Any]] = []

    for page in result.pages:
        page.text = _sanitize_nested(page.text, f"page[{page.page_number}].text", changes)
        for block_index, block in enumerate(page.blocks):
            block.text = _sanitize_nested(block.text, f"page[{page.page_number}].block[{block_index}].text", changes)
            block.metadata = _sanitize_nested(block.metadata, f"page[{page.page_number}].block[{block_index}].metadata", changes)
        page.metadata = _sanitize_nested(page.metadata, f"page[{page.page_number}].metadata", changes)

    for table_index, table in enumerate(result.tables):
        table_location = f"page[{table.page_number}].table[{table_index}]"
        table.title = _sanitize_nested(table.title, f"{table_location}.title", changes)
        table.headers = _sanitize_nested(table.headers, f"{table_location}.headers", changes)
        table.rows = _sanitize_nested(table.rows, f"{table_location}.rows", changes)
        table.cells = _sanitize_nested(table.cells, f"{table_location}.cells", changes)
        table.merged_cells = _sanitize_nested(table.merged_cells, f"{table_location}.merged_cells", changes)
        table.formulas = _sanitize_nested(table.formulas, f"{table_location}.formulas", changes)
        table.displayed_values = _sanitize_nested(table.displayed_values, f"{table_location}.displayed_values", changes)
        table.warnings = _sanitize_nested(table.warnings, f"{table_location}.warnings", changes)

    for image_index, image in enumerate(result.images):
        image_location = f"page[{image.page_number or 'unknown'}].image[{image_index}]"
        image.text = _sanitize_nested(image.text, f"{image_location}.text", changes)
        image.metadata = _sanitize_nested(image.metadata, f"{image_location}.metadata", changes)

    result.metadata = _sanitize_nested(result.metadata, "document.metadata", changes)
    result.warnings = _sanitize_nested(result.warnings, "document.warnings", changes)

    if not changes:
        return result

    by_page: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for change in changes:
        location = change["location"]
        page_key = location.split(".", 1)[0]
        by_page[page_key].append(change)

    # Keep a compact, machine-readable provenance record on the document and
    # page. Full extracted text is deliberately never copied into warnings or
    # logs.
    summary = {
        "warning_code": "TEXT_SANITIZED_INVALID_CONTROL_CHARACTER",
        "changed_field_count": len(changes),
        "removed_count": sum(change["removed_count"] for change in changes),
        "removed_codepoints": sorted({codepoint for change in changes for codepoint in change["removed_codepoints"]}),
        "fields": changes,
    }
    result.metadata["text_sanitization"] = summary
    for page in result.pages:
        page_changes = by_page.get(f"page[{page.page_number}]")
        if page_changes:
            page.metadata["text_sanitization"] = {
                "warning_code": "TEXT_SANITIZED_INVALID_CONTROL_CHARACTER",
                "changed_field_count": len(page_changes),
                "removed_count": sum(change["removed_count"] for change in page_changes),
                "removed_codepoints": sorted({codepoint for change in page_changes for codepoint in change["removed_codepoints"]}),
                "fields": page_changes,
            }

    for page_key, page_changes in sorted(by_page.items()):
        removed_count = sum(change["removed_count"] for change in page_changes)
        codepoints = sorted({codepoint for change in page_changes for codepoint in change["removed_codepoints"]})
        result.warnings.append(
            "TEXT_SANITIZED_INVALID_CONTROL_CHARACTER: removed "
            f"{removed_count} unsafe character(s) from {page_key} "
            f"({', '.join(codepoints)}); original text offsets are recorded in provenance"
        )
    return result
