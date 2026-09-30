# Task 5 — PostgreSQL Step 1 Acceptance

## Database safety

All PostgreSQL work used only `coalintel_step1_acceptance` on localhost:5432
with user `postgres`. Authentication came from local `pgpass.conf`; the
password was not printed, logged, persisted, or committed. The normal
development database was not modified.

## Migration result

PostgreSQL 18.6 connection: **PASS**.

The disposable database was prepared with the repository base schema, then
Step 1 and related columns/tables were removed to emulate the pre-Step-1
schema. These migrations were applied in order with `ON_ERROR_STOP=1`:

1. `001_add_data_origin_to_extracted_metrics.sql`
2. `002_add_missing_mine_master_and_provenance_columns.sql`
3. `003_step1_document_ingestion.sql`

Result: **PASS**.

A second run of all three migrations also passed with expected “already exists”
notices: **idempotence PASS**.

Validated relations include:

- `documents`
- `official_sources`
- `official_documents`
- `document_pages`
- `document_tables`
- `document_images`

Validated relationships and indexes include official documents → official
sources, documents → official documents, pages/tables/images → documents, the
URL/version index, artifact document indexes, and provenance indexes.

## Backend startup

Configured against `postgresql://postgres@localhost:5432/coalintel_step1_acceptance`.

- Startup: **PASS**
- `/health`: HTTP 200
- `/api/v1/health`: HTTP 200
- Protected source/document endpoints correctly require authentication

## Official-source live acceptance correction

The earlier live-sync conclusion that official documents were `INGESTED` was
incorrect. `official_sync_service.py` called `process_file_ingestion()`, which
created and committed a `PENDING` document with `processing_status=DOWNLOADED`,
but it never called `execute_document_processing_pipeline()`. The registry row
therefore recorded acquisition/registration as `INGESTED` even though no pages,
tables or parsed text existed.

The official path now invokes and verifies the same common processing pipeline
used by manual uploads. A checksum-unchanged record is also reprocessed when
its linked document has not reached a validated state. Processing failures are
recorded as `PROCESSING_FAILED`; they are not marked `INGESTED` or `READY`.

The registry-to-document link is committed before parsing, so a processing
failure remains traceable to the downloaded document and its persisted error.

Bounded live verification against the real Ministry site and this disposable
PostgreSQL database:

- Three existing live records were reprocessed: all reached `PARSED` with
  `REVIEW_RECOMMENDED`, 21/22/21 persisted pages, and corresponding tables.
- The reported `srn-jan-2023.pdf` record was reprocessed: 128 pages, 128
  `document_pages`, 192 tables, native/OCR mixed page text, and no error.
- The backend was restarted; the 128 pages and 192 tables remained available.
- A second bounded sync returned `unchanged=3`, `failed=0`, and created no new
  versions for the three-sample check.

The initial Task-5 “live sync PASS” is therefore superseded. Acquisition and
registry persistence passed, but successful parsing was not previously proven.

## Step 1 acceptance tests

With the backend configured for PostgreSQL:

```text
59 passed, 3 warnings
```

This covered ingestion, official-source synchronization behavior, OCR, tables,
persistence, processing reliability, and standalone ingestion.

Final full backend rerun after database seeding:

```text
359 passed, 5 failed, 2 skipped, 17 subtests passed
```

The five remaining failures are ONNX embedding tests requiring unavailable
offline `all-MiniLM-L6-v2` model artifacts. They are outside Step 1 and do not
prevent PostgreSQL-backed ingestion startup or processing.

An earlier full run also showed the existing `test_mines_api.py` fixture expects
startup-seeded mine data before creating its client. It passed in isolation once
startup seeding had run and passed in the subsequent full run; this was a test
ordering/fixture initialization issue, not a PostgreSQL migration failure.

## Status

PostgreSQL migration/startup acceptance: **PASS**.

Previous live official-ingestion acceptance: **INVALIDATED and corrected**.
Corrected bounded live official-ingestion acceptance: **PASS**.

## Existing official-document recovery

The previously broken official-sync path left 96 current Ministry-linked
documents in `DOWNLOADED`/unvalidated states. They were reprocessed in bounded
batches against the same document IDs and persisted files; no replacement
versions were created and no records were deleted.

Recovery result:

- Candidates: **96**
- Successfully processed: **96**
- `READY` / `PARSED`: **10** across the 100 current official documents
- `REVIEW_RECOMMENDED`: **90** across the 100 current official documents
- `PROCESSING_FAILED`: **0** current documents after bounded retries
- Still `DOWNLOADED` / `PENDING`: **0**
- Duplicate versions created during recovery: **0**

The remaining four documents had already been validated before recovery began;
therefore the all-current totals above are 100 validated documents. One old,
non-current `FAILED` registry row remains as an audit record.

Representative persisted artifacts include:

- `srn-jan-2023.pdf`: 128 pages, 128 page rows, 192 tables, page text and
  mixed native/OCR evidence; four review warnings.
- `msg-june25.pdf`: 30 pages, 30 page rows, 22 tables and 19 warnings.
- `14-06-2022a-wn.pdf`: 76 pages, 76 page rows, 83 tables and 50 warnings.
- `srn-jan-2025.pdf`: 129 pages, 129 page rows, 178 tables and 22 warnings.
- `srn-Aug-2021.pdf`: 122 pages, 122 page rows, 182 tables and 5 warnings.

The recovery exposed and fixed two genuine common-pipeline defects: stale
intermediate/failure states were not reset before an in-place retry, and
extracted metric fields could exceed existing PostgreSQL column limits. The
optional vector/ONNX phase was bypassed only for the final retry worker; page,
table, OCR, validation and PostgreSQL artifact persistence used the common
pipeline.

Focused regression tests for both defects passed: **2 passed, 8 deselected**;
Python compilation passed.

Files changed in this recovery correction:

- `backend/app/services/processing_pipeline.py` — reset stale in-progress/
  failure states for safe in-place retries and constrain extracted metric text
  to existing schema limits.
- `backend/tests/test_processing_reliability.py` — regression coverage for
  failure-state reprocessing and legacy metric-column bounds.
- `implementation_reports/TASK5_POSTGRESQL_ACCEPTANCE.md` — recovery evidence
  and corrected counts.
- `implementation_reports/STEP1_FINAL_ACCEPTANCE.md` — final acceptance
  correction and recovery evidence.

The later localhost acceptance alert was a request-lifecycle issue, not a
Ministry sync failure. The synchronous sync endpoint could outlive the browser
or proxy request and had no concurrent-run claim. It now returns `202 Accepted`
after an atomic persisted claim, runs the existing sync in a worker-owned
session, rejects duplicate requests with `409`, and is polled by the existing
frontend status surface. Successful runs become `CONNECTED`; handled partial
or worker failures remain explicit `PARTIAL`/`ERROR` states.
Startup reconciliation also converts orphaned `SYNCING` claims left by a
backend restart into explicit `ERROR` state.

Official-sync blocker regression tests: **PASS** (`13 passed`).

Task 4 Step 1 integration/build scope: **PASS with five documented out-of-scope
ONNX test limitations**.

Final reconciliation: Step 1 is **COMPLETE** with five isolated, out-of-scope
ONNX/model-artifact failures documented in the final acceptance report. No
Step 2 work was started.
