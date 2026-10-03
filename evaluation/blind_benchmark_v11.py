"""Historical v11 reference, now explicitly used for hard-case development.

The fixture and its hash remain frozen; it is no longer an untouched blind test.
All 22 named targets are scored, including Tier-2; two unknown targets are also
included in all-case accuracy. No cases or denominators are dropped for difficulty.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from evaluation.benchmark import print_case_table, print_summary, run_all
from evaluation.blind_cases_v11 import BLIND_CASES_V11


def _verify_frozen_hash() -> None:
    root = Path(__file__).resolve().parents[1]
    case_file = root / "evaluation" / "blind_cases_v11.py"
    manifest = json.loads((root / "evaluation" / "blind_v11_manifest.json").read_text())
    actual = hashlib.sha256(case_file.read_bytes()).hexdigest()
    if actual != manifest["file_sha256"]:
        raise SystemExit(
            "BLIND V11 INTEGRITY FAILURE: evaluation/blind_cases_v11.py hash "
            f"{actual} != frozen manifest hash {manifest['file_sha256']}. The blind set was edited "
            "after freeze. Do not run/report this as the untouched Blind v11; author a fresh v12."
        )


if __name__ == "__main__":
    _verify_frozen_hash()
    results = run_all(BLIND_CASES_V11)
    print_case_table(results)
    print_summary("blind_benchmark_v11 (reference after audit fixes)", results)
