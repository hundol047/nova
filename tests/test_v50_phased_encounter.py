"""Invented protocol regressions. These are not clinical/leaderboard scores."""
import copy
import json

import pytest
from test_adaptive_encounter import Scenario, proposal, run_new, fresh, accept, engine_config, nova_sdk
from competition.encounter_contract import care_text, ledger, plan_issues
from competition.interview_coverage import CORE_HISTORY
from nova_agent.clinical_interview import missing_foundation_topics


class Phased(Scenario):
    """Unlike old full-response mocks, return only the requested phase fields."""
    def respond(self, system, content):
        data = json.loads(content)
        if '"actions"' in system:return super().respond(system, content)
        self.inputs.append(data)
        if data['phase'] == 'diagnosis':
            return json.dumps({k:v for k,v in self.final.items() if k not in ('plan','communication')}, ensure_ascii=False)
        return json.dumps({k:self.final[k] for k in ('plan','communication')}, ensure_ascii=False)


def test_gathering_then_diagnosis_then_plan_uses_actual_observations():
    s = Phased(actions=[]); e = run_new(s)
    phases = [x['phase'] for x in s.inputs]
    assert phases[-2:] == ['diagnosis', 'care_plan']
    assert all(x == 'information_collection' for x in phases[:-2])
    assert 20 <= e._gather_end <= 25
    assert s.chat_calls <= 7 and s.turns < 44
    final_rows = s.inputs[-2]['PATIENT_EVIDENCE']
    assert len([r for r in final_rows if r['kind'] in ('SAY','EXAM')]) == e._gather_end
    assert any(r['kind'] == 'EXAM' for r in final_rows)
    assert not set(CORE_HISTORY).intersection(missing_foundation_topics(e.pstate))
    assert s.diagnosis == '급성 방광염' and '소변 검사' in s.record['P']['tests']


def test_endless_planner_cannot_use_reserved_exam_and_safety_slots():
    class Endless(Phased):
        def respond(self, system, content):
            if '"actions"' not in system:return super().respond(system, content)
            self.inputs.append(json.loads(content))
            return json.dumps({'ready':False, 'actions':[
                {'kind':'SAY','text':f'생활 변화 {self.chat_calls}-{i}는요?'} for i in range(6)]})
    s = Endless(); e = run_new(s)
    assert e._gather_end == 25
    assert any(t.kind == 'EXAM' for t in e.turns[:25])
    assert not set(CORE_HISTORY).intersection(missing_foundation_topics(e.pstate))
    assert s.closed and s.turns <= 49


def test_incomplete_plan_gets_one_targeted_repair_without_rediagnosis():
    class Repair(Phased):
        def respond(self, system, content):
            data = json.loads(content)
            if data.get('phase') == 'care_plan' and 'repair_only_these_missing_or_unspeakable_fields' not in data:
                self.inputs.append(data)
                bad = copy.deepcopy(self.final)
                del bad['plan']['tests'][0]['if_abnormal']
                del bad['plan']['follow_up']['when']
                bad['plan']['education'] = '안내가 길어서 ' * 20
                return json.dumps({'plan':bad['plan'], 'communication':bad['communication']}, ensure_ascii=False)
            return super().respond(system, content)
    s = Repair(actions=[]); e = run_new(s)
    assert [x['phase'] for x in s.inputs].count('diagnosis') == 1
    assert [x['phase'] for x in s.inputs].count('care_plan') == 2
    issues = s.inputs[-1]['repair_only_these_missing_or_unspeakable_fields']
    assert 'follow_up.when_missing' in issues and 'tests[0].if_abnormal_missing_or_unsafe' in issues
    assert not e._plan_issues
    assert '이상 시' in s.record['P']['tests'] and '2일 내' in s.record['P']['follow_up']


