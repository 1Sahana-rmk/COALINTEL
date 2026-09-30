"""Step 2A benchmark harness.

This module intentionally lives outside the production ingestion path.  It
generates a deterministic OCR corpus, runs the existing Tesseract-backed
parser as the baseline, probes (but does not install) Paddle components, and
writes machine-readable results.  It must not be imported by the backend.
"""

from __future__ import annotations

import importlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
REPORT_DIR = ROOT / "implementation_reports"

CONTROL_LINES = [
    "COALINTEL OCR ACCEPTANCE TEST",
    "781.05 1,294.73 -14.82 97.45%",
    "BH-27 143.20 4.60 G8",
    "0.0047 12,345,678.90 -0.875 99.07%",
    "23.456789, 86.123456",
    "20-09-2026 CMPDI-BH-104A M.Cu.M",
    "142.75 m - 148.35 m",
]
CONTROL_TEXT = "\n".join(CONTROL_LINES)
CONTROL_TOKENS = re.findall(r"\S+", CONTROL_TEXT)

NUMERIC_TOKENS = ["781.05", "1,294.73", "-14.82", "0.0047", "12,345,678.90", "-0.875"]
DECIMAL_TOKENS = ["781.05", "1,294.73", "-14.82", "0.0047", "12,345,678.90", "-0.875", "99.07%", "143.20", "4.60", "23.456789", "86.123456", "142.75", "148.35"]
COMMA_TOKENS = ["1,294.73", "12,345,678.90"]
NEGATIVE_TOKENS = ["-14.82", "-0.875"]
PERCENT_TOKENS = ["97.45%", "99.07%"]
IDENTIFIER_TOKENS = ["BH-27", "G8", "CMPDI-BH-104A"]
UNIT_TOKENS = ["M.Cu.M", "m"]


def _levenshtein(left: list[str], right: list[str]) -> int:
    previous = list(range(len(right) + 1))
    for i, lvalue in enumerate(left, start=1):
        current = [i]
        for j, rvalue in enumerate(right, start=1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (lvalue != rvalue)))
        previous = current
    return previous[-1]


def _normalise_for_error_rate(value: str) -> str:
    # Whitespace is not an accuracy target here; punctuation is retained.
    return re.sub(r"\s+", " ", value or "").strip()


def _error_metrics(expected: str, actual: str) -> dict[str, Any]:
    expected_norm = _normalise_for_error_rate(expected)
    actual_norm = _normalise_for_error_rate(actual)
    expected_chars, actual_chars = list(expected_norm), list(actual_norm)
    expected_words, actual_words = expected_norm.split(), actual_norm.split()
    return {
        "cer": _levenshtein(expected_chars, actual_chars) / max(1, len(expected_chars)),
        "wer": _levenshtein(expected_words, actual_words) / max(1, len(expected_words)),
        "expected_characters": len(expected_chars),
        "actual_characters": len(actual_chars),
        "expected_words": len(expected_words),
        "actual_words": len(actual_words),
    }


def _token_metrics(actual: str, tokens: Iterable[str]) -> dict[str, Any]:
    actual = actual or ""

    def score(values: list[str]) -> dict[str, Any]:
        matches = [value for value in values if value in actual]
        return {"matched": len(matches), "total": len(values), "rate": len(matches) / max(1, len(values)), "missing": [value for value in values if value not in actual]}

    return {
        "all_control_tokens": score(list(tokens)),
        "numeric_exact": score(NUMERIC_TOKENS),
        "decimal_preservation": score(DECIMAL_TOKENS),
        "comma_separator_preservation": score(COMMA_TOKENS),
        "negative_sign_preservation": score(NEGATIVE_TOKENS),
        "percentage_preservation": score(PERCENT_TOKENS),
        "identifier_preservation": score(IDENTIFIER_TOKENS),
        "unit_preservation": score(UNIT_TOKENS),
    }


