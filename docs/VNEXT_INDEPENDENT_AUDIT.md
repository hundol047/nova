# vNext Independent Audit — Ontology + Learning + Continual-Learning

Second, independent pass over the vNext work (ontology universe, optional DL ranker, continual
learning). Each finding is judged against the actual code, and states what was **VERIFIED locally**
vs **NOT VERIFIED** here (deferred to CI / a runtime environment). No GitHub Actions were triggered.

Branch: `offline/nova-clinical-learning-disease-expansion`. Base: `07c5eab`.

## Audit matrix

| # | Concern | Finding | Status |
|---|---------|---------|--------|
| 1 | **Disease coverage honest?** | Catalog reports 174 concepts (34 deep + 140 structured + 0 ontology) via `report_disease_coverage.py`; NOT_CURATED discipline; no "all diseases/100%" claim in README/docs. | VERIFIED (local, dependency-free) |
| 2 | **Unknown handling first-class?** | `open_world.py` returns KNOWN / POSSIBLE_UNMAPPED / INSUFFICIENT_INFORMATION / UNKNOWN_PRESENTATION; nonsense → UNKNOWN, tiny query → INSUFFICIENT. | VERIFIED (smoke + CI test) |
| 3 | **LLM dx never coerced?** | `normalize_llm_diagnosis` maps only on ≥0.90 confidence; else UNMAPPED_LLM_DIAGNOSIS with concept=None. | VERIFIED |
| 4 | **ML isolation from core/submission?** | `learning/` imported by none of nova_agent/submission/competition/backend; submission excludes learning + torch; requirements pydantic-only. | VERIFIED (test + grep) |
| 5 | **Safety priority preserved?** | Ranker drops `safety_excluded`, floats critical/red-flag to top band, cannot outrank a critical with a normal. Safety Guard > ML > LLM. | VERIFIED |
| 6 | **No fake probabilities?** | Calibrator returns None until fitted (≥30 samples); ranker emits calibrated_score=None and `calibrated=False` otherwise; OOD suppresses calibration. | VERIFIED |
| 7 | **Training-data leakage?** | `learning/` may not import `evaluation/` (static test); patient-level + temporal splits abort on cross-fold overlap; train.py asserts no forbidden labels + aborts on patient leakage. | VERIFIED (static + unit) |
| 8 | **NOVA prediction never a label?** | Stored separately (`nova_top_concept_id`); FORBIDDEN_LABEL_SOURCES rejected at capture, dataset build, and DB CHECK; pending rows not training-eligible. | VERIFIED |
| 9 | **Privacy / de-identification?** | Capture strips direct identifiers + HMAC-pseudonymizes patient id; features allow-listed; `clinical_learning_cases` has no PHI columns; coverage-gap uses non-reversible fingerprint (raw text never stored). | VERIFIED (unit) |
| 10 | **Capture opt-in?** | `NOVA_LEARNING_ENABLED=false` default; capture raises when disabled. `NOVA_ONLINE_TRAINING` tripwire blocks online training. | VERIFIED |
| 11 | **Versioning / rollback / no self-modify?** | Registry SHADOW→gated-promote(critical_recall≥0.99, no regression)→rollback; single production artifact; never auto-promotes. | VERIFIED (unit) |
| 12 | **Terminology licensing / no network?** | Repo ships terminology-free; providers read local snapshots only, yield nothing if absent; no requests/urllib/httpx/socket in ontology or learning; only code-system URI *identifiers* present. | VERIFIED (grep) |
| 13 | **Core reasoning unchanged?** | vNext is additive; no existing engine module imports ontology/open_world; reasoning code (differential/orchestrator/safety) untouched → Blind v9 remains the current untouched set (no v10 needed). | VERIFIED (grep) |
| 14 | **Submission still runnable?** | submission/nova_agent re-synced byte-identical (pydantic-only). Import/subprocess smoke test needs pydantic. | NOT VERIFIED locally (no pydantic) → CI |
| 15 | **Backend migration 0003 correctness?** | py_compile OK; 3 migrations load; SQL not executed here. | NOT VERIFIED locally (no postgres/psycopg) → CI postgres-integration job |
| 16 | **Ontology CI tests pass?** | `test_ontology_catalog.py` compiles; collection needs pydantic (nova_agent package __init__). | NOT VERIFIED locally → CI |

## Local verification summary

- `py_compile`: all new Python compiles.
- `pytest tests/test_learning_pipeline.py tests/test_learning_eval_isolation.py`: **17 passed**.
- `scripts/report_disease_coverage.py`: 174 concepts, 0 duplicates.
- `scripts/verify_local_release.py`: ontology_catalog_integrity PASS, learning_isolation PASS,
  learning_pipeline_tests PASS (17). pydantic/fastapi/npm/postgres checks NOT AVAILABLE (env).
- Secret scan over new files: clean. TODO/FIXME in new code: none.

## Environment limits (honest)

This environment has no pydantic / fastapi / torch / psycopg / node_modules / network. Therefore:
the full backend + ontology-through-nova_agent test suites, the submission import smoke test, the
Postgres migration, blind v9, and any neural training are **NOT VERIFIED here** and rely on CI /
a proper learning environment. They are marked as such above — never reported as PASS.
