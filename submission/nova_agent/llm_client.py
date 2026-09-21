"""LLM Clinical Reasoning layer (spec sections 2/3/12/13/20/21).

Architecture: LLM Clinical Reasoning + Deterministic Safety Guard + Structured Action Validation.
This module produces the reasoning half (a structured AgentTurnOutput); nova_agent/safety_validator.py
provides the guard half that orchestrator.py applies afterward. The LLM here is a real participant
in differential ranking and action selection -- it is handed the deterministically-generated
candidate pool (with utilities, for context) plus retrieved knowledge snippets, and may pick any
legal candidate (not just the top-utility one) or introduce a new differential diagnosis outside
the local knowledge base. It is not handed unlimited authority: safety_validator.py is what
actually enforces the hard constraints (duplicates, unknown keys, unresolved dangerous
alternatives, the turn limit), never this module.

Providers (spec section 3), selected via NOVA_LLM_PROVIDER:
- ``mock`` (default, no network): a deterministic reasoning stand-in -- repackages the
  already-computed candidate/differential data into the schema, picking the highest-utility
  candidate. This is what makes the whole agent runnable offline with zero external dependencies
  and reproducible output (spec section 21), and is what evaluation/benchmark.py uses by default.
  Architecturally interchangeable with a real reasoning call: see tests/test_nova_agent.py's
  test_llm_can_change_differential / test_llm_can_select_valid_non_deterministic_candidate for a
  scripted client proving the pipeline actually honors a *different* LLM choice, not just mock's.
- ``anthropic``: a real Claude call (optional `anthropic` package + ANTHROPIC_API_KEY).
- ``openai_compatible``: any OpenAI Chat Completions-compatible HTTP endpoint (local vLLM /
  llama.cpp / ollama server, or a hosted API) -- base_url/model/api_key from config, so a
  locally-hosted model (e.g. openai/gpt-oss-20b) works with no internet access.
- ``local``: alias of ``openai_compatible`` for a local-only deployment (no API key required).
- ``competition``: alias of ``openai_compatible`` reading the separate NOVA_COMPETITION_*
  variables, so the official competition runtime can be pointed to without touching any other
  provider's configuration.

Any JSON parsing failure, timeout, empty response, or missing SDK/API key/local server falls back
to the deterministic mock output rather than raising -- a single LLM error must never end the
whole evaluation run (spec section 20).
"""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import List, Optional

from pydantic import BaseModel, ValidationError

from nova_agent.action_selector import AgentAction, ScoredCandidate
from nova_agent.clinical_summary import ClinicalSummary
from nova_agent.config import get_config
from nova_agent.differential import DifferentialItem
from nova_agent.llm_schema import (
    AgentTurnOutput,
    CandidateActionOutput,
    DifferentialItemOutput,
    SelectedActionOutput,
)
from nova_agent.safety import SafetyFinding
from nova_agent.stop_policy import StopDecision

log = logging.getLogger("nova_agent.llm")


class TurnContext(BaseModel):
    summary: ClinicalSummary
    differential: List[DifferentialItem]
    safety_findings: List[SafetyFinding]
    candidates: List[ScoredCandidate]
    chosen_action: AgentAction
    stop_decision: StopDecision
    retrieved_context: List[dict] = []

    model_config = {"arbitrary_types_allowed": True}


def _deterministic_turn_output(ctx: TurnContext) -> AgentTurnOutput:
    """The mock/fallback reasoning output: picks the highest-utility candidate (already sorted by
    action_selector.py), same behavior as before this module supported real LLM choice."""
    differential_out = [
        DifferentialItemOutput(
            diagnosis=d.diagnosis, diagnosis_id=d.diagnosis_id, rank=d.rank,
            supporting_evidence=d.supporting_evidence, contradictory_evidence=d.contradictory_evidence,
            missing_information=d.missing_discriminative_evidence,
            dangerous_if_missed=d.dangerous_if_missed, confidence=d.confidence_band,
        ) for d in ctx.differential
    ]
    candidate_out = [
        CandidateActionOutput(type=c.action_type, key=c.key, content=c.content, utility=c.utility)
        for c in ctx.candidates
    ]
    return AgentTurnOutput(
        summary=ctx.summary.to_text(),
        differential=differential_out,
        red_flags=[f.condition for f in ctx.safety_findings],
        candidate_actions=candidate_out,
        selected_action=SelectedActionOutput(type=ctx.chosen_action.action_type, key=ctx.chosen_action.key,
                                              content=ctx.chosen_action.content),
        ready_to_diagnose=ctx.stop_decision.should_diagnose,
    )


