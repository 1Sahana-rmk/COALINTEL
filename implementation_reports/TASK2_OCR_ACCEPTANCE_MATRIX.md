# Task 2 OCR and Document Ingestion Acceptance Matrix

Actual OCR was run with Tesseract `5.5.3.20260724` using the installed executable at `C:\Program Files\Tesseract-OCR\tesseract.exe`. The real-OCR rows below call the parser without replacing `_ocr_image`.

| ID | Real fixture | Observed result | OCR confidence | Classification / method | Result |
|---|---|---|---:|---|---|
| PDF-NATIVE | Native text PDF | Native text preserved; no OCR call | N/A | `DIGITAL` / `NATIVE` | PASS |
| PDF-SCANNED | Full-page raster PDF | `COAL 781.05 MT` | 0.9533 | `SCANNED` / `OCR` | PASS |
| PDF-MIXED | Native text plus raster | Native context plus `COAL 781.05 MT` | 0.9533 | `MIXED` / `NATIVE+OCR` | PASS |
| PDF-LOWRES | Low-resolution raster PDF | Text recovered; source-resolution warning emitted | 0.8225 image run | `SCANNED` / `OCR` | PASS with review warning |
| PDF-ROTATED | 7-degree rotated scan | `COAL 781.05 MT` | 0.9400 | `SCANNED` / `OCR` | PASS |
| PDF-SKEWED | -4-degree skewed scan | `COAL 781.05 MT` | 0.9533 | `SCANNED` / `OCR` | PASS |
| PDF-NOISY | Noisy and blurred scan | `COAL 781.05 MT` | 0.9567 | `SCANNED` / `OCR` | PASS |
| PDF-TABLE | Scanned table text | `Subsidiary April Total ECL 7.07 8.10` | 0.9600 | `SCANNED` / `OCR` | PASS; no invented table rows |
| PDF-BLANK | Blank page | Empty text; `no readable text extracted` warning | 0.2000 | `DIGITAL` / `NATIVE` | PASS |
| PDF-IMAGE | Image-only PDF page | OCR text and word evidence preserved | 0.9533 | `SCANNED` / `OCR` | PASS |
| IMG-PNG | PNG scan | `COAL 781.05 MT` | 0.9533 | `SCANNED` / `OCR` | PASS |
| IMG-JPG | JPG scan | `COAL 781.05 MT` | 0.9567 | `SCANNED` / `OCR` | PASS |
| IMG-JPEG | JPEG scan | `COAL 781.05 MT` | 0.9567 | `SCANNED` / `OCR` | PASS |
| IMG-TIF | TIFF scan | `COAL 781.05 MT` | 0.9533 | `SCANNED` / `OCR` | PASS |
| IMG-TIFF | TIFF scan | `COAL 781.05 MT` | 0.9533 | `SCANNED` / `OCR` | PASS |
| DOCX-ORDER | Heading, paragraph, table, paragraph | Original order preserved | 0.9800 native | `NATIVE` | PASS |
| XLSX-PROVENANCE | Two sheets, formula, merge, blank cell | Workbook → sheet → coordinate preserved | 0.9900 native | `NATIVE` | PASS |
| CSV-TABLE | CSV rows and cells | Structured rows and coordinates | 0.9900 native | `NATIVE` | PASS |
| FAIL-CORRUPT | Invalid PDF bytes | Explicit parser exception | N/A | Error, not READY | PASS |
| FAIL-UNSUPPORTED | Unsupported BIN | Explicit `ValueError` | N/A | Error, not READY | PASS |
| FAIL-EMPTY | Empty PDF bytes | Explicit parser exception | N/A | Error, not READY | PASS |
| DUPLICATE | Repeated content | Stable SHA-256 identity | N/A | Duplicate/version path | PASS |

## Actual OCR quality notes

- Clean, rotated, skewed, noisy, full-page scanned, mixed-page, scanned-table, and all five image formats executed against real Tesseract.
- Word bounding boxes were preserved for actual OCR words and validated as four-coordinate boxes.
- The low-resolution image produced `COAL 781 05 MT` rather than preserving the decimal point. Its confidence was `0.8225`, so the implementation now emits a generic low-source-resolution review warning instead of silently treating it as high-quality extraction.
- Blank pages remain non-OCR digital pages with an explicit no-readable-text warning.
- Scanned-table row/column reconstruction is intentionally not attempted. OCR text and evidence are retained; no table rows are fabricated.

## Acceptance run

```text
Tesseract: 5.5.3.20260724
python -m pytest -q tests/test_task2_ocr_acceptance.py
30 passed, 1 warning in 13.87s
```

The real OCR acceptance suite is no longer blocked by the environment.
