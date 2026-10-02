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

Commits `eca566f`, `b53fbb1`, `3b24a6c`, and `ff76e22` refined general multilingual/lay phrasing
aliases while rejecting an over-aggressive final-label safety override; they did not add any
evaluation-case-specific label rule. The provenance-correct replay produced:

| Slice | Result | Change vs previous replay |
|---|---:|---:|
| Frozen-family replay, 191 cases | 146/191 (76.44%) | +6 cases, +3.14 percentage points |
| Critical target in that replay | 83/97 (85.57%) | +4 cases, +4.12 percentage points |
| Development split | 118/156 (75.64%) | prior 112/156 (71.79%) |
| Validation split | 28/35 (80.0%) | unchanged |

The final provenance-correct replay used commit `ff76e22` and still has 14 critical-target misses
and 45 non-matching cases. This is a
development/replay signal, not a 100% claim or clinical performance estimate.

The saved failure rows are for triage and regression review only. They must not be added to the
training set or used to claim population accuracy, calibrated probabilities, or clinical
sensitivity/specificity.
