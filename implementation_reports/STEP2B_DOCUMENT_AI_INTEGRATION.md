# Step 2B Document AI Integration Acceptance

## Status

**STEP 2B — READY FOR MANUAL RE-ACCEPTANCE**

The routing, normalized service contract, fallback behavior, provenance, and bounded real Paddle integration are implemented. The demonstrated NUL persistence crash and stale document-workspace state have been fixed. Step 2B remains incomplete pending authenticated manual re-acceptance with PostgreSQL and the Document AI service.

## Architecture

The Python 3.14 FastAPI application does not import Paddle packages. It calls a narrow HTTP boundary:

```text
Python 3.14 backend
  └─ document_ai_client.py
       ├─ GET /health
       ├─ POST /v1/ocr
       └─ POST /v1/structure
              │
              ▼
      document_ai_service/server.py
      Python 3.12 + PaddleOCR 3.7.0
```

The service accepts base64 PNG raster bytes and page/source-raster metadata, never backend filesystem paths. This keeps the boundary portable to Docker, WSL2, or Linux deployment.

Models are initialized once per service process. PP-StructureV3 is lazy-loaded only when table hints justify a structure request.

## Routing

- `DIGITAL`: existing PyMuPDF native text/blocks/tables only; no Document AI request.
- `SCANNED`: Paddle PP-OCRv6 primary OCR.
- `MIXED`: native text is preserved; Paddle/Tesseract runs on embedded raster regions rather than OCRing the whole page and duplicating native text.
- Table/layout-heavy scanned pages: PP-StructureV3 only when repeated multi-column OCR rows are detected or structure mode is explicitly `always`.
- Paddle unavailable, timeout, unhealthy, initialization failure, or inference failure: existing Tesseract path is attempted.
- Embedded-raster Tesseract recovery remains available for screenshot-like scans where preprocessing destroys useful glyphs.

The structure heuristic avoids routing numeric-heavy prose pages to PP-StructureV3 unless repeated multi-column rows are present. No table is fabricated when structure output is absent or cell geometry cannot be aligned.

## Models and runtime

- PaddlePaddle: `3.2.0`
- PaddleOCR: `3.7.0`
- PaddleX: `3.7.2`
- OCR: `PP-OCRv6_medium_det` + `PP-OCRv6_medium_rec`
- Structure: current PaddleOCR 3.x `PP-StructureV3` pipeline, with observed layout/OCR/table models recorded in the Step 2A benchmark report.
- Development runtime: isolated Python 3.12 `.venv-paddle312`.
- Existing backend Python 3.14 environment: unchanged.
- GPU: not enabled; Windows Paddle runtime is CPU-only and `paddle.is_compiled_with_cuda()` is false.

## Normalized provenance

Paddle OCR blocks preserve:

- text;
- raster/page coordinates;
- confidence;
- `method=\"paddle_ppocrv6\"`;
- engine, model, version;
- source raster relationship.

Fallback blocks use `method=\"tesseract\"` and page metadata explicitly records `ocr_fallback_from=\"paddle_ppocrv6\"`. Native blocks remain `method=\"NATIVE\"`.

PP-StructureV3 tables preserve generic headers, rows, cells, cell coordinates when aligned, extraction method, confidence, model/version, and source raster metadata. The backend persists these through the existing `DocumentResult`/`DocumentTable` path.

Blank/empty responses are represented as `EMPTY`; they are not converted into engine failures. A non-blank raster with empty Paddle output triggers Tesseract recovery. Low confidence and recovery warnings continue through existing `REVIEW_RECOMMENDED` semantics.

## Configuration

Configured through environment variables in `.env` or deployment configuration:

```text
DOCUMENT_AI_ENABLED=true
DOCUMENT_AI_URL=http://127.0.0.1:8765
DOCUMENT_AI_CONNECT_TIMEOUT_SECONDS=0.5
DOCUMENT_AI_OCR_TIMEOUT_SECONDS=120.0
DOCUMENT_AI_STRUCTURE_TIMEOUT_SECONDS=180.0
DOCUMENT_AI_ENABLE_STRUCTURE=true
DOCUMENT_AI_STRUCTURE_MODE=table_hint
DOCUMENT_AI_FALLBACK_TO_TESSERACT=true
DOCUMENT_AI_DEVICE=cpu
```

The isolated service uses `DOCUMENT_AI_HOST`, `DOCUMENT_AI_PORT`, `DOCUMENT_AI_DEVICE`, and `PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK` as process environment settings.

## Automated tests

Executed with `DOCUMENT_AI_ENABLED=false` for deterministic legacy regression tests:

```text
backend\.venv\Scripts\python.exe -m pytest \
  backend\tests\test_step2b_document_ai_integration.py \
  backend\tests\test_step1_document_ingestion.py \
  backend\tests\test_task2_ocr_acceptance.py \
  backend\tests\test_task3_table_acceptance.py -q --basetemp .pytest-tmp-step2b
```

Result: **61 passed, 1 warning**.

The dedicated Step 2B routing suite contains 9 tests covering native routing, Paddle routing, mixed-page merge, timeout/inference fallback, blank raster, low confidence, table routing/provenance, and no-table behavior. It passed independently: **9 passed**.

The warning is the existing Chroma telemetry deprecation warning; it is unrelated to Document AI.

