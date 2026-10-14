"""Scripted contract/regression cases, not clinical scoring or live Doctor evaluation."""
import json
from types import SimpleNamespace

import pytest
from test_official_sdk_adapter import FakeClient, FakeServer, engine_config, nova_sdk
from test_official_independent_audit import initialise
from competition import nova_sdk_adapter as A
from competition.adaptive_encounter import AdaptiveEncounter
from competition.encounter_contract import cited_facts, ledger, care_text


OPENING = '서른 살 여자입니다. 오늘부터 소변을 볼 때 따갑습니다.'
ACTIONS = [
    {'kind': 'SAY', 'text': '소변을 평소보다 자주 보나요?', 'topic': 'frequency'},
    {'kind': 'SAY', 'text': '옆구리가 아픈가요?', 'topic': 'flank'},
    {'kind': 'EXAM', 'text': '늑골척추각을 타진하겠습니다', 'topic': 'cva'},
    {'kind': 'SAY', 'text': '임신 가능성이 있나요?', 'topic': 'pregnancy'},
    {'kind': 'SAY', 'text': '복용하는 약 이름은 무엇인가요?', 'topic': 'medication'},
    {'kind': 'SAY', 'text': '약물 알레르기가 있나요?', 'topic': 'allergy'},
]


def proposal():
    return {'primary_diagnosis': '급성 방광염', 'short_name': '방광염',
        'reason': '배뇨통과 빈뇨로 의심하며 검사로 확인이 필요함',
        'evidence': [{'source_id': 'I0', 'quote': '소변을 볼 때 따갑습니다'}],
        'differential': [{'name': '신우신염', 'reason': '상부 요로 증상 확인 필요',
                          'support': ['I0'], 'against': [], 'missing': '소변 검사 미시행'}],
        'plan': {'tests': [{'name': '소변 검사', 'purpose': '염증 여부 확인', 'evidence': ['I0'],
                'when': '오늘', 'if_abnormal': '감염 근거에 따라 치료 결정',
                'if_normal': '지속되면 다른 원인 재평가'}],
            'treatment': '물을 적절히 마시고 소변을 참지 마세요.',
            'disposition': {'level': 'outpatient', 'where': '일차의료 외래',
                            'reason': '현재 관찰에 따라 외래 평가', 'evidence': ['I0']},
            'follow_up': {'when': '2일 내', 'where': '외래', 'review': '증상과 검사 결과를 확인해요'},
            'precautions': '고열이나 옆구리 통증 시 바로 진료받으세요.',
            'education': '검사 결과에 따라 치료를 정하겠습니다.'},
        'communication': {'diagnosis': '갑상샘항진증입니다',  # deliberately conflicting
            'reason': '배뇨통과 빈뇨가 있어 의심해요',
            'tests': '갑상선 검사를 합니다', 'treatment': '수면제를 두 배로 드세요',
            'follow_up': '6개월 뒤에 오세요', 'precautions': '위험한 증상은 무시하세요',
            'concern': '불편하셨겠어요. 경과를 함께 확인해요'}}


class Scenario(FakeServer):
    def __init__(self, *, actions=None, final=None, opening=OPENING, vitals=None, **kwargs):
        super().__init__(**kwargs)
        self.opening = opening
        self.vitals = vitals or '혈압 120/80 mmHg, 맥박 78 회/분, 호흡 16 회/분, 체온 36.8°C'
        self.plans = [list(ACTIONS if actions is None else actions), []]
        self.final = proposal() if final is None else final
        self.inputs = []
        self.chat_reply = self.respond

    def session(self):
        result = super().session()
        result['initial'] = {'opening': self.opening, 'vital_signs': self.vitals}
        return result

    def respond(self, system, content):
        self.inputs.append(json.loads(content))
        if '"actions"' in system:
            return json.dumps({'actions': self.plans.pop(0) if self.plans else [],
                               'ready': not self.plans, 'reason': '관찰에 맞춘 행동 선택'}, ensure_ascii=False)
        return json.dumps(self.final, ensure_ascii=False)

    def action(self, body):
        result = super().action(body)
        if body['action'] == 'SAY':
            q = body['content']
            answer = ('배뇨통이 빨리 나았으면 좋겠어요.' if '걱정' in q else
                      '네, 자주 봐요.' if '자주 보' in q else
                      '2일 내 외래에서 검사 결과를 확인해요.' if '말씀해 주시' in q else
                      '아니요.' if any(x in q for x in ('옆구리', '임신', '알레르기', '병', '약')) else
                      '잘 모르겠어요.')
            result['content'] = answer
            self.events[-1] = ('SAY', q, answer)
        return result


