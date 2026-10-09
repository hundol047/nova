# N.O.V.A. 2026 — current competition status

**PRE-GUIDE CANDIDATE — ROUND U: TARGETED REPAIR — STRICT REGRESSION FAIL — NOT OFFICIALLY READY.**

Executed local runtime: `da7cfca7eb80f09af82019326f9964a285946f1d`.
Execution baseline: `761fcda7f4f5b6c58b0e0b6e8b77047b37301782` (Round T).
Original Claude branch, main and original user checkout were preserved.

- Implemented prompt: [ROUND_U_IMPLEMENTATION_PROMPT_KO.md](competition/ROUND_U_IMPLEMENTATION_PROMPT_KO.md).
- Results and limitations: [ROUND_U_REPAIR_REPORT_KO.md](competition/ROUND_U_REPAIR_REPORT_KO.md).
- Remaining work: [ROUND_U_FOLLOWUP_KO.md](competition/ROUND_U_FOLLOWUP_KO.md).
- Public/source evidence scope: [ROUND_U_SOURCE_REVIEW_NOTICE.md](competition/ROUND_U_SOURCE_REVIEW_NOTICE.md).

All performance figures are **offline mock / implementation-aware synthetic engineering evidence**, not official, real-model or independent clinical scores.
Configured model identity remains `openai/gpt-oss-20b`, revision `4d7ae4984b7db7de8f8457170b3f1a419ee76d52`; actual model and official interface **NOT VERIFIED**.

Round U repairs relation qualifiers, subjective vs objective rhythm wording, unconfirmed assertions, compositional observation normalization,
EXAM-driven candidate re-entry, diagnostic Top25 vs separate safety watch, and thin-evidence naming/disposition paths.
Full local tests: **2,425 passed / 0 failed / 1 skipped / 0 deselected**. One initial package skip was completed separately after the audited ZIP was available; it is not double-counted. Torch training remains unexecuted; no model download or training was performed.

| Same-condition evaluation | Round T → U | Critical after |
|---|---:|---:|
| Preliminary development (230 total / 222 scored) | 209→209/222 | 85/85 |
| Round P development | 26→27/32 | 11/13 |
| Round M with TEST | 114→115/123 | 43/43 |
| Round M long-tail | Top1 17→18/26; Top5 21→21/26 | Existing flags unchanged |
| Round J with TEST | 51→51/54 | 20/20 |
| Last fresh Closing U8 (8 total / 4 scored) | 4→4/4; behavior 25→26/26 | 2/2 |

Preliminary new correct: RoundI_enzyme_sparse. New wrong: RoundM_066 (single diarrhea observation → undifferentiated, scored as wrong).
No new critical diagnostic miss in the completed paired suites, but existing critical misses/overnaming remain; overall acceptance is not PASS.
Preliminary average interactions 19.95→20.33 and unnecessary exams 319→371: efficiency worsened.
Chief-only proxy Top150 117→118/164 and diagnostic Top25 103→117/164. Initial retrieval remains weak.
M terminal Top150 116→117/123, diagnostic Top25 100→114/123, active 123/123. Long-tail-only terminal Top25 falls 25→24/26; RoundM_106 stays active/correct.

T postfreeze, U20, U12 and U10 are development after result-informed repairs. Closing U8 was frozen before first execution on the final runtime;
no runtime changes followed. Its author saw implementation/failures. This small control set is not broad generalization or independent clinical validation.

No new clinical profiles were added. Catalog remains 34 Tier-1 + 1,246 Tier-2 = 1,280. Existing enrichment entries: 83; Tier-2 without an entry: 1,163.
Neither the entry count nor ontology coverage certifies clinical depth. Provenance coverage PASS; permission status remains BLOCKED.

Local v26 ZIP integrity, 100-file runtime/launcher/requirements byte binding and isolated mock PASS.
ZIP SHA256: `b5c2c704c9463b9f12d941cf97e1997986faf245daa7d604ff2ddc1fffb39369` (830,977 bytes).
Source review branch: `codex/nova-round-u-source-review-20261009`; exact public commit parity is recorded in the linked notice.
Detailed local traces/XML and the local ZIP are not part of the source-only publication. The public CURRENT_RELEASE.json remains historical;
it does not certify the current source branch. Local executed SHA, public byte-equivalent source and official readiness are distinct claims.