## Real production-path results

Executed through `backend/app/services/parsing_service.py`, not parser seams:

| Case | Result |
|---|---|
| Native digital PDF | `DIGITAL → NATIVE`, no Document AI request |
| Controlled scanned PDF | `SCANNED → paddle_ppocrv6`, confidence `0.9955`, exact control text preserved |
| Mixed PDF | `MIXED → NATIVE+OCR`, native text retained once, raster text added selectively |
| Blank image-only page | Empty text remains distinguishable from successful OCR failure; no fabricated text |
| Scanned table | `paddle_ppocrv6` plus `paddle_ppstructurev3`; 3 rows, 4 columns, 12 cells |
| Real controlled OCR PDF | Two scanned pages successfully routed through Paddle in the healthy-service run; one page received a structure result and a later structure request failure was surfaced as a warning without fabricating a table |
| Difficult screenshot scan | Paddle timeout triggered embedded-raster Tesseract recovery; confidence `0.632745`, review warnings retained |

The difficult screenshot reproduced the known Tesseract errors (`781.05 → 781. 05`, `1,294.73 → 1,298.73`, `-14.82 → -14.a2`, `97.45% → 97.A5%`) and was not falsely marked as high-quality.

## Performance observations

The Step 2A measurements remain authoritative: native extraction is preferred, Paddle CPU OCR is materially slower/heavier, and PP-StructureV3 is expensive. In the real service run, a controlled scanned page completed with the same high-confidence OCR behavior as the benchmark; the scanned-table request required PP-StructureV3 model reuse and completed with the benchmarked 3×4/12-cell result.

The long multi-document CPU run caused the service process to exit after extended activity. Backend requests remained recoverable through Tesseract fallback, but service supervision/resource limits must be addressed before production completion.

## Limitations and manual acceptance remaining

1. Run the service under a supervised process manager or container with explicit memory/restart limits.
2. Repeat authenticated frontend upload acceptance with `DOCUMENT_AI_ENABLED=true` and the service endpoint configured.
3. Verify PostgreSQL persistence of Paddle page metadata, block provenance, fallback warnings, and PP-Structure tables through the existing APIs.
4. Decide deployment target for CPU service versus WSL2/Linux GPU service; the current Windows environment did not provide a verified CUDA-enabled Paddle runtime.
5. Run a longer representative corpus after service supervision is established.

No Paddle packages were added to backend Python 3.14 requirements. No PostgreSQL schema, Ministry sync, processing-state model, Step 2C, Step 3, or Step 4 work was started.

## Stability investigation and final acceptance addendum

### Root cause of the previous exit

The controlled foreground reproduction did not end in a Python exception,
client termination, HTTP timeout, or deliberate restart. The service exited
with Windows code `-1073741819` (`0xC0000005`, native access violation). The
log immediately before exit contained Paddle/PaddleX OCR predictor tracebacks
(`paddlex ... paddle_static ... runner.py:265`) with `RuntimeError: Unknown
exception`, followed by the native process exit. The service was already
serialized, but the default Windows CPU/oneDNN runtime accumulated large
virtual-memory reservations (observed up to approximately 46 GiB) and RSS
peaks around 3.9 GiB while available memory fell to approximately 1.5–3.1 GiB.
This is a native Paddle/PaddleX/oneDNN access violation under cumulative CPU
resource pressure, not an application-level Python crash. No automatic restart
was used.

### Stability changes

- OCR and Structure inference now share one exclusive lock; health exposes
  queue/busy state, request IDs, RSS/VMS/available-memory telemetry, failures,
  model-init counts, and request-level tracebacks.
- PP-StructureV3 remains lazy and initializes at most once per service process.
- Safe, overridable service defaults are applied before Paddle import:
  `DOCUMENT_AI_CPU_THREADS=2`, `OMP_NUM_THREADS=2`,
  `MKL_NUM_THREADS=2`, `FLAGS_paddle_num_threads=2`, and
  `DOCUMENT_AI_DISABLE_MKLDNN=true` (`FLAGS_use_mkldnn=0`).
- Client disconnects are logged as request-level events instead of causing a
  second response exception; startup exits visibly nonzero when OCR cannot be
  initialized.
- The foreground launcher and non-restarting soak harness were added; request
  correlation IDs were added to the service client.

### Startup/readiness

Run from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_document_ai_service.ps1 `
  -LogPath .\implementation_reports\STEP2B_document_ai_service.log
```

This binds to `127.0.0.1:8765` in the isolated `.venv-paddle312` environment,
uses CPU-safe defaults, and stays visible in the foreground. `/health` reports
`process_alive`, `ocr_ready`, lazy `structure_ready`, `busy`, resources, stats,
and degraded/error state. A service is not `ready` when OCR initialization
failed. Docker/WSL/Linux can use the same module and HTTP contract later.

### Stop/fallback/restart/Paddle recovery

Through the real Python 3.14 production parser route:

| Service state | Observed result |
|---|---|
| Running | `SCANNED → paddle_ppocrv6`, confidence `0.995534` on the controlled scan |
| Stopped | backend remained alive; `SCANNED → tesseract`, `fallback_from=paddle_ppocrv6`, explicit ConnectTimeout warning |
| Restarted | subsequent request returned to Paddle without restarting FastAPI |