def _font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arial.ttf", Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _control_image(*, rotate: float = 0, noise: bool = False, low_resolution: bool = False) -> Image.Image:
    image = Image.new("RGB", (1800, 1050), "white")
    draw = ImageDraw.Draw(image)
    font = _font(42)
    for index, line in enumerate(CONTROL_LINES):
        draw.text((70, 80 + index * 125), line, fill="black", font=font)
    if noise:
        pixels = image.load()
        for x in range(0, image.width, 17):
            for y in range(0, image.height, 19):
                pixels[x, y] = (90, 90, 90)
        image = image.filter(ImageFilter.GaussianBlur(radius=0.7))
    if rotate:
        image = image.rotate(rotate, expand=True, fillcolor="white")
    if low_resolution:
        image = image.resize((450, 263), Image.Resampling.LANCZOS)
    return image


def _table_image() -> Image.Image:
    image = Image.new("RGB", (1600, 900), "white")
    draw = ImageDraw.Draw(image)
    font = _font(38)
    rows = [
        ["Subsidiary", "April", "May", "Total"],
        ["ECL", "781.05", "781.50", "1,562.55"],
        ["BCCL", "", "0.781", "-5.00"],
    ]
    x0, y0, col_w, row_h = 80, 80, 350, 180
    for row_index, row in enumerate(rows):
        for col_index, value in enumerate(row):
            x1, y1 = x0 + col_index * col_w, y0 + row_index * row_h
            draw.rectangle((x1, y1, x1 + col_w, y1 + row_h), outline="black", width=3)
            if value:
                draw.text((x1 + 18, y1 + 60), value, fill="black", font=font)
    return image


def _write_image(image: Image.Image, path: Path, fmt: str) -> None:
    image.save(path, format=fmt)


def _write_image_pdf(image: Image.Image, path: Path) -> None:
    import fitz

    stream = tempfile.SpooledTemporaryFile()
    image.save(stream, format="PNG")
    stream.seek(0)
    pdf = fitz.open()
    page = pdf.new_page(width=612, height=792)
    page.insert_image(page.rect, stream=stream.read())
    pdf.save(path)
    pdf.close()


def _write_native_pdf(path: Path) -> None:
    import fitz

    pdf = fitz.open()
    page = pdf.new_page(width=612, height=792)
    page.insert_text((50, 80), CONTROL_TEXT, fontsize=15)
    pdf.save(path)
    pdf.close()


def _write_mixed_pdf(path: Path, image: Image.Image) -> None:
    import fitz

    stream = tempfile.SpooledTemporaryFile()
    image.save(stream, format="PNG")
    stream.seek(0)
    pdf = fitz.open()
    page = pdf.new_page(width=612, height=792)
    page.insert_text((50, 60), "Native digital heading retained by PyMuPDF.", fontsize=15)
    page.insert_image(fitz.Rect(0, 100, 612, 750), stream=stream.read())
    pdf.save(path)
    pdf.close()


def _make_corpus(root: Path) -> list[dict[str, Any]]:
    corpus_dir = root / "generated_corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)
    clean = _control_image()
    entries: list[dict[str, Any]] = []

    def add(name: str, path: Path, expected: str = CONTROL_TEXT, *, table: bool = False, token_only: bool = False) -> None:
        entries.append({"id": name, "path": str(path), "expected_text": None if token_only else expected, "expected_tokens": CONTROL_TOKENS, "expected_table": table, "ground_truth_scope": "token_only" if token_only else "full_text"})

    _write_native_pdf(corpus_dir / "native_digital.pdf")
    add("PDF_NATIVE", corpus_dir / "native_digital.pdf")
    _write_image_pdf(clean, corpus_dir / "fully_scanned.pdf")
    add("PDF_SCANNED", corpus_dir / "fully_scanned.pdf")
    _write_mixed_pdf(corpus_dir / "mixed.pdf", clean)
    add("PDF_MIXED", corpus_dir / "mixed.pdf")
    for name, image in [("rotated", _control_image(rotate=7)), ("skewed", _control_image(rotate=-4)), ("noisy", _control_image(noise=True)), ("low_resolution", _control_image(low_resolution=True))]:
        _write_image_pdf(image, corpus_dir / f"{name}.pdf")
        add(f"PDF_{name.upper()}", corpus_dir / f"{name}.pdf")
    _write_image_pdf(Image.new("RGB", (1800, 1050), "white"), corpus_dir / "blank.pdf")
    add("PDF_BLANK", corpus_dir / "blank.pdf", expected="")
    _write_image_pdf(_table_image(), corpus_dir / "scanned_table.pdf")
    entries.append({"id": "PDF_SCANNED_TABLE", "path": str(corpus_dir / "scanned_table.pdf"), "expected_text": "Subsidiary April May Total ECL 781.05 781.50 1,562.55 BCCL 0.781 -5.00", "expected_tokens": re.findall(r"\S+", "Subsidiary April May Total ECL 781.05 781.50 1,562.55 BCCL 0.781 -5.00"), "expected_table": True, "ground_truth_scope": "full_text"})

    for fmt, extension in [("PNG", "png"), ("JPEG", "jpg"), ("JPEG", "jpeg"), ("TIFF", "tif"), ("TIFF", "tiff")]:
        path = corpus_dir / f"image_scan.{extension}"
        _write_image(_control_image(), path, fmt)
        add(f"IMG_{extension.upper()}", path)

    # Include locally available real Step-1 acceptance PDFs.  Their full text
    # is not asserted because no separate ground-truth transcript is stored.
    for pattern, name in [("*COALINTEL_Scanned_OCR_Acceptance_Test.pdf", "REAL_COALINTEL_SCAN"), ("*WhatsApp_Image_2026-09-20_at_1.49.46_PM.pdf", "REAL_SCREENSHOT_SCAN")]:
        matches = sorted((BACKEND / "storage" / "uploads").glob(pattern))
        if matches:
            add(name, matches[0], token_only=True)
    return entries


