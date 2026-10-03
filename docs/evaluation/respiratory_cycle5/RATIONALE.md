# Respiratory evidence revision — 2026-10-03

The latest difficult cohort had 14 target-label mismatches. Twelve were already marked
scoring_expected=False in the frozen corpus; two scoreable errors were variants of the same
multimorbidity source. These flags and labels are NOT changed. In that source, COPD, heart
failure and other causes can overlap; matching its synthetic target is not independent clinical
confirmation or a reason to suppress safety warnings.

Inspection found an evidence-profile imbalance: pneumonia treated crackles as a separate
confirmatory finding, while the asthma/COPD profile omitted cough and dyspnea entirely.
Remove the standalone confirmatory crackles item (retain the typical auscultation feature),
and add cough/dyspnea as ordinary, low-weight features of the existing obstructive-airway profile.
Do not change score weights, thresholds, test labels, or infer that cough alone confirms COPD.
No new disease, trained model or external runtime service is added.

Sources checked:
- NHLBI COPD symptoms: https://www.nhlbi.nih.gov/health/copd/symptoms
- ATS/IDSA 2019 guideline: https://pmc.ncbi.nlm.nih.gov/articles/PMC6812437/
The former documents common symptoms, worsening and comorbid disease; the latter describes
limitations of symptoms/signs alone and the use of imaging in the evidence base. These support
reviewing the heuristic profile, not clinical validation of the specific software weights.

Regression protocol: run identical inputs from all three 400-case cohorts (600 easy + 600 hard),
compare case-by-case correctness and safety flags, then run the complete non-API software suite.
Data are existing synthetic development families, not independent patients or an external holdout.
Each evaluation writes fixed inputs, trajectories and runtime/result hashes. Current engine
weights and all evaluation labels are held fixed during execution. No finetuning or training.

The first attempt (`latest`, `original`, `extra`) lost one correct older-adult pneumonia
variant in each cohort and corrected no target-label error, so it was not accepted.
Inspection found an unrecognized current imaging expression: regional airspace opacity.
The revised attempt (`revised_*`) connects airspace opacity/opacities to the existing infiltrate
feature, with negation checks, rather than restoring strong confirmation from crackles alone.
It also represents worsening dyspnea explicitly with scoped ordinary-language aliases;
stable breathlessness and negated worsening do not satisfy that feature.

Additional imaging background: https://www.merckmanuals.com/professional/pulmonary-disorders/pneumonia/community-acquired-pneumonia
Airspace opacity is supportive imaging evidence in context, not uniquely diagnostic of infection.
The mixed COPD/heart-failure cases require clinical review despite any target-label improvement.
Both positive and negative software checks protect these distinctions. No rule returns a named
benchmark target directly, and neither outcome labels nor scoring flags are edited.