### Stabilized targeted results

Final health after the targeted run was `ready`, idle, with
`requests_total=12`, `requests_completed=12`, `request_failures=0`, one OCR
model initialization and one Structure initialization.

| Case | Result |
|---|---|
| Native digital PDF | `DIGITAL → NATIVE`; no Document AI request |
| Mixed PDF | `MIXED → NATIVE+OCR`; native text retained once and raster text recovered with Paddle |
| Scanned table | PP-OCRv6 + PP-StructureV3; 3 rows × 4 columns × 12 cells, confidence `0.996767`, no warnings |
| Blank page | empty Paddle OCR remained distinguishable; confidence `0.0`, explicit no-text warnings |
| Difficult screenshot scan | Paddle client timeout; service stayed alive; embedded-raster Tesseract fallback, confidence `0.632745`, review warnings retained |

The difficult scan preserved the known Tesseract errors (`781.05 → 781. 05`,
`1,294.73 → 1,298.73`, `-14.82 → -14.a2`, `97.45% → 97.A5%`) and was not
reported as high-quality Paddle output.

### Soak/memory result

The first default-runtime no-restart run reproduced the native exit above. The
corrected harness used the actual production parser route, but the full
three-pass/16-document CPU workload was stopped as impractical after 7
serialized OCR service requests; multi-page real documents were taking
minute-scale per page. The service remained alive through those requests and
was not auto-restarted. The stabilized targeted run then completed 12/12
service requests, including Structure, with zero service request failures.

Conservative-runtime observations were approximately: OCR-ready startup RSS
`518 MiB`; active RSS generally `1.1–3.4 GiB`; Structure peak `3.7 GiB`; final
targeted RSS `2.46 GiB`; final VMS `5.77 GiB`. Models initialized once each and
were reused. The full three-pass soak is not claimed as passed.

### Final automated validation

With `DOCUMENT_AI_ENABLED=false` for deterministic legacy tests:

```text
python -m pytest backend/tests/test_step2b_document_ai_integration.py \
  backend/tests/test_step1_document_ingestion.py \
  backend/tests/test_task2_ocr_acceptance.py \
  backend/tests/test_task3_table_acceptance.py \
  backend/tests/test_processing_reliability.py -q --basetemp .pytest-tmp-step2b-stability
```

Result: **72 passed, 3 warnings**.

Full backend suite:

```text
python -m pytest backend/tests -q --basetemp .pytest-tmp-step2b-full
```

Result: **367 passed, 5 failed, 2 skipped, 17 subtests passed, 15 warnings**.
All five failures are the pre-existing offline ONNX embedding/model-artifact
tests for `sentence-transformers/all-MiniLM-L6-v2`, outside Step 2B and Step 1.

`python -m compileall -q backend/app document_ai_service benchmarks/step2b_service_soak.py`
passed with exit code 0. The existing frontend production build passed using
the bundled Node runtime and the installed Next.js `14.2.35` tree; `npm` was
not exposed on PATH, so direct Next invocation was used without changing
dependencies or the lockfile.

### Remaining limitations/manual acceptance

1. Repeat authenticated frontend upload/status/warning/provenance acceptance
   with `DOCUMENT_AI_ENABLED=true` against PostgreSQL.
2. Run a longer supervised soak on the intended deployment host; the full
   three-pass corpus was not completed here because CPU latency was impractical.
3. Windows Paddle is CPU-only here (`cuda_compiled=false`); WSL2/Linux/GPU
   deployment needs separate validation.
4. A fresh service process is still required after an actual native
   `0xC0000005` exit, although Python-level Paddle failures remain recoverable
   through explicit Tesseract fallback.
5. Paddle confidence is not correctness proof; difficult numeric/table scans
   continue to use Step-1 review semantics.

**STEP 2B — READY FOR MANUAL RE-ACCEPTANCE**. No Step 2C, Step 3, or Step 4 work was started,
and Step-1 production code/environment, PostgreSQL schema/data, and Ministry
synchronization were not modified.

## Digital PDF processing regression acceptance

### Root cause

The real `DCM -  UNIT 2 CGM.pdf` is not uniformly digital at page level. It
contains 60 pages with a reliable native text layer and five genuinely
image-only pages (1, 2, 17, 24, and 43). Before this fix, the classifier
treated a reliable native text layer plus a full-page embedded background image
as `MIXED`. That made 57 native-text pages `MIXED` and requested OCR for 62 of
65 pages. The native text extraction and native table detector were not the
long-running stage: the pre-fix instrumented run took 55.182 seconds, with
approximately 0.298 seconds of native text work and 3.918 seconds of native
table work; the excessive OCR routing was the demonstrated regression.

The classifier now treats a page as `DIGITAL` when it has at least 40
meaningful native characters, at least one native text block, and an embedded
image coverage of at least 95%. This handles decorative/full-page raster
backgrounds without discarding native text. Pages with partial raster content
remain `MIXED`, and genuinely image-only pages remain `SCANNED`.

### Before/after results

The same local PDF was parsed through the production parser with Paddle
disabled so that the timing comparison isolates routing and native behavior:

