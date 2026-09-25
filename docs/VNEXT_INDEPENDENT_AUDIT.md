# vNext Independent Audit — Ontology + Learning + Continual-Learning

Second, independent pass over the vNext work (ontology universe, optional DL ranker, continual
learning). Each finding is judged against the actual code, and states what was **VERIFIED locally**
vs **NOT VERIFIED** here (deferred to CI / a runtime environment). No GitHub Actions were triggered.

Branch: `offline/nova-clinical-learning-disease-expansion`. Base: `07c5eab`.

> **NOTE ON SECTIONS.** The first matrix below is a **HISTORICAL SNAPSHOT** of the vNext *first*
> round (174-concept catalog; Blind **v9** current). It is accurate for that round and kept as
> history. The CURRENT state is the **"vNext completion round"** section further down (516 bundled;
> Blind **v10** current) and, for the 5,000-diagnosis work, the FIVE_THOUSAND comparison doc.
> The authoritative current blind version is `evaluation/current_blind.py`.

## Audit matrix — HISTORICAL SNAPSHOT (vNext first round: 174 concepts, Blind v9 current)

| # | Concern | Finding | Status |
|---|---------|---------|--------|
| 1 | **Disease coverage honest?** | Catalog reports 516 bundled concepts (34 deep + 482 structured; Tier-3 via operator snapshot) via `report_disease_coverage.py`; NOT_CURATED discipline; no "all diseases/100%" claim in README/docs. | VERIFIED (local, dependency-free) |
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



---

## vNext completion round (500+ catalog, real training, governed ML, outcome capture)

Independent re-audit after the completion round. Each item is judged against the actual code; items
needing torch/pydantic/fastapi/psycopg/network are marked **NOT VERIFIED (env)** and rely on CI —
never falsely reported as passed.

| # | Concern | Finding | Status |
|---|---------|---------|--------|
| 1 | Bundled disease count ≥ 500 | 516 bundled (34 Tier-1 + 482 Tier-2); `coverage_target_met=true`; 0 dup ids; 33 balanced specialties. | VERIFIED (local) |
| 2 | 34 Tier-1 deep preserved | Exactly 34 TIER1_DEEP concepts, ids unchanged. | VERIFIED (local) |
| 3 | Terminology import functional | `import_terminology.py` validates + writes a provider snapshot; Tier-3 count 0→N with a test snapshot; graceful degrade without. | VERIFIED (local) |
| 4 | Tier-3 not over-curated | Tier-3 concepts are `NOT_CURATED`, retrievable as named possibilities only. | VERIFIED (local) |
| 5 | Real training loop exists | `learning/train.py` has Adam + cross-entropy ranking loss + grad clip + validation + early stop + best-ckpt + metrics; not a placeholder. | VERIFIED code present; torch execution NOT VERIFIED (env) → CI/torch |
| 6 | Checkpoint save/load + fail-safe | `learning/checkpoint.py` compat-guard on feature/schema/arch/input_dim before loading weights; `TorchRanker.load` factory. | VERIFIED (guard logic, local); weight roundtrip NOT VERIFIED (env) |
| 7 | ML integrated into hospital path | `_consult_ml_shadow` hook in backend `decide`; governed runtime shadow/active/fallback. | VERIFIED (control logic, local); backend web tests NOT VERIFIED (env) → CI |
| 8 | Shadow mode never changes output | `GovernedMLRuntime` shadow returns `changed_clinical_output=False`; tests assert it. | VERIFIED (local) |
| 9 | Safety Guard > ML > LLM | `_merge_preserving` never drops a deterministic candidate; OOD keeps deterministic order; Safety applied after ML. | VERIFIED (local) |
| 10 | Outcome capture wired to backend | `close_case` captures on close (opt-in, fail-safe, after durable close); admin endpoints gated by `learning:admin`. | VERIFIED (logic + RBAC, local); backend web tests NOT VERIFIED (env) → CI |
| 11 | NOVA/LLM prediction never a label | Enforced at capture, dataset build, and DB CHECK; tests assert refusal. | VERIFIED (local) |
| 12 | Offline retraining lifecycle | `learning/retrain.py` train→SHADOW / promote(gated+approved) / rollback / status. | VERIFIED (local) |
| 13 | Promotion gated + approved | `promote()` requires non-empty `approved_by` AND critical-recall floor + no regression. | VERIFIED (local) |
| 14 | Rollback works | Restores previous production; tests assert. | VERIFIED (local) |
| 15 | Patient/temporal leakage blocked | Splits abort on overlap; train entrypoint raises `PATIENT LEAKAGE`; tests assert. | VERIFIED (local) |
| 16 | learning/ never reads eval sets | Import + docstring-aware code scan for blind/held-out/generalization. | VERIFIED (local) |
| 17 | Open-world UNKNOWN/OOD preserved | `assess_multi_signal` returns UNKNOWN/INSUFFICIENT; rare fallback before unknown; tests assert. | VERIFIED (local) |
| 18 | Competition isolated | submission requires pydantic only; no torch/learning import; no external terminology call. | VERIFIED (local) |
| 19 | Blind discipline | v3–v9 REFERENCE-ONLY; v10 authored + frozen (hash guard) + in leakage BLIND_MODULES. | VERIFIED (freeze, local); FIRST RUN NOT VERIFIED (env) → run once |
| 20 | REAL PATIENT TRAINING | No real patient data; synthetic only. | NOT VERIFIED (by design) |

**Environment note:** this authoring environment is network-isolated with no pydantic / fastapi /
torch / psycopg / node_modules and no pip. All items marked NOT VERIFIED (env) are deferred to CI or
a torch/hospital environment and are never reported as passed here. Dependency-free suites (ontology,
coverage-500, terminology import, ML runtime, training-loop mechanics, retraining lifecycle,
continual validation, open-world, admin RBAC) run locally and PASS.
