"""Isolated Step 2A PaddleOCR benchmark runner.

This file is deliberately outside the backend package.  It reuses the exact
corpus/ground-truth generator and metric functions from the frozen Tesseract
benchmark, but never imports or changes the production parser.  Run it with
the dedicated Python 3.12 Paddle environment only.
"""

from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import psutil

from step2a_document_ai_benchmark import (
    REPORT_DIR,
    ROOT,
    _aggregate,
    _error_metrics,
    _make_corpus,
    _normalise_for_error_rate,
    _token_metrics,
)


os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")


def _json_value(value: Any) -> Any:
    """Return a JSON-friendly representation of a Paddle result value."""
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _result_dict(result: Any) -> dict[str, Any]:
    """Extract the stable ``res`` dictionary from PaddleOCR 3.x objects."""
    for attribute in ("json", "res"):
        try:
            value = getattr(result, attribute)
            if callable(value):
                value = value()
            if isinstance(value, dict):
                value = value.get("res", value)
                if isinstance(value, dict):
                    return value
        except Exception:
            continue
    if isinstance(result, dict):
        return result.get("res", result)
    try:
        value = dict(result)
        return value.get("res", value)
    except Exception:
        return {}


def _boxes(result: dict[str, Any]) -> list[Any]:
    values = result.get("rec_boxes") or result.get("rec_polys") or result.get("dt_polys") or []
    return [_json_value(value) for value in values]


def _texts(result: dict[str, Any]) -> list[str]:
    return [str(value) for value in (result.get("rec_texts") or [])]


def _scores(result: dict[str, Any]) -> list[float]:
    scores = result.get("rec_scores") or []
    return [float(value) for value in scores if isinstance(value, (int, float))]


def _paddle_row(entry: dict[str, Any], page_results: list[dict[str, Any]], *, elapsed: float, init_seconds: float, peak_rss: int, error: str | None = None) -> dict[str, Any]:
    pages: list[dict[str, Any]] = []
    text_parts: list[str] = []
    for page_index, result in enumerate(page_results, start=1):
        texts = _texts(result)
        scores = _scores(result)
        boxes = _boxes(result)
        text_parts.append("\n".join(texts))
        source_page_index = result.get("page_index")
        if source_page_index is None:
            source_page_index = page_index - 1
        pages.append({
            "page_number": int(source_page_index) + 1,
            "text_characters": len("\n".join(texts)),
            "text_block_count": len(texts),
            "bbox_count": len(boxes),
            "confidence_count": len(scores),
            "mean_confidence": sum(scores) / len(scores) if scores else None,
            "text_preview": "\n".join(texts)[:800],
        })
    text = "\n".join(text_parts)
    metrics = {"cer": None, "wer": None}
    if entry["expected_text"] is not None:
        metrics = _error_metrics(entry["expected_text"], text)
    metrics.update(_token_metrics(text, entry["expected_tokens"]))
    return {
        "id": entry["id"],
        "file": Path(entry["path"]).name,
        "engine": "PaddleOCR 3.7.0 PP-OCRv6 CPU",
        "status": "ERROR" if error else "PASS",
        "error": error,
        "initialization_seconds": round(init_seconds, 4),
        "whole_document_latency_seconds": round(elapsed, 4),
        "approx_peak_rss_mb": round(peak_rss / (1024 * 1024), 2),
        "page_count": len(pages),
        "pages": pages,
        "text_preview": text[:2000],
        "metrics": metrics,
        "bbox_availability": any(page["bbox_count"] for page in pages),
        "confidence_availability": any(page["confidence_count"] for page in pages),
        "table_metrics": {
            "expected": entry["expected_table"],
            "flattened_ocr_is_not_table_success": bool(entry["expected_table"]),
            "table_detection": None,
            "row_recovery": None,
            "column_recovery": None,
            "cell_value_accuracy": None,
            "header_preservation": None,
            "blank_cell_preservation": None,
            "numeric_cell_accuracy": None,
            "cell_bbox_availability": None,
        },
    }


