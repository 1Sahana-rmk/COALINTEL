# Step 1 Final Real-World Acceptance

Date: 2026-09-19  
Database: disposable PostgreSQL `coalintel_step1_acceptance` only. The normal development database was not modified.

## Result

**STEP 1 — COMPLETE**

Manual real-application acceptance and the final automated regression pass are
complete. Five legacy optional ONNX/model-artifact tests remain failed, but
they are isolated to the future knowledge-layer embedding implementation and
do not affect Step-1 ingestion, persistence, synchronization, provenance,
state, or audit behavior.

## Critical acceptance matrix

| Criterion | Result | Evidence / limitation |
|---|---|---|
| Live Ministry discovery and category traversal | PASS | Real site: 3 same-host pages checked, 20 bounded documents discovered initially; later default connector run discovered 100. |
| Same-host and redirect restrictions | PASS | Live resources remained on `coal.nic.in`; existing connector tests cover off-host rejection. No policy weakening was made. |
| First live sync acquisition | PASS | 100 current official registry records with SHA-256/version 1 and linked document IDs. The earlier `INGESTED` count was not a parsing result and is superseded. |
| Second unchanged sync | PASS | Bounded second run: 5 discovered, 5 unchanged, 0 duplicates, 0 failures; registry count stayed 20. |
| Official documents enter common processing pipeline | PASS after fix | Root cause was missing `execute_document_processing_pipeline()` after `process_file_ingestion()`. New and checksum-unchanged-but-unprocessed records now invoke and verify the common pipeline. |
| Real `srn-jan-2023.pdf` reprocessing | PASS | 128 real pages, 128 persisted `document_pages`, 192 persisted tables, native/OCR mixed text, `PARSED` + `REVIEW_RECOMMENDED`, no error. |
| Restart persistence after official reprocessing | PASS | After backend restart, the same record retained 128 pages, 192 tables, text, version 1 and source linkage. |
| Live individual failure isolation | PASS | Fault-injected one-resource check using 3 real discovered resources: 2 unchanged, 1 failed, source `PARTIAL`; subsequent real bounded sync restored `CONNECTED`. |
| Common backend ingestion path | PASS | Manual upload and corrected official sync both use `process_file_ingestion()` followed by the common processing pipeline. |
| PostgreSQL persistence and restart | PASS | New `TestClient` application startup against PostgreSQL retained documents, pages, tables, images, audit history, warnings and official registry records. |
| Corrupt/empty failure state | PASS | Corrupt PDF and empty PDF persisted as `FAILED` / `EXTRACTION_FAILED`; neither became `READY`; errors were returned by the warnings API. |
| Poor-quality scan warning | PASS | PNG/JPG/TIFF uploads persisted as `REVIEW_RECOMMENDED` with low-OCR-confidence warnings. |
| Real native PDF | PASS | Ministry `MoC_Production_Supplies_2023-24.pdf` uploaded through backend; 8 pages and 8 tables persisted. Representative native cell: document 37 → page 5 → table 1 → row 24 → column 2 → raw `s 781.056` → bbox `[221.3374, 377.9570, 269.3985, 391.1570]`. |
| Real scanned/mixed/image/DOCX/XLSX/CSV coverage | PASS | Manual localhost acceptance verified scanned/image-only PDF, DOCX, XLSX and CSV backend ingestion and persistence. Deterministic fixtures provide repeatable regression coverage. |
| XLSX provenance | PASS | Backend upload preserved workbook → sheet → coordinate → raw value/formula/displayed-value fields and merged range. Example document 43, `Production!B2=781.05`, `Production!C2` formula `=B2*2`, merged `D1:E1`; cached displayed values were `None` because the fixture had no cached calculation result. |
| Frontend authentication and repository | PASS | Production frontend authenticated with seeded Admin session; repository displayed PostgreSQL-backed documents, failed rows and Ministry `CONNECTED` status. |
| Frontend tables/warnings/history surfaces | PASS | Minimal wiring added to the existing document detail page; authenticated UI displayed 8 extracted tables, 0 warnings and 1 persisted history event for document 37. |
| Frontend Sync Now | PASS | Manual authenticated acceptance verified asynchronous start, polling, completion, duplicate-run protection and explicit failure/partial presentation. |
| Production frontend build | PASS | Next production build compiled, linted/typechecked and generated 17/17 static pages after the integration changes. |
| Python compilation | PASS | `python -m compileall -q app tests`. |
| Focused Step-1 regression suite | PASS | PostgreSQL run: `59 passed, 3 warnings`. |
| Full backend suite | PASS with out-of-scope failures | Final clean run: `359 passed, 5 failed, 2 skipped, 17 subtests passed`. All five failures are isolated `tests/test_low_memory_embedding.py` failures caused by missing offline `sentence-transformers/all-MiniLM-L6-v2` artifacts; no Step-1 tests failed. |