| Measurement | Before fix | After fix |
|---|---:|---:|
| Total pages | 65 | 65 |
| `DIGITAL` | 3 | 60 |
| `MIXED` | 57 | 0 |
| `SCANNED` | 5 | 5 |
| OCR-requested pages | 62 | 5 |
| Native tables | 49 | 49 |
| Warnings | 90 | 4 |
| Parse duration | 55.182 s | 8.760 s |
| Native text timing | 0.298 s | 0.274 s |
| Native table timing | 3.918 s | 3.816 s |
| OCR timing | included for 62 pages | 4.482 s for 5 pages |

After the fix, only pages 1, 2, 17, 24, and 43 request OCR. The five pages
are real image-only pages, so a service-enabled run is expected to make five
OCR calls; a reliable native page makes no Document AI call. No page requested
PP-StructureV3 in this PDF. The native table detector, not Paddle, remains the
path for its native tables.

An actual service-boundary run was started against the corrected parser. The
service health telemetry showed `structure_requests=0` and OCR requests only
for the five scanned pages; the CPU Paddle request latency exceeded the current
120-second per-request client budget on the first heavy pages, so the bounded
run was stopped rather than allowing another multi-minute manual reproduction.
The service logged the client disconnect as a request-level event and was
stopped cleanly. This confirms the regression fix does not route the 60
reliable native pages to Paddle; the remaining cost is limited to the five
genuine scanned pages and is covered by the existing fallback behavior.

### Timing and regression coverage

`parse_pdf_result()` now records page-load, native-text, raster-inspection,
classification, OCR, native-table, normalization, and total page timings in
page/document metadata and emits per-page timing logs. The processing pipeline
also logs parse, artifact persistence, downstream normalization, validation,
and total processing durations.

The regression fixture creates a 65-page PDF with full-page raster backgrounds
and native text. It asserts that every page is `DIGITAL`, every page uses
`NATIVE`, no `/v1/ocr` or `/v1/structure` call is made, and timing metadata
records `ocr_requested=false` for every page. Existing scanned and mixed
routing tests remain green.

Focused result after the fix: **73 passed, 3 warnings**. Python compilation
also passed. The warning set is the existing FastAPI/httpx and Chroma
deprecation warnings; no new routing failure was introduced.

## Manual acceptance bug fixes

### NUL crash diagnosis and fix

The local uploaded `DCM_2.pdf` binary is SHA-256
`035f0802d160a3eb8cc606a75484b64e0290fdfbbd1ecc8708fb91b6cfbb2ca2` and
contains 66 pages. Its NUL characters originate in native PyMuPDF extraction,
not Paddle or Tesseract: page 9 contains five NUL characters in native page
text and the corresponding native table row/cell evidence. The first unsafe
database write was common artifact persistence: pending `document_pages.text`
and `document_tables.rows_json/cells_json` values were flushed during the
pipeline's first downstream database operation. PostgreSQL rejected the NUL
before chunking/indexing could complete. The vector path was not the cause.

The new common `DocumentResult` boundary removes NUL and other unsafe control
characters while preserving Unicode, tabs, spaces, newlines, numeric values,
and PDF/OCR geometry. It records the warning code
`TEXT_SANITIZED_INVALID_CONTROL_CHARACTER`, removed codepoints, and original
field offsets in document/page provenance. The DCM_2 real-file pipeline test
persisted 66 pages, 46 tables, and 66 chunks, removed 25 `U+0000` characters,
and finished `PARSED` with `REVIEW_RECOMMENDED`; no NUL remained in persisted
page text, table data, or chunks. With Paddle unavailable, OCR pages explicitly
recorded `tesseract` with `fallback_from=paddle_ppocrv6`.

The pipeline now logs the sanitization count/field count and includes the
current stage in processing failures without logging document text.

### Document workspace refresh diagnosis and fix

The detail page polled only the document metadata under a narrow
`PENDING`/`PROCESSING` check. Tables and history were fetched once, and pages
and lineage were disabled as soon as the document became `FAILED`. The global
React Query cache also used a 60-second stale window for this live workspace,
and there was no status-transition invalidation to force a final dependent-data
refresh. This allowed a terminal backend failure to remain visually stale until
navigation or reload.

The workspace now:

- polls all live document panels every three seconds while status is
  non-terminal;
- treats `READY`, `REVIEW_RECOMMENDED`, validation failures, and `FAILED` as
  terminal processing outcomes;
- keeps pages, lineage, tables, warnings, and history enabled for the final
  terminal refresh;
- invalidates all dependent queries when status or canonical processing state
  changes;
- uses `staleTime: 0`, background polling, and `Cache-Control: no-cache` for
  live document reads;
- relies on React Query request deduplication, so identical interval/refetch
  requests do not overlap for a query; and
- stops polling automatically after a terminal state and on component unmount.

At the time of the initial polling diagnosis, the frontend production build
could not be rerun because `frontend/node_modules` was unavailable in the
shell. After the isolated frontend dependencies became available, the build
was rerun successfully; authenticated browser acceptance remains required.

### Final live-polling state ownership fix

The later localhost acceptance run showed that the browser was issuing the
expected `/documents/{id}` and artifact requests, but the rendered detail
page could remain on the upload-time object (`PROCESSING`, `1 Pages`). The
detail header/page count was still indirectly dependent on the React Query
document cache, so network activity did not provide a strong guarantee that
the object used by the rendered tree had been replaced. The list also had no
continuous refresh while rows were processing.

