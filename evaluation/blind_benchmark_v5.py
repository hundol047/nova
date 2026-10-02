"""Legacy V5 runner. As of the accuracy revision, V5 is development data, not blind.
The original case file and freeze manifest remain unchanged for historical provenance.
"""

from __future__ import annotations

from evaluation.benchmark import print_case_table, print_summary, run_all
from evaluation.blind_cases_v5 import BLIND_CASES_V5

if __name__ == "__main__":
    results = run_all(BLIND_CASES_V5)
    print("=== V5 development set (reused; not blind) ===")
    print_case_table(results)
    print_summary("Blind v5 summary", results)
