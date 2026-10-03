import pytest
from nova_agent.matching import feature_present
from nova_agent.objective_evidence import normalize_objective_evidence
from nova_agent.state import PatientState


@pytest.mark.parametrize('text', ['possible pleural effusion', 'pleural effusion is suspected',
                                  'cannot exclude pleural effusion', 'pleural effusion not ruled out',
                                  'pleural effusion may be present'])
def test_uncertain_report_is_not_affirmative_confirmation(text):
    assert not feature_present('pleural effusion', [text], scrub_negated_spans=True, strict=True)


def test_uncertainty_does_not_erase_separate_confirmed_clause():
    assert feature_present('focal consolidation', ['Possible effusion; focal consolidation is present'],
                           scrub_negated_spans=True, strict=True)


@pytest.mark.parametrize('text', ['possible potassium 6.8', 'potassium 6.8 remains uncertain'])
def test_qualified_numeric_value_is_not_an_unqualified_measurement(text):
    state = PatientState(case_id='uncertain', chief_complaint='assessment')
    state.laboratory_tests['potassium'] = text
    result = normalize_objective_evidence(state)['lab.potassium']
    assert result.value is None
    assert result.interpretation == 'unknown'


def test_affirmative_measurement_remains_available():
    state = PatientState(case_id='measured', chief_complaint='assessment')
    state.laboratory_tests['potassium'] = 'potassium 6.8 mEq/L'
    assert normalize_objective_evidence(state)['lab.potassium'].value == 6.8
