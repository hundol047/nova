"""One test per rule of the 2026-10-06 opening-ceremony briefing (slides supplied by the team), run against
the always-on submission profile. The wire encoding is still a PLACEHOLDER, so these check behaviour, not format."""

from __future__ import annotations

import pytest

from competition.submission_profile import build_submission_agent
from evaluation.generalization_dev_cases_round_m import ROUND_M_CASES
from nova_agent.config import (PRELIMINARY_CASE_SECONDS, PRELIMINARY_MAX_LLM_CALLS_PER_CASE, PRELIMINARY_MAX_TURNS)
from nova_agent.llm_client import MockLLMClient
from nova_agent.orchestrator import DoctorAgent
from nova_agent.preliminary import SAY_MAX_CHARS
from nova_agent.soap import build_soap
from nova_agent.state import PatientState


def _case(case_id):
    return next(c for c in ROUND_M_CASES if c.case_id == case_id)


def _encounter(case_id="RoundM_044", exam_override=None, answer_override=None):
    case = _case(case_id)
    agent = build_submission_agent(DoctorAgent(llm_client=MockLLMClient()))
    obs = {"case_id": case_id, "observation_type": "initial", "chief_complaint": case.chief_complaint,
           "demographics": case.demographics, "vital_signs": "BP 130/82, HR 104, RR 18, Temp 38.1, SpO2 97%"}
    actions, states = [], {}
    for _ in range(PRELIMINARY_MAX_TURNS + 12):
        act = agent.act(obs)
        actions.append(act)
        state = agent._states.get(case_id)
        if state is not None:
            states[case_id] = state
        if act["action_type"] == "DIAGNOSE":
            break
        pending = agent._pending_actions[case_id]
        if act["action_type"] == "SAY":
            reply = (answer_override or {}).get(pending.key) or case.answers.get(pending.key, case.default_answer)
            obs = {"case_id": case_id, "observation_type": "say_response", "content": reply}
        else:
            reply = (exam_override or {}).get(pending.key) or case.exam_results.get(pending.key, case.default_exam_result)
            obs = {"case_id": case_id, "observation_type": "exam_result", "content": reply}
    return actions, states[case_id], agent


def test_actions_are_only_say_exam_diagnose_and_never_test():
    actions, _state, _ = _encounter()
    assert {a["action_type"] for a in actions} <= {"SAY", "EXAM", "DIAGNOSE"}
    assert actions[-1]["action_type"] == "DIAGNOSE"


def test_at_most_50_turns_and_the_note_comes_last():
    actions, state, _ = _encounter()
    assert len([a for a in actions if a["action_type"] != "DIAGNOSE"]) <= PRELIMINARY_MAX_TURNS
    assert state.max_turns == PRELIMINARY_MAX_TURNS and state.time_limit_seconds == PRELIMINARY_CASE_SECONDS


def test_say_is_at_most_30_characters_and_asks_one_thing():
    actions, _state, _ = _encounter()
    for a in actions:
        if a["action_type"] == "SAY":
            assert 0 < len(a["content"]) <= SAY_MAX_CHARS, a["content"]
            assert a["content"].count("?") + a["content"].count("？") <= 1, a["content"]


def test_exam_requests_one_maneuver_at_a_time():
    actions, _state, _ = _encounter()
    exams = [a for a in actions if a["action_type"] == "EXAM"]
    assert exams, "this case is expected to include at least one physical examination"
    for a in exams:
        assert "\n" not in a["content"] and " and " not in a["content"].lower().replace("and/or", ""), a["content"]


def test_initial_vitals_are_used_and_dated_turn_zero_in_the_note():
    _actions, state, _ = _encounter()
    assert state.initial_vitals_text
    soap = build_soap(state, [], "en")
    assert "[T0" in soap["O"] and "BP 130/82" in soap["O"]


def test_exam_findings_carry_the_turn_number_they_arrived_in():
    _actions, state, _ = _encounter()
    soap = build_soap(state, [], "en")
    exam_turns = [t.turn for t in state.performed_actions if t.action_type == "EXAM"]
    assert exam_turns
    for turn in exam_turns:
        assert f"[T{turn}]" in soap["O"]