No external LLM call, API-key request, model download/replacement/training, blind v18/v19 run/tuning or new blind creation.
Historical sections below describe only their named runtimes. The previous Round T report remains preserved.

## 1. Backend load check (production-backend CI step) — fixed

Command unchanged: `python scripts/load_smoke_backend.py --cases 100 --concurrency 10 --max-p95-ms 3000`.
Evidence: `artifacts/backend_load/before_after.json`.

| Run | p95 | Throughput | Errors | Verdict |
| --- | --- | --- | --- | --- |
| CI 37564554756, 8d37c73 (GitHub runner) | 4,680 ms | 2.2 cases/s | 0/100 | FAIL |
| local, 8d37c73 | 7,590 ms | 1.4 cases/s | 0/100 | FAIL |
| local, merged line before the fix | 17,846 ms | 0.62 cases/s | 0/100 | FAIL |
| local, `8efd5d3` (3 runs) | 2,324 / 2,498 / 2,326 ms | 4.4–4.7 cases/s | 0/100 | PASS |

This container measured the same baseline about 1.6× slower than the GitHub runner. Startup (lifespan and knowledge warm-up,
0.25–0.36 s) is reported separately from steady-state latency. Root cause (cProfile): 80% of a decision was pure string
normalisation repeated inside `matching.feature_present_with_aliases`, called once per (disease, phrase, alias, finding), with
1.5 M `_stem`, 254 k negation-scrub and 1.67 M `re._compile` calls. The fixes:
- A decision-scoped memo (ContextVar, discarded after each decision, private to the calling thread, so no patient data crosses cases).
- Regex-free boundary scans, property-tested equal to the regexes they replace.
- A sparse query dot product in `learning/retrieval/index.py` (identical scores).
- A synthetic, patient-free warm-up of the immutable caches at backend startup.

Decisions are unchanged: `tests/test_matching_performance_equivalence.py` compares transcripts with and without the memo, and every
development suite is unchanged case by case. The threshold, case count and concurrency were **not** changed.

## 2. Preliminary diagnostic performance — LOCAL DEVELOPMENT / PRELIMINARY SIMULATION (mock, not an official score)

**Previous (Round Q, runtime `8257ba6`, competition retrieval, mock, all 230 cases, FROZEN simulator; `artifacts/round_q/final/`).**
Top-1 **202/222**, critical **85/85**, avg / max interactions 19.65 / 35, unnecessary exams 297, semantic duplicate questions 11, 0 rule
violations, 0 unsupported SOAP lines. Versus `ead1595` (215/222, 84/85): 1 better (RoundJ_25), 14 worse (non-critical). 12 of the 14 come
from grounding bare answers while the frozen simulator answers every unscripted question "No" (all 12 are correct again with the separate
`--unscripted-unknown` evaluation-tool variant, where the run scores 213/222, 84/85); RoundM_024 was previously right only through the false
"irregularly irregular" match; RoundM_095 now ends undifferentiated. Unscored sparse cases: dangerous diagnosis named 7 -> 0. TEST-enabled
competition regressions and legacy suites: no case worse. Same legacy suites in competition mode WITH TEST: 2 critical regressions
(RoundM_096, ValO_11) from the same simulator-default cause -- unresolved, see the Round Q report. Round P set (now development data):
24/32 -> 28/32, critical 9/13 -> 11/13. All development/regression numbers, not official or clinical performance.

**Previous (Round P, runtime `3831555`, competition retrieval, mock, all 230 cases; `artifacts/round_p/final/prelim.json`).**
Baseline `10e7de7` reproduced first (204/222, critical 80/85). Details, causes, ablations and the frozen Round P validation set are in
`docs/competition/ROUND_P_ALGORITHM_REPORT.md`.

| Suite | Cases (scored) | Top-1 | Critical Top-1 | Avg interactions |
|---|---|---|---|---|
| NEW Korean set | 20 (20) | 20/20 | 8/8 | 19.7 |
| Round M dev | 128 (123) | 120/123 | 43/43 | 21.7 |
| Round J dev | 54 (52) | 49/52 | 19/20 | 19.7 |
| Round I dev | 20 (19) | 18/19 | 8/8 | 21.0 |
| Original tuning set | 8 (8) | 8/8 | 6/6 | 25.8 |
| **All** | 230 (222) | **215/222 (96.8%)** | **84/85** | 21.1 (max 40) |

