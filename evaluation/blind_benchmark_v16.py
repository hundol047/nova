"""`python -m evaluation.blind_benchmark_v16` -- runs evaluation/blind_cases_v16.py, a configuration-
realism measurement of the FROZEN runtime (FINAL_REASONING_SHA 659c7dc6cdb484dc7dc351a39c52eea71a5b621f,
byte-identical to what Blind v15 measured; no reasoning change in Round F).

Declared in advance (blind_v16_manifest.json "declared_runs"): exactly TWO executions, one per config,
never repeated, reported as-is, never re-tuned against:
  (a) default/legacy:        python -m evaluation.blind_benchmark_v16
  (b) competition-like:      NOVA_COMPETITION_RETRIEVAL=1 python -m evaluation.blind_benchmark_v16
Blind v3-v15 are REFERENCE-ONLY. Cases with scoring_expected=False are excluded from the accuracy
denominator but still executed for safe/crash/turn-limit behavior.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from evaluation.benchmark import print_case_table, print_summary, run_all
from evaluation.blind_cases_v16 import BLIND_CASES_V16


def _verify_frozen_hash() -> None:
    root = Path(__file__).resolve().parents[1]
    case_file = root / "evaluation" / "blind_cases_v16.py"
    manifest = json.loads((root / "evaluation" / "blind_v16_manifest.json").read_text())
    actual = hashlib.sha256(case_file.read_bytes()).hexdigest()
    if actual != manifest["file_sha256"]:
        raise SystemExit(
            "BLIND V16 INTEGRITY FAILURE: evaluation/blind_cases_v16.py hash "
            f"{actual} != frozen manifest hash {manifest['file_sha256']}. The blind set was edited "
            "after freeze. Do not run/report this as the untouched Blind v16; author a fresh v17."
        )


if __name__ == "__main__":
    _verify_frozen_hash()
    results = run_all(BLIND_CASES_V16)
    print_case_table(results)
    print_summary("Blind v16 summary", results)
