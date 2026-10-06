# Resumed clinical review pass (v15)

This pass resumes the uncommitted work recovered on 2026-10-05 from the v14
checkout. The selected runtime is commit 920eb608337fd035746be17cd87f12eb93bbe604.

## Evidence

- `baseline_round_m.json` and `baseline_regressions.json` retain earlier v14 runs.
- `final_summary.json` and `regressions.json` are the recovered development runs.
  Every recorded runtime file hash was checked against the resumed working tree
  and the selected commit; these runs were not represented as newly executed.
- `performance_comparison.json` retains all metrics and changed case outcomes.
- `experiments/` retains rejected variants; `experiment_decisions.json` records
  selection of `coverage_only`. No blind dataset was executed on resumption.
- `pytest_runtime.xml` and `pytest_release.xml` were newly executed on resumption:
  1,028 passed, zero failed, one skipped because torch is not installed.
- `standalone.log` records the newly executed isolated mock full loop.
- `package_audit.json` audits the final package after tests rebuilt the ZIP.
  ZIP timestamps mean a rebuild can change its digest without runtime changes.
- `field_provenance_inventory.json` contains lexical matches, not clinical review.
  Professor materials are in `docs/clinical_review/`; approvals remain pending.

Synthetic/mock Round M Top1 remains 118/123 (95.9349%); critical Top1 remains
43/43. Mean turns decrease from 25.8984 to 24.6797, while mean tests increase
from 8.9922 to 9.0234. The small test-cost increase and case-level losses remain
visible; no claim of universal improvement or real clinical accuracy is made.

## Verification commands

Run from the repository root:

```sh
python -m pytest tests/ --ignore=tests/test_current_pre_guide_release.py -q --junitxml=artifacts/clinical_review_pass/pytest_runtime.xml
python scripts/build_nova_submission.py
python scripts/verify_submission_standalone_full_loop.py
python scripts/audit_pre_guide_package.py --output artifacts/clinical_review_pass/package_audit.json
python scripts/record_clinical_review_release.py --runtime 920eb608337fd035746be17cd87f12eb93bbe604
python -m pytest tests/test_current_pre_guide_release.py -q --junitxml=artifacts/clinical_review_pass/pytest_release.xml
python scripts/record_clinical_review_release.py --runtime 920eb608337fd035746be17cd87f12eb93bbe604
```

The candidate is NOT READY for official submission. Legacy clinical source,
license and generation receipts, clinician review, the organizer's exact
interface, and real fixed-model execution remain unresolved.

GitHub transport imported the runtime with an identical Git tree; the local original
commit 542faa6256d85a036cb3760f88ad999a55e697e9 remains preserved locally.

## Public test evidence

JUnit reports publish hashed test identities, outcomes and durations only. Parameters,
paths, host metadata and output text are omitted. Adjacent receipt JSON files retain
the original report digest and outcome counts. Full originals remain in the local
pre-publication checkout. Redaction does not rerun tests or change their results.
The optional torch check remains the single skipped current-suite test.