def parse_agent_turn_output(raw: str) -> Optional[AgentTurnOutput]:
    """Validator/repair for LLM output (spec section 12): tolerates markdown code fences and
    leading/trailing prose around the JSON object; returns None (never raises) on any failure so
    callers can fall back to the deterministic path."""
    if not raw or not raw.strip():
        return None
    text = raw.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    else:
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            text = brace_match.group(0)
    try:
        data = json.loads(text)
        return AgentTurnOutput.model_validate(data)
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        log.warning("Failed to parse/validate LLM structured output: %s", exc)
        return None


def build_reasoning_prompt(ctx: TurnContext) -> str:
    """Shared prompt builder for every real-LLM provider below. Includes the RAG-retrieved
    knowledge snippets (spec section 13) and the full legal candidate pool (not just one
    pre-selected "correct" choice) so the model has both the clinical context and the actual
    decision space to reason over."""
    candidate_lines = [f"- key={c.key!r} type={c.action_type} content={c.content!r} (utility={c.utility})"
                        for c in ctx.candidates if c.action_type != "DIAGNOSE"]
    candidates_text = "\n".join(candidate_lines) or "(no ASK/EXAM/TEST candidates remain)"
    context_lines = [f"[{s.get('source', '?')}] {s.get('text', '')}" for s in ctx.retrieved_context]
    context_text = "\n".join(context_lines) or "(no retrieved context)"

    return (
        "You are the clinical reasoning component of a conversational diagnosis agent. You will "
        "see the current structured patient summary, relevant retrieved medical knowledge, and "
        "the legal action candidates for this turn. Respond with ONLY a single JSON object with "
        "this exact shape (no prose outside the JSON):\n"
        '{"summary": str, '
        '"differential": [{"diagnosis": str, "diagnosis_id": str|null, "rank": int, '
        '"supporting_evidence": [str], "contradictory_evidence": [str], "missing_information": [str], '
        '"dangerous_if_missed": bool, "confidence": "LOW"|"MEDIUM"|"HIGH"}], '
        '"red_flags": [str], '
        '"candidate_actions": [{"type": "ASK"|"EXAM"|"TEST"|"DIAGNOSE", "key": str, "content": str, "utility": float|null}], '
        '"selected_action": {"type": "ASK"|"EXAM"|"TEST"|"DIAGNOSE", "key": str, "content": str}, '
        '"ready_to_diagnose": bool}\n\n'
        "Rules: you MAY re-rank the differential, add supporting/contradictory evidence, or "
        "introduce a diagnosis not in the candidate list below if clinically justified (set its "
        "diagnosis_id to null). For selected_action of type ASK/EXAM/TEST, `key` MUST be copied "
        "EXACTLY from one of the candidate keys listed below -- never invent one. For DIAGNOSE, "
        "only choose it when you are genuinely confident and have no unresolved dangerous "
        "alternative; a deterministic safety layer will reject an unsafe or premature diagnosis "
        "regardless of your choice, so choose honestly rather than trying to guess what will pass.\n\n"
        f"{ctx.summary.to_text()}\n\n"
        f"Retrieved knowledge:\n{context_text}\n\n"
        f"Legal ASK/EXAM/TEST candidates this turn:\n{candidates_text}\n"
    )


class BaseLLMClient(ABC):
    @abstractmethod
    def generate_turn_output(self, ctx: TurnContext) -> AgentTurnOutput:
        raise NotImplementedError


# Backwards-compatible alias (pre-existing code/tests may still import `LLMClient`).
LLMClient = BaseLLMClient


class MockLLMClient(BaseLLMClient):
    """Deterministic, offline, zero-cost reasoning stand-in. Default provider -- see module
    docstring for why this is architecturally a full participant in the pipeline, not a rubber
    stamp: it is simply the one provider whose "reasoning" is a closed-form function of already-
    computed state rather than a network call."""

    def generate_turn_output(self, ctx: TurnContext) -> AgentTurnOutput:
        return _deterministic_turn_output(ctx)


class AnthropicLLMClient(BaseLLMClient):
    """Real-LLM path via the Anthropic Messages API. Requires the `anthropic` package and
    ANTHROPIC_API_KEY. Falls back to the deterministic output on any SDK/network/parsing failure
    (never raises)."""

    def __init__(self) -> None:
        cfg = get_config()
        self.model = cfg.llm_model
        self.temperature = cfg.llm_temperature
        self.max_retries = cfg.llm_max_retries
        self.timeout = cfg.llm_timeout_seconds
        try:
            import anthropic  # type: ignore

            self._client = anthropic.Anthropic()
            self._available = True
        except Exception as exc:  # pragma: no cover - exercised only when SDK/key is present
            log.warning("AnthropicLLMClient unavailable (%s); falling back to deterministic output.", exc)
            self._client = None
            self._available = False

    def generate_turn_output(self, ctx: TurnContext) -> AgentTurnOutput:
        fallback = _deterministic_turn_output(ctx)
        if not self._available:
            return fallback
        prompt = build_reasoning_prompt(ctx)
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.messages.create(
                    model=self.model, max_tokens=get_config().llm_max_tokens, temperature=self.temperature,
                    messages=[{"role": "user", "content": prompt}], timeout=self.timeout,
                )
                raw = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
                parsed = parse_agent_turn_output(raw)
                if parsed is not None:
                    return parsed
            except Exception as exc:  # network error, timeout, SDK error, etc.
                log.warning("Anthropic call failed (attempt %d/%d): %s", attempt + 1, self.max_retries + 1, exc)
        log.warning("Falling back to deterministic turn output after %d failed attempt(s).", self.max_retries + 1)
        return fallback


