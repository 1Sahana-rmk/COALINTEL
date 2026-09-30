# Step 2A Document AI Benchmark

This benchmark is isolated from the frozen Step-1 production pipeline. The Tesseract baseline is retained from the original Python 3.14 run; Paddle was executed in `.venv-paddle312` with Python 3.12.

## Environment and models

- Python: `3.12.10 (tags/v3.12.10:0cc8128, Apr  8 2025, 12:21:36) [MSC v.1943 64 bit (AMD64)]`
- Platform: `Windows-11-10.0.26200-SP0`
- GPU probe: `NVIDIA GeForce RTX 4050 Laptop GPU, 592.82, 6141, 0`
- Paddle versions: `{"compiled_with_cuda": false, "paddleocr": "3.7.0", "paddlepaddle": "3.2.0", "paddlex": "3.7.2"}`
- PP-OCR model: `PP-OCRv6_medium_det` + `PP-OCRv6_medium_rec`.
- Document AI model: current PaddleOCR 3.7.0 `PP-StructureV3` pipeline on CPU; observed models include `PP-DocLayout_plus-L`, `PP-OCRv5_server_det/rec`, `SLANeXt_wired`, `SLANet_plus`, and RT-DETR table-cell detectors (full list is in the JSON report).
- GPU inference: `NOT_RUN_INCOMPATIBLE_WINDOWS_CPU_WHEEL`; the installed Windows package reports `compiled_with_cuda=false`.

## Corpus and metric policy

- Documents: `16` Tesseract baseline rows and `16` Paddle rows, generated from the same corpus and ground truth.
- CER/WER retain punctuation; whitespace is normalized only for error-rate comparison.
- Flattened OCR text is not counted as table reconstruction.
- Native digital PDF extraction remains the preferred production path; this benchmark measures OCR separately.

## Direct comparison

| Metric | Tesseract baseline | PP-OCRv6 CPU |
|---|---:|---:|
| Mean CER | 0.09267260095527573 | 0.02469604863221885 |
| Mean WER | 0.1535964035964036 | 0.12912087912087913 |
| Mean exact numeric rate | 0.6979166666666666 | 0.8541666666666666 |
| Mean decimal preservation | 0.7115384615384616 | 0.8413461538461539 |
| Bounding boxes available | 0.9375 | 0.9375 |
| Confidence available | 1.0 | 0.9375 |

## Table benchmark

- Tesseract table detection: `0.0`; the production parser does not reconstruct the generated scanned table reliably.
- PP-StructureV3 result: `{"approx_peak_rss_mb": 2835.35, "engine": "PP-StructureV3 via PaddleOCR 3.7.0 CPU", "error": null, "file": "scanned_table.pdf", "id": "PDF_SCANNED_TABLE", "initialization_seconds": 16.0294, "metrics": {"blank_cell_preservation": 1.0, "cell_bbox_availability": 1.0, "cell_box_count": 12, "cell_value_accuracy": 1.0, "column_recovery": 1.0, "detected_tables": 1, "header_preservation": 1.0, "html_preview": ["<html><body><table><tr><td>Subsidiary</td><td>April</td><td>May</td><td>Total</td></tr><tr><td>ECL</td><td>781.05</td><td>781.50</td><td>1,562.55</td></tr><tr><td>BCCL</td><td></td><td>0.781</td><td>-5.00</td></tr></table></body></html>"], "numeric_cell_accuracy": 1.0, "recovered_columns": 4, "recovered_rows": 3, "row_recovery": 1.0, "table_detection": true, "warnings": ["Structural row/column scoring requires parsing the returned table HTML; raw table evidence was retained."]}, "page_count": 1, "status": "PASS", "whole_document_latency_seconds": 42.6618}`
- Cell/row/column metrics are reported as unknown when the pipeline output did not expose reliable structure; no structure is fabricated.

## Per-document Paddle metrics

