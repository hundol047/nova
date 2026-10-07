# N.O.V.A. 2026 — current competition status

**Status: PRE-GUIDE CANDIDATE — NOT OFFICIALLY READY.** Maintained page; older reports are historical evidence for the
commit they name. Last regenerated for runtime commit `fd238d7` (see `artifacts/verification/CURRENT_RELEASE.json`).

| Question | Answer |
| --- | --- |
| Fixed preliminary model | `openai/gpt-oss-20b`, revision `4d7ae4984b7db7de8f8457170b3f1a419ee76d52` (constants `EXPECTED_COMPETITION_MODEL/REVISION`). Never fine-tuned, adapted, replaced or bundled. |
| Real fixed-model call ever observed | **NO — NOT VERIFIED.** All results below use the deterministic **mock** model. |
| Official API / schema / `run.py` contract | **NOT VERIFIED / PLACEHOLDER.** Participant guide not available to us. `submission/run.py` is fail-closed by design. |
| One successful case-relevant model call per case (eventual requirement) | Designed for (first turn + diagnosis turn always call; `TransportLLMClient` attributes calls to a case id); **not demonstrable** until the real interface exists. A startup/preflight call never counts. |
| Clinical review of the knowledge base | **None.** Internally authored heuristics; see `nova_agent/knowledge/PROVENANCE.md`. |
| Runtime asset provenance / licence | **Submission clearance BLOCKED**: 75 of 81 inventoried assets are `UNRESOLVED` (details below). |
| Package | `submission/submission.zip` (≈0.7 MB, `run.py` + `requirements.txt` at the root, pydantic only), built from the current tree. |

## 1. What changed in this round (all local, none needs the guide)

1. **SOAP data-loss bug fixed at the root.** `nova_agent/soap.py::classify_answer` now reports `denied` only when *every* clause
   of an answer is a clear denial. Mixed/positive/uncertain answers keep the patient's words:
   `"No insulin. I take metformin."`, `"No penicillin allergy; aspirin causes a rash."`,
   `"아니요, 아스피린 알레르기가 있어요."` are retained verbatim. Covers English/Korean/Japanese/Chinese denials, `but/however/except/and`,
   `; , .`, Korean connectives (`하지만/그러나/-지만/-고/…`), "only/just/except" guards and uncertainty ("not sure", "모르겠어요" is *not* a denial).
   Regression tests: `tests/test_soap_regression.py` (85 cases). The submission copy is produced by `scripts/build_nova_submission.py`
   and `tests/test_safety_regression.py::test_submission_source_sync` fails on drift.
2. **SOAP evidence integrity.** `evaluation/soap_provenance.py` checks that every S/O line is traceable to the encounter log
   (chief complaint, initial vitals, actual ASK answers, actual successful EXAM results), that rejected EXAMs are
   "request rejected (no result)", that no TEST appears, that Assessment has exactly one primary diagnosis with supporting /
   contradictory / missing evidence, and that no drug dose is generated. Adversarial mutation tests prove fabricated facts are detected.
   "Patient education" now shows what was *actually said* (verbatim SAY) or an explicit "Planned:" — never an unperformed explanation.
3. **Closing explanation fixed.** The diagnosis SAY (≤ 30 chars) previously degraded to "I will explain next." for any long name
   ("Acute Coronary Syndrome"); it now uses a short alias ("This may be heart attack.").
4. **Korean evidence bridge.** First-person Korean answers were stored but never reached differential scoring (e.g. "종아리가 붓고 아파요").
   A bounded, negation-aware vocabulary in `multilingual_concepts.py` maps ~100 colloquial phrases to canonical evidence; routing aliases added
   for fainting, allergic reaction and dyspnea wording. Authored by the engineering agent, **not clinician-reviewed**.
5. **Isolated official-transport boundary** `competition/official_transport.py` (no endpoint/schema/header invented): evidence ladder
   `NOT_CONFIGURED → CONFIGURED → CALL_ATTEMPTED → RESPONSE_RECEIVED → MODEL_IDENTITY_VERIFIED → REVISION_VERIFIED`; a stub can never
   leave `RESPONSE_RECEIVED`; `official_case_call_made(case_id)` requires an OFFICIAL response carrying that case id.
6. **Preliminary-only benchmark** and 20 **new synthetic Korean development cases** (`evaluation/preliminary_dev_cases.py`), run through the
   same adapter path as the submission; **TEST is a recorded rule violation**.