The detail page now uses `useLiveDocument()` as the direct owner of the
authoritative document state. It performs non-overlapping, cache-busted
requests every three seconds, retains the last successful record across a
transient read error, and stops only after a real terminal state. The page
renders status and page count from that state; the backend's authoritative
page count therefore replaces the temporary upload count without navigation.
Pages, lineage, tables, warnings, and history continue to refresh while the
document is active and are invalidated on status/processing-state changes.
The Documents list now uses the same cache-busted reads and polls while any
visible row is non-terminal. No backend ingestion, parsing, or Document AI
routing code was changed for this fix.

The frontend TypeScript check and production build pass. The focused
`documentPolling` acceptance test covers `PROCESSING -> PARSED`, terminal
poll-stop behavior, temporary-to-authoritative page-count replacement, and
live cache-busting. Authenticated browser acceptance should still be rerun
with the local services running; the browser was not available in the shell
validation environment.

### Cross-document comparison matrix disappearance investigation

The comparison page had two independent failure paths. On the initial render,
`selectedDocIds` was empty while options were still loading, so the matrix
effect issued a request without `document_ids`. The backend contract interprets
omitted `document_ids` as an unrestricted/all-document query. Once options
arrived, another request used the selected catalog IDs. The page also allowed
every completed response to call `setData`, without associating the response
with the filter/selection snapshot that created it. Consequently, an older
empty or mixed-selection response could replace a newer valid matrix. The
frontend logs showed this exact family of requests: omitted IDs, mixed numeric
database IDs plus catalog IDs, and the final catalog-ID selection.

The options endpoint also returned authoritative `DataSource.source_id` values
and numeric ingested `Document.id` values in one untyped `documents` array.
Both identifier types are intentionally supported by the backend matrix route:
catalog IDs filter official `MineYearlyMetric.source_id` records, while
numeric IDs/filenames filter extracted metrics joined to `Document`. They must
not be silently merged by the authoritative catalog selector.

The endpoint now labels the two identifier domains. The comparison page selects
only `document_kind=catalog`, waits for options before its first matrix request,
sorts/deduplicates IDs for deterministic request identity, aborts superseded
requests, and applies a response only when both its request key and request ID
still match the current filters and selection. Empty transient selection never
becomes an omitted-ID all-document query. Catalog refreshes no longer replace
the matrix catalog from an arbitrary matrix response.

Focused comparison acceptance tests cover stable catalog selection, identifier
separation, omitted-ID suppression, deterministic request keys, empty-state
protection, and delayed stale-response rejection. The frontend TypeScript
check and production build pass; backend comparison tests pass. Manual browser
acceptance remains required and the Step 2B status is unchanged.

### Conflict-resolution reopen-loop fix

The conflict lifecycle audit found a backend and frontend loop. For extracted
document conflicts, the comparison endpoint looked up an existing canonical
`DataConflict` using `status="OPEN"` only. After resolution, the original row
was `RESOLVED`, so the next matrix refresh failed to find it and created a new
OPEN row for the same document pair/entity/metric/fiscal-year identity. The
same unresolved conflict therefore returned. The frontend also retained the
`/conflicts?id=...` URL; invalidating the conflict list returned the resolved
record and the URL-driven effect selected it again, reopening the modal.

The comparison lookup now includes resolved records and uses the stable
document-pair/entity/metric/fiscal-year identity. Resolved rows are returned
with `is_resolved=true` rather than recreated as active conflicts. Government
conflict records remain auditable but are excluded from the active conflict
collection after resolution. Resolution writes set `resolved_at`, preserve the
resolution and audit transaction, and repeated resolution requests return the
existing resolved record without another audit entry.

The conflict API no longer substitutes database ID `0` for government source
records. Database-backed conflicts expose nullable document IDs; government
records expose their source identifiers. The modal renders `Source <id>` or
`Identifier unavailable` instead of `ID #0`. Successful resolution clears the
selected conflict and removes the URL target before invalidating/refetching;
failed resolution leaves the modal open with the actual error and preserves the
form state. Resolved conflicts display resolution details and cannot be
submitted again.

Focused frontend and backend conflict-resolution tests pass. Read-only
PostgreSQL verification was attempted against the disposable acceptance
database, but the current shell did not expose a usable pgpass entry for the
requested host and no password was requested or logged; SQLite-backed
transaction/idempotency tests and Python compilation passed. Manual PostgreSQL
and authenticated browser acceptance remain required.
### Official Sources sync-state lifecycle fix

The Official Sources page previously used a local `syncing` flag as the main
polling lifecycle. The source query itself was not continuously polling when a
backend job was already active, and the local flag could remain inconsistent
with the persisted source row. The corrected UI treats
`official_sources.status` as authoritative: `SYNCING` enables a three-second
source poll, a page reload resumes polling from persisted `SYNCING`, and a
terminal `CONNECTED`, `PARTIAL`, or `ERROR` status clears the indicator and
refreshes the document list. Source reads carry explicit no-cache headers and a
cache-busting query value. HTTP 202 is treated as accepted/background work, not
completion.

