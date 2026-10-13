# v47: patient-specific encounter rebuild

## Status and score evidence

This is an **unscored engineering candidate**, not a claim of full marks.
The owner reported these latest leaderboard scores: information 9.46/25,
reasoning 7.08/15, tests/follow-up 3.79/10, safety 9.75/15,
communication 4.45/15 and efficiency 14.44/20: **48.97/100**.
The preceding reported total was 57.41. We have not established identical
cases, evaluator versions or run conditions, so the 8.44 difference cannot
by itself establish which code change caused each lost point.

The official preliminary contract remains 50 turns, 30 NFC characters per
SAY/EXAM, one question/maneuver at a time, and no TEST execution. Runtime
uses only the supplied SDK for the designated Doctor; it does not hard-code
an old model name. Official docs checked on 2026-10-13 name GPT-6-Luna as the
designated Doctor. Sample, leaderboard and final evaluation are different;
passing synthetic/local tests is not evidence of a leaderboard score.
Sources: https://nova.snubhai.org/rules/ , https://nova.snubhai.org/evaluation/
and https://nova.snubhai.org/docs/ .

## Why rebuild the controller

The old controller could spend many turns in a fixed chronic-complaint and
general-history sequence before asking the Doctor what this patient needed.
Its final plan primarily came from a few catalog profiles and could discard
the Doctor's case-specific treatment and follow-up. A nonspecific weakness
candidate could also terminate a stable interview as an electrolyte emergency.
These are observed code behaviors, not a proven explanation of hidden scores.

`consult()` now uses `AdaptiveEncounter`, retaining the SDK transport,
request replay, deadlines, action accounting, literal observation recording,
vital/glucose safety and engine fallback from `OfficialEncounter`.

| Rubric | Implemented behavior |
| --- | --- |
| Information | Ask the patient's concern, then review actual observations before choosing the next questions and physical maneuvers. Interleave SAY/EXAM. Reassess flagged positive answers, reject duplicate/invalid actions, and close essential medication/allergy/history gaps. |
| Reasoning | Let the designated Doctor compare diagnoses beyond the small profile catalog. Cite actual observation IDs; preserve opposite findings and uncertainty. Do not turn a hypothetical, family history or unknown reply into a confirmed finding. |
| Tests/follow-up | Preserve a supported case-specific plan: indicated test, purpose, timing, abnormal/normal-result next steps, treatment direction, disposition, dated follow-up and return precautions. A deliberately empty test plan does not insert an unrelated panel. |
| Safety | Independent measured danger can override an outpatient plan. A single generic symptom does not automatically activate an urgent diagnostic alternative. Emergency explanation includes transport. New current symptoms reported at closing trigger a bounded reassessment when time permits. |
| Communication | Actually speak the working diagnosis, next steps, warnings, test purpose and treatment; check understanding and invite questions. Timed follow-up, treatment and precautions are drawn from the resolved written plan rather than potentially conflicting model paraphrases. |
| Efficiency | At most five planning batches of up to six actions, normally followed by one final review. Stop when no useful action remains. Cache engine scoring, remove full-history duplication in HPI, reserve 12 closing turns and allow up to 38 clinical actions when needed. No added model call solely for sentence phrasing. |

The source-reference check establishes observation provenance. It does **not**
certify clinical diagnostic accuracy, appropriate test selection or correct
treatment. Those remain material risks requiring actual designated-model and
official evaluation. Prompts are clinical reasoning instructions, not medical
guideline certification. Proposed care stays in P, never fabricated S/O.
New model-written drug doses and direct unsupported dose escalation/cessation
instructions are blocked; this is not a complete prescribing safety validator.

## Second review

The additional pass checked cases that a normal happy-path run misses:

- Initial complaint and supplied vitals must remain eligible observation
  sources; an empty answer field must not discard those non-question sources.
- A model's different spoken diagnosis, treatment or six-month return interval
  must not replace the accepted diagnosis and two-day written follow-up.
- At a short deadline, prioritize disposition and warning signs. A same-day
  visit must not be replaced by a later follow-up interval.
- Rejected/unknown exams must not become normal findings or repeat endlessly.
- A newly reported current symptom at closing must enter the evidence and
  undergo reassessment; a hypothetical future symptom must not.
- A cached outpatient plan must still be overridden by new measured danger.
- Lost responses must retain request replay and submit only once.

## Verification scope

`tests/test_adaptive_encounter.py` directly exercises the production controller
with scripted patients and scripted Doctor responses. Existing selected
regression suites cover retained transport, evidence, safety, history, SOAP,
scope and isolation. Full commands, counts and package evidence are recorded
in `artifacts/releases/nova-v47-publication.json`.

`scripts/compare_encounter_controllers.py` runs the same synthetic lower-urinary
complaint and a compatible scripted Doctor response through old/new controllers.
Observed actions were **34 versus 18**, with **3 Doctor requests each**. The
new controller retained and spoke the supplied two-day follow-up; the old one
replaced it. Both selected a cystitis label. This is one control-flow fixture,
not independent clinical validation, a diagnosis accuracy rate, real cost, or
a projected leaderboard gain. Fixture token counts are constants, not prices.

The archive is checked in a clean environment and via a local HTTP simulation
running the real vendored SDK from an extracted read-only ZIP. That proves
packaging and local transport behavior only. No private evaluation content,
answers, credentials, guidelines corpus or local tests enter the ZIP. Blind
v18 is reference-only and is neither rerun nor tuned. No official submission
or live designated-model evaluation was performed during this change.

## Reproduction

```sh
python -m pytest -q tests/test_adaptive_encounter.py
python scripts/compare_encounter_controllers.py --output comparison.json
python scripts/package_quality_candidate.py --version v47
python scripts/audit_official_package.py artifacts/releases/nova-v47-submission.zip
python scripts/validate_submission_zip.py artifacts/releases/nova-v47-submission.zip
python scripts/smoke_official_http.py artifacts/releases/nova-v47-submission.zip
```

Use the exact dependency versions in `submission/requirements.txt`. The ZIP
manifest contains exact runtime file hashes and makes no official-score claim.
Submit `nova-v47-submission.zip` unchanged to obtain an actual new score; judge
the next revision on all six reported components rather than test counts.
