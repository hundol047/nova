"""`python -m evaluation.blind_benchmark_v14` -- runs evaluation/blind_cases_v14.py, the untouched
final generalization check for the current code AFTER Round D's root-cause chief-complaint
generalization hardening (chief_complaint.py's systematic taxonomy audit + specificity precedence,
matching.py's conservative morphology normalizer, candidate_generator.py/differential.py/
stop_policy.py/safety_validator.py's zero-evidence UNKNOWN_PRESENTATION fallback fix).

Blind v3-v13 are now REFERENCE-ONLY (each was frozen before a later reasoning change). Blind v14 is
authored/frozen after this round's changes (commit 202ed76c4b9bf49fffc62f1ba42f316fcc9f9b9b,
FINAL_REASONING_SHA) and is the untouched check for the current code.

Deliberately NOT wired into CI's regression gate: a one-shot honesty check, run exactly once,
reported as-is, never re-tuned against. If reasoning/retrieval code changes again, v14 becomes
reference-only and a fresh v15 is authored.

Cases with scoring_expected=False (long-tail Tier-2, unknown/OOD targets) are excluded from the
accuracy denominator but still executed for safe/crash/turn-limit behavior -- the point for those
is retrieval + explicit uncertainty, not deterministic top-1.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from evaluation.benchmark import print_case_table, print_summary, run_all
from evaluation.blind_cases_v14 import BLIND_CASES_V14


def _verify_frozen_hash() -> None:
    root = Path(__file__).resolve().parents[1]
    case_file = root / "evaluation" / "blind_cases_v14.py"
    manifest = json.loads((root / "evaluation" / "blind_v14_manifest.json").read_text())
    actual = hashlib.sha256(case_file.read_bytes()).hexdigest()
    if actual != manifest["file_sha256"]:
        raise SystemExit(
            "BLIND V14 INTEGRITY FAILURE: evaluation/blind_cases_v14.py hash "
            f"{actual} != frozen manifest hash {manifest['file_sha256']}. The blind set was edited "
            "after freeze. Do not run/report this as the untouched Blind v14; author a fresh v15."
        )


if __name__ == "__main__":
    _verify_frozen_hash()
    results = run_all(BLIND_CASES_V14)
    print_case_table(results)
    print_summary("Blind v14 summary", results)
