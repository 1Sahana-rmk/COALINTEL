"""Run a bounded real-document check through the Python 3.14 parser path."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.parsing_service import parse_document_result


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "benchmarks" / ".step2a_frozen_corpus" / "generated_corpus"
UPLOADS = ROOT / "backend" / "storage" / "uploads"


def main() -> int:
    paths = {
        "native_digital": CORPUS / "native_digital.pdf",
        "fully_scanned": CORPUS / "fully_scanned.pdf",
        "mixed": CORPUS / "mixed.pdf",
        "blank": CORPUS / "blank.pdf",
        "scanned_table": CORPUS / "scanned_table.pdf",
    }
    real = sorted(UPLOADS.glob("*COALINTEL_Scanned_OCR_Acceptance_Test.pdf"))
    screenshot = sorted(UPLOADS.glob("*WhatsApp_Image_2026-09-20_at_1.49.46_PM.pdf"))
    if real:
        paths["real_controlled_scan"] = real[0]
    if screenshot:
        paths["real_screenshot_scan"] = screenshot[0]
    if len(sys.argv) > 1:
        paths = {name: path for name, path in paths.items() if name in set(sys.argv[1:])}
    output = []
    for name, path in paths.items():
        result = parse_document_result(str(path), "PDF", filename=path.name)
        output.append({
            "case": name,
            "file": path.name,
            "pages": [{"page": page.page_number, "classification": page.classification, "method": page.extraction_method, "engine": page.metadata.get("ocr_engine"), "confidence": page.confidence, "text_characters": len(page.text), "blocks": len(page.blocks), "fallback_from": page.metadata.get("ocr_fallback_from")} for page in result.pages],
            "tables": [{"page": table.page_number, "method": table.extraction_method, "headers": table.headers, "rows": table.rows, "cells": len(table.cells), "bbox": table.bounding_box, "confidence": table.extraction_confidence} for table in result.tables],
            "warnings": result.warnings,
            "text_preview": "\n".join(page.text for page in result.pages)[:1200],
        })
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
