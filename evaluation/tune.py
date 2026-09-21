"""Calibration / parameter search (spec section 22): `python -m evaluation.tune`

Explores nova_agent/config.py's tunable weights against the TUNING set only (evaluation/cases.py)
-- never the held-out set, which exists specifically to measure generalization independent of
whatever this script recommends. This script only prints a ranked table of configurations and
their tuning-set metrics; it does NOT write config.py or hardcode any answer to make a specific
case pass -- a human decides whether to adopt a suggested weight change, same as the existing
defaults were arrived at.

    python -m evaluation.tune                 # small built-in grid
    python -m evaluation.tune --random 20      # 20 random samples instead
"""

from __future__ import annotations

import argparse
import random
import statistics
from dataclasses import dataclass

import nova_agent.config as config_module
from nova_agent.config import NovaConfig, StopPolicyConfig, UtilityWeights, get_config
from nova_agent.orchestrator import DoctorAgent

from evaluation.cases import CASES
from evaluation.simulator import run_case


@dataclass
class TrialResult:
    diagnose_threshold: float
    safety_weight: float
    info_gain_weight: float
    accuracy: float
    avg_turns: float
    critical_miss_rate: float


def _run_trial(diagnose_threshold: float, safety_weight: float, info_gain_weight: float) -> TrialResult:
    base = get_config()
    weights = UtilityWeights(
        info_gain_weight=info_gain_weight, discrimination_weight=base.weights.discrimination_weight,
        safety_weight=safety_weight, management_relevance_weight=base.weights.management_relevance_weight,
        turn_cost_weight=base.weights.turn_cost_weight, redundancy_penalty=base.weights.redundancy_penalty,
    )
    stop_policy = StopPolicyConfig(
        diagnose_threshold=diagnose_threshold, min_gap_rank1_rank2=base.stop_policy.min_gap_rank1_rank2,
        forced_diagnose_remaining_turns=base.stop_policy.forced_diagnose_remaining_turns,
        min_turns_before_diagnose=base.stop_policy.min_turns_before_diagnose,
        min_evidence_items=base.stop_policy.min_evidence_items,
    )
    trial_config = NovaConfig(max_turns=base.max_turns, weights=weights, stop_policy=stop_policy)

    original = config_module._config
    config_module._config = trial_config
    try:
        agent = DoctorAgent()
        results = [run_case(agent, case) for case in CASES]
    finally:
        config_module._config = original

    n = len(results) or 1
    critical = [r for r in results if r.critical]
    return TrialResult(
        diagnose_threshold=diagnose_threshold, safety_weight=safety_weight, info_gain_weight=info_gain_weight,
        accuracy=sum(r.correct for r in results) / n,
        avg_turns=statistics.mean(r.turns for r in results),
        critical_miss_rate=(sum(r.critical_miss for r in critical) / len(critical)) if critical else 0.0,
    )


def grid_search() -> list[TrialResult]:
    thresholds = [0.5, 0.6, 0.7]
    safety_weights = [1.0, 1.5, 2.0]
    info_gain_weights = [0.7, 1.0, 1.3]
    return [_run_trial(t, s, i) for t in thresholds for s in safety_weights for i in info_gain_weights]


def random_search(n: int, seed: int = 42) -> list[TrialResult]:
    rng = random.Random(seed)
    trials = []
    for _ in range(n):
        t = round(rng.uniform(0.4, 0.8), 2)
        s = round(rng.uniform(0.5, 2.5), 2)
        i = round(rng.uniform(0.5, 2.0), 2)
        trials.append(_run_trial(t, s, i))
    return trials


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--random", type=int, default=0, help="Use N random samples instead of the built-in grid.")
    args = parser.parse_args()

    trials = random_search(args.random) if args.random else grid_search()
    # Prioritize zero critical misses, then accuracy, then fewer turns -- never accuracy alone
    # (spec: safety first).
    trials.sort(key=lambda t: (t.critical_miss_rate, -t.accuracy, t.avg_turns))

    header = f"{'threshold':<12}{'safety_w':<11}{'info_gain_w':<13}{'accuracy':<11}{'avg_turns':<11}{'crit_miss':<10}"
    print(header)
    print("-" * len(header))
    for t in trials[:15]:
        print(f"{t.diagnose_threshold:<12}{t.safety_weight:<11}{t.info_gain_weight:<13}"
              f"{t.accuracy * 100:>7.1f}%   {t.avg_turns:>7.1f}   {t.critical_miss_rate * 100:>6.1f}%")

    best = trials[0]
    print(f"\nBest on the TUNING set only: diagnose_threshold={best.diagnose_threshold}, "
          f"safety_weight={best.safety_weight}, info_gain_weight={best.info_gain_weight} "
          f"(accuracy={best.accuracy * 100:.1f}%, avg_turns={best.avg_turns:.1f}, "
          f"critical_miss_rate={best.critical_miss_rate * 100:.1f}%)")
    print("Re-run `python -m evaluation.benchmark` on the HELD-OUT set before adopting any change "
          "-- this script never validates generalization on its own.")


if __name__ == "__main__":
    main()
