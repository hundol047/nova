"""Clinical information must be answered, scoped and rechecked at execution time."""
import json
import pytest

from nova_agent.state import PatientState
from nova_agent.clinical_interview import topic_known, next_clinical_action
from test_official_independent_audit import encounter, initialise
from test_official_sdk_adapter import engine_config, nova_sdk
from competition import nova_sdk_adapter as A


@pytest.mark.parametrize('opening,topic,known', [
    ('불면 때문에 수면제를 먹어요. amlodipine 5mg을 먹어요.', 'medication_dose', False),
    ('불면 때문에 수면제를 먹어요, amlodipine 5mg을 먹어요.', 'medication_dose', False),
    ('불면 때문에 수면제를 먹어요. 용량은 잘 모르겠어요.', 'medication_dose', False),
    ('불면 때문에 수면제를 먹어요.', 'medication_name', False),
    ('불면 때문에 졸피뎀 5mg을 매일 밤 먹어요.', 'medication_dose', True),
    ('불면 때문에 졸피뎀 5mg을 매일 밤 먹어요.', 'medication_name', True),
    ('불면입니다. 어머니는 졸피뎀 5mg을 먹어요.', 'medication_dose', False),
    ('체중이 줄어요. 어머니가 더위를 많이 타요.', 'heat', False),
    ('체중이 줄어요. 더위를 타는지는 모르겠어요.', 'heat', False),
    ('체중이 줄어요. 더위는 타지 않아요.', 'heat', True),
    ('키가 작아요. 아버지 키 172cm입니다.', 'parent_height', False),
    ('키가 작아요. 아버지 키 172cm, 어머니 키 162cm입니다.', 'parent_height', True),
])
def test_known_means_actual_topic_evidence(opening, topic, known):
    assert topic_known(PatientState(chief_complaint=opening), topic) is known


def test_unknown_attempt_is_not_known():
    s = PatientState(chief_complaint='불면 때문에 수면제를 먹어요.')
    s.record_ask('medication', '수면제 한 번 용량은 몇 mg인가요?', '잘 모르겠어요.')
    assert not topic_known(s, 'medication_dose')


def test_short_numeric_answer_inherits_its_own_question():
    s = PatientState(chief_complaint='불면 때문에 수면제를 먹어요.')
    s.record_ask('medication', '수면제 한 번 용량은 몇 mg인가요?', '5mg이에요.')
    assert topic_known(s, 'medication_dose')


def test_parent_measurements_are_not_child_growth_records():
    s = PatientState(chief_complaint='키가 작아요. 아버지 키 172cm, 어머니 키 162cm입니다.')
    assert not topic_known(s, 'growth_records')


def test_annual_velocity_answer_inherits_interval():
    s = PatientState(chief_complaint='키가 작아요.')
    s.record_ask('associated_symptoms', '1년 동안 키가 얼마나 컸나요?', '5cm 컸어요.')
    assert topic_known(s, 'growth_velocity')


def test_bowel_frequency_is_not_medication_frequency():
    from nova_agent.clinical_interview import topic_for_question
    assert topic_for_question('하루에 배변을 몇 번 보시나요?') == 'bowel'


def test_generic_medication_question_has_the_same_topic():
    from nova_agent.clinical_interview import topic_for_question
    assert topic_for_question('현재 복용하시는 약이 있습니까?') == 'medication_name'


def test_weight_trajectory_retains_values_and_explicit_interval():
    from nova_agent.interview_evidence import weight_trajectory
    text='3개월간 56kg에서 49kg으로 체중이 줄었어요.'
    facts=weight_trajectory(text)
    assert (facts['previous_weight_kg'],facts['current_weight_kg'],facts['weight_change_kg'])==(56,49,-7)
    assert facts['time_window']=='3개월'
    assert topic_known(PatientState(chief_complaint=text),'weight_change')
    assert topic_known(PatientState(chief_complaint=text),'symptom_onset')


@pytest.mark.parametrize('text',['56에서 49로 줄었어요','어머니는 56kg에서 49kg으로 줄었어요','체중은 49kg입니다'])
def test_weight_trajectory_does_not_invent_missing_or_family_values(text):
    from nova_agent.interview_evidence import weight_trajectory
    assert weight_trajectory(text) is None


def test_new_unresolved_evidence_gets_a_bounded_reassessment(monkeypatch):
    e, _ = encounter(); initialise(e, '불편한 증상이 있어요.')
    assert e._needs_more_information()
    e.turns_left = 4
    assert not e._needs_more_information()


def test_unknown_answer_does_not_trigger_an_endless_interview():
    s = PatientState(chief_complaint='불면 때문에 수면제를 먹어요.')
    seen = []
    for _ in range(20):
        action = next_clinical_action(s)
        if action is None: break
        kind, key, text, _ = action
        seen.append(text)
        s.record_ask(key, text, '잘 모르겠어요.')
    assert len(seen) == len(set(seen)) and len(seen) < 20


def test_followup_rechecks_knowledge_after_each_reply(monkeypatch):
    e, _ = encounter(); initialise(e, '불면 때문에 수면제를 먹어요.')
    monkeypatch.setattr(e, 'chat', lambda *a, **k: json.dumps({'questions': [
        '수면제 한 번 용량은 몇 mg인가요?', '수면제를 하루 몇 번 드시나요?', '한 번에 몇 mg 드세요?']}))
    def say(text, category):
        t = A.Turn('SAY', text, '졸피뎀 5mg을 하루 한 번 매일 밤 먹어요.', category)
        e.turns.append(t); e.turns_left -= 1
        return t
    monkeypatch.setattr(e, 'say', say)
    e._followup_phase()
    assert len(e.turns) == 1


def test_followup_does_not_repeat_equivalent_exam(monkeypatch):
    e, _ = encounter(); initialise(e, '체중이 줄고 더위를 타요.')
    e.pstate.record_exam('thyroid_exam', '갑상선 미만성 비대(+)', request_text='갑상선을 촉진하겠습니다')
    e.turns.append(A.Turn('EXAM', '갑상선을 촉진하겠습니다', '갑상선 미만성 비대(+)', 'thyroid_exam'))
    monkeypatch.setattr(e, 'chat', lambda *a, **k: json.dumps({'exams': ['갑상샘을 촉진하겠습니다']}))
    e._followup_phase()
    assert len(e.turns) == 1


@pytest.mark.parametrize('method', ['action', 'chat'])
def test_provider_unavailable_replays_same_logical_request(method):
    e, _ = encounter(); ids = []
    def fn(*args, request_id, **kwargs):
        ids.append(request_id)
        if len(ids) == 1: raise nova_sdk.NovaError('PROVIDER_UNAVAILABLE', 503)
        return {'choices': [{'message': {'content': '{"primary_diagnosis":"undetermined"}'}}],
                'usage': {'prompt_tokens': 10, 'completion_tokens': 5}}
    if method == 'action': e._call(fn, '질문')
    else:
        e.client.chat = fn
        e.chat([{'role': 'user', 'content': 'question'}], max_tokens=50, effort='low', required=True, case_relevant=True)
    assert len(ids) == 2 and ids[0] == ids[1]


def test_record_evidence_retains_objective_findings_on_failed_doctor():
    e, _ = encounter(); initialise(e, '기침이 있어요.')
    e.pstate.record_exam('lung_auscultation', '수포음(+/+)', request_text='폐를 청진하겠습니다')
    e.turns.append(A.Turn('EXAM', '폐를 청진하겠습니다', '수포음(+/+)', 'lung_auscultation'))
    record, _ = e.official_record([], None)
    assert '수포음(+/+)' in record['A']['evidence']
