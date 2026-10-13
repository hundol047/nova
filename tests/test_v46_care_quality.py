"""General engineering regressions, never official scoring or case-key tuning."""
import json
from types import SimpleNamespace
import pytest
from competition import nova_sdk_adapter as A
from nova_agent.encounter_quality import grounded_reasoning, merged_model_tests, complete_care_plan
from nova_agent.clinical_interview import next_clinical_action
from nova_agent.state import PatientState
from test_official_independent_audit import encounter, initialise, official_mode
from test_official_sdk_adapter import FakeServer, run


def test_plan_contract_requests_consumed_fields():
    for key in ('test_plan', 'if_abnormal', 'if_normal', 'clinical_reasoning', 'observation', 'interpretation'):
        assert key in A._FINAL_SYSTEM


def test_test_plan_preserves_indication_and_result_contingencies():
    proposal={'test_plan':[{'test':'ECG','evidence':'가슴이 두근거려요',
        'indication':'리듬 이상 확인','if_abnormal':'심장 진료에서 추가 평가',
        'if_normal':'증상이 지속되면 장기 심전도 필요성을 재평가'}]}
    p=merged_model_tests({'tests':''},proposal,'가슴이 두근거려요',{'ECG'}, A.grounded_in)
    assert '리듬 이상 확인' in p['tests'] and '이상 결과 시' in p['tests']
    assert '정상이나 증상 지속 시' in p['tests'] and '미시행' in p['tests']
    proposal['test_plan'][0]['evidence']='의식 소실이 있어요'
    assert not merged_model_tests({'tests':''},proposal,'가슴이 두근거려요',{'ECG'}, A.grounded_in)['tests']


def test_test_plan_cannot_add_unlisted_test_or_drug_dose():
    row={'test':'ECG','evidence':'두근거림','indication':'리듬 평가','if_abnormal':'약물 50mg 투여'}
    p=merged_model_tests({'tests':''},{'test_plan':[row]},'두근거림',{'ECG'}, A.grounded_in)
    assert '50mg' not in p['tests']
    row['test']='전신 CT'
    assert not merged_model_tests({'tests':''},{'test_plan':[row]},'두근거림',{'ECG'}, A.grounded_in)['tests']


def test_interpretation_cannot_create_observed_findings():
    proposal={'clinical_reasoning':[
        {'observation':'손이 떨려요','interpretation':'호르몬 관련 원인 감별이 필요함'},
        {'observation':'혈당 30mg/dL','interpretation':'저혈당 확진'}]}
    text=' '.join(grounded_reasoning(proposal,'손이 떨려요', A.grounded_in))
    assert '임상적 해석' in text and '호르몬' in text and '30mg' not in text


def test_urgent_plan_has_transport_and_immediate_review():
    plan=complete_care_plan({'education':'','follow_up':'1주'},PatientState(),None,True)
    assert '119' in plan['spoken_precautions']
    assert '즉시' in plan['follow_up'] and '1주' not in plan['follow_up']
    assert '이송을 지연하지 않음' in plan['disposition']


def test_stable_generic_plan_has_specific_conditional_precautions():
    e,_=encounter();initialise(e,'가슴이 두근거려요.')
    plan=e._engine_plan([],None)
    assert '실신' in plan['spoken_precautions'] and '추정' in plan['education']


def test_urgent_closing_delivers_transport_without_routine_interview(monkeypatch):
    e,_=encounter();initialise(e,'호흡이 힘들어요.')
    e.pstate.record_exam('oxygen','SpO2 86%')
    e._explain([],None)
    assert any('119' in t.text for t in e.turns)
    assert any('지금 응급실' in t.text for t in e.turns)
    assert all(len(t.text)<=30 for t in e.turns)


def test_chronic_interview_screens_relevant_danger_before_long_history():
    s=PatientState(chief_complaint='체중이 줄어요.')
    first=next_clinical_action(s)
    assert first[2]=='가슴에 통증이 있나요?'
    s.record_ask(first[1],first[2],'아니요')
    assert next_clinical_action(s)[2]=='숨이 차나요?'


def test_negative_answer_can_trigger_reassessment_of_missing_history(monkeypatch):
    rounds=[]
    def planner(self):
        rounds.append(len(self.turns))
        self.followup_plan={}
        if len(rounds)==1:
            t=self.say('기침이 나나요?',category='associated_symptoms:cough')
            self._absorb('ASK',t.category,t.text,t.reply)
    monkeypatch.setattr(A.OfficialEncounter,'_engine_phase',lambda *a:None)
    monkeypatch.setattr(A.OfficialEncounter,'_foundation_phase',lambda *a,**k:None)
    monkeypatch.setattr(A.OfficialEncounter,'_followup_phase',planner)
    s=FakeServer();e,_=run(s)
    assert len(rounds)==2  # second empty plan stops; no unnecessary four-call quota
    assert s.closed and s.turns<=50


def test_all_unknown_questions_and_exams_are_attempted_at_most_once():
    s=PatientState(chief_complaint='불면 때문에 졸피뎀을 먹어요.')
    sent=[]
    for _ in range(50):
        action=next_clinical_action(s)
        if action is None:break
        kind,key,text,_=action;sent.append((kind,text))
        if kind=='EXAM':s.record_exam(key,'미확인',request_text=text)
        else:s.record_ask(key,text,'잘 모르겠어요.')
    assert len(sent)<50 and len(sent)==len(set(sent))


def test_snapshot_differential_cannot_hide_observed_hypoxemia():
    e,_=encounter();initialise(e,'호흡이 힘들어요.')
    e.pstate.record_exam('oxygen','SpO2 86%')
    assert e.pstate.current_differential
    assert e._urgent(e.pstate.current_differential,None)
    plan=e._engine_plan([],None)
    assert '119' in plan['spoken_precautions']
    assert '즉시' in plan['follow_up'] and '1~2주' not in plan['spoken_follow_up']


def test_candidate_failure_keeps_independent_vital_safety(monkeypatch):
    e,_=encounter();initialise(e,'몸이 불편해요.')
    e.pstate.record_exam('oxygen','SpO2 86%')
    def fail(*a):raise RuntimeError('candidate failure')
    monkeypatch.setattr(e.engine.agent.differential_engine,'update',fail)
    assert e._urgent(e.pstate.current_differential,None)


def test_doctor_explanation_is_retained_only_for_the_spoken_diagnosis():
    e,_=encounter();initialise(e,'불편해요.')
    e.final_consult={'primary_diagnosis':'편두통','patient_talk':['빛에 민감해질 수 있는 두통입니다']}
    assert e._doctor_talk('편두통')==['빛에 민감해질 수 있는 두통입니다']
    assert not e._doctor_talk('긴장형 두통')


def test_external_working_label_requires_two_observed_facts():
    e,_=encounter();initialise(e,'오른쪽 귀가 먹먹해요. 비행기 착륙 직후 시작했어요.')
    e.final_consult={'primary_diagnosis':'압력 변화 관련 이관 기능장애',
                     'evidence':['오른쪽 귀가 먹먹해요.']}
    assert '진단 미정' in e._diagnosis_label(None)
    e.final_consult['evidence'].append('비행기 착륙 직후 시작했어요.')
    assert e._diagnosis_label(None)=='압력 변화 관련 이관 기능장애'
