"""Bounded history clarification and traceable reasoning; no live model calls."""
from types import SimpleNamespace
import pytest
from nova_agent.state import PatientState
from nova_agent.clinical_interview import (TOPICS, DETAIL_QUESTIONS, topic_known,
    next_foundation_action, next_history_clarification, unresolved_history, topic_for_question)
from competition import nova_sdk_adapter as A
from test_official_independent_audit import encounter, initialise, official_mode


@pytest.mark.parametrize('topic',list(DETAIL_QUESTIONS))
def test_positive_screen_is_not_detailed_history(topic):
    s=PatientState(chief_complaint='불편해요')
    category,q,_=TOPICS[topic]
    s.record_ask(category,q,'네')
    assert not topic_known(s,topic)
    action=next_foundation_action(s)
    assert action[2]==DETAIL_QUESTIONS[topic] and len(action[2])<=30
    assert topic_for_question(action[2])==topic
    s.record_ask(action[1],action[2],'네')
    assert next_history_clarification(s) is None
    assert unresolved_history(s)


@pytest.mark.parametrize('reply',['없어요','잘 모르겠어요','답하기 싫어요'])
def test_unknown_negative_or_declined_not_clarified(reply):
    s=PatientState(chief_complaint='불편해요')
    s.record_ask('past_medical_history',TOPICS['medical_history'][1],reply)
    assert next_history_clarification(s) is None


@pytest.mark.parametrize('topic,reply',[
    ('medical_history','고혈압입니다'),('surgery','10년 전 충수절제술을 받았어요'),
    ('family_illness','아버지가 당뇨예요'),('prior_care','동네 의원에서 정상이라고 했어요'),
    ('function','계단을 못 올라가요')])
def test_named_direct_response_is_covered_without_repeating_question_words(topic,reply):
    s=PatientState(chief_complaint='불편해요')
    s.record_ask(TOPICS[topic][0],TOPICS[topic][1],reply)
    assert topic_known(s,topic)
    assert next_history_clarification(s) is None
    assert not unresolved_history(s)


def test_clarifications_have_a_global_three_turn_cap():
    s=PatientState(chief_complaint='불편해요')
    for topic in DETAIL_QUESTIONS:
        s.record_ask(TOPICS[topic][0],TOPICS[topic][1],'네')
    for _ in range(3):
        action=next_history_clarification(s)
        assert action is not None
        s.record_ask(action[1],action[2],'잘 모르겠어요')
    assert next_history_clarification(s) is None


def test_diagnostic_history_survives_late_unknown_and_social_answers():
    turns=[A.Turn('SAY','약 이름은요?','졸피뎀 10mg','medication',turn=2),
           A.Turn('SAY','낮 활동은요?','낮에 졸려서 운전을 못해요','associated_symptoms',turn=3)]
    turns += [A.Turn('SAY','다른 질문','모르겠어요','social_history',turn=i) for i in range(4,10)]
    out=' '.join(A._salient_history(turns))
    assert '졸피뎀 10mg' in out and '운전' in out and '턴 2' in out
    assert '모르겠어요' not in out


def test_review_plan_links_observed_findings_and_actual_gaps():
    s=PatientState(chief_complaint='불면이에요')
    s.record_ask('medication',TOPICS['medication_name'][1],'모르겠어요')
    item=SimpleNamespace(supporting_evidence=['daytime sleepiness'],missing_discriminative_evidence=['medication dose'])
    p=A._plan_review_items({'follow_up':'1주 내 재진','tests':'복약 검토'},s,SimpleNamespace(item=item))
    assert '약봉투·처방전' in p['follow_up'] and 'daytime sleepiness' in p['follow_up']
    assert 'medication dose' in p['tests'] and '확인된 검사 결과 아님' in p['tests']
    assert '모르겠어요' in p['follow_up']


@pytest.mark.parametrize('reply',['암일까 걱정돼요','일정 때문에 못 가요','치료하면 나을까요?'])
def test_patient_concern_has_bounded_response(reply):
    response=A._concern_response(reply,{})
    assert 0<len(response)<=30
    assert '괜찮' not in response


@pytest.mark.parametrize('reply',['네','없어요','모르겠어요'])
def test_no_extra_reassurance_turn_for_filler(reply):
    assert not A._concern_response(reply,{})


def test_foundation_absorbs_clarification_in_live_state(monkeypatch):
    e,_=encounter();initialise(e,'불편해요')
    e.pstate.record_ask('past_medical_history',TOPICS['medical_history'][1],'네')
    sent=[]
    monkeypatch.setattr(e,'_urgent',lambda *args:False)
    monkeypatch.setattr(e,'can_gather',lambda: len(sent)<1)
    def say(text,category):
        sent.append(text)
        return A.Turn('SAY',text,'고혈압입니다',category)
    monkeypatch.setattr(e,'say',say)
    e._foundation_phase()
    assert sent==[DETAIL_QUESTIONS['medical_history']]
    assert topic_known(e.pstate,'medical_history')
    assert not unresolved_history(e.pstate)
