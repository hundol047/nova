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
from pathlib import Path

from nova_agent.config import get_config
from nova_agent.orchestrator import DoctorAgent

from evaluation.cases import CASES
from evaluation.generalization_cases_v2 import GENERALIZATION_CASES_V2
from evaluation.generalization_stress_cases import GENERALIZATION_STRESS_CASES
from evaluation.held_out_cases import HELD_OUT_CASES
from evaluation.scoring import score_case
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
    """Spec section 17: every metric is reported together, and which cases are excluded from which
    denominator is always named explicitly -- never silently drop hard cases just to inflate one
    headline accuracy number."""
    n = len(results) or 1
    scored = [r for r in results if r.scoring_expected]
    unsupported = [r for r in results if not r.scoring_expected]
    scored_n = len(scored) or 1
    critical_cases = [r for r in results if r.critical]
    turns_list = [r.turns for r in results]

    ask_total = sum(r.ask_count for r in results)
    exam_total = sum(r.exam_count for r in results)
    test_total = sum(r.test_count for r in results)

    utility_proxy = statistics.mean(score_case(r) for r in results)

    return {
        # Scored: only cases with a well-defined single right answer (excludes ambiguous/
        # insufficient-info/unmapped-complaint stress cases -- see each case's `scoring_expected`).
        "scored_diagnostic_accuracy": sum(r.correct for r in scored) / scored_n,
        # All-case: the SAME correctness check applied to every case, unscored ones included, so
        # inflating the headline number by excluding hard cases is never possible to hide.
        "all_case_diagnostic_accuracy": sum(r.correct for r in results) / n,
        "unscored_case_names": [r.case_id for r in unsupported],
        # Unsupported (excluded-from-scoring) cases: not "correct/incorrect" (no single right
        # answer), but still checked for safe handling -- reached a diagnosis, no critical miss.
        "unsupported_case_success_rate": (
            sum(1 for r in unsupported if not r.failed_to_diagnose and not r.critical_miss) / len(unsupported)
            if unsupported else None
        ),
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
        # Real per-call fallback rate (llm_fallback_count / llm_call_count, aggregated across every
        # case), distinct from malformed_output_rate above -- a malformed turn is a structured-
        # output PARSE failure on an otherwise-successful call; a fallback is "no usable real-LLM
        # output at all this turn" (network error, timeout, exhausted retries, or the call was
        # never attempted). state.py only increments llm_call_count when a real provider actually
        # attempted a call (see orchestrator.py) -- under the default `mock` provider no case ever
        # makes one, so the denominator is 0 for every case and this is correctly reported as None
        # (never fabricated as 0%, which would misleadingly read as "verified zero fallbacks").
        "fallback_rate": (
            sum(r.llm_fallback_count for r in results) / sum(r.llm_call_count for r in results)
            if sum(r.llm_call_count for r in results) else None
        ),
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
    print(f"  Scored Diagnostic Accuracy:   {s['scored_diagnostic_accuracy'] * 100:.1f}%  "
          f"(excludes: {', '.join(s['unscored_case_names']) or 'none'})")
    print(f"  All-Case Diagnostic Accuracy: {s['all_case_diagnostic_accuracy'] * 100:.1f}%  (every case, no exclusions)")
    if s["unsupported_case_success_rate"] is not None:
        print(f"  Unsupported-Case Success Rate:{s['unsupported_case_success_rate'] * 100:.1f}%  "
              f"(safe handling of excluded cases: diagnosed, no critical miss)")
    if s["critical_diagnosis_recall"] is not None:
        print(f"  Critical Diagnosis Recall:    {s['critical_diagnosis_recall'] * 100:.1f}%")
    print(f"  Critical Miss Rate:           {s['critical_miss_rate'] * 100:.1f}%")
    print(f"  Average / Median Turns:       {s['average_turns']:.1f} / {s['median_turns']:.1f}")
    print(f"  Duplicate Action Rate:        {s['duplicate_action_rate']:.2f} per case")
    print(f"  Unnecessary Test Rate:        {s['unnecessary_test_rate']:.2f} per case")
    print(f"  Malformed Output Rate:        {s['malformed_output_rate']:.2f} per case")
    fallback_display = "NOT MEANINGFUL (0 real LLM calls -- mock provider)" if s["fallback_rate"] is None \
        else f"{s['fallback_rate'] * 100:.1f}%"
    print(f"  Real-LLM Fallback Rate:       {fallback_display}")
    print(f"  Failed Diagnosis Rate:        {s['failed_diagnosis_rate'] * 100:.1f}%")
    print(f"  Avg ASK / EXAM / TEST:        {s['average_ask_count']:.1f} / {s['average_exam_count']:.1f} / "
          f"{s['average_test_count']:.1f}")
    print(f"  Utility Score Proxy:          {s['utility_score_proxy']:.3f}  "
          f"(informal local metric, evaluation/scoring.py -- not an official competition score)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the N.O.V.A. Doctor Agent local benchmark.")
    parser.add_argument("--held-out-only", action="store_true", help="Skip the tuning set.")
    parser.add_argument("--tuning-only", action="store_true", help="Skip the held-out set.")
    parser.add_argument("--generalization-v2", action="store_true",
                         help="Also run evaluation/generalization_cases_v2.py (a second, "
                              "independent held-out-style set -- never used to tune any default).")
    parser.add_argument("--stress", action="store_true",
                         help="Also run evaluation/generalization_stress_cases.py (spec section "
                              "17-18: a small, targeted set probing the two known generalization "
                              "miss patterns from both directions -- run only after held-out and "
                              "generalization-v2 both stay clean).")
    parser.add_argument("--save-json", default=None,
                         help="Write each run set's compute_summary() output to this path (spec "
                              "section 25: a single generated source of truth for benchmark "
                              "numbers, so README.md never carries a stale hand-typed figure). "
                              "Implies --generalization-v2.")
    args = parser.parse_args()
    results_for_json: dict = {}

    if not args.held_out_only:
        tuning_results = run_all(CASES)
        print("=== Tuning set (evaluation/cases.py) ===")
        print_case_table(tuning_results)
        print_summary("Tuning set summary", tuning_results)
        results_for_json["tuning"] = compute_summary(tuning_results)

    if not args.tuning_only:
        held_out_results = run_all(HELD_OUT_CASES)
        print("\n=== Held-out set (evaluation/held_out_cases.py -- never used to tune defaults) ===")
        print_case_table(held_out_results)
        print_summary("Held-out set summary", held_out_results)
        results_for_json["held_out"] = compute_summary(held_out_results)

    if args.generalization_v2 or args.save_json:
        v2_results = run_all(GENERALIZATION_CASES_V2)
        print("\n=== Generalization v2 set (evaluation/generalization_cases_v2.py -- never used to tune defaults) ===")
        print_case_table(v2_results)
        print_summary("Generalization v2 summary", v2_results)
        results_for_json["generalization_v2"] = compute_summary(v2_results)

    if args.stress:
        stress_results = run_all(GENERALIZATION_STRESS_CASES)
        print("\n=== Stress set (evaluation/generalization_stress_cases.py -- targeted probes of the "
              "two known miss patterns) ===")
        print_case_table(stress_results)
        print_summary("Stress set summary", stress_results)
        results_for_json["stress"] = compute_summary(stress_results)

    if args.save_json:
        import json

        Path(args.save_json).write_text(json.dumps(results_for_json, indent=2), encoding="utf-8")
        print(f"\nWrote {args.save_json}")


if __name__ == "__main__":
    main()
