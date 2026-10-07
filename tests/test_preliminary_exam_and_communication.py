"""EXAM rejection recovery, patient communication before DIAGNOSE, SAY/EXAM wire discipline (preliminary)."""
import re

import pytest

from competition.adapter import NovaCompetitionAgent
from evaluation.preliminary_driver import Environment, check_wire, run_episode
from evaluation.preliminary_dev_cases import PRELIM_KO_CASES
from evaluation.soap_provenance import check_soap
from nova_agent.llm_client import MockLLMClient
from nova_agent.orchestrator import DoctorAgent
from nova_agent.preliminary import SAY_MAX_CHARS, explanation_text, plan_say_text, rejection_signal, say_text

CASE = {c.case_id: c for c in PRELIM_KO_CASES}["PrelimKo_ChestPain_ACS"]
ALL_EXAMS = frozenset({"vital_signs", "general_appearance", "cardiac_auscultation", "lung_auscultation", "abdominal_exam",
                       "neuro_exam", "meningeal_signs", "skin_exam", "extremity_exam", "costovertebral_tenderness",
                       "pelvic_exam", "mental_status_exam"})


def _exam_keys(ep):
    return [w["metadata"]["key"] for w in ep.wire if w["action_type"] == "EXAM"]


@pytest.mark.parametrize("unsupported", [frozenset({"cardiac_auscultation"}), frozenset({"cardiac_auscultation", "general_appearance"}), ALL_EXAMS])
def test_rejected_exams_are_never_repeated_never_recorded_as_findings_and_case_still_ends(unsupported):
    ep = run_episode(CASE, env=Environment(unsupported_exams=unsupported))
    keys = _exam_keys(ep)
    assert len(keys) == len(set(keys)), "a rejected (or any) examination must never be requested twice"
    assert ep.wire[-1]["action_type"] == "DIAGNOSE" and not ep.violations
    soap = ep.wire[-1]["soap"]
    for key in {k for k in keys if k in unsupported}:
        assert "request rejected" in soap["O"] or "요청 거절됨" in soap["O"]
    assert not re.search(r"Request not supported\.", soap["O"]), "rejection wording must not be copied in as a finding"
    assert ep.result["rejected_exams"] == len([k for k in keys if k in unsupported])


def test_rejection_adds_no_evidence_and_costs_no_turn():
    from nova_agent.action_selector import AgentAction
    agent = NovaCompetitionAgent(agent=DoctorAgent(llm_client=MockLLMClient()), preliminary=True)
    agent.act({"case_id": "r", "observation_type": "initial", "chief_complaint": "I have chest pain. 55 year old man.",
               "demographics": {"age": 55, "sex": "male"}})
    state = agent._states["r"]
    # Force an EXAM rejection regardless of what the engine asked first.
    agent._pending_actions["r"] = AgentAction(action_type="EXAM", key="cardiac_auscultation", content="x", rationale="t")
    before_turns = state.turn_count
    agent.act({"case_id": "r", "observation_type": "exam_result", "content": "Request not supported."})
    assert "cardiac_auscultation" in state.rejected_exams
    assert state.turn_count == before_turns, "a rejection consumes no turn"
    assert "cardiac_auscultation" not in state.physical_examinations
    assert not any("Request not supported" in t for t in state.all_findings_text())


@pytest.mark.parametrize("raw,content,expected", [
    ({"rejected": True}, "x", True), ({"status": "unsupported"}, "ok", True), ({"ok": False}, "ok", True),
    ({}, "", True), ({}, "   ", True), ({}, "지원하지 않는 요청입니다.", True), ({}, "対応していません", True),
    ({}, "不支持该请求", True), ({}, "Request rejected: not on the list", True),
    ({}, "Breath sounds are not available on the left; right clear.", False),
    ({}, "Regular rhythm, no murmur", False), ({}, "BP 120/80", False), ({}, "심음 정상", False),
])
def test_rejection_detection_does_not_mistake_findings_for_refusals(raw, content, expected):
    assert rejection_signal(raw, content) is expected


