"""`python -m evaluation.blind_benchmark_v5` -- runs evaluation/blind_cases_v5.py, the untouched
final generalization check for this session's structural rewrite (chief-complaint confidence
routing, diagnostic/severity score separation, safety_priority). See that module's docstring for
the authoring rules that keep it blind, and evaluation/blind_v5_manifest.json for the file hash
recorded at freeze time, before this runner was ever executed.

Deliberately NOT wired into evaluation/benchmark.py's --save-json output or CI's regression gate,
same as blind_benchmark.py/blind_benchmark_v4.py: this set stays a one-shot honesty check, never a
target a later session tunes against. Its first real result is reported as-is -- never silently
re-run-and-cherry-picked, never used to justify reverting or adjusting a case after the fact.
"""

from __future__ import annotations

from evaluation.benchmark import print_case_table, print_summary, run_all
from evaluation.blind_cases_v5 import BLIND_CASES_V5

if __name__ == "__main__":
    results = run_all(BLIND_CASES_V5)
    print("=== Blind v5 set (evaluation/blind_cases_v5.py -- the untouched final generalization "
          "check for this round's routing/severity/safety_priority rewrite, never tuned against) ===")
    print_case_table(results)
    print_summary("Blind v5 summary", results)
