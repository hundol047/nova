# Reference integration evidence

Baseline remote/head: 3ede61c1079dc4597597a29ded1fd6668ae85402.
Bound runtime: c37d0c4b28565c90422c4df2d3bac099791ef97e.

- before/: fresh baseline full Round M and all eight permitted development suites.
- after/: same sets after adding static publisher reference context. Evaluation ran
  on staged runtime bytes; all file hashes were subsequently matched to the imported
  identical-tree commit. Original execution checkout HEAD is separately retained.
- performance_comparison.json: all aggregate metrics and case decisions equal.
- pytest_first_attempt.xml: historical interim run with two new test-import errors.
- pytest_runtime.xml: corrected suite excluding the three current-release checks.
- pytest_release.xml: those three checks, after writing current-release evidence.
- pytest.xml: union of the two disjoint successful groups, no duplicate tests;
  1,024 passed, 0 failed, 1 skipped. Optional hospital torch training check skipped
  because torch is absent; not reachable from competition inference.
- package_audit.json: exact final ZIP hash, source mirror and heuristic secret scan.
- standalone_mock.txt: actual isolated offline full loop, not organizer verification.

Commands (NOVA_LLM_PROVIDER=mock and NOVA_COMPETITION_RETRIEVAL=true for evaluation):

    NOVA_REGRESSION_OUTPUT=artifacts/licensed_references/after/regressions.json python scripts/evaluate_pre_guide_regressions.py
    python -c "import scripts.evaluate_round_m_final as e; e.OUT=e.ROOT/'artifacts/licensed_references/after/round_m/final'; e.main()"
    python -m pytest tests --ignore=tests/test_current_pre_guide_release.py --junitxml=artifacts/licensed_references/pytest_runtime.xml -q
    python scripts/build_nova_submission.py
    python scripts/audit_pre_guide_package.py --output artifacts/licensed_references/package_audit.json
    python scripts/record_reference_release.py
    python -m pytest tests/test_current_pre_guide_release.py --junitxml=artifacts/licensed_references/pytest_release.xml -q
    python scripts/record_reference_release.py

Full original per-turn trace JSONs are losslessly retained in each traces.tar.xz;
individual compressed duplicates are ignored. No blind cases were run or modified.
Source material and rights evidence are in research/licensed_references, separate
from synthetic development evidence here. Only the runtime reference catalog and
lookup module enter the candidate ZIP, never these evaluation artifacts.

Real fixed-model benefit, prompt token use and latency remain NOT VERIFIED.
The provider lock is unchanged. Official submission remains blocked by the guide/
transport and unresolved legacy provenance/review gaps.
