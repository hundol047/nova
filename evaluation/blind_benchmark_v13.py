"""`python -m evaluation.blind_benchmark_v13` -- runs evaluation/blind_cases_v13.py, the untouched
final generalization check for the current code AFTER this round's critical-generalization
hardening (candidate_generator.py's must-not-miss pool-trim fix, differential.py's analogous
final-differential safety reinjection + typical_feature contribution cap, objective_evidence.py's
broadened qualitative-evidence vocabulary, matching.py's shared alias-aware pool-membership fix).

Blind v3-v12 are now REFERENCE-ONLY (each was frozen before a later reasoning change). Blind v13 is
authored/frozen after this round's generalization changes (commit
faa1701a1954239074cc9dea1137525eb19b3a22, FINAL_REASONING_SHA) and is the untouched check for the
current code.

Deliberately NOT wired into CI's regression gate: a one-shot honesty check, run exactly once,
reported as-is, never re-tuned against. If reasoning/retrieval code changes again, v13 becomes
reference-only and a fresh v14 is authored.

Cases with scoring_expected=False (long-tail Tier-2, unknown/OOD targets) are excluded from the
accuracy denominator but still executed for safe/crash/turn-limit behavior -- the point for those
is retrieval + explicit uncertainty, not deterministic top-1.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from evaluation.benchmark import print_case_table, print_summary, run_all
from evaluation.blind_cases_v13 import BLIND_CASES_V13


def _verify_frozen_hash() -> None:
    root = Path(__file__).resolve().parents[1]
    case_file = root / "evaluation" / "blind_cases_v13.py"
    manifest = json.loads((root / "evaluation" / "blind_v13_manifest.json").read_text())
    actual = hashlib.sha256(case_file.read_bytes()).hexdigest()
    if actual != manifest["file_sha256"]:
        raise SystemExit(
            "BLIND V13 INTEGRITY FAILURE: evaluation/blind_cases_v13.py hash "
            f"{actual} != frozen manifest hash {manifest['file_sha256']}. The blind set was edited "
            "after freeze. Do not run/report this as the untouched Blind v13; author a fresh v14."
        )


if __name__ == "__main__":
    _verify_frozen_hash()
    results = run_all(BLIND_CASES_V13)
    print_case_table(results)
    print_summary("Blind v13 summary", results)
