"""Central configuration for the N.O.V.A. Doctor Agent.

All tunable weights and thresholds live here (never hardcoded in the
reasoning modules) so they can be adjusted from local benchmark /
leaderboard feedback without touching engine code. Every value can be
overridden with an environment variable so deployment behavior can change
without a code change.
"""

from __future__ import annotations

# Official rules checked 2026-10-03: https://nova.snubhai.org/rules/
EXPECTED_COMPETITION_MODEL = "openai/gpt-oss-20b"
EXPECTED_COMPETITION_REVISION = "4d7ae4984b7db7de8f8457170b3f1a419ee76d52"

import os
from dataclasses import dataclass, field


# Preliminary-round limits from the organizer briefing of 2026-10-06 (opening ceremony slides,
# supplied by the team): at most 50 turns and 20 minutes per case; DIAGNOSE costs no turn.
PRELIMINARY_MAX_TURNS = 50
PRELIMINARY_CASE_SECONDS = 20 * 60
# Fraction of the wall-clock limit after which the agent stops gathering and submits its diagnosis
# (leaves headroom for the final SOAP submission and for model latency on the last turn).
PRELIMINARY_TIME_SAFETY_FRACTION = 0.85
# Adaptive guard on top of the fixed fraction: with the MEASURED seconds per turn (model + environment
# latency), force the diagnosis as soon as the closing dialogue (history top-up, diagnosis and next-step
# SAY, DIAGNOSE) would no longer fit; PRELIMINARY_CLOSING_TURNS turns at 1.5x the average, inside 97%.
PRELIMINARY_CLOSING_TURNS = 4
PRELIMINARY_TIME_HARD_FRACTION = 0.97
# Real-model calls per case in the preliminary round: an INTERNAL ENGINEERING BUDGET, NOT an organizer
# requirement. The briefing (as transcribed by the team) says the fixed model is limited to 200 calls and
# 500k input / 100k output tokens per session, that efficiency counts model usage, and that a case with no
# model call scores 0 -- so at least one successful case-relevant call per case is needed. This cap of 8 is the
# team's own sizing so that a session of 10 cases stays inside every transcribed cap: 10 x 8 = 80 calls,
# ~8k characters (~3-4k tokens) of prompt per call (~320k input) and max_tokens=1024 per call (~82k output),
# leaving headroom for retries. Re-derive it when the participant guide states the real session size/limits.
PRELIMINARY_MAX_LLM_CALLS_PER_CASE = 8
# INTERNAL operating policy, not an organizer limit: the cap above counts HTTP REQUESTS (retries included,
# state.llm_http_attempts), because the session caps count requests. Per-case token ceilings are the
# session caps divided by the 10 cases that policy assumes (500k input / 100k output per session).
PRELIMINARY_CASE_INPUT_TOKENS = 50_000
PRELIMINARY_CASE_OUTPUT_TOKENS = 10_000


