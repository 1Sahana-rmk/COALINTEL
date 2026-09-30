# Step 3 — PostgreSQL AI Knowledge Layer

## Status

**STEP 3 — READY FOR MANUAL ACCEPTANCE**

The bounded real-PostgreSQL acceptance path is working. Migration 005 was
applied twice to `coalintel_step1_acceptance`; a representative document was
indexed with real ONNX embeddings; structured, pgvector semantic, and hybrid
retrieval were exercised; and provenance was returned. Step 4 was not started.

## 1. Architecture assessment

The existing Step 1/2 surfaces remain intact:

- `document_pages` and `document_tables` are the persisted canonical page/table
  artifacts.
- `structured_facts` is the Step 2C evidence-linked fact surface, including
  document/page/table references, period, raw/normalized values and units,
  extraction metadata, validation state, and evidence locator JSON.
- `document_chunks` and Chroma remain legacy Step 2 compatibility storage.
- The legacy embedding API still supports its deterministic fallback for its
  existing callers, but the Step 3 path refuses that fallback for semantic
  storage/retrieval.

Step 3 adds one PostgreSQL knowledge surface, `knowledge_chunks`, and builds
chunks from persisted pages, tables, table rows, and structured facts. It does
not reread source files or alter extraction/provenance records.

## 2. Knowledge chunk and provenance contract

`knowledge_chunks` stores document ID, page ID/page number, table ID where
applicable, stable chunk key/index, chunk type, text, content hash, embedding,
embedding provider/model/status, source locator JSON, metadata, and timestamps.

The chunker preserves provenance for page text, table/table-row evidence,
figure markers, and structured facts. Table-row locators retain table ID, page,
row index, non-empty column indexes, and persisted cell/header context. Fact
chunks retain the fact ID and evidence locator. No geometry or cell relationship
is fabricated.

Navigation/TOC-like material is conservatively excluded from embedding
candidates; persisted source artifacts are unchanged.

## 3. Migration and real PostgreSQL result

Added [`005_step3_pgvector_knowledge_chunks.sql`](../backend/migrations/005_step3_pgvector_knowledge_chunks.sql).
It is additive and idempotent:

- `CREATE EXTENSION IF NOT EXISTS vector`;
- `CREATE TABLE IF NOT EXISTS knowledge_chunks`;
- repeat-safe indexes for content hash, document/page/table/type/status,
  embedding, and the stable chunk key.

The generic startup `create_all()` excludes this migration-managed table, so a
Step 1 database cannot silently replace pgvector with a JSON/BLOB test shape.

On `coalintel_step1_acceptance`:

- PostgreSQL: 18.6;
- pgvector server extension: 0.8.6;
- Python `pgvector`: 0.5.0;
- migration run 1: success;
- migration run 2: success with only expected already-exists notices;
- `knowledge_chunks.embedding`: `vector(384)`;
- extension and table/index verification: passed.

The migration did not delete or rewrite existing document, page, table, or
fact data.

## 4. Chroma transition strategy

Chroma is retained only as a legacy Step 2 compatibility path. New Step 3
indexing and retrieval use PostgreSQL/pgvector and do not write or read Chroma.
The later transition can index selected documents, compare provenance/results,
move Step 4 callers to this interface, and deprecate Chroma after rollback and
usage criteria are reviewed. No competing new production vector path was
introduced.

## 5. Embedding behavior

Step 3 uses the strict production embedding API:

- cached all-MiniLM-L6-v2 ONNX model available: persist `READY` real vectors;
- initialization/inference unavailable: persist no vector and explicit
  `UNAVAILABLE` status/reason;
- deterministic SHA-256 vectors are never written to `knowledge_chunks` and
  are never reported as semantic retrieval;
- semantic search returns an explicit unavailable/degraded result rather than
  empty-success.

Current real status:

```text
status=READY
available=True
degraded=False
provider=ONNX
model=sentence-transformers/all-MiniLM-L6-v2
dimension=384
```

## 6. Bounded real indexing and retrieval

Representative document: document **154**, the controlled DOCX acceptance
document (one page with a persisted table). It was deliberately selected
instead of indexing the 100+ document corpus.

Initial indexing result:

```text
generated=27  inserted=27  updated=0  chunk_count=27
embedding_status=READY
persisted total=27, ready=27, unavailable=0
providers=[ONNX]
models=[sentence-transformers/all-MiniLM-L6-v2]
non_null_embeddings=27
```

The repeated indexing check used the same stable keys and produced:

```text
before=27  inserted=0  updated=27  after=27
stable IDs remained [1, 2, 3, 4, 5, ...]
```

This verifies idempotent upsert behavior without duplicate chunks or replacement
document versions.

Real retrieval checks:

- structured search against document 126 and `COAL_PRODUCTION` returned
  evidence-linked facts, including page 11/table 1/row 2/column 3/cell text
  `4.34`, header context `Production During Nov 2020`, and persisted bbox
  where available;
