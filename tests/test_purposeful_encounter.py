"""Clinical quality and resource regressions; synthetic inputs, no live API."""
from types import SimpleNamespace
import pytest
from competition import nova_sdk_adapter as A
from nova_agent.clinical_interview import missing_foundation_topics, topic_known
from nova_agent.state import PatientState, Demographics
from test_official_independent_audit import encounter, initialise, official_mode
from test_official_sdk_adapter import FakeServer, run


@pytest.mark.parametrize('reply,expected',[
    ('1~2주 안에 갈게요',True),('2주 안에 다시 올게요',True),
    ('한 주 후요',True),('3주 후요',False),('2개월 후요',False),
    ('네',False),('1주인지 모르겠어요',False),('2주에는 못 가요',False)])
def test_teachback_matches_meaning_not_literal_range(reply,expected):
    assert A._followup_understood(reply,'검사 후 1~2주 내 재진하세요') is expected


@pytest.mark.parametrize('reply',['네','감사합니다','없어요','잘 모르겠어요.'])
def test_filler_does_not_replay_plan(reply):
    assert A._requested_clarification(reply,{'spoken_follow_up':'1주 내 재진하세요'},'재진하세요')==''


def test_question_and_practical_barrier_get_targeted_reply():
    plan={'spoken_test_purpose':'검사로 원인을 확인해요','spoken_treatment':'처방의와 조절해요'}
    assert A._requested_clarification('왜 검사하나요?',plan,'')==plan['spoken_test_purpose']
    assert A._requested_clarification('약은 어떻게 하나요?',plan,'')==plan['spoken_treatment']
    assert '상의' in A._requested_clarification('비용이 부담돼요',plan,'')


def test_adult_context_is_not_child_context():
    adult=PatientState(chief_complaint='불편해요',demographics=Demographics(age=40))
    child=PatientState(chief_complaint='키가 작아요',demographics=Demographics(age=9))
    assert {'surgery','smoking','alcohol'} <= set(missing_foundation_topics(adult))
    assert not {'smoking','alcohol'} & set(missing_foundation_topics(child))


def test_functional_impact_already_answered_needs_no_repeat():
    s=PatientState(chief_complaint='불면 때문에 낮에 졸려서 일에 지장이 있어요.')
    assert topic_known(s,'function')
    assert 'function' not in missing_foundation_topics(s)


def test_history_status_preserves_unknown_and_never_expands_negatives():
    no=A._history_line(A.Turn('SAY','진단받은 병이 있나요?','없어요','past_medical_history',turn=3))
    unknown=A._history_line(A.Turn('SAY','수술받은 적이 있나요?','모르겠어요','past_medical_history'))
    assert '(-)' in no and '턴 3' in no and 'DM' not in no
    assert '미확인' in unknown and '(-)' not in unknown


def test_previous_care_and_function_are_hpi():
    assert A._category_bucket('past_medical_history:prior_care')=='hpi'
    assert A._category_bucket('associated_symptoms:function')=='hpi'
    assert A._category_bucket('past_medical_history:surgery')=='pmh'


def test_reasoning_distinguishes_support_opposition_and_missing():
    item=SimpleNamespace(supporting_evidence=['observed tremor'],contradictory_evidence=['observed bradycardia'],
                         missing_discriminative_evidence=['thyroid function'])
    text=A._candidate_reason(item)
    assert 'observed tremor 소견이 이 후보를 지지' in text
    assert '상충 소견: observed bradycardia' in text
    assert 'thyroid function (음성으로 간주하지 않음)' in text


def test_real_uncertainty_still_has_final_review_without_automatic_three_planners(monkeypatch):
    calls=[]
    original=A.OfficialEncounter.chat
    def chat(self,*a,**kw):
        calls.append(kw.get('purpose'));return original(self,*a,**kw)
    monkeypatch.setattr(A.OfficialEncounter,'chat',chat)
    s=FakeServer();e,_=run(s)
    assert 1 <= calls.count('followup') < A.MAX_FOLLOWUP_ROUNDS
    assert calls.count('final_consult')==1
    assert s.closed and e.stats.diagnostic_reasoning_successful>=1


def test_planner_has_lower_budget_and_keeps_final_reasoning_budget(monkeypatch):
    e,_=encounter();initialise(e,'체중이 줄어요.')
    seen=[]
    monkeypatch.setattr(e,'chat',lambda *a,**kw: seen.append(kw) or '{}')
    e._followup_phase()
    assert seen[0]['effort']=='medium' and seen[0]['max_tokens']<A.CONSULT_MAX_TOKENS


def test_plan_has_purpose_and_result_contingency_without_fake_results():
    from nova_agent.clinical_profiles import profiles
    for profile in profiles().values():
        plan=A._purposeful_profile_plan(profile,dict(profile['plan']))
        assert len(plan['tests'])>len(profile['plan']['tests'])
        assert '재평가' in plan['follow_up'] or '검토' in plan['follow_up']
    p=A._purposeful_profile_plan({'category':'thyroid'},{'tests':'TSH','follow_up':'1주'})
    assert '정상 또는 불일치' in p['tests'] and 'ECG' in p['tests']
