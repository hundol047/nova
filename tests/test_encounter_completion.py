"""Regression tests for premature closure, actual education and finite budgets.

Synthetic interactions only; no sample answer keys or live model requests.
"""
from types import SimpleNamespace
import pytest

from competition import nova_sdk_adapter as A
from nova_agent.clinical_interview import (TOPICS, missing_foundation_topics,
                                         next_clinical_action, topic_for_question)
from nova_agent.state import PatientState, Demographics
from test_official_independent_audit import encounter, initialise, official_mode
from test_official_sdk_adapter import FakeServer, run


def test_birth_and_parental_height_do_not_replace_general_history():
    s=PatientState(chief_complaint='키가 작아요.',demographics=Demographics(age=9))
    s.record_ask('past_medical_history','태어날 때 체중은 얼마였나요?','3.2kg')
    s.record_ask('family_history','부모님 키는 각각 얼마인가요?','아버지 175cm 어머니 160cm')
    missing=missing_foundation_topics(s)
    assert 'medical_history' in missing and 'family_illness' in missing


def test_unknown_birth_weight_is_not_repeated_as_weight_loss():
    s=PatientState(chief_complaint='키가 작아요.',demographics=Demographics(age=9))
    asked=[]
    for _ in range(24):
        a=next_clinical_action(s)
        if a is None:break
        asked.append(a[2])
        if a[0]=='EXAM':s.record_exam(a[1],'미확인')
        else:s.record_ask(a[1],a[2],'잘 모르겠어요.')
    assert len(asked)==len(set(asked)) and len(asked)<24
    assert topic_for_question('태어날 때 체중은 얼마였나요?')=='birth'


def test_negative_drug_allergy_does_not_answer_current_medication():
    from nova_agent.clinical_interview import topic_known
    s=PatientState(chief_complaint='체중이 줄어요. 약물 알레르기 없어요.')
    assert not topic_known(s,'medication_name')


def test_unknown_essential_history_is_attempted_once_not_assumed_negative():
    e,_=encounter();initialise(e,'9세 남아, 키가 작아요.')
    e._foundation_phase()
    questions=[t.text for t in e.turns if t.category!='patient_concern']
    assert len(questions)==len(set(questions))
    assert not missing_foundation_topics(e.pstate)
    assert any('잘 모르' in t.reply for t in e.turns)


@pytest.mark.parametrize('opening', ['잠이 안 와요.','불면으로 졸피뎀을 먹어요.'])
def test_sleep_interview_includes_sleep_history_not_only_medications(opening):
    s=PatientState(chief_complaint=opening)
    asked=[]
    for _ in range(24):
        a=next_clinical_action(s)
        if a is None:break
        assert a[0]=='SAY'
        asked.append(topic_for_question(a[2]))
        s.record_ask(a[1],a[2],'잘 모르겠어요.')
    assert {'symptom_onset','sleep_pattern','sleep_hours','snoring','caffeine'} <= set(asked)
    assert len(asked)==len(set(asked)) and len(asked)<24


def test_positive_thyroid_exam_does_not_cancel_unanswered_ros():
    s=PatientState(chief_complaint='체중 감소; 식욕 증가; 더위를 타고 손이 떨려요.')
    s.record_exam('thyroid_exam','갑상선 미만성 비대(+)')
    s.record_exam('thyroid_eye','안구 돌출(+)')
    asked=[]
    for _ in range(24):
        a=next_clinical_action(s)
        if a is None:break
        if a[0]=='EXAM':s.record_exam(a[1],'미확인');continue
        asked.append(topic_for_question(a[2]));s.record_ask(a[1],a[2],'모르겠어요')
    assert {'bowel','sweat','palpitations','allergy'} <= set(asked)


def test_leading_diagnosis_does_not_hide_missing_foundation(monkeypatch):
    e,_=encounter();initialise(e,'불편해요.')
    monkeypatch.setattr('nova_agent.final_decision.decide_final',lambda *a:SimpleNamespace(certainty='LEADING'))
    monkeypatch.setattr(e,'_urgent',lambda *a:False)
    assert e._needs_more_information()


@pytest.mark.parametrize('remaining,used,budget', [(50,0,38),(20,28,10),(10,38,0),(3,0,0),(50,48,0)])
def test_gathering_reserves_real_server_turns(remaining,used,budget):
    e,_=encounter();e.turns_left=remaining;e.turns=[None]*used
    assert e.gathering_budget()==budget
    assert e.can_gather()==bool(budget)


def test_danger_skips_routine_completion():
    e,_=encounter();initialise(e,'호흡이 힘들어요.')
    e.pstate.record_exam('oxygen','SpO2 86%')
    e._foundation_phase()
    assert e.turns==[]


def test_full_encounter_delivers_and_records_understanding_check():
    s=FakeServer();e,_=run(s)
    categories={t.category for t in e.turns}
    assert {'understanding_check','patient_questions','patient_concern'} <= categories
    assert all(len(t.text)<=30 for t in e.turns) and len(e.turns)<=48
    assert '이해 확인·추가 질문에 대한 실제 응답' in s.record['P']['education']
    assert all(t.text in s.record['P']['education'] for t in e.turns if t.category in A.COMMUNICATION_CATEGORIES)
    assert not any(t.text in str(s.record['S']) for t in e.turns if t.category in A.COMMUNICATION_CATEGORIES)
    assert s.record['O']['tests']==''


def test_teachback_cannot_become_diagnostic_evidence():
    e,_=encounter();initialise(e,'잠이 안 와요.')
    e.turns.append(A.Turn('SAY','다음 진료 시점을 말씀해 주시겠어요?',
                          '폐렴 2주 후 항생제','understanding_check'))
    note,_=e.official_record([],None)
    assert '항생제' not in e._observed_corpus()
    assert '항생제' not in str(note['S'])+str(note['A'])
    assert '항생제' in note['P']['education']


def test_short_deadline_still_submits_with_short_closing():
    s=FakeServer(minutes=1);e,_=run(s)
    assert s.closed and s.turns<=3
    assert not any(t.category in ('understanding_check','patient_questions') for t in e.turns
                   if '응급실' in s.record['P']['disposition'])


def test_new_question_templates_are_single_turn_length():
    assert all(A.fits(text) for _,text,_ in TOPICS.values())