7. Tests added: case isolation (A/B/A, interleaved, id reuse, exception/timeout), evaluation-time-learning tripwires (audit-hook: no file
   writes, no sockets, no learning/ML/web modules loaded), EXAM-rejection recovery, patient communication, malformed-output / timeout /
   network failure, model-call policy, Korean, documentation honesty.
8. CI: Python 3.11 **and 3.12** matrix; preliminary tests + benchmark gates; provenance coverage; `offline/**` branches now trigger CI.

## 2. Organizer assumptions (centralised, UNCONFIRMED)

Source: briefing of 2026-10-06 **as transcribed by the team from slide photos**; it conflicts with the public page in places.
Code: `evaluation/preliminary_driver.py::ORGANIZER_ASSUMPTIONS`, `nova_agent/config.py` (`PRELIMINARY_*`), `competition/schema.py`.

| Assumption | Value | Status |
| --- | --- | --- |
| Max interactions per case | 50 (public page says 60) | UNCONFIRMED — re-check with the guide |
| Max time per case | 20 minutes | UNCONFIRMED; enforced with an adaptive guard, not simulated by the benchmark |
| Actions | `SAY`, `EXAM`, `DIAGNOSE`; no `TEST` | UNCONFIRMED |
| SAY length | ≤ 30 characters, one question or explanation | UNCONFIRMED |
| EXAM | one maneuver per request; unsupported wording is rejected, rejection costs no turn | rejection wording/format UNPUBLISHED (heuristic detector); "costs no turn" UNCONFIRMED — the simulator conservatively counts rejections toward the cap |
| Result | one primary diagnosis + S/O/A/P note | field names PLACEHOLDER |
| Model calls per case (8) | **INTERNAL ENGINEERING BUDGET — not an organizer requirement** | team sizing against the briefing's per-session caps (200 calls, 500k in / 100k out tokens) |

Only the interface layer (`competition/`, wire field names, rejection detection, the constants above) should need to change.

## 3. Preliminary-only development benchmark — LOCAL DEVELOPMENT / PRELIMINARY SIMULATION

Mock model, synthetic same-author cases, scripted patient answers keyed by internal question category, **no `TEST`**. Not an official score,
not clinical accuracy, and not comparable with the historical TEST-enabled numbers elsewhere in the repository.
Reproduce: `python scripts/evaluate_preliminary_benchmark.py --gate --output artifacts/preliminary_benchmark/latest.json`
(raw rows: `artifacts/preliminary_benchmark/latest.json`).

| Suite (synthetic dev cases) | Cases | Top-1 | Top-3 | Top-5 | Critical recall (Top-1) | Avg / median interactions |
|---|---|---|---|---|---|---|
| NEW Korean (this round) | 20 | 95.0% | 100.0% | 100.0% | 87.5% (8) | 15.8 / 16 |
| Round M dev (English/KO/JA mix) | 128 | 66.7% | 70.7% | 72.4% | 86.0% (43) | 16.7 / 17 |
| Round J dev | 54 | 84.6% | 86.5% | 86.5% | 95.0% (20) | 16.8 / 17 |
| Round I dev | 20 | 89.5% | 89.5% | 89.5% | 100.0% (8) | 16.4 / 16 |
| Original tuning set | 8 | 75.0% | 100.0% | 100.0% | 66.7% (6) | 16.4 / 17 |
| **All** | 230 | 75.7% | 79.7% | 80.6% | 88.2% (85) | 16.6 / 17 |

All 230 cases (`ALL`): critical miss rate 11.8%; SAY 2572 / EXAM 1242 / rejected EXAM 0 (0 in the default run; see the rejection scenario);
max interactions 22 (cap 50, 0 over); duplicate-action rate 0.000; semantically-duplicate-question rate 0.000;
EXAMs outside any weighed diagnosis's discriminating set 2.4%; premature-diagnosis rate 0.4%;
unresolved critical alternative at diagnosis 1.3% (3 cases, all Round M); SOAP completeness 100.0%;
SOAP information retention 100.0%; SOAP unsupported-information rate 0.0%; explanation SAY before DIAGNOSE 100.0%;
**rule violations 0** (TEST / SAY > 30 chars / multi-question SAY / multi-maneuver EXAM / > 50 interactions / malformed DIAGNOSE); malformed-output rate 0.0%;
model-fallback turns 0 (mock never falls back; timeout/failure behaviour is covered by `tests/test_preliminary_failure_modes.py`).

