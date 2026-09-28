"""N.O.V.A. 2026 -- Autonomous Clinical Reasoning Doctor Agent
Standalone browser workspace for development / manual testing / demo / clinical reasoning
visualization. This is NOT the competition submission interface (see submission/run.py for that)
and is deliberately excluded from submission/ (scripts/build_nova_submission.py never copies web/).

Uses the SAME nova_agent.orchestrator.DoctorAgent every other entry point uses, through the thin
NovaWebSession adapter in nova_web_adapter.py -- there is only one clinical reasoning core.

Run:
    python -m streamlit run web/nova_app.py
Then open http://localhost:8501

Set NOVA_WEB_DEBUG=1 to also show candidate actions / utility components / safety findings /
normalization results for development. Default UI stays clean (no internal scoring exposed).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from nova_web_adapter import NovaWebSession  # noqa: E402

DEBUG = os.getenv("NOVA_WEB_DEBUG", "0").lower() in ("1", "true", "yes")

st.set_page_config(page_title="N.O.V.A. 2026 Clinical Reasoning Workspace", page_icon="\U0001FA7A",
                    layout="wide")

_UI_TEXT = {
    "en": {
        "title": "N.O.V.A. 2026", "subtitle": "Autonomous Clinical Reasoning Doctor Agent",
        "banner": "Decision Support · Not Autonomous Medical Diagnosis · Clinician Review Required",
        "start_case": "Start Case", "new_patient": "New Patient / Reset Case",
        "chief_complaint": "Chief Complaint", "age": "Age", "sex": "Sex",
        "initial_vitals": "Initial vital signs (optional)", "history": "Past medical history (optional)",
        "medications": "Current medications (optional)",
        "patient_answer": "Patient Answer", "exam_result": "Examination Result",
        "test_result": "Test Result", "submit": "Submit", "final_diagnosis": "FINAL DIAGNOSIS",
        "differential": "Current Differential", "must_not_miss": "Must-Not-Miss",
        "turn_count": "Turn Count", "remaining_turns": "Remaining Turns",
        "llm_provider": "LLM Provider", "successful_calls": "Successful LLM Calls",
        "current_mode": "Current Mode", "why_this_action": "Why this action?",
        "mock_warning": "DEVELOPMENT MODE — MOCK LLM — NOT A REAL LLM",
        "no_case": "No active case. Start one from the left panel.",
    },
    "ko": {
        "title": "N.O.V.A. 2026", "subtitle": "자율 임상 추론 닥터 에이전트",
        "banner": "의사결정 지원 · 자동 진단이 아님 · 임상의의 검토 필수",
        "start_case": "새 사례 시작", "new_patient": "새 환자 / 사례 초기화",
        "chief_complaint": "주소증", "age": "나이", "sex": "성별",
        "initial_vitals": "초기 활력징후 (선택)", "history": "과거병력 (선택)",
        "medications": "복용 약물 (선택)",
        "patient_answer": "환자 답변", "exam_result": "진찰 결과",
        "test_result": "검사 결과", "submit": "제출", "final_diagnosis": "최종 진단",
        "differential": "현재 감별진단", "must_not_miss": "놓치면 안 되는 진단",
        "turn_count": "턴 수", "remaining_turns": "남은 턴",
        "llm_provider": "LLM 제공자", "successful_calls": "성공한 LLM 호출",
        "current_mode": "현재 모드", "why_this_action": "왜 이 행동인가요?",
        "mock_warning": "개발 모드 — 모의(MOCK) LLM — 실제 LLM이 아닙니다",
        "no_case": "활성 사례가 없습니다. 왼쪽 패널에서 새 사례를 시작하세요.",
    },
}


def _t(key: str) -> str:
    lang = st.session_state.get("ui_lang", "en")
    return _UI_TEXT.get(lang, _UI_TEXT["en"]).get(key, _UI_TEXT["en"][key])


def _reset_session() -> None:
    st.session_state.pop("nova_session", None)
    st.session_state.pop("pending_action_type", None)


def _action_type_label(action_type: str) -> str:
    return {"ASK": "\U0001F4AC ASK", "EXAM": "\U0001FA7A EXAM", "TEST": "\U0001F9EA TEST",
            "DIAGNOSE": "✅ DIAGNOSE"}.get(action_type, action_type)


def _render_sidebar_intake() -> None:
    st.sidebar.markdown(f"## {_t('title')}")
    st.sidebar.caption(_t("subtitle"))
    st.sidebar.selectbox("Language / 언어", options=["en", "ko"], key="ui_lang",
                          format_func=lambda v: {"en": "English", "ko": "한국어"}[v])

    if st.session_state.get("nova_session") is not None:
        if st.sidebar.button(_t("new_patient"), type="secondary", use_container_width=True):
            _reset_session()
            st.rerun()
        return

    with st.sidebar.form("intake_form"):
        chief_complaint = st.text_area(_t("chief_complaint"), height=80,
                                        placeholder="e.g. sudden severe chest pain radiating to the back")
        col1, col2 = st.columns(2)
        age = col1.number_input(_t("age"), min_value=0, max_value=120, value=45, step=1)
        sex = col2.selectbox(_t("sex"), options=["male", "female"])
        initial_vitals = st.text_input(_t("initial_vitals"),
                                        placeholder="BP 120/80, HR 88, RR 16, SpO2 98%")
        history = st.text_input(_t("history"), placeholder="hypertension, diabetes")
        medications = st.text_input(_t("medications"), placeholder="metformin, lisinopril")
        submitted = st.form_submit_button(_t("start_case"), type="primary", use_container_width=True)

    if submitted:
        if not chief_complaint.strip():
            st.sidebar.error("Chief complaint is required.")
            return
        try:
            session = NovaWebSession.start(
                chief_complaint=chief_complaint.strip(), age=int(age), sex=sex,
                initial_vitals=initial_vitals, history=history, medications=medications,
                lang=st.session_state.get("ui_lang", "en"),
            )
        except Exception as exc:  # noqa: BLE001 - never crash the whole UI on a bad case start
            st.sidebar.error(f"Could not start case: {exc}")
            if DEBUG:
                st.sidebar.exception(exc)
            return
        st.session_state.nova_session = session
        st.session_state.pending_action_type = None
        st.rerun()


def _render_status_panel(session: NovaWebSession) -> None:
    state = session.state
    provider = session.provider_status()

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**{_t('turn_count')}:** {state.turn_count} / {state.max_turns}")
    st.sidebar.markdown(f"**{_t('remaining_turns')}:** {state.remaining_turns}")
    st.sidebar.progress(min(1.0, state.turn_count / max(1, state.max_turns)))

    st.sidebar.markdown(f"**{_t('llm_provider')}:** `{provider['provider']}`")
    if provider["is_mock"]:
        st.sidebar.warning(_t("mock_warning"), icon="⚠️")
    else:
        st.sidebar.markdown(f"**{_t('successful_calls')}:** {provider['llm_success_count']}")
        st.sidebar.markdown(f"successful: {provider['llm_success_count']} · "
                             f"failed: {provider['llm_failure_count']} · "
                             f"fallback active: {'yes' if provider['llm_fallback_count'] else 'no'}")

    mode_label = "development (mock)" if provider["is_mock"] else f"real LLM ({provider['provider']})"
    st.sidebar.markdown(f"**{_t('current_mode')}:** {mode_label}")

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"### {_t('differential')}")
    if state.current_differential:
        for item in state.current_differential[:6]:
            danger_marker = " ⚠️" if item.dangerous_if_missed else ""
            st.sidebar.markdown(f"{item.rank}. {item.diagnosis}{danger_marker}  \n"
                                 f"&nbsp;&nbsp;&nbsp;&nbsp;*ranking score: {item.confidence_band.lower()}*")
    else:
        st.sidebar.caption("No differential yet.")

    must_not_miss = [d for d in state.current_differential if d.dangerous_if_missed]
    st.sidebar.markdown(f"### {_t('must_not_miss')}")
    if must_not_miss:
        for item in must_not_miss:
            st.sidebar.markdown(f"\U0001F6A8 **{item.diagnosis}** — unresolved")
    else:
        st.sidebar.caption("None currently flagged.")


def _render_debug_panel(session: NovaWebSession) -> None:
    if not DEBUG:
        return
    with st.expander("\U0001F41B Debug details (NOVA_WEB_DEBUG=1)"):
        st.write("Candidate actions from the last decide() call are not retained on the session "
                 "object (only the chosen action is) -- this panel shows what IS retained.")
        st.json({
            "case_id": session.state.case_id,
            "llm_call_count": session.state.llm_call_count,
            "llm_success_count": session.state.llm_success_count,
            "llm_failure_count": session.state.llm_failure_count,
            "performed_action_count": len(session.state.performed_actions),
            "current_differential": [d.model_dump() for d in session.state.current_differential],
        })


def _render_diagnose(session: NovaWebSession) -> None:
    st.success(f"### {_t('final_diagnosis')}: {session.state.final_diagnosis}")
    if session.state.final_diagnosis_rationale:
        st.markdown(f"**{_t('why_this_action')}** {session.state.final_diagnosis_rationale}")
    st.info(_t("banner"))


def _render_pending_action(session: NovaWebSession) -> None:
    action = session.pending_action
    st.markdown(f"## N.O.V.A.")
    st.markdown(f"**[{_action_type_label(action.action_type)}]**")
    st.markdown(f"### {action.content}")
    if action.rationale:
        with st.expander(_t("why_this_action")):
            st.write(action.rationale)

    field_label = {"ASK": _t("patient_answer"), "EXAM": _t("exam_result"),
                   "TEST": _t("test_result")}.get(action.action_type, "Result")

    with st.form(f"result_form_{session.state.turn_count}"):
        result_text = st.text_area(field_label, height=80, key=f"result_input_{session.state.turn_count}")
        submitted = st.form_submit_button(_t("submit"), type="primary")
    if submitted:
        if not result_text.strip():
            st.warning("Please enter a value before submitting.")
            return
        try:
            session.submit_result(result_text.strip())
        except Exception as exc:  # noqa: BLE001 - never crash the whole UI on a bad observation
            st.error("Could not record that result. Please try again.")
            if DEBUG:
                st.exception(exc)
            return
        st.rerun()


def _render_transcript(session: NovaWebSession) -> None:
    if not session.transcript:
        return
    st.markdown("---")
    st.markdown("#### Case history")
    for turn in session.transcript:
        with st.chat_message("assistant"):
            st.markdown(f"**[{_action_type_label(turn.action_type)}]** {turn.content}")
        with st.chat_message("user"):
            st.markdown(turn.result)


def main() -> None:
    st.session_state.setdefault("ui_lang", "en")
    _render_sidebar_intake()

    st.markdown(f"# {_t('title')} — {_t('subtitle')}")
    st.caption(_t("banner"))

    session: NovaWebSession | None = st.session_state.get("nova_session")
    if session is None:
        st.info(_t("no_case"))
        return

    _render_status_panel(session)

    if session.finished:
        _render_diagnose(session)
        _render_transcript(session)
        _render_debug_panel(session)
        return

    if session.pending_action is None:
        try:
            session.decide_next()
        except Exception as exc:  # noqa: BLE001 - never crash the whole UI on a decide() failure
            st.error("N.O.V.A. could not determine the next action. Please use New Patient / Reset Case.")
            if DEBUG:
                st.exception(exc)
            return
        st.rerun()

    if session.finished:
        _render_diagnose(session)
    else:
        _render_pending_action(session)

    _render_transcript(session)
    _render_debug_panel(session)


if __name__ == "__main__":
    main()
