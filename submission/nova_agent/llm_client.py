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
  locally-hosted model (e.g. openai/gpt-oss-20b) works with no internet access. Implemented with
  stdlib `urllib` (no `openai` package needed at all -- see OpenAICompatibleLLMClient).
- ``local``: alias of ``openai_compatible`` for a local-only deployment (no API key required).
- ``competition``: alias of ``openai_compatible`` reading the separate NOVA_COMPETITION_*
  variables, so the official competition runtime can be pointed to without touching any other
  provider's configuration. This is the provider `submission/run.py` selects by default -- see
  its module docstring and `scripts/preflight_competition.py` for the startup-time check that
  stops a competition run from silently spending the whole case on the `mock` fallback just
  because the real endpoint was never reachable.

Any JSON parsing failure, timeout, empty response, or missing SDK/API key/local server falls back
to the deterministic mock output PER TURN rather than raising (spec section 20) -- that per-turn
dev/runtime fallback policy is intentionally separate from the competition STARTUP preflight
policy (`preflight()` on each real client, and `scripts/preflight_competition.py`), which must
fail loudly rather than silently let an entire competition run happen on mock.
"""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

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


_VALID_ACTION_TYPES = {"ask": "ASK", "exam": "EXAM", "test": "TEST", "diagnose": "DIAGNOSE"}


def _extract_json_candidate_text(text: str) -> str:
    """Strips markdown fences / leading-trailing prose down to the (probable) JSON object -- pure
    text slicing, no content interpretation."""
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1)
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    return brace_match.group(0) if brace_match else text


def _strip_trailing_commas(text: str) -> str:
    return re.sub(r",(\s*[}\]])", r"\1", text)


def _normalize_action_type_casing(data: dict) -> dict:
    """A small open-weight model frequently emits the right enum value with the wrong casing
    ("test"/"Ask") -- fixing that is a pure syntax/schema repair (the value's MEANING is
    unchanged, only its casing), never a guess about what action was actually meant. Anything that
    doesn't cleanly map to a known action type is left as-is so schema validation still rejects it."""
    def fix(action: object) -> None:
        if isinstance(action, dict) and isinstance(action.get("type"), str):
            mapped = _VALID_ACTION_TYPES.get(action["type"].strip().lower())
            if mapped:
                action["type"] = mapped

    fix(data.get("selected_action"))
    for candidate in data.get("candidate_actions") or []:
        fix(candidate)
    return data


def _best_effort_json_parse(text: str) -> Optional[dict]:
    """Tries, in order: (1) plain JSON, (2) JSON with trailing commas removed, (3) a Python-dict-
    literal repair (single-quoted keys/strings, Python True/False/None) for a model that emitted
    valid Python but not valid JSON. Every step is pure SYNTAX repair -- no field value is ever
    invented or clinically reinterpreted; if none of these parse to a dict, returns None and the
    caller falls back to the deterministic path (spec section 6/12)."""
    for candidate_text in (text, _strip_trailing_commas(text)):
        try:
            data = json.loads(candidate_text)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue
    try:
        import ast

        python_literal_text = re.sub(r"\btrue\b", "True", text)
        python_literal_text = re.sub(r"\bfalse\b", "False", python_literal_text)
        python_literal_text = re.sub(r"\bnull\b", "None", python_literal_text)
        data = ast.literal_eval(python_literal_text)
        if isinstance(data, dict):
            return data
    except (ValueError, SyntaxError, TypeError):
        pass
    return None


