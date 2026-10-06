# Round G pre-change trace

Runtime: 83abfceb972fc9101ecbab5145cd4038c30bf5c4. Twelve fresh synthetic development scenarios, competition retrieval 150 / rerank 25 / reasoning 25, mock LLM. No v16 rerun.

- No eligible critical candidate dropped in this slice (retained candidate-turn counts in baseline_summary.json). Therefore no new survival persistence or ranking boost is justified. Existing re-generation/reinjection remains.
- Pleural scenario: positive exam evidence reached scoring at turn 14 but all candidate source tags remained zero_evidence_fallback, so UNKNOWN_PRESENTATION persisted until action exhaustion at turn 48. Proven stage: STOP_POLICY_FAILURE, not RETRIEVAL_MISS. Pool provenance must not override actual scoring evidence when evaluating the zero-evidence gate.
- Average turns 41.5; late actions still discriminate resolved alternatives and unsupported filler candidates. Action-focus filtering may reduce this without deleting candidates from safety/ranking. Measure before accepting.
- Korean denial 두통이 아니에요 is incorrectly normalized to headache; add a bounded denial marker and clause boundary checks.
- Infection scenario finishes as pyelonephritis rather than the sepsis target. It includes a urinary source and remains a documented ranking/syndrome failure; do not hardcode its answer.

These are development traces, not independent validation or clinically reviewed labels.

## Accepted changes

Zero-evidence status now also checks actual supporting findings after scoring. Competition action generation excludes already-resolved non-leading alternatives but keeps the full ranking/safety differential unchanged; no Top25 reduction, score bonus, persistent/immortal candidate, new stopping threshold, or new medical rule was introduced. NOVA_FOCUS_RESOLVED_ACTIONS disables this action-focus experiment for comparison. Clinical concept normalization recognizes Korean denial and limits negation scope to a symptom clause.

All six existing competition-mode slices retain accuracy and critical recall; held-out average turns 34.67 -> 29.06 and TEST 15.00 -> 11.39. Legacy generalization-v2 unnecessary-test proxy changes 1.333 -> 1.444 despite identical accuracy, recall and average total turns: recorded, not hidden. Round G remains 11/12 with a sepsis/urinary-source ranking miss. No expert adjudication is claimed.

Candidate survival persistence/dynamic ranking-width reduction were not added because dropout was not observed. Action focus is separate from candidate survival/ranking. Re-entry tests check new objective evidence; the development trajectories had no drop-then-return events, so an empirical re-entry success rate is not estimated.
