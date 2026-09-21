"""PLACEHOLDER competition I/O schema.

No official N.O.V.A. 2026 Agent API/interface document was found in this repository or in the
materials available at implementation time. Nothing about scoring, the exact observation/action
JSON shape, or the final-diagnosis submission format has been guessed into the clinical reasoning
engine (nova_agent/) itself -- it only knows about PatientState and AgentAction (see
nova_agent/state.py, nova_agent/action_selector.py).

This module defines a reasonable, generic turn-based protocol so the adapter has something concrete
to translate to/from today. When the official schema is published:
  1. Update (or replace) CompetitionObservation / CompetitionAction below to match it exactly.
  2. Update competition/adapter.py's observation_to_state() / action_to_competition() translation
     logic to match.
  3. Nothing in nova_agent/, evaluation/, or tests/ should need to change, since they only depend
     on PatientState / AgentAction, never on this module.
"""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

ObservationType = Literal["initial", "ask_response", "exam_result", "test_result"]


class CompetitionObservation(BaseModel):
    """One turn's input from the competition environment."""

    case_id: str
    turn: int = 0
    observation_type: ObservationType
    # Present on observation_type == 'initial' only.
    chief_complaint: Optional[str] = None
    demographics: Optional[Dict[str, Any]] = None
    max_turns: Optional[int] = None
    # Present on 'ask_response' / 'exam_result' / 'test_result': the environment's reply to the
    # agent's previous action (patient's answer, exam finding, or test result, as text).
    content: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None  # escape hatch for any field this placeholder didn't anticipate


class CompetitionAction(BaseModel):
    """One turn's output back to the competition environment."""

    case_id: str
    action_type: Literal["ASK", "EXAM", "TEST", "DIAGNOSE"]
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