class OpenAICompatibleLLMClient(BaseLLMClient):
    """Real-LLM path via any OpenAI Chat Completions-compatible HTTP endpoint: a locally-hosted
    server (vLLM / llama.cpp / ollama / text-generation-inference) serving an open-weight model
    such as openai/gpt-oss-20b with no internet access required, or a hosted OpenAI-compatible API.

    Uses the `openai` Python package's generic client pointed at a configurable `base_url`, so it
    works against any server implementing that HTTP contract -- never assumes OpenAI's own hosted
    service specifically. Falls back to the deterministic output on any SDK/network/parsing
    failure (never raises); a missing `openai` package or unreachable server is treated exactly
    like an Anthropic SDK/key failure.
    """

    def __init__(self, *, base_url: Optional[str] = None, model: Optional[str] = None,
                 api_key: Optional[str] = None) -> None:
        cfg = get_config()
        self.base_url = base_url or cfg.llm_base_url
        self.model = model or cfg.llm_model
        self.api_key = api_key if api_key is not None else cfg.llm_api_key
        self.temperature = cfg.llm_temperature
        self.max_retries = cfg.llm_max_retries
        self.timeout = cfg.llm_timeout_seconds
        try:
            import openai  # type: ignore

            self._client = openai.OpenAI(base_url=self.base_url, api_key=self.api_key or "not-needed",
                                          timeout=self.timeout)
            self._available = True
        except Exception as exc:  # pragma: no cover - exercised only when SDK is present
            log.warning("%s unavailable (%s); falling back to deterministic output.",
                        type(self).__name__, exc)
            self._client = None
            self._available = False

    def generate_turn_output(self, ctx: TurnContext) -> AgentTurnOutput:
        fallback = _deterministic_turn_output(ctx)
        if not self._available:
            return fallback
        prompt = build_reasoning_prompt(ctx)
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self.model, temperature=self.temperature, max_tokens=get_config().llm_max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = response.choices[0].message.content or ""
                parsed = parse_agent_turn_output(raw)
                if parsed is not None:
                    return parsed
            except Exception as exc:
                log.warning("%s call failed (attempt %d/%d): %s", type(self).__name__, attempt + 1,
                            self.max_retries + 1, exc)
        log.warning("Falling back to deterministic turn output after %d failed attempt(s).", self.max_retries + 1)
        return fallback


class LocalLLMClient(OpenAICompatibleLLMClient):
    """Explicit alias for a locally-hosted OpenAI-compatible server (no internet access needed).
    Behaviorally identical to OpenAICompatibleLLMClient; separated only so NOVA_LLM_PROVIDER=local
    documents deployment intent (a runtime with no outbound network access) without requiring an
    API key to be set."""


class CompetitionLLMClient(OpenAICompatibleLLMClient):
    """Reads the separate NOVA_COMPETITION_* settings (base URL / model / API key) instead of the
    generic NOVA_LLM_* ones, so the official competition runtime endpoint can be configured
    independently of local development settings. Defaults to a local, offline OpenAI-compatible
    endpoint serving openai/gpt-oss-20b (the model named in the publicly discussed N.O.V.A.
    qualifier requirements at implementation time) -- override every value from the environment
    once the official rules are published; no other file needs to change."""

    def __init__(self) -> None:
        cfg = get_config()
        super().__init__(base_url=cfg.competition_base_url, model=cfg.competition_model,
                          api_key=cfg.competition_api_key)


_PROVIDERS = {
    "mock": MockLLMClient,
    "anthropic": AnthropicLLMClient,
    "openai_compatible": OpenAICompatibleLLMClient,
    "local": LocalLLMClient,
    "competition": CompetitionLLMClient,
}


def get_llm_client() -> BaseLLMClient:
    provider = get_config().llm_provider.lower()
    cls = _PROVIDERS.get(provider)
    if cls is None:
        log.warning("Unknown NOVA_LLM_PROVIDER=%r (valid: %s); falling back to 'mock'.",
                    provider, ", ".join(_PROVIDERS))
        cls = MockLLMClient
    return cls()
