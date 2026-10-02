# Mock replay record: multilingual evidence fix

Date: 2026-10-02 (Asia/Seoul)

This directory records a development-only synthetic/mock replay. It is not a clinical validation
set, does not represent independent patients, and all rows remain `eligible_for_training=false`.
The frozen 50,000-case benchmark was not edited or rescored.

| Slice | Before | After | Notes |
|---|---:|---:|---|
| Frozen-family replay, 191 cases | 135/191 (70.68%) | 140/191 (73.30%) | same one-case-per-family slice |
| Critical target in that replay | 74/97 (76.29%) | 79/97 (81.44%) | exact target match, synthetic labels |
| Post-fix validation family slice | — | 28/35 (80.0%) | critical target 17/20 (85.0%) |

## Follow-up replay after generic high-risk phrasing fix

Commits `eca566f` and `b53fbb1` added only general multilingual/lay phrasing aliases plus a
safety-routing regression fix; they did not add any
evaluation-case-specific label rule. The provenance-correct replay produced:

| Slice | Result | Change vs previous replay |
|---|---:|---:|
| Frozen-family replay, 191 cases | 145/191 (75.92%) | +5 cases, +2.62 percentage points |
| Critical target in that replay | 82/97 (84.54%) | +3 cases, +3.09 percentage points |
| Development split | 117/156 (75.0%) | prior 112/156 (71.79%) |
| Validation split | 28/35 (80.0%) | unchanged |

The final provenance-correct replay used commit `b53fbb1` and still has 15 critical-target misses
and 46 non-matching cases. This is a
development/replay signal, not a 100% claim or clinical performance estimate.

The saved failure rows are for triage and regression review only. They must not be added to the
training set or used to claim population accuracy, calibrated probabilities, or clinical
sensitivity/specificity.