The source worker already performs an atomic `SYNCING` claim and rejects a
second concurrent manual request. Its final status and error are persisted by
the worker-owned database session. Timestamp semantics are now explicit:
`last_sync_at` is the attempt/claim time; `last_success_at` is written only at
terminal `CONNECTED` completion. Failed or partial runs do not falsely advance
the successful timestamp. A successful empty discovery still records a
completion timestamp.

Focused lifecycle tests pass: 6 backend tests and the frontend source-sync
state acceptance test. Backend compilation, frontend TypeScript checking, and
the Next.js production build pass. Authenticated browser acceptance with the
local PostgreSQL-backed services remains required.
### Conflict Resolver repeated-detail-fetch fix

The conflict page’s URL-target effect ran while the list query was still
loading. Its `data: conflicts = []` fallback allocated a new array on every
render. Because that array was an effect dependency, each render started
another `GET /conflicts/{id}`; each response updated `activeConflict`, causing
another render. The list loading state remained independent, but the page could
remain on skeletons while the list query was unsettled and the detail requests
continued.

The effect now waits for the conflict list to settle, uses a stable empty-list
value, and records one in-flight/completed direct lookup per explicit URL
target. List rows are the only source of the table skeleton state. A normal
page load makes no detail request; an explicit target makes at most one direct
lookup unless the target changes. Stable IDs, resolved-state retention,
resolution invalidation, and idempotent audit behavior are unchanged.

The focused fetch-state acceptance test and existing conflict-resolution
regression tests pass. TypeScript and Python compilation pass. The first
production-build attempt encountered a Windows `.next/trace` EPERM lock; a
retry did not complete and was stopped, so a new production-build pass is not
claimed from this run.
### Conflict list routing and pending-request fix

The frontend routing was not conflict-specific. `validationApi.ts` uses the
shared Axios client with the same `/api/v1` base path as documents, dashboard,
and validation-feed calls. Next’s single `/api/v1/:path*` rewrite therefore
already routes `/conflicts` to FastAPI. The missing access-log line during the
manual timeout was not evidence of a different origin: the FastAPI handler
performed synchronous conflict detection before returning, and the access log
was emitted only after the request completed.

The detector performed a database lookup for every candidate metric pair. On a
large real corpus this produced an N+1 query storm and could exceed the
frontend’s 15-second Axios timeout. Existing conflict identities are now loaded
once into an in-memory set for the scan, preserving the same document-pair,
entity, metric, and fiscal-year identity without per-pair queries.

The conflict list query now receives React Query’s abort signal, disables
automatic retries and window/reconnect refetches for this explicit list read,
and disables the manual refresh button while a request is active. Failed list
retrieval renders an error row and an unavailable badge rather than a false
successful empty state. The earlier bounded URL-target detail lookup remains in
place.

Focused backend conflict/detector/API tests pass: 17 tests plus the HTTP API
route test. Frontend conflict-fetch state tests and TypeScript pass. A new
production build was not claimed because the existing Windows `.next/trace`
file lock prevented a clean build during this run.
### Conflict endpoint timing diagnostics

The conflict list path now emits bounded diagnostic stages without document or
metric payloads: request entry, authentication/session readiness, metrics and
identity timings, detection completion, serialization, SQL count/slowest
statement classes, and response readiness. Detector statistics include metrics
loaded, candidate pairs, existing conflicts, discrepancies, new conflicts, and
elapsed timings.

The detector’s remaining list-read N+1 patterns were removed: existing conflict
identities are loaded once, and response serialization preloads referenced
documents and mine records instead of querying per row. The route now uses
bounded preloads for both document conflicts and official conflict records.

At this validation run the local FastAPI service was not listening on
`127.0.0.1:8000`, so authenticated direct-versus-proxied latency and live
acceptance-database query counts could not be measured. Those are intentionally
not reported as passed. The diagnostics are ready for the next manual run;
client aborts will be visible by the absence of `CONFLICT_RESPONSE_READY` and
the last completed diagnostic stage.

### Conflict Resolver bounded retrieval and semantic audit

The acceptance measurements showed that the backend detector itself completed in
about 3.3–3.6 seconds, but the old list endpoint returned approximately 65,560
full rows and the browser became unresponsive while rendering them. The list
endpoint no longer runs detection or materializes the full result set.

The current generated-conflict comparability key is the exact mine name, metric
name, fiscal year, and unordered document pair. Candidate groups use the
case-normalized mine/metric plus fiscal year, then apply metric-domain and unit
compatibility and the 1% discrepancy threshold. Period granularity (monthly,
quarterly, annual/YTD), reporting month/quarter, measurement context, and metric
qualifiers are not represented as independent fields in `ExtractedMetric` or
`DataConflict`. Therefore the implementation cannot prove that every same-name,
same-fiscal-year comparison is semantically equivalent; it must not invent those
missing dimensions. The observed examples are legitimate according to the
current stored key, but the missing dimensions remain a known semantic limitation
for later conflict-model work.

`DataConflict` rows and `DataConflictRecord` rows are separate stores. The old
diagnostic `existing_conflicts` was ambiguous: in the detector it meant loaded
generated `DataConflict` identities, while the API-side value represented a
different persisted official-record/list concept. Detector logging now calls the
former `existing_data_conflicts`; list logging reports
`data_conflict_rows`, `official_non_overlapping_rows`, and `total` separately.
The legacy list deduplication rule is preserved in SQL: an official record is
excluded only when a generated conflict has the same mine, fiscal year, and
metric. Historical rows are not deleted or silently rewritten.

