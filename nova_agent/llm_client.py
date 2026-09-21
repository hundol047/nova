"""LLM orchestration layer (spec sections 12/13/20/21).

The deterministic engine (differential.py / safety.py / missing_info.py / action_selector.py) is
always the source of truth for WHAT the candidate actions and differential are -- this module only
decides how the turn's structured summary/selection gets produced and phrased:

- ``mock`` (default, no network, fully deterministic): repackages the already-computed
  differential/candidates/stop-decision into the AgentTurnOutput schema. This is what makes the
  whole agent runnable offline with zero external dependencies and identical output across runs
  (spec section 21), and is what evaluation/benchmark.py uses.
- ``anthropic`` (optional): asks a real Claude model to pick among the deterministically generated
  candidate_actions and phrase the summary, in one call (section 13). Its output is still only
  ever a hint -- orchestrator.py clamps the final selected_action back onto the deterministic
  candidate list, so a malformed/hallucinated response can change phrasing but never the agent's
  actual safety-relevant behavior.

Any JSON parsing failure, timeout, empty response, or missing SDK/API key falls back to the mock
path rather than raising -- a single LLM error must never end the whole evaluation run.
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

    model_config = {"arbitrary_types_allowed": True}


def _deterministic_turn_output(ctx: TurnContext) -> AgentTurnOutput:
    differential_out = [
        DifferentialItemOutput(
            diagnosis=d.diagnosis, rank=d.rank, supporting_evidence=d.supporting_evidence,
            contradictory_evidence=d.contradictory_evidence, missing_information=d.missing_discriminative_evidence,
            dangerous_if_missed=d.dangerous_if_missed, confidence=d.confidence_band,
        ) for d in ctx.differential
    ]
    candidate_out = [
        CandidateActionOutput(type=c.action_type, content=c.content, utility=c.utility) for c in ctx.candidates
    ]
    return AgentTurnOutput(
        summary=ctx.summary.to_text(),
        differential=differential_out,
        red_flags=[f.condition for f in ctx.safety_findings],
        candidate_actions=candidate_out,
        selected_action=SelectedActionOutput(type=ctx.chosen_action.action_type, content=ctx.chosen_action.content),
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


class LLMClient(ABC):
    @abstractmethod
    def generate_turn_output(self, ctx: TurnContext) -> AgentTurnOutput:
        raise NotImplementedError


class MockLLMClient(LLMClient):
    """Deterministic, offline, zero-cost. Default provider -- see module docstring."""

    def generate_turn_output(self, ctx: TurnContext) -> AgentTurnOutput:
        return _deterministic_turn_output(ctx)


class AnthropicLLMClient(LLMClient):
    """Optional real-LLM path. Requires the `anthropic` package and ANTHROPIC_API_KEY. Falls back
    to the deterministic output on any SDK/network/parsing failure (never raises)."""

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

    def _prompt(self, ctx: TurnContext) -> str:
        candidates_text = "\n".join(f"- [{c.action_type}] {c.content} (utility={c.utility})" for c in ctx.candidates)
        return (
            "You are assisting a deterministic clinical reasoning engine. Given the structured "
            "clinical summary and the pre-computed candidate actions below, respond with ONLY a "
            "JSON object matching the AgentTurnOutput schema (summary, differential, red_flags, "
            "candidate_actions, selected_action, ready_to_diagnose). Choose selected_action from "
            "the candidate list verbatim (type and content) unless ready_to_diagnose. Do not invent "
            "a diagnosis, question, exam, or test that is not already present in the summary or "
            "candidate list. Do not include any text outside the JSON object.\n\n"
            f"{ctx.summary.to_text()}\n\nCandidate actions:\n{candidates_text}\n"
        )

    def generate_turn_output(self, ctx: TurnContext) -> AgentTurnOutput:
        fallback = _deterministic_turn_output(ctx)
        if not self._available:
            return fallback
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.messages.create(
                    model=self.model, max_tokens=1024, temperature=self.temperature,
                    messages=[{"role": "user", "content": self._prompt(ctx)}],
                    timeout=self.timeout,
                )
                raw = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
                parsed = parse_agent_turn_output(raw)
                if parsed is not None:
                    return parsed
            except Exception as exc:  # network error, timeout, SDK error, etc.
                log.warning("Anthropic call failed (attempt %d/%d): %s", attempt + 1, self.max_retries + 1, exc)
        log.warning("Falling back to deterministic turn output after %d failed attempt(s).", self.max_retries + 1)
        return fallback


def get_llm_client() -> LLMClient:
    provider = get_config().llm_provider.lower()
    if provider == "anthropic":
        return AnthropicLLMClient()
    if provider != "mock":
        log.warning("Unknown NOVA_LLM_PROVIDER=%r; falling back to 'mock'.", provider)
    return MockLLMClient()