def test_invalid_partial_model_plan_never_inherits_a_different_profile():
    e, _ = fresh()
    p = proposal(); p['plan'] = {'tests':[{'name':'갑상선 검사', 'purpose':'확인', 'evidence':['T999']}]}
    accept(e,p); plan = e._engine_plan([], None)
    assert '갑상선' not in plan['tests']
    assert all('미확인' in plan[k] for k in ('tests','treatment','follow_up'))
    assert not any(k.startswith('spoken_') for k in plan)


def test_core_explanations_precede_optional_sentences_and_feedback_remains():
    e, _ = fresh(); p = proposal()
    p['plan']['treatment'] = '물을 적절히 마셔요. 소변을 참지 마세요.'
    p['plan']['precautions'] = '고열이 나면 바로 진료받으세요. 옆구리가 아파도 바로 진료받으세요.'
    accept(e,p); e._explain([],None)
    said = [t.text for t in e.turns]
    assert all(x in said for x in ('오늘 검사를 받으세요','2일 내 외래에서 재진하세요',
        '증상과 검사 결과를 확인해요','검사 결과에 따라 치료를 정하겠습니다',
        '소변을 참지 마세요','옆구리가 아파도 바로 진료받으세요'))
    assert said.index('오늘 검사를 받으세요') < said.index('소변을 참지 마세요')
    assert any(t.category == 'understanding_check' for t in e.turns)
    assert any(t.category == 'patient_questions' for t in e.turns)
    assert all(len(x) <= 30 for x in said)


def test_plan_repair_is_bounded_when_doctor_keeps_returning_incomplete_plan():
    p = proposal(); p['plan'] = {}
    s = Phased(actions=[], final=p); e = run_new(s)
    assert len([x for x in s.inputs if x['phase'] == 'care_plan']) == 2
    assert e._plan_issues and s.closed and s.chat_calls <= 8


def test_urgent_case_skips_collection_quota_and_plan_latency():
    s = Phased(vitals='SpO2 86%, 맥박 120 회/분'); e = run_new(s)
    assert e._gather_end == 0
    assert not any(x['phase'] == 'care_plan' for x in s.inputs)
    assert any('119' in t.text for t in e.turns)
    assert s.closed and s.turns <= 5


@pytest.mark.parametrize('mutation,issue', [
    (lambda p:p['plan']['tests'][0].pop('when'), 'tests[0].when_missing_or_unsafe'),
    (lambda p:p['plan']['tests'][0].update(evidence=['T999']), 'tests[0].evidence_unobserved'),
    (lambda p:p['plan'].update(treatment='새 약 500mg을 드세요'), 'treatment_missing_unsafe_or_too_long'),
])
def test_incomplete_or_unsafe_plans_are_detected(mutation, issue):
    e, _ = fresh(); p = proposal(); mutation(p)
    assert issue in plan_issues(p,ledger(e))


def test_long_instruction_is_not_truncated_into_a_different_action():
    assert not care_text('약을 중단하세요. 단, ' + '담당의와 확인한 경우에만 ' * 90, 100)


def test_multisentence_concern_and_long_valid_test_name_are_actually_spoken():
    e, _ = fresh(); p = proposal()
    p['communication']['concern'] = '일상생활이 불편해서 걱정이 되셨겠어요. 함께 경과를 확인하며 치료를 정해요.'
    name = '긴검사이름' * 6  # 30 characters: a label must not hide it.
    p['plan']['tests'][0]['name'] = name
    accept(e,p); e._explain([],None)
    said = [t.text for t in e.turns]
    assert name in said
    assert '일상생활이 불편해서 걱정이 되셨겠어요' in said
    assert all(len(t) <= 30 for t in said)


def test_unspeakable_location_does_not_hide_same_day_disposition():
    e, _ = fresh(); p = proposal()
    p['plan']['disposition'].update(level='same_day', where='길게 적은 진료 장소 ' * 5)
    assert 'same_day_location_too_long' in plan_issues(p,ledger(e))
    accept(e,p); e._explain([],None)
    assert any(t.text == '오늘 의료기관에서 진료받으세요' for t in e.turns)
