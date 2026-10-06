# Evidence parsing follow-up — 2026-10-03

Synthetic mock replay, one case per family. No real LLM calls, independent cases or clinical adjudication.
This corpus has been repeatedly inspected during development, including its nominal validation slice;
its results are regression evidence, not an untouched estimate of generalization.

| Metric | Prior recorded run | Current run |
|---|---:|---:|
| All cases Top-1 | 172/191 (90.05%) | 180/191 (94.24%) |
| Pre-existing scoring_expected subset | 168/178 (94.38%) | 176/178 (98.88%) |
| Critical target exact match | 85/97 (87.63%) | 89/97 (91.75%) |
| Development | 140/156 | 148/156 |
| Nominal validation | 32/35 | 32/35 |

The all-case 97% target is NOT reached. No denominator or expected label was changed.
Binary dangerous-diagnosis classification: TP 90, FP 6, FN 7, TN 88. This is a proxy derived
from the final diagnosis, not a direct measurement of the Safety Engine's triage sensitivity.
Top-3: 94.24%; Top-5: 94.76%. Calibration unavailable.

## Changes and rationale

- `nova_agent/state.py` and submission mirror: split comma-delimited explicit denials while
  preserving leading positive assertions and the existing leading-no/positive-clause behavior.
- `nova_agent/differential.py` and submission mirror: consolidate duplicate alias keys so earlier
  translations are retained; extend feature-local wording for respiratory, abdominal and syncopal signs.
- Reassuring neurological findings require complete literal wording in actual physical examinations;
  family history and partial overlap with an abnormal focal finding cannot provide reassurance.
- `tests/test_evidence_precision.py`: polarity, duplicate-key, current-exam and opposite-finding regressions.
- Proposed unvalidated lab-direction and vital-threshold changes were withdrawn before evaluation.

## Remaining problems and next priority

11 all-case misses remain: seven review-only Tier-2 targets, two scored cases (GI bleeding versus
orthostatic hypotension, obstructive respiratory disease versus pneumonia), and two non-scoring
ambiguous/insufficient-information targets. A forced answer for those targets is not a safe fix.
Next: assess objective evidence provenance and discriminating follow-up coverage using development
cases, then evaluate a newly authored, independently reviewed holdout without further tuning.

## Reproduce

```sh
python scripts/run_large_simulation.py --output /tmp/nova_new_replay --limit-per-family 1 --workers 6
python scripts/summarize_large_simulation.py /tmp/nova_new_replay
```

`completion.json` records exact runtime/corpus hashes. Its runtime_commit is the parent commit;
the runtime hash identifies the uncommitted implementation actually tested. `results.jsonl.gz`
contains all 191 result rows; `summary.json` contains automatic metrics; `scored_subset.json`
uses the unchanged corpus eligibility flags. Frozen input data were not edited.

## Verification and release limitation

- Final implementation: `python -m pytest -q tests --ignore=tests/test_production_api.py`:
  **584 passed, 1 skipped**. See `regression.log`.
- Focused evidence regression: 37 passed (included in the count above).
- Full suite was interrupted at the API TestClient fixture. An isolated first API test also
  timed out after 15 seconds; its stack waits in AnyIO/Starlette TestClient initialization.
  Cause is not established. API integration is **NOT VERIFIED**; do not claim all tests pass.
- Source and submission differential modules are identical; `git diff --check` passed.
- No deployment or merge was performed. Resolve the API test blocker before release.
