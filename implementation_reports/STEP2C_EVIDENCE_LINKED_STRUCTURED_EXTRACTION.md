# Step 2C — Evidence-Linked AI Structured Extraction

## Status

**STEP 2C — READY FOR FINAL ACCEPTANCE**

Step 2C remains an additive, conservative structured-fact layer. Manual acceptance of real Ministry document 126 (`srn-nov_1st.pdf`) found false-positive classes; bounded automated validation and corrected reprocessing now pass. Final human acceptance is still required before this task can be marked complete. The existing Step 2B manual-acceptance defects remain documented and open.

No Step 3/pgvector work was started. Existing ingestion, OCR/Document AI routing, conflict identity/calculation, RBAC, and frontend behavior were not redesigned.

## Architecture assessment

The existing authoritative ingestion path is:

```text
parse_document_result()
  -> DocumentResult / PageResult / TableResult
  -> processing_pipeline._persist_common_artifacts()
  -> document_pages / document_tables / document_images
  -> legacy domain extraction
  -> extracted_metrics / validation / conflicts / optional vectors
```

The legacy `extracted_metrics` table remains the compatibility surface for current dashboards, validation, conflicts, reports, and existing Step 2B consumers. It has document/page and raw/normalized value fields, but it cannot reliably represent table-cell coordinates, hierarchical header context, raw period semantics, resolution methods, duplicate identity, or a page/table foreign-key chain.

Step 2C therefore adds one derived `structured_facts` view from the already persisted common `DocumentResult`. It does not create a competing parser or replace `extracted_metrics`.

## Canonical structured fact

The new record carries:

```text
document_id
document_page_id / page_number
document_table_id where applicable
source_metric_id nullable for legacy linkage
entity type/id/raw/canonical/resolution method/confidence
metric type/raw/canonical/resolution method/confidence
raw value text/numeric
normalized value/unit and raw unit
raw/normalized period and period type
qualifiers
extraction method/confidence
evidence type/locator
validation status/warnings
fact status
fact_key / duplicate_group_key
```

The evidence hierarchy is table cell, text block, then page text. Missing geometry remains null; coordinates are never fabricated.

## Implementation

`structured_extraction_service.py` provides generic context-aware candidate extraction:

- table title, headers, row context, explicit periods, units, and cell metadata are retained;
- `Apr 2023` and full month names normalize to the same explicit monthly period form;
- raw numeric tokens preserve commas, signs, and source spelling while normalized numeric values use safe numeric conversion;
- physical geological units such as `m` and `M.Cu.M` are not converted to coal mass;
- structural labels (`Sl No`, serial numbers, header labels) are represented only as review candidates and never become canonical mine entities;
- aggregate labels such as `Grand Total` remain aggregate context, not a mine;
- no period is inferred when the source does not supply one;
- a transparent weighted confidence score uses method, table structure, entity resolution, metric resolution, numeric parsing, and period evidence;
- warning-bearing or page-only candidates remain `REVIEW_REQUIRED`, not authoritative;
- structurally detected contents/index/navigation tables are excluded from domain-fact generation when an explicit page-reference column and repeated page-reference pattern establish that the table is navigational;
- borehole identifiers require a numeric `BH` identifier pattern (`BH-27`, `BH 27`, etc.) plus nearby borehole/ID context; ordinary address text such as `Lok Nayak Bhavan` is not a borehole fact;
- explicit serial-number columns, fiscal-period label cells, and numbered section-label cells are retained in the source table but are not emitted as numeric domain facts;
- explicit table headers take precedence over broad row context for metric classification, and unit inference does not borrow a unit from neighboring cells;
- exact evidence identity and semantic duplicate-group identity are separate;
- persistence is idempotent for a document/fact key and reprocessing replaces only the derived Step 2C view for that document, not source versions.

`validate_ai_fact_proposal()` is an AI safety boundary, not an AI model. A future model adapter can submit a proposal, but it is rejected unless the claimed page/table/cell or text value and supplied context can be located in the provided persisted evidence. AI output is never treated as evidence by itself.

## Schema and migration

Added additive migration:

`backend/migrations/004_step2c_structured_facts.sql`

The migration creates `structured_facts`, its foreign keys and indexes. It is rerunnable with `IF NOT EXISTS` guards, including the page-provenance column guard needed to recover from a partial first application. No existing table is dropped or rewritten.

PostgreSQL validation against the disposable `coalintel_step1_acceptance` database:

- migration applied successfully;
- rerun was idempotent after the guarded page-column correction;
- `structured_facts` exists with `document_page_id` and the expected fact/provenance columns;
- existing row count before manual real-document reprocessing: 0.

## API

