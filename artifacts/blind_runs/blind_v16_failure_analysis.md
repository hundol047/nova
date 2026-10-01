# Blind v16 results and analysis (read-only, post-freeze)

Two runs, declared in advance in `evaluation/blind_v16_manifest.json`, executed exactly once each against the
frozen, hash-verified set, on a runtime byte-identical to the Blind v15 measurement
(FINAL_REASONING_SHA `659c7dc6cdb484dc7dc351a39c52eea71a5b621f`; no reasoning change in Round F).
Raw outputs: `blind_v16_run_default_legacy.txt`, `blind_v16_run_competition_like.txt`.

| Run | Scored acc. | Crit. recall | Crit. miss | Avg / median turns | Avg ASK/EXAM/TEST |
|---|---|---|---|---|---|
| default / legacy (top-5 differential) | 79.7% (47/59) | 89.3% | 10.7% (3/28) | 23.8 / 24.0 | 8.0 / 6.1 / 8.7 |
| competition-like (`NOVA_COMPETITION_RETRIEVAL=1`, differential 25) | 83.1% (49/59) | 92.9% | 7.1% (2/28) | 39.8 / 42.0 | 11.0 / 9.7 / 18.0 |

History (scored accuracy / critical miss): v12 64.0%/22.2%, v13 57.9%/42.9%, v14 83.7%/13.0%,
v15 59.3%/38.5%, **v16 79.7%/10.7% (default)**, 83.1%/7.1% (competition-like). Different sets, so not a controlled trend.

## What this shows
1. The v15 collapse was largely a **distribution effect**, not (only) a code defect: v15 was deliberately skewed
   toward vague presentations. On a set whose chief-complaint specificity spans detailed-to-vague, the SAME code scores
   79.7%/10.7% under the default config, in line with v14.
2. Competition-like config is modestly more accurate (+3.4 pts accuracy, one fewer critical miss: DKA case 25 is
   found) but costs ~16 more turns and ~2x the tests per case (18.0 vs 8.7). Differences this size on 59 cases are
   within noise; no claim of a significant gain is made. The real turn limit is unknown, so the extra turns are a risk.
3. Still wrong in BOTH configs: critical `Blind16_15` (tension pneumothorax, young tall male) and `Blind16_17`
   (ectopic pregnancy presenting as a faint at work); non-critical `05` bronchitis, `18` chest-wall pain, `29` renal
   colic, `39` sulfonylurea hypoglycemia, `40` COPD/HF exacerbation, and both Japanese-mixed cases `43`, `44`.
   Default-only additional misses: `21` GERD and critical `25` DKA (lay phrasing).
4. Japanese-mixed: both cases wrong in both configs. Chief-complaint routing itself is correct (read-only check:
   vomiting/dizziness/dyspnea/abdominal_pain tags all assigned HIGH confidence), so the failure is NOT language
   normalization; cause not established here. Round E's Japanese mapping handles routing but its end-to-end
   benefit is unproven on blind data.
5. Reproductive-age contextual safety (Round E) did not rescue `Blind16_17`; the earlier-identified
   "vague complaint loses ranking over many turns" pattern is the likely cause (not re-investigated here).

## Round F code experiments (development sets only, fully reverted)
- Equal-score tie-break by evidence-source count, urgency, id: generalization-v2 100%->88.9%, Round D dev
  100%->83.3% (critical miss 33%), Round E dev 100%->66.7% (critical miss 40%). With >=6 tied candidates any order of
  5 drops some; PE/ectopic simply swapped places with others.
- Never splitting a tie at the cutoff: breaks 4 tests guarding the documented prompt-size invariants
  (legacy differential size 5; differential never exceeds reasoning_top_k). Not adopted.
Both reverted; no nova_agent/ change. Raising the legacy cap remains an open design decision.
