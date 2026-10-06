# Blind v15 first-run failure analysis (read-only, post-freeze)

Written strictly AFTER the frozen, exactly-once run of `evaluation.blind_benchmark_v15`
(`artifacts/blind_runs/blind_v15_first_run_output.txt`), against the current runtime with **no
reasoning/candidate/ranking code changed since**. This document only reads and reports; it makes no
further edits to `nova_agent/`, `competition/`, or `submission/`. Per the blind-set discipline,
Blind v15 itself is never re-tuned against these findings -- any fix implied here belongs to a
*future* round, which would then need its own fresh blind set (v16).

## Headline numbers (reported honestly, no improvement claimed)

- Scored diagnostic accuracy: **59.3%** (32/54 scored cases; 7 excluded: 4 long-tail Tier-2 + 1
  reproductive-age-emergency Tier-2 + 2 unknown/OOD, all handled safely -- diagnosed, no critical
  miss, 100% unsupported-case success).
- Critical miss rate: **38.5%** (10 of 26 critical cases) -- **substantially worse than Blind v14
  (13.0%)**, and worse than every prior blind set on record. This is a real, honestly-reported
  result, not a typo and not spin: **Blind v15 does not show a monotonic improvement over v14.**
- All-case accuracy: 52.5%. Zero malformed output, zero duplicate actions, 0% failed-to-diagnose.

## Why the number dropped: this is NOT primarily a Round E regression

Round E's five named defect classes (A: generic-word/relational-word fuzzy-match false positives,
B: context-aware critical safety activation, C: diagnostic-specificity-vs-generic-severity
separation, D: bounded multilingual concept normalization, E: residual morphology-truncation
removal) are each independently verified fixed by dedicated unit tests
(`tests/test_feature_match_*`, `tests/test_*_safety*`, `tests/test_severity_not_diagnostic_identity.py`,
`tests/test_specific_evidence_over_generic_severity.py`, `tests/test_multilingual_*`,
`tests/test_mixed_language_routing.py`, `tests/test_morphology_no_truncation_fallback.py`), and by
this round's own development-case suite (`evaluation/generalization_dev_cases_round_e.py`, 100%
scored accuracy / 0% critical miss), and by the full existing regression suite (held-out,
generalization-v2, stress, Round D dev, tuning -- all still at their exact required floors, zero
regression). None of those checks moved when this document was written.

Investigating a sample of Blind v15's critical misses (read-only, via
`nova_agent.differential.DifferentialEngine`, never modifying any case or reasoning file) points to
a DIFFERENT, previously out-of-scope architectural boundary that Round E's five named defect areas
never touched:

### Root cause 1 (the majority of sampled misses): the legacy top-5 differential cap + zero-score tie-break

`differential.py`'s non-competition-retrieval path truncates the scored candidate list to
`top_k = get_config().effective_differential_top_k()`, which defaults to **5** -- long-standing,
unchanged behavior, confirmed byte-identical before and after this round's freeze. On turn 1 (chief
complaint only, no ASK/EXAM/TEST evidence gathered yet), it is common for the correct diagnosis and
several rival candidates -- including the always-present 8-entry `CROSS_CUTTING_DANGEROUS_DIAGNOSES`
safety net -- to all score exactly 0.0 (no typical_feature has been evidenced yet). The tie-break
among equally-scored zero-evidence candidates is a stable sort, which in practice follows candidate-
pool insertion order (disease-KB tag/file iteration order). For a genuinely lay, low-detail chief
complaint -- exactly the style this round's spec explicitly required more of ("vague presentations,"
"sparse evidence," "premature diagnosis trap") -- this insertion-order tie-break can exclude the true
diagnosis from the top-5 differential from turn 1 onward, before the agent ever has a chance to ask
the question that would surface its real evidence.

Sampled and confirmed for 6 of 10 investigated critical misses (`Blind15_09` pulmonary embolism after
a cast removal, `Blind15_13` tension pneumothorax after a fall, `Blind15_20` DKA in a teenager,
`Blind15_29` pulmonary embolism in pregnancy, `Blind15_40` DKA-vs-sepsis, `Blind15_57` DKA presenting
as flu-like illness): the ground-truth diagnosis is absent from `DifferentialEngine().update(state)`'s
turn-1 output despite chief-complaint routing correctly identifying the right symptom tag (verified
directly), and despite `candidate_generator.generate_candidates()` correctly INCLUDING the true
diagnosis in its raw pool (also verified directly) -- the loss happens specifically at the `top_k`
truncation step, on an all-zero tie.