Added authenticated read endpoint:

`GET /api/v1/documents/{id}/structured-facts`

It returns the additive facts with document/page/table IDs, canonical/raw fields, confidence, warnings, and evidence locators. The existing `/lineage` response remains unchanged.

## Frozen benchmark

Corpus:

`benchmarks/step2c_structured_extraction_corpus.json`

Runner:

`benchmarks/step2c_structured_extraction_benchmark.py`

The labelled corpus contains a native two-period table, the controlled OCR numeric/geology page, and a structural-label rejection table. Local golden Ministry PDFs are inventoried and two are run as unlabelled parser smoke checks; no accuracy percentage is claimed for them because the repository does not contain independent field-level ground truth.

Machine output:

`benchmarks/STEP2C_STRUCTURED_EXTRACTION_BENCHMARK.json`

Human matrix:

`benchmarks/STEP2C_STRUCTURED_EXTRACTION_BENCHMARK.md`

Latest deterministic result:

| Measure | Result |
|---|---:|
| Labelled cases | 3 |
| Expected labelled facts | 7 |
| Candidate facts | 14 |
| Full fact exact rate | 0.7143 |
| Evidence-link exact rate | 0.7143 |
| Numeric exact rate | 1.0000 |
| Entity macro precision / recall / F1 | 0.6667 / 1.0000 / 0.6667 |
| Metric macro precision / recall / F1 | 0.4286 / 0.8889 / 0.4667 |
| Value / unit / period exact rates | 0.8000 / 0.8000 / 1.0000 |
| Structural candidates marked review | 6 |

The native period-table case achieved 2/2 full fact and 2/2 evidence-link matches. The OCR/geology case intentionally leaves ambiguous page-level/structural candidates in review; it does not turn uncertain OCR or unsupported semantics into accepted facts.

Unlabelled real-document smoke checks from the latest run:

- `MoC_Production_Supplies_2023-24.pdf`: 8 pages, 8 tables, 70 candidate facts.
- `MoC_Annual_Report_2023-24_Chap2_Production.pdf`: 12 pages, 16 tables, 493 candidate facts; existing Paddle service timeouts/Tesseract fallback and low-resolution review warnings were preserved in parser warnings.

## Manual acceptance regression: `srn-nov_1st.pdf` / document 126

The failed acceptance run was reproduced against the disposable PostgreSQL database before reprocessing:

| Check | Before correction | After corrected common-pipeline reprocessing |
|---|---:|---:|
| Structured facts for document 126 | 10,473 | 10,046 |
| Facts on page 7 / contents table | 34 | 0 |
| Facts claiming `document_table` 1 on page 7 | 34 | 0 |
| `BOREHOLE_ID` facts | 16 | 0 |
| Duplicate `fact_key` rows | 0 | 0 |
| Document processing state | `PARSED` / `REVIEW_RECOMMENDED` | `PARSED` / `REVIEW_RECOMMENDED` |

The bounded final audit additionally found and corrected these reproducible
patterns: explicit serial-number columns (`Sl No`, `Serial No`), cells
containing fiscal labels such as `FY 21`, numbered section labels such as
`DRILLING 1. DRILLING BY CMPDI`, and unit contamination from neighboring row
cells. After final reprocessing, page-7 facts, borehole false positives,
fiscal-label measurements, numbered-label measurements, duplicate keys, and
missing evidence links were all zero. Growth facts no longer received `m`
from `M-O-M` text or neighboring cells.

Representative final persisted evidence checks included:

- page 11, `ECL`, `COAL_PRODUCTION`, raw `4.34`, cell `4.34`, header `Production During Nov 2020`;
- page 12, `ECL`, `COAL_DISPATCH`, raw `26.26`, cell `26.26`, header `Progressive Despatch`;
- page 38, `ECL`, `OVERBURDEN_REMOVAL`, raw `8.380`, cell `8.380`, header `OBR During Nov 2020`;
- page 56, `EXPLORATION_DRILLING`, raw `488000`, cell `488000`, header `MOU TARGET 2020-21 (Proposed)`.

Each retained sample had a valid document-page/table-cell locator. Eleven
page-56 exploration cells explicitly contain `%` but have blank extracted
column headers; they remain review candidates rather than being relabelled as
achievement or growth facts without reliable header evidence.

The original page-7 table was persisted as a native table with headers `Chapter Name`, `Table`, and `Page`; its rows contained navigation labels and page references such as `State-wise Coal Production → 3`, `Exploration → 42`, and `OBR Status → 48`. The previous extractor treated the page-reference column as a measurement column. The general fix rejects a table only when its explicit page-reference column is predominantly page references and the table has contents/index/navigation signals; ordinary sparse measurement tables remain eligible.

