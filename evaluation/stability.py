"""Determinism / run-to-run stability harness (spec section 22): `python -m evaluation.stability
--runs 5`.

Runs each case multiple times and measures final-diagnosis agreement, per-turn action-sequence
agreement, and turn-count variance. Under the default `mock` provider this is a sanity check (mock
is a deterministic closed-form function of state, so 100% agreement / zero variance is expected and
required -- any deviation would itself be a bug). Against a real LLM provider, this is what
actually measures reproducibility (spec: config temperature/seed/max_tokens as low/fixed as the
endpoint supports, but never force a seed parameter an endpoint doesn't accept -- see
nova_agent/config.py's llm_temperature, already defaulted to 0.0).
"""

from __future__ import annotations

import argparse
import statistics
from collections import Counter

from nova_agent.config import get_config
from nova_agent.orchestrator import DoctorAgent

from evaluation.held_out_cases import HELD_OUT_CASES
from evaluation.simulator import run_case


def _action_sequence(result) -> tuple:
    return tuple(t["action"] for t in result.differential_trajectory)


def run_stability(cases, runs: int) -> list:
    rows = []
    for case in cases:
        per_run = []
        for _ in range(runs):
            agent = DoctorAgent()  # fresh agent per run -- no cross-run state leakage
            per_run.append(run_case(agent, case, capture_trajectory=True))

        diagnoses = Counter(r.final_diagnosis for r in per_run)
        diagnosis_agreement = diagnoses.most_common(1)[0][1] / runs

        sequences = Counter(_action_sequence(r) for r in per_run)
        action_agreement = sequences.most_common(1)[0][1] / runs

        turns = [r.turns for r in per_run]
        turn_variance = statistics.pvariance(turns) if len(turns) > 1 else 0.0

        rows.append({
            "case_id": case.case_id,
            "diagnosis_agreement": diagnosis_agreement,
            "distinct_diagnoses": len(diagnoses),
            "action_agreement": action_agreement,
            "distinct_action_sequences": len(sequences),
            "turns": turns,
            "turn_variance": turn_variance,
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", type=int, default=5, help="Number of repeated runs per case.")
    parser.add_argument("--cases", type=int, default=6, help="How many held-out cases to check (default: first 6).")
    args = parser.parse_args()

    cfg = get_config()
    print(f"Provider: {cfg.llm_provider} | temperature: {cfg.llm_temperature} | runs/case: {args.runs}\n")

    rows = run_stability(HELD_OUT_CASES[: args.cases], args.runs)
    header = f"{'Case':<32}{'Dx Agreement':<15}{'Action Agreement':<18}{'Turn Variance':<15}{'Turns'}"
    print(header)
    print("-" * len(header))
    for row in rows:
        print(f"{row['case_id']:<32}{row['diagnosis_agreement'] * 100:>6.1f}%       "
              f"{row['action_agreement'] * 100:>6.1f}%           {row['turn_variance']:<15.2f}{row['turns']}")

    n = len(rows) or 1
    avg_dx_agreement = sum(r["diagnosis_agreement"] for r in rows) / n
    avg_action_agreement = sum(r["action_agreement"] for r in rows) / n
    unstable = [r for r in rows if r["diagnosis_agreement"] < 1.0]
    print(f"\nAverage final-diagnosis agreement: {avg_dx_agreement * 100:.1f}%")
    print(f"Average action-sequence agreement: {avg_action_agreement * 100:.1f}%")
    if unstable:
        print(f"WARNING: {len(unstable)} case(s) produced a different final diagnosis across "
              f"repeated runs: {[r['case_id'] for r in unstable]}")
    else:
        print("All cases reached the same final diagnosis on every run.")


if __name__ == "__main__":
    main()
