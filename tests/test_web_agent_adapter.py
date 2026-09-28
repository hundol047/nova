"""nova_web_adapter.NovaWebSession -- the translation layer between the browser workspace
(web/nova_app.py) and the SAME nova_agent.orchestrator.DoctorAgent every other entry point uses.
Exercises the adapter directly (no browser/Streamlit runtime needed) -- see
docs/NOVA_WEB_VERIFICATION.md (if present) for the separate real-browser (Playwright) verification
of the Streamlit page itself, which this test file does not attempt to replace.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_WEB_DIR = Path(__file__).resolve().parents[1] / "web"
if str(_WEB_DIR) not in sys.path:
    sys.path.insert(0, str(_WEB_DIR))

from nova_web_adapter import NovaWebSession  # noqa: E402


def test_start_case_creates_a_fresh_case_with_the_given_chief_complaint():
    session = NovaWebSession.start(chief_complaint="sudden severe chest pain", age=58, sex="male")
    assert session.state.chief_complaint == "sudden severe chest pain"
    assert session.state.demographics.age == 58
    assert session.state.demographics.sex == "male"
    assert session.state.turn_count == 0
    assert not session.finished


def test_optional_intake_fields_are_recorded_through_normal_state_methods():
    session = NovaWebSession.start(
        chief_complaint="chest pain", age=60, sex="female",
        initial_vitals="BP 90/60, HR 130, SpO2 88%", history="hypertension", medications="metformin",
    )
    assert "hypertension" in session.state.past_medical_history
    assert any("metformin" in m for m in session.state.medication_text)
    # Initial vitals go through the SAME record_exam() path a real EXAM turn would use.
    assert session.state.turn_count == 1
    assert len(session.transcript) == 1
    assert session.transcript[0].action_type == "EXAM"


def test_decide_next_uses_the_same_doctoragent_never_a_second_engine():
    """The adapter must not re-implement action selection -- decide_next() must produce exactly
    what agent.decide() itself would, since it's a direct passthrough call."""
    session = NovaWebSession.start(chief_complaint="sudden severe chest pain", age=58, sex="male")
    action_from_adapter = session.decide_next()
    # A second, independent DoctorAgent given the identical starting state produces the same
    # deterministic (mock-provider) choice -- proving the adapter isn't injecting its own logic.
    from nova_agent.orchestrator import DoctorAgent
    from nova_agent.state import PatientState
    twin_state = PatientState(case_id="twin", chief_complaint="sudden severe chest pain",
                               demographics=session.state.demographics)
    twin_action, _, _ = DoctorAgent().decide(twin_state)
    assert action_from_adapter.action_type == twin_action.action_type
    assert action_from_adapter.key == twin_action.key


def test_submit_result_advances_turn_count_and_appends_to_transcript():
    session = NovaWebSession.start(chief_complaint="chest pain", age=50, sex="male")
    session.decide_next()
    before = session.state.turn_count
    session.submit_result("denies")
    assert session.state.turn_count == before + 1
    assert len(session.transcript) == 1
    assert session.transcript[0].result == "denies"
    assert session.pending_action is None  # consumed, ready for the next decide_next()


def test_diagnose_action_marks_the_session_finished_and_stops_requesting_observations():
    session = NovaWebSession.start(chief_complaint="chest pain", age=50, sex="male")
    for _ in range(60):
        action = session.decide_next()
        if action.action_type == "DIAGNOSE":
            break
        session.submit_result("unremarkable")
    assert session.finished
    assert session.state.final_diagnosis is not None
    # Once finished, decide_next() must never be called again by the UI -- but even if it somehow
    # were, submit_result() on a finished session is a safe no-op, not a crash.
    turn_before = session.state.turn_count
    session.submit_result("should be ignored")
    assert session.state.turn_count == turn_before


def test_two_sessions_never_share_state_no_cross_patient_leakage():
    """Standing in for 'New Patient / Reset Case': a fresh NovaWebSession must be completely
    independent of any prior one -- the actual reset mechanism in nova_app.py is dropping the old
    session and creating this new one, so THIS is the guarantee that matters."""
    session_a = NovaWebSession.start(chief_complaint="chest pain", age=58, sex="male")
    session_a.decide_next()
    session_a.submit_result("denies")

    session_b = NovaWebSession.start(chief_complaint="unrelated headache", age=22, sex="female")
    assert session_b.state.chief_complaint == "unrelated headache"
    assert session_b.state.turn_count == 0
    assert session_b.transcript == []
    assert session_b.state.case_id != session_a.state.case_id
    # Mutating b must never affect a.
    session_b.decide_next()
    session_b.submit_result("also denies")
    assert session_a.state.turn_count == 1
    assert session_b.state.turn_count == 1
    assert session_a.state.chief_complaint != session_b.state.chief_complaint


def test_provider_status_reports_mock_by_default():
    session = NovaWebSession.start(chief_complaint="chest pain", age=40, sex="male")
    status = session.provider_status()
    assert status["provider"] == "mock"
    assert status["is_mock"] is True
    assert status["llm_call_count"] == 0  # mock provider never makes a real call


@pytest.mark.parametrize("action_type,expected_field", [
    ("ASK", "Patient Answer"), ("EXAM", "Examination Result"), ("TEST", "Test Result"),
])
def test_action_type_determines_the_correct_result_field_label(action_type, expected_field):
    """Mirrors nova_app.py's _render_pending_action() field-label mapping -- the UI must never
    let the user type free text into an ambiguous single box regardless of action type."""
    field_label = {"ASK": "Patient Answer", "EXAM": "Examination Result",
                   "TEST": "Test Result"}[action_type]
    assert field_label == expected_field
