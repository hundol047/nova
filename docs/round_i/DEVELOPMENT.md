# Round I development and freeze rationale

The starting remote HEAD was `22b95686b42b6d38f3809da64745da398966593a` on the requested offline branch. Main was not changed. v17 wording/results were not used to tune this round; its cases and recorded results remain unchanged.

## Measured change

| Development measure | Before | After |
| --- | --- | --- |
| Top1 / Top3 / Top5 / Top10 | 16/19 (84.21%) | 17/19 (89.47%) |
| MRR | 0.84421 | 0.89474 |
| Median true rank (present ranks only) | 1; 2 absent | 1; 2 absent |
| Critical Top1 / Top5 | 7/8 | 8/8 |
| Fresh task-scope OOD detection | 0/9 | 9/9 |
| Supported false OOD | 0/8 | 0/8 |
| Hard clinical presentations retained in medical scope | 2/2 | 2/2 |
| Insufficient-information detection | 7/7 | 7/7 |
| Unsafe confident unsupported label proxy | 0/16 | 0/16 |
| Protocol-forced labels in one-turn OOD probe | 24/24 | 24/24 |

These are small, authored synthetic DEVELOPMENT samples using competition retrieval with a mock LLM, not independent clinical validation, calibrated confidence, training, or measured real-model performance. Nonsense/unsupported symptoms stay insufficient; OOD means outside the symptom-diagnosis task, including administration and medication storage. The two hard clinical controls only test preservation of medical scope; they do not establish rare-disease diagnosis accuracy. The forced-label rate reflects a deliberately one-turn provisional protocol; internal uncertainty must accompany those labels.

## Mechanism and bounded scope

`matching.py` and `differential.py` now require an actual denial before crediting negative reassuring evidence. Previously, a positive focal neurological deficit also matched “no focal neurological deficit”, producing false contradiction penalties. The new check removes those penalties without changing diagnosis weights, retrieval, safety, action selection or stop policy. A fresh stroke development case changed from a wrong ectopic-pregnancy label to the expected stroke label. Negative and unrelated-negation controls are unit-tested.

`uncertainty.py` recognizes general request verbs plus administrative objects, or medication-information language without patient evidence. Current clinical evidence or exposure risk protects mixed text from OOD. This does not patch the preceding eight examples: their result remains 6/8, with supported false OOD 0/12.

Every development error retains retrieval/rerank/active ranks and counterfactual scorer contributions, objective/risk/medication/negative evidence and contradictions in `artifacts/round_i/{baseline,after}.json`. Successful cases retain their final trace. Component deltas are non-additive because of scorer caps and are not probabilities. Baseline was taken before the diagnostic/OOD fixes in this working tree; transport changes had already been applied and are not part of the mock accuracy comparison.

## Remaining failures and next priorities

The positional-dizziness case still loses its candidate in the active differential; the long-tail Sjogren author hypothesis still misses retrieval. Keep these as development errors, not claims of unsupported clinical accuracy. The known Round G systemic-infection miss remains: 11/12, critical 3/4, average 36.75 turns. No broad retrieval rebuild or shortened safety workup was justified by this small sample.

Full pre-freeze regression: 828 passed, 1 skipped (optional torch unavailable). Six legacy and six competition-structure slices retain their scored/critical results. Retrieval remains chief-only R@20 56.8%, R@50 61.4%; chief+history 75.0%, 93.2% on the 44-case synthetic retrieval benchmark. Routing, specificity, adversarial, failure analysis and leakage checks passed. Specificity still reports three thin phrases for periodic review. Historical evaluation sets are regression evidence, not fresh holdouts.

## Integration changes

`llm_preflight.py`, `llm_client.py`, `config.py`, `competition/readiness.py`, `preflight_competition.py`, `smoke_real_llm.py` and mirrored submission files expose explicit statuses; keep expected model/revision separate; reject credential-bearing URLs and redirects; and preserve per-case parsed-call gating. Syntax repair now preserves string content. Unit and isolated subprocess tests exercise bounded failure modes and case isolation. No new dependencies or learned weights were introduced.

The official public audit confirms model/revision and action names, but not executable schemas, auth syntax, endpoint or abstention legality. This environment has no explicitly configured endpoint. Real-model development comparison is EXTERNAL BLOCKED. A fresh v18 will therefore be predeclared COMPETITION-STRUCTURE / MOCK-LLM, authored after the published reasoning freeze, hash-frozen, and executed exactly once. No runtime changes are permitted after that run.