`GET /api/v1/conflicts` now accepts `skip` and `limit` (maximum 100) plus the
existing status/subsidiary filters and optional mine, metric, and fiscal-year
filters. It returns `{items,total,skip,limit,has_next}`. The database query loads
only a bounded page window and the UI renders one 50-row page with total and
previous/next controls. `POST /api/v1/conflicts/recompute`, restricted to Admin
and Reviewer roles, is the explicit expensive detector operation. Conflict detail
and resolution endpoints remain unchanged, including stable IDs and idempotent
resolution behavior.

The user-provided live acceptance measurements remain the authoritative live
benchmark for the pre-change endpoint: 7 SQL queries, 44,688 candidate pairs,
26,995 current discrepancies, and 65,560 response rows. This shell could not
connect to the disposable PostgreSQL service during final verification and did
not substitute local SQLite counts for those values. Live PostgreSQL validation
of OPEN/RESOLVED/stale/legacy breakdowns and the before/after payload/latency
must be repeated with the acceptance services running.

Focused pagination, explicit-recompute separation, legacy conflict-list compatibility,
resolution, and API tests pass. Python compilation passes. Frontend TypeScript and the Next.js
production build pass. Step 2B remains **READY FOR MANUAL RE-ACCEPTANCE**.

Final automated totals for this change: `pytest -q --basetemp .pytest-tmp-conflict-suite backend/tests` => **375 passed, 5 failed, 2 skipped, 17 subtests passed**. The five failures are the pre-existing offline `sentence-transformers/all-MiniLM-L6-v2` ONNX artifact tests; no new conflict pagination test failed. The frontend `tsc --noEmit` and `next build` both exit 0.

### Conflict resolution modal viewport positioning

Manual acceptance identified a positioning defect, not a resolution/API defect.
The dashboard `main` element uses the `animate-page-enter` transform. That
transformed ancestor changed the containing block for the modal's `position:
fixed` overlay, so a modal opened from a lower table row could be positioned
relative to the long document instead of the viewport.

`ConflictResolveModal` now renders through a React portal attached to
`document.body`. Its overlay is therefore viewport-relative with `fixed inset-0`
and centered flex positioning. The dialog retains an internal `max-h-[90vh]`
scroll region, while the background body is locked during display and the
original body styles and scroll position are restored on close. No pagination,
conflict identity, resolution, or backend behavior changed.

Frontend TypeScript checking and the production Next.js build pass after the
fix. A dedicated component-test runner is not configured in the repository;
manual browser acceptance remains required at the top of page 1, on page 9,
and near the bottom of a visible page.

### Conflict resolution identity contract fix

The failed request for `/conflicts/65555/resolve` was a real backend identity
contract defect. `65555` is the persisted primary key of a generated
`DataConflict`. The old detail and resolve handlers classified every numeric ID
below 10,000 as generated and every ID at or above 10,000 as official. That
cutoff misclassified valid generated rows after the table grew beyond 10,000,
so the handler looked for an official record and returned 404.

Conflict API responses now include an explicit stable `conflict_key`:

- generated conflict: `data:<DataConflict.id>`
- official conflict: `official:<DataConflictRecord.conflict_id>`

The frontend submits this key for detail and resolution. Numeric IDs remain in
responses for display and legacy compatibility. Numeric detail/resolve URLs now
look up `DataConflict` first, then apply the old official offset only when no
generated row exists. Persisted primary keys and audit records are unchanged.
Comparison deep links now use the namespaced key when available.

Regression coverage proves paginated generated ID `65555` flows through list,
detail, resolve, `RESOLVED` persistence, and exactly one audit record. Existing
official numeric compatibility, nonexistent-ID 404 behavior, idempotency, and
pagination tests remain passing. Focused backend result: **8 passed**. Python
compilation, frontend TypeScript checking, and the Next.js production build
pass. Step 2B remains **IN PROGRESS / READY FOR MANUAL RE-ACCEPTANCE**.

### Conflict evidence deep-linking

Conflict list items now expose independent `evidence_a` and `evidence_b`
objects. For generated `DataConflict` rows, each side is matched to the
persisted `ExtractedMetric` using document, mine, metric, fiscal-year, and the
persisted comparison value. The response includes the metric record ID and its
persisted one-based `page_number`. The two sides are resolved independently;
one side's page is never inferred from the other side or from the filename.

The frontend opens the existing workspace in a new tab using:
`/documents/{document_id}?page={page_number}&evidence={metric_id}`. The
workspace and extraction records both use one-based page numbers, so the
navigation boundary performs no offset conversion. Invalid, missing, ambiguous,
or non-exact metric matches are explicitly marked as unavailable. The current
`ExtractedMetric` schema has no reliable metric-level bounding box, so the API
returns no fabricated geometry and the workspace states that exact highlighting
is unavailable while still opening the exact persisted page when one exists.
Official conflict records currently have no linked document/page provenance and
therefore display the explicit page-level-provenance-unavailable state.

Added acceptance coverage verifies page 1 and a later page for both conflict
sides, missing page provenance, no fabricated bounding boxes, and the generated
list-to-provenance contract. Backend focused result for this change: **17
passed** across the conflict pagination and conflict-engine suites; Python
compilation passed; frontend TypeScript checking passed (`tsc --noEmit`, exit
0). An earlier build attempt was blocked by a transient Windows `EPERM` on the
live `frontend/.next/trace` file; the subsequent clean build completed
successfully. Step 2B remains **READY FOR MANUAL RE-ACCEPTANCE**.

### Official source access from the Document Workspace

The workspace header now uses the persisted document `source_type` and
`source_url` fields. When the source type is `OFFICIAL` or
`OFFICIAL_WEBSITE` and the persisted value is a valid credential-free HTTP(S)
URL, the filename and an explicit `Official source` label open that original
government URL in a new tab. Manual documents, missing URLs, malformed URLs,
unsafe schemes, and credential-bearing URLs display `Official source
unavailable`; no URL is inferred from a filename and no web lookup is made.

For a PDF workspace opened with a valid `page` query parameter, the official
link receives a best-effort `#page=N` fragment. This does not change the local
COALINTEL evidence reader or claim that every government PDF viewer honors the
fragment. The local workspace remains the source for persisted extraction
evidence and page navigation.

