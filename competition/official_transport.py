"""Isolated boundary for the (still unpublished) organizer model/runtime interface.

NOTHING in this module is an organizer contract. No endpoint, request schema, response schema,
header, token format or environment-variable name is defined here, because none has been published.
The final integration is intended to be: implement ``OfficialTransport.call`` (and nothing else) in a
subclass that follows the participant guide, then construct the submission agent with it.

The clinical reasoning engine (``nova_agent``) never imports this module. Evidence of progress is
tracked in ``TransportEvidence`` as a monotone ladder; a state is only reached by observing it, and a
stub transport can never reach the model-identity states ("STUB SUCCESS != OFFICIAL SUCCESS").
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, Mapping, Optional

from nova_agent.config import EXPECTED_COMPETITION_MODEL, EXPECTED_COMPETITION_REVISION
from nova_agent.llm_client import BaseLLMClient, TurnContext, _deterministic_turn_output, build_reasoning_prompt, parse_agent_turn_output
from nova_agent.llm_schema import AgentTurnOutput


class TransportState(IntEnum):
    NOT_CONFIGURED = 0
    CONFIGURED = 1
    CALL_ATTEMPTED = 2
    RESPONSE_RECEIVED = 3
    MODEL_IDENTITY_VERIFIED = 4
    REVISION_VERIFIED = 5


class TransportError(RuntimeError):
    """Any failure to obtain a model response; callers must fail closed, never fabricate one."""


@dataclass
class TransportEvidence:
    """What has actually been observed. ``state`` only ever rises, and only through the ``note_*``
    methods; there is deliberately no setter, so a state cannot be reported without its evidence."""

    kind: str = "NONE"                      # "NONE" | "STUB" | "OFFICIAL"
    state: TransportState = TransportState.NOT_CONFIGURED
    calls_attempted: int = 0
    responses_received: int = 0
    reported_model: Optional[str] = None
    reported_revision: Optional[str] = None
    case_ids_with_response: set = field(default_factory=set)

    def _raise_to(self, state: TransportState) -> None:
        if state > self.state:
            self.state = state

    def note_configured(self, kind: str) -> None:
        self.kind = kind
        self._raise_to(TransportState.CONFIGURED)

    def note_attempt(self) -> None:
        self.calls_attempted += 1
        self._raise_to(TransportState.CALL_ATTEMPTED)

    def note_response(self, case_id: str, model: Optional[str], revision: Optional[str]) -> None:
        self.responses_received += 1
        self.case_ids_with_response.add(case_id)
        self._raise_to(TransportState.RESPONSE_RECEIVED)
        if self.kind != "OFFICIAL":  # a stub never proves anything about the fixed model
            return
        self.reported_model, self.reported_revision = model, revision
        if model == EXPECTED_COMPETITION_MODEL:
            self._raise_to(TransportState.MODEL_IDENTITY_VERIFIED)
            if revision == EXPECTED_COMPETITION_REVISION:
                self._raise_to(TransportState.REVISION_VERIFIED)

    @property
    def official_success(self) -> bool:
        return self.kind == "OFFICIAL" and self.state >= TransportState.MODEL_IDENTITY_VERIFIED

    def official_case_call_made(self, case_id: str) -> bool:
        """The per-case requirement: a successful official response for THIS case (a startup probe
        carries no case id and never counts)."""
        return self.kind == "OFFICIAL" and case_id in self.case_ids_with_response

    def as_dict(self) -> Dict[str, Any]:
        return {"kind": self.kind, "state": self.state.name, "calls_attempted": self.calls_attempted,
                "responses_received": self.responses_received, "official_success": self.official_success,
                "reported_model": self.reported_model, "reported_revision": self.reported_revision}


class OfficialTransport:
    """Base class and the default: fail-closed. ``kind`` is "OFFICIAL" only for a reviewed
    implementation of the organizer interface."""

    kind = "NONE"

    def __init__(self) -> None:
        self.evidence = TransportEvidence()

    def configured(self) -> bool:
        return False

    def _send(self, case_id: str, prompt: str) -> Mapping[str, Any]:  # pragma: no cover - interface
        raise TransportError("NOT_CONFIGURED: no organizer-approved transport is integrated")

    def call(self, case_id: str, prompt: str) -> str:
        """One case-relevant fixed-model call. Returns the model text; raises TransportError."""
        if not self.configured():
            raise TransportError("NOT_CONFIGURED: no organizer-approved transport is integrated")
        self.evidence.note_configured(self.kind)
        self.evidence.note_attempt()
        try:
            reply = self._send(case_id, prompt)
        except TransportError:
            raise
        except Exception as exc:  # noqa: BLE001 - every transport failure is a closed failure
            raise TransportError(f"{type(exc).__name__}") from exc
        text = reply.get("text") if isinstance(reply, Mapping) else None
        if not isinstance(text, str) or not text.strip():
            raise TransportError("EMPTY_OR_MALFORMED_RESPONSE")
        self.evidence.note_response(case_id, reply.get("model"), reply.get("revision"))
        return text


class NotConfiguredTransport(OfficialTransport):
    """Explicit name for the shipped default."""


class StubTransport(OfficialTransport):
    """Local test double. Its successes are recorded as ``kind == "STUB"`` and never count as official."""

    kind = "STUB"

    def __init__(self, replies=None, model: Optional[str] = EXPECTED_COMPETITION_MODEL,
                 revision: Optional[str] = EXPECTED_COMPETITION_REVISION) -> None:
        super().__init__()
        self._replies = list(replies or [])
        self._model, self._revision = model, revision

    def configured(self) -> bool:
        return True

    def _send(self, case_id: str, prompt: str) -> Mapping[str, Any]:
        if not self._replies:
            raise TransportError("STUB_EXHAUSTED")
        reply = self._replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return {"text": reply, "model": self._model, "revision": self._revision}


class TransportLLMClient(BaseLLMClient):
    """Adapts an ``OfficialTransport`` to the engine's model-client interface -- the ONLY place the reasoning
    engine and a transport meet, so the final integration is: subclass OfficialTransport, pass it here.

    A failed/malformed transport call returns the deterministic turn output and is recorded as a real attempt
    that did not succeed (never as a success). ``bind_case`` is called by the adapter before every decision so
    that evidence is attributed to the case being served."""

    def __init__(self, transport: Optional[OfficialTransport] = None) -> None:
        self.transport = transport or NotConfiguredTransport()
        self.current_case_id = ""

    def bind_case(self, case_id: str) -> None:
        self.current_case_id = case_id

    def generate_turn_output(self, ctx: TurnContext) -> AgentTurnOutput:
        fallback = _deterministic_turn_output(ctx)
        self._last_call_was_real = False
        self._last_call_succeeded = False
        if not self.transport.configured():
            return fallback
        self._last_call_was_real = True
        try:
            text = self.transport.call(self.current_case_id, build_reasoning_prompt(ctx))
        except TransportError:
            return fallback
        parsed = parse_agent_turn_output(text)
        if parsed is None:
            return fallback
        self._last_call_succeeded = True
        return parsed
