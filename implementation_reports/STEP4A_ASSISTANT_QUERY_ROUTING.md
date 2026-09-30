# Step 4A — COALINTEL AI Assistant: Query Understanding, Routing & Grounded Answers

## Status

**STEP 4A — READY FOR MANUAL ACCEPTANCE**

Step 4A adds a deterministic query-analysis and evidence-first orchestration
layer to the existing `/api/v1/query/ask` assistant endpoint. Step 1–3
ingestion, extraction, provenance, conflict, and pgvector behavior were not
redesigned. Step 4B–4D work was not started.

## 1. Existing assistant/RAG audit

Before this change, `/query/ask` called the legacy `rag_service.execute_rag_query`.
That path combined Chroma vector search, keyword search, legacy extracted metrics,
Gemini/OpenAI/degraded generation, and citation gates. Step 3 retrieval APIs
existed independently but were not used by the main assistant endpoint.

The existing assistant frontend, authentication dependency, citation drawer, and
answer card were reusable. The legacy service remains available for databases
that do not yet have the Step 3 migration, preserving compatibility with older
test/development stores.

## 2. Architecture implemented

Added `app/services/assistant_service.py` with this flow:

```text
question
  -> deterministic analysis
  -> STRUCTURED / SEMANTIC / HYBRID route
  -> Step 3 evidence retrieval
  -> evidence packet
  -> deterministic answer or bounded grounded LLM synthesis
  -> response with route, support state, provenance, and generation status
```

The production route uses Step 3 when `knowledge_chunks` exists. The legacy
RAG service is used only as a compatibility fallback when the Step 3 table is
not present; this prevents test SQLite databases and older deployments from
breaking while the migration is rolled out.

## 3. Query routing

`analyze_query()` returns the selected route, extracted filters, entities, and
debuggable signals. It uses the existing deterministic entity/metric/period
parsers and explicit lexical signals; an LLM is not allowed to choose database
access.

- `STRUCTURED`: exact numeric/entity/metric/period questions. Uses only
  `structured_facts` retrieval for factual values.
- `SEMANTIC`: explanations, policy, descriptions, summaries, and document prose.
  Uses pgvector evidence chunks.
- `HYBRID`: comparisons or questions requiring exact facts plus context. Returns
  structured and semantic candidates separately.

Representative routes:

```text
What was ECL coal production in November 2020?        STRUCTURED
What is the policy for coal dispatch reporting?        SEMANTIC
Compare ECL production with report context.            HYBRID
```

The semantic acceptance threshold is currently `0.20` cosine similarity. It is
an explicit conservative gate, not an accuracy claim, and should be calibrated
against a labelled retrieval set later.

## 4. Evidence packet and response contract

The response now carries, in addition to the existing answer/citations fields:

- `route`;
- `support_state`: `SUPPORTED`, `CONFLICTING`, `UNSUPPORTED`, or `UNAVAILABLE`;
- `generation_status`;
- `analysis` with route/filter diagnostics;
- `structured_facts`;
- `semantic_evidence`;
- `conflicts`;
- `source_references` containing document/page/table/evidence locators.

Structured facts retain their Step 2C entity, metric, value, unit, period,
validation, extraction, and evidence fields. Semantic results retain Step 3
chunk IDs, document/page/table locators, retrieval scores, provider/model, and
source locator metadata.

Contradictory structured candidates are grouped and returned separately. No
value is silently selected as authoritative.

## 5. Grounded generation behavior

For semantic and hybrid routes, the LLM receives only the bounded retrieved
evidence packet inside the existing untrusted-document prompt isolation. Citation
tags are validated against the retrieved evidence before the answer is marked
supported. If citations cannot be validated, the result becomes
`INSUFFICIENT_EVIDENCE` rather than a plausible uncited answer.

For structured routes, values are rendered deterministically from structured
facts and do not depend on semantic similarity or LLM generation. This preserves
numeric source-of-truth behavior.

