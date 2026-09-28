# N.O.V.A. Known Limitations

Honest, current limitations — only what actually remains. None are hidden.

> **Round update (commit `b3fdccd`, competition retrieval-recall round):** in competition mode
> (`NOVA_COMPETITION_RETRIEVAL`), the deterministic prior is no longer limited to the 34-diagnosis
> KB alone -- `nova_agent/retrieval_pipeline.py` retrieves and reranks candidates from the full
> 1,280-concept default catalog (34 Tier-1 + 1,246 Tier-2), so the two bullets immediately below now
> apply specifically to the CLOSED-KB / non-competition path. The retriever itself is STILL purely
> lexical (token-overlap + IDF-like weighting over `nova_agent/ontology/search.py`'s index, not an
> embedding model) -- this round materially improved its recall (see README.md section 2.2) but did
> not change that fundamental design choice, and measured recall is still well short of what an
> embedding retriever would likely achieve (chief-complaint-only Recall@50 61.4%, not 90%+).
>
> **Round update (critical-generalization hardening round, FINAL_REASONING_SHA `faa1701`):** Blind
> v12 is now REFERENCE-ONLY (its first-run 64.0%/22.2% figures are historical). This round audited
> (never tuned directly against) v12's 4 critical misses and fixed the identified abstract root
> causes generically. A fresh, untouched **Blind v13** (52 cases) then scored **57.9% diagnostic
> accuracy and a 42.9% critical-miss rate -- materially WORSE than v12**, reported honestly, not
> hidden. Root-cause tracing (read-only, no code changed after the run) found a real,
> **pre-existing** cluster of chief-complaint-routing/matching-stemmer/fallback-tie-break gaps that
> this round's own fixes did not touch and did not cause -- see
> `artifacts/blind_runs/blind_v13_failure_analysis.md` for the full technical detail. **This is the
> single largest known limitation in this release**, more significant than any other line in this
> document, and is the clear top priority for a future round.

## Reasoning / clinical scope
- **Closed-KB (non-competition-retrieval) path is 34 diagnoses** across a bounded set of
  chief-complaint concepts — far from exhaustive. The LLM may introduce diagnoses outside this set,
  but the deterministic prior on this path only covers these 34.
- **Matching is keyword/entropy-based, not an embedding model** (`nova_agent/matching.py`,
  `nova_agent/ontology/search.py`) — deliberate, for determinism/testability/competition submission
  weight, but misses synonym pairs neither stemmed, aliased, nor typical-feature-indexed.
- **Objective-evidence numeric interpretation is scoped** to a defined analyte registry with a
  unit-safety guard (a value in an unexpected unit is not interpreted). Analytes/units outside the
  registry are not numerically interpreted.
- **No pediatrics / obstetrics depth** beyond the covered pelvic/pregnancy cases.

## Evaluation
- All benchmark numbers are on **synthetic** vignettes with a **mock** LLM in CI — not real
  patients, not a live model.
- **Blind v8's first run has not been executed** (needs a runnable Python env); it is frozen and
  will be run exactly once, then reported as-is. No Blind v8 accuracy number exists yet.
- Blind v3/v4/v5/v6 are reference-only.

## Integration & runtime (NOT VERIFIED)
- **No live real-LLM call** has been observed (no GPU/API/secret). The HTTP client, prompt
  construction, and parse/repair/fallback path are only unit/subprocess-tested.
- **Real FHIR / OIDC / SMART** endpoints have never been exercised (no hospital endpoint or
  credentials).
- **Official N.O.V.A. 2026 competition API** is unknown; `competition/schema.py` +
  `adapter.py` are a disclosed placeholder. `Official competition API: NOT VERIFIED`.

## Operations (NOT VERIFIED beyond CI)
- Load/performance verified only at the CI load-smoke defaults; 100/250/500-concurrent-case
  behavior, P50/P95/P99 under sustained load, DB connection scaling, and memory growth over long
  60-turn cases are not systematically measured.
- Backup/restore and image-rollback drills against a real database are not executed.
- A repo-history-wide secret scan and pip/npm dependency-vulnerability scan are recommended but not
  yet wired as dedicated CI steps.

## External validation (NOT VERIFIED — out of software scope)
- **Clinical validation:** none performed.
- **Institutional/hospital security review:** none performed.
- **Regulatory review:** none performed.
- **Real SNUBH integration:** none performed.

These four must remain NOT VERIFIED until externally proven, regardless of software maturity.
