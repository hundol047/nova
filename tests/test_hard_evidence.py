"""Development safety and equivalence tests, not clinical validation."""
import pytest
from nova_agent.state import PatientState
from nova_agent.objective_evidence import normalize_objective_evidence
from nova_agent.differential import _present_with_aliases, DifferentialEngine
from nova_agent.clinical_presentation import build_clinical_presentation


def reading(key, text):
    state = PatientState(case_id='units', chief_complaint='assessment')
    state.laboratory_tests[key] = text
    return normalize_objective_evidence(state)['lab.' + key]


@pytest.mark.parametrize('key,canonical,alternate', [
    ('hemoglobin','hemoglobin 6.2 g/dL','Hb 62 g/L'),
    ('hemoglobin','hemoglobin 13.5 g/dL','Hgb 135 g / L'),
    ('creatinine','creatinine 1 mg/dL','creatinine 88.4 umol/L'),
    ('creatinine','creatinine 2 mg/dL','creatinine 176.8 µmol/L'),
    ('creatinine','creatinine 5 mg/dL','creatinine 442 μmol / L'),
])
def test_equivalent_units_preserve_interpretation(key, canonical, alternate):
    a,b = reading(key,canonical),reading(key,alternate)
    assert a.value == pytest.approx(b.value)
    assert a.interpretation == b.interpretation
    assert a.unit == b.unit


@pytest.mark.parametrize('text', ['creatinine 100 mmol/L','creatinine 100 umol/Liter',
                                 'creatinine 10 mg/L','possible creatinine 442 umol/L',
                                 'baseline creatinine 442 umol/L'])
def test_unhandled_or_uncertain_units_not_guessed(text):
    assert reading('creatinine',text).value is None


def test_repeated_equivalent_values_do_not_conflict():
    assert reading('creatinine','creatinine 176.8 umol/L; creatinine 2 mg/dL').value == 2
    assert reading('hemoglobin','Hb 62 g/L; Hb 13 g/dL').interpretation == 'unknown'


@pytest.mark.parametrize('text', ['black stool', 'tarry road', 'no black tarry stools',
                                 'possible black tarry stools', 'black tarry stools are absent'])
def test_melena_alias_requires_affirmative_complete_description(text):
    assert not _present_with_aliases('melena',[text])


def test_gi_alias_is_symptom_support_only():
    assert _present_with_aliases('melena',['black and tarry stools'])
    assert _present_with_aliases('hematemesis',['vomited blood'])
    assert not _present_with_aliases('low hemoglobin',['black and tarry stools'])


@pytest.mark.parametrize('location', ['right lower quadrant','left upper quadrant','배꼽 주변','우하복부'])
def test_abdominal_location_remains_routable_after_fever(location):
    state = PatientState(case_id='mixed', chief_complaint=f'{location} 통증 pain')
    assert 'abdominal_pain' in build_clinical_presentation(state).symptoms
    state.associated_symptoms = ['low-grade fever']
    assert 'abdominal_pain' in build_clinical_presentation(state).symptoms


def test_abdominal_routing_does_not_confirm_appendicitis():
    state = PatientState(case_id='nonspecific', chief_complaint='left upper quadrant pain')
    items = DifferentialEngine().update(state)
    assert not any('appendiceal inflammation' in d.supporting_evidence for d in items)


@pytest.mark.parametrize('term', ['melena','hematemesis','hematochezia'])
def test_clinical_bleeding_terms_keep_bleeding_candidates(term):
    state = PatientState(case_id='bleeding', chief_complaint=f'{term} with lightheadedness')
    assert 'gi_bleeding' in build_clinical_presentation(state).symptoms