0 rule violations, 0 TEST, 0 malformed outputs, 0 unsupported SOAP lines, 100% information retention. Versus baseline: 11 cases
better, 0 worse. Frozen Round P validation set (34 synthetic cases, single author, not independent): Top-1 23/32 → 24/32,
critical 8/13 → 9/13. All of these are development/regression numbers, not unseen-blind or official performance.

**Historical table below (integration pass at `8efd5d3`); kept as evidence for that commit only.**

**Metric definitions.**
- **Top-1** is final *primary-diagnosis* accuracy: the submitted primary diagnosis, or its internal key, matches the case label via `same_diagnosis()`.
- **Top-3/5** count the label inside the first 3/5 entries of the final validated differential.
- The denominator is scored cases (`scoring_expected=True`).
- **Critical recall** is Top-1 over scored cases whose label is a critical condition.

TEST is a rule violation. Scripted patients answer by internal question key.

**Why PR #16 said 89.4% and the last offline report said 75.7%.** The two runs used different retrieval modes, not different
scoring. PR #16 measured Round M only (123 scored) with `NOVA_COMPETITION_RETRIEVAL=1`, the mode the submission uses: the
`competition` provider turns it on. The offline report measured all 230 cases with the legacy/hospital retrieval path, which was the
unset default. On the same merged code before this pass's evidence fixes, both evaluators reproduce 89.4% on Round M in competition
mode (`scripts/evaluate_preliminary_rules.py` and `scripts/evaluate_preliminary_benchmark.py` agree). The table below is competition
mode; the legacy column is shown for completeness.

| Suite | Cases (scored) | Top-1 | Top-3 | Top-5 | Critical Top-1 | Avg / median interactions | Legacy-retrieval Top-1 |
|---|---|---|---|---|---|---|---|
| NEW Korean set | 20 (20) | 95.0% | 100.0% | 100.0% | 87.5% of 8 | 18.1 / 18 | 95.0% |
| Round M dev | 128 (123) | 91.1% | 95.9% | 95.9% | 90.7% of 43 | 20.1 / 21 | 70.7% |
| Round J dev | 54 (52) | 88.5% | 92.3% | 92.3% | 95.0% of 20 | 19.7 / 22 | 84.6% |
| Round I dev | 20 (19) | 94.7% | 94.7% | 94.7% | 100.0% of 8 | 19.2 / 22 | 89.5% |
| Original tuning set | 8 (8) | 100.0% | 100.0% | 100.0% | 100.0% of 6 | 23.1 / 23 | 100.0% |
| **All** | 230 (222) | 91.4% | 95.5% | 95.5% | 92.9% of 85 | 19.9 / 21 | 78.8% |

**Change in this pass (same code base, competition mode, all 230 cases):** Top-1 89.6% → **91.4%**, critical Top-1
75/85 → **79/85 (92.9%)**, **0 cases worse**, 4 better (RoundM_062 ACS, RoundM_072 DKA,
RoundI_urinary_systemic sepsis, AlteredMentalStatus01 DKA). The integration evaluator on Round M moves from 89.4% to 91.1% and critical recall
from 86.0% to 90.7%. In legacy mode, 0 cases got worse and 3 got better. The TEST-enabled development suites (held-out, generalization-v2, stress, rounds D/E/G/I/J)
and Round M with TEST (Top-1 96.7%, critical 97.7%) are **unchanged case by case**. Every rule/safety gate holds: 0 rule violations, 0 TEST,
0 SAY > 30 characters, 0 malformed outputs, 0 unsupported SOAP lines, 100% information retention, an explanation before every DIAGNOSE,
and a maximum of 41 interactions (cap 50).

**Generic fixes, motivated by the error analysis.** No case ids, labels or test sentences are used, and nothing was added to the
runtime retrieval data from evaluation answers. These are lexicon/rule changes informed by *development* cases, so they are
development evidence, not proof of generalisation:
1. **Assertion interpretation.** A drug the patient stopped, ran out of or skipped is not *current use* ("ran out of insulin" no
   longer supports "insulin use"; it supports "missed insulin doses").
