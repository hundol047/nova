"""Invented control cases: coverage/turn policy, not diagnostic accuracy."""
import json
import pytest
from test_adaptive_encounter import Scenario, proposal, run_new, fresh, accept, engine_config, nova_sdk
from competition.interview_coverage import options, exam_options, question_key, coverage, complaint_groups
from competition.encounter_contract import cited_facts, ledger


@pytest.mark.parametrize('opening', [
    '서른 살 여자입니다. 오늘 소변 볼 때 따가워요.',
    '마흔 살 남자입니다. 사흘째 기침이 나요.',
    '스물다섯 살 여자입니다. 이틀째 배가 아파요.',
    '마흔 살 여자입니다. 한 달간 가끔 두통이 생겨요.',
    '마흔 살 남자입니다. 석 달간 체중이 줄었어요.',
    '서른 살 남자입니다. 한 달간 잠을 못 자요.',
    '일곱 살 남자아이입니다. 키가 또래보다 작아요.',
    '서른 살 남자입니다. 며칠간 귀가 먹먹해요.',
])
def test_stable_empty_planner_collects_20_to_25_actions_then_explains(opening):
    p = proposal(); p.update(primary_diagnosis='원인 미상의 증상', short_name='원인 미상', evidence=['I0'])
    s = Scenario(actions=[], opening=opening, final=p)
    e = run_new(s)
    assert 20 <= e._gather_end <= 25, (opening, e._gather_end)
    assert e._gather_end < s.turns <= 49
    assert len({(t.kind, t.text) for t in e.turns}) == len(e.turns)
    assert all(len(t.text) <= 30 for t in e.turns)
    assert sum(t.category == 'understanding_check' for t in e.turns) == 1
    assert sum(t.category == 'patient_questions' for t in e.turns) == 1
    assert all(t.text in str(s.record) for t in e.turns if t.ok and t.kind == 'SAY'
               and t.category not in ('explanation','plan_explanation','understanding_check','patient_questions'))
    assert s.closed


@pytest.mark.parametrize('questions', [
    ['약물 알레르기가 있나요?', '알레르기 원인 약 이름이 뭔가요?', '알레르기 때 어떤 반응이 생겼나요?'],
    ['가족 중 질환이 있는 분이 있나요?', '가족 중 당뇨가 있나요?', '가족 중 갑상선 질환이 있나요?'],
    ['복용하는 약 이름은 무엇인가요?', '수면제를 얼마나 자주 드시나요?', '수면제 한 번 용량은 몇 mg인가요?'],
    ['아버지 키는 얼마인가요?', '어머니 키는 얼마인가요?'],
])
def test_screen_and_details_are_not_collapsed_by_a_broad_model_topic(questions):
    e, _ = fresh()
    for text in questions:
        assert e._send_planned({'kind':'SAY','text':text,'topic':'history'}) is not None, text


@pytest.mark.parametrize('question', ['알레르기 약 이름과 반응을 알려주세요',
                                   '부모님 키는 각각 얼마인가요?',
                                   '언제 시작됐고 얼마나 오래 갔나요?'])
def test_multiple_requested_attributes_are_rejected(question):
    e, s = fresh()
    assert e._send_planned({'kind':'SAY','text':question}) is None
    assert not s.events


def test_unknown_answers_remain_unresolved_in_reviewer_input():
    e, _ = fresh()
    e._send_planned({'kind':'SAY','text':'증상이 얼마나 심한가요?'})
    row = next(r for r in coverage(e) if r['domain'] == 'severity')
    assert row['status'] == 'unresolved' and row['observation_ids']


def test_patient_request_to_rephrase_is_not_diagnostic_support():
    e, _ = fresh()
    t = e.say('통증이 심한가요?', 'severity')
    t.reply = '한 번에 하나씩 물어봐 주세요.'
    assert not cited_facts(['T1'], ledger(e))


def test_sleep_medication_details_are_retained_only_for_observed_exposure():
    e, _ = fresh('불면으로 졸피뎀을 복용하고 있어요.')
    selected = {a['topic'] for a in options(e.pstate)}
    assert {'medication_dose', 'medication_frequency', 'medication_duration', 'withdrawal'} <= selected
    e2, _ = fresh('불면이 있지만 수면제는 먹지 않아요.')
    assert 'medication_dose' not in {a['topic'] for a in options(e2.pstate)}


@pytest.mark.parametrize('text,group', [('배가 아파요.', 'abdominal'),
    ('가슴이 아파요.', 'chest'), ('머리가 아파요.', 'headache')])
def test_conversational_korean_pain_still_selects_focused_exam(text,group):
    e, _ = fresh(text)
    assert group in complaint_groups(e.pstate)
    assert list(exam_options(e.pstate))


def test_child_surgical_history_is_not_mistaken_for_alcohol():
    from nova_agent.clinical_interview import relevant_substance_question
    e, _ = fresh('일곱 살 남자아이입니다. 키가 작아요.')
    assert relevant_substance_question(e.pstate, '수술받은 적이 있나요?')
    assert not relevant_substance_question(e.pstate, '술은 얼마나 자주 드시나요?')
    assert not relevant_substance_question(e.pstate, '담배를 피우시나요?')
    assert e._send_planned({'kind':'SAY', 'text':'수술받은 적이 있나요?'}) is not None


def test_invalid_reviewer_cannot_replace_a_grounded_plan():
    class Reviewed(Scenario):
        def respond(self, system, content):
            data = json.loads(content)
            if 'PROPOSED_DECISION_NOT_OBSERVATIONS' in data:
                p = proposal(); p.update(primary_diagnosis='위암', evidence=['T999'])
                self.inputs.append(data)
                return json.dumps(p, ensure_ascii=False)
            return super().respond(system, content)
    s = Reviewed()
    run_new(s)
    assert s.diagnosis == '급성 방광염'
    assert any('PROPOSED_DECISION_NOT_OBSERVATIONS' in x for x in s.inputs)


def test_return_plan_retains_test_timing_result_branches_and_review():
    e, _ = fresh(); accept(e, proposal())
    p = e._engine_plan([], None)
    assert all(term in p['tests'] for term in ('오늘', '염증', '이상 시', '정상이나 지속 시', '미시행'))
    assert '검사 결과' in p['follow_up']
    assert '오늘' in p['say_test_timing']


def test_user_cap_cannot_be_exceeded_by_late_explanations():
    e, s = fresh()
    for i in range(49):e.say(f'기록 확인 {i}', 'explanation')
    from competition.nova_sdk_adapter import EncounterOver
    with pytest.raises(EncounterOver):e.say('마지막 설명', 'explanation')
    assert s.turns == 49


@pytest.mark.parametrize('question,expected', [
    ('왜 그 진단을 의심하나요?', '배뇨통과 빈뇨가 있어 의심해요'),
    ('위험 신호는 무엇인가요?', '고열이나 옆구리 통증 시 바로 진료받으세요'),
])
def test_patient_followup_question_gets_current_plan_answer(question, expected):
    class Asking(Scenario):
        def action(self, body):
            result = super().action(body)
            if body.get('content') == '궁금하거나 걱정되는 점이 더 있나요?':
                result['content'] = question
            return result
    s = Asking()
    e = run_new(s)
    i = next(i for i, t in enumerate(e.turns) if t.category == 'patient_questions')
    assert any(t.text == expected for t in e.turns[i+1:])
    assert s.turns <= 49