def effective_max_turns(value, default=60, ceiling=60):
    """Reject non-integral/invalid budgets and enforce the turn ceiling (60 public, 50 preliminary)."""
    def valid(x):
        if isinstance(x, bool): return None
        if isinstance(x, int): return x if x > 0 else None
        if isinstance(x, str) and x.strip().isdigit():
            n = int(x.strip()); return n if n > 0 else None
        return None
    return min(valid(value) or valid(default) or ceiling, ceiling)


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

    top_competitor_weight: float = field(default_factory=lambda: _float_env("NOVA_TOP_COMPETITOR_WEIGHT", 1.2))
    critical_resolution_weight: float = field(default_factory=lambda: _float_env("NOVA_CRITICAL_RESOLUTION_WEIGHT", 0.8))
    specificity_gain_weight: float = field(default_factory=lambda: _float_env("NOVA_SPECIFICITY_GAIN_WEIGHT", 0.5))
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
    focus_resolved_actions: bool = field(default_factory=lambda: _bool_env("NOVA_FOCUS_RESOLVED_ACTIONS", True))

    max_turns: int = field(default_factory=lambda: effective_max_turns(os.environ.get("NOVA_MAX_TURNS")))
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

    # competition_retrieval_enabled: broad, multi-signal open-world retrieval over the SAME
    # DiseaseCatalog (nova_agent/open_world.py's OpenWorldRetriever), rebuilt every turn from the
    # FULL current PatientState (chief complaint + symptoms + PMH/FH/SH + medications + imaging),
    # not just the original chief complaint. Distinct from ontology_broadening_enabled above (which
    # stays untouched, Tier-2-only, single-signal, off by default): this flag also allows Tier-3
    # ontology-only concepts through, and defaults ON when NOVA_LLM_PROVIDER=competition, since a
    # genuinely broad (thousands-of-concepts) differential is the competition's own goal. Any
    # deployer/test can still force it explicitly with NOVA_COMPETITION_RETRIEVAL=true|false
    # regardless of provider. Pure additive supplement -- see candidate_generator._broaden_with_
    # open_world's docstring for the safety/fallback contract.
    # Preliminary-round rules (no TEST action, vitals given at the start, 50 turns / 20 minutes, a
    # bounded number of model calls, SAY <= 30 characters, SOAP note on DIAGNOSE). Default ON only
    # for the competition provider so every development benchmark keeps its behavior.
    preliminary_rules: bool = field(
        default_factory=lambda: _bool_env(
            "NOVA_PRELIMINARY_RULES", _str_env("NOVA_LLM_PROVIDER", "mock") == "competition"
        )
    )
    # Mondo (CC BY 4.0) EXACT synonyms as Tier-2 aliases. OFF by default: measured on the Round M
    # development set it changed no decision (Top1 unchanged) and lowered retrieval@150/rerank@25 by
    # 0.8 points each, so it is shipped as opt-in data (NOVA_MONDO_SYNONYMS=1) rather than active.
    # Disease Ontology (CC0) EXACT synonyms as Tier-2 aliases: also OFF by default. On the Round M development
    # set they changed no decision (Top1 unchanged), and enabling them changes which candidate review
    # entries the frozen, reproducible review datasets screen out (research/diagnosis_expansion), so the
    # integrated release keeps them opt-in (NOVA_OPEN_SYNONYMS=1) rather than silently active.
    open_synonyms_enabled: bool = field(default_factory=lambda: _bool_env("NOVA_OPEN_SYNONYMS", False))
    mondo_synonyms_enabled: bool = field(default_factory=lambda: _bool_env("NOVA_MONDO_SYNONYMS", False))
    # Round N switches (ablation): clinical concept normalisation (nova_agent/clinical_concepts.py) feeding
    # the evidence bag and routing. Default ON; NOVA_CONCEPT_NORMALIZATION=0 reproduces the previous behaviour.
    concept_normalization_enabled: bool = field(default_factory=lambda: _bool_env("NOVA_CONCEPT_NORMALIZATION", True))
    # Round N evidence-interpretation switch: proximity-bounded alias matching, negative beta-hCG as evidence
    # against its pregnancy finding, lying/standing blood-pressure interpretation. NOVA_EVIDENCE_V2=0 disables.
    evidence_v2_enabled: bool = field(default_factory=lambda: _bool_env("NOVA_EVIDENCE_V2", True))
    # Round N action switch: once core history is taken, prefer the outstanding minimum workup of a dangerous
    # diagnosis that is actively blocking the stop (resolves the danger sooner). NOVA_ACTION_V2=0 disables.
    action_v2_enabled: bool = field(default_factory=lambda: _bool_env("NOVA_ACTION_V2", True))
    # Round O switches (ablation). NOVA_ROUTING_V2: fuzzy chief-complaint routing ignores connectives and knows
    # chest-anatomy words; NOVA_CONCEPTS_V2: additional everyday-wording concepts (chest wall, reflux, sepsis).
    routing_v2_enabled: bool = field(default_factory=lambda: _bool_env("NOVA_ROUTING_V2", True))
    concepts_v2_enabled: bool = field(default_factory=lambda: _bool_env("NOVA_CONCEPTS_V2", True))
    # NOVA_LABS_V2: a lab result's bare value with an explicit unit is read as that lab (e.g. "4.6 mmol/L" under
    # the lactate test).
    labs_v2_enabled: bool = field(default_factory=lambda: _bool_env("NOVA_LABS_V2", True))
    # NOVA_STOP_V2: the decisive-lead / mature-low-value stop (with its unchanged dangerous-alternative guards),
    # previously reachable only in competition retrieval mode, also applies in legacy retrieval mode.
    stop_v2_enabled: bool = field(default_factory=lambda: _bool_env("NOVA_STOP_V2", True))
    # NOVA_ESCALATION_PRIORITY: a localized diagnosis's own KB red flag (e.g. hypotension in pyelonephritis), when
    # present and supporting a dangerous systemic diagnosis that lists it (sepsis), ranks that diagnosis above it.
    escalation_priority_enabled: bool = field(default_factory=lambda: _bool_env("NOVA_ESCALATION_PRIORITY", True))
    competition_retrieval_enabled: bool = field(
        default_factory=lambda: _bool_env(
            "NOVA_COMPETITION_RETRIEVAL", _str_env("NOVA_LLM_PROVIDER", "mock") == "competition"
        )
    )

    # Round E: whether the (still-unofficial, see competition/schema.py's own PLACEHOLDER
    # disclosure) competition protocol accepts an explicit "we don't know" final result distinct
    # from an ordinary DIAGNOSE. No official N.O.V.A. 2026 schema confirms this either way at
    # implementation time, so this defaults to False (obey the existing forced-final-diagnosis
    # contract: a DIAGNOSE is always eventually produced, per stop_policy.py's own hard turn-limit
    # guarantee) -- never assumed/invented. competition/adapter.py's action_to_competition() only
    # ever emits action_type="INSUFFICIENT_INFORMATION" (competition/schema.py's own, equally
    # optional, addition to the wire enum) when this is explicitly set True AND the diagnosis being
    # returned is genuinely a forced/zero-evidence one (PatientState.final_diagnosis_zero_evidence_
    # at_diagnosis or .final_diagnosis_fallback_candidate_selected) -- never for an ordinary,
    # evidence-backed diagnosis. Regardless of this flag, the underlying reasoning/turn-count
    # behavior is completely unchanged; only the WIRE label differs.
    competition_supports_insufficient_information: bool = field(
        default_factory=lambda: _bool_env("NOVA_COMPETITION_SUPPORTS_INSUFFICIENT_INFO", False)
    )

    # Three DISTINCT stage sizes of the competition retrieval pipeline (nova_agent/retrieval_
    # pipeline.py) -- deliberately not one shared number, since each stage has a different job:
    #   retrieval_top_k  (Stage 1, recommended 100-200): how many catalog hits high-recall
    #                     retrieval pulls. Large on purpose -- a true long-tail diagnosis needs
    #                     room to survive before anything narrows the pool.
    #   rerank_top_k     (Stage 2/3, recommended 20-30): how many of those survive the lightweight
    #                     deterministic reranker (+ mandatory dangerous-concept reinjection) before
    #                     being added to this turn's candidate pool.
    #   reasoning_top_k  (recommended 20-30): how large the FINAL active clinical differential
    #                     (deterministic KB pool + reranked ontology candidates, see differential.py
    #                     `effective_differential_top_k()`) is allowed to be -- this is what
    #                     actually reaches the LLM context, replacing the legacy fixed
    #                     top_k_differential=5 cap ONLY when competition_retrieval_enabled is True,
    #                     so the change never affects the mock/legacy/non-retrieval path.
    # Retrieval/rerank are only consulted when competition_retrieval_enabled is True.
    retrieval_top_k: int = field(default_factory=lambda: _int_env("NOVA_RETRIEVAL_TOP_K", 150))
    rerank_top_k: int = field(default_factory=lambda: _int_env("NOVA_RERANK_TOP_K", 25))
    reasoning_top_k: int = field(default_factory=lambda: _int_env("NOVA_REASONING_TOP_K", 25))

    # --- Optional ML ranker (HOSPITAL deployment only; NEVER in the competition submission) ------
    # ml_ranker_enabled: master switch for the optional deep-learning candidate ranker. DEFAULT
    # FALSE. When false the ML subsystem is never consulted and behavior is unchanged.
    # ml_shadow_mode: when true (default), the ML ranker runs in SHADOW — its ordering is computed
    # and audited but NEVER changes the clinician-facing result. Active (non-shadow) mode requires
    # BOTH ml_ranker_enabled=true AND ml_shadow_mode=false AND an approved model, and even then the
    # deterministic Safety Guard remains authoritative (Safety Guard > ML Ranker > LLM).
    # ml_model_path: filesystem path to an approved checkpoint (.pt + .json sidecar). Empty => no model.
    ml_ranker_enabled: bool = field(default_factory=lambda: _bool_env("NOVA_ML_RANKER_ENABLED", False))
    ml_shadow_mode: bool = field(default_factory=lambda: _bool_env("NOVA_ML_SHADOW_MODE", True))
    ml_model_path: str = field(default_factory=lambda: _str_env("NOVA_ML_MODEL_PATH", ""))

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

    # Competition model/revision are confirmed in the public rules. The serving contract
    # remains provisional: explicitly configure the authorized endpoint; absence is NOT_CONFIGURED.
    # The current OpenAI-compatible transport is not an official API contract.
    competition_base_url: str = field(default_factory=lambda: _str_env("NOVA_COMPETITION_BASE_URL", ""))
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

    def effective_differential_top_k(self) -> int:
        """The final active-differential size (differential.py's DifferentialEngine.update() and
        safety_validator.py's SafetyValidator.merge_differential() both call this, so the two stay
        consistent). `reasoning_top_k` (competition, ~25) when competition retrieval is enabled;
        the legacy `top_k_differential` (~5) otherwise -- so enabling competition retrieval is what
        widens the differential that actually reaches the LLM context, and every existing
        mock/legacy caller that never turns retrieval on keeps its exact previous behavior."""
        return self.reasoning_top_k if self.competition_retrieval_enabled else self.top_k_differential


_config: NovaConfig | None = None


def get_config(reload: bool = False) -> NovaConfig:
    """Return the process-wide config, loading it lazily from the environment."""
    global _config
    if _config is None or reload:
        _config = NovaConfig()
    return _config
