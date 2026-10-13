"""Short patient replies retain their actually asked, single-feature meaning."""
import json
from types import SimpleNamespace
import pytest
from competition import nova_sdk_adapter as A
from competition.official_evidence import followup_discriminator, _SINGLE_FEATURE_QUESTIONS
from nova_agent.state import answer_kind
from test_official_independent_audit import encounter, initialise, official_mode


@pytest.mark.parametrize('feature',list(_SINGLE_FEATURE_QUESTIONS))
@pytest.mark.parametrize('reply',['네','아니요','모르겠어요'])
def test_actual_question_binds_short_reply_without_extra_turn(feature,reply):
    e,_=encounter();initialise(e,'불편해요')
    question=_SINGLE_FEATURE_QUESTIONS[feature][0]
    before=e.pstate.turn_count
    e._absorb('ASK','associated_symptoms',question,reply)
    assert e.pstate.turn_count==before+1
    assert e.pstate.performed_actions[-1].content==question
    if reply=='네':assert feature in e.pstate.pertinent_positives
    elif reply=='아니요':assert 'no '+feature in e.pstate.pertinent_negatives
    else:assert feature in e.pstate.unknown_findings
    if reply!='네':assert feature not in e.pstate.pertinent_positives


@pytest.mark.parametrize('question',[
    '어머니 손이 떨리나요?','과거에 손이 떨렸나요?','손이 떨리지 않나요?',
    '손이 떨리거나 땀이 나나요?','체중이 몇 kg 줄었나요?',
    '어떤 약을 드시나요?','다른 증상이 있나요?','의식을 잃은 적이 있나요?'])
def test_ambiguous_or_open_questions_never_get_a_patient_feature(question):
    assert not followup_discriminator(question)


@pytest.mark.parametrize('reply,kind',[('그렇습니다','yes'),('네, 그렇습니다.','yes'),('네 맞아요','yes'),('아닙니다','no'),('알겠습니다',None)])
def test_precise_korean_reply_variants(reply,kind):
    assert answer_kind(reply)==kind


def test_planned_followup_updates_differential_from_binary_replies(monkeypatch):
    from nova_agent.matching import feature_present_with_aliases
    e,_=encounter();initialise(e,'불편해요')
    monkeypatch.setattr(e,'chat',lambda *a,**kw:json.dumps({'questions':['손이 떨리나요?','더위를 많이 타시나요?']}))
    def say(text,category):
        t=A.Turn('SAY',text,'네, 그렇습니다.',category);e.turns.append(t);e.turns_left-=1;return t
    monkeypatch.setattr(e,'say',say)
    e._followup_phase()
    assert len(e.turns)==2
    assert all(':' in t.category for t in e.turns)
    current=e.pstate.all_findings_text(include_context=False,include_family=False)
    assert feature_present_with_aliases('tremor',current,scrub_negated_spans=True)
    assert feature_present_with_aliases('heat intolerance',current,scrub_negated_spans=True)
    assert any(d.diagnosis_id.endswith('hyperthyroidism') for d in e.pstate.current_differential)


def test_partial_model_evidence_does_not_hide_exam_or_binary_history():
    e,_=encounter();initialise(e,'불편해요')
    e.final_consult={'evidence':['불편해요']}
    e.turns.extend([A.Turn('SAY','손이 떨리나요?','네','associated_symptoms:tremor',turn=1),
                    A.Turn('EXAM','손 떨림을 관찰하겠습니다','손 떨림(+)','tremor',turn=2)])
    note,_=e.official_record([],None)
    assert '손이 떨리나요? → 네' in note['A']['evidence']
    assert '손 떨림(+)' in note['A']['evidence'] and '턴 2' in note['A']['evidence']
    assert '모르겠어요' not in note['A']['evidence']


def test_spoken_reason_is_bounded_and_uses_only_validated_support():
    item=SimpleNamespace(supporting_evidence=['weight loss','tremor','fever'])
    line=A._spoken_observation_reason(SimpleNamespace(item=item))
    assert '체중 감소' in line and '손 떨림' in line and len(line)<=30
    assert '발열' not in line
    item.supporting_evidence=['weight loss']
    assert not A._spoken_observation_reason(SimpleNamespace(item=item))


def test_model_followup_does_not_erase_actual_unresolved_medication_task():
    e,_=encounter();initialise(e,'불편해요')
    e.pstate.record_ask('medication','복용 중인 약 이름이 뭔가요?','모르겠어요')
    e.final_consult={'plan':{'follow_up':'다음 방문 때 확인','tests':'원인 검사'}}
    e._diagnosis_checked=True
    e._accepted_proposal=e.final_consult
    note,_=e.official_record([],None)
    assert '1~2주' in note['P']['follow_up']  # vague model plan cannot erase timed follow-up
    assert '약봉투·처방전' in note['P']['follow_up']
    assert note['P']['follow_up'].count('약봉투·처방전')==1


@pytest.mark.parametrize('reply',['네','아니요','모르겠어요'])
def test_same_feature_paraphrase_not_asked_twice(reply):
    e,_=encounter();initialise(e,'불편해요')
    e._absorb('ASK','associated_symptoms','열이 나나요?',reply)
    assert e._verified_followup_done('발열이 있나요?')


def test_opening_answered_feature_is_not_reasked():
    e,_=encounter();initialise(e,'열이 나고 기침이 나요')
    assert e._verified_followup_done('발열이 있나요?')
    assert not e._verified_followup_done('소변볼 때 아픈가요?')
