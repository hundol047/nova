"""Internal utility-score proxy (spec section 18).

No official N.O.V.A. 2026 scoring formula was available at implementation time -- this is NOT
presented as one anywhere in this codebase. It exists only as a local, config-tunable signal for
comparing agent configurations against each other during development (e.g. evaluation/tune.py).
Replace `score_case` the moment an official formula is published; nothing else needs to change
since evaluation/benchmark.py only ever calls this one function.
"""

from __future__ import annotations

from dataclasses import dataclass

from nova_agent.config import get_config

from evaluation.simulator import CaseResult


@dataclass(frozen=True)
class ScoringWeights:
    correct_reward: float = 1.0
    critical_miss_penalty: float = 0.5
    turn_penalty_per_turn: float = 0.01
    unnecessary_test_penalty: float = 0.05
    duplicate_action_penalty: float = 0.1
    malformed_output_penalty: float = 0.1
    failed_diagnosis_penalty: float = 1.0


def _weights_from_config() -> ScoringWeights:
    """Reuses the existing NOVA_* action-utility env vars where a natural mapping exists, so a
    single local benchmark/leaderboard tuning pass can adjust both without two separate knobs;
    falls back to ScoringWeights' defaults for the rest."""
    cfg = get_config()
    return ScoringWeights(
        critical_miss_penalty=cfg.weights.safety_weight / 3.0 if cfg.weights.safety_weight else 0.5,
        turn_penalty_per_turn=cfg.weights.turn_cost_weight / 30.0 if cfg.weights.turn_cost_weight else 0.01,
    )


def score_case(result: CaseResult, weights: ScoringWeights | None = None) -> float:
    """Never an official score -- an explicitly local, informal proxy (see module docstring)."""
    w = weights or _weights_from_config()
    score = w.correct_reward if result.correct else 0.0
    score -= w.turn_penalty_per_turn * result.turns
    score -= w.unnecessary_test_penalty * result.unnecessary_tests
    score -= w.duplicate_action_penalty * result.duplicate_actions
    score -= w.malformed_output_penalty * result.malformed_turns
    if result.critical_miss:
        score -= w.critical_miss_penalty
    if result.failed_to_diagnose:
        score -= w.failed_diagnosis_penalty
    return score
