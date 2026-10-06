"""Preliminary-round (예선) rules from the organizer briefing of 2026-10-06:
SAY <= 30 characters and one question; EXAM one maneuver; no TEST; vitals handed over at the start;
a SOAP note recorded from what was actually asked/examined; 50 turns and 20 minutes per case; a
bounded number of model calls. Pure rule/format tests plus one full mock encounter."""

from __future__ import annotations

import time

import pytest

from competition.adapter import NovaCompetitionAgent
from evaluation.generalization_dev_cases_round_m import ROUND_M_CASES
from nova_agent.action_selector import AgentAction
from nova_agent.config import (PRELIMINARY_CASE_SECONDS, PRELIMINARY_MAX_LLM_CALLS_PER_CASE,
                               PRELIMINARY_MAX_TURNS, effective_max_turns)
from nova_agent.llm_client import MockLLMClient
from nova_agent.orchestrator import DoctorAgent
from nova_agent.preliminary import (SAY_MAX_CHARS, detect_language, exam_request_text, explanation_text,
                                    fit_say, say_text)
from nova_agent.soap import build_soap
from nova_agent.state import PatientState
from nova_agent.taxonomy import EXAM_CATALOG, QUESTION_CATALOG

LANGS = ("ko", "en", "ja", "zh")


@pytest.mark.parametrize("lang", LANGS)
def test_every_core_question_fits_the_say_limit_and_asks_one_thing(lang):
    for category in QUESTION_CATALOG:
        text = say_text(category, lang)
        assert 0 < len(text) <= SAY_MAX_CHARS, (category, lang, text)
        assert text.count("?") + text.count("？") <= 1, text


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("feature", ["fever", "neck stiffness", "pain radiating to the left arm or jaw",
                                     "severe abdominal pain out of proportion to examination"])
def test_feature_questions_always_fit_even_for_long_feature_names(lang, feature):
    assert len(say_text(f"associated_symptoms:{feature}", lang)) <= SAY_MAX_CHARS


def test_fit_say_trims_at_a_word_boundary_and_never_exceeds_the_limit():
    long = "Please tell me in detail about every single symptom you have had this week"
    out = fit_say(long)
    assert len(out) <= SAY_MAX_CHARS and not out.endswith(" ")


@pytest.mark.parametrize("lang", LANGS)
def test_closing_explanation_fits_even_with_a_very_long_diagnosis_name(lang):
    for name in ("Gout", "Acute Coronary Syndrome (ST-elevation myocardial infarction)", "급성 관상동맥 증후군"):
        assert len(explanation_text(name, lang)) <= SAY_MAX_CHARS


def test_every_exam_has_a_single_sentence_request_in_each_language():
    for exam_id in EXAM_CATALOG:
        for lang in LANGS:
            text = exam_request_text(exam_id, lang)
            assert text and "\n" not in text


def test_language_is_detected_from_the_first_statement():
    assert detect_language("배가 아파요") == "ko"
    assert detect_language("お腹が痛いです") == "ja"
    assert detect_language("我肚子痛") == "zh"
    assert detect_language("My stomach hurts") == "en"


def test_preliminary_turn_and_time_limits():
    assert effective_max_turns(80, 50, PRELIMINARY_MAX_TURNS) == 50
    assert PRELIMINARY_CASE_SECONDS == 20 * 60
    agent = DoctorAgent(llm_client=MockLLMClient())
    state = agent.new_case("c", "headache", {"age": 30, "sex": "male"}, preliminary=True)
    assert state.max_turns == 50 and state.time_limit_seconds == PRELIMINARY_CASE_SECONDS and state.preliminary_rules
    legacy = agent.new_case("c", "headache", {"age": 30, "sex": "male"}, preliminary=False)
    assert legacy.max_turns == 60 and legacy.time_limit_seconds is None and not legacy.preliminary_rules


def test_initial_vitals_cost_no_turn_and_count_as_the_vital_sign_exam():
    state = PatientState(case_id="v", chief_complaint="chest pain", preliminary_rules=True)
    state.record_initial_vitals("BP 88/52, HR 126, RR 26, Temp 38.9, SpO2 91%")
    assert state.turn_count == 0 and state.exam_done("vital_signs")
    assert state.vital_sign_findings, "abnormal vitals must reach the evidence bag"


def test_rejected_exam_costs_no_turn_contributes_no_finding_and_is_not_repeated():
    state = PatientState(case_id="r", chief_complaint="cough", preliminary_rules=True)
    state.record_exam_rejected("pelvic_exam")
    assert state.turn_count == 0 and state.exam_done("pelvic_exam")
    assert "pelvic_exam" not in state.physical_examinations


def test_say_costs_one_turn_and_its_reply_is_not_absorbed_as_evidence():
    state = PatientState(case_id="s", chief_complaint="cough", preliminary_rules=True)
    state.record_say("This may be a cold.", "I have chest pain and fever now")
    assert state.turn_count == 1
    assert not state.pertinent_positives and not state.associated_symptoms


def test_no_test_action_is_ever_selected_under_preliminary_rules():
    case = next(c for c in ROUND_M_CASES if c.case_id == "RoundM_045")  # a lab-led case
    agent = DoctorAgent(llm_client=MockLLMClient())
    state = agent.new_case(case.case_id, case.chief_complaint, case.demographics, preliminary=True)
    kinds = []
    for _ in range(state.max_turns):
        action, _, _ = agent.decide(state)
        kinds.append(action.action_type)
        if action.action_type == "DIAGNOSE":
            break
        reply = {"ASK": case.answers.get(action.key, case.default_answer),
                 "EXAM": case.exam_results.get(action.key, case.default_exam_result)}[action.action_type]
        agent.observe(state, action, reply)
    assert "TEST" not in kinds and kinds[-1] == "DIAGNOSE"


