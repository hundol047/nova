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
            + tau   * time_critical_bonus
            - lam   * turn_cost
            - rho   * redundancy
    """

    info_gain_weight: float = field(default_factory=lambda: _float_env("NOVA_INFO_GAIN_WEIGHT", 1.0))
    discrimination_weight: float = field(default_factory=lambda: _float_env("NOVA_DISCRIMINATION_WEIGHT", 1.2))
    safety_weight: float = field(default_factory=lambda: _float_env("NOVA_SAFETY_WEIGHT", 1.5))
    management_relevance_weight: float = field(
        default_factory=lambda: _float_env("NOVA_MANAGEMENT_RELEVANCE_WEIGHT", 0.5)
    )
    # A candidate action that helps discriminate a "time is tissue/brain/myocardium" diagnosis
    # (stroke/ACS/sepsis/anaphylaxis-class -- see action_selector.py's `_time_critical_ids()`)
    # gets a small additional priority bump on top of the existing safety_weight, reflecting that
    # minutes matter more for these specifically than for "merely" dangerous_if_missed diagnoses
    # in general. Deliberately small relative to safety_weight/discrimination_weight -- this
    # breaks a close tie toward the more time-sensitive question, never overrides genuine
    # evidence-based prioritization. Purely a question/test PRIORITIZATION weight -- never
    # triggers or implies any treatment/auto-treatment action.
    time_critical_weight: float = field(default_factory=lambda: _float_env("NOVA_TIME_CRITICAL_WEIGHT", 0.4))
    turn_cost_weight: float = field(default_factory=lambda: _float_env("NOVA_TURN_COST", 0.3))
    redundancy_penalty: float = field(default_factory=lambda: _float_env("NOVA_REDUNDANCY_PENALTY", 5.0))


@dataclass(frozen=True)
class StopPolicyConfig:
    diagnose_threshold: float = field(default_factory=lambda: _float_env("NOVA_DIAGNOSE_THRESHOLD", 0.60))
    min_gap_rank1_rank2: float = field(default_factory=lambda: _float_env("NOVA_MIN_GAP_RANK1_RANK2", 0.18))
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

    # ontology_broadening_enabled: OPT-IN open-world broadening of the candidate pool with Tier-2
    # structured concepts from the DiseaseCatalog (nova_agent/ontology). DEFAULT FALSE so the closed
    # 34-disease behavior — and every existing test/benchmark — is byte-identical unless a deployer
    # turns it on. When true, candidate_generator adds broad ontology candidates ONLY as a thin,
    # provenance-tagged supplement; it never removes a KB candidate and never changes scoring.
    ontology_broadening_enabled: bool = field(
        default_factory=lambda: _bool_env("NOVA_ONTOLOGY_BROADENING", False))
    ontology_broadening_max: int = field(
        default_factory=lambda: _int_env("NOVA_ONTOLOGY_BROADENING_MAX", 5))

    # llm_provider: 'mock' (default, offline/deterministic) | 'anthropic' | 'openai_compatible'
    # (any OpenAI Chat Completions-compatible HTTP endpoint: local vLLM/llama.cpp/ollama, or a
    # hosted API) | 'local' (openai_compatible preset for a local server) | 'competition' (reads
    # the NOVA_COMPETITION_* variables below -- the one to point at whatever runtime the official
    # N.O.V.A. rules specify, without touching code). See nova_agent/llm_client.py.
    llm_provider: str = field(default_factory=lambda: _str_env("NOVA_LLM_PROVIDER", "mock"))
    llm_model: str = field(default_factory=lambda: _str_env("NOVA_LLM_MODEL", "claude-sonnet-5"))
    llm_temperature: float = field(default_factory=lambda: _float_env("NOVA_LLM_TEMPERATURE", 0.0))
    llm_max_retries: int = field(default_factory=lambda: _int_env("NOVA_LLM_MAX_RETRIES", 2))
    llm_timeout_seconds: float = field(default_factory=lambda: _float_env("NOVA_LLM_TIMEOUT_SECONDS", 30.0))
    llm_max_tokens: int = field(default_factory=lambda: _int_env("NOVA_LLM_MAX_TOKENS", 1024))

    # OpenAI-compatible / local runtime settings (provider='openai_compatible' or 'local').
    llm_base_url: str = field(default_factory=lambda: _str_env("NOVA_LLM_BASE_URL", "http://localhost:8000/v1"))
    llm_api_key: str = field(default_factory=lambda: _str_env("NOVA_LLM_API_KEY", ""))

    # Competition runtime settings (provider='competition'). Defaults assume the officially
    # discussed 'openai/gpt-oss-20b' served through an OpenAI-compatible local/offline endpoint;
    # override every one of these from the environment once the official rules are published --
    # nothing else in the codebase needs to change (see CompetitionLLMClient).
    competition_base_url: str = field(
        default_factory=lambda: _str_env("NOVA_COMPETITION_BASE_URL", "http://localhost:8000/v1")
    )
    competition_model: str = field(
        default_factory=lambda: _str_env("NOVA_COMPETITION_MODEL", "openai/gpt-oss-20b")
    )
    competition_api_key: str = field(default_factory=lambda: _str_env("NOVA_COMPETITION_API_KEY", ""))

    # Case-level budget (spec: graceful degradation, not a crash, as a case's time/call budget
    # runs out). Off by default (None) -- no official per-case timeout or call cap has been
    # published, so nothing is enforced unless explicitly configured. When set, orchestrator.py
    # skips RAG retrieval and the real LLM call (using the deterministic action/stop-decision
    # directly) once the budget is exhausted, rather than exceeding it or crashing.
    case_timeout_seconds: float | None = field(
        default_factory=lambda: _float_env("NOVA_CASE_TIMEOUT_SECONDS", 0.0) or None
    )
    max_llm_calls_per_case: int | None = field(
        default_factory=lambda: _int_env("NOVA_MAX_LLM_CALLS", 0) or None
    )

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
