# N.O.V.A. MVP implementation audit

Audit date: 2026-10-02 (Asia/Seoul)

This is a software/reproducibility audit, not a clinical validation report. The repository has no
independent patient test set, clinician-adjudicated result set, or live competition-model result.
All local large-run figures are synthetic mock-dialogue results and must not be presented as
population accuracy or medical performance.

## Competition source and constraints

The technical rules used for this audit are the official N.O.V.A. 2026 pages:

- Rules: https://nova.snubhai.org/rules/
- Evaluation and submission: https://nova.snubhai.org/evaluation/
- FAQ: https://nova.snubhai.org/faq/

The separately stored `제27회 강원특별자치도 대학생 창업경진대회` PDF is a startup-camp
announcement, not the N.O.V.A. Doctor Agent technical rulebook. It is not used as evidence for
the table below.

| Official requirement | Repository evidence | Status / remaining risk |
|---|---|---|
| ASK / EXAM / TEST / DIAGNOSE interaction, at most 60 turns | `nova_agent/orchestrator.py`, `competition/adapter.py`, `tests/` | Implemented and locally tested; official server protocol still not verified |
| Qualifying preliminary model is fixed `openai/gpt-oss-20b`; no fine-tuning | `nova_agent/llm_client.py`, `scripts/preflight_competition.py` | Configuration path exists; no live fixed-model call has been observed |
| At least one case-relevant fixed-model call per case | `scripts/preflight_competition.py`, `submission/run.py` | Submission preflight is NOT READY under the current mock-only environment |
| External data/tools allowed only with publication-compatible license and attributable source | `docs/licenses/`, `docs/ontology/TERMINOLOGY_PROVENANCE.md`, source manifests | Source records exist; each new clinical candidate remains review-gated |
| No external LLM/API call from submitted inference code | `submission/`, secret/source scans, `tests/test_safety_regression.py` | Static/local checks pass; server-side enforcement is outside this repository |
| No private-case leakage, cross-case adaptation, or score extraction | frozen corpus split/group checks; per-case fresh state in `scripts/run_large_simulation.py` | Local harness checks pass; no private evaluation data is present |
| Python, UTF-8, `run.py` + `requirements.txt`, ZIP <= 50 MB | `submission/`, build script, standalone smoke test | Local artifact is 0.24 MB and smoke-tested; official API remains a placeholder |

## Feature classification

