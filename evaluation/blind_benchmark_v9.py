"""`python -m evaluation.blind_benchmark_v9` -- runs evaluation/blind_cases_v9.py, the untouched
final generalization check for the current code AFTER the independent-re-audit round's reasoning
changes (lab-unit safety generalization in nova_agent/unit_safety.py + objective_evidence.py +
severity_evidence.py, and the lipase/urinalysis objective-evidence registry additions).

Blind v6 and Blind v8 are now REFERENCE-ONLY (each was frozen before a later reasoning change).
Blind v9 is authored/frozen after these changes and is the untouched check for the current code.

Deliberately NOT wired into evaluation/benchmark.py's --save-json output or CI's regression gate,
same as the earlier blind runners: a one-shot honesty check, run exactly once, reported as-is,
never re-tuned against. If reasoning code changes again, v9 becomes reference-only and a fresh v10
is authored.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from evaluation.benchmark import print_case_table, print_summary, run_all
from evaluation.blind_cases_v9 import BLIND_CASES_V9


def _verify_frozen_hash() -> None:
    root = Path(__file__).resolve().parents[1]
    case_file = root / "evaluation" / "blind_cases_v9.py"
    manifest = json.loads((root / "evaluation" / "blind_v9_manifest.json").read_text())
    actual = hashlib.sha256(case_file.read_bytes()).hexdigest()
    if actual != manifest["file_sha256"]:
        raise SystemExit(
            "BLIND V9 INTEGRITY FAILURE: evaluation/blind_cases_v9.py hash "
            f"{actual} != frozen manifest hash {manifest['file_sha256']}. The blind set was edited "
            "after freeze. Do not run/report this as the untouched Blind v9; author a fresh v10."
        )


if __name__ == "__main__":
    _verify_frozen_hash()
    results = run_all(BLIND_CASES_V9)
    print("=== Blind v9 set (evaluation/blind_cases_v9.py -- untouched check for the current code "
          "after the independent-re-audit unit-safety reasoning changes; never tuned against) ===")
    print_case_table(results)
    print_summary("Blind v9 summary", results)
