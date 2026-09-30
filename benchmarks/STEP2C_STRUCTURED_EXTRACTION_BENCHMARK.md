# Step 2C Structured Extraction Benchmark

Corpus: `2c-1`; scored cases: 3

This is a deterministic candidate-extraction benchmark. A fact is only counted as a full match when entity, metric, value, unit/period where labelled, evidence type, and page agree. Real Ministry PDFs are inventoried separately because they do not have field-level frozen ground truth in this repository.

## Aggregate results

- Expected labelled facts: **7**
- Extracted candidates: **14**
- Full fact exact rate: **0.7143**
- Evidence-link exact rate: **0.7143**
- Numeric exact rate: **1.0000**
- Entity macro P/R/F1: **0.6667 / 1.0000 / 0.6667**
- Metric macro P/R/F1: **0.4286 / 0.8889 / 0.4667**
- Value/unit/period exact rates: **0.8000 / 0.8000 / 1.0000**
- Structural candidates marked review: **6**

## Per-case matrix

| case | expected | candidates | full fact | provenance | numeric | warnings/review |
|---|---:|---:|---:|---:|---:|---:|
| native_period_table | 2 | 2 | 1.0 | 1.0 | 1.0 | 0 |
| controlled_ocr_numeric_and_geology | 5 | 10 | 0.6 | 0.6 | 1.0 | 5 |
| structural_labels_rejected | 0 | 2 | n/a | n/a | n/a | 1 |

## Real-document smoke checks

The runner can be invoked with `--include-real` to parse the first two locally available golden PDFs. These are integration smoke checks only, not accuracy claims, because no field-level labels are stored for them.
- Not run in the default deterministic mode.

## Limitations

- This layer is conservative rule/context extraction, not an LLM extractor. AI-assisted proposals are not enabled by default.
- Real Ministry documents listed in the corpus inventory require independently labelled fact/evidence annotations before their accuracy can be reported honestly.
- OCR text without reliable table/cell structure remains a review candidate; no cell geometry is fabricated.
- Legacy `extracted_metrics`, validation, conflict, and Step 2B consumers are intentionally unchanged.
