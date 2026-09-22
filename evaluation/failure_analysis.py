"""Automated miss/critical-miss root-cause classification (spec section 9): `python -m
evaluation.failure_analysis`.

Runs the held-out set (never used to tune any default) with per-turn trajectory capture and, for
every case that isn't correct, prints a structured evidence summary (top-5 differential trajectory,
actions taken, evidence count, miss category tags) -- never a private chain-of-thought, only
already-computed structured state. Classification is rule-based over that structured state (not a
guess), and deliberately leaves an "uncategorized" bucket rather than force-fitting every miss into
a category the available signals can't actually support (e.g. distinguishing a negation-parsing
bug from a genuinely ambiguous case needs a human to read the transcript -- this script points at
where to look, it doesn't claim to diagnose the bug itself).
"""

from __future__ import annotations

import random
from typing import List

from nova_agent.chief_complaint import classify as classify_chief_complaint
from nova_agent.config import get_config
from nova_agent.diagnosis_normalizer import normalize_diagnosis, same_diagnosis
from nova_agent.knowledge.retrieval import disease_by_id
from nova_agent.orchestrator import DoctorAgent

from evaluation.held_out_cases import HELD_OUT_CASES
from evaluation.simulator import CaseResult, run_case


def _appears_in_trajectory(diagnosis_id: str, result: CaseResult) -> bool:
    return any(
        any(same_diagnosis(name, diagnosis_id) for name in turn["top5_differential"])
        for turn in result.differential_trajectory
    )


def _appears_at_rank1(diagnosis_id: str, result: CaseResult) -> bool:
    return any(
        turn["top5_differential"] and same_diagnosis(turn["top5_differential"][0], diagnosis_id)
        for turn in result.differential_trajectory
    )


def classify_miss(case, result: CaseResult) -> List[str]:
    """Returns applicable root-cause category tags (not mutually exclusive). Empty if `result` was
    actually correct (nothing to classify)."""
    if result.correct:
        return []

    tags: List[str] = []
    gt_id = case.ground_truth_diagnosis
    gt_entry = disease_by_id(gt_id)
    tag = classify_chief_complaint(case.chief_complaint)

    if not case.scoring_expected:
        tags.append("excluded_from_scoring_stress_case")

    if result.final_diagnosis is None:
        tags.append("failed_to_diagnose")

    if gt_entry and tag not in gt_entry.get("chief_complaint_tags", []):
        tags.append("wrong_chief_complaint_classification")

    ever_present = _appears_in_trajectory(gt_id, result)
    if not ever_present:
        tags.append("missing_differential")
    elif not _appears_at_rank1(gt_id, result):
        tags.append("wrong_ranking")

    if case.critical and not ever_present:
        tags.append("missing_dangerous_diagnosis")

    if result.unnecessary_tests > 0:
        tags.append("unnecessary_workup")

    cfg = get_config().stop_policy
    if result.turns <= cfg.min_turns_before_diagnose + 1 and result.final_diagnosis is not None:
        tags.append("premature_diagnosis")
    if result.turns >= get_config().max_turns - get_config().stop_policy.forced_diagnose_remaining_turns - 1:
        tags.append("late_diagnosis_forced_by_turn_limit")

    if result.malformed_turns > 0:
        tags.append("llm_output_malformed_or_hallucinated")

    if result.final_diagnosis is not None and not normalize_diagnosis(result.final_diagnosis).mapped:
        tags.append("normalization_error_unmapped_final_diagnosis")

    if not tags or tags == ["excluded_from_scoring_stress_case"]:
        tags.append("uncategorized_needs_manual_review")

    return tags


def main() -> None:
    random.seed(get_config().random_seed)
    agent = DoctorAgent()
    results = [run_case(agent, case, capture_trajectory=True) for case in HELD_OUT_CASES]

    misses = [(case, r) for case, r in zip(HELD_OUT_CASES, results) if not r.correct]
    print(f"=== Failure analysis: {len(misses)}/{len(results)} held-out case(s) not correct ===\n")

    for case, result in misses:
        tags = classify_miss(case, result)
        print(f"--- {case.case_id} ({case.category}) ---")
        print(f"  Ground truth:        {case.ground_truth_diagnosis}")
        print(f"  Final diagnosis:     {result.final_diagnosis!r}")
        print(f"  Critical / Miss:     {result.critical} / {result.critical_miss}")
        print(f"  Turns:               {result.turns}")
        print(f"  Unnecessary tests:   {result.unnecessary_tests}")
        print(f"  Miss categories:     {', '.join(tags)}")
        if result.differential_trajectory:
            last = result.differential_trajectory[-1]
            print(f"  Final top-5:         {last['top5_differential']}")
            actions = [t["action"] for t in result.differential_trajectory]
            print(f"  Actions taken:       {actions}")
        print()

    if not misses:
        print("No misses in the held-out set on this run.")


if __name__ == "__main__":
    main()