**Confirmed pre-existing, not new this round**: the identical mechanism reproduces on Blind v14's own
historical case content (`Blind14_09_SharpChestPainAfterLongDrive`) run against the CURRENT, fully
Round-E-fixed code -- pulmonary embolism is absent from that case's own turn-1 top-5 for the same
tie-break reason, even though Round E's fix to the GERD fuzzy-match false positive (the original,
already-documented cause of that specific case's Round D-era miss) is confirmed working. This is a
different, deeper architectural boundary that Round D and Round E's fixes never targeted, because it
sits one level below all five of Round E's named defect classes: it is not about WHICH candidates get
proposed or how they are scored once evidence exists, but about how many zero-evidence candidates the
turn-1 differential is willing to carry forward at all.

### Root cause 2 (several sampled misses): the true diagnosis stays a live candidate the whole case but loses the final ranking

For `Blind15_10` (meningitis), `Blind15_26` (isolated-ataxia stroke), and `Blind15_56` (early acute
abdomen), the ground-truth diagnosis is present in the top-5 differential at every turn checked,
including up to the final DIAGNOSE turn -- yet a different, rank-1 rival still wins at the moment of
diagnosis. This is a genuine ranking-precision limitation, not a candidate-pool exclusion: the
competing diagnosis's accumulated evidence out-scores the true diagnosis's by the end of the case even
though both remain plausible candidates throughout. Round E's defect-C fix (generic severity no longer
counts as diagnostic-specific evidence) measurably helps this class of problem where it was checked
directly (see `tests/test_specific_evidence_over_generic_severity.py` and the
`specific_vs_generic_severity_conflict` Blind v15 cases themselves, which scored 2/3 correct) but does
not eliminate every case where two genuinely plausible, partially-evidenced diagnoses compete for the
same rank across many turns.

### Root cause 3 (at least one sampled miss): the recurring "vague complaint loses competitive ranking over many turns" pattern

`Blind15_36` (ectopic pregnancy, deliberately vague reproductive-age presentation) shows the true
diagnosis present via `contextual_safety` at early turns, then dropping out of the top-5 entirely by
around turn 3 and never returning, ultimately diagnosed as something else. This is the SAME pattern
already identified twice before in this project's history: Round D's `Dev07_VagueComplaintHypoglycemiaOnLabs`
development case, and (independently) this round's own `DevE03_VagueReproductiveAgeEmergency`
development case before its answers were strengthened to keep the true diagnosis competitive. It is
explicitly a known, previously-documented, NOT-yet-architecturally-solved failure mode -- this round's
`contextual_safety.py` mechanism (defect B) is independently verified correct at the point of
ACTIVATION (see `tests/test_reproductive_emergency_safety.py`,
`tests/test_cross_cutting_critical_activation.py`), but activation alone does not guarantee the
activated candidate survives many subsequent turns of competing evidence accumulation for rival
diagnoses.

## Why v15 surfaces this more than v14 did

Blind v14 (56 cases) and Blind v15 (61 cases) run through the identical `top_k=5` / tie-break /
ranking-drift architecture. The difference in observed impact is best explained by the DISTRIBUTION
of the two case sets, not the reasoning code: Blind v15's required category spread (per this round's
mandate) explicitly calls for more vague/lay-phrased/sparse-evidence/premature-diagnosis-trap/late-
diagnosis-trap presentations than Blind v14's own spread did, and those are exactly the presentation
styles most exposed to root causes 1 and 3 above (a rich, specific chief complaint is far more likely
to give the true diagnosis nonzero turn-1 evidence and avoid the all-zero tie-break entirely). Blind
v15 is, in this sense, doing its job: it is a harder, more architecturally probing set than v14 was,
and it found a real, previously-undetected weak point.

## What this does NOT mean

This does not mean Round E's five fixes are ineffective -- each is independently verified via unit
tests, development cases, and the full unchanged regression suite (held-out/generalization-v2/stress/
Round D dev/tuning all remain at their exact required floors). It means Round E's scope (the five
named defect classes A-E) did not happen to cover this different, deeper limitation, and Blind v15's
broader, harder distribution was effective at finding it.

## Recommendation for a future round

The single highest-value architectural target surfaced here: reconsider the legacy `top_k=5`
differential-candidate cap and its all-zero-score tie-break in the non-competition-retrieval path
(`nova_agent/differential.py`'s `effective_differential_top_k()` / `NovaConfig` defaults) -- either
raise the default cap, or replace the insertion-order tie-break among zero-scored candidates with a
principled one (e.g. urgency/dangerousness-aware, or simply never let the fixed 8-entry safety net
crowd out a symptom-matched, tag-relevant candidate at equal score). A fresh, independent blind set
(v16) would be required to measure any fix to this, per the same discipline this round followed.
