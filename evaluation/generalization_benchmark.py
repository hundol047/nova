"""`python -m evaluation.generalization_benchmark` -- thin alias for
`python -m evaluation.benchmark --generalization-v2`, matching the exact command name the task
spec listed. No separate logic: reuses evaluation/benchmark.py's runner/printer so there is only
one implementation of "run a case set and print its summary" to maintain.
"""

from __future__ import annotations

from evaluation.benchmark import print_case_table, print_summary, run_all
from evaluation.generalization_cases_v2 import GENERALIZATION_CASES_V2

if __name__ == "__main__":
    results = run_all(GENERALIZATION_CASES_V2)
    print("=== Generalization v2 set (evaluation/generalization_cases_v2.py) ===")
    print_case_table(results)
    print_summary("Generalization v2 summary", results)
