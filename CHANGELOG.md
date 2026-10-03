# Changelog

## 2026-10-03 — grounded reasoning and fixed-model comparison readiness

- Preserve past/family/social history, medication/allergy text, symptom timing and previous hypotheses in the model summary without presenting history as current symptoms.
- Offer uncompleted legal catalog actions and record short evidence-gap reasons. Ask the model to distinguish primary causes from manifestations without inventing observations.
- Match novel diagnoses by name, ground LLM evidence in quoted observations, count distinct assertions and preserve abstention for unsupported diagnoses or unresolved dangerous alternatives at forced completion.
- Add a label-blind direct/full-information/interactive fixed-model comparison runner, integrity/leakage checks and a research-only 59/50/100 external case split. Unreviewed interactive mappings remain blocked.
- Non-API regression: 699 passed, 1 skipped. Production API tests remain excluded because of the previously observed TestClient hang. Runtime-mutating tests must finish before performance evaluation.
- No fixed-model training or measured live-model accuracy gain. The model endpoint and official API adapter remain unavailable/unverified; preflight reports NOT READY. See `docs/evaluation/reasoning_cycle8/REPORT.md` for measured mock results and remaining work.

## 2026-10-03 — preserve assertion boundaries in evidence matching

- Prevent feature overlap from joining unrelated sentences, semicolons or newline-delimited findings; preserve comma-linked modifiers and decimal numbers.
- Add 13 focused tests. Non-API regression: 685 passed, 1 skipped. Existing production API tests remain excluded because of the previously observed TestClient hang.
- Frozen 400-case synthetic replay remains 385/400 (96.25%), with identical final predictions and safety flags; no clinical accuracy improvement is claimed.
- Preserve the rejected over-splitting experiment and final evaluation artifacts under `docs/evaluation/assertion_cycle7/`.

## 2026-10-03 — first external nine-case replay

- Run the nine previously selected DiagnosisArena research cases through the mock DoctorAgent with gold/options excluded and missing follow-up data kept unknown.
- Complete-label exact match: 0/9; one abstention, eight different labels, zero real LLM calls. This small unsupported-case adapter evaluation is not overall clinical accuracy.
- Preserve inputs, traces, hashes and [limitations/failure analysis](docs/evaluation/external_nine_2026_10_03/REPORT.md). No training or runtime changes.

## 2026-10-03 — external expert-reviewed evidence intake

- Preserve MedXpertQA Text (2,455 rows) and the public DiagnosisArena subset (915 rows), original answer keys, source notices, fixed dataset revisions and SHA-256 manifests.
- Index 9 DiagnosisArena final-label matches for unsupported disease review; complex diagnoses remain intact and NOVA clinician adjudication is pending.
- Add official clinical source links and an offline integrity/coverage audit. No training, runtime change, or accuracy measurement; DiagnosisArena remains research/evaluation-only under its source terms.

## 2026-10-03
- Fix mixed comma-list assertion scope and current-exam reassurance matching.
- Preserve multilingual feature aliases previously overwritten by duplicate dictionary keys.
- Add evidence-semantics regressions and retain reproducible synthetic replay artifacts.
- All-case synthetic mock Top-1: 180/191 (94.24%); 97% all-case target remains unmet.

### Laboratory trend follow-up
- Parse measured trend endpoints with existing unit and numeric conflict guards.
- Reject hypothetical/predicted laboratory clauses as current observations.
- Synthetic mock final-answer accuracy: 181/191 (94.76%); 100% remains unmet.

Safety follow-up: [observed flags and tradeoffs](docs/evaluation/safety_flags_2026_10_03/README.md). Synthetic critical-case final flags: 71/97 to 84/97; exact dangerous target answers unchanged at 90/97. Not clinical sensitivity.

Added 24 source-informed synthetic safety snapshots and fixed historical/family symptoms triggering current safety flags. [Evidence and limitations](docs/evaluation/source_safety_2026_10_03/README.md).

ICD-11 2026 reference registration: [18,375 ordinary categories plus separately classified functioning/extension codes](docs/ontology/ICD11_2026_REFERENCE.md). Offline reference only; diagnostic coverage and accuracy are unchanged.

## 2026-10-03 — specific current signs remain safety-relevant

- Fixed missed bleeding/focal neurological safety flags when language routing misses a tag or a candidate originated only from the safety net. Added scoped speech-deficit aliases.
- Evaluated two 400-input synthetic cohorts before and after: warning misses 22→15 and 19→13, without increasing noncritical warning counts. Exact diagnosis agreement remained 95.75% and 96.75%; no diagnostic-accuracy improvement claimed.
- Rejected broader evidence and cold-sweat alias attempts because they increased warnings on noncritical cases. Regression: 633 passed, 1 skipped; pre-existing API TestClient issue excluded.
- Evidence and limitations: `docs/evaluation/safety_cycle2/RESULTS.md` and `README.md`. No training, clinical validation or deployment.

## 2026-10-03 — current regional imaging evidence

- Recognize lobar/localized lung consolidation as the existing focal-consolidation feature; reuse current-result filtering for objective exam/imaging scoring.
- Paired synthetic cohorts improved 383/400→384/400 and 387/400→388/400, with zero previously correct cases becoming incorrect. Safety warning misses did not increase. These correlated development cases do not establish clinical accuracy.
- Regression: 646 passed, 1 skipped; known API TestClient blocker excluded. Evidence: `docs/evaluation/accuracy_cycle3/REPORT.md`.

## 2026-10-03 — recorded evidence for experimental neural training

- Removed hash-derived per-candidate pseudo-features from neural training. Require recorded evidence/retrieval/prior signals matching inference, strict feature validation and immutable snapshot hash verification.
- Bumped checkpoint schema to sched.v2; old experimental checkpoints must not be reused as if trained on actual signals. Renamed early-stopping evaluation output to validation metrics.
- No clinical dataset or PyTorch execution environment available: no new trained model or accuracy claim. Competition fixed-model weights remain unchanged. See `docs/learning/RECORDED_SIGNALS_READINESS.md`.

## 2026-10-03 — respiratory evidence balance

- Corrected respiratory evidence categories and scoped wording for worsening dyspnea and airspace opacity. Kept nonspecific crackles as typical, not independently confirmatory pneumonia evidence.
- Paired hard synthetic cohorts: 184→185, 188→190, 186→188 of 200 each; no previously correct case regressed across 1,200 inputs. Improvements are five variants of one source family, not independent clinical successes.
- Safety miss counts did not increase; 663 software checks passed, 1 skipped, known API file excluded. Full evidence: `docs/evaluation/respiratory_cycle5/REPORT.md`.

## 2026-10-03 — specific context before final meningitis naming

- Added a final-label context guard and reused scoped aliases; workup candidates and safety flags remain available.
- Replayed 1,200 synthetic inputs: 12 previously wrong meningitis names became unknown, with unchanged target agreement and case-level safety flags. These remain incorrect under the frozen labels; no accuracy gain claimed.
- 672 checks passed, 1 skipped; known API file excluded. Evidence: `docs/evaluation/abstention_cycle6/REPORT.md`.
