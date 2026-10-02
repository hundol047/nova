"""Finalization guard semantics; these are development tests, not patient accuracy."""
import pytest
from nova_agent.differential import DifferentialItem, has_required_diagnostic_context
from nova_agent.state import PatientState


def item():
    return DifferentialItem(diagnosis='Acute Pyelonephritis', diagnosis_id='pyelonephritis',
        rank=1, score=4, score_ratio=.8, supporting_evidence=['fever','pyuria'],
        urgency='MEDIUM', dangerous_if_missed=False, confidence_band='HIGH')


@pytest.mark.parametrize('text', ['fever with chills','rigors and nausea',
    'fever; denies flank pain', 'possible dysuria', 'CVA tenderness is absent',
    'no pyuria', 'negative nitrites'])
def test_systemic_or_unconfirmed_findings_cannot_localize_infection(text):
    state = PatientState(case_id='context', chief_complaint=text)
    assert not has_required_diagnostic_context(item(),state)


def test_historical_result_is_not_current_localization():
    state = PatientState(case_id='old',chief_complaint='fever')
    state.laboratory_tests['urinalysis']='last year: pyuria; current urinalysis pending'
    assert not has_required_diagnostic_context(item(),state)


def test_family_or_past_history_cannot_replace_current_context():
    state = PatientState(case_id='history',chief_complaint='fever')
    state.past_medical_history=['pyuria']
    state.family_history=['parent had flank pain']
    assert not has_required_diagnostic_context(item(),state)


@pytest.mark.parametrize('text',['positive nitrites','pyuria','positive urine culture',
    'leukocyte esterase positive'])
def test_urine_evidence_allows_assessment_without_urinary_symptoms(text):
    state = PatientState(case_id='atypical',chief_complaint='fever; denies dysuria')
    state.laboratory_tests['urinalysis']=text
    assert has_required_diagnostic_context(item(),state)


def test_exam_can_supply_context():
    state = PatientState(case_id='exam',chief_complaint='fever')
    state.physical_examinations['costovertebral_tenderness']='CVA tenderness'
    assert has_required_diagnostic_context(item(),state)