2. **Objective evidence.** A descriptive `Tachycardia` (HR 101–119) and `Fever` (38.0–38.9 °C) below the existing red-flag
   thresholds. Before this, HR 118 contributed nothing.
3. **Language interpretation.** Plain wording for an operation or bed-bound state (VTE context), exertional chest symptoms,
   "thirsty", confusion/sleepiness, and "pain on urinating" (routing plus infection-source alias).
4. **Isolation.** The repository-level `learning/` catalog retriever never runs under the preliminary rules.

**Stage attribution of the remaining 19 wrong scored cases** (`scripts/analyze_preliminary_failures.py`; a heuristic engineering
attribution, not clinical adjudication): {'ranking:outscored': 9, 'rerank': 5, 'retrieval': 5}. No premature-diagnosis flags. Final-name normalisation failures: 0.
Several "outscored" misses are hierarchy pairs (appendicitis vs acute abdomen, SVT vs cardiac arrhythmia, epididymo-orchitis vs
epididymitis, duodenal ulcer vs peptic ulcer disease). They are still scored as wrong.

| Language | Scored | Top-1 | Critical Top-1 |
|---|---|---|---|
| en | 188 | 90.4% | 68/73 |
| ja/zh | 7 | 100.0% | 1/1 |
| ko | 27 | 96.3% | 10/11 |

| Wrong case | Label | Submitted | Stage | Label rank | Critical |
|---|---|---|---|---|---|
| PrelimKo_Fever_Meningitis | meningitis | 지주막하출혈 (Subarachnoid Hemorrhage) | ranking:outscored | 2 | yes |
| RoundM_018 | pulmonary_embolism | Hypertrophic Cardiomyopathy | rerank | 10 | yes |
| RoundM_026 | cardiac_arrhythmia | Severe Electrolyte Disorder (e.g. Hyperkalemia/Hyponatremia) | ranking:outscored | 3 |  |
| RoundM_041 | severe_electrolyte_disorder | Syndrome of Inappropriate ADH | rerank | 7 | yes |
| RoundM_046 | acute_abdomen | Acute Appendicitis | ranking:outscored | 2 | yes |
| RoundM_054 | severe_electrolyte_disorder | Adrenal Crisis | retrieval | None | yes |
| RoundM_064 | cardiac_arrhythmia | Pheochromocytoma | ranking:outscored | 2 |  |
| RoundM_069 | acute_pancreatitis | Duodenal Ulcer | rerank | 9 |  |
| RoundM_070 | cardiac_arrhythmia | Optic Neuritis | rerank | 13 |  |
| RoundM_105 | Ovarian Torsion | Ectopic Pregnancy | ranking:outscored | 3 |  |
| RoundM_108 | Peptic Ulcer Disease | Duodenal Ulcer | ranking:outscored | 2 |  |
| RoundM_112 | Epididymitis | Epididymo-Orchitis | ranking:outscored | 2 |  |
| RoundJ_05 | cardiac_arrhythmia | Supraventricular Tachycardia | ranking:outscored | 2 |  |
| RoundJ_25 | acute_abdomen | Acute Appendicitis | ranking:outscored | 3 | yes |
| RoundJ_49 | Peripheral Arterial Disease | Acute Abdomen (Surgical Abdomen) | retrieval | None |  |
| RoundJ_50 | Premature Ventricular Contractions | Acute Abdomen (Surgical Abdomen) | retrieval | None |  |
| RoundJ_51 | Meniere Disease | Ectopic Pregnancy | retrieval | None |  |
| RoundJ_52 | Acute Pericarditis | Acute Coronary Syndrome | rerank | 24 |  |
| RoundI_long_tail | Sjogren syndrome | Stevens-Johnson Syndrome | retrieval | None |  |

The remaining critical misses are left as they are and documented here:
- **RoundM_018 (PE).** Risk context and tachycardia now count, but post-operative dyspnoea with hypoxia still ranks PE 16th, below
  cardiomyopathies. PE's knowledge-base features carry no hypoxia, and a weight change could not be validated without a real model.
- Two electrolyte cases (retrieval and rerank).
- Meningitis vs SAH. Both are critical, and the label is rank 2.
- Two acute-abdomen hierarchy cases.

