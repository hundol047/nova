import json
import pytest
from competition import nova_sdk_adapter as A
from nova_agent import clinical_interview as C
from test_official_independent_audit import encounter, initialise, official_mode


def setup(monkeypatch):
    e,_=encounter();initialise(e,'불편해요')
    monkeypatch.setattr(e,'_urgent',lambda *a:False)
    def say(text,category):
        t=A.Turn('SAY',text,'고혈압' if text==C.DETAIL_QUESTIONS['medical_history'] else '아니요',category)
        e.turns.append(t);e.turns_left-=1;return t
    monkeypatch.setattr(e,'say',say)
    return e


def test_positive_screen_allows_one_needed_named_history_question(monkeypatch):
    e=setup(monkeypatch)
    e._absorb('ASK','past_medical_history',C.TOPICS['medical_history'][1],'네')
    q=C.DETAIL_QUESTIONS['medical_history']
    monkeypatch.setattr(e,'chat',lambda *a,**kw:json.dumps({'questions':[q]}))
    e._followup_phase();e._followup_phase()
    assert [t.text for t in e.turns]==[q]
    assert any(a.result=='고혈압' for a in e.pstate.performed_actions)

@pytest.mark.parametrize('reply',['아니요','모르겠어요'])
def test_denied_or_unknown_history_does_not_force_detail(monkeypatch,reply):
    e=setup(monkeypatch)
    e._absorb('ASK','past_medical_history',C.TOPICS['medical_history'][1],reply)
    monkeypatch.setattr(e,'chat',lambda *a,**kw:json.dumps({'questions':[C.DETAIL_QUESTIONS['medical_history']]}))
    e._followup_phase();assert not e.turns


def test_optional_background_yields_last_four_turns_to_differential(monkeypatch):
    e=setup(monkeypatch);e.turns_left=A.CLOSING_TURN_RESERVE+4
    action=('SAY','family_history:family_illness',C.TOPICS['family_illness'][1],'family_history')
    monkeypatch.setattr(C,'next_foundation_action',lambda s:action)
    e._foundation_phase();assert not e.turns and e.gathering_budget()==4
    monkeypatch.setattr(e,'chat',lambda *a,**kw:json.dumps({'questions':['열이 나나요?']}))
    e._followup_phase()
    assert e.turns[0].text=='열이 나나요?'
    e._foundation_phase(reserve_followup=False)
    assert len(e.turns)==4 and e.gathering_budget()==0

@pytest.mark.parametrize('topic',['allergy','medication_name','medical_history','symptom_onset','course'])
def test_core_history_is_not_deferred_at_reserve(monkeypatch,topic):
    e=setup(monkeypatch);e.turns_left=A.CLOSING_TURN_RESERVE+1
    category,text,_=C.TOPICS[topic]
    monkeypatch.setattr(C,'next_foundation_action',lambda s:('SAY',category+':'+topic,text,category))
    e._foundation_phase();assert len(e.turns)==1 and e.turns[0].text==text


def test_second_foundation_pass_does_not_repeat_concern(monkeypatch):
    e=setup(monkeypatch)
    monkeypatch.setattr(C,'next_foundation_action',lambda s:None)
    e._foundation_phase();e._foundation_phase(reserve_followup=False)
    assert len(e.turns)==1 and e.turns[0].category=='patient_concern'


def test_generic_plan_compaction_preserves_interaction_and_safety():
    original=[('검사로 의심 원인을 구분해 보겠습니다','plan_explanation'),
              ('1주 내 재진하세요','plan_explanation'),('악화 시 바로 진료받으세요','plan_explanation'),
              ('궁금한 점은요?','patient_questions'),('원인을 확인한 뒤 치료를 정하겠습니다','plan_explanation')]
    result=A._compact_closing_messages(original)
    assert len(result)==len(original)-1
    assert all(pair in result for pair in original[1:4])
    assert all(A.fits(text) for text,_ in result)


def test_specific_drug_instruction_is_never_compacted():
    original=[('검사로 의심 원인을 구분해 보겠습니다','plan_explanation'),
              ('약은 처방의와 상의해 서서히 조절해요','plan_explanation')]
    assert A._compact_closing_messages(original)==original
