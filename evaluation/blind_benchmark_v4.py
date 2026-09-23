"""`python -m evaluation.blind_benchmark_v4` -- runs evaluation/blind_cases_v4.py, a second
genuinely blind final check (see that module's docstring for the authoring rules that keep it
blind).

Deliberately NOT wired into evaluation/benchmark.py's --save-json output or CI's regression gate,
same as blind_benchmark.py/blind_cases_v3.py: this set stays a one-shot honesty check, never a
target a later session tunes against. Its first real result is reported as-is -- never silently
re-run-and-cherry-picked, never used to justify reverting or adjusting a case after the fact.
"""

from __future__ import annotations

from evaluation.benchmark import print_case_table, print_summary, run_all
from evaluation.blind_cases_v4 import BLIND_CASES_V4

if __name__ == "__main__":
    results = run_all(BLIND_CASES_V4)
    print("=== Blind v4 set (evaluation/blind_cases_v4.py -- authored blind after the routing/"
          "severity rewrite, never tuned against) ===")
    print_case_table(results)
    print_summary("Blind v4 summary", results)
