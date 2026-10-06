import pytest
from nova_agent.state import PatientState
from nova_agent.objective_evidence import normalize_objective_evidence


def result(values, lab='lab.potassium'):
    state = PatientState(case_id='numeric-audit', chief_complaint='assessment')
    state.laboratory_tests.update(values)
    return normalize_objective_evidence(state)[lab]


@pytest.mark.parametrize('text', ['potassium 4.0; potassium 7.1',
                                  'potassium 7.1; potassium 4.0',
                                  'potassium 4.0; potassium 7.1; elevated potassium'])
def test_unordered_conflicts_cannot_pick_first_value_or_qualitative_fallback(text):
    finding = result({'potassium': text})
    assert finding.value is None
    assert finding.interpretation == 'unknown'


def test_panel_and_standalone_conflicts_are_detected():
    assert result({'potassium': 'potassium 4.0', 'bmp': 'K 7.1'}).interpretation == 'unknown'


def test_duplicate_same_result_does_not_create_conflict():
    assert result({'potassium': 'potassium 7.1', 'bmp': 'K 7.1'}).value == 7.1


def test_historical_value_does_not_override_explicit_current_value():
    finding = result({'creatinine': 'previously creatinine 5.0; current creatinine 1.0'}, 'lab.creatinine')
    assert finding.value == 1.0


@pytest.mark.parametrize('text', ['historical potassium 7.1', 'baseline potassium 7.1',
                                  'reference range potassium 3.5', 'not potassium 7.1'])
def test_noncurrent_or_negated_number_is_not_a_current_measurement(text):
    finding = result({'potassium': text})
    assert finding.value is None
    assert finding.interpretation == 'unknown'


@pytest.mark.parametrize('text,value,interpretation', [
    ('hemoglobin has fallen to 8.2 g/dL', 8.2, 'low'),
    ('hemoglobin dropped to 14.1 g/dL', 14.1, 'normal'),
    ('Hb decreased to 82 g/L', 8.2, 'low'),
    ('hemoglobin rose to 9.3 g/dL', 9.3, 'low'),
])
def test_trend_endpoint_uses_measured_value_and_unit(text, value, interpretation):
    finding = result({'cbc': text}, 'lab.hemoglobin')
    assert finding.value == pytest.approx(value)
    assert finding.interpretation == interpretation


@pytest.mark.parametrize('text', [
    'if hemoglobin falls to 8.2 g/dL',
    'hemoglobin could have fallen to 8.2 g/dL',
    'expected hemoglobin dropped to 8.2 g/dL',
    'historical hemoglobin fell to 8.2 g/dL',
    'no hemoglobin decrease; sodium 128',
    'hemoglobin dropped to an unspecified value; potassium 6.1',
    'hemoglobin dropped to 82 mmol/L',
])
def test_unmeasured_or_invalid_trend_endpoint_stays_unknown(text):
    finding = result({'cbc': text}, 'lab.hemoglobin')
    assert finding.value is None
    assert finding.interpretation == 'unknown'


def test_trend_endpoint_conflicts_are_not_resolved_by_order():
    finding = result({'cbc': 'Hb dropped to 8.2 g/dL; Hb 13.4 g/dL'}, 'lab.hemoglobin')
    assert finding.interpretation == 'unknown'
