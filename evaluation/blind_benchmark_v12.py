"""`python -m evaluation.blind_benchmark_v12` -- runs evaluation/blind_cases_v12.py, the untouched
final generalization check for the current code AFTER this round's competition retrieval-recall
rebuild (nova_agent/retrieval_pipeline.py's multi-query weighted RRF fusion + signal weighting,
nova_agent/ontology/search.py's typical_features indexing + IDF-like token weighting).

Blind v3-v11 are now REFERENCE-ONLY (each was frozen before a later reasoning change). Blind v12 is
authored/frozen after this round's retrieval changes (commit b3fdccd) and is the untouched check
for the current code.

Deliberately NOT wired into CI's regression gate: a one-shot honesty check, run exactly once,
reported as-is, never re-tuned against. If reasoning/retrieval code changes again, v12 becomes
reference-only and a fresh v13 is authored.

Cases with scoring_expected=False (long-tail Tier-2/shallow-Tier-3/pediatric/pregnancy/unknown/
sparse-information targets, plus the retrieval-miss trap) are excluded from the accuracy
denominator but still executed for safe/crash/turn-limit behavior -- the point for those is
retrieval + explicit uncertainty, not deterministic top-1.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from evaluation.benchmark import print_case_table, print_summary, run_all
from evaluation.blind_cases_v12 import BLIND_CASES_V12


def _verify_frozen_hash() -> None:
    root = Path(__file__).resolve().parents[1]
    case_file = root / "evaluation" / "blind_cases_v12.py"
    manifest = json.loads((root / "evaluation" / "blind_v12_manifest.json").read_text())
    actual = hashlib.sha256(case_file.read_bytes()).hexdigest()
    if actual != manifest["file_sha256"]:
        raise SystemExit(
            "BLIND V12 INTEGRITY FAILURE: evaluation/blind_cases_v12.py hash "
            f"{actual} != frozen manifest hash {manifest['file_sha256']}. The blind set was edited "
            "after freeze. Do not run/report this as the untouched Blind v12; author a fresh v13."
        )


if __name__ == "__main__":
    _verify_frozen_hash()
    results = run_all(BLIND_CASES_V12)
    print_case_table(results)
    print_summary("Blind v12 summary", results)
