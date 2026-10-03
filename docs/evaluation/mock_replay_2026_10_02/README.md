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

## Follow-up 2: feature-local multilingual aliases

Added only feature-local aliases for high-value phrases such as Chinese point tenderness,
palpation-reproduced pain, vasovagal prodrome, brief syncope, and rapid recovery. No diagnosis
label or frozen case was hardcoded. On the same 191-case replay this changed only two previously
unknown benign outputs to their matching diagnoses and produced no observed regressions:

| Slice | Result | Change vs alias-only baseline |
|---|---:|---:|
| Frozen-family replay, 191 cases | 148/191 (77.49%) | +2 cases |
| Critical target in that replay | 83/97 (85.57%) | unchanged |
| Development split | 120/156 (76.92%) | +2 cases |
| Validation split | 28/35 (80.0%) | unchanged |

This remains a synthetic/mock replay and is not clinical accuracy. The change is retained only
because the full slice showed no regression and the targeted multilingual tests passed.

## Follow-up 3: polarity scope and discriminating-workup fixes

The next pass fixed two general pipeline issues found in the failure audit: mixed comma-lists no
longer let a leading `no` erase later positive symptoms, and high-specificity workup evidence was
made reachable through the legal exam catalog. The pass also added objective-only evidence for
appendicitis, pancreatitis, arrhythmia, and chest-wall pain, plus multilingual routing aliases.
No frozen case or expected label was added to the implementation.

| Slice | Result | Change vs follow-up 2 |
|---|---:|---:|
| Frozen-family replay, 191 cases | **172/191 (90.05%)** | +24 cases vs the original 148/191 baseline |
| Development split | 140/156 (89.74%) | +20 cases |
| Validation split | **32/35 (91.43%)** | +4 cases |
| Critical target | 85/97 (87.63%) | unchanged from follow-up 2 |
| Top-3 / Top-5 recall | 93.19% / 94.24% | descriptive replay metrics |

The 90.05% figure is a synthetic one-case-per-family mock replay, not clinical accuracy. The
validation slice contains 32/32 correct among rows marked `scoring_expected=true`; the remaining
validation misses are Tier-2/non-scoring or deliberately insufficient-information cases.

The saved failure rows are for triage and regression review only. They must not be added to the
training set or used to claim population accuracy, calibrated probabilities, or clinical
sensitivity/specificity.