**Korean (new set, 20 cases) before → after this round's Korean bridge** (same adapter path): Top-1 50% → 95%, Top-3 65% → 100%,
critical Top-1 3/8 → 7/8. The remaining Korean miss (meningitis ranked behind subarachnoid hemorrhage, both critical, truth is Top-2) is left
as is: it is a scoring-weight question I did not tune against my own development cases. Gains on a set I authored are *development evidence
for the bridge*, not a generalisation claim.

Reading the other suites honestly: the existing English development sets were authored with `TEST` evidence in mind, so without TEST their
Top-1 is lower than their historical numbers (e.g. Round M historically ≈ 96% with tests, here ≈ 67% without) — that gap is the cost of the
preliminary rules, not a regression. English suites are **bit-identical before/after this round** (the multilingual code only fires on
non-ASCII text).

**Information collection.** Audit result: no duplicate actions, no semantically duplicated questions, 4% of EXAMs outside the
discriminating set of any diagnosis the agent weighed, ~17 interactions per case (cap 50), core safety history (PMH / medication / allergy) and a
diagnosis + next-step explanation always happen before `DIAGNOSE`. Premature diagnoses and unresolved critical alternatives at diagnosis are
rare (see table). **I did not retune the action policy**: without the real model it cannot be validated, and the safety gates (critical
recall, no unresolved critical alternative) must not regress. This is a gap to revisit once real-model behaviour is observable.

**Model-call efficiency** (`tests/test_model_call_policy.py`, instrumented offline stand-in for a real client; no fixed-model call has been observed):
architecture is deterministic state → local retrieval → compact clinical summary → model reasoning → deterministic validation/safety → action.
Measured on six Korean cases: ≤ 8 model calls/case (**internal engineering budget**, first turn + diagnosis turn + every 4th turn), longest prompt
8.6k characters (≈ 3–4k tokens), ≤ 64k prompt characters per case, active differential ≤ 5 entries; the 1,280-concept catalog is never put in the prompt
(`tests/test_full_catalog_not_in_prompt.py`). Real tokenisation and output length are unmeasured.