If Gemini/OpenAI is unavailable, the existing degraded grounded provider may
produce an evidence-only answer. The response explicitly reports degraded
generation. If retrieval/model availability fails, the response exposes
`UNAVAILABLE`/`UNSUPPORTED` and does not fabricate an answer.

## 6. API/frontend integration

The existing authenticated `POST /api/v1/query/ask` endpoint now invokes the
Step 4A orchestration when the Step 3 knowledge store is available. No new
chatbot surface was created.

The existing assistant answer card now displays the selected route, non-supported
state, and generation status. Existing citations, evidence drawer, loading/error
states, and authentication behavior remain in place.

## 7. Files changed

- `backend/app/services/assistant_service.py` — new Step 4A analysis/retrieval/
  grounding orchestration.
- `backend/app/api/query.py` — Step 3-aware compatibility routing for the
  existing assistant endpoint.
- `backend/app/schemas/query.py` — response contract extensions.
- `backend/tests/test_step4a_assistant.py` — deterministic Step 4A tests.
- `frontend/lib/api/queryApi.ts` — new response diagnostics/types.
- `frontend/components/query/CitedAnswerCard.tsx` — route/support/generation
  diagnostics.
- `implementation_reports/STEP4A_ASSISTANT_QUERY_ROUTING.md` — this report.

No database migration or production ingestion/OCR/Document AI change was made.

## 8. Tests

New focused suite:

```text
python -m pytest backend/tests/test_step4a_assistant.py -q
6 passed, 1 warning
```

Coverage includes structured, semantic, and hybrid routing; entity/metric/period
filters; structured-only exact retrieval; semantic pgvector routing; hybrid
dual retrieval; conflict preservation; unavailable knowledge/embedding behavior;
and authenticated route dependency presence.

The existing RAG regression suite was not counted as complete in this pass
because its host run did not terminate within the bounded execution window. The
legacy service itself was not removed; its prior regression coverage remains
applicable to the compatibility path.

Frontend validation was attempted with the repository's existing installed
toolchain. TypeScript and Next.js could not start because Windows returned
`EPERM` while Node attempted to read the existing pnpm-linked files under
`frontend/node_modules/.pnpm` (TypeScript `_tsc.js` and Next `dist/bin/next`).
No dependency or lockfile was changed. This requires a clean/manual frontend
toolchain run after the file lock is released.

## 9. Known limitations

- Step 3 manual acceptance and Step 2C final manual acceptance remain deferred,
  so answer quality is bounded by the indexed/fact corpus quality.
- The semantic threshold is conservative and not yet calibrated on a labelled
  Step 4 benchmark.
- No final citation/conflict UX, topic modelling, trend intelligence, report
  redesign, or Parliamentary Briefing redesign was implemented.
- Full-corpus knowledge indexing is an operational prerequisite for broad
  assistant coverage; the Step 3 acceptance indexed only a bounded document.
- Legacy Chroma fallback remains for pre-migration stores and should be retired
  only after Step 3 rollout acceptance.

## 10. Manual acceptance procedure

1. Start the backend against the PostgreSQL acceptance database with migration
   005 applied and authenticate as an authorized user.
2. Open the existing Ask COALINTEL page and submit a known exact fact query.
   Verify `Route: STRUCTURED`, values from structured facts, and document/page/
   table provenance.
3. Submit a prose/policy question. Verify `Route: SEMANTIC`, bounded pgvector
   evidence, citations, and provider/generation status.
4. Submit a comparison/context question. Verify `Route: HYBRID`; structured
   values and semantic context remain separate.
5. Test a nonexistent entity/period and verify `UNSUPPORTED` or
   `INSUFFICIENT_EVIDENCE`, without invented values.
6. Temporarily make the embedding/LLM provider unavailable in a controlled
   environment. Verify retrieval or generation degradation is explicit and the
   UI does not present unsupported content as authoritative.
7. Verify a subsidiary-scoped account cannot retrieve outside its existing
   authorized scope and that unauthenticated requests are rejected.

Do not interpret this acceptance as final Step 4 completion.
