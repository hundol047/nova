"""Follow-up regressions for unresolved onset and explicit teach-back mistakes."""
import pytest
from nova_agent.state import PatientState
from nova_agent.clinical_interview import TOPICS, DETAIL_QUESTIONS, topic_known, next_history_clarification, unresolved_history
from competition import nova_sdk_adapter as A
from test_official_independent_audit import encounter, initialise, official_mode


@pytest.mark.parametrize('reply',['네','아니요','모르겠어요'])
def test_binary_or_unknown_reply_does_not_establish_onset(reply):
    s=PatientState(chief_complaint='불편해요')
    s.record_ask('onset',TOPICS['symptom_onset'][1],reply)
    assert not topic_known(s,'symptom_onset')
    assert unresolved_history(s)
    a=next_history_clarification(s)
    assert bool(a)==(reply=='네')


def test_specific_onset_closes_gap_after_clarification():
    s=PatientState(chief_complaint='불편해요')
    s.record_ask('onset',TOPICS['symptom_onset'][1],'네')
    a=next_history_clarification(s)
    s.record_ask(a[1],a[2],'3개월 전부터요')
    assert topic_known(s,'symptom_onset')
    assert not unresolved_history(s)


@pytest.mark.parametrize('reply',['네','아니요','모르겠어요'])
def test_bare_reply_not_written_as_onset_value(reply):
    e,_=encounter();initialise(e,'불편해요')
    e.turns.append(A.Turn('SAY',TOPICS['symptom_onset'][1],reply,'onset:symptom_onset'))
    note,_=e.official_record([],None)
    assert 'Onset :' not in note['S']['cc']
    assert reply in note['S']['hpi']


def test_corrected_onset_is_the_summary_value():
    e,_=encounter();initialise(e,'불편해요')
    for q,r in [(TOPICS['symptom_onset'][1],'네'),(DETAIL_QUESTIONS['symptom_onset'],'3개월 전부터요')]:
        e.turns.append(A.Turn('SAY',q,r,'onset:symptom_onset'))
    note,_=e.official_record([],None)
    assert 'Onset : 3개월 전부터요' in note['S']['cc']
    assert '→ 네' in note['S']['hpi']


@pytest.mark.parametrize('reply',['3개월 후에 올게요','3주 후요','내일이요'])
def test_explicit_mismatched_time_gets_correction_even_when_plan_already_said(reply):
    plan='1~2주 내 증상과 결과를 다시 확인해요'
    assert A._teachback_correction(reply,plan,True)==plan


@pytest.mark.parametrize('reply',['네','모르겠어요','감사합니다','2주 후요'])
def test_filler_or_correct_reply_does_not_repeat_delivered_plan(reply):
    assert not A._teachback_correction(reply,'1~2주 내 재진하세요',True)


def test_practical_barrier_gets_help_instead_of_repeating_date():
    r=A._teachback_correction('2주에는 못 가요','1~2주 내 재진하세요',True)
    assert '함께 상의' in r and len(r)<=30


def test_explanation_actually_corrects_wrong_teachback_once(monkeypatch):
    e,_=encounter();initialise(e,'불편해요')
    e.turns_left=20
    plan={'spoken_next_step':'1~2주 내 재진하세요','spoken_follow_up':'1~2주 내 재진하세요',
          'spoken_precautions':'악화 시 즉시 진료받으세요','spoken_test_purpose':'검사로 원인을 확인해요',
          'spoken_treatment':'원인에 따라 치료를 정해요'}
    monkeypatch.setattr(e,'_urgent',lambda *args:False)
    monkeypatch.setattr(e,'_engine_plan',lambda *args:plan)
    monkeypatch.setattr(e,'seconds_left',lambda:1000)
    def say(text,category):
        reply='3개월 후요' if category=='understanding_check' else '없어요'
        t=A.Turn('SAY',text,reply,category);e.turns.append(t);e.turns_left-=1;return t
    monkeypatch.setattr(e,'say',say)
    e._explain([],None)
    spoken=[t.text for t in e.turns]
    assert spoken.count(plan['spoken_follow_up'])==2
    assert sum(t.category=='understanding_check' for t in e.turns)==1
    assert len(e.turns)<=A.CLOSING_TURN_RESERVE