By-symptom-group results are in `artifacts/preliminary_benchmark/failure_analysis.json`. SOAP records the uncertainty: a
*Missing discriminating evidence* line, a *Contradictory findings* line, and further tests in Plan. No test is ever reported as performed.

## 3. Official interface — blocked (nothing guessed)

Checked:
- The repository and its documentation contain no participant guide, example or connection settings.
- The environment has no `NOVA_COMPETITION_*` or `NOVA_LLM_*` settings.
- nova.snubhai.org is blocked by this environment's network egress.

The submission therefore stays fail-closed, and no stub result is reported as official success.
`competition/official_transport.py` is the single integration point (an evidence ladder from NOT_CONFIGURED to REVISION_VERIFIED;
a stub can never reach the identity states).

**Needed to finish:**
1. The participant guide: the `run.py` invocation (CLI, stdin/stdout or HTTP callback).
2. The observation JSON schema: the first statement with name/age/sex, the vitals field and the turn counter.
3. The action JSON schema for SAY, EXAM and DIAGNOSE, including the SOAP and primary-diagnosis field names.
4. The EXAM rejection format and whether a rejection costs a turn.
5. The time-limit semantics.
6. The model endpoint URL, route and request/response schema for `openai/gpt-oss-20b`, and how the revision is attested.
7. Credentials and how they are delivered: the token format, the header name, and the environment-variable names the organizer will set.
   Secrets must never enter Git or logs.
8. Session caps: calls and tokens per session or case.
9. An official example case and its expected output, to use as a contract test.

## 4. Provenance / licence

See `docs/compliance/PROVENANCE_STATUS.md` (record level; generated by `scripts/report_provenance_status.py`).

**80 assets are UNRESOLVED:**
- 44 engine code files,
- 13 clinical data/rule files (the Tier-1 disease KB, red flags, guidelines, test notes, Tier-2 catalog and enrichment),
- ontology and i18n code.

**3 are VERIFIED from their embedded source terms:** MedlinePlus/Orphanet references, Disease Ontology CC0 synonyms, and Mondo CC BY 4.0
synonyms. **3 ontology snapshots are not shipped.**

The repository has **no LICENSE file**. The core knowledge base cannot be excluded without disabling diagnosis and safety, and it
cannot be legitimately cleared by an engineering agent. The owner has to decide: substantiate team authorship and add a licence,
re-derive the entries from licensed references and re-run the suites, or exclude them.

This pass's own edits are logged in `docs/compliance/LLM_GENERATION_LOG.md`.

## 5. Verification of this commit

The test counts, ZIP hash and clean-room result are recorded in the v22 record named by `CURRENT_RELEASE.json`. Commands:
`pytest tests`, `pytest backend/tests`, `scripts/load_smoke_backend.py`, `scripts/evaluate_preliminary_benchmark.py --gate`,
`scripts/validate_runtime_provenance.py`, `scripts/refresh_runtime_inventory.py --check`, `scripts/check_eval_leakage.py`,
`scripts/build_nova_submission.py`, `scripts/validate_submission_zip.py`, `scripts/smoke_fresh_package.py`.

## 6. Organizer assumptions (UNCONFIRMED; centralised in `evaluation/preliminary_driver.py::ORGANIZER_ASSUMPTIONS` and `nova_agent/config.py`)

| Assumption | Value | Status |
| --- | --- | --- |
| Interactions per case | 50 (the public page says 60) | UNCONFIRMED |
| Time per case | 20 minutes | UNCONFIRMED |
| Actions | SAY, EXAM, DIAGNOSE; no TEST | UNCONFIRMED |
| SAY | ≤ 30 characters, one question | UNCONFIRMED |
| EXAM | one maneuver; rejection costs no turn | UNCONFIRMED (the simulator counts rejections conservatively) |
| Model calls per case: 8 | **INTERNAL ENGINEERING BUDGET — not an organizer requirement** | team sizing |

Disease coverage: **1,280 searchable concepts** = **34 Tier-1 deep clinical profiles** + **1,246 Tier-2 structured concepts**
(83 with partial, unreviewed features). Tier-3 is 0 in the submission. This means candidate coverage, never "accurately diagnoses N diseases".
