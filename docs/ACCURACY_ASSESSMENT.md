# Accuracy assessment and the 99% target

**Real-world diagnostic accuracy remains unknown. The requested 99% clinical target has not
been achieved or verified.** There are 68 rule-supported diagnoses and 1,383 reference-only
candidates, not 1,451 validated diagnostic classes. Reference title lookup and unit-test success
must never be presented as patient diagnostic accuracy.

## Measured improvement

A new, same-author set of 43 potassium text-parsing probes was written and executed before
changing the parser. It exposed unsupported units, decimal commas, scientific notation,
ranges, uncertainty and contradictory repeated values being accepted as reliable numbers.
The baseline passed **20/43 (46.5%)**; the fix passed **43/43 (100%)**. These are deliberately
adversarial parser checks, not patient cases or an estimate of overall diagnostic accuracy.
The probes were used for fixing the code and are development data, not independent validation.

The parser now uses a closed supported-unit grammar, rejects ambiguous ranges and uncertain
values, and requires repeated measurements to agree. Valid supported-unit point values retain
their previous behavior. Existing threshold and unitless-BMP conventions remain unchanged.
Unknown results stay unknown rather than providing confirmatory diagnostic support.
Unrecognized but legitimate narrative formats can also remain unknown under this conservative
grammar; recall on real laboratory reports has not been measured. Additional
integration tests verify that invalid values do not add severe-hyperkalemia support while a
valid positive control still does. Before/after reports are committed as
`evaluation/potassium_before.json` and `evaluation/potassium_after.json`.

The existing threshold's source was rechecked, without changing clinical criteria:
UK Kidney Association, Management of Hyperkalaemia in Adults, October 2023:
https://www.ukkidney.org/sites/default/files/FINAL%20VERSION%20-%20UKKA%20CLINICAL%20PRACTICE%20GUIDELINE%20-%20MANAGEMENT%20OF%20HYPERKALAEMIA%20IN%20ADULTS%20-%20191223.pdf
The closed parser grammar is an engineering safeguard, not a reproduced clinical guideline.

## Diagnostic evaluation

The full 205 scored synthetic/mock regression cases were rerun and all 205 passed; three
additional unscored cases are not added to the accuracy denominator. Their current report is
`evaluation/catalog_results.json`, with immutable snapshots under `evaluation/learning_archive/`.
All 1,873 unit tests, standalone build/source synchronization, adversarial checks and the
existing leakage scan also passed. `evaluation/accuracy_status.json` records the separate
metrics and explicitly leaves clinical accuracy null and the 99% target unverified.
These cases have been reused during development, so success cannot establish clinical
non-inferiority, independent generalization, or 99% performance in real patients.

The selected local model endpoint was checked again and was unavailable; no real model
completion, clinical validation or retraining occurred. The previous official weight-download
network blocker remains unresolved. The result is a deterministic-rule assessment, not a
Qwen model accuracy assessment.

For the 99% target, the missing work is independent adjudicated, representative cases with
positive and near-neighbor negative controls per target condition, a working model endpoint,
and a prespecified prospective evaluation. Aggregate accuracy alone can hide rare-condition
failures and critical misses. The existing external audit's 90% engineering screening threshold
is explicitly not a 99% clinical approval gate, and no flags were relaxed to create a pass.
Do not reuse these development probes or training candidates as an independent final test set.
