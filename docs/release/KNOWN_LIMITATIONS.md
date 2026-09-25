# N.O.V.A. Known Limitations

Honest, current limitations — only what actually remains. None are hidden.

## Reasoning / clinical scope
- **Knowledge base is 34 diagnoses** across a bounded set of chief-complaint concepts — far from
  exhaustive. The LLM may introduce diagnoses outside this set, but the deterministic prior only
  covers these 34.
- **Matching is keyword/entropy-based, not an embedding model** (`nova_agent/matching.py`) —
  deliberate, for determinism/testability, but misses synonym pairs neither stemmed nor
  keyword-matched.
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