def parse_agent_turn_output(raw: str) -> Optional[AgentTurnOutput]:
    """Validator/repair for LLM output (spec section 6/12): tolerates markdown code fences,
    leading/trailing prose, trailing commas, single-quoted/Python-dict-style output, and wrong
    enum casing -- all pure syntax/schema repair, never a correction of clinical content (an
    unknown test/diagnosis name is never invented or substituted here). Returns None (never
    raises) on any failure so callers can fall back to the deterministic path."""
    if not raw or not raw.strip():
        return None
    candidate_text = _extract_json_candidate_text(raw.strip())
    data = _best_effort_json_parse(candidate_text)
    if data is None:
        log.warning("Failed to parse LLM structured output as JSON (or a repairable variant of it).")
        return None
    try:
        return AgentTurnOutput.model_validate(_normalize_action_type_casing(data))
    except (ValidationError, TypeError) as exc:
        log.warning("Failed to validate LLM structured output against the schema: %s", exc)
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
    # Per-call reliability signal (spec: LLM failures must never be invisible behind a healthy-
    # looking deterministic fallback). Reset by each generate_turn_output() call, read by
    # orchestrator.decide() immediately afterward and folded into the per-CASE PatientState
    # counters (never accumulated on the client itself, since one client instance can be reused
    # across many cases -- e.g. evaluation/benchmark.py's run_all()). False/None here (the default)
    # means "not a real LLM attempt at all" -- true for MockLLMClient, which never overrides this.
    _last_call_was_real: bool = False
    _last_call_succeeded: Optional[bool] = None
    # Latency/token instrumentation (spec: LLM latency/token/call-count optimization needs real
    # numbers, never an estimate). None means "not observed this call" -- e.g. an endpoint that
    # doesn't return a `usage` block, or a call that never actually reached the network.
    _last_call_latency_seconds: Optional[float] = None
    _last_call_input_tokens: Optional[int] = None
    _last_call_output_tokens: Optional[int] = None

    @abstractmethod
    def generate_turn_output(self, ctx: TurnContext) -> AgentTurnOutput:
        raise NotImplementedError

    def preflight(self) -> Tuple[bool, str]:
        """Startup-time readiness check. Default: always ready (true for mock, and a safe default
        for any client that doesn't override this) -- real network-backed clients override it with
        an actual reachability check. Returns (ok, reason)."""
        return True, f"{type(self).__name__} requires no external readiness check."


# Backwards-compatible alias (pre-existing code/tests may still import `LLMClient`).
LLMClient = BaseLLMClient


class MockLLMClient(BaseLLMClient):
    """Deterministic, offline, zero-cost reasoning stand-in. Default provider -- see module
    docstring for why this is architecturally a full participant in the pipeline, not a rubber
    stamp: it is simply the one provider whose "reasoning" is a closed-form function of already-
    computed state rather than a network call."""

    def generate_turn_output(self, ctx: TurnContext) -> AgentTurnOutput:
        return _deterministic_turn_output(ctx)

    def preflight(self) -> Tuple[bool, str]:
        return True, "mock provider: fully offline, always ready (not a real LLM)."


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
        self._last_call_was_real = True
        self._last_call_succeeded = False
        self._last_call_latency_seconds = None
        self._last_call_input_tokens = None
        self._last_call_output_tokens = None
        if not self._available:
            return fallback
        prompt = build_reasoning_prompt(ctx)
        for attempt in range(self.max_retries + 1):
            start = time.perf_counter()
            try:
                response = self._client.messages.create(
                    model=self.model, max_tokens=get_config().llm_max_tokens, temperature=self.temperature,
                    messages=[{"role": "user", "content": prompt}], timeout=self.timeout,
                )
                self._last_call_latency_seconds = time.perf_counter() - start
                usage = getattr(response, "usage", None)
                if usage is not None:
                    self._last_call_input_tokens = getattr(usage, "input_tokens", None)
                    self._last_call_output_tokens = getattr(usage, "output_tokens", None)
                raw = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
                parsed = parse_agent_turn_output(raw)
                if parsed is not None:
                    self._last_call_succeeded = True
                    return parsed
            except Exception as exc:  # network error, timeout, SDK error, etc.
                self._last_call_latency_seconds = time.perf_counter() - start
                log.warning("Anthropic call failed (attempt %d/%d): %s", attempt + 1, self.max_retries + 1, exc)
        log.warning("Falling back to deterministic turn output after %d failed attempt(s).", self.max_retries + 1)
        return fallback

    def preflight(self) -> Tuple[bool, str]:
        if not self._available:
            return False, "anthropic package not installed or ANTHROPIC_API_KEY not set/invalid."
        try:
            response = self._client.messages.create(
                model=self.model, max_tokens=8, temperature=self.temperature,
                messages=[{"role": "user", "content": "Reply with the single word: ready"}], timeout=self.timeout,
            )
            text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
            if not text.strip():
                return False, "Anthropic API responded but returned an empty completion."
            return True, f"Anthropic API reachable, model={self.model!r}."
        except Exception as exc:
            return False, f"{type(exc).__name__}: {exc}"


