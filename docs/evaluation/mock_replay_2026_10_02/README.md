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

The saved failure rows are for triage and regression review only. They must not be added to the
training set or used to claim population accuracy, calibrated probabilities, or clinical
sensitivity/specificity.
