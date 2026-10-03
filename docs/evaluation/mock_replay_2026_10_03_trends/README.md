# Measured laboratory trend endpoints — 2026-10-03

This is a synthetic mock regression replay, not model training or clinical validation.
The repeatedly inspected corpus is development evidence, including its nominal validation split.
No frozen inputs, labels, scoring flags or learned model weights were changed. Real LLM calls: 0.

| Metric | Previous | Current |
|---|---:|---:|
| All-case exact final answer | 180/191 (94.24%) | 181/191 (94.76%) |
| Existing scoring_expected subset | 176/178 (98.88%) | 177/178 (99.44%) |
| Critical target exact answer | 89/97 (91.75%) | 90/97 (92.78%) |

One previously wrong final answer improved; no previously correct answer regressed.
100% has NOT been reached. The remaining scored miss concerns obstructive respiratory disease
versus pneumonia. Seven Tier-2 targets remain review-only; two additional non-scoring ambiguous
cases remain misses. Do not force those labels into the runtime solely to satisfy this corpus.

## Implementation

`nova_agent/objective_evidence.py` and its submission mirror now parse a numeric endpoint after
phrases such as "has fallen to" and "rose to". Endpoint numbers retain existing unit conversion,
normal-range interpretation and conflict handling. Direction words alone never establish an
abnormal result. Hypothetical, predicted and historical clauses do not establish measured values.
`tests/test_numeric_result_conflicts.py` adds 12 tests for endpoint units, normal results after a
fall, persistently low results after a rise, missing values, invalid units and conflicts.
The focused evidence suites passed 102 tests before the replay.

## Metrics limitations and next priorities

Binary critical classification (derived from final diagnosis, NOT direct Safety Engine triage):
TP 91, FP 6, FN 6, TN 88. Current Top-3 metric uses the last differential snapshot, whereas Top-1
uses the final answer; these refer to different stages and must not be described as a single
consistent top-k ranking curve. Audit snapshot timing before using top-k figures externally.

Next: resolve API integration verification, assess respiratory discriminating evidence, and
obtain a fresh independently reviewed holdout before making any generalization claim.

## Reproduction

```sh
python scripts/run_large_simulation.py --output /tmp/nova_trend_replay_new --limit-per-family 1 --workers 6
python scripts/summarize_large_simulation.py /tmp/nova_trend_replay_new
```

See completion.json for corpus/runtime hashes. Its commit identifies the parent revision;
the runtime hash identifies the exact uncommitted implementation evaluated. Results and
comparison are saved alongside this report. No model training occurred.

## Final regression result

`python -m pytest -q tests --ignore=tests/test_production_api.py`: **596 passed, 1 skipped**.
The previously documented API TestClient initialization timeout remains unresolved; that file
was explicitly excluded, so this is not a full integration pass. No deployment or merge.
The source and submission objective-evidence modules match, and `git diff --check` passed.
