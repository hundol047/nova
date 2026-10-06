# Safety flag instrumentation and fixes — 2026-10-03

## Scope

191 synthetic mock dialogues, including 97 labelled critical cases. No real LLM calls, model
training, clinician adjudication or independent clinical validation. The corpus has been repeatedly
inspected during development; it measures regression behavior, not generalization.
The requested 99.99% target is NOT established.

## Separate outcomes

| Metric | Before | After |
|---|---:|---:|
| Exact dangerous target answer | 90/97 (92.78%) | 90/97 (92.78%) |
| Any SafetyLayer flag at final decision, critical cases | 71/97 (73.20%) | 84/97 (86.60%) |
| Critical cases without such a flag | 26 | 13 |
| Noncritical cases with such a flag | 30/94 | 32/94 |
| Specificity of final-flag indicator | 68.09% | 65.96% |
| All-case exact final answer | 181/191 (94.76%) | 181/191 (94.76%) |

A flag can identify a different condition and is not proof of appropriate emergency referral.
An absent flag can coexist with a correct dangerous final answer. These measures must therefore
not be called interchangeable clinical sensitivity measures. More warnings increase both recall
and false positives; the tradeoff is explicitly retained. No previously correct final answer
regressed and no previously flagged critical case lost its flag in this replay.

## Implementation

- `nova_agent/safety.py` and submission mirror share existing feature-local multilingual aliases
  with the differential engine. Negation scrubbing remains active.
- The existing critical potassium/sodium interpretations now feed SafetyLayer independently of
  complaint routing. No clinical cutoffs were added or relaxed. Uncertain, historical, conflicting,
  invalid-specimen and normal readings are tested not to raise this objective-lab flag.
- `evaluation/simulator.py` records actual final flags, first flag turn and per-turn flag conditions.
- `evaluation/safety_metrics.py` and `scripts/summarize_large_simulation.py` report observed flags
  separately from exact diagnosis and dangerous-final-label proxies. Legacy missing telemetry
  is unknown, never silently counted as a negative.
- Regression tests cover both the runtime flags and the evaluation distinction.

## Remaining priority

13 critical cases still have no final SafetyLayer flag. Review unsupported Tier-2 conditions,
missing current evidence and vocabulary coverage without tuning to frozen case labels. Introduce
new independently reviewed safety/negative cases, and measure referral decisions and warning timing
in addition to flag presence. Do not force a disease label or flag every case to reach a target.
API TestClient integration remains unverified due to the previously reproduced initialization
hang. No deployment or merge is included in this work.

## Reproduction and artifacts

Run `python scripts/run_large_simulation.py --output <new-directory> --limit-per-family 1 --workers 6`,
then `python scripts/summarize_large_simulation.py <new-directory>`.
Before/after directories retain runtime/corpus/simulator hashes, metadata, all dialogue result
rows and automatic summaries. Runtime commit metadata identifies the parent commit; the recorded
runtime hash identifies the actual uncommitted code evaluated.

## Verification

- Focused safety regressions: 63 passed.
- All tests excluding the documented blocked API file: **609 passed, 1 skipped**.
- Command: `python -m pytest -q tests --ignore=tests/test_production_api.py`.
- Runtime/submission safety modules are identical; `git diff --check` passed.
- API integration is NOT verified; release gate remains open.