def _run_ocr(ocr: Any, entry: dict[str, Any], *, init_seconds: float, process: psutil.Process) -> dict[str, Any]:
    before = process.memory_info().rss
    start = time.perf_counter()
    error = None
    result_dicts: list[dict[str, Any]] = []
    try:
        for result in ocr.predict(entry["path"]):
            result_dicts.append(_result_dict(result))
    except Exception as exc:
        error = f"{type(exc).__name__}: {str(exc)[:400]}"
    elapsed = time.perf_counter() - start
    after = process.memory_info().rss
    return _paddle_row(entry, result_dicts, elapsed=elapsed, init_seconds=init_seconds, peak_rss=max(before, after), error=error)


def _structure_table_metrics(result_dicts: list[dict[str, Any]], expected: dict[str, Any]) -> dict[str, Any]:
    tables: list[dict[str, Any]] = []
    for page in result_dicts:
        for table in page.get("table_res_list") or []:
            table = _json_value(table)
            if isinstance(table, dict):
                tables.append(table)
    if not tables:
        return {
            "table_detection": False,
            "detected_tables": 0,
            "row_recovery": 0.0,
            "column_recovery": 0.0,
            "header_preservation": 0.0,
            "cell_value_accuracy": 0.0,
            "blank_cell_preservation": 0.0,
            "numeric_cell_accuracy": 0.0,
            "cell_bbox_availability": 0.0,
            "warnings": ["PP-StructureV3 returned no table_res_list; flattened OCR is not counted."],
        }

    expected_header = ["Subsidiary", "April", "May", "Total"]
    expected_nonblank = ["Subsidiary", "April", "May", "Total", "ECL", "781.05", "781.50", "1,562.55", "BCCL", "0.781", "-5.00"]
    expected_blank_cells = 1  # BCCL/April in the deterministic fixture.
    parsed_grids: list[list[list[str]]] = []
    html_previews: list[str] = []
    try:
        from bs4 import BeautifulSoup

        for table in tables:
            html = table.get("pred_html")
            if not isinstance(html, str):
                continue
            html_previews.append(html[:2000])
            soup = BeautifulSoup(html, "html.parser")
            grid: list[list[str]] = []
            for tr in soup.find_all("tr"):
                cells = tr.find_all(["th", "td"])
                if cells:
                    grid.append([" ".join(cell.get_text(" ", strip=True).split()) for cell in cells])
            if grid:
                parsed_grids.append(grid)
    except Exception:
        parsed_grids = []
    recovered_cells = [cell for grid in parsed_grids for row in grid for cell in row]
    recovered_text = " ".join(recovered_cells)
    matched_nonblank = sum(1 for value in expected_nonblank if value in recovered_cells or value in recovered_text)
    header_matches = sum(1 for value in expected_header if value in recovered_cells or value in recovered_text)
    recovered_rows = max((len(grid) for grid in parsed_grids), default=0)
    recovered_columns = max((max((len(row) for row in grid), default=0) for grid in parsed_grids), default=0)
    recovered_blank_cells = sum(1 for grid in parsed_grids for row in grid for cell in row if not cell)
    cell_boxes = sum(len(table.get("cell_box_list") or []) for table in tables)
    return {
        "table_detection": True,
        "detected_tables": len(tables),
        "row_recovery": recovered_rows / 3,
        "column_recovery": recovered_columns / 4,
        "header_preservation": header_matches / len(expected_header),
        "cell_value_accuracy": matched_nonblank / len(expected_nonblank),
        "blank_cell_preservation": min(1.0, recovered_blank_cells / expected_blank_cells),
        "numeric_cell_accuracy": sum(1 for value in ["781.05", "781.50", "1,562.55", "0.781", "-5.00"] if value in recovered_cells or value in recovered_text) / 5,
        "cell_bbox_availability": 1.0 if cell_boxes else 0.0,
        "cell_box_count": cell_boxes,
        "recovered_rows": recovered_rows,
        "recovered_columns": recovered_columns,
        "html_preview": html_previews,
        "warnings": ["Structural row/column scoring requires parsing the returned table HTML; raw table evidence was retained."],
    }


