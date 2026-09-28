# Blind v14 first-run failure analysis (read-only, post-freeze)

Written strictly AFTER the frozen, exactly-once run of `evaluation.blind_benchmark_v14`
(`artifacts/blind_runs/blind_v14_first_run_output.txt`), against the current runtime with **no
reasoning/candidate/ranking code changed since**. This document only reads and reports; it makes
no further edits to `nova_agent/`, `competition/`, or `submission/`. Per the blind-set discipline,
Blind v14 itself is never re-tuned against these findings -- any fix implied here belongs to a
*future* round, which would then need its own fresh blind set (v15).

## Headline numbers

- Scored diagnostic accuracy: **83.7%** (41/49 scored cases; 7 excluded: 5 long-tail Tier-2 + 2
  unknown/OOD, all handled safely -- diagnosed, no critical miss, 100% unsupported-case success).
- Critical miss rate: **13.0%** (3 of 23 critical cases) -- **better than both Blind v13 (42.9%)
  and Blind v12 (22.2%)**, though not at the 0% floor the tuning/held-out/generalization-v2/stress/
  dev-round-d regression suites all hit.
- All-case accuracy: 73.2%. Zero malformed output, zero duplicate actions, 0% failed-to-diagnose.

## The 4 critical misses

### Blind14_09_SharpChestPainAfterLongDrive (truth: pulmonary_embolism, got: GERD)

Root cause identified by direct inspection (read-only): `pulmonary_embolism` never enters the
top-5 differential at all, even on turn 1, despite chief-complaint routing correctly identifying
both `chest_pain` and `dyspnea` (HIGH confidence) -- PE is a real member of the `chest_pain`/
`dyspnea` candidate pool via `symptom_match`. The actual problem is a **fuzzy-matching false
positive competing for the top rank**: on chief-complaint text alone, `gastroesophageal_reflux`
("gerd") scores 1.5 with supporting_evidence `['worse after meals']` -- the phrase "worse after
meals" is somehow satisfied by "...pain that's worse when I breathe...", i.e. a *different* disease's
generic "worse after X" pattern spuriously overlapping "worse when I breathe" via shared filler
words, not real GERD signal (the case never mentions meals at all). `tension_pneumothorax`
similarly scores via `['chest pain after trauma']` from "chest pain...after a 9-hour drive" -- the
word "after" plus "chest pain" clearing the fuzzy overlap threshold against an unrelated trauma
phrase. With PE genuinely absent from turn-1's differential and the case's key risk factor
("9-hour drive", answered under `social_history`) and confirmatory exam finding (mild calf
swelling, under `extremity_exam`) never actually elicited within the session (the agent's own
question-priority heuristics spent its budget on GERD/pneumothorax/ACS/arrhythmia discrimination
instead), PE never earns enough evidence to surface and the case closes as GERD.

**This is the same general class of bug this round's own hemoptysis/syncope fixes closed inside
`chief_complaint.py`'s fuzzy matcher** (a short, generic-word-heavy phrase overlapping unrelated
text without the real distinguishing word present) -- but here it lives in `differential.py`'s
separate `_score_phrase()`/`_present_with_aliases()` typical_features scoring path, which this
round's mandate did not include in scope (the four defect classes were chief-complaint routing
taxonomy, morphology, specificity precedence, and the zero-evidence file-order fallback -- not a
general robustness pass over every KB phrase's fuzzy-match safety). **Recommended for a future
round**: apply the same "short/generic-word phrase reduces to too little real signal" discipline
`matching.py`'s `feature_present()` already partially has to `differential.py`'s typical_features
scoring, and specifically audit "worse after X" / "X after Y"-style short causal phrases across the
KB for the same collision risk.

### Blind14_12_LatePeriodMistakenForStomachBug (truth: ectopic_pregnancy, got: ischemic_stroke)

`ectopic_pregnancy` is not a member of `CROSS_CUTTING_DANGEROUS_DIAGNOSES` (the small fixed
safety-net list), and the chief complaint ("nauseous and crampy on one side... stomach bug going
around") routes to no chief-complaint tag with real signal at turn 1 -- every candidate,
`ischemic_stroke` included, starts tied at score 0.0 via the safety net alone. The case's
decisive information (last-menstrual-period timing, under `social_history`; beta-hCG and pelvic
ultrasound results) requires the agent to specifically pursue those discriminators, which its
utility-based action selection did not prioritize highly enough within the turn budget against
competing safety-net candidates that DO have `dangerous:true`. This mirrors a limitation already
surfaced and worked around once this round, in `evaluation/generalization_dev_cases_round_d.py`'s
own Dev07 case (which needed explicit early routing wording to become reliably reachable) --
**ectopic_pregnancy's continued absence from the small fixed safety net remains a genuine,
documented gap for vague reproductive-age-female presentations**, outside this round's four
defect classes.

### Blind14_36_JapaneseMixedAbdominalPain (truth: appendicitis, got: meningitis) -- not critical, but instructive

Not a critical miss (appendicitis is `dangerous: false`), but worth noting: this is the one
mixed-language case that failed (the Korean-mixed ACS case, Blind14_35, passed). Not yet
root-caused in depth (time-boxed per this document's read-only, post-freeze scope) -- plausibly a
combination of the Japanese-language clause reducing effective chief-complaint routing signal and
a similar fuzzy-match dynamic to Blind14_09 pulling in an unrelated safety-net candidate. Flagged
for a future round's own mixed-language routing audit rather than investigated further here.

### Blind14_54_PeanutReactionAtRestaurant (truth: anaphylaxis, got: sepsis)

Chief-complaint routing correctly puts `anaphylaxis` at rank 1 on turn 1 (real `symptom_match`
signal from "throat...closing up" + "hives"). The case's vital signs are genuinely severe
(hypotension, tachycardia, tachypnea, hypoxia) by design (to make anaphylaxis's own dangerous
urgency legitimate) -- but those same numbers are also generically consistent with `sepsis` (also
in the fixed safety net, also `dangerous:true`), and `sepsis` apparently accumulates enough
generic severity-adjacent evidence over the session to overtake anaphylaxis's own thinner
typical_features match. Same general "acute physiologic derangement is evidence for the wrong
dangerous diagnosis when the RIGHT diagnosis's own KB `typical_features` list is thin" pattern as
Blind14_09 above -- not independently investigated further here.

## What this does NOT change

No `nova_agent/`, `competition/`, or `submission/nova_agent` file has been modified since the
reasoning freeze (commit `202ed76c4b9bf49fffc62f1ba42f316fcc9f9b9b`) or since this analysis was
written. Blind v14 was run exactly once and is reported here exactly as it came out -- these 4
misses are real, honestly recorded, and are NOT fixed by tuning against them. They represent
genuine remaining limitations outside this round's four defect classes, documented for a possible
future round (which would require its own fresh, independently-authored blind set).
