# Evidence precision corrections — 2026-10-02

Local baseline: `91e76ac`. No new conditions were added. Expansion remains **BLOCKED**.

## Changes

- Interpret qualitative negation and conflicting lab statements conservatively. Separate urine markers so one positive marker does not establish all other markers. Invalid specimens become unknown.
- Bind numbers and units to the named analyte, support K/Na/Hb abbreviations, and reject neighboring analyte values and incompatible units. mg/L no longer matches mg/dL.
- Require current objective findings for confirmatory evidence; family history cannot establish current confirmation. Match all meaningful words for confirmatory phrases and enforce word boundaries.
- Count synonymous lab evidence once, including its score denominator.
- Resolve explicit stable IDs paired with canonical names despite duplicate display names; ambiguous abbreviations remain unresolved.
- Require positive diagnostic support for final diagnosis. Absent symptoms and risk factors alone are insufficient. Unknown keeps unresolved dangerous alternatives in the differential.
- Add referenced appendiceal imaging evidence to the existing appendicitis entry. Interpret explicitly preceding symptoms as prodromes without requiring that technical word. These changes address development-set regressions; no case IDs or expected diagnoses are used in runtime rules.
- Avoid reading the word normal inside an abnormal reference-range phrase as a separate normal result.
- Regenerate the submission package with the same runtime changes.

## Executed results

All diagnosis evaluations below used the deterministic mock provider, not a real LLM or patient cohort.

| Evaluation | Baseline | Candidate | Interpretation |
| --- | ---: | ---: | --- |
| Tuning | 6/8 | 8/8 | Development, not independent |
| Historical held-out | 15/18 | 17/18 | Reference replay; not newly held out |
| Generalization v2 | 18/18 | 18/18 | Used to diagnose development regressions |
| Stress | 8/8 | 8/8 | Reference replay |
| Combined above | 47/52 (90.4%) | 51/52 (98.1%) | Small synthetic suite; not clinical accuracy |
| Critical subset above | 28/29 | 29/29 | Limited to this suite |
| Complete-state synthetic checks | 9/14 | 14/14 | Internally authored; all cases included |
| Complete-state critical subset | 3/4 | 4/4 | Four synthetic cases |
| Complete-state unknown subset | 0/4 | 4/4 | Does not prove general uncertainty detection |
| v11 all cases | 11/24 | 12/24 | Historical hard reference, all cases included |
| v11 named/scored diagnoses | 11/22 | 11/22 | No improvement in named diagnosis accuracy |
| v11 critical subset | 7/15 | 7/15 | Still unacceptable for expansion |
| v11 unknown subset | 0/2 | 1/2 | One unresolved failure remains |

Full software suite: **419 passed, 1 skipped**. Thirty focused evidence-regression tests are included. A preliminary 21-test subset reproduced 16 failures on the baseline. Software tests establish specified behavior, not medical correctness. One dependency deprecation warning remains.

The new 14-case fixture was frozen before its first execution, after the initial fixes. Later generic prodrome and reference-range corrections were made after that first execution. Final results are therefore explicitly **reference replays**, not untouched independent validation. The fixture's SHA-256 is `60dddfd8265bcbf02d5e8063845b55e7966e17a10e6553052ef837c3dce94e2e`. Its runner uses exact canonical output titles for both revisions, supplies complete observations, and forces a final turn; it does not measure autonomous interviewing or investigation. Cases and labels were not changed to improve results.

The original v11 fixtures remain unchanged and were not used to select clinical rules in this pass. Runtime diagnosis normalization was repaired, so scores from the original harness include that corrected identity handling; the complete-state runner uses a separate unchanged exact-title comparator.

## Reproduction and retained evidence

Run from repository root:

```sh
python -m pytest tests/ -q --tb=short
python -m evaluation.benchmark --generalization-v2 --stress
python -m evaluation.blind_benchmark_v11
python scripts/run_precision_holdout.py --repo . --output /tmp/precision-candidate.json
python scripts/run_precision_holdout.py --repo /path/to/91e76ac-checkout --output /tmp/precision-baseline.json
python scripts/check_expansion_gate.py
```

The gate is expected to exit 1. Full baseline/candidate outputs, synthetic per-case results, tests, and gate counts are retained in `precision_2026_10_02/` beside this report.

## Remaining blockers

- All 1,246 additional entries still lack independent clinical review; 1,226 have unverified mappings and 16 have quarantined mappings.
- v11 critical recall remains 7/15. Small-suite improvements cannot justify broad diagnostic claims.
- No real-provider evaluation, clinician-adjudicated patient cohort, confidence calibration, or independent clinical validation was performed.
- Matching and parsing remain heuristic. Unhandled phrasing, temporal context, conflicting numeric specimens, language variation, and domain coverage can still cause errors.
- Source-backed imaging features do not make the whole diagnosis entry clinically verified. The existing evidence level remains internally authored heuristic.

Imaging sources retained on the appendicitis entry:
- https://www.niddk.nih.gov/health-information/digestive-diseases/appendicitis/diagnosis
- https://link.springer.com/article/10.1186/s13017-016-0090-5