class OpenAICompatibleLLMClient(BaseLLMClient):
    """Real-LLM path via any OpenAI Chat Completions-compatible HTTP endpoint: a locally-hosted
    server (vLLM / llama.cpp / ollama / text-generation-inference) serving an open-weight model
    such as openai/gpt-oss-20b with no internet access required, or a hosted OpenAI-compatible API.

    Deliberately implemented with the stdlib `urllib` (POST to `{base_url}/chat/completions`)
    instead of the `openai` package: a competition submission environment may not have that (or
    any) third-party package pre-installed, and the OpenAI Chat Completions HTTP contract is
    simple enough not to need an SDK. This is what lets `submission/requirements.txt` ship with
    only `pydantic` and still have `competition`/`local`/`openai_compatible` actually reach a real
    model -- no missing-package failure mode exists for this provider at all. Falls back to the
    deterministic output on any network/HTTP/parsing failure per turn (never raises -- spec
    section 20); `preflight()` below is the separate, stricter startup-time check (spec section 2:
    a competition run must not silently spend the whole case on mock just because the endpoint
    was never reachable to begin with).
    """

    def __init__(self, *, base_url: Optional[str] = None, model: Optional[str] = None,
                 api_key: Optional[str] = None) -> None:
        cfg = get_config()
        self.base_url = (base_url or cfg.llm_base_url).rstrip("/")
        self.model = model or cfg.llm_model
        self.api_key = api_key if api_key is not None else cfg.llm_api_key
        self.temperature = cfg.llm_temperature
        self.max_retries = cfg.llm_max_retries
        self.timeout = cfg.llm_timeout_seconds
        self.max_tokens = cfg.llm_max_tokens
        # Always "available" architecturally (no SDK import can fail) -- reachability is a
        # per-call/per-preflight network fact, not a constructor-time one. Kept for interface
        # parity with AnthropicLLMClient.
        self._available = True

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _post_chat_completion(self, messages: list, *, max_tokens: Optional[int] = None) -> Tuple[str, dict]:
        """POSTs one Chat Completions request. Returns (content_text, raw_response_dict). Raises
        on any failure (network, HTTP status, JSON decode, unexpected shape) -- callers handle
        that; this method never swallows an error itself, so preflight() sees the real reason."""
        body = json.dumps({
            "model": self.model, "temperature": self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
            "messages": messages,
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions", data=body, headers=self._headers(), method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            raw = json.loads(response.read().decode("utf-8"))
        content = raw["choices"][0]["message"]["content"] or ""
        return content, raw

    def generate_turn_output(self, ctx: TurnContext) -> AgentTurnOutput:
        fallback = _deterministic_turn_output(ctx)
        self._last_call_was_real = True
        self._last_call_succeeded = False
        self._last_call_latency_seconds = None
        self._last_call_input_tokens = None
        self._last_call_output_tokens = None
        prompt = build_reasoning_prompt(ctx)
        for attempt in range(self.max_retries + 1):
            start = time.perf_counter()
            try:
                content, raw = self._post_chat_completion([{"role": "user", "content": prompt}])
                self._last_call_latency_seconds = time.perf_counter() - start
                usage = raw.get("usage") if isinstance(raw, dict) else None
                if isinstance(usage, dict):
                    # OpenAI Chat Completions naming; not every OpenAI-compatible server returns
                    # this block at all -- left None (never estimated) when absent.
                    self._last_call_input_tokens = usage.get("prompt_tokens")
                    self._last_call_output_tokens = usage.get("completion_tokens")
                parsed = parse_agent_turn_output(content)
                if parsed is not None:
                    self._last_call_succeeded = True
                    return parsed
            except Exception as exc:
                self._last_call_latency_seconds = time.perf_counter() - start
                log.warning("%s call failed (attempt %d/%d): %s", type(self).__name__, attempt + 1,
                            self.max_retries + 1, exc)
        log.warning("Falling back to deterministic turn output after %d failed attempt(s).", self.max_retries + 1)
        return fallback

    def preflight(self) -> Tuple[bool, str]:
        """Startup-time reachability check (spec section 2/22) -- a minimal real request, not just
        a socket check, so a server that accepts TCP connections but 404s/500s on this route is
        still correctly reported as NOT ready. Returns (ok, reason)."""
        try:
            content, _raw = self._post_chat_completion(
                [{"role": "user", "content": "Reply with the single word: ready"}], max_tokens=8,
            )
            if not content.strip():
                return False, "Endpoint responded but returned an empty completion."
            return True, f"Endpoint reachable at {self.base_url}, model={self.model!r}."
        except urllib.error.HTTPError as exc:
            return False, f"HTTP {exc.code} from {self.base_url}/chat/completions: {exc.reason}"
        except urllib.error.URLError as exc:
            return False, f"Cannot reach {self.base_url}: {exc.reason}"
        except Exception as exc:  # noqa: BLE001 - preflight must report every failure mode, not raise
            return False, f"{type(exc).__name__}: {exc}"


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
