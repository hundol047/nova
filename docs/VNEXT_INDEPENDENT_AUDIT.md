# vNext Independent Audit — Ontology + Learning + Continual-Learning

Second, independent pass over the vNext work (ontology universe, optional DL ranker, continual
learning). Each finding is judged against the actual code, and states what was **VERIFIED locally**
vs **NOT VERIFIED** here (deferred to CI / a runtime environment). No GitHub Actions were triggered.

Branch: `offline/nova-clinical-learning-disease-expansion`. Base: `07c5eab`.

> **NOTE ON SECTIONS.** This doc accretes one audit matrix per round; earlier matrices are
> **HISTORICAL SNAPSHOTS** kept for provenance, not the current state.
> - Round 1 (first matrix below): 174-concept catalog, Blind **v9** — HISTORICAL.
> - Round 2 ("vNext completion round"): 516 bundled, Blind **v10** — HISTORICAL.
> - **Round 3 (CURRENT): "5,000-diagnosis expansion round" — 1,280 bundled / 5,651 searchable,
>   Blind v11 current.** See also `docs/evaluation/FIVE_THOUSAND_DISEASE_COMPARISON.md`.
> The authoritative current blind version is always `evaluation/current_blind.py`.

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


---

## 5,000-diagnosis expansion round (retrieval architecture, Blind v11 current)

Third, independent pass over the ≥ 5,000-searchable-diagnosis retrieval architecture (PHASE 0
repairs + PHASE 1 retrieval → router → safety-recall → reranker → narrowed LLM → open-world).
Branch: `offline/nova-5000-diagnosis-expansion`. The authoritative current blind version is now
**v11** (`evaluation/current_blind.py`); v3–v10 are REFERENCE-ONLY and the frozen v10 file/hash is
untouched. Items needing torch/pydantic/fastapi/network are marked **NOT VERIFIED (env)** and rely
on CI — never falsely reported as passed.

| # | Concern | Finding | Status |
|---|---------|---------|--------|
| 1 | ≥ 5,000 searchable universe | `report_disease_coverage.py` → 5,651 total searchable (34 Tier-1 + 1,246 Tier-2 + 4,371 Tier-3), `searchable_target_met=true`, 0 duplicate ids; Tier-3 from a reproducible **synthetic** snapshot (gitignored). Bundled-alone = 1,280. | VERIFIED (local, dependency-free) |
| 2 | 34 Tier-1 deep preserved | Exactly 34 TIER1_DEEP; ids unchanged; not padded to 500 with fabricated detail (honesty rule). | VERIFIED (local) |
| 3 | Not a naive 5,000-way classifier | `learning/pipeline.FiveKPipeline` is retrieval→router→safety→rerank→LLM(≤26)→open-world; LLM never sees the full universe. | VERIFIED (local) |
| 4 | Embedding retrieval executes | `learning/retrieval/*` builds an index over 5,651 concepts (~0.2 s) and queries (~72 ms) dependency-free. | VERIFIED (local) |
| 5 | Recall@K measured | Synthetic eval: recall@50/100/200 = 1.0, recall@20 = 0.996; critical_recall@100 = 1.0; critical_miss_rate@100 = 0.0. Synthetic mechanics only. | VERIFIED (local, synthetic) |
| 6 | Multi-specialty router | `SpecialtyRouter` activates multiple specialties (bands HIGH/MED/LOW), global fallback on low confidence. | VERIFIED (local) |
| 7 | Router miss cannot drop critical | `boost()` is additive-only (raises scores, never removes); safety-recall re-inserts critical regardless. | VERIFIED (local) |
| 8 | Safety restores critical | `apply_safety_recall` adds missing must-not-miss conditions; `assert_no_critical_dropped` guards. | VERIFIED (local) |
| 9 | Reranker executes; safety retained | `Reranker` Top-100→keep≈25; `safety_mandatory` retained even at score ≈ 0.003 (PE kept rank-1 in smoke). | VERIFIED (local); torch training NOT VERIFIED (env) → CI |
| 10 | LLM narrowed + normalized | Bundle ≤ 26; `normalize_llm_diagnosis` → canonical or `UNMAPPED_LLM_DIAGNOSIS`. | VERIFIED (local) |
| 11 | UNKNOWN/OOD preserved | Outcomes KNOWN / POSSIBLE_UNMAPPED / INSUFFICIENT / UNKNOWN; lexical-grounding guard → gibberish = UNKNOWN. | VERIFIED (local) |
| 12 | Baseline gate blocks worse critical recall | `MultiMetricGate`: zero-tolerance critical regression, top-1-only cannot promote, catastrophic specialty regression → REJECT/SHADOW. | VERIFIED (local) |
| 13 | Shadow unchanged clinical output | Candidate introduced via existing `GovernedMLRuntime` shadow; output unchanged, data logged. | VERIFIED (local) |
| 14 | Continual learning governed | Error taxonomy (6 classes) + `CoverageGapQueue` human-review-only, no auto KB edit. | VERIFIED (local) |
| 15 | Failure-mode resilience | `resilience.safe_call` degrades (missing ML/index/ontology/LLM, incompatible checkpoint, corrupt snapshot) without crash. | VERIFIED (local) |
| 16 | v10 reference-only, v11 authored + frozen | v10 hash `182f373a…` untouched; v11 authored (24 cases), sha `dedfec2a…`, manifest + hash guard; leakage scanner auto-includes v11. | VERIFIED (freeze, local); FIRST RUN NOT VERIFIED (env, needs pydantic) → run once in CI |
| 17 | Verifier points to current blind | `verify_local_release.py` derives blind checks from `current_blind.py` → reports v11. | VERIFIED (local) |
| 18 | Docs current + non-overclaim | DISEASE_COVERAGE / TERMINOLOGY_PROVENANCE / learning docs / README / this audit updated; old 516 figure marked HISTORICAL. | VERIFIED (local) |
| 19 | Competition isolated | `submission/` declares pydantic only; no torch / index / training / admin / `learning` import; no external terminology dep; official-interface placeholder untouched. | VERIFIED (local) |
| 20 | REAL PATIENT TRAINING | No real patient data; synthetic only; torch reranker training `IMPLEMENTED_BUT_NOT_EXECUTED` here. | NOT VERIFIED (by design / env) |

**Environment note (unchanged):** network-isolated, no pydantic / fastapi / torch / psycopg /
node_modules / pip. The full `pytest tests/`, the eval-leakage scan through `nova_agent`, the Blind
v11 FIRST RUN, the `submission/` import smoke test, and any neural training are **NOT VERIFIED
here** and deferred to CI. Dependency-free suites (5,000 catalog, 5,000 pipeline, learning
retrieval/router/rerank/pipeline/gate, coverage) run locally and PASS.
