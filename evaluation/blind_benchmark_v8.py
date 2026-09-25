"""`python -m evaluation.blind_benchmark_v8` -- runs evaluation/blind_cases_v8.py, the untouched
final generalization check authored AFTER this pilot-readiness workstream's only reasoning-code
change (the Stage 4 glucose unit-safety guard in nova_agent/glucose_evidence.py). See that module's
docstring for the authoring rules that keep it blind, and evaluation/blind_v8_manifest.json for the
file hash recorded at freeze time, before this runner was ever executed.

Deliberately NOT wired into evaluation/benchmark.py's --save-json output or CI's regression gate,
same as blind_benchmark.py / blind_benchmark_v4.py / blind_benchmark_v5.py / blind_benchmark_v6.py:
this set stays a one-shot honesty check, never a target a later session tunes against. Its first
real result is reported as-is -- never silently re-run-and-cherry-picked, never used to justify
reverting or adjusting a case after the fact. If a future reasoning change is made, Blind v8
becomes reference-only and a fresh untouched v9 is authored instead.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from evaluation.benchmark import print_case_table, print_summary, run_all
from evaluation.blind_cases_v8 import BLIND_CASES_V8


def _verify_frozen_hash() -> None:
    """Fail loudly if blind_cases_v8.py was edited after its manifest hash was frozen -- the freeze
    is the whole point of a blind set. Prints a clear warning rather than silently running a
    modified set as if it were the frozen one."""
    root = Path(__file__).resolve().parents[1]
    case_file = root / "evaluation" / "blind_cases_v8.py"
    manifest = json.loads((root / "evaluation" / "blind_v8_manifest.json").read_text())
    actual = hashlib.sha256(case_file.read_bytes()).hexdigest()
    if actual != manifest["file_sha256"]:
        raise SystemExit(
            "BLIND V8 INTEGRITY FAILURE: evaluation/blind_cases_v8.py hash "
            f"{actual} != frozen manifest hash {manifest['file_sha256']}. The blind set was edited "
            "after freeze. Do not run/report this as the untouched Blind v8; author a fresh v9 "
            "instead (see the manifest note)."
        )


if __name__ == "__main__":
    _verify_frozen_hash()
    results = run_all(BLIND_CASES_V8)
    print("=== Blind v8 set (evaluation/blind_cases_v8.py -- the untouched final generalization "
          "check authored after the Stage 4 glucose unit-safety reasoning fix, never tuned "
          "against) ===")
    print_case_table(results)
    print_summary("Blind v8 summary", results)
