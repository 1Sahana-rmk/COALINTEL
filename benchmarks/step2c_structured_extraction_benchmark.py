"""Deterministic Step 2C structured-extraction benchmark.

This runner is outside the production ingestion path.  It evaluates the
evidence-linked candidate layer against a small frozen, field-labelled corpus
and writes JSON/Markdown results.  Real Ministry PDFs are inventoried but are
not scored without independently labelled fact/evidence ground truth.
"""

from __future__ import annotations

import json
import argparse
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.document_models import DocumentResult, EvidenceBlock, PageResult, TableResult  # noqa: E402
from app.services.parsing_service import parse_document_result  # noqa: E402
from app.services.structured_extraction_service import extract_structured_fact_candidates  # noqa: E402


CORPUS_PATH = Path(__file__).with_name("step2c_structured_extraction_corpus.json")
JSON_PATH = Path(__file__).with_name("STEP2C_STRUCTURED_EXTRACTION_BENCHMARK.json")
MARKDOWN_PATH = Path(__file__).with_name("STEP2C_STRUCTURED_EXTRACTION_BENCHMARK.md")


def _load_corpus() -> dict[str, Any]:
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


def _result(case: dict[str, Any]) -> DocumentResult:
    pages = []
    for raw in case.get("pages", []):
        blocks = [EvidenceBlock(**block) for block in raw.get("blocks", [])]
        page_fields = {key: value for key, value in raw.items() if key in {
            "page_number", "text", "extraction_method", "confidence", "classification",
            "width", "height", "metadata"
        }}
        page_fields["blocks"] = blocks
        pages.append(PageResult(**page_fields))
    tables = []
    for raw in case.get("tables", []):
        fields = {key: value for key, value in raw.items() if key in {
            "page_number", "table_number", "title", "headers", "rows", "bounding_box",
            "extraction_confidence", "extraction_method", "sheet_name", "cells",
            "merged_cells", "formulas", "displayed_values", "warnings"
        }}
        tables.append(TableResult(**fields))
    return DocumentResult(
        document_id=case.get("document_id"),
        filename=case["filename"],
        file_type=case["file_type"],
        pages=pages,
        tables=tables,
    )


def _value_match(predicted: dict[str, Any], expected: dict[str, Any]) -> bool:
    if expected.get("value_text") is not None:
        return predicted.get("raw_value_text") == expected["value_text"]
    actual = predicted.get("raw_value_numeric")
    wanted = expected.get("value")
    return actual is not None and wanted is not None and abs(float(actual) - float(wanted)) < 1e-9


def _fact_match(predicted: dict[str, Any], expected: dict[str, Any]) -> bool:
    return (
        (predicted.get("entity_name_canonical") == expected.get("entity_canonical"))
        and predicted.get("metric_type") == expected.get("metric_type")
        and _value_match(predicted, expected)
        and (predicted.get("raw_unit") == expected.get("unit") if expected.get("unit") is not None else True)
        and (predicted.get("period_normalized") == expected.get("period") if expected.get("period") is not None else True)
        and predicted.get("evidence_type") == expected.get("evidence_type")
        and predicted.get("page_number") == expected.get("page")
    )


def _evidence_match(predicted: dict[str, Any], expected: dict[str, Any]) -> bool:
    if not _fact_match(predicted, expected):
        return False
    locator = predicted.get("evidence_locator") or {}
    for expected_key, locator_key in (("table", "table_number"), ("row", "row_index"), ("column", "column_index")):
        if expected.get(expected_key) is not None and locator.get(locator_key) != expected[expected_key]:
            return False
    return True


def _component_match(predicted: dict[str, Any], expected: dict[str, Any]) -> bool:
    """Find a candidate for an independently scored labelled component."""
    if not _value_match(predicted, expected):
        return False
    if expected.get("entity_canonical") is not None and predicted.get("entity_name_canonical") != expected["entity_canonical"]:
        return False
    if predicted.get("metric_type") != expected.get("metric_type"):
        return False
    return True


def _prf(expected: Iterable[Any], predicted: Iterable[Any]) -> dict[str, Any]:
    expected_set, predicted_set = set(expected), set(predicted)
    tp = len(expected_set & predicted_set)
    precision = tp / len(predicted_set) if predicted_set else 0.0
    recall = tp / len(expected_set) if expected_set else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4), "true_positive": tp, "expected": len(expected_set), "predicted": len(predicted_set)}