Official-source URL acceptance coverage passed for URL present, missing source,
manual source, PDF page fragments, non-PDF behavior, unsafe schemes, and
credential-bearing URLs. TypeScript checking, Python compilation, and the
Next.js production build all passed for this change.

### Evidence workspace table readability

The existing Document Workspace now renders the persisted `document_tables`
artifacts associated with the active page. Headers, row arrays, blank cells,
cell-record counts, available cell geometry, merged-cell metadata, extraction
method/confidence, and persisted warnings are shown without reparsing or
heuristic table reconstruction. Unsupported or missing row structure is shown
as an explicit unavailable state.

Page text remains the complete persisted extraction text because the current
artifact model does not provide a reliable table-region exclusion map. The UI
therefore does not silently remove or duplicate text based on guesses. Evidence
summaries use the persisted metric locator and page, and explicitly state that
metric-to-table-cell provenance is unavailable when no direct relationship is
persisted. No OCR, ingestion, conflict, or extraction semantics changed.

Presentation acceptance tests, official-source-link tests, conflict evidence
tests, and comparison regression tests passed. TypeScript checking, Python
compilation, and the Next.js production build passed. Step 2B remains **IN
PROGRESS / READY FOR MANUAL RE-ACCEPTANCE**.

### Document Workspace layout refinement

The workspace keeps the metrics and page-evidence reader in the upper two-column
area. The metrics card is now a bounded flex panel with an independently
scrollable metric body, sticky column headers, and an internal horizontal scroll
for its wide table. The page reader retains page navigation, Page Content
Summary, raw-text disclosure, evidence locators, and official-source access.

Persisted tables are now rendered once, below the two-column area, at full
content width. Their table containers retain horizontal scrolling and a minimum
readable table width so wide government tables are not compressed into
unreadable columns. No ingestion, OCR, extraction, conflict, provenance, or
backend API behavior changed. Relevant frontend tests, TypeScript checking, and
the Next.js production build passed. Step 2B remains **READY FOR MANUAL
RE-ACCEPTANCE**.

### Persisted table merge/span audit

The table artifact model persists `merged_cells_json`, but the affected PDF
table extraction path currently persists cell row/column indices and optional
geometry without a row-span/column-span relationship. Therefore labels such as
`Power Generation`, `Fig in MU`, and `During the period of May` cannot be
reliably promoted to spanning headers from the current PDF metadata alone; the
frontend must not infer those relationships from blank neighboring values or
visual position.

The presentation now consumes explicit persisted merge metadata when present,
including Excel-style ranges such as `A1:B1` and explicit row/column span
records, and renders them with HTML `rowSpan`/`colSpan`. Covered cells are not
given artificial `Blank header` labels. Independent blank cells remain blank.
When no merge metadata exists, the current auditable representation is retained.
No backend, extraction, OCR, ingestion, conflict, or provenance semantics were
changed.

The live PostgreSQL metadata query could not be completed in this shell because
the local `pgpass.conf` entry was not accepted; the application fallback was
SQLite with zero table records. Consequently, the exact affected live row/cell
JSON was not claimed here and requires manual verification against the
acceptance database. Persisted-merge acceptance tests and TypeScript checking
passed. A Next build attempt was blocked by Windows `EPERM` on the existing
live `.next/trace` file. Step 2B remains **IN PROGRESS / READY FOR MANUAL
RE-ACCEPTANCE**.

### Page Content Summary presentation

When reliable persisted structured tables exist for the active page, the
Document Workspace now presents a deterministic **Page Content Summary** before
the table artifact. The summary uses only persisted table titles, headers, and
row counts. The complete persisted table remains immediately below it, including
blank cells and warnings. The original page text is retained in a collapsed
**View raw extracted text** disclosure for audit/debugging.

Pages without reliable persisted headers/rows retain the existing text-first
presentation. No table structure, semantic meaning, or cell provenance is
inferred in the frontend. Presentation tests cover table pages, ordinary/no
structure pages, titles/columns, blank cells, and evidence metric lookup.
TypeScript checking and the Next.js production build passed. Step 2B remains
**READY FOR MANUAL RE-ACCEPTANCE**.
