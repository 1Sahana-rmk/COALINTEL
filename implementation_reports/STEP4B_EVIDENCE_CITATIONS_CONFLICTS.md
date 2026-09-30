# Step 4B — Evidence Citations, Conflict Handling & Answer Validation

## Status

**STEP 4B — READY FOR MANUAL ACCEPTANCE**

Step 4B extends the Step 4A response and existing assistant UI. It does not
redesign routing and does not modify Steps 1–3, conflict persistence, OCR,
ingestion, or the database schema.

## 1. Audit findings

The Step 4A assistant already had:

- structured-fact and semantic retrieval provenance;
- an existing citation gate validating `[filename, Page N]` tags against the
  supplied retrieval packet;
- the existing Document Workspace deep link and source-file endpoint;
- persisted official `source_url` and source type on `documents`;
- persisted `document_tables`/cell locators and Step 2C fact locators.

The gap was that the assistant response reduced these to generic document/page
citation items. Table/cell locators, official URLs, excerpts, validation state,
and claim-to-evidence associations were not exposed consistently. Conflict
candidates were detected but were not represented as an explicit answer packet.

## 2. Canonical citation contract

`CitationItem` now supports:

```text
document_id
document_name
page_number
evidence_type
table_id
locator
source_url
source_type
file_type
excerpt
extraction_method
confidence
validation_state
citation_tag
```

Missing page/table/cell geometry remains null or an empty locator. No frontend
geometry or URL is fabricated. The existing `officialSourceLink` safety checks
remain the authority for opening persisted official URLs.

## 3. Claim/evidence mapping

The response now includes `claims`:

- structured facts produce one claim per fact, each linked to its own fact/page/
  table/cell evidence;
- semantic/hybrid generated answers produce a bounded synthesis claim linked to
  the citations that passed validation;
- `source_references` contains the normalized evidence references for the full
  packet.

Thus two numeric facts from different table cells/documents cannot silently share
one generic citation.

## 4. Citation validation

Generated citation tags are still validated against the exact retrieval packet.
Unknown document/page citations are dropped. If no valid citation remains, the
answer is downgraded to `INSUFFICIENT_EVIDENCE` rather than marked supported.

Structured numeric answers do not depend on generated citation text: they are
constructed directly from retrieved structured facts and receive canonical
fact-level citations.

## 5. Conflict behavior

Contradictory structured candidates remain separate. The response includes:

- `conflicts` with each candidate fact/value/unit/period/source;
- `conflict_states` indicating `UNRESOLVED` or an existing persisted
  `RESOLVED` conflict when the legacy conflict record matches;
- `support_state=CONFLICTING`.

No values are averaged or silently selected. Existing resolved conflict records
remain resolved and their original evidence remains available.

## 6. Unsupported and degraded behavior

The assistant distinguishes:

- `SUPPORTED` — evidence and citations validated;
- `CONFLICTING` — supported candidates disagree;
- `UNSUPPORTED` — no sufficient evidence or weak semantic match;
- `UNAVAILABLE` — knowledge store or required model unavailable.

Extraction confidence remains separate from answer support state. Embedding and
LLM failures are exposed through `generation_status`; the deterministic/hash
embedding fallback is not used as production semantic evidence.

The semantic acceptance threshold remains the explicit Step 4A threshold of
`0.20` cosine similarity. This is a conservative gate, not an accuracy claim.

## 7. Frontend changes

The existing Cited Answer Card now shows route/support/generation diagnostics and
an explicit conflicting-evidence panel. The existing citation drawer now shows:

- evidence type, table ID, validation state, and persisted locator;
- the persisted evidence excerpt;
- Open Canvas at the cited page;
- Open Official Source when the persisted URL passes existing safety checks;
- Download Stored Copy through the authenticated existing document endpoint.

The drawer no longer fabricates document ID `1` when provenance is missing.

## 8. Files changed

