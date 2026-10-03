# Source-informed safety snapshots — 2026-10-03

## Data and provenance

Added 24 newly authored synthetic snapshots: 12 active danger-sign examples and 12 target-negative
controls (denial, family history, past history, unrelated current symptoms). Sources inform the
signs; they do NOT supply actual patient records or clinically adjudicate these labels.

- NHS stroke: https://www.nhs.uk/conditions/stroke/symptoms/
- NHS anaphylaxis: https://www.nhs.uk/conditions/anaphylaxis/
- NIDDK GI bleeding: https://www.niddk.nih.gov/health-information/digestive-diseases/gastrointestinal-bleeding/symptoms-causes

Development: stroke/GI bleeding, 16 cases. Validation: anaphylaxis, 8 cases, run once after the fix.
The same assistant authored both splits, and negative-control templates are related. This is
NOT independent clinical validation. Labels specify whether a particular SafetyLayer condition
should be flagged; no exact disease, safe discharge or referral correctness is asserted.
A negative target label does not mean the patient has no other medical risk.

Manifest/hash and lexical duplicate/family-overlap audit live in evaluation/safety_challenge_v1.
No exact input duplicates or family overlap across splits. Lexical screening cannot rule out
semantic leakage, and shared scenario structures are explicitly disclosed.

## Finding and fix

Development baseline detected 8/8 active target signals, but wrongly flagged 4/8 controls.
SafetyLayer used the combined current/history evidence bag, so a relative's or past red-flag
phrase could be interpreted as a current symptom. Added an optional context exclusion to
PatientState.all_findings_text and used it solely for symptom-based safety matching. Existing
risk context remains available to the differential engine and dedicated medication/risk rules.
This addresses structured history fields; free-text history extraction is not established by
this snapshot benchmark. No new thresholds, training weights or benchmark labels in runtime.

## Results

| Slice | Target positives detected | Negative controls without target flag |
|---|---:|---:|
| Development before | 8/8 | 4/8 |
| Development after | 8/8 | 8/8 |
| Validation, first post-fix run | 4/4 | 4/4 |

Do not describe this small test's complete pass as 100% medical accuracy.
The frozen 191-dialogue replay remains 181/191 exact answers; dangerous exact answers remain
90/97; observed final critical-case flags remain 84/97, with 32/94 noncritical cases flagged.
There is no measured increase in that replay's dangerous-diagnosis accuracy.

## Files and reproduction

- evaluation/safety_challenge_v1: cases, manifest, source links, leakage audit.
- scripts/evaluate_safety_challenge.py: target-specific flag evaluation; expected labels are
  never passed into patient state or the runtime.
- nova_agent/state.py, nova_agent/safety.py and submission mirrors: provenance separation.
- tests/test_danger_recall.py: history/current-symptom and retained-context regressions.

```sh
python scripts/evaluate_safety_challenge.py --split development --output /tmp/dev.json
python scripts/evaluate_safety_challenge.py --split validation --output /tmp/validation.json
```

Next priority: independently reviewed cases with ambiguous onset, mixed languages, and current
symptoms embedded directly in free text. API TestClient integration remains unverified due to the
previously reproduced initialization hang. No deployment or merge.

Final regression: **612 passed, 1 skipped**, using `python -m pytest -q tests --ignore=tests/test_production_api.py`. The excluded API integration suite remains unverified. Source/submission safety modules match and diff whitespace validation passed.