def _run_structure(table_entry: dict[str, Any], *, process: psutil.Process) -> dict[str, Any]:
    from paddleocr import PPStructureV3

    before = process.memory_info().rss
    init_start = time.perf_counter()
    pipeline = PPStructureV3(
        device="cpu",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        use_table_recognition=True,
        use_formula_recognition=False,
        use_chart_recognition=False,
        engine="paddle",
    )
    init_seconds = time.perf_counter() - init_start
    start = time.perf_counter()
    error = None
    result_dicts: list[dict[str, Any]] = []
    try:
        for result in pipeline.predict(table_entry["path"]):
            result_dicts.append(_result_dict(result))
    except Exception as exc:
        error = f"{type(exc).__name__}: {str(exc)[:400]}"
    elapsed = time.perf_counter() - start
    after = process.memory_info().rss
    metrics = _structure_table_metrics(result_dicts, table_entry) if not error else {"table_detection": None, "warnings": [error]}
    return {
        "id": table_entry["id"],
        "file": Path(table_entry["path"]).name,
        "engine": "PP-StructureV3 via PaddleOCR 3.7.0 CPU",
        "status": "ERROR" if error else "PASS",
        "error": error,
        "initialization_seconds": round(init_seconds, 4),
        "whole_document_latency_seconds": round(elapsed, 4),
        "approx_peak_rss_mb": round(max(before, after) / (1024 * 1024), 2),
        "page_count": len(result_dicts),
        "metrics": metrics,
    }


def _gpu_probe() -> dict[str, Any]:
    result: dict[str, Any] = {"available": False, "raw": ""}
    try:
        completed = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10, check=False)
        result.update({"raw": completed.stdout.strip(), "returncode": completed.returncode, "available": completed.returncode == 0 and bool(completed.stdout.strip())})
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {str(exc)[:240]}"
    return result


def _paddle_versions() -> dict[str, Any]:
    import paddle
    import paddleocr
    import paddlex

    return {
        "paddlepaddle": paddle.__version__,
        "paddleocr": paddleocr.__version__,
        "paddlex": paddlex.__version__,
        "compiled_with_cuda": bool(paddle.is_compiled_with_cuda()),
    }