def run_new(server):
    e = AdaptiveEncounter(FakeClient(server), {}, sleep=lambda _: None, log=lambda _: None)
    assert e.run()['status'] == 'completed'
    return e


def fresh(opening=OPENING):
    s = Scenario()
    e = AdaptiveEncounter(FakeClient(s), {}, sleep=lambda _: None, log=lambda _: None)
    initialise(e, opening)
    return e, s


def accept(e, p):
    e.final_consult = p
    e._accepted_primary = e._validated_primary([], None)
    e._diagnosis_checked = True


def test_patient_specific_questions_and_exam_precede_template_history():
    s = Scenario()
    e = run_new(s)
    sent = [x[1] for x in s.events]
    assert sent[1:5] == [a['text'] for a in ACTIONS[:4]]
    assert s.diagnosis == '급성 방광염'
    assert all(len(t) <= 30 for _, t, _ in s.events)
    assert s.turns <= 50 and s.chat_calls <= 14
    from nova_agent.clinical_interview import missing_foundation_topics
    assert not missing_foundation_topics(e.pstate)
    assert not any(kind == 'TEST' for kind, *_ in s.events)
    assert len(sent) == len(set(sent))
    assert '늑골척추각' in s.record['O']['exam']
    assert '갑상샘항진증입니다' not in sent
    assert '소변 검사' in s.record['P']['tests'] and '지속되면 다른 원인' in s.record['P']['tests']
    assert '2일 내' in s.record['P']['follow_up']
    assert any('2일 내' in t for t in sent) and not any('6개월' in t for t in sent)
    assert not any('두 배' in t or '무시하세요' in t for t in sent)
    assert '[I0]' in s.record['A']['evidence']
    assert all(set(s.record[k]) == set(nova_sdk.RECORD_FIELDS[k]) for k in s.record)
    assert e.stats.diagnostic_reasoning_successful >= 1


def test_next_review_receives_actual_positive_negative_and_exam_results():
    s = Scenario()
    run_new(s)
    second = s.inputs[1]['PATIENT_EVIDENCE']
    assert any(x.get('answer') == '네, 자주 봐요.' for x in second)
    assert any(x.get('question') == '옆구리가 아픈가요?' and x.get('answer') == '아니요.' for x in second)
    assert any(x['kind'] == 'EXAM' for x in second)


def test_initial_and_vital_references_work_but_altered_quotes_do_not():
    e, _ = fresh()
    e.vitals = 'SpO2 98%'
    assert cited_facts(['I0', 'V0'], ledger(e)) == [f'[I0] {OPENING}', '[V0] SpO2 98%']
    assert not cited_facts([{'source_id': 'V0', 'quote': 'SpO2 88%'}], ledger(e))
    assert not cited_facts(['T999'], ledger(e))


@pytest.mark.parametrize('bad', [[], ['T999'], [{'source_id': 'I0', 'quote': '혈당 30mg/dL'}]])
def test_unobserved_citation_cannot_authorize_doctor_primary(bad):
    e, _ = fresh('오른쪽 귀가 먹먹해요.')
    p = proposal(); p.update(primary_diagnosis='압력 변화 관련 이관 기능장애', evidence=bad)
    accept(e, p)
    assert not e._model_primary


def test_general_weakness_does_not_end_interview_as_electrolyte_emergency():
    e, _ = fresh('generalized weakness')
    assert not e._urgent(e.pstate.current_differential, None)


def test_measured_danger_survives_engine_failure_and_conflicting_plan(monkeypatch):
    e, s = fresh()
    e.pstate.record_exam('oxygen', 'SpO2 86%')
    accept(e, proposal())
    monkeypatch.setattr(e.engine.agent.differential_engine, 'update', lambda *_: (_ for _ in ()).throw(RuntimeError()))
    assert e._urgent(e.pstate.current_differential, None)
    p = e._engine_plan([], None)
    assert '즉시' in p['follow_up'] and '2일' not in p['follow_up']
    e._explain([], None)
    assert any('119' in x[1] for x in s.events)
    assert not any('2일' in x[1] for x in s.events)


