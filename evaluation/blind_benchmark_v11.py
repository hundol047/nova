"""`python -m evaluation.blind_benchmark_v11` -- runs evaluation/blind_cases_v11.py, the untouched
final generalization check for the current code AFTER the 5,000-diagnosis retrieval-architecture
round (embedding retrieval, multi-specialty router, safety-recall expansion, deep reranker,
retrieval->rerank->LLM pipeline with a lexical-grounding UNKNOWN guard).

Blind v3–v10 are now REFERENCE-ONLY (each was frozen before a later reasoning change). Blind v11 is
authored/frozen after these changes and is the untouched check for the current code.

Deliberately NOT wired into CI's regression gate: a one-shot honesty check, run exactly once,
reported as-is, never re-tuned against. If reasoning code changes again, v11 becomes reference-only
and a fresh v12 is authored.

Cases with scoring_expected=False (rare/long-tail/Tier-2/unknown/OOD/pediatric/pregnancy/unit-safety
targets, plus the retrieval-miss trap) are excluded from the accuracy denominator but still executed
for safe/crash/turn-limit behavior — the point for those is retrieval + explicit uncertainty, not
deterministic top-1.
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
    print_summary(results)
