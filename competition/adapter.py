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
        self._pending_actions[obs.case_id] = action
        real_llm_verified: Optional[bool] = None
        if action.action_type == "DIAGNOSE":
            self._pending_actions.pop(obs.case_id, None)
            in_competition_mode = get_config().llm_provider != "mock"
            real_llm_verified = state.real_llm_ever_succeeded
            if in_competition_mode and real_llm_verified is False:
                # Every real-LLM attempt this case failed, even after bounded retry -- the final
                # answer is deterministic-fallback-only. This is NOT the same as "some fallback
                # rate" below: it means the real LLM contributed literally nothing to this case,
                # so the result must never be mistaken for a normal, LLM-backed competition
                # completion (spec: dev/mock mode may ride the deterministic fallback freely;
                # competition mode may not silently do the same for an entire case).
                print(
                    f"ERROR: case={obs.case_id} reached DIAGNOSE with ZERO successful real-LLM "
                    f"calls ({state.llm_call_count} attempted, all failed even after bounded "
                    "retry). This result is deterministic-fallback-only and must NOT be treated "
                    "as a normal competition completion -- treat it as a runtime failure. Run "
                    "scripts/preflight_competition.py before submitting.",
                    file=sys.stderr,
                )
            else:
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
