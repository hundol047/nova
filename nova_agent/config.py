"""Central configuration for the N.O.V.A. Doctor Agent.

All tunable weights and thresholds live here (never hardcoded in the
reasoning modules) so they can be adjusted from local benchmark /
leaderboard feedback without touching engine code. Every value can be
overridden with an environment variable so deployment behavior can change
without a code change.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _str_env(name: str, default: str) -> str:
    raw = os.environ.get(name)
    return raw if raw not in (None, "") else default


@dataclass(frozen=True)
class UtilityWeights:
    """Weights for the action-selection utility function.

    utility = alpha * information_gain
            + beta  * diagnostic_separation
            + gamma * safety_gain
            + delta * expected_management_relevance
            - lam   * turn_cost
            - rho   * redundancy
    """

    info_gain_weight: float = field(default_factory=lambda: _float_env("NOVA_INFO_GAIN_WEIGHT", 1.0))
    discrimination_weight: float = field(default_factory=lambda: _float_env("NOVA_DISCRIMINATION_WEIGHT", 1.2))
    safety_weight: float = field(default_factory=lambda: _float_env("NOVA_SAFETY_WEIGHT", 1.5))
    management_relevance_weight: float = field(
        default_factory=lambda: _float_env("NOVA_MANAGEMENT_RELEVANCE_WEIGHT", 0.5)
    )
    turn_cost_weight: float = field(default_factory=lambda: _float_env("NOVA_TURN_COST", 0.3))
    redundancy_penalty: float = field(default_factory=lambda: _float_env("NOVA_REDUNDANCY_PENALTY", 5.0))


@dataclass(frozen=True)
class StopPolicyConfig:
    diagnose_threshold: float = field(default_factory=lambda: _float_env("NOVA_DIAGNOSE_THRESHOLD", 0.72))
    min_gap_rank1_rank2: float = field(default_factory=lambda: _float_env("NOVA_MIN_GAP_RANK1_RANK2", 0.22))
    forced_diagnose_remaining_turns: int = field(
        default_factory=lambda: _int_env("NOVA_FORCED_DIAGNOSE_REMAINING_TURNS", 3)
    )
    min_turns_before_diagnose: int = field(default_factory=lambda: _int_env("NOVA_MIN_TURNS_BEFORE_DIAGNOSE", 2))
    min_evidence_items: int = field(default_factory=lambda: _int_env("NOVA_MIN_EVIDENCE_ITEMS", 2))


@dataclass(frozen=True)
class NovaConfig:
    max_turns: int = field(default_factory=lambda: _int_env("NOVA_MAX_TURNS", 60))
    top_k_differential: int = field(default_factory=lambda: _int_env("NOVA_TOP_K_DIFFERENTIAL", 5))
    candidate_pool_size: int = field(default_factory=lambda: _int_env("NOVA_CANDIDATE_POOL_SIZE", 8))

    rag_enabled: bool = field(default_factory=lambda: _bool_env("NOVA_RAG_ENABLED", True))
    rag_top_k: int = field(default_factory=lambda: _int_env("NOVA_RAG_TOP_K", 4))

    llm_provider: str = field(default_factory=lambda: _str_env("NOVA_LLM_PROVIDER", "mock"))
    llm_model: str = field(default_factory=lambda: _str_env("NOVA_LLM_MODEL", "claude-sonnet-5"))
    llm_temperature: float = field(default_factory=lambda: _float_env("NOVA_LLM_TEMPERATURE", 0.0))
    llm_max_retries: int = field(default_factory=lambda: _int_env("NOVA_LLM_MAX_RETRIES", 2))
    llm_timeout_seconds: float = field(default_factory=lambda: _float_env("NOVA_LLM_TIMEOUT_SECONDS", 30.0))

    random_seed: int = field(default_factory=lambda: _int_env("NOVA_RANDOM_SEED", 42))

    weights: UtilityWeights = field(default_factory=UtilityWeights)
    stop_policy: StopPolicyConfig = field(default_factory=StopPolicyConfig)

    knowledge_dir: str = field(
        default_factory=lambda: _str_env(
            "NOVA_KNOWLEDGE_DIR", os.path.join(os.path.dirname(__file__), "knowledge")
        )
    )


_config: NovaConfig | None = None


def get_config(reload: bool = False) -> NovaConfig:
    """Return the process-wide config, loading it lazily from the environment."""
    global _config
    if _config is None or reload:
        _config = NovaConfig()
    return _config
