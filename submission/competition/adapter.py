"""Competition Adapter (spec section 16) -- the ONLY place that should need to change once the
official N.O.V.A. 2026 Agent API is published.

Responsibilities (and nothing else):
  competition observation  -> internal PatientState
  internal AgentAction     -> competition action

nova_agent/'s clinical reasoning engine (state/differential/safety/missing_info/action_selector/
stop_policy/orchestrator) never imports anything from this package, and this package never
contains clinical reasoning logic -- only translation. That separation is what lets the real
competition interface replace competition/schema.py + the two translation functions below without
touching anything else in the repository.
"""

from __future__ import annotations

import logging
import sys
from typing import Dict, Optional

from nova_agent.action_selector import AgentAction
from nova_agent.config import get_config
from nova_agent.orchestrator import DoctorAgent
from nova_agent.state import PatientState

from competition.schema import CompetitionAction, CompetitionObservation

log = logging.getLogger("competition.adapter")

# Heuristic, not an official threshold -- just a loud, honest signal that a real-LLM run's
# clinical reasoning quietly spent most of its turns on the deterministic fallback rather than
# the real model (spec: LLM failure must never be invisible behind a healthy-looking run).
_HIGH_FALLBACK_RATE_THRESHOLD = 0.3

# Bounded, never unlimited -- each retry here calls DoctorAgent.decide() again, which itself
# already applies its own bounded per-call retry inside the LLM client (NOVA_LLM_MAX_RETRIES).
# When the case's time/call budget is already exhausted, decide() skips the real LLM call
# entirely (see orchestrator.py's budget_exhausted check) and returns immediately, so a retry
# loop here can never itself push a case past its configured case timeout -- it just fails fast.
_DIAGNOSE_ZERO_LLM_SUCCESS_RETRIES = 2


class RealLLMUnavailableError(RuntimeError):
    """Raised by NovaCompetitionAgent.act() instead of returning a DIAGNOSE action, when a
    competition-mode (provider != mock) case reaches its final answer having never once received
    a successful real-LLM response across the whole case, even after the bounded retries above.

    This is the explicit-failure half of spec section 12: a deterministic-fallback-only result
    must never be silently returned as a normal, successful competition completion just because
    it happens to be a well-formed action. Dev/mock mode never raises this -- see the
    `in_competition_mode` gate in `act()` below; the deterministic fallback stays fully available
    there, unchanged."""


def observation_to_state(obs: CompetitionObservation, agent: DoctorAgent,
                          existing_state: Optional[PatientState],
                          pending_action: Optional[AgentAction]) -> PatientState:
    """Translates one CompetitionObservation into a PatientState update.

    On observation_type == 'initial', starts a fresh case. Otherwise, records the environment's
    reply against `pending_action` (the action this adapter returned on the previous turn) via
    DoctorAgent.observe(), which is what actually accumulates evidence into PatientState.
    """
    if obs.observation_type == "initial" or existing_state is None:
        return agent.new_case(obs.case_id, obs.chief_complaint or "", obs.demographics, obs.max_turns)

    if pending_action is None:
        log.warning("Non-initial observation for case=%s with no pending action; ignoring content.", obs.case_id)
        return existing_state

    agent.observe(existing_state, pending_action, obs.content or "")
    return existing_state


def action_to_competition(case_id: str, action: AgentAction, *, real_llm_verified: Optional[bool] = None) -> CompetitionAction:
    metadata = {"key": action.key, "rationale": action.rationale}
    if real_llm_verified is not None:
        # Only ever attached to a DIAGNOSE action (see NovaCompetitionAgent.act() below) -- lets a
        # competition-readiness harness detect "this case's final answer came from a real LLM at
        # least once" programmatically, not just by grepping a stderr log line.
        metadata["real_llm_verified"] = real_llm_verified
    return CompetitionAction(case_id=case_id, action_type=action.action_type, content=action.content,
                              metadata=metadata)


class NovaCompetitionAgent:
    """Stateful per-process entrypoint a competition runtime can drive directly: one
    `act(observation)` call per turn, holding each case's PatientState internally by case_id.

    This is intentionally the thinnest possible wrapper around DoctorAgent -- if the competition
    harness instead calls nova_agent directly (or a different integration shape is required), the
    reasoning engine underneath (DoctorAgent) is unaffected either way.
    """

    def __init__(self, agent: Optional[DoctorAgent] = None) -> None:
        self.agent = agent or DoctorAgent()
        self._states: Dict[str, PatientState] = {}
        self._pending_actions: Dict[str, AgentAction] = {}

    def act(self, observation: dict) -> dict:
        obs = CompetitionObservation.model_validate(observation)
        state = observation_to_state(obs, self.agent, self._states.get(obs.case_id),
                                      self._pending_actions.get(obs.case_id))
        self._states[obs.case_id] = state

        action, _llm_output, _differential = self.agent.decide(state)
        in_competition_mode = get_config().llm_provider != "mock"

        if action.action_type == "DIAGNOSE" and in_competition_mode and state.real_llm_ever_succeeded is False:
            # Required flow (spec section 12): bounded retry -> real LLM retry -> if it succeeds,
            # proceed normally -> if every attempt still fails, an explicit runtime failure, never
            # a disguised deterministic-only "success". Re-calling decide() on the same
            # (unmutated -- observe() has not run yet for this turn) state re-attempts the real
            # LLM call fresh each time, so a retry that lands after a transient outage clears is
            # indistinguishable from having succeeded on the first try.
            for _ in range(_DIAGNOSE_ZERO_LLM_SUCCESS_RETRIES):
                if state.real_llm_ever_succeeded:
                    break
                action, _llm_output, _differential = self.agent.decide(state)
            if state.real_llm_ever_succeeded is False:
                # Every real-LLM attempt this case failed, even after this bounded retry -- the
                # only available answer is deterministic-fallback-only. Dev/mock mode never
                # reaches this branch (in_competition_mode is False there), so its existing
                # fallback behavior is completely unchanged.
                self._pending_actions.pop(obs.case_id, None)
                raise RealLLMUnavailableError(
                    f"case={obs.case_id}: reached DIAGNOSE with ZERO successful real-LLM calls "
                    f"({state.llm_call_count} attempted across the case and "
                    f"{_DIAGNOSE_ZERO_LLM_SUCCESS_RETRIES} additional bounded retries, all failed). "
                    "Competition mode does not permit a deterministic-fallback-only submission -- "
                    "this is a runtime failure, not a completion. Run "
                    "scripts/preflight_competition.py before submitting."
                )

        self._pending_actions[obs.case_id] = action
        real_llm_verified: Optional[bool] = None
        if action.action_type == "DIAGNOSE":
            self._pending_actions.pop(obs.case_id, None)
            real_llm_verified = state.real_llm_ever_succeeded
            if not (in_competition_mode and real_llm_verified is False):
                # The ZERO-success case above either already raised or (after a successful retry)
                # no longer applies here -- this branch is the ordinary "some real LLM evidence
                # exists" path, dev/mock included.
                fallback_rate = state.llm_fallback_rate
                if fallback_rate is not None and fallback_rate >= _HIGH_FALLBACK_RATE_THRESHOLD:
                    print(
                        f"WARNING: {state.llm_fallback_count}/{state.llm_call_count} turns used "
                        f"deterministic fallback for case={obs.case_id} (fallback rate "
                        f"{fallback_rate:.0%}) -- the configured LLM provider may not be reliably "
                        "reachable; run scripts/preflight_competition.py before submitting.",
                        file=sys.stderr,
                    )

        return action_to_competition(obs.case_id, action, real_llm_verified=real_llm_verified).model_dump()