- `backend/app/services/assistant_service.py`
- `backend/app/schemas/query.py`
- `backend/tests/test_step4b_citations.py`
- `frontend/lib/api/queryApi.ts`
- `frontend/components/query/CitedAnswerCard.tsx`
- `frontend/components/query/CitationDrawer.tsx`
- `implementation_reports/STEP4B_EVIDENCE_CITATIONS_CONFLICTS.md`

## 9. Deterministic tests

```text
python -m pytest backend/tests/test_step4a_assistant.py backend/tests/test_step4b_citations.py -q --disable-warnings
10 passed

python -m py_compile backend/app/services/assistant_service.py backend/app/api/query.py backend/app/schemas/query.py
passed
```

Coverage includes structured numeric citations, semantic/hybrid evidence,
multiple claims with separate evidence, narrow table/cell locators, missing
locators, hallucinated/out-of-packet citation rejection, unresolved/resolved
conflict state handling, no averaging, unsupported retrieval, and degraded
behavior.

Existing official-source URL tests cover missing, manual, malformed, unsafe,
credential-bearing, and page-fragment URLs. Frontend TypeScript/Next build
validation was attempted but remains blocked by the known Windows `EPERM` lock
under `frontend/node_modules/.pnpm`; no dependency or lockfile was changed.
Direct Node execution of the repository's TypeScript test files is not the
configured test harness and failed module-extension resolution, so it was not
counted as a frontend test result.

## 10. Bounded real-data validation

Against PostgreSQL `coalintel_step1_acceptance`, the bounded Step 3 retrieval
sample returned:

```text
COAL_PRODUCTION       2 facts, document 126, page 11
COAL_DISPATCH         2 facts, document 126, page 12
OVERBURDEN_REMOVAL    2 facts, document 126, page 38
EXPLORATION_DRILLING  2 facts, document 126, page 56
```

Representative persisted normalized values included production `4.34` and
`2.54`, dispatch `26.26` and `14.98`, OBR `8.38` and `58.222`, and exploration
drilling `43870` and `40225`. These were inspected through structured retrieval;
the task makes no corpus-wide accuracy claim.

The semantic sample over indexed document 154 returned three pgvector results
with scores approximately `0.322`, `0.209`, and `0.207`, preserving page and
chunk provenance. An assistant semantic query with insufficient grounded
citation support correctly returned `UNSUPPORTED` rather than an uncited fact.

## 11. Known limitations

- Exact claim-to-cell mapping for generated free-form LLM prose is bounded by
  the citation syntax and retrieval packet; richer claim parsing belongs in a
  later citation UX pass.
- The bounded real sample is not a retrieval or answer-accuracy benchmark.
- Full-corpus Step 3 indexing and Step 2C final manual acceptance remain
  deferred.
- Conflict matching uses existing `DataConflict` identity where it can be
  matched to retrieved fact dimensions; it does not redesign conflict identity.
- Frontend production build/typecheck remains pending the known Windows file
  lock being released.

## 12. Manual acceptance procedure

1. Start the backend against PostgreSQL with Step 3 migration applied and log
   in as an authorized user.
2. Ask an exact production/dispatch/OBR question. Verify each value has its own
   document, page, fact, and table/cell locator where persisted.
3. Ask a semantic explanation question. Verify only retrieved pgvector evidence
   is cited and unsupported claims are refused.
4. Ask a hybrid comparison. Verify structured values and semantic context remain
   separate.
5. Use the citation drawer to open the exact workspace page, official source,
   and authenticated stored copy where available.
6. Test an unresolved conflicting fact and verify both values remain visible with
   `CONFLICTING`; no average or silent winner is shown.
7. Resolve an existing conflict, repeat the query, and verify the resolved state
   is reflected without deleting the original evidence.
8. Test missing/weak evidence and temporarily unavailable embedding/LLM states;
   verify `INSUFFICIENT_EVIDENCE` or explicit degraded status.

Step 4C, Step 4D, and Step 5 were not started.
