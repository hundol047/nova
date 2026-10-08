"""SOAP data-loss regression + provenance tests (preliminary round)."""
import copy

import pytest

from evaluation.soap_provenance import check_soap, retention
from nova_agent.llm_client import MockLLMClient
from nova_agent.orchestrator import DoctorAgent
from nova_agent.soap import _subjective, _labels, build_soap, classify_answer

DENIED = [
    "No.", "No, I don't have any allergies.", "None", "Nope", "No insulin and no other medicines.",
    "No, none", "I do not take any medication", "없어요", "아니요, 없습니다", "아니요. 알레르기 없어요.",
    "ありません", "没有", "No pain, and no fever",
]
RETAINED = [
    "I take metformin.", "I take metformin and insulin", "Aspirin causes a rash.", "I'm allergic to penicillin",
    "아스피린 알레르기가 있습니다", "혈압약을 복용합니다", "No insulin. I take metformin.",
    "No penicillin allergy; aspirin causes a rash.", "아니요, 아스피린 알레르기가 있어요.",
    "No insulin but I take metformin", "No allergies, however aspirin gives me a rash",
    "None, except penicillin", "No, only aspirin", "No metformin, and also I take insulin",
    "알레르기는 없지만 약은 복용합니다", "아니요, 약은 안 먹고 아스피린만 먹어요", "그러나 페니실린 알레르기가 있어요",
    "没有，但是我吃阿司匹林", "ありませんが、アスピリンを飲んでいます", "No statins, yes metoprolol", "No; aspirin, yes",
    "Not sure", "I don't know what I take", "모르겠어요", "I take aspirin without food",
]


@pytest.mark.parametrize("answer", DENIED)
def test_pure_denials_are_normalised(answer):
    assert classify_answer(answer) == "denied"


@pytest.mark.parametrize("answer", RETAINED)
def test_positive_mixed_or_uncertain_answers_are_never_denied(answer):
    assert classify_answer(answer) != "denied"


@pytest.mark.parametrize("lang,answer", [("en", a) for a in RETAINED[:4] + RETAINED[6:9]] + [("ko", a) for a in RETAINED[4:6] + RETAINED[9:12]])
@pytest.mark.parametrize("category", ["medication", "allergy"])
def test_soap_text_keeps_the_patients_own_words(lang, answer, category):
    agent = DoctorAgent(llm_client=MockLLMClient())
    state = agent.new_case("c1", "chest pain", {"age": 50, "sex": "male"}, 50, preliminary=True)
    state.record_ask(category, "q", answer)
    note = "\n".join(_subjective(state, _labels(lang)))
    assert answer.strip() in note


def test_empty_and_punctuation_only_answers():
    assert classify_answer("") == "empty" and classify_answer("  ...  ") == "empty"


def test_long_pure_denial_and_long_mixed_answer():
    assert classify_answer(", ".join(["no insulin"] * 40)) == "denied"
    long_mixed = "No insulin. " * 40 + "I take metformin."
    assert classify_answer(long_mixed) == "mixed"


@pytest.mark.parametrize("sep", [". ", "; ", ", ", " but ", " however ", " and ", " except "])
def test_separators_do_not_hide_a_positive_clause(sep):
    assert classify_answer(f"No insulin{sep}I take metformin") != "denied"
    assert classify_answer(f"No insulin{sep}no aspirin") == "denied"


def _full_case():
    agent = DoctorAgent(llm_client=MockLLMClient())
    state = agent.new_case("c1", "Chest pain for 2 hours, 55 year old man", {"age": 55, "sex": "male"}, 50, preliminary=True)
    state.record_initial_vitals("BP 150/90, HR 100, SpO2 97%")
    state.record_ask("onset", "q", "About 2 hours ago")
    state.record_ask("medication", "q", "No insulin. I take metformin.")
    state.record_ask("allergy", "q", "No.")
    state.record_ask("associated_symptoms:fever", "q", "No fever")
    state.record_exam("cardiac_auscultation", "Regular rhythm, no murmur")
    state.record_exam_rejected("pelvic_exam")
    state.record_say("This may be angina.", "okay")
    return agent, state


def _soap(state, differential=None, lang="en"):
    return build_soap(state, differential or [], lang)


def test_real_note_is_fully_traceable_and_retains_everything():
    _, state = _full_case()
    note = _soap(state)
    assert check_soap(state, note, "en") == []
    assert retention(state, note)["retention"] == 1.0
    assert "No insulin. I take metformin." in note["S"]
    assert "request rejected" in note["O"] and "NORMAL" not in note["O"].upper()
    assert "not performed during the visit" in note["P"], "an un-keyed chat turn is not an explanation"


def test_unasked_categories_are_not_asked_never_negative():
    _, state = _full_case()
    S = _soap(state)["S"]
    assert "Family history: not asked" in S and "Social history: not asked" in S


@pytest.mark.parametrize("mutation,rule", [
    (lambda n: n.update(S=n["S"] + "\nSmoking: never smoker"), "untraceable_token"),
    (lambda n: n.update(S=n["S"].replace("Allergies: denied", "Allergies: denied\nFamily history: denied")), "denial_without_source"),
    (lambda n: n.update(O=n["O"] + "\n[T9] Abdominal exam: soft, non-tender"), "exam_line_not_in_log"),
    (lambda n: n.update(O=n["O"] + "\nLab: troponin 0.01 normal"), "untraceable_objective_line"),
    (lambda n: n.update(O=n["O"].replace("request rejected (no result)", "normal")), "untraceable_objective_line"),
    (lambda n: n.update(O=n["O"].replace("Regular rhythm, no murmur", "Regular rhythm, no murmur, normal")), "exam_line_not_in_log"),
    (lambda n: n.update(P=n["P"] + "\nAspirin 300 mg"), "unsupported_dose"),
    (lambda n: n.update(A=n["A"] + "\nPrimary diagnosis: second"), "not_exactly_one_primary_diagnosis"),
    (lambda n: n.update(O="\n".join(l for l in n["O"].splitlines() if "Cardiac" not in l and "cardiac" not in l.lower())), "exam_result_omitted"),
])
def test_adversarial_fabrications_are_detected(mutation, rule):
    _, state = _full_case()
    note = copy.deepcopy(_soap(state))
    mutation(note)
    assert rule in {v["rule"] for v in check_soap(state, note, "en")}


def test_a_denial_label_over_a_positive_answer_is_detected_as_lost_information():
    _, state = _full_case()
    note = copy.deepcopy(_soap(state))
    note["S"] = note["S"].replace("No insulin. I take metformin.", "denied")
    assert retention(state, note)["retention"] < 1.0


def test_no_education_claim_without_a_dialogue_turn():
    agent = DoctorAgent(llm_client=MockLLMClient())
    state = agent.new_case("c2", "headache", {"age": 30, "sex": "female"}, 50, preliminary=True)
    P = _soap(state)["P"]
    assert "not performed during the visit" in P and "delivered to the patient" not in P


def test_korean_note_is_traceable():
    agent = DoctorAgent(llm_client=MockLLMClient())
    state = agent.new_case("c3", "가슴이 아파요. 55세 남자입니다.", {"age": 55, "sex": "male"}, 50, preliminary=True)
    state.locale = "ko"
    state.record_ask("allergy", "q", "아니요, 아스피린 알레르기가 있어요.")
    state.record_ask("medication", "q", "없어요")
    note = _soap(state, lang="ko")
    assert "아니요, 아스피린 알레르기가 있어요." in note["S"]
    assert check_soap(state, note, "ko") == []
