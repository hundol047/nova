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
from typing import Dict, Optional

from nova_agent.action_selector import AgentAction
from nova_agent.orchestrator import DoctorAgent
from nova_agent.state import PatientState

from competition.schema import CompetitionAction, CompetitionObservation

log = logging.getLogger("competition.adapter")


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


def action_to_competition(case_id: str, action: AgentAction) -> CompetitionAction:
    return CompetitionAction(case_id=case_id, action_type=action.action_type, content=action.content,
                              metadata={"key": action.key, "rationale": action.rationale})


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
        if action.action_type == "DIAGNOSE":
            self._pending_actions.pop(obs.case_id, None)

        return action_to_competition(obs.case_id, action).model_dump()
