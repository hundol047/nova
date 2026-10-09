# Round S local evidence and public source review

See `docs/competition/ROUND_S_REPAIR_REPORT_KO.md` for the complete comparison and FAIL/partial acceptance.
Runtime: `95d465b0f01023148d60ff02667596bf22c19b4a`; public source: `ed5a5e4131a04e37ca15559334794f5f817c2b35`.
Baseline runtime: `18b994984d0e22c1ee15a3e9ffcc125d5056b46b` (tree-identical public `cf31e011244a9f5340ea36c05a723dc1d11177aa`).

All evaluations use mock and competition retrieval. No official interface/model claim. Source-only publication
excludes the detailed traces/XML/v24 ZIP; locally present evidence below is not necessarily on GitHub.

- `final/execution_binding.json`: complete runtime hashes, execution conditions, final evidence hashes.
- `final/reasoning_freeze.json`: final freeze; `evaluation/frozen_validation_round_s_manifest.json`: unchanged fixture freeze.
- `final/comparison.json`: case-by-case same-scorer comparison; includes new wrong and critical regressions.
- `final/prelim.json`, `round_p.json`, `round_q.json`, `round_r/summary.json`, `acceptance_regression/summary.json`: development evidence.
- `baseline/new_validation/`, `final/new_validation/`: same newly frozen 24 cases on both runtimes.
- `final/regressions.json`: eight TEST-enabled suites; `final/round_m/`: complete 128 cases, metrics/failure analysis/compressed traces.
- `final/val_o11.json`: targeted old TEST-path critical failure rerun.
- `final/test_summary.json`, three disjoint JUnit XML files and logs: 2208/0/1 with skip reason.
- `final/sync.json`, `package_audit.json`, `zip_validation.json`, `package_smoke.log`: isolated build/package checks.
- `final/static_checks.log`: leakage, specificity, routing, retrieval proxy, adversarial and failure analysis actual commands/exit codes.
- `final/remaining_reproductions.json`, `scripts/reproduce_round_s_remaining.py`: read-only failures after freeze; not passing tests.
- `development/`: failed/intermediate attempts, including the explicitly disclosed unread partial baseline-only S attempt.
- `final/public_source_binding.json`: runtime bytes tied to the public source commit; not full-tree equality.

## Reproduction entry points

Use a clean worktree at the named runtime and the same dependencies. Preserve original cases/scoring.

```sh
NOVA_LLM_PROVIDER=mock NOVA_COMPETITION_RETRIEVAL=1 python scripts/evaluate_preliminary_benchmark.py --workers 4 --gate --output /tmp/nova-prelim.json
NOVA_LLM_PROVIDER=mock NOVA_COMPETITION_RETRIEVAL=1 python scripts/evaluate_round_s.py --checkout . --cases evaluation/frozen_validation_round_s.json --freeze evaluation/frozen_validation_round_s_manifest.json --output /tmp/nova-s --workers 4
NOVA_LLM_PROVIDER=mock NOVA_COMPETITION_RETRIEVAL=1 python scripts/reproduce_round_s_remaining.py
python scripts/summarize_round_s.py
```

Tests were run without a global competition-retrieval override; test-local configurations are preserved.
Ordinary tests excluded only `test_ncit_review_expansion.py` and `test_current_pre_guide_release.py`, then both
files ran in separate processes. Union has no duplicate tests, no deselections, one intentional torch skip.
`record_round_s_release.py` checks runtime/ZIP equality and binds only the actual final evidence. Intermediate
results are never substituted. Build in a disposable worktree because the build tool updates submission mirrors.
