"""`python -m evaluation.blind_benchmark` -- runs evaluation/blind_cases_v3.py, a genuinely blind
final check (see that module's docstring for the authoring rules that keep it blind).

Deliberately NOT wired into evaluation/benchmark.py's --save-json output or CI's regression gate:
the whole point of this set is that it stays a one-shot honesty check, never a target a later
session tunes against. Its first real result is reported as-is in README.md /completion reports --
never silently re-run-and-cherry-picked, never used to justify reverting or adjusting a case after
the fact.
"""

from __future__ import annotations

from evaluation.benchmark import print_case_table, print_summary, run_all
from evaluation.blind_cases_v3 import BLIND_CASES_V3

if __name__ == "__main__":
    results = run_all(BLIND_CASES_V3)
    print("=== Blind v3 set (evaluation/blind_cases_v3.py -- authored blind, never tuned against) ===")
    print_case_table(results)
    print_summary("Blind v3 summary", results)
