#!/usr/bin/env python3
"""Verifies README.md's benchmark numbers actually match evaluation/latest_results.json (spec
section 25: never let a stale hand-typed figure linger after the code that produced it changes).

    python -m evaluation.benchmark --save-json evaluation/latest_results.json
    python scripts/check_readme_numbers.py

Checks a small, explicit set of (JSON path, README percentage) pairs -- not every number in the
README, just the headline accuracy/critical-miss/recall figures in its Results table, which are
the ones most likely to silently drift. Exits non-zero with a clear diff if any mismatch.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Each entry: (JSON key path, README section label used only in error messages). The check reads
# the number as a percentage (0-100, one decimal place, matching print_summary()'s own "%.1f"
# formatting) and confirms that exact string appears somewhere in README.md.
CHECKS = [
    (("tuning", "scored_diagnostic_accuracy"), "Tuning scored accuracy"),
    (("held_out", "scored_diagnostic_accuracy"), "Held-out scored accuracy"),
    (("held_out", "all_case_diagnostic_accuracy"), "Held-out all-case accuracy"),
    (("held_out", "critical_diagnosis_recall"), "Held-out critical recall"),
    (("held_out", "critical_miss_rate"), "Held-out critical miss rate"),
]


def main() -> None:
    results_path = ROOT / "evaluation" / "latest_results.json"
    if not results_path.exists():
        print(f"NOT READY: {results_path} does not exist. Run:\n"
              "  python -m evaluation.benchmark --save-json evaluation/latest_results.json", file=sys.stderr)
        sys.exit(1)

    results = json.loads(results_path.read_text(encoding="utf-8"))
    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")

    mismatches = []
    for (top_key, metric_key), label in CHECKS:
        value = results.get(top_key, {}).get(metric_key)
        if value is None:
            mismatches.append(f"{label}: {metric_key!r} missing from latest_results.json")
            continue
        expected_pct = f"{value * 100:.1f}%"
        if expected_pct not in readme_text:
            mismatches.append(f"{label}: expected {expected_pct!r} (from latest_results.json) not found in README.md")

    if mismatches:
        print("README.md benchmark numbers are STALE:", file=sys.stderr)
        for m in mismatches:
            print(f"  - {m}", file=sys.stderr)
        print("\nRe-run `python -m evaluation.benchmark --save-json evaluation/latest_results.json` "
              "and update README.md's Results table.", file=sys.stderr)
        sys.exit(1)

    print("README.md benchmark numbers match evaluation/latest_results.json.")


if __name__ == "__main__":
    main()
