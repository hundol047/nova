# Safety cycle 2 — synthetic replay, not clinical accuracy

2026-10-03. No model training or independent clinical validation. All cases are existing
synthetic source-family variants; mock provider, no real LLM calls. Original cohort and extra
cohort each contain 200 low and 200 high difficulty inputs. The extra cohort excludes every
original input hash but shares historical source families. Both cohorts became development
material during this cycle; neither is an independent holdout. Multiple runs do not create
additional patients or independent evidence.

## Defect and chosen change

The SafetyLayer relevance gate ignored a candidate whose origin was only `safety_candidate`,
even after specific current signs were recognized. For example the differential recognized
Japanese melena, but routing did not assign a gastrointestinal complaint tag and safety stayed
silent. Add a narrow route-independent gate for current melena/hematemesis/hematochezia and
focal neurological signs, using existing negation-aware matching and excluding structured
past/family history. Add scoped dysarthria and Korean speech-deficit aliases to slurred speech.
These rules create safety concerns, not confirmed diagnoses. No benchmark ID, target label or
expected outcome enters runtime code.

Initial attempt broadly admitted candidates with supporting evidence (`after_*`). This raised
warnings on nonspecific symptoms and was rejected. A narrower attempt (`final_*`) retained a
Korean cold-sweat alias, which raised extra warnings in vasovagal cases with denied chest pain;
that alias was also removed. Only `accepted_*` describes the chosen implementation.
Intermediate output snapshots record experimental results and are not release metrics.

## Evidence scope and sources

NHS stroke guidance identifies speech change and one-sided deficits as warning signs; NIDDK
lists overt gastrointestinal bleeding symptoms. These sources support safety considerations,
not the measured accuracy or clinical validation of these program rules.

- https://www.nhs.uk/conditions/stroke/symptoms/
- https://www.niddk.nih.gov/health-information/digestive-diseases/gastrointestinal-bleeding/symptoms-causes
- https://www.nhs.uk/conditions/heart-attack/ (reviewed during rejected sweating expansion)

Sources checked 2026-10-03. Existing multilingual aliases are reused; no new medical model or
external runtime service was introduced. Whole-free-text historical/negation handling remains
limited; these changes do not establish comprehensive clinical language understanding.

## Files and verification

- `nova_agent/safety.py` and submission mirror: scoped evidence gate and speech aliases.
- `tests/test_safety_evidence_relevance.py`: current positive signs, negation, family context,
  empty candidates and nonspecific-feature counterexamples.
- `scripts/run_balanced_400.py`: reproducible selection seed, exclusion and fresh output controls.
- Each evaluation directory retains fixed inputs, trajectories, result hashes, failures and metrics.
- `comparison.json` and `RESULTS.md`: accepted before/after comparisons.
- `regression.txt`: complete non-API regression outcome. The known API TestClient blocker is
  still excluded explicitly; API verification remains unfinished.

Next priorities: review the remaining warning misses; keep separate current findings and past
results; improve insufficient-information handling and review supplementary targets lacking
validated deep profiles. Do not tune using future independent test labels or claim repeated
simulations constitute model training.