| ID | Status | CER | WER | Exact numeric | Latency (s) | BBoxes | Mean OCR confidence |
|---|---|---:|---:|---:|---:|---:|---:|
| PDF_NATIVE | PASS | 0.005319148936170213 | 0.07692307692307693 | 1.0 | 17.4174 | True | 0.9948842184884208 |
| PDF_SCANNED | PASS | 0.010638297872340425 | 0.15384615384615385 | 1.0 | 20.3743 | True | 0.9937705908502851 |
| PDF_MIXED | PASS | 0.2393617021276596 | 0.3076923076923077 | 1.0 | 19.9992 | True | 0.9950496628880501 |
| PDF_ROTATED | PASS | 0.005319148936170213 | 0.07692307692307693 | 1.0 | 17.6796 | True | 0.9891638840947833 |
| PDF_SKEWED | PASS | 0.005319148936170213 | 0.07692307692307693 | 1.0 | 18.9929 | True | 0.9914550270353045 |
| PDF_NOISY | PASS | 0.026595744680851064 | 0.38461538461538464 | 1.0 | 20.7144 | True | 0.9866525190217155 |
| PDF_LOW_RESOLUTION | PASS | 0.015957446808510637 | 0.19230769230769232 | 1.0 | 18.7874 | True | 0.9911289640835353 |
| PDF_BLANK | PASS | 0.0 | 0.0 | 0.0 | 11.112 | False | None |
| PDF_SCANNED_TABLE | PASS | 0.0 | 0.0 | 0.16666666666666666 | 16.695 | True | 0.9999579949812456 |
| IMG_PNG | PASS | 0.005319148936170213 | 0.07692307692307693 | 1.0 | 19.5115 | True | 0.993618266923087 |
| IMG_JPG | PASS | 0.010638297872340425 | 0.15384615384615385 | 1.0 | 18.9797 | True | 0.9907625232424054 |
| IMG_JPEG | PASS | 0.010638297872340425 | 0.15384615384615385 | 1.0 | 18.9892 | True | 0.9907625232424054 |
| IMG_TIF | PASS | 0.005319148936170213 | 0.07692307692307693 | 1.0 | 19.3074 | True | 0.993618266923087 |
| IMG_TIFF | PASS | 0.005319148936170213 | 0.07692307692307693 | 1.0 | 18.7312 | True | 0.993618266923087 |
| REAL_COALINTEL_SCAN | PASS | None | None | 1.0 | 72.8578 | True | 0.9980243790149689 |
| REAL_SCREENSHOT_SCAN | PASS | None | None | 0.5 | 21.2149 | True | 0.9839915881554285 |

## Performance and failure checks

- Paddle OCR initialization: `2.1454` seconds.
- Paddle OCR aggregate peak RSS observation: `1554.12` MB.
- Paddle table pipeline: `{'status': 'PASS', 'id': 'PDF_SCANNED_TABLE', 'file': 'scanned_table.pdf', 'engine': 'PP-StructureV3 via PaddleOCR 3.7.0 CPU', 'error': None, 'initialization_seconds': 16.0294, 'whole_document_latency_seconds': 42.6618, 'approx_peak_rss_mb': 2835.35, 'page_count': 1, 'metrics': {'table_detection': True, 'detected_tables': 1, 'row_recovery': 1.0, 'column_recovery': 1.0, 'header_preservation': 1.0, 'cell_value_accuracy': 1.0, 'blank_cell_preservation': 1.0, 'numeric_cell_accuracy': 1.0, 'cell_bbox_availability': 1.0, 'cell_box_count': 12, 'recovered_rows': 3, 'recovered_columns': 4, 'html_preview': ['<html><body><table><tr><td>Subsidiary</td><td>April</td><td>May</td><td>Total</td></tr><tr><td>ECL</td><td>781.05</td><td>781.50</td><td>1,562.55</td></tr><tr><td>BCCL</td><td></td><td>0.781</td><td>-5.00</td></tr></table></body></html>'], 'warnings': ['Structural row/column scoring requires parsing the returned table HTML; raw table evidence was retained.']}}`.
- Failure checks: `{"corrupt_or_unsupported": "NOT_RUN_IN_PADDLE_METRIC_CORPUS", "cpu_only_paddle": "PASS", "gpu_unavailable_paddle": "DOCUMENTED_CPU_WHEEL", "paddle_initialization_failure": "NOT_RUN", "paddle_model_unavailable": "NOT_RUN", "tesseract_runtime": "BASELINE_RETAINED"}`

## Recommendation

**C — hybrid routing** — Measured Paddle OCR provides current PP-OCRv6 boxes/confidence and is the appropriate isolated candidate for scanned pages, while the frozen baseline confirms native digital extraction is substantially faster and exact. Keep PyMuPDF/native extraction for reliable digital pages, evaluate Paddle for scanned/complex pages, and retain Tesseract as a fallback until broader CPU latency and difficult-document results are validated.

## Limitations

- Windows GPU inference was not counted as successful because the installed official CPU wheel is not CUDA-enabled; `nvidia-smi` hardware visibility alone is not Paddle runtime compatibility.
- PP-StructureV3 structure metrics remain conservative when returned HTML/cell evidence cannot be mapped to the controlled ground-truth grid without assumptions.
- No production dependency, parser, processing state, database, sync connector, or Step-1 behavior was changed.

Official references: [PaddleOCR quick start](https://www.paddleocr.ai/latest/en/quick_start.html), [PaddlePaddle package metadata](https://pypi.org/pypi/paddlepaddle/json), [PaddleOCR high-performance deployment](https://paddlepaddle.github.io/PaddleOCR/main/en/version3.x/deployment/high_performance_inference.html).