- pgvector semantic Top-K search over document 154 returned five ranked
  results with cosine scores, page/table locators, and ONNX provider metadata;
- hybrid retrieval returned structured and semantic arrays separately with
  `conflicts_preserved=true`;
- a controlled same-period test with two conflicting MCL production values
  returned both candidates rather than merging them. A bounded database audit
  of document 126 found no same `entity + metric + period` group with more
  than one distinct normalized value.

## 7. Authenticated APIs

Added under `/api/v1/knowledge`:

- `GET /health` — PostgreSQL/pgvector storage and embedding readiness;
- `GET /stats` — indexed, ready, unavailable, and provider/model counts;
- `POST /index-document/{document_id}` — Admin/Analyst indexing;
- `GET /structured-facts/search` — authenticated structured retrieval;
- `GET /semantic/search` — authenticated pgvector candidate retrieval;
- `GET /hybrid/search` — authenticated structured + semantic retrieval.

The authenticated HTTP smoke test returned 200 for health, structured, semantic,
and hybrid routes. The health response reported PostgreSQL/pgvector storage and
27 indexed/embedded chunks. Unauthenticated access remains rejected by the
existing authentication dependency. Responses include source document/page/table
references, source locators, extraction metadata, and retrieval status.

## 8. Defects found and fixed during acceptance

1. PostgreSQL `<=>` returned a scalar distance but SQLAlchemy applied the
   vector result processor. The distance expression now declares `Float`, so
   real pgvector ranking works.
2. Hybrid retrieval passed `limit` twice when API filters already contained it.
   Filters are now copied and assigned a default only when absent.
3. Re-indexing originally defaulted to delete/reinsert behavior. The Step 3
   index operation now defaults to stable-key upsert (`replace_existing=False`),
   preserving IDs and preventing duplicate growth.
4. A migration-path assertion depended on the process working directory. The
   test now resolves the migration relative to its own file.

## 9. Tests and validation

Commands run from `backend` using `backend\.venv\Scripts\python.exe`:

```text
python -m pytest tests/test_step3_knowledge_layer.py -q
6 passed, 1 warning

python -m pytest tests/test_step2c_structured_extraction.py -q --disable-warnings
11 passed

python -m pytest tests/test_processing_reliability.py -q --disable-warnings -k "not test_03_pipeline_execution_success_and_idempotency"
8 passed, 3 deselected, 3 warnings

python -m pytest tests/test_low_memory_embedding.py -q --disable-warnings
14 passed, 3 warnings
```

The full processing-reliability run was not counted as passing: its existing
`test_03_pipeline_execution_success_and_idempotency` case did not terminate in
the current host run and was interrupted. The same suite's other eight tests
passed. This is a test-environment/runtime limitation requiring separate
follow-up, not a Step 3 pgvector failure.

The previously reported five offline ONNX failures are no longer present in
`test_low_memory_embedding.py` after the approved local model cache became
available.

Python compilation of the changed Step 3 modules and `main.py` passed. The
deterministic Step 3 suite covers migration clauses, authentication dependency
presence, provenance-preserving chunk generation, TOC suppression, duplicate
prevention, semantic ranking, structured filters, conflict preservation, and
explicit unavailable-embedding behavior.

## 10. Known limitations

- The bounded acceptance indexed document 154 rather than the complete corpus;
  full-corpus indexing needs an operational batch/retry plan.
- No HNSW/IVFFlat index was added; initial exact pgvector cosine ordering is
  sufficient for acceptance, but production-scale tuning remains.
- Structured fact quality remains subject to Step 2C's pending final manual
  acceptance; Step 3 does not repair extraction semantics.
- The legacy Chroma path remains for Step 2 compatibility.
- The real processing-reliability test noted above must be isolated and resolved
  before a claim of a completely green backend suite.
- This task does not provide LLM answer generation, a final question router,
  chat UI, pgvector-based report generation, or Step 4 behavior.

## 11. Manual acceptance procedure

1. Start the backend against `coalintel_step1_acceptance` and authenticate as an
   authorized Admin or Analyst.
2. Call `/api/v1/knowledge/health` and verify PostgreSQL/pgvector storage and
   real ONNX readiness.
3. Index one bounded representative document through
   `POST /api/v1/knowledge/index-document/{id}`.
4. Query `/stats`; verify ready chunks, ONNX provider/model, and no unavailable
   vectors for the selected document.
5. Repeat the same index request; verify count stability and upsert behavior.
6. Run structured search for a known metric/period and inspect document, page,
   table/cell, and evidence-locator fields.
7. Run semantic search and verify ranked Top-K results include page/table
   provenance and real ONNX metadata.
8. Run hybrid search and confirm structured and semantic candidates remain
   separate, including contradictory candidates where present.
9. Stop or make the real embedding service unavailable in a controlled test;
   verify explicit degraded/unavailable behavior and no deterministic vector is
   persisted as production semantic data.
10. Confirm existing Step 1/2 ingestion and Chroma compatibility behavior is
    unchanged.

No Step 4 work was started.
