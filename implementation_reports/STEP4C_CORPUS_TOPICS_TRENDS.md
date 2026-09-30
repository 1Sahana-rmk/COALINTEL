# STEP 4C — Corpus Topics, Trends & Historical Intelligence

Status: **STEP 4C — READY FOR MANUAL ACCEPTANCE**

## Audit findings

The previous `/api/v1/analytics/wordcloud` implementation returned a hard-coded
`DEFAULT_ALL_CIL_TOPICS` list and only appended a few extracted metric labels.
The analytics page also had the same static list as a client-side fallback. The
displayed “TF-IDF” score was a presentation calculation over those fixed
weights, not a measured corpus score. There was no topic evidence linkage or
structured-fact trend service behind the page.

The existing Step 3 knowledge chunks, Step 2C `structured_facts`, document
metadata, and Step 4B provenance conventions are retained and used as the
inputs for this bounded implementation. No migration or schema change was
required.

## Architecture implemented

`app/services/corpus_intelligence_service.py` provides deterministic primitives:

- Word cloud: bounded token/phrase frequency from persisted `knowledge_chunks`.
  When a document has not yet been Step 3-indexed, persisted
  `extracted_metrics` are used as an explicit compatibility fallback; no static
  topics are substituted.
- Topics: deterministic co-occurrence groups over the same persisted corpus.
  Topic IDs are stable hashes of representative terms and each topic includes
  supporting document/page/chunk references.
- Trends: structured-fact observations grouped by entity, normalized period,
  and unit. Fiscal years remain separate; no cross-year sum is produced.
- Historical comparison: deterministic same-period, same-unit comparison with
  absolute and percentage change only for accepted, non-conflicting facts.

Noise suppression is limited to stopwords, numeric-only tokens, navigation/TOC
labels, and generic extraction metadata labels. It does not inject a coal
vocabulary or manufacture domain topics.

Pending/review-required facts remain visible as `UNVERIFIED` observations for
auditability. Only facts with `fact_status=ACCEPTED` and
`validation_status=ACCEPTED` receive `OK` status or participate in derived
comparisons. Conflicting values remain separate candidates with
`CONFLICTING` status and source fact IDs.

## APIs

All routes use the existing authenticated analytics router:

- `GET /api/v1/analytics/wordcloud`
  - filters: `subsidiary_filter`, `document_id`, `period`, `top_n`
  - returns measured `weight`, `occurrence_count`, `document_count`, and method
- `GET /api/v1/analytics/topics`
  - returns topic terms, prevalence, and supporting evidence references
- `GET /api/v1/analytics/trends?metric=...`
  - returns period-preserving points and validation state
- `GET /api/v1/analytics/historical?metric=...`
  - returns same-period comparisons and fact IDs used for calculations

Responses use `EMPTY`, `UNVERIFIED`, `CONFLICTING`, and `UNAVAILABLE` semantics
where applicable rather than silently returning fake values.

## Frontend changes

The existing Analytics page now consumes corpus-derived responses, removes the
hard-coded fallback topic list and fixed mine/subsidiary counts, displays topic
supporting document/page references, and shows a bounded production history
table with the explicit “annual values are not summed across years” rule.
The existing word-cloud and matrix components now describe measured corpus
frequency rather than pretending the values are TF-IDF.

## Bounded real-data validation

Against `coalintel_step1_acceptance`, a bounded read-only run produced:

- word-cloud input: 27 persisted Step 3 chunks; top terms included `production`,
  `seam`, `depth`, `borehole`, and `bh-27` after metadata/navigation suppression;
- topics: deterministic topics with document/page evidence, including pages 1,
  4, and 8 in the bounded indexed sample;
- structured-fact sample counts before status gating: production 121 points,
  dispatch 40, OBR 71, exploration 9;
- the current acceptance database's 10,046 Step 2C facts are
  `CANDIDATE`/`REVIEW_REQUIRED`, so those observations are surfaced as
  `UNVERIFIED` and are not used for derived historical calculations;
- no accepted facts were silently presented as validated trend values.

This is an honest data-state result, not an accuracy claim. Manual acceptance
should use a scope containing accepted facts to verify `OK` trend points and
derived comparisons.

## Performance and caching

The service uses bounded database reads (`10,000` corpus items, `200` word-cloud
terms, `50` topics, and `1,000` facts per trend request). It performs no model
initialization, embedding generation, or corpus-wide reprocessing on dashboard
requests. React Query retains the existing 60-second client cache. A future
persisted analysis cache can be added when document/index invalidation semantics
are available; this pass avoids a new cache table or vector store.

## Tests

Added `backend/tests/test_step4c_corpus_intelligence.py` covering:

- corpus-derived frequency and noise suppression;
- topic evidence linkage and empty corpus;
- multi-period production series without summation;
- same-period comparison and provenance;
- conflict preservation/no averaging;
- unit separation.

Focused result:

```
8 passed, 1 warning
```

The combined Step 3/4A/4B/4C regression run also passed:

```
31 passed, 3 warnings
```

Python compilation of the new service, analytics API, and schemas passed.
Frontend TypeScript/build validation remains subject to the existing Windows
EPERM lock under `frontend/node_modules/.pnpm`; dependencies and lockfiles were
not changed to bypass it.

## Known limitations and manual acceptance

- Topic names are deterministic term-group labels, not curated semantic labels.
- The current acceptance database has review-required Step 2C facts, so it is
  expected to show unverified observations rather than authoritative derived
  results.
- Evidence links in the Analytics page currently expose document/page identity;
  the existing Document Workspace remains the path for full cell-level review.
- No speculative recommendations, LLM topic generation, report redesign, or
  Step 5 evaluation was started.

Manual acceptance:

1. Open Analytics as an authenticated user and verify that terms change when
   the subsidiary scope changes and that an empty scope is an honest empty state.
2. Inspect topic evidence references and open the referenced document/page.
3. Open production, dispatch, and OBR trends with a scope containing accepted
   facts; confirm periods remain separate and conflicting points are not averaged.
4. Compare two entities for the same period/unit and verify fact IDs and source
   evidence for the derived change.
5. Confirm a unit mismatch, missing operand, or review-required fact displays an
   unavailable/unverified state rather than a fabricated calculation.
