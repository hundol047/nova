"""Benchmark command (spec section 24): `python -m evaluation.benchmark`

Runs the tuning set (evaluation/cases.py, the 8 cases the current config.py defaults were
iterated against) and, separately, the held-out set (evaluation/held_out_cases.py, never used to
shape any default -- spec section 19/22) through a fresh DoctorAgent and prints per-case tables
plus expanded summary metrics (spec section 21).
"""

from __future__ import annotations

import argparse
import random
import statistics

from nova_agent.config import get_config
from nova_agent.orchestrator import DoctorAgent

from evaluation.cases import CASES
from evaluation.held_out_cases import HELD_OUT_CASES
from evaluation.simulator import CaseResult, run_case


def run_all(cases) -> list[CaseResult]:
    random.seed(get_config().random_seed)
    agent = DoctorAgent()
    return [run_case(agent, case) for case in cases]


def print_case_table(results: list[CaseResult]) -> None:
    header = f"{'Case':<32}{'Category':<22}{'Correct':<10}{'Turns':<8}{'Duplicate':<11}{'Critical Miss':<15}"
    print(header)
    print("-" * len(header))
    for r in results:
        expected_marker = "" if r.scoring_expected else " (not scored)"
        print(f"{r.case_id:<32}{r.category:<22}{(('YES' if r.correct else 'NO') + expected_marker):<10}"
              f"{r.turns:<8}{r.duplicate_actions:<11}{('YES' if r.critical_miss else 'NO'):<15}")


def compute_summary(results: list[CaseResult]) -> dict:
    n = len(results) or 1
    scored = [r for r in results if r.scoring_expected]
    scored_n = len(scored) or 1
    critical_cases = [r for r in results if r.critical]
    turns_list = [r.turns for r in results]

    ask_total = sum(r.ask_count for r in results)
    exam_total = sum(r.exam_count for r in results)
    test_total = sum(r.test_count for r in results)

    # Utility score proxy ONLY (spec section 21: not an official scoring formula -- none has been
    # published at implementation time; replace this the moment one is). Rewards correctness,
    # penalizes turns/unnecessary tests/critical misses.
    utility_proxy = statistics.mean(
        (1.0 if r.correct else 0.0) - 0.01 * r.turns - 0.05 * r.unnecessary_tests
        - (0.5 if r.critical_miss else 0.0)
        for r in results
    )

    return {
        "diagnostic_accuracy": sum(r.correct for r in scored) / scored_n,
        "critical_diagnosis_recall": (
            sum(1 for r in critical_cases if r.correct) / len(critical_cases) if critical_cases else None
        ),
        "critical_miss_rate": (
            sum(r.critical_miss for r in critical_cases) / len(critical_cases) if critical_cases else 0.0
        ),
        "average_turns": statistics.mean(turns_list) if turns_list else 0.0,
        "median_turns": statistics.median(turns_list) if turns_list else 0.0,
        "duplicate_action_rate": sum(r.duplicate_actions for r in results) / n,
        "unnecessary_test_rate": sum(r.unnecessary_tests for r in results) / n,
        "malformed_output_rate": sum(r.malformed_turns for r in results) / n,
        "failed_diagnosis_rate": sum(r.failed_to_diagnose for r in results) / n,
        "fallback_rate": sum(r.malformed_turns for r in results) / n,  # see module docstring caveat below
        "average_ask_count": ask_total / n,
        "average_exam_count": exam_total / n,
        "average_test_count": test_total / n,
        "utility_score_proxy": utility_proxy,
        "n_cases": len(results),
        "n_scored_cases": len(scored),
        "n_critical_cases": len(critical_cases),
    }


def print_summary(title: str, results: list[CaseResult]) -> None:
    s = compute_summary(results)
    print(f"\n{title} ({s['n_cases']} cases, {s['n_scored_cases']} scored, {s['n_critical_cases']} critical)")
    print(f"  Diagnostic Accuracy:      {s['diagnostic_accuracy'] * 100:.1f}%")
    if s["critical_diagnosis_recall"] is not None:
        print(f"  Critical Diagnosis Recall:{s['critical_diagnosis_recall'] * 100:.1f}%")
    print(f"  Critical Miss Rate:       {s['critical_miss_rate'] * 100:.1f}%")
    print(f"  Average / Median Turns:   {s['average_turns']:.1f} / {s['median_turns']:.1f}")
    print(f"  Duplicate Action Rate:    {s['duplicate_action_rate']:.2f} per case")
    print(f"  Unnecessary Test Rate:    {s['unnecessary_test_rate']:.2f} per case")
    print(f"  Malformed Output Rate:    {s['malformed_output_rate']:.2f} per case")
    print(f"  Failed Diagnosis Rate:    {s['failed_diagnosis_rate'] * 100:.1f}%")
    print(f"  Avg ASK / EXAM / TEST:    {s['average_ask_count']:.1f} / {s['average_exam_count']:.1f} / "
          f"{s['average_test_count']:.1f}")
    print(f"  Utility Score Proxy:      {s['utility_score_proxy']:.3f}  "
          f"(informal local metric -- see module docstring; not an official competition score)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the N.O.V.A. Doctor Agent local benchmark.")
    parser.add_argument("--held-out-only", action="store_true", help="Skip the tuning set.")
    parser.add_argument("--tuning-only", action="store_true", help="Skip the held-out set.")
    args = parser.parse_args()

    if not args.held_out_only:
        tuning_results = run_all(CASES)
        print("=== Tuning set (evaluation/cases.py) ===")
        print_case_table(tuning_results)
        print_summary("Tuning set summary", tuning_results)

    if not args.tuning_only:
        held_out_results = run_all(HELD_OUT_CASES)
        print("\n=== Held-out set (evaluation/held_out_cases.py -- never used to tune defaults) ===")
        print_case_table(held_out_results)
        print_summary("Held-out set summary", held_out_results)


if __name__ == "__main__":
    main()