The two pre-fix borehole rows were page-level text candidates with raw value `Bhavan` and snippets `Floor, Lok Nayak Bhavan,` / `Floor, Lok Nayak Bhavan`. The prior pattern matched the `Bh` prefix without requiring a numeric identifier. The corrected pattern requires a numeric `BH` identifier and nearby borehole/ID context, preserving valid cases such as `Borehole ID: BH-27`.

The corrected run replaced only the derived `structured_facts` for document 126 through the normal processing pipeline, with optional vector operations isolated for this bounded validation. No replacement document/version was created, source bytes were not changed, and the document remained `PARSED` with its existing `REVIEW_RECOMMENDED` state.

## Tests and verification

Passed:

- `.venv\Scripts\python.exe -m pytest tests\test_step2c_structured_extraction.py -q` — **11 passed** (one existing pytest cache warning due a Windows temp/cache permission issue).
- `.venv\Scripts\python.exe ..\benchmarks\step2c_structured_extraction_benchmark.py` — **completed**: 7 expected facts, 14 candidates, 0.7143 full-fact exact rate, 1.0000 numeric exact rate.
- `.venv\Scripts\python.exe -m py_compile app\services\structured_extraction_service.py app\services\processing_pipeline.py app\api\documents.py app\models\structured_fact.py ..\benchmarks\step2c_structured_extraction_benchmark.py` — **passed**.
- `.venv\Scripts\python.exe -m pytest tests\test_step1_document_ingestion.py -q --basetemp <workspace temp> -k "page_classifier or csv_preserves or xlsx_preserves or docx_preserves or mixed_pdf_ocr_only_runs or official_connector or state_machine"` — **9 passed, 4 deselected**.
- `.venv\Scripts\python.exe -m pytest tests\test_step2b_document_ai_integration.py -q --basetemp <workspace temp>` — **10 passed**.
- Python compilation for the new model/service/pipeline/API/benchmark modules — **passed**.
- `import main` from the backend virtual environment — **passed**.
- PostgreSQL migration apply/rerun and schema inspection — **passed** against the disposable acceptance database.

Not completed / environment-limited:

- The unfiltered full `test_step1_document_ingestion.py` run was not reported as passing. The first attempt hit `PermissionError: [WinError 5]` while pytest scanned the user temp directory; the workspace-basetemp attempt progressed through seven tests and then stopped without completing the remaining official-sync cases, so it was interrupted rather than misreported.
- A targeted pre-existing processing-reliability pipeline test was also interrupted after prolonged optional embedding/vector work. The new Step 2C pipeline smoke test passes with optional vector operations isolated, and the existing Step 2B suite passes; this does not establish a full-suite pass.
- Full backend suite was not claimed as passing for this task.
- Frontend was not changed, so no frontend build was rerun for this backend extraction task.

## Known limitations and manual acceptance

1. No external LLM is invoked by this change. The production layer is an evidence-linked candidate/validation foundation; AI proposals must pass the supplied-evidence gate before a future adapter can persist them.
2. Real-document accuracy requires a labelled evidence corpus. The smoke run measures parser/candidate behavior only.
3. OCR-only facts without reliable blocks/cells remain page-level review candidates. Exact cell geometry is retained only when Step 1 supplied it.
4. `source_metric_id` remains nullable because the legacy metric rows are produced by a separate compatibility pass and cannot be safely matched by position or value alone. The document/page/table/cell locator is authoritative for the new layer.
5. Repeated semantic facts across different source documents are grouped by `duplicate_group_key`; cross-document conflict behavior remains a later consumer concern and was not rewritten.
6. Period and metric resolution is intentionally conservative. It does not infer monthly/annual meaning from filename, page position, or a numeric column alone.
7. The final bounded audit confirms the reported TOC, false-borehole, serial-column, fiscal-label, numbered-section-label, and cross-cell-unit-contamination patterns are suppressed. Eleven exploration percentage cells have explicit percent tokens but incomplete header metadata; they remain review candidates. The remaining 10,046 candidates still require final human review for domain suitability; this task did not expand into a general document-quality cleanup or Step 2C semantic redesign.

Manual acceptance should reprocess document 126 and representative real native, OCR, mixed, XLSX, CSV, and DOCX documents through the normal upload/common pipeline, then inspect `/api/v1/documents/{id}/structured-facts` and PostgreSQL to confirm document → page → table/cell locators, review warnings, raw/normalized values, explicit periods, no contents/index facts, no false `Bhavan` borehole, and no canonical serial-number entities. Existing Step 2B defects must be tested and documented independently; they are not hidden by this work.
