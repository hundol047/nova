"""`python -m evaluation.blind_benchmark_v10` -- runs evaluation/blind_cases_v10.py, the untouched
final generalization check for the current code AFTER the vNext 500-disease + ML-integration round's
reasoning changes (candidate_generator ontology broadening, open_world multi-signal retrieval +
rare fallback + hierarchy expansion, governed ML ranker backend integration).

Blind v3–v9 are now REFERENCE-ONLY (each was frozen before a later reasoning change). Blind v10 is
authored/frozen after these changes and is the untouched check for the current code.

Deliberately NOT wired into evaluation/benchmark.py's --save-json output or CI's regression gate,
same as the earlier blind runners: a one-shot honesty check, run exactly once, reported as-is,
never re-tuned against. If reasoning code changes again, v10 becomes reference-only and a fresh v11
is authored.

Cases with scoring_expected=False (rare/ontology-only/unknown/OOD/pediatric/pregnancy/unit-safety
Tier-2 targets) are excluded from the accuracy denominator by run_all/print_summary, but are still
executed for safe/crash/turn-limit behavior — the point for those is retrieval + explicit
uncertainty, not deterministic top-1.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from evaluation.benchmark import print_case_table, print_summary, run_all
from evaluation.blind_cases_v10 import BLIND_CASES_V10


def _verify_frozen_hash() -> None:
    root = Path(__file__).resolve().parents[1]
    case_file = root / "evaluation" / "blind_cases_v10.py"
    manifest = json.loads((root / "evaluation" / "blind_v10_manifest.json").read_text())
    actual = hashlib.sha256(case_file.read_bytes()).hexdigest()
    if actual != manifest["file_sha256"]:
        raise SystemExit(
            "BLIND V10 INTEGRITY FAILURE: evaluation/blind_cases_v10.py hash "
            f"{actual} != frozen manifest hash {manifest['file_sha256']}. The blind set was edited "
            "after freeze. Do not run/report this as the untouched Blind v10; author a fresh v11."
        )


if __name__ == "__main__":
    _verify_frozen_hash()
    results = run_all(BLIND_CASES_V10)
    print_case_table(results)
    print_summary(results)