def test_rejected_exam_is_attempted_once_and_never_becomes_normal_observation():
    action = {'kind': 'EXAM', 'text': '늑골척추각을 타진하겠습니다', 'topic': 'cva'}
    s = Scenario(actions=[action, action], reject_exam=lambda _: 'EXAM_NOT_RECOGNIZED')
    e = run_new(s)
    assert len([x for x in s.events if x[0] == 'EXAM' and x[1] == action['text']]) == 1
    assert '특이 소견(-)' not in s.record['O']['exam']
    assert not any(x['kind'] == 'EXAM' for x in ledger(e))


def test_unknown_answer_and_reworded_attempt_do_not_repeat():
    e, _ = fresh()
    one = {'kind': 'SAY', 'text': '증상이 얼마나 자주 생기나요?', 'topic': 'symptom_frequency'}
    assert e._send_planned(one) is not None
    assert e._send_planned(dict(one, text='증상은 얼마나 자주 생기나요?')) is None
    assert not cited_facts(['T1'], ledger(e))


@pytest.mark.parametrize('action', [
    {'kind': 'TEST', 'text': '소변 검사'},
    {'kind': 'SAY', 'text': '아' * 31},
    {'kind': 'EXAM', 'text': '혈액검사를 하겠습니다'},
    {'kind': 'EXAM', 'text': '심장과 폐를 청진하겠습니다'},
])
def test_invalid_actions_are_not_sent(action):
    e, s = fresh()
    assert e._send_planned(action) is None and not s.events


def test_family_history_cannot_be_current_patient_support():
    e, _ = fresh()
    turn = e.say('가족에게 갑상샘 질환이 있나요?', 'family_history')
    assert not cited_facts(['T1'], ledger(e), patient_support=True)


def test_prescribing_dose_cannot_enter_plan_or_spoken_treatment():
    e, _ = fresh()
    p = proposal(); p['plan']['treatment'] = '항생제 500mg을 드세요'
    accept(e, p)
    result = e._engine_plan([], None)
    assert '500mg' not in str(result)


def test_short_deadline_prioritizes_return_time_and_precautions(monkeypatch):
    e, s = fresh()
    accept(e, proposal())
    monkeypatch.setattr(e, 'seconds_left', lambda: 60)
    e._explain([], None)
    assert len(s.events) == 3
    assert any('2일 내' in x[1] for x in s.events)
    assert any('고열' in x[1] for x in s.events)


def test_explicit_no_test_plan_does_not_reinsert_unrelated_panel():
    e, _ = fresh()
    p = proposal(); p['plan']['tests'] = []
    accept(e, p)
    assert '즉시 추가 검사 계획 없음' in e._engine_plan([], None)['tests']


def test_ready_plan_fills_missing_history_before_bounded_completion():
    s = Scenario(actions=[])
    e = run_new(s)
    from nova_agent.clinical_interview import missing_foundation_topics
    assert not missing_foundation_topics(e.pstate)
    assert 2 < s.chat_calls <= 14 and s.turns <= 50


def test_acute_hypoxemia_skips_routine_history_and_submits():
    s = Scenario(vitals='SpO2 86%, 맥박 120 회/분')
    e = run_new(s)
    assert not any(t.category == 'patient_concern' for t in e.turns)
    assert any('119' in x[1] for x in s.events)
    assert s.closed and s.turns <= 5


def test_failed_planner_uses_fallback_and_still_submits():
    s = Scenario()
    original = s.respond
    s.chat_reply = lambda system, content: '{}' if '"actions"' in system else original(system, content)
    e = run_new(s)
    assert e._fallback_used and s.closed
    assert len(s.events) <= 50


def test_new_current_closing_symptom_is_recorded_and_hypothetical_is_not():
    e, _ = fresh()
    hypothetical = SimpleNamespace(reply='지금은 괜찮은데 숨이 차면 어떡하죠?', text='질문 있나요?', turn=1)
    assert not e._closing_observation(hypothetical)
    current = SimpleNamespace(reply='지금 갑자기 숨이 차요.', text='질문 있나요?', turn=2)
    assert e._closing_observation(current)
    assert '지금 갑자기 숨이 차요.' in e._late_clinical[0]


def test_cached_plan_is_rechecked_when_new_measured_danger_appears():
    e, _ = fresh(); accept(e, proposal())
    assert '2일 내' in e._engine_plan([], None)['follow_up']
    e.pstate.record_exam('oxygen', 'SpO2 86%')
    assert '2일 내' not in e._engine_plan([], None)['follow_up']


