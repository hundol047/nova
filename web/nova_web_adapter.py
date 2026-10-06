"""Thin adapter between the browser workspace (nova_app.py) and the SAME clinical reasoning core
every other entry point uses -- nova_agent.orchestrator.DoctorAgent. This is deliberately NOT a
second reasoning engine: it never re-implements action selection, differential ranking, or safety
logic. It only translates between Streamlit-friendly plain data (dicts/dataclasses) and the
DoctorAgent/PatientState objects, the same role competition/adapter.py plays for the competition
environment and backend/app/services/nova_service.py plays for the hospital backend.

    Browser UI (nova_app.py)
        |
    NovaWebSession (this module)
        |
    nova_agent.orchestrator.DoctorAgent  <-- the ONE clinical reasoning core

Kept out of submission/ (see scripts/build_nova_submission.py) and out of the competition
package -- this is a development/demo/testing surface only, never part of the competition protocol
or the official submission.
"""

from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from nova_agent.action_selector import AgentAction  # noqa: E402
from nova_agent.config import get_config  # noqa: E402
from nova_agent.orchestrator import DoctorAgent  # noqa: E402
from nova_agent.state import Demographics, PatientState  # noqa: E402


@dataclass
class TurnRecord:
    """One completed ASK/EXAM/TEST/DIAGNOSE turn, for the chat-style transcript."""

    turn: int
    action_type: str
    key: str
    content: str
    rationale: str
    result: str = ""


@dataclass
class NovaWebSession:
    """Owns exactly one DoctorAgent + PatientState pair for the lifetime of one browser case.
    nova_app.py stores ONE of these in st.session_state -- never reconstructed on a Streamlit
    rerun, so the case's turn history/differential/LLM counters genuinely persist across every
    widget interaction (spec: reruns must not erase PatientState)."""

    agent: DoctorAgent
    state: PatientState
    transcript: List[TurnRecord] = field(default_factory=list)
    pending_action: Optional[AgentAction] = None
    finished: bool = False

    @classmethod
    def start(cls, *, chief_complaint: str, age: Optional[int], sex: Optional[str],
              initial_vitals: str = "", history: str = "", medications: str = "",
              lang: str = "en") -> "NovaWebSession":
        agent = DoctorAgent(lang=lang)
        case_id = f"web-{uuid.uuid4().hex[:10]}"
        state = agent.new_case(case_id=case_id, chief_complaint=chief_complaint,
                                demographics={"age": age, "sex": sex})
        # Optional intake fields volunteered up front (spec: "initial vitals/history/medications")
        # are recorded through the SAME state.record_* methods a real ASK/EXAM turn would use, not
        # injected as a special-cased field only the web UI understands -- so the differential
        # engine sees them exactly like any other elicited finding.
        if history.strip():
            state.past_medical_history.append(history.strip())
        if medications.strip():
            state.medication_text.append(medications.strip())
        session = cls(agent=agent, state=state)
        if initial_vitals.strip():
            session.state.record_exam("vital_signs", initial_vitals.strip())
            session.transcript.append(TurnRecord(
                turn=session.state.turn_count, action_type="EXAM", key="vital_signs",
                content="Initial vital signs", rationale="Provided at intake.",
                result=initial_vitals.strip(),
            ))
        return session

    def decide_next(self) -> AgentAction:
        """Asks the SAME DoctorAgent.decide() every other entry point calls. Never invented here."""
        action, _llm_output, _differential = self.agent.decide(self.state)
        self.pending_action = action
        if action.action_type == "DIAGNOSE":
            self.agent.observe(self.state, action, result=action.rationale)
            self.finished = True
        return action

    def submit_result(self, result: str) -> None:
        """Records the clinician/patient's answer to the currently pending ASK/EXAM/TEST action --
        the ONLY way free text enters PatientState here, exactly like the CLI's observe() call."""
        if self.pending_action is None or self.finished:
            return
        action = self.pending_action
        self.agent.observe(self.state, action, result=result)
        self.transcript.append(TurnRecord(
            turn=self.state.turn_count, action_type=action.action_type, key=action.key,
            content=action.content, rationale=action.rationale, result=result,
        ))
        self.pending_action = None

    def provider_status(self) -> dict:
        cfg = get_config()
        return {
            "provider": cfg.llm_provider,
            "is_mock": cfg.llm_provider == "mock",
            "llm_call_count": self.state.llm_call_count,
            "llm_success_count": self.state.llm_success_count,
            "llm_failure_count": self.state.llm_failure_count,
            "llm_fallback_count": self.state.llm_fallback_count,
        }