| Classification | Current implementation | Evidence / limitation |
|---|---|---|
| ① Implemented | Stateful ASK/EXAM/TEST/DIAGNOSE loop; hard turn limit; deterministic candidate selection; LLM structured-output parsing and fallback | `nova_agent/orchestrator.py`, `action_selector.py`, `llm_client.py`; mock-only full local evidence |
| ① Implemented | Safety validator keeps dangerous candidates, blocks unsafe premature diagnosis, validates action keys, and handles novel dangerous diagnoses | `nova_agent/safety_validator.py`, `resolution.py`; regression coverage in `tests/test_safety_regression.py` |
| ① Implemented | Evidence panels, red-flag panel, ranked differential, confidence bands without uncalibrated percentages, clinician-review-required path | `backend/app/main.py`, `backend/app/nova_schemas.py`, `frontend/src/components/nova/` |
| ① Implemented | Read-only FHIR normalization, provenance/temporality handling, RBAC/OIDC/audit/idempotency controls | `backend/app/services/nova_fhir_mapper.py`, `auth.py`, `audit.py`; real hospital endpoints are not verified |
| ① Implemented | 35,000 distinct offline review labels/candidates are catalogued; expansion is blocked from runtime clinical activation | `research/diagnosis_expansion/`, `docs/ontology/DISEASE_COVERAGE.md`; not 35,000 clinically validated diseases |
| ② Implemented but needs improvement | Korean symptom matching, negation, temporal history, family/past-history separation and objective lab evidence | Matching and state fields exist, but adversarial and high-risk recall errors remain; no clinical-language benchmark |
| ② Implemented but needs improvement | Uncertainty/open-world outcomes and safety recall | `nova_agent/open_world.py`, `safety.py`; calibration is unavailable and synthetic pilot still has named-target abstentions and misses |
| ② Implemented but needs improvement | Synthetic evaluation, failure capture and large-run reproducibility | `evaluation/large_simulation/`, `research/simulation_50000_v1/`; current 1,248-case pilot is not the frozen 50,000-case result |
| ② Implemented but needs improvement | Mobile clinician workspace and evidence explanation | Frontend panels exist; full device/accessibility/usability validation has not been completed |
| ③ Not implemented or not verified | Independent real-patient test set, clinician adjudication, calibrated probabilities, clinical sensitivity/specificity claims | No source data or approved clinical study is available; must remain NOT VERIFIED |
| ③ Not implemented or not verified | Official competition API adapter and live `gpt-oss-20b` submission run | `competition/schema.py` explicitly documents a placeholder; participant guide/server contract is still required |
| ③ Not implemented or not verified | Automated Evidence Dashboard fed by the completed 50,000-case run | Existing validation/observability endpoints are not the requested run-evidence dashboard |
| ④ Competition-essential | Freeze an auditable submission, prove per-case model invocation, verify package size/source manifest, and run the official protocol smoke test | Build and static checks are present; real-provider and official-interface gates remain open |
| ④ Competition-essential | Keep public claims limited to synthetic/mock results and disclose clinical validation status | README and release docs already contain this policy; this audit records the current numbers |
| ⑤ Post-competition | Prospective/retrospective clinical study, institutional security review, real SMART/FHIR integration, calibrated external validation, broad pediatric/obstetric coverage | Explicitly out of the current software-only evidence boundary |

## P0/P1 work completed in this cycle

1. **P0 laboratory assertion safety:** current glucose/lactate extraction now ignores explicitly
   historical, hypothetical, denied, or prior-report clauses; conflicting current values return
   unknown rather than selecting one by order. Unit handling and thresholds were not broadened.
   Tests: `tests/test_glucose_lactate_assertions.py` (23 cases), plus existing unit/severity/safety
   tests.
2. **P1 evaluation protocol integrity:** synthetic patient replies now use explicit canonical test
   aliases and return `Not provided in synthetic case.` for absent data. The adapter never reads a
   ground-truth label and never invents a non-equivalent test result.
3. **P1 same-protocol comparison:** under `mapped_unknown_missing`, the fixed engine improved the
   development pilot from 834/1,248 to 839/1,248 and critical recall from 439/616 to 444/616.
   This is a mock synthetic pilot, not clinical accuracy.

## Frozen 50,000-case evaluation design

`research/simulation_50000_v1/manifest.json` records a deterministic corpus hash. It contains
25,000 construction-labelled low-complexity variants and 25,000 high-complexity variants from 191
source families and 42 diagnostic targets (including unknown). Forty thousand cases are marked
development and 10,000 validation; the development/validation split is grouped by diagnostic
source family to prevent variant-family leakage. These are all synthetic cases with inherited
unverified labels. There is no real TRAIN set and no independent clinical test set in this corpus.

The term “low” describes the corpus construction recipe, not low urgency. Likewise, a correct
result means agreement with an inherited synthetic label, not a confirmed patient diagnosis.
Calibration and population-level uncertainty metrics are intentionally unavailable until suitable
independent data exists.

## Immediate queue

1. Freeze and commit the P0/P1 code plus submission mirror only after the scoped regression suite,
   safety regression, and build smoke pass.
2. Run the full frozen corpus and a separately recorded 10,000-case validation comparison without
   changing runtime code during either run.
3. Extend the result summary with top-3/top-5 recall, critical false negatives, unknown/OOD
   handling, split/source-family leakage checks, and explicit `calibration: NOT AVAILABLE` fields.
4. After the result is frozen, address the highest-frequency failure class with a new, separately
   frozen regression slice; never tune on the validation slice.