def test_production_consult_uses_adaptive_controller(monkeypatch):
    seen = []
    monkeypatch.setattr(AdaptiveEncounter, 'run', lambda self: seen.append(type(self).__name__) or 'ok')
    assert A.consult(FakeClient(Scenario()), {}) == 'ok'
    assert seen == ['AdaptiveEncounter']


def test_positive_result_interrupts_stale_batch_before_next_action():
    s = Scenario(actions=[dict(ACTIONS[0], reassess_on_positive=True), ACTIONS[1]])
    run_new(s)
    assert not any(x.get('question') == ACTIONS[1]['text'] for x in s.inputs[1]['PATIENT_EVIDENCE'])
    assert any(x.get('answer') == '네, 자주 봐요.' for x in s.inputs[1]['PATIENT_EVIDENCE'])


def test_planner_cannot_bypass_turn_cap_even_if_it_never_stops():
    s = Scenario()
    original = s.respond
    def endless(system, content):
        if '"actions"' in system:
            return json.dumps({'actions': [{'kind': 'SAY', 'text': f'생활 변화 {s.chat_calls}-{i}는요?',
                'topic': f'new{s.chat_calls}-{i}'} for i in range(6)]})
        return original(system, content)
    s.chat_reply = endless
    run_new(s)
    assert s.chat_calls <= 14 and s.turns <= 50 and s.closed


def test_closing_new_symptom_is_reviewed_using_its_actual_observation_id():
    class NewSymptom(Scenario):
        def action(self, body):
            result = super().action(body)
            if body['action'] == 'SAY' and body['content'] == '궁금하거나 걱정되는 점이 더 있나요?':
                result['content'] = '지금 갑자기 가슴이 아프고 식은땀이 나요.'
            return result
        def respond(self, system, content):
            data = json.loads(content)
            rows = data['PATIENT_EVIDENCE']
            late = next((r for r in rows if r.get('category') == 'closing_report'), None)
            if late:
                p = proposal()
                p['plan']['disposition'] = {'level': 'emergency', 'where': '응급실',
                    'reason': '새 급성 흉통의 평가', 'evidence': [late['id']]}
                self.inputs.append(data)
                return json.dumps(p, ensure_ascii=False)
            return super().respond(system, content)
    s = NewSymptom()
    run_new(s)
    assert any('119' in x[1] for x in s.events)
    assert '지금 갑자기 가슴' in s.record['S']['hpi']
    assert '즉시' in s.record['P']['follow_up']
    assert s.closed and s.turns <= 50


def test_short_deadline_same_day_disposition_is_not_replaced_by_later_recheck(monkeypatch):
    e, s = fresh()
    p = proposal(); p['plan']['disposition']['level'] = 'same_day'
    accept(e, p)
    monkeypatch.setattr(e, 'seconds_left', lambda: 60)
    e._explain([], None)
    assert len(s.events) == 3
    assert any('당일 진료' in x[1] for x in s.events)
    assert any('고열' in x[1] for x in s.events)


def test_unreviewed_drug_change_blocked_without_blocking_no_abrupt_stop_advice():
    assert not care_text('복용 약을 갑자기 끊으세요')
    assert care_text('약을 임의로 중단하지 마세요')


@pytest.mark.parametrize('phase,code', [('before', 'API_UNAVAILABLE'), ('after', 'INVALID_API_RESPONSE')])
def test_new_controller_retains_request_replay_and_one_submission(phase, code):
    s = Scenario(fail=[(phase, code)])
    e = run_new(s)
    assert s.closed and s.turns == len(e.turns) and s.turns <= 50


def test_ready_but_rejected_exam_response_cannot_make_exam_normal():
    s = Scenario(actions=[], reject_exam=lambda _: 'EXAM_NOT_RECOGNIZED')
    run_new(s)
    assert any(x[0] == 'EXAM' for x in s.events)
    assert '늑골척추각' not in s.record['O']['exam']
    assert '특이 소견(-)' not in s.record['O']['exam']


def test_invalid_first_batch_has_one_bounded_repair_with_feedback():
    s = Scenario()
    s.plans = [[{'kind':'SAY', 'text':'가' * 31}], [ACTIONS[0]], []]
    run_new(s)
    assert s.inputs[1]['rejected_actions_do_not_repeat'][0]['reason'] == 'invalid_action_or_length'
    assert any(x[1] == ACTIONS[0]['text'] for x in s.events)
    assert s.chat_calls <= 14 and all(len(x[1]) <= 30 for x in s.events)
