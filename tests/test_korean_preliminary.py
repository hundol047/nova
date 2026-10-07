"""Korean DEVELOPMENT coverage for the preliminary round (synthetic cases, no private/competition material).

Routing, localized evidence + negation, answer retention in the SOAP note, action selection and
critical-safety behaviour. Mock model: these show the deterministic engine handles Korean input, not
fixed-model accuracy."""
import re

import pytest

from evaluation.preliminary_dev_cases import PRELIM_KO_CASES
from evaluation.preliminary_driver import run_episode
from nova_agent.chief_complaint import top_candidates
from nova_agent.multilingual_concepts import english_evidence_for
from nova_agent.soap import classify_answer

CASES = {c.case_id: c for c in PRELIM_KO_CASES}


def test_case_set_is_new_synthetic_korean_and_needs_no_test():
    assert len(PRELIM_KO_CASES) >= 20
    for case in PRELIM_KO_CASES:
        assert re.search(r"[가-힣]", case.chief_complaint) and not case.test_results
        assert "synthetic" in case.notes.lower()
    domains = " ".join(c.category for c in PRELIM_KO_CASES)
    for needed in ("chest_pain", "dyspnea", "abdominal_pain", "headache", "fever", "syncope", "neuro", "allergic"):
        assert needed in domains


@pytest.mark.parametrize("text,expected", [
    ("오른쪽 종아리가 붓고 아파요", "calf swelling"), ("피 섞인 가래가 나왔어요", "hemoptysis"),
    ("목이 뻣뻣해요", "neck stiffness"), ("빛이 눈부셔요", "photophobia"), ("말이 어눌해졌어요", "slurred speech"),
    ("입이 한쪽으로 돌아갔어요", "facial droop"), ("온몸에 두드러기가 났어요", "urticaria hives"),
    ("고혈압이랑 당뇨가 있어요", "diabetes"), ("인슐린은 맞아요", "known diabetes on insulin insulin use"),
    ("질 출혈이 있어요", "vaginal bleeding"), ("쌕쌕거려요", "wheeze"),
])
def test_colloquial_korean_becomes_canonical_evidence(text, expected):
    assert expected in " ".join(english_evidence_for(text))


@pytest.mark.parametrize("text,absent", [
    ("종아리가 붓지 않아요", "calf swelling"), ("목이 뻣뻣하지 않아요", "neck stiffness"), ("당뇨는 없어요", "diabetes"),
    ("두드러기는 없었어요", "hives"), ("쌕쌕거리지 않아요", "wheeze"),
])
def test_negated_korean_findings_are_never_evidence(text, absent):
    assert absent not in " ".join(english_evidence_for(text))


@pytest.mark.parametrize("text,tag", [
    ("가슴이 쥐어짜듯이 아파요", "chest_pain"), ("배가 아파요", "abdominal_pain"), ("머리가 너무 아파요", "headache"),
    ("열이 나고 기침해요", "fever"), ("오래 서 있다가 쓰러졌어요", "syncope"), ("숨이 차요", "dyspnea"),
    ("온몸이 가렵고 숨이 안 쉬어져요", "dyspnea"), ("새우 먹고 두드러기가 났어요", "allergic"), ("어지러워요", "dizziness"),
])
def test_korean_chief_complaints_route(text, tag):
    assert tag in top_candidates(text, 3)


@pytest.mark.parametrize("answer,expected_denied", [
    ("아니요, 없어요.", True), ("없습니다.", True), ("아니요 알러지 없어요", True), ("당뇨는 없고 고혈압도 없어요", True),
    ("아니요, 아스피린 알레르기가 있어요.", False), ("메트포르민은 먹고 인슐린은 안 맞아요", False),
    ("아니요 약은 안 먹고 아스피린만 먹어요", False), ("알레르기는 없지만 약은 복용합니다", False), ("잘 모르겠어요", False),
    ("조영제는 모르겠어요", False),
])
def test_korean_negation_classification(answer, expected_denied):
    assert (classify_answer(answer) == "denied") is expected_denied


@pytest.mark.parametrize("case_id", ["PrelimKo_ChestPain_ACS", "PrelimKo_Noisy_Typo_Chest", "PrelimKo_Gluc_Hypoglycemia"])
def test_mixed_korean_answers_survive_into_the_note(case_id):
    ep = run_episode(CASES[case_id])
    S = ep.wire[-1]["soap"]["S"]
    for key in ("medication", "allergy"):
        answer = CASES[case_id].answers.get(key)
        if answer and classify_answer(answer) != "denied":
            assert answer in S, (key, answer)
    assert ep.result["soap_retention"] == 1.0 and ep.result["soap_unsupported"] == 0


CRITICAL = [c.case_id for c in PRELIM_KO_CASES if c.critical]


@pytest.mark.parametrize("case_id", CRITICAL)
def test_critical_korean_case_keeps_the_true_diagnosis_in_the_final_top5_and_follows_the_rules(case_id):
    result = run_episode(CASES[case_id]).result
    assert result["top5"], f"{case_id}: true critical diagnosis fell out of the final top 5 (primary={result['primary']})"
    assert result["rule_violations"] == 0 and result["interactions"] <= 50
    assert result["unresolved_critical_at_diagnosis"] == 0 or result["top1"]
