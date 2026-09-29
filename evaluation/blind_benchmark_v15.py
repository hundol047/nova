"""`python -m evaluation.blind_benchmark_v15` -- runs evaluation/blind_cases_v15.py, the untouched
final generalization check for the current code AFTER Round E's root-cause hardening: generic-word/
short-alias fuzzy-match false positives in matching.py, context-aware critical safety activation
(nova_agent/contextual_safety.py), separation of diagnostic-specific evidence from generic
physiologic severity (differential.py/severity_evidence.py), bounded multilingual clinical concept
normalization (nova_agent/multilingual_concepts.py), and removal of the residual 6-character
morphology-truncation fallback.

Blind v3-v14 are now REFERENCE-ONLY (each was frozen before a later reasoning change). Blind v15 is
authored/frozen after this round's changes (commit 659c7dc6cdb484dc7dc351a39c52eea71a5b621f,
FINAL_REASONING_SHA) and is the untouched check for the current code.

Deliberately NOT wired into CI's regression gate: a one-shot honesty check, run exactly once,
reported as-is, never re-tuned against. If reasoning/retrieval code changes again, v15 becomes
reference-only and a fresh v16 is authored.

Cases with scoring_expected=False (long-tail Tier-2, unknown/OOD targets) are excluded from the
accuracy denominator but still executed for safe/crash/turn-limit behavior -- the point for those
is retrieval + explicit uncertainty, not deterministic top-1.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from evaluation.benchmark import print_case_table, print_summary, run_all
from evaluation.blind_cases_v15 import BLIND_CASES_V15


def _verify_frozen_hash() -> None:
    root = Path(__file__).resolve().parents[1]
    case_file = root / "evaluation" / "blind_cases_v15.py"
    manifest = json.loads((root / "evaluation" / "blind_v15_manifest.json").read_text())
    actual = hashlib.sha256(case_file.read_bytes()).hexdigest()
    if actual != manifest["file_sha256"]:
        raise SystemExit(
            "BLIND V15 INTEGRITY FAILURE: evaluation/blind_cases_v15.py hash "
            f"{actual} != frozen manifest hash {manifest['file_sha256']}. The blind set was edited "
            "after freeze. Do not run/report this as the untouched Blind v15; author a fresh v16."
        )


if __name__ == "__main__":
    _verify_frozen_hash()
    results = run_all(BLIND_CASES_V15)
    print_case_table(results)
    print_summary("Blind v15 summary", results)