**EXAM rejection** (`--exam-rejection`, an *assumed* unsupported set — the organizer's list is unknown): rejected requests are never repeated, add no
evidence, appear in the note as "request rejected (no result)", and the case still ends in one valid DIAGNOSE (16 rejections over 20 Korean cases, no rule violations).

## 4. Case isolation and no evaluation-time learning

* `tests/test_case_isolation.py`: A alone, B alone, A→B, B→A, A→B→A, interleaved A/B on one agent, reused case id, exception during A then B,
  model timeout during A then B — transcripts equal a fresh agent every time. All process-wide caches in `nova_agent` are asserted to be
  zero-argument static knowledge loaders (no argument-keyed cache that could retain patient text).
* `tests/test_no_evaluation_time_learning.py`: an audit-hooked subprocess runs full encounters with **zero file writes and zero socket events**;
  no `learning/backend/production/torch/sklearn/numpy/transformers/requests/…` module is imported or loaded; the ML ranker is off and blocked for
  submissions; no training/online-adaptation entry point exists in `nova_agent/` or `competition/`; the zip contains no learning/training artifacts.

## 5. Disease coverage terminology

**1,280 searchable concepts** = **34 Tier-1 deep clinical profiles** + **1,246 Tier-2 structured concepts** (name/aliases/urgency/ICD-10;
83 of them carry agent-authored, unreviewed `typical_features` and 27 `confirmatory_findings`; the other 1,163 are names/aliases/urgency/ICD-10 only). Tier-3 = **0** in the submission; the "5,000+" figure is a synthetic, test-only snapshot and is not clinically curated.
Use "searchable concepts / candidate coverage / structured concepts / deep clinical profiles"; never "accurately diagnoses N diseases"
(`tests/test_documentation_honesty.py` guards this).

## 6. Runtime asset provenance (never fabricated)

Inventory: `artifacts/compliance_hardening/clinical_asset_inventory.json` (path, SHA-256, source, author, licence, permissions, generation
method/model/prompt, clinician review, status); validator: `python scripts/validate_runtime_provenance.py` (coverage **PASS**, permission **BLOCKED**).
Maintenance: `python scripts/refresh_asset_inventory.py` re-hashes changed bytes **without** touching status/licence fields and adds new files as
`UNRESOLVED` unless their own embedded provenance + the attribution document back a `VERIFIED` record.

| Status (validator vocabulary) | Count | Meaning |
| --- | --- | --- |
| UNRESOLVED | 75 | in the submission; source/licence/authorship not recoverable from the repository — **blocks clearance** |
| NOT_USED_IN_SUBMISSION | 3 | not bundled (EXCLUDE_FROM_SUBMISSION) |
| VERIFIED | 3 | in the submission; source, licence, version and transformation documented and checked against the source text (still not clinically reviewed) |

Status mapping to the requested vocabulary: `VERIFIED` = VERIFIED; `UNRESOLVED` = UNRESOLVED; `NOT_USED_IN_SUBMISSION` = EXCLUDE_FROM_SUBMISSION.
**Blocker, unchanged:** the knowledge-base JSON and the engineering code are internally authored by the implementer/AI agent; no original source,
licence grant, generation record or clinician review can be *recovered from the repository*. I could not legitimately recover, regenerate or replace them
offline, and I did **not** remove them (that would silently gut coverage). A human owner must decide per asset: (a) substantiate team authorship and
generation records, (b) replace with licensed sources and re-run the regression suites, or (c) exclude. No clinician review is claimed anywhere.
This round re-hashed 9 changed assets (their status is unchanged and they are **not re-reviewed**) and added `tier2_mondo_synonyms.json` as VERIFIED from
its own embedded source URL/SHA-256/licence (Mondo, CC BY 4.0, attribution in `docs/compliance/SOURCES_AND_LICENSES.md`).

## 7. Verification of this commit

Executed locally against the committed runtime `fd238d7` (record: `artifacts/verification/local-release-fd238d7-v17.json`, pointer `CURRENT_RELEASE.json`):

| Check | Result |
| --- | --- |
| Full suite, Python 3.13 (`pytest tests`, minus the four FastAPI `test_production_*` files that CI runs in a separate job) | **1288 passed, 1 skipped** (the skip is the pre-existing optional-`torch` test); junit: `artifacts/preliminary_candidate/pytest_runtime.xml` |
| Same suite, Python 3.12 (the briefing's Python) | **1288 passed, 1 skipped** |
| README benchmark numbers vs `evaluation/latest_results.json` (the check that failed in the earlier CI run, never disabled) | match — accuracy figures unchanged; turn statistics refreshed |
| Historical development regressions (held-out, generalization-v2, stress, rounds D/E/G/I/J; mock, competition retrieval) | per-suite accuracy, critical recall and critical miss **identical to the previous record**, no per-case change (`artifacts/preliminary_candidate/regressions.json`) |
| Round M dev (128 cases, with TEST) | Top-1 95.9 %, Top-3 98.4 %, critical 100 % — unchanged, no per-case change |
| Preliminary-only benchmark gates | pass: 0 rule violations, 0 malformed, 0 unsupported SOAP lines, retention 100 % |
| Evaluation-leakage scan | no leakage (807 blind cases vs 136 agent-core files; blind sets stay REFERENCE-ONLY and were not used) |
| Package audit / secret scan | no credentials, no model weights/LoRA, no learning/training/frontend/backend/hospital code; source and `submission/` byte-identical |
| Fresh-directory install + run | clean venv, `pip install -r requirements.txt` (pydantic only), `run.py` fails closed (exit 1, `NOT READY`), one complete Korean preliminary encounter OK (`scripts/smoke_fresh_package.py`) |
| ZIP | `run.py` + `requirements.txt` at the root, UTF-8, ≈ 0.74 MB (< 50 MB), SHA-256 in the v17 record |
| Provenance inventory | coverage PASS (every runtime file inventoried, hashes current); permission **BLOCKED** |

Promotion rule applied: a diagnostic gain would not be accepted with a critical-recall regression; none was needed — critical recall is unchanged on every
historical suite and improved on the new Korean set. Reference-only blind sets were not run and not used for tuning.

## 8. What remains (cannot be done without the organizer / a human)

1. Participant guide: real transport, request/response schema, auth, `run.py` invocation, SAY/EXAM/DIAGNOSE/SOAP wire fields, EXAM rejection format, turn/time semantics.
2. Implement `OfficialTransport._send`, then observe REAL `gpt-oss-20b` behaviour (latency, structured-output reliability, calls per case) and re-validate the call budget and prompt size.
3. Provenance/licence decisions for the 75 unresolved assets; clinician review if any clinical claim is to be made.
4. Fresh, independently authored blind evaluation (the existing blind sets are REFERENCE-ONLY and were not used for tuning).
5. OS-level network isolation (only application-level policy and the audit-hook test are verified).