def _paddle_probe() -> dict[str, Any]:
    result: dict[str, Any] = {"paddle": None, "paddleocr": None, "paddlex": None, "status": "UNAVAILABLE"}
    for module in ("paddle", "paddleocr", "paddlex"):
        try:
            imported = importlib.import_module(module)
            result[module] = getattr(imported, "__version__", "installed_without_version")
        except Exception as exc:
            result[f"{module}_error"] = f"{type(exc).__name__}: {str(exc)[:240]}"
    if result["paddle"] and result["paddleocr"]:
        result["status"] = "INSTALLED_NOT_BENCHMARKED"
    return result


def _gpu_probe() -> dict[str, Any]:
    result: dict[str, Any] = {"available": False, "raw": ""}
    try:
        completed = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10, check=False)
        result["raw"] = completed.stdout.strip()
        result["returncode"] = completed.returncode
        result["available"] = completed.returncode == 0 and bool(completed.stdout.strip())
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {str(exc)[:240]}"
    return result


def _baseline_entry(entry: dict[str, Any]) -> dict[str, Any]:
    sys.path.insert(0, str(BACKEND))
    from app.services.parsing_service import parse_document_result

    path = Path(entry["path"])
    suffix = path.suffix.lower().lstrip(".")
    file_type = "IMAGE" if suffix in {"png", "jpg", "jpeg", "tif", "tiff"} else suffix.upper()
    start = time.perf_counter()
    error = None
    result = None
    try:
        result = parse_document_result(str(path), file_type, filename=path.name)
    except Exception as exc:
        error = f"{type(exc).__name__}: {str(exc)[:240]}"
    elapsed = time.perf_counter() - start
    pages = []
    text = ""
    tables = []
    if result is not None:
        text = "\n".join(page.text for page in result.pages)
        tables = result.tables
        for page in result.pages:
            pages.append({
                "page_number": page.page_number,
                "classification": page.classification,
                "method": page.extraction_method,
                "confidence": page.confidence,
                "text_characters": len(page.text),
                "blocks": len(page.blocks),
                "bbox_blocks": sum(1 for block in page.blocks if block.bbox and len(block.bbox) == 4),
                "metadata": page.metadata,
            })
    metrics = {"cer": None, "wer": None}
    if entry["expected_text"] is not None:
        metrics = _error_metrics(entry["expected_text"], text)
    metric_payload = {**metrics, **_token_metrics(text, entry["expected_tokens"])}
    bbox_available = sum(page["bbox_blocks"] for page in pages)
    confidence_available = sum(1 for page in pages if page["confidence"] is not None)
    table_payload = {
        "expected": entry["expected_table"],
        "detected_tables": len(tables),
        "table_detection": bool(tables) if entry["expected_table"] else None,
        "row_recovery": None,
        "column_recovery": None,
        "cell_value_accuracy": None,
        "header_preservation": None,
        "blank_cell_preservation": None,
        "numeric_cell_accuracy": None,
        "cell_bbox_availability": None,
    }
    if entry["expected_table"]:
        table_payload["cell_bbox_availability"] = sum(1 for table in tables for cell in table.cells if cell.get("bbox")) / max(1, sum(len(table.cells) for table in tables)) if tables else 0.0
    return {
        "id": entry["id"],
        "file": path.name,
        "engine": "Tesseract via existing production parser",
        "status": "ERROR" if error else "PASS",
        "error": error,
        "whole_document_latency_seconds": round(elapsed, 4),
        "page_count": len(pages),
        "pages": pages,
        "text_preview": text[:2000],
        "metrics": metric_payload,
        "bbox_availability": bbox_available > 0,
        "confidence_availability": confidence_available > 0,
        "table_metrics": table_payload,
        "warnings": result.warnings if result is not None else [],
    }


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [row for row in rows if row["status"] == "PASS"]

    def mean(path: tuple[str, ...]) -> float | None:
        values = []
        for row in successful:
            value: Any = row
            for key in path:
                value = value.get(key) if isinstance(value, dict) else None
            if isinstance(value, (int, float)):
                values.append(value)
        return sum(values) / len(values) if values else None

    return {
        "documents": len(rows),
        "successful": len(successful),
        "errors": len(rows) - len(successful),
        "mean_cer_full_text_documents": mean(("metrics", "cer")),
        "mean_wer_full_text_documents": mean(("metrics", "wer")),
        "mean_exact_numeric_rate": mean(("metrics", "numeric_exact", "rate")),
        "mean_decimal_rate": mean(("metrics", "decimal_preservation", "rate")),
        "mean_bbox_available": sum(1 for row in successful if row["bbox_availability"]) / max(1, len(successful)),
        "mean_confidence_available": sum(1 for row in successful if row["confidence_availability"]) / max(1, len(successful)),
        "table_documents": sum(1 for row in successful if row["table_metrics"]["expected"]),
        "table_detection_rate": sum(1 for row in successful if row["table_metrics"]["expected"] and row["table_metrics"]["table_detection"]) / max(1, sum(1 for row in successful if row["table_metrics"]["expected"])),
    }


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="coalintel_step2a_") as temp:
        entries = _make_corpus(Path(temp))
        rows = [_baseline_entry(entry) for entry in entries]
    payload = {
        "benchmark": "COALINTEL Step 2A Document AI benchmark",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "tesseract": "queried through existing pytesseract configuration",
            "gpu": _gpu_probe(),
        },
        "paddle_probe": _paddle_probe(),
        "paddle_execution": {"status": "NOT_RUN", "target_stack": {"paddlepaddle": "3.2.0", "paddleocr": "3.7.0 current PyPI metadata", "general_ocr": "PP-OCRv6", "document_ai": "PP-StructureV3"}, "reason": "Paddle/PaddleOCR/PaddleX are not installed; current environment is Python 3.14 while the PaddlePaddle Windows package documentation supports Python 3.8-3.12."},
        "models": {"tesseract": "system Tesseract configured by existing parser", "paddle_ocr_target": "PP-OCRv6", "pp_structure_target": "PP-StructureV3"},
        "corpus": rows,
        "aggregate": _aggregate(rows),
        "failure_checks": {
            "corrupt_or_unsupported": "not part of generated OCR metric corpus; existing Step-1 tests cover explicit parser errors",
            "paddle_model_unavailable": "BLOCKED_NOT_INSTALLED",
            "paddle_initialization_failure": "NOT_RUN",
            "cpu_only_paddle": "NOT_RUN",
            "gpu_unavailable_paddle": "NOT_RUN",
            "tesseract_runtime": "AVAILABLE if rows completed",
        },
    }
    output = REPORT_DIR / "STEP2A_DOCUMENT_AI_BENCHMARK.json"
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"output": str(output), "aggregate": payload["aggregate"], "paddle_probe": payload["paddle_probe"], "gpu": payload["environment"]["gpu"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