## Files changed in the blocker-fix pass

- `backend/app/services/official_sync_service.py` — official acquisition now invokes and verifies the common processing pipeline; unchanged records with unvalidated linked documents are retried; processing failure is distinct from download success.
- `backend/tests/test_step1_document_ingestion.py` — regression tests proving official sync cannot report a download-only `PENDING` document as `INGESTED`, and that pipeline failures remain linked and explicit.

## Files changed in the earlier final acceptance pass

- `backend/app/api/documents.py` — fixed the existing history endpoint to use the model’s real `AuditLog.timestamp` field instead of nonexistent `created_at`.
- `frontend/lib/api/sourceApi.ts` — added a bounded 120-second timeout for the real, potentially long-running Ministry sync.
- `frontend/lib/api/documentApi.ts` — exposed the existing tables, warnings and history endpoints to the frontend.
- `frontend/types/document.ts` — added response types for those existing Step-1 APIs.
- `frontend/app/(dashboard)/documents/[id]/page.tsx` — displayed existing table-count/provenance, warning/error and persisted-history summaries without redesigning the workspace.
- `implementation_reports/STEP1_FINAL_ACCEPTANCE.md` — this evidence report.

No new dependency was added. The disposable PostgreSQL database was used for bounded reprocessing only; no normal development database was changed.

## Remaining limitations and blockers

1. The live Ministry source currently exposed PDF resources; non-PDF official-resource behavior remains covered by bounded connector fixtures rather than live evidence.
2. A naturally changed live resource at the same URL was not observed during the acceptance window; deterministic same-URL/new-checksum tests cover version creation without overwriting history.
3. Five full-suite ONNX failures remain because the offline `sentence-transformers/all-MiniLM-L6-v2` model artifacts are unavailable. This is future knowledge-layer technical debt and was not bypassed or redesigned.
4. Difficult numerical/table OCR remains imperfect with the current Tesseract stack. Low-confidence/fallback extraction is explicitly marked `REVIEW_RECOMMENDED`; OCR model/document-AI improvements are deferred to Step 2.
5. Scanned-table row/column reconstruction remains conservative when OCR/layout evidence is insufficient; raw OCR evidence and warnings are retained rather than inventing structure. Coal-domain interpretation is deferred.

## Official-document recovery correction

The 96 current Ministry documents left `DOWNLOADED` by the previously broken
official-sync path were recovered in bounded batches using the existing common
processing helper and original document IDs. No replacement versions were
created and no auditable records were deleted.

| Recovery measure | Result |
|---|---|
| Candidates | 96 |
| Successfully processed | 96 |
| Current official documents `READY` / `PARSED` | 10 |
| Current official documents `REVIEW_RECOMMENDED` | 90 |
| Current official documents `PROCESSING_FAILED` | 0 |
| Still `DOWNLOADED` / `PENDING` | 0 |
| Duplicate versions created during recovery | 0 |

All 100 current official documents now have persisted validated processing
states. One historical non-current `FAILED` registry row is retained for audit.
Representative recovered files include `srn-jan-2023.pdf` (128 pages, 192
tables), `msg-june25.pdf` (30 pages, 22 tables), `14-06-2022a-wn.pdf` (76
pages, 83 tables), `srn-jan-2025.pdf` (129 pages, 178 tables), and
`srn-Aug-2021.pdf` (122 pages, 182 tables). Text, page rows, tables and review
warnings are persisted in PostgreSQL.

Recovery found two genuine defects in the common pipeline: stale processing
states could produce invalid retry transitions, and long extracted metric
fields could violate existing column lengths. Both were fixed and covered by
focused regression tests. Optional vector indexing was bypassed only during
the final bounded retry because it is outside Step 1 and known to depend on
the unavailable ONNX model artifact.

## Blocker-fix test results

- Official-source and processing reliability tests: `21 passed, 4 warnings`.
- Python compilation: passed.
- Live target discovery: 5 same-host pages checked, target found, 8,750,240 bytes downloaded.
- Live target sync pass 1: `discovered=1, unchanged=1, failed=0`, version unchanged.
- Live target sync pass 2: `discovered=1, unchanged=1, failed=0`, no duplicate version.

## Recovery correction files and verification