def _evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    candidates = extract_structured_fact_candidates(_result(case), document_id=case.get("document_id"))
    predicted = [candidate.as_dict() for candidate in candidates]
    expected = case.get("expected_facts", [])
    remaining = list(predicted)
    matches = []
    evidence_matches = 0
    for expected_fact in expected:
        match_index = next((index for index, item in enumerate(remaining) if _fact_match(item, expected_fact)), None)
        if match_index is None:
            matches.append(False)
            continue
        item = remaining.pop(match_index)
        matches.append(True)
        evidence_matches += int(_evidence_match(item, expected_fact))

    entity_expected = [fact.get("entity_canonical") for fact in expected if fact.get("entity_canonical")]
    entity_predicted = [fact.get("entity_name_canonical") for fact in predicted if fact.get("entity_name_canonical")]
    metric_expected = [fact.get("metric_type") for fact in expected]
    metric_predicted = [fact.get("metric_type") for fact in predicted if fact.get("metric_type") != "UNCLASSIFIED"]
    numeric_expected = [fact["value"] for fact in expected if fact.get("value") is not None]
    numeric_predicted = [fact.get("raw_value_numeric", fact.get("raw_value_text")) for fact in predicted if fact.get("raw_value_numeric", fact.get("raw_value_text")) is not None]
    exact_count = sum(matches)
    return {
        "case_id": case["case_id"],
        "document_id": case.get("document_id"),
        "filename": case["filename"],
        "expected_fact_count": len(expected),
        "candidate_count": len(predicted),
        "full_fact_exact_count": exact_count,
        "full_fact_exact_rate": round(exact_count / len(expected), 4) if expected else None,
        "provenance_correct_count": evidence_matches,
        "provenance_correct_rate": round(evidence_matches / len(expected), 4) if expected else None,
        "entity": _prf(entity_expected, entity_predicted),
        "metric": _prf(metric_expected, metric_predicted),
        "value_exact_rate": round(exact_count / len(expected), 4) if expected else None,
        "unit_exact_rate": round(sum(1 for fact in expected if fact.get("unit") is None or any(_component_match(item, fact) and item.get("raw_unit") == fact["unit"] for item in predicted)) / len(expected), 4) if expected else None,
        "period_exact_rate": round(sum(1 for fact in expected if fact.get("period") is None or any(_component_match(item, fact) and item.get("period_normalized") == fact["period"] for item in predicted)) / len(expected), 4) if expected else None,
        "numeric_exact_rate": round(sum(1 for expected_value in numeric_expected if any(abs(float(item.get("raw_value_numeric")) - float(expected_value)) < 1e-9 for item in predicted if item.get("raw_value_numeric") is not None)) / len(numeric_expected), 4) if numeric_expected else None,
        "structural_review_candidates": sum(1 for item in predicted if item.get("entity_type") == "STRUCTURAL"),
        "status_counts": dict(Counter(item.get("validation_status") for item in predicted)),
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Step 2C Structured Extraction Benchmark",
        "",
        f"Corpus: `{report['corpus_version']}`; scored cases: {report['case_count']}",
        "",
        "This is a deterministic candidate-extraction benchmark. A fact is only counted as a full match when entity, metric, value, unit/period where labelled, evidence type, and page agree. Real Ministry PDFs are inventoried separately because they do not have field-level frozen ground truth in this repository.",
        "",
        "## Aggregate results",
        "",
        f"- Expected labelled facts: **{report['aggregate']['expected_fact_count']}**",
        f"- Extracted candidates: **{report['aggregate']['candidate_count']}**",
        f"- Full fact exact rate: **{report['aggregate']['full_fact_exact_rate']:.4f}**",
        f"- Evidence-link exact rate: **{report['aggregate']['provenance_correct_rate']:.4f}**",
        f"- Numeric exact rate: **{report['aggregate']['numeric_exact_rate']:.4f}**",
        f"- Entity macro P/R/F1: **{report['aggregate']['entity']['precision']:.4f} / {report['aggregate']['entity']['recall']:.4f} / {report['aggregate']['entity']['f1']:.4f}**",
        f"- Metric macro P/R/F1: **{report['aggregate']['metric']['precision']:.4f} / {report['aggregate']['metric']['recall']:.4f} / {report['aggregate']['metric']['f1']:.4f}**",
        f"- Value/unit/period exact rates: **{report['aggregate']['value_exact_rate']:.4f} / {report['aggregate']['unit_exact_rate']:.4f} / {report['aggregate']['period_exact_rate']:.4f}**",
        f"- Structural candidates marked review: **{report['aggregate']['structural_review_candidates']}**",
        "",
        "## Per-case matrix",
        "",
        "| case | expected | candidates | full fact | provenance | numeric | warnings/review |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for case in report["cases"]:
        lines.append(f"| {case['case_id']} | {case['expected_fact_count']} | {case['candidate_count']} | {case['full_fact_exact_rate'] if case['full_fact_exact_rate'] is not None else 'n/a'} | {case['provenance_correct_rate'] if case['provenance_correct_rate'] is not None else 'n/a'} | {case['numeric_exact_rate'] if case['numeric_exact_rate'] is not None else 'n/a'} | {case['structural_review_candidates']} |")
    lines.extend([
        "",
        "## Real-document smoke checks",
        "",
        "The runner can be invoked with `--include-real` to parse the first two locally available golden PDFs. These are integration smoke checks only, not accuracy claims, because no field-level labels are stored for them.",
    ])
    for smoke in report.get("real_document_smoke", []):
        if smoke.get("error_type"):
            lines.append(f"- `{smoke['path']}`: **ERROR** {smoke['error_type']} — {smoke['error']}")
        else:
            lines.append(f"- `{smoke['path']}`: {smoke['pages']} pages, {smoke['tables']} tables, {smoke['candidate_facts']} candidate facts, {smoke['elapsed_ms']} ms (unlabelled)")
    if not report.get("real_document_smoke"):
        lines.append("- Not run in the default deterministic mode.")
    lines.extend([
        "",
        "## Limitations",
        "",
        "- This layer is conservative rule/context extraction, not an LLM extractor. AI-assisted proposals are not enabled by default.",
        "- Real Ministry documents listed in the corpus inventory require independently labelled fact/evidence annotations before their accuracy can be reported honestly.",
        "- OCR text without reliable table/cell structure remains a review candidate; no cell geometry is fabricated.",
        "- Legacy `extracted_metrics`, validation, conflict, and Step 2B consumers are intentionally unchanged.",
    ])
    return "\n".join(lines) + "\n"


def _real_document_smoke(inventory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for item in inventory[:2]:
        path = ROOT / item["path"]
        if not path.exists():
            continue
        started = time.perf_counter()
        try:
            parsed = parse_document_result(
                str(path),
                "PDF",
                file_bytes=path.read_bytes(),
                filename=path.name,
            )
            candidates = extract_structured_fact_candidates(parsed, document_id=None)
            results.append({
                "path": item["path"],
                "pages": len(parsed.pages),
                "tables": len(parsed.tables),
                "images": len(parsed.images),
                "candidate_facts": len(candidates),
                "warnings": parsed.warnings,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                "ground_truth_scored": False,
            })
        except Exception as exc:
            results.append({
                "path": item["path"],
                "error_type": type(exc).__name__,
                "error": str(exc)[:300],
                "ground_truth_scored": False,
            })
    return results


def run(include_real: bool = False) -> dict[str, Any]:
    corpus = _load_corpus()
    cases = [_evaluate_case(case) for case in corpus["cases"]]
    expected_count = sum(case["expected_fact_count"] for case in cases)
    candidate_count = sum(case["candidate_count"] for case in cases)
    exact_count = sum(case["full_fact_exact_count"] for case in cases)
    provenance_count = sum(case["provenance_correct_count"] for case in cases)
    numeric_values = [case["numeric_exact_rate"] for case in cases if case["numeric_exact_rate"] is not None]
    structural_review = sum(case["structural_review_candidates"] for case in cases)
    inventory = [{"path": path, "exists": (ROOT / path).exists()} for path in corpus.get("real_document_inventory", [])]

    def average(field: str) -> float:
        values = [case[field] for case in cases if case[field] is not None]
        return round(sum(values) / len(values), 4) if values else 0.0

    def average_prf(field: str) -> dict[str, Any]:
        values = [case[field] for case in cases]
        return {
            "precision": round(sum(item["precision"] for item in values) / len(values), 4),
            "recall": round(sum(item["recall"] for item in values) / len(values), 4),
            "f1": round(sum(item["f1"] for item in values) / len(values), 4),
            "aggregation": "macro-average across labelled cases",
        }
    report = {
        "benchmark": "STEP2C_STRUCTURED_EXTRACTION",
        "corpus_version": corpus["corpus_version"],
        "case_count": len(cases),
        "cases": cases,
        "aggregate": {
            "expected_fact_count": expected_count,
            "candidate_count": candidate_count,
            "full_fact_exact_count": exact_count,
            "full_fact_exact_rate": round(exact_count / expected_count, 4) if expected_count else 0.0,
            "provenance_correct_count": provenance_count,
            "provenance_correct_rate": round(provenance_count / expected_count, 4) if expected_count else 0.0,
            "numeric_exact_rate": round(sum(numeric_values) / len(numeric_values), 4) if numeric_values else 0.0,
            "entity": average_prf("entity"),
            "metric": average_prf("metric"),
            "value_exact_rate": average("value_exact_rate"),
            "unit_exact_rate": average("unit_exact_rate"),
            "period_exact_rate": average("period_exact_rate"),
            "structural_review_candidates": structural_review,
        },
        "real_document_inventory": inventory,
        "real_document_smoke": _real_document_smoke(inventory) if include_real else [],
        "notes": [
            "Benchmark runs outside production ingestion.",
            "No real-document accuracy is claimed without frozen field-level labels.",
        ],
    }
    JSON_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    MARKDOWN_PATH.write_text(_markdown(report), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-real", action="store_true", help="Parse two locally available real PDFs as unlabelled smoke checks.")
    args = parser.parse_args()
    result = run(include_real=args.include_real)
    print(json.dumps(result["aggregate"], indent=2))