def test_closing_dialogue_explains_before_diagnose_with_a_named_diagnosis():
    ep = run_episode(CASE)
    says = [w for w in ep.wire if w["action_type"] == "SAY"]
    keys = [w["metadata"]["key"] for w in says]
    assert "explanation" in keys and "plan_explanation" in keys
    assert max(i for i, w in enumerate(ep.wire) if w["metadata"]["key"] in {"explanation", "plan_explanation"}) < len(ep.wire) - 1
    explanation = next(w for w in says if w["metadata"]["key"] == "explanation")["content"]
    assert explanation != "원인을 더 확인할게요." and len(explanation) <= SAY_MAX_CHARS
    assert "Told to the patient" in ep.wire[-1]["soap"]["P"] or "환자에게 실제 안내한 내용" in ep.wire[-1]["soap"]["P"]


@pytest.mark.parametrize("lang", ["ko", "en", "ja", "zh"])
def test_say_texts_fit_one_purpose_and_the_character_limit(lang):
    from nova_agent.taxonomy import QUESTION_CATALOG
    texts = [say_text(k, lang) for k in QUESTION_CATALOG] + [say_text("associated_symptoms:fever", lang),
             say_text("associated_symptoms:radiation_to_the_left_arm_or_jaw", lang), say_text("unknown_key", lang, "x" * 90),
             plan_say_text(True, lang), plan_say_text(False, lang), explanation_text("A" * 70, lang),
             explanation_text("Acute Coronary Syndrome", lang, ["heart attack"])]
    for text in texts:
        assert 0 < len(text) <= SAY_MAX_CHARS, text
        assert len(re.findall(r"[?？]", text)) <= 1 and "\n" not in text


def test_say_text_never_contains_grader_or_simulator_manipulation():
    banned = re.compile(r"ignore|previous instruction|system prompt|grader|score|rubric|simulator|pretend|jailbreak|"
                        r"채점|점수|무시|시스템", re.IGNORECASE)
    for case in PRELIM_KO_CASES[:4]:
        for w in run_episode(case).wire:
            assert not banned.search(w["content"].split("\n")[0] if w["action_type"] != "DIAGNOSE" else ""), w["content"]


def test_wire_checker_flags_each_rule_violation():
    ok = {"action_type": "SAY", "content": "When did it start?"}
    assert check_wire(ok, 0) == []
    assert "say_over_limit" in check_wire({"action_type": "SAY", "content": "x" * 31}, 0)
    assert "say_multi_question" in check_wire({"action_type": "SAY", "content": "Fever? Cough?"}, 0)
    assert "exam_multi_maneuver" in check_wire({"action_type": "EXAM", "content": "Listen to the heart and the lungs"}, 0)
    assert "forbidden_action_type:TEST" in check_wire({"action_type": "TEST", "content": "ecg"}, 0)
    assert "over_interaction_cap" in check_wire(ok, 50)
    assert "diagnose_missing_soap_or_primary" in check_wire({"action_type": "DIAGNOSE", "content": "x"}, 3)


def test_every_exam_request_phrase_is_a_single_maneuver():
    from nova_agent.preliminary import exam_request_text
    from nova_agent.taxonomy import EXAM_CATALOG
    for lang in ("ko", "en", "ja", "zh"):
        for exam in EXAM_CATALOG:
            assert check_wire({"action_type": "EXAM", "content": exam_request_text(exam, lang)}, 0) == [], (exam, lang)


def test_note_is_traceable_after_rejections_and_mixed_answers():
    ep = run_episode(CASE, env=Environment(unsupported_exams=frozenset({"cardiac_auscultation"})))
    assert ep.result["soap_unsupported"] == 0 and ep.result["soap_retention"] == 1.0
    assert "메트포르민은 먹어요" in ep.wire[-1]["soap"]["S"] and "페니실린 알레르기가 있어요" in ep.wire[-1]["soap"]["S"]