def test_time_budget_forces_the_diagnosis():
    agent = DoctorAgent(llm_client=MockLLMClient())
    state = agent.new_case("t", "belly pain", {"age": 40, "sex": "female"}, preliminary=True)
    state.time_limit_seconds = 1.0
    state.case_started_at_unix = time.time() - 10
    action, _, _ = agent.decide(state)
    assert action.action_type == "DIAGNOSE"


def test_preliminary_model_call_schedule_is_bounded_and_always_calls_first_and_last():
    agent = DoctorAgent(llm_client=MockLLMClient())
    state = agent.new_case("m", "headache", {"age": 30, "sex": "male"}, preliminary=True)
    ask = AgentAction(action_type="ASK", key="onset", content="x", rationale="")
    dx = AgentAction(action_type="DIAGNOSE", key="migraine", content="Migraine", rationale="")
    assert agent._preliminary_llm_call_due(state, ask)  # the first call is mandatory
    state.llm_call_count = 3
    state.turn_count = 5
    assert not agent._preliminary_llm_call_due(state, ask)  # off-schedule turn
    assert agent._preliminary_llm_call_due(state, dx)  # the submitting turn always calls
    state.llm_call_count = PRELIMINARY_MAX_LLM_CALLS_PER_CASE
    assert not agent._preliminary_llm_call_due(state, dx)  # hard cap


def test_soap_is_rebuilt_from_the_turn_log_and_records_only_what_was_asked():
    state = PatientState(case_id="p", chief_complaint="Pain in the upper belly", preliminary_rules=True)
    state.record_initial_vitals("BP 120/80, HR 80, Temp 36.8")
    state.record_ask("past_medical_history", "Any past illnesses?", "high blood pressure")
    state.record_ask("allergy", "Any allergies?", "No, I don't have that.")
    state.record_exam("abdominal_exam", "tender in the epigastrium")
    note = build_soap(state, [], "en")
    assert "high blood pressure" in note["S"] and "denied" in note["S"]
    assert "Family history: not asked" in note["S"] and "Social history: not asked" in note["S"]
    assert "[T0 at presentation]" in note["O"] and "[T3]" in note["O"] and "epigastrium" in note["O"]
    assert "unavailable" in note["O"] and "mg" not in note["P"]


def test_full_mock_encounter_obeys_every_preliminary_rule():
    case = next(c for c in ROUND_M_CASES if c.case_id == "RoundM_044")
    agent = NovaCompetitionAgent(agent=DoctorAgent(llm_client=MockLLMClient()), preliminary=True)
    obs = {"case_id": case.case_id, "observation_type": "initial", "chief_complaint": case.chief_complaint,
           "demographics": case.demographics, "vital_signs": "BP 118/74, HR 96, Temp 37.9"}
    actions = []
    for _ in range(60):
        act = agent.act(obs)
        actions.append(act)
        if act["action_type"] == "DIAGNOSE":
            break
        pending = agent._pending_actions[case.case_id]
        if act["action_type"] == "SAY":
            reply = case.answers.get(pending.key, case.default_answer) if pending.key != "explanation" else "OK"
            obs = {"case_id": case.case_id, "observation_type": "say_response", "content": reply}
        else:
            obs = {"case_id": case.case_id, "observation_type": "exam_result",
                   "content": case.exam_results.get(pending.key, case.default_exam_result)}
    kinds = [a["action_type"] for a in actions]
    assert kinds[-1] == "DIAGNOSE" and "TEST" not in kinds and "ASK" not in kinds
    assert all(len(a["content"]) <= SAY_MAX_CHARS for a in actions if a["action_type"] == "SAY")
    assert len(actions) - 1 <= PRELIMINARY_MAX_TURNS
    assert kinds[-2] == "SAY", "the working diagnosis is explained in dialogue right before the note"
    final = actions[-1]
    assert set(final["soap"]) == {"S", "O", "A", "P"} and final["primary_diagnosis"]
    assert "[T0 at presentation]" in final["soap"]["O"]
    assert not any(a["metadata"].get("key") == "vital_signs" for a in actions), "vitals were given at the start"


def test_exam_rejection_costs_no_turn_through_the_adapter():
    case = next(c for c in ROUND_M_CASES if c.case_id == "RoundM_044")
    agent = NovaCompetitionAgent(agent=DoctorAgent(llm_client=MockLLMClient()), preliminary=True)
    obs = {"case_id": case.case_id, "observation_type": "initial", "chief_complaint": case.chief_complaint,
           "demographics": case.demographics}
    for _ in range(40):
        act = agent.act(obs)
        if act["action_type"] == "EXAM":
            break
        pending = agent._pending_actions[case.case_id]
        obs = {"case_id": case.case_id, "observation_type": "say_response",
               "content": case.answers.get(pending.key, case.default_answer)}
    assert act["action_type"] == "EXAM"
    turns_before = agent._states[case.case_id].turn_count
    exam_key = agent._pending_actions[case.case_id].key
    agent.act({"case_id": case.case_id, "observation_type": "exam_result", "content": "", "raw": {"rejected": True}})
    state = agent._states[case.case_id]
    assert state.turn_count == turns_before and exam_key in state.rejected_exams