- `backend/app/services/processing_pipeline.py` — fixed in-place retry reset
  and legacy metric-column length handling.
- `backend/tests/test_processing_reliability.py` — added two focused
  regressions; both passed (`2 passed, 8 deselected, 3 warnings`).
- `implementation_reports/TASK5_POSTGRESQL_ACCEPTANCE.md` — recorded bounded
  recovery counts and representative artifacts.
- `implementation_reports/STEP1_FINAL_ACCEPTANCE.md` — recorded the corrected
  final acceptance state.

Python compilation passed. That earlier partial-run note is superseded by the
final clean reconciliation below: `359 passed, 5 failed, 2 skipped, 17
subtests passed`, with the five known optional ONNX/model-artifact failures.

## Official sync request-lifecycle correction

The localhost UI alert was not a Ministry or ingestion failure. The browser
called `POST /api/v1/sources/ministry-of-coal/sync` through the Next.js rewrite;
the FastAPI handler synchronously performed discovery, downloads, checksums and
processing before responding. The 15-second Axios default (previously raised
only for this call) and proxy/request lifetime could therefore report an HTTP
failure while the backend operation continued and eventually committed
`CONNECTED`. The endpoint also had no atomic in-progress claim, so repeated
clicks could start duplicate work.

The endpoint now atomically claims the persisted `OfficialSource`, returns
`202 Accepted` with a job identifier immediately, and runs the existing sync
function in a worker-owned database session. A second request receives `409`
with `SYNCING`; it cannot start another sync. The existing `/sources/sync-status`
and `/sources` data are polled by the frontend every three seconds. Completion
shows `CONNECTED`; `PARTIAL` and `ERROR` remain explicit and display the
persisted error. Worker exceptions clear `SYNCING` to `ERROR`, while the normal
sync function clears it to `CONNECTED` or `PARTIAL` on every handled path.
On backend startup, orphaned `SYNCING` claims are reconciled to explicit
`ERROR` because their worker no longer exists.

Focused lifecycle regression tests: **7 passed, 1 warning**. Frontend
production build: **PASS**, 17/17 static pages generated with no lint or type
errors. No timeout increase was used as the fix, and SHA-256/version and common
document processing behavior were unchanged.

Files changed for this lifecycle correction:

- `backend/app/api/sources.py` — prompt `202` manual-sync response, worker
  execution, duplicate-run rejection, and worker failure reconciliation.
- `backend/app/services/official_sync_service.py` — atomic source claim and
  startup recovery of orphaned claims; existing sync/version logic preserved.
- `backend/main.py` — startup invocation of orphaned-sync reconciliation.
- `backend/tests/test_official_sync_lifecycle.py` — lifecycle, duplicate,
  completion, failure, and restart regression coverage.
- `frontend/lib/api/sourceApi.ts` — accepted-job response typing and removal of
  the long-running request timeout override.
- `frontend/app/(dashboard)/documents/page.tsx` — persisted-status polling and
  accurate syncing/partial/error UI states.
- `implementation_reports/STEP1_FINAL_ACCEPTANCE.md` and
  `implementation_reports/TASK5_POSTGRESQL_ACCEPTANCE.md` — lifecycle issue,
  resolution, and test evidence.
## Image-only PDF OCR blocker correction (2026-09-20)

The real file `WhatsApp Image 2026-09-20 at 1.49.46 PM.pdf` was reproduced
from the disposable PostgreSQL acceptance database. Its page was correctly
classified as `SCANNED` (zero meaningful native characters, zero native text
blocks, one image covering approximately 79.6% of the page). Tesseract was
invoked. The original 300-DPI preprocessed image path returned no text, while
the page's embedded 900x1600 raster produced fallback OCR text and evidence
blocks. The prior implementation did not mark that fallback as degraded, and
the confidence threshold of 0.60 allowed the imperfect result to become
`READY`.

The parser now retains the generic embedded-raster fallback, records its
coordinate space and source, emits an explicit fallback/review warning, and
uses a 0.70 OCR review threshold. The existing document was repaired in
place; no replacement version was created.

| Evidence | Result |
|---|---|
| Classification / OCR | `SCANNED`; Tesseract invoked |
| OCR source | `embedded_raster` fallback |
| Persisted page | 1 page, 245 characters, 51 evidence blocks |
| Confidence | `0.632745...` |
| Coordinates | `embedded_image_pixels` |
| Warnings | fallback used/review recommended; low confidence `0.63`/review recommended |
| Final state | `PARSED` + canonical `REVIEW_RECOMMENDED` |
| Tables | 0; no fabricated table structure |

