# Blind v13 first-run failure analysis

Recorded once, immediately after the single, frozen first run of `evaluation.blind_benchmark_v13`
(raw output: `blind_v13_first_run_output.txt` in this directory). This is read-only, post-hoc
analysis of the untouched result -- **no reasoning/retrieval code was modified in response to
these findings.** `evaluation/blind_cases_v13.py` was not edited after the run.

## Headline result

52 cases, 38 scored (14 long-tail/OOD cases correctly excluded from the accuracy denominator).

- Scored diagnostic accuracy: **57.9%** (vs Blind v12's 64.0%)
- Critical diagnosis recall: **57.1%** (vs Blind v12's 77.8%)
- Critical miss rate: **42.9%** (vs Blind v12's 22.2%)
- Unsupported-case success rate (safe handling of long-tail/OOD cases): 100.0%
- Duplicate action rate: 0.00/case; malformed output rate: 0.0%

**This is materially worse than Blind v12, not better.** Reported honestly, as-is, per this
round's discipline: the point of a blind set is to measure the actual current code, not to be
tuned until it looks good.

## Root-cause categorization (using evaluation/failure_analysis.py's classify_miss(), applied
read-only to the 16 scored misses)

| Root-cause tag | Count (of 16 scored misses) |
|---|---|
| `wrong_chief_complaint_classification` | 9 |
| `missing_differential` | 8 |
| `unnecessary_workup` | 7 |
| `missing_dangerous_diagnosis` | 5 |
| `wrong_ranking` | 4 |
| `uncategorized_needs_manual_review` | 2 |

`wrong_chief_complaint_classification` dominates (9/16, 56%). Tracing three representative misses
down to the actual mechanism (via read-only diagnostics, no code changed) found three distinct,
precisely-diagnosed, **pre-existing** (not introduced by this round's own changes -- this round's
targeted fixes are separately unit/integration-tested and pass) generalization gaps that this
round's broader, more naturally-varied case authoring happened to expose for the first time:

1. **`chief_complaint.py` has no tag/alias coverage at all for extremely common upper-respiratory/
   cold-symptom wording.** `Blind13_01` ("stuffy nose and a scratchy throat... feeling a bit run
   down") routes to `primary_tag="other"` -- `build_clinical_presentation()` extracts
   `symptoms=[]`. No chief_complaint tag exists for "stuffy nose"/"runny nose"/"scratchy
   throat"/"congestion" at all (`viral_uri`'s own KB entry has typical_features, but nothing
   routes to it without a matching tag). Confirmed by direct reproduction:
   `route("stuffy nose and a scratchy throat since yesterday, feeling a bit run down")` returns
   `match_type="none"`.

2. **`matching.py`'s naive 6-character-truncation stemmer fails on common morphological variants**
   -- "weak" vs "weakness" and "spin" vs "spinning" do not stem to the same token (`_stem()` just
   truncates to 6 chars, so "weakness"->"weakne" while "weak"->"weak": different strings). This
   silently breaks otherwise-correct alias matches (e.g. `Blind13_15`'s "the room spins violently"
   against `dizziness`'s own alias "room spinning"; `Blind13_19`'s "weak all over" against
   `weakness`'s own canonical term "weakness").

3. **`chief_complaint.py`'s generic `weakness` tag has an alias ("can't move") broad enough to
   lexically capture and shadow the much more specific, clinically CRITICAL `focal_weakness` tag.**
   `Blind13_47` ("her left arm at all... can't move") routes to `primary_tag="weakness"` (generic,
   `RELATED_TAGS` -> `altered_mental_status`/`dizziness`, NOT stroke's disease pool) instead of
   `focal_weakness` (which would pull `ischemic_stroke` in directly) -- confirmed by direct
   reproduction of `route()` on the case's own chief-complaint text.

4. **The candidate-pool "nothing matched anything" whole-catalog fallback
   (`candidate_generator.generate_candidates`'s `if not pool:` branch) has no clinically-neutral
   tie-break.** When every one of the 34 Tier-1 diagnoses ties at score 0.0 (genuinely zero
   evidence matched, as in cases 1-3 above), `differential.py`'s stable sort preserves
   `all_diseases()`'s dict-insertion order -- which is simply the alphabetical order the
   `nova_agent/knowledge/diseases/*.json` files happen to load in. `abdominal_gi.json` loads
   first, so `acute_abdomen`/`gi_bleeding`/`ectopic_pregnancy`/`acute_pancreatitis`/`appendicitis`
   silently win every such tie -- confirmed directly:
   `list(all_diseases().keys())[:5] == ['acute_abdomen', 'gi_bleeding', 'ectopic_pregnancy',
   'acute_pancreatitis', 'appendicitis']`, exactly matching the (wrong) top-5 differential produced
   for three unrelated cases (`Blind13_01` viral URI, `Blind13_15` BPPV, `Blind13_19` severe
   electrolyte disorder). A genuinely uninformative presentation should degrade to explicit
   uncertainty, not a confident, clinically arbitrary wrong answer.

None of these four are blind-case-specific patches -- they are root, architectural gaps in the
routing/matching/fallback layers, independent of any specific diagnosis or vignette. Blind v12's
own case wording happened not to exercise them; Blind v13's broader, more naturally-varied
authoring (deliberately not reworded from v12) did.

## Explicit non-action

Per this round's discipline, **none of the four root causes above were fixed this round.**
`evaluation/blind_cases_v13.py` was not edited after the run, and no `nova_agent/`/`competition/`
file was touched after the reasoning freeze (`faa1701a1954239074cc9dea1137525eb19b3a22`). They are
recorded here as this round's honest, unremediated finding and the clear top priority for a future
generalization round -- to be fixed generically (broader chief_complaint.py tag coverage for common
complaint categories; a real morphological stemmer or suffix-stripping beyond naive truncation;
scoping the generic `weakness` tag's aliases so they cannot shadow `focal_weakness`; and a
clinically-neutral (or explicitly-uncertain) tie-break for the zero-evidence whole-catalog
fallback), then re-verified with a fresh Blind v14 authored after that fix.