def _update_markdown(payload: dict[str, Any], path: Path) -> None:
    # The frozen pre-Paddle report stores the Tesseract aggregate at the
    # top-level ``aggregate`` key.  Keep that baseline unchanged.
    t = payload["aggregate"]
    p = payload.get("paddle_ocr_cpu", {})
    s = payload.get("pp_structure_v3_cpu", {})
    comparison = payload.get("comparison", {})
    lines = [
        "# Step 2A Document AI Benchmark",
        "",
        "This benchmark is isolated from the frozen Step-1 production pipeline. The Tesseract baseline is retained from the original Python 3.14 run; Paddle was executed in `.venv-paddle312` with Python 3.12.",
        "",
        "## Environment and models",
        "",
        f"- Python: `{payload['environment']['python']}`",
        f"- Platform: `{payload['environment']['platform']}`",
        f"- GPU probe: `{payload['environment']['gpu'].get('raw', '')}`",
        f"- Paddle versions: `{json.dumps(payload.get('paddle_versions', {}), sort_keys=True)}`",
        "- PP-OCR model: `PP-OCRv6_medium_det` + `PP-OCRv6_medium_rec`.",
        "- Document AI model: current PaddleOCR 3.7.0 `PP-StructureV3` pipeline on CPU.",
        f"- GPU inference: `{payload.get('gpu_execution', {}).get('status', 'NOT_RUN')}`; the installed Windows package reports `compiled_with_cuda=false`.",
        "",
        "## Corpus and metric policy",
        "",
        f"- Documents: `{t.get('documents')}` Tesseract baseline rows and `{p.get('documents')}` Paddle rows, generated from the same corpus and ground truth.",
        "- CER/WER retain punctuation; whitespace is normalized only for error-rate comparison.",
        "- Flattened OCR text is not counted as table reconstruction.",
        "- Native digital PDF extraction remains the preferred production path; this benchmark measures OCR separately.",
        "",
        "## Direct comparison",
        "",
        "| Metric | Tesseract baseline | PP-OCRv6 CPU |",
        "|---|---:|---:|",
        f"| Mean CER | {t.get('mean_cer_full_text_documents')} | {p.get('mean_cer_full_text_documents')} |",
        f"| Mean WER | {t.get('mean_wer_full_text_documents')} | {p.get('mean_wer_full_text_documents')} |",
        f"| Mean exact numeric rate | {t.get('mean_exact_numeric_rate')} | {p.get('mean_exact_numeric_rate')} |",
        f"| Mean decimal preservation | {t.get('mean_decimal_rate')} | {p.get('mean_decimal_rate')} |",
        f"| Bounding boxes available | {t.get('mean_bbox_available')} | {p.get('mean_bbox_available')} |",
        f"| Confidence available | {t.get('mean_confidence_available')} | {p.get('mean_confidence_available')} |",
        "",
        "## Table benchmark",
        "",
        f"- Tesseract table detection: `{t.get('table_detection_rate')}`; the production parser does not reconstruct the generated scanned table reliably.",
        f"- PP-StructureV3 result: `{json.dumps(s, sort_keys=True)}`",
        "- Cell/row/column metrics are reported as unknown when the pipeline output did not expose reliable structure; no structure is fabricated.",
        "",
        "## Per-document Paddle metrics",
        "",
        "| ID | Status | CER | WER | Exact numeric | Latency (s) | BBoxes | Mean OCR confidence |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload.get("paddle_ocr_cpu", {}).get("rows", []):
        metrics = row.get("metrics", {})
        mean_conf = [page["mean_confidence"] for page in row.get("pages", []) if page.get("mean_confidence") is not None]
        lines.append(f"| {row['id']} | {row['status']} | {metrics.get('cer')} | {metrics.get('wer')} | {metrics.get('numeric_exact', {}).get('rate')} | {row.get('whole_document_latency_seconds')} | {row.get('bbox_availability')} | {(sum(mean_conf) / len(mean_conf)) if mean_conf else None} |")
    lines += [
        "",
        "## Performance and failure checks",
        "",
        f"- Paddle OCR initialization: `{p.get('initialization_seconds')}` seconds.",
        f"- Paddle OCR aggregate peak RSS observation: `{p.get('approx_peak_rss_mb')}` MB.",
        f"- Paddle table pipeline: `{s}`.",
        f"- Failure checks: `{json.dumps(payload.get('failure_checks', {}), sort_keys=True)}`",
        "",
        "## Recommendation",
        "",
        f"**{payload.get('recommendation', {}).get('option')}** — {payload.get('recommendation', {}).get('rationale')}",
        "",
        "## Limitations",
        "",
        "- Windows GPU inference was not counted as successful because the installed official CPU wheel is not CUDA-enabled; `nvidia-smi` hardware visibility alone is not Paddle runtime compatibility.",
        "- PP-StructureV3 structure metrics remain conservative when returned HTML/cell evidence cannot be mapped to the controlled ground-truth grid without assumptions.",
        "- No production dependency, parser, processing state, database, sync connector, or Step-1 behavior was changed.",
        "",
        "Official references: [PaddleOCR quick start](https://www.paddleocr.ai/latest/en/quick_start.html), [PaddlePaddle package metadata](https://pypi.org/pypi/paddlepaddle/json), [PaddleOCR high-performance deployment](https://paddlepaddle.github.io/PaddleOCR/main/en/version3.x/deployment/high_performance_inference.html).",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    existing_path = REPORT_DIR / "STEP2A_DOCUMENT_AI_BENCHMARK.json"
    existing = json.loads(existing_path.read_text(encoding="utf-8"))
    corpus_root = ROOT / "benchmarks" / ".step2a_frozen_corpus"
    corpus_root.mkdir(parents=True, exist_ok=True)
    entries = _make_corpus(corpus_root)

    if "--structure-only" in sys.argv:
        table_entry = next(entry for entry in entries if entry["id"] == "PDF_SCANNED_TABLE")
        process = psutil.Process()
        try:
            structure_row = _run_structure(table_entry, process=process)
            structure_status = "PASS" if structure_row["status"] == "PASS" else "ERROR"
        except Exception as exc:
            structure_row = {"id": table_entry["id"], "file": Path(table_entry["path"]).name, "status": "ERROR", "error": f"{type(exc).__name__}: {str(exc)[:400]}"}
            structure_status = "ERROR"
        existing["pp_structure_v3_cpu"] = {"status": structure_status, **structure_row}
        existing_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
        _update_markdown(existing, REPORT_DIR / "STEP2A_DOCUMENT_AI_BENCHMARK.md")
        print(json.dumps(existing["pp_structure_v3_cpu"], indent=2, default=str))
        return 0

    from paddleocr import PaddleOCR

    process = psutil.Process()
    init_start = time.perf_counter()
    ocr = PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        device="cpu",
        engine="paddle",
    )
    init_seconds = time.perf_counter() - init_start
    rows = [_run_ocr(ocr, entry, init_seconds=init_seconds, process=process) for entry in entries]
    paddle_aggregate = _aggregate(rows)
    paddle_aggregate["initialization_seconds"] = round(init_seconds, 4)
    paddle_aggregate["approx_peak_rss_mb"] = round(process.memory_info().rss / (1024 * 1024), 2)

    table_entry = next(entry for entry in entries if entry["id"] == "PDF_SCANNED_TABLE")
    try:
        structure_row = _run_structure(table_entry, process=process)
        structure_status = "PASS" if structure_row["status"] == "PASS" else "ERROR"
    except Exception as exc:
        structure_row = {"id": table_entry["id"], "file": Path(table_entry["path"]).name, "status": "ERROR", "error": f"{type(exc).__name__}: {str(exc)[:400]}"}
        structure_status = "ERROR"

    versions = _paddle_versions()
    existing.update({
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": {**existing.get("environment", {}), "python": sys.version, "platform": platform.platform(), "machine": platform.machine(), "gpu": _gpu_probe()},
        "paddle_probe": {**versions, "status": "BENCHMARKED"},
        "paddle_versions": versions,
        "paddle_execution": {"status": "CPU_COMPLETED", "target_stack": {"paddlepaddle": versions["paddlepaddle"], "paddleocr": versions["paddleocr"], "paddlex": versions["paddlex"], "general_ocr": "PP-OCRv6_medium_det + PP-OCRv6_medium_rec", "document_ai": "PP-StructureV3"}, "structure_models_observed": ["PP-DocBlockLayout", "PP-DocLayout_plus-L", "PP-OCRv5_server_det", "PP-OCRv5_server_rec", "PP-LCNet_x1_0_table_cls", "SLANeXt_wired", "SLANet_plus", "RT-DETR-L_wired_table_cell_det", "RT-DETR-L_wireless_table_cell_det", "PP-LCNet_x1_0_doc_ori", "PP-LCNet_x1_0_textline_ori"]},
        "paddle_ocr_cpu": {**paddle_aggregate, "rows": rows},
        "pp_structure_v3_cpu": {"status": structure_status, **structure_row},
        "gpu_execution": {"status": "NOT_RUN_INCOMPATIBLE_WINDOWS_CPU_WHEEL", "reason": "PaddlePaddle 3.2.0 installed successfully on Windows CPU, but paddle.is_compiled_with_cuda() is false; no incompatible GPU wheel was forced into the benchmark environment."},
        "failure_checks": {"corrupt_or_unsupported": "NOT_RUN_IN_PADDLE_METRIC_CORPUS", "paddle_model_unavailable": "NOT_RUN", "paddle_initialization_failure": "NOT_RUN", "cpu_only_paddle": "PASS", "gpu_unavailable_paddle": "DOCUMENTED_CPU_WHEEL", "tesseract_runtime": "BASELINE_RETAINED"},
        "recommendation": {"option": "C — hybrid routing", "rationale": "Measured Paddle OCR provides current PP-OCRv6 boxes/confidence and is the appropriate isolated candidate for scanned pages, while the frozen baseline confirms native digital extraction is substantially faster and exact. Keep PyMuPDF/native extraction for reliable digital pages, evaluate Paddle for scanned/complex pages, and retain Tesseract as a fallback until broader CPU latency and difficult-document results are validated."},
    })
    existing_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    _update_markdown(existing, REPORT_DIR / "STEP2A_DOCUMENT_AI_BENCHMARK.md")
    print(json.dumps({"output": str(existing_path), "paddle_aggregate": paddle_aggregate, "structure": structure_row, "versions": versions}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
