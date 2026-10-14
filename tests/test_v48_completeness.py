"""Behavioral coverage with invented fixtures; not clinical scoring."""
import ast
from pathlib import Path

from test_adaptive_encounter import (Scenario, fresh, proposal, accept, run_new,
                                    engine_config, nova_sdk)
from nova_agent.clinical_interview import TOPICS, DETAIL_QUESTIONS, missing_foundation_topics


def test_empty_planner_asks_missing_history_and_reviews_actual_replies():
    s = Scenario(actions=[])
    e = run_new(s)
    from competition.interview_coverage import CORE_HISTORY
    assert not set(CORE_HISTORY).intersection(missing_foundation_topics(e.pstate))
    final_rows = s.inputs[-1]['PATIENT_EVIDENCE']
    for topic in ('medical_history', 'medication_name', 'allergy',
                  'function', 'prior_care'):
        question = TOPICS[topic][1]
        assert sum(t.text == question for t in e.turns) == 1
        assert any(r.get('question') == question for r in final_rows)
    assert s.inputs[-1]['unresolved_history_never_assume_negative']


def test_multiple_positive_screens_get_details_before_empty_plan_can_finish():
    class Positive(Scenario):
        def action(self, body):
            result = super().action(body)
            if body['action'] == 'SAY':
                q = body['content']
                responses = {
                    TOPICS['allergy'][1]: '네.',
                    DETAIL_QUESTIONS['allergy']: '페니실린이요.',
                    TOPICS['allergy_reaction'][1]: '두드러기가 났어요.',
                    TOPICS['medication_name'][1]: '네.',
                    DETAIL_QUESTIONS['medication_name']: '혈압약을 먹고 있어요.',
                    TOPICS['medical_history'][1]: '네.',
                    DETAIL_QUESTIONS['medical_history']: '고혈압입니다.',
                }
                if q in responses:
                    result['content'] = responses[q]
                    self.events[-1] = ('SAY', q, result['content'])
            return result
    s = Positive(actions=[])
    e = run_new(s)
    text = str(s.record)
    assert all(value in text for value in ('고혈압', '혈압약', '페니실린', '두드러기'))
    assert len([t for t in e.turns if t.text in DETAIL_QUESTIONS.values()]) >= 3
    assert len({t.text for t in e.turns}) == len(e.turns)


def test_broad_model_topic_does_not_block_distinct_medication_questions():
    e, _ = fresh('수면제를 먹고 있어요.')
    for question in ('복용 중인 약 이름이 뭔가요?', '수면제 한 번 용량은 몇 mg인가요?',
                     '수면제를 하루 몇 번 드시나요?'):
        assert e._send_planned({'kind': 'SAY', 'text': question, 'topic': 'medication'}) is not None


def test_spoken_plan_includes_review_second_warning_and_two_way_communication():
    e, s = fresh()
    p = proposal()
    p['plan']['precautions'] = '고열이 나면 바로 진료받으세요. 옆구리가 아파도 바로 진료받으세요.'
    p['plan']['treatment'] = '물을 적절히 마셔요. 소변을 참지 마세요.'
    accept(e, p)
    e._explain([], None)
    said = [t.text for t in e.turns]
    assert '증상과 검사 결과를 확인해요' in said
    assert '옆구리가 아파도 바로 진료받으세요' in said
    assert '소변을 참지 마세요' in said
    assert any(t.category == 'understanding_check' for t in e.turns)
    assert any(t.category == 'patient_questions' for t in e.turns)
    assert all(len(t) <= 30 for t in said)


def test_sample_runner_uses_packaged_runtime_factory():
    from competition.nova_sdk_adapter import make_encounter
    from competition.adaptive_encounter import AdaptiveEncounter
    from test_official_sdk_adapter import FakeClient
    assert isinstance(make_encounter(FakeClient(Scenario()), {}), AdaptiveEncounter)
    source = (Path(__file__).resolve().parents[1] / 'scripts/run_dev_samples.py').read_text()
    tree = ast.parse(source)
    assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                   and n.func.id == 'OfficialEncounter' for n in ast.walk(tree))
    assert "getattr(adapter, 'make_encounter', None)" in source


def test_completion_review_can_add_exam_after_early_ready():
    import json
    class Reviewed(Scenario):
        def respond(self, system, content):
            data = json.loads(content)
            if ('"actions"' in system and not data['unasked_general_domains_not_a_mandatory_quota']
                    and not data['physical_exam_actions_attempted']):
                self.inputs.append(data)
                return json.dumps({'actions': [{'kind': 'EXAM', 'text': '늑골척추각을 타진하겠습니다'}]})
            return super().respond(system, content)
    s = Reviewed(actions=[])
    run_new(s)
    assert sum(kind == 'EXAM' and '늑골척추각' in text for kind, text, _ in s.events) == 1
    assert '늑골척추각' in s.record['O']['exam']


def test_short_deadline_still_preserves_submission_with_more_history(monkeypatch):
    e, s = fresh()
    monkeypatch.setattr(e, 'seconds_left', lambda: 60)
    assert e._completion_phase(8) == 0
    assert not s.events
