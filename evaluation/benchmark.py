"""Benchmark command (spec section 24): `python -m evaluation.benchmark`

Runs every case in evaluation/cases.py through a fresh DoctorAgent and prints a per-case table
plus summary metrics (diagnostic accuracy, average turns, critical miss rate, duplicate action
rate).
"""

from __future__ import annotations

import argparse
import random

from nova_agent.config import get_config
from nova_agent.orchestrator import DoctorAgent

from evaluation.cases import CASES
from evaluation.simulator import CaseResult, run_case


def run_all(rag_enabled: bool = True) -> list[CaseResult]:
    random.seed(get_config().random_seed)
    agent = DoctorAgent()
    results = []
    for case in CASES:
        results.append(run_case(agent, case))
    return results


def print_report(results: list[CaseResult]) -> None:
    header = f"{'Case':<22}{'Correct':<10}{'Turns':<8}{'Duplicate':<11}{'Critical Miss':<15}"
    print(header)
    print("-" * len(header))
    for r in results:
        print(f"{r.case_id:<22}{('YES' if r.correct else 'NO'):<10}{r.turns:<8}{r.duplicate_actions:<11}"
              f"{('YES' if r.critical_miss else 'NO'):<15}")

    n = len(results) or 1
    accuracy = sum(r.correct for r in results) / n
    avg_turns = sum(r.turns for r in results) / n
    critical_cases = [r for r in results if r.critical]
    critical_miss_rate = (sum(r.critical_miss for r in critical_cases) / len(critical_cases)) if critical_cases else 0.0
    duplicate_rate = sum(r.duplicate_actions for r in results) / n
    malformed_total = sum(r.malformed_turns for r in results)
    failed_diagnose = sum(r.failed_to_diagnose for r in results)
    unnecessary_tests_total = sum(r.unnecessary_tests for r in results)

    print("\nSummary")
    print(f"  Diagnostic Accuracy:      {accuracy * 100:.1f}%")
    print(f"  Average Turns:            {avg_turns:.1f}")
    print(f"  Critical Miss Rate:       {critical_miss_rate * 100:.1f}% ({len(critical_cases)} critical case(s))")
    print(f"  Duplicate Action Rate:    {duplicate_rate:.2f} per case")
    print(f"  Unnecessary Tests:        {unnecessary_tests_total} total")
    print(f"  Malformed LLM Turns:      {malformed_total} total")
    print(f"  Failed to Diagnose:       {failed_diagnose} case(s)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the N.O.V.A. Doctor Agent local benchmark.")
    parser.parse_args()
    results = run_all()
    print_report(results)


if __name__ == "__main__":
    main()
