"""Observation relations, not diagnosis-specific score patches."""
import pytest
from nova_agent.matching import feature_present, feature_present_with_aliases, or_branches
from nova_agent.state import PatientState
from nova_agent.differential import DifferentialEngine
from nova_agent.final_decision import decide_final
from nova_agent.clinical_concepts import canonical_findings_for


@pytest.fixture(autouse=True)
def config(monkeypatch):
    from nova_agent.config import get_config
    monkeypatch.setenv('NOVA_LLM_PROVIDER', 'mock')
    monkeypatch.setenv('NOVA_COMPETITION_RETRIEVAL', '1')
    get_config(reload=True)
    yield
    monkeypatch.undo(); get_config(reload=True)


@pytest.mark.parametrize('feature,text,expected', [
    ('worse after meals', 'I eat poor meals and feel drained.', False),
    ('worse after meals', 'I take a capsule after dinner.', False),
    ('worse after meals', 'I feel weak after poor meals.', False),
    ('worse after meals', 'Heartburn gets worse after dinner.', True),
    ('worse after meals', 'After a heavy meal my pain worsens.', True),
    ('worse after meals', 'worse with after large meals', True),
    ('worse after meals', 'The burning gets worse after I eat.', True),
    ('worse after meals', 'No heartburn after meals.', False),
    ('worse after meals', 'My aunt has pain after meals. I am tired.', False),
    ('worse after meals', '식사 후 속쓰림이 심해져요.', True),
    ('worse lying down', 'The discomfort is worse when I lie down.', True),
    ('worse lying down', 'worse with when I lie down', True),
    ('worse lying down', 'The discomfort is better when I lie down.', False),
    ('worse lying down', 'I take tablets lying down.', False),
    ('improves with sitting or lying down', 'worse with lying down', False),
    ('improves with sitting or lying down', 'after big meals and lying down', False),
    ('improves with sitting or lying down', 'It eases when I lie down.', True),
    ('improves with sitting or lying down', 'relieved by when I lie down', True),
    ('improves with sitting or lying down', 'It passes when I sit back down.', True),
    ('improves with sitting or lying down', '누우면 더 아파요.', False),
    ('improves with sitting or lying down', '누우면 나아져요.', True),
])
@pytest.mark.parametrize('matcher', [feature_present, feature_present_with_aliases])
def test_relation_and_direction(feature, text, expected, matcher):
    assert matcher(feature, [text], scrub_negated_spans=True) is expected


def test_relief_disjunction_cannot_generate_a_bare_posture_branch():
    assert not or_branches('improves with sitting or lying down')


@pytest.mark.parametrize('text', ['A fluttering feeling somewhere.', 'My eyelid is fluttering.',
                                 'I feel fluttering in my heart.', 'My mother has an uneven pulse.'])
def test_fluttering_is_not_an_observed_irregular_pulse(text):
    assert not feature_present_with_aliases('irregular heartbeat', [text])
    s = PatientState(chief_complaint=text, preliminary_rules=True)
    s.record_initial_vitals('BP 122/74, HR 48, RR 15, Temp 36.7, SpO2 98%')
    diff = DifferentialEngine().update(s)
    assert not any('irregular heartbeat' in d.supporting_evidence for d in diff)
    assert decide_final(s, diff, 'information_exhausted').primary_id != 'cardiac_arrhythmia'


def test_subjective_cardiac_feeling_and_measured_irregularity_are_preserved_separately():
    assert feature_present_with_aliases('palpitations', ['My heart is fluttering.'])
    s = PatientState(chief_complaint='An odd sensation.', preliminary_rules=True)
    s.record_exam('cardiac_auscultation', 'The pulse is irregular.')
    assert any('irregular heartbeat' in d.supporting_evidence for d in DifferentialEngine().update(s))


def test_posture_question_context_survives_without_inverting_it():
    s = PatientState(chief_complaint='Heartburn.', preliminary_rules=True)
    s.record_ask('aggravating', 'What worsens it?', 'after large meals and lying down')
    assert feature_present_with_aliases('worse after meals', s.all_findings_text())
    assert feature_present_with_aliases('worse lying down', s.all_findings_text())
    d = DifferentialEngine().update(s)
    assert not any('improves with sitting or lying down' in x.supporting_evidence for x in d)


def test_rotation_duration_and_trigger_require_their_own_observation():
    observed = canonical_findings_for('When I rolled over the room spun for half a minute.')
    assert {'vertigo', 'brief episodic vertigo', 'triggered by head position change'} <= set(observed)
    for text in ['I turn the chair and feel tired.', 'My father says the room spun for half a minute.',
                 'The room has been spinning continuously for six hours.']:
        assert 'brief episodic vertigo' not in canonical_findings_for(text)


def test_undifferentiated_rate_syncope_plan_keeps_ecg_without_fabricating_result():
    from nova_agent.soap import build_soap
    s = PatientState(chief_complaint='I lost consciousness.', preliminary_rules=True)
    s.record_initial_vitals('BP 117/72, HR 39, RR 16, Temp 36.7, SpO2 98%')
    d = DifferentialEngine().update(s)
    final = decide_final(s, d, 'information_exhausted')
    soap = build_soap(s, d, final=final)
    assert 'ECG' in soap['P'] and 'immediate emergency' in soap['P']
    assert not s.laboratory_tests and 'no test results' in soap['O']


def test_constitutional_weakness_and_perfusion_findings_do_not_name_a_cause():
    from nova_agent.disposition import disposition_for
    s = PatientState(chief_complaint='Profound weakness and sweating.', preliminary_rules=True)
    s.record_initial_vitals('BP 78/44, HR 134, RR 26, Temp 36.5, SpO2 97%')
    d = DifferentialEngine().update(s)
    final = decide_final(s, d, 'information_exhausted')
    assert final.primary_id == 'unknown'
    assert disposition_for(s, final, d).urgent


def test_severe_weakness_is_not_a_specific_adrenal_finding():
    from nova_agent.differential import DifferentialItem
    from nova_agent.final_decision import support_problems
    item = DifferentialItem(diagnosis_id='onto::tier2:adrenal_crisis', diagnosis='Adrenal crisis',
        rank=1, score=1.25, score_ratio=.2, supporting_evidence=['severe weakness'],
        dangerous_if_missed=True, urgency='CRITICAL', confidence_band='LOW')
    assert 'single_nonspecific_support' in support_problems(item, PatientState(), [item])


def test_fever_and_observed_cognitive_change_are_not_erased_with_perfusion_findings():
    s = PatientState(chief_complaint='Fever and confusion.', preliminary_rules=True)
    s.record_initial_vitals('BP 84/46, HR 126, RR 28, Temp 39.3, SpO2 93%')
    s.record_exam('mental_status_exam', 'Confused and drowsy.')
    d = DifferentialEngine().update(s)
    assert decide_final(s, d).primary_id == 'sepsis'


@pytest.mark.parametrize('text', ['A rash spreads to the arm.', 'My sister has pressure under the breastbone.',
                                 'No pressure under the breastbone.'])
def test_new_anatomical_paraphrases_do_not_borrow_another_sign_or_subject(text):
    assert not feature_present_with_aliases('substernal pressure', [text])
    assert not feature_present_with_aliases('radiates to arm or jaw', [text])


def test_actual_pressure_and_spread_are_preserved():
    assert feature_present_with_aliases('substernal pressure', ['Pressure behind the breastbone.'])
    assert feature_present_with_aliases('radiates to arm or jaw', ['Pressure that spreads to the arm.'])