def test_note_records_only_what_was_obtained_and_marks_what_was_not_asked():
    _actions, state, _ = _encounter()
    soap = build_soap(state, [], "en")
    asked_categories = {t.key.partition(":")[0] for t in state.performed_actions if t.action_type == "ASK"}
    if "family_history" not in asked_categories:
        assert "Family history: not asked" in soap["S"]
    if "allergy" not in asked_categories:
        assert "Allergies: not asked" in soap["S"]


def test_unrequested_tests_are_never_reported_as_results():
    _actions, state, _ = _encounter()
    soap = build_soap(state, [], "en")
    assert "no test results" in soap["O"]
    assert not state.completed_tests


def test_rejected_and_unclear_states_are_distinguished():
    state = PatientState(case_id="x", chief_complaint="cough", preliminary_rules=True)
    state.record_ask("past_medical_history", "?", "I am not sure, maybe diabetes?")
    state.record_ask("allergy", "?", "No, none.")
    state.record_exam_rejected("lung_auscultation")
    soap = build_soap(state, [], "en")
    assert "unclear (needs confirmation)" in soap["S"]
    assert "denied" in soap["S"]
    assert "request rejected (no result)" in soap["O"]


def test_patient_education_is_recorded_only_when_it_was_said_during_the_visit():
    state = PatientState(case_id="x", chief_complaint="cough", preliminary_rules=True)
    assert "not performed during the visit" in build_soap(state, [], "en")["P"]
    state.record_say("You may have pneumonia.", "OK", key="explanation")
    state.record_say("Return if worse.", "OK", key="plan_explanation")
    plan = build_soap(state, [], "en")["P"]
    assert "[T1]" in plan and "[T2]" in plan and "not performed" not in plan


def test_full_encounter_ends_with_diagnosis_and_next_step_said_to_the_patient_and_matches_the_note():
    actions, state, _ = _encounter()
    kinds = [a["action_type"] for a in actions]
    assert kinds[-1] == "DIAGNOSE" and kinds[-2] == "SAY" and kinds[-3] == "SAY"
    keys = [t.key for t in state.performed_actions if t.action_type == "SAY"]
    assert "explanation" in keys and "plan_explanation" in keys
    soap_text = actions[-1]["content"]
    assert "Patient education" in soap_text and "not performed during the visit" not in soap_text


def test_exactly_one_primary_diagnosis_accompanies_the_note():
    actions, _state, _ = _encounter()
    final = actions[-1]
    assert final["action_type"] == "DIAGNOSE"
    assert final.get("primary_diagnosis")
    assert "\n" not in final["primary_diagnosis"]


def test_model_call_budget_is_an_internal_policy_not_an_official_limit():
    import pathlib
    text = (pathlib.Path(__file__).resolve().parents[1] / "nova_agent/config.py").read_text(encoding="utf-8")
    assert "INTERNAL operating policy, not an organizer limit" in text
    assert PRELIMINARY_MAX_LLM_CALLS_PER_CASE == 8


def test_a_feature_question_is_complete_or_generic_never_a_truncated_fragment():
    """Every KB feature, in English: the 30-character SAY either contains every content word of the feature
    (possibly with filler words removed) or is the generic follow-up -- never "blood pressure falls on?"."""
    from nova_agent.knowledge.retrieval import all_diseases
    from nova_agent.matching import _content_words
    from nova_agent.preliminary import say_text
    generic = say_text("associated_symptoms", "en")
    features = {f for e in all_diseases().values() for f in e.get("typical_features", []) + e.get("confirmatory_findings", [])}
    assert len(features) > 100
    complete = 0
    for feature in sorted(features):
        text = say_text("associated_symptoms:" + feature.replace(" ", "_"), "en")
        assert len(text) <= SAY_MAX_CHARS
        if text == generic:
            continue
        from nova_agent.preliminary import _FILLER_WORDS
        missing = [w for w in _content_words(feature) if w not in _FILLER_WORDS and w not in _content_words(text.lower())]
        assert not missing, (feature, text, missing)
        complete += 1
    assert complete > len(features) * 0.7   # most features can be asked faithfully
