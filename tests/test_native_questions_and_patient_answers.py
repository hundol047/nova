import re
import pytest
from competition import nova_sdk_adapter as A
from competition.official_evidence import followup_discriminator, _SINGLE_FEATURE_QUESTIONS
from nova_agent.preliminary import say_text, question_is_faithful
from nova_agent.action_selector import AgentAction
from test_official_independent_audit import encounter, initialise, official_mode

@pytest.mark.parametrize('feature',list(_SINGLE_FEATURE_QUESTIONS))
def test_native_question_keeps_target_without_a_translation_call(monkeypatch,feature):
    e,_=encounter();initialise(e,'불편해요')
    key='associated_symptoms:'+feature
    question=say_text(key,'ko')
    assert not re.search('[A-Za-z]',question)
    assert followup_discriminator(question)==key
    assert question_is_faithful(key,'ko') and A.fits(question)
    def unexpected(*a,**kw):raise AssertionError('No translation request needed')
    monkeypatch.setattr(e,'chat',unexpected)
    assert e._korean_question(key,question)==question
    assert e.phrase_calls==0

@pytest.mark.parametrize('feature',list(_SINGLE_FEATURE_QUESTIONS))
@pytest.mark.parametrize('reply',['네','아니요','모르겠어요'])
def test_engine_observation_preserves_native_question_polarity(feature,reply):
    e,_=encounter();initialise(e,'불편해요')
    key='associated_symptoms:'+feature;q=say_text(key,'ko');before=e.pstate.turn_count
    e.engine.agent.observe(e.pstate,AgentAction(action_type='ASK',key=key,content=q,rationale='test'),reply)
    assert e.pstate.turn_count==before+1
    if reply=='네':assert feature in e.pstate.pertinent_positives
    elif reply=='아니요':assert 'no '+feature in e.pstate.pertinent_negatives
    else:assert feature in e.pstate.unknown_findings

@pytest.mark.parametrize('question',[
    '어떤 증상이 생기면 바로 와야 하나요?', '응급실에는 언제 가나요?',
    '어떤 위험 신호를 봐야 하나요?', '악화하면 어떻게 하나요?'])
def test_patient_safety_question_gets_selected_precautions(question):
    plan={'spoken_precautions':'경련·혼돈·호흡저하 시 즉시 진료받으세요',
          'spoken_follow_up':'1주 내 재진하세요'}
    assert A._requested_clarification(question,plan,'다음 진료')==plan['spoken_precautions']

@pytest.mark.parametrize('question',['완치될까요?','언제 회복되나요?','평생 이런가요?'])
def test_prognosis_question_gets_uncertainty_not_a_promise(question):
    answer=A._requested_clarification(question,{},'')
    assert answer and A.fits(answer) and '원인' in answer
    assert '완치됩니다' not in answer


def test_patient_question_actually_gets_answer_without_extra_model_call(monkeypatch):
    e,_=encounter();initialise(e,'불편해요');e.turns_left=10
    plan={'spoken_next_step':'1주 내 재진하세요','spoken_follow_up':'1주 내 재진하세요',
          'spoken_precautions':'증상이 악화하면 바로 진료받으세요',
          'spoken_test_purpose':'평가로 원인을 확인해요'}
    monkeypatch.setattr(e,'_urgent',lambda *a:False)
    monkeypatch.setattr(e,'_engine_plan',lambda *a:plan)
    def say(text,category):
        reply='어떤 증상이 생기면 바로 와야 하나요?' if category=='patient_questions' else '1주 후요'
        t=A.Turn('SAY',text,reply,category);e.turns.append(t);e.turns_left-=1;return t
    monkeypatch.setattr(e,'say',say);e._explain([],None)
    i=next(i for i,t in enumerate(e.turns) if t.category=='patient_questions')
    assert e.turns[i+1].text==plan['spoken_precautions']
    assert len(e.turns)<=A.CLOSING_TURN_RESERVE

@pytest.mark.parametrize('question',['왜 그렇게 진단하셨나요?','어떤 근거로 의심하나요?'])
def test_diagnosis_question_reuses_validated_reason(question):
    plan={'spoken_reason':'체중 감소·손 떨림을 함께 고려했어요',
          'spoken_test_purpose':'검사로 원인을 확인해요'}
    assert A._requested_clarification(question,plan,'')==plan['spoken_reason']


def test_missing_reason_is_not_fabricated():
    assert '추가 확인' in A._requested_clarification('진단 근거가 뭔가요?',{},'')
