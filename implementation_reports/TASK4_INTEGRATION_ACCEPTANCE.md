# Task 4 — Step 1 Integration, Regression and Build Hardening

## Result

**Task 4: PASS for Step 1 integration/build scope, with documented out-of-scope
test limitations.** PostgreSQL migration and startup have now been verified on
the disposable acceptance database. Five out-of-scope ONNX tests remain blocked
by missing offline model artifacts.

Step 1 was not declared complete at the time of this earlier report; final
reconciliation is recorded below.

## Files changed

- `backend/app/api/dashboard.py`
  - Fixed an existing genuine regression: `/dashboard/charts` returned from
    inside the subsidiary loop and therefore returned only the first series.
- `frontend/app/(dashboard)/documents/page.tsx`
  - Added explicit document/source query error states and a visible Sync Now
    failure state. Loading and empty states remain non-fatal.
- `implementation_reports/TASK4_INTEGRATION_ACCEPTANCE.md`
  - This integration, regression, migration, and build report.
- `implementation_reports/TASK5_POSTGRESQL_ACCEPTANCE.md`
  - PostgreSQL migration and acceptance evidence.

No dependency manifests were changed. Frontend dependencies were installed
using the existing `package.json` and `package-lock.json`; generated
`node_modules`/`.next` output is environment build state, not a source change.

## Full backend regression

Final run:

```text
359 passed, 5 failed, 2 skipped, 17 subtests passed, 17 warnings
```

The dashboard failure was a genuine regression and is fixed. Its focused tests
now pass: `3 passed`.

The remaining five failures are all `tests/test_low_memory_embedding.py`:

- `test_01_onnx_backend_singleton`
- `test_04_zero_torch_in_embedding_path`
- `test_05_tokenizer_encoding_contract`
- `test_06_strict_offline_operation`
- `test_13_onnx_arena_and_mem_pattern_disabled`

Classification: missing optional/offline ONNX model artifacts. The runtime
reports that `sentence-transformers/all-MiniLM-L6-v2` is not present in the
local Hugging Face cache and outbound model retrieval is disabled. This is
outside Step 1, so the embedding system was not redesigned and tests were not
weakened.

## Database migration

PostgreSQL acceptance verification was completed on the disposable
`coalintel_step1_acceptance` database using PostgreSQL 18.6 at localhost:5432.
The normal development database was not modified.

The disposable database was prepared with the repository base schema, then
Step 1 and related columns/tables were removed to emulate the expected
pre-Step-1 shape. Migrations 001, 002, and 003 were applied in order with
`ON_ERROR_STOP=1` and completed successfully. A second ordered run also
passed, confirming idempotence.

Validated relations include `documents`, `official_sources`,
`official_documents`, `document_pages`, `document_tables`, and
`document_images`, along with Step 1 columns, foreign keys, and indexes.

## Backend startup and API checks

Application startup succeeded in development mode against PostgreSQL.

Verified with `TestClient`:

- `/health` → `200`
- `/api/v1/health` → `200`
- `/api/v1/sources` → `401` without authentication
- `/api/v1/sources/sync-status` → `401` without authentication
- `/api/v1/documents` → `401` without authentication

The protected response confirms authentication remains enforced. Existing Step 1
tests cover authenticated upload, source synchronization, document status,
warnings, history, and table endpoints.

Optional RAG/ONNX artifacts do not prevent the ingestion backend from importing
or starting; vector indexing is explicitly degraded while authoritative
extraction remains persisted.

## Frontend build and integration

Using the existing frontend manifest and lockfile, dependency installation
completed with pnpm. The production Next.js build passed:

- Next.js compilation: PASS
- TypeScript validation: PASS
- Static generation: PASS, 17/17 pages
- Production optimization: PASS

The built server returned HTTP `200` for:

- `/`
- `/documents`
- `/dashboard`

The existing document page is wired to manual upload, source listing, Ministry
sync, document status/listing, and document detail/page APIs. Query loading,
empty, API failure, and Sync Now failure states now render explicitly without
throwing from the page. Authenticated browser-level interaction with Sync Now
and uploaded-document rendering was not completed because no live authenticated
browser session was available. The backend route contract and existing
integration tests were used instead.

## Processing-state integrity

Existing processing/reliability tests pass. The pipeline persists generic
artifacts before optional vector indexing, records extraction failure

s, and
does not turn vector-indexing failure into a false extraction failure. Existing
Step 1 tests verify persisted failures, restart-safe records, and version
handling.

## Remaining limitations

- Five ONNX tests require offline model artifacts not present locally.
- Live authenticated frontend interaction was not browser-verified.
- No new migration runner was introduced; the existing ordered SQL migration
  workflow was exercised directly.

## Commands executed

- Full backend: `359 passed, 5 failed, 2 skipped, 17 subtests passed`

Final reconciliation: all Step-1 focused suites passed, the frontend build
passed, and PostgreSQL persistence was read-only verified. The five remaining
full-suite failures are isolated optional ONNX/model-artifact failures.
Step 1 is **COMPLETE**. No Step 2 work was started.
- Focused dashboard regression: `3 passed`
- Python compilation: `PASS`
- Frontend production build: `PASS`, 17 static pages generated
- Backend startup/API smoke: health `200`; protected APIs correctly `401`
