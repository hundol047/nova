"""Historical synthetic runner. This set is reused development data after follow-up
error analysis; the original case files and manifests remain unchanged.
"""

from __future__ import annotations

from evaluation.benchmark import print_case_table, print_summary, run_all
from evaluation.blind_cases_v3 import BLIND_CASES_V3

if __name__ == "__main__":
    results = run_all(BLIND_CASES_V3)
    print("=== Blind v3 set (evaluation/blind_cases_v3.py -- authored blind, used for development) ===")
    print_case_table(results)
    print_summary("V3 development summary", results)