The actual OCR preserved `BH-27` and `143.20` exactly. It did not preserve
the exact requested forms of `781.05`, `1,294.73`, `-14.82`, `97.45`, `4.60`
and `G8` in this low-quality screenshot-like raster; examples include
`781. 05`, `1,298.73`, `-14. a2` and `97. A5%`. These remain OCR limitations
and are not normalized or fabricated. Zero-text OCR still produces explicit
warnings and cannot be treated as clean extraction.

Focused verification:

- Actual OCR image-only/classification/empty-OCR tests: `3 passed, 27 deselected`.
- Processing retry/review/metric-bound regressions: `3 passed, 8 deselected`.
- Python compilation: passed.
- Direct live-document PostgreSQL reprocessing: page text, evidence,
  confidence, source metadata and `REVIEW_RECOMMENDED` persisted as above.

Files changed for this blocker:

- `backend/app/services/parsing_service.py` — explicit degraded fallback
  provenance/warning and conservative OCR review threshold.
- `backend/app/services/processing_pipeline.py` — in-place retry reset retained
  from the related recovery fix.
- `backend/tests/test_task2_ocr_acceptance.py` — actual readable image-only
  PDF regression and fallback-warning assertion.
- `backend/tests/test_processing_reliability.py` — review-state retry
  regression retained from the related recovery fix.
- `implementation_reports/STEP1_FINAL_ACCEPTANCE.md` — this blocker result.

Task 2 OCR integration blocker: **RESOLVED**. OCR quality remains explicitly
reviewable rather than falsely successful. Step 1 final status: **COMPLETE**,
with the out-of-scope ONNX failures and documented OCR limitations above.

## Final regression and freeze reconciliation (2026-09-20)

The final runs used the existing backend virtual environment, a writable
repository-local pytest base directory, and an isolated Chroma test directory
to avoid a Windows lock in the default optional vector-store directory. No
production ingestion code or assertions were changed for this environment
workaround.

Exact commands and results:

```text
.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-basetemp-final tests/test_step1_document_ingestion.py
13 passed, 2 warnings

.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-basetemp-final tests/test_standalone_ingestion.py
3 passed, 1 warning

.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-basetemp-final tests/test_task2_ocr_acceptance.py tests/test_processing_reliability.py tests/test_official_sync_lifecycle.py tests/test_table_extraction.py tests/test_task3_table_acceptance.py tests/test_database_configuration.py tests/test_day7_integration.py tests/test_pipeline_e2e.py
77 passed, 2 skipped, 4 warnings

.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-basetemp-final
359 passed, 5 failed, 2 skipped, 17 subtests passed, 17 warnings

.venv\Scripts\python.exe -m compileall -q app tests
PASS

node node_modules/next/dist/bin/next build
PASS; Next.js 14.2.35; 17/17 static pages; typecheck/lint passed
```

The five full-suite failures are exactly:

- `test_low_memory_embedding.py::test_01_onnx_backend_singleton`
- `test_low_memory_embedding.py::test_04_zero_torch_in_embedding_path`
- `test_low_memory_embedding.py::test_05_tokenizer_encoding_contract`
- `test_low_memory_embedding.py::test_06_strict_offline_operation`
- `test_low_memory_embedding.py::test_13_onnx_arena_and_mem_pattern_disabled`

Each fails because the local offline cache does not contain
`sentence-transformers/all-MiniLM-L6-v2` ONNX/tokenizer artifacts. They are
unrelated to Step-1 ingestion and remain deferred technical debt.

XLSX provenance audit: `parse_xlsx_result()` loads both formula and
`data_only` workbook views. Each cell retains coordinate, row, column, raw
value, formula/data type, displayed/cached value where available, blank-cell
status, and merged ranges at workbook → worksheet → cell provenance. Formula
floating-point artifacts such as `4.600000000000023` remain raw values; the
displayed-value field is used when a cached value exists, without overwriting
raw/formula evidence. This is sufficient for Step 1 and does not justify a
representation redesign.

Read-only PostgreSQL validation against `coalintel_step1_acceptance` passed:

```text
documents 129
document_pages 7249
document_tables 10157
document_images 3
official_sources 1
official_documents 101
audit_logs 169
document 152: PARSED / REVIEW_RECOMMENDED / 1 page
document 152 persisted page rows/text: 1 / 245 characters
```

No Step-2 work was started. The Step-1 common ingestion pipeline,
official-source synchronization, version registry, PostgreSQL persistence,
provenance, processing states, review semantics and audit history are frozen
for the next reviewed stage.
