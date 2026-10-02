"""Development regressions for candidate retention and symptom provenance."""
import pytest
from nova_agent.candidate_generator import generate_candidates
from nova_agent.clinical_presentation import ClinicalPresentation
from nova_agent.chief_complaint import CROSS_CUTTING_DANGEROUS_DIAGNOSES
from nova_agent.matching import feature_present
from nova_agent.differential import DifferentialEngine, has_positive_diagnostic_support
from nova_agent.state import PatientState


@pytest.mark.parametrize('symptoms', [
    ['abdominal_pain','fever'], ['dyspnea','cough','leg_swelling'],
    ['headache','urinary_symptoms'], ['abdominal_pain','dyspnea','fever','weakness'],
])
def test_dangerous_safety_candidates_survive_pool_limit(symptoms):
    pool = generate_candidates(ClinicalPresentation(symptoms=symptoms))
    assert set(CROSS_CUTTING_DANGEROUS_DIAGNOSES) <= {c.id for c in pool}


@pytest.mark.parametrize('text', ['BP 130/75 in the left arm', 'left arm is warm',
                                 'left arm pain is absent', 'denies left arm pain'])
def test_arm_measurement_is_not_arm_pain(text):
    assert not feature_present('left arm pain',[text],scrub_negated_spans=True)


@pytest.mark.parametrize('text', ['left arm hurts', 'aching left arm',
                                 'left arm discomfort', 'left arm 통증'])
def test_explicit_pain_synonyms_are_preserved(text):
    assert feature_present('left arm pain',[text],scrub_negated_spans=True)


def test_known_copd_without_current_symptoms_is_not_diagnostic_support():
    state = PatientState(case_id='history',chief_complaint='assessment')
    state.past_medical_history = ['COPD']
    for item in DifferentialEngine().update(state):
        if item.diagnosis_id == 'asthma_copd_exacerbation':
            assert not has_positive_diagnostic_support(item)
