"""A lone stool symptom is not an observed infectious cause."""
import pytest
from nova_agent.differential import DifferentialItem
from nova_agent.final_decision import support_problems
from nova_agent.state import PatientState


def item(evidence):
    return DifferentialItem(diagnosis_id='gastroenteritis', diagnosis='Acute Gastroenteritis',
                            score=4.0, rank=1, score_ratio=1.0, urgency='routine',
                            confidence_band='LOW', dangerous_if_missed=False, supporting_evidence=evidence)


def test_single_stool_observation_keeps_cause_unresolved():
    candidate = item(['diarrhea'])
    state = PatientState(chief_complaint='Loose stools after a new medication.', preliminary_rules=True)
    assert 'single_nonspecific_support' in support_problems(candidate, state, [candidate])


@pytest.mark.parametrize('evidence', [
    ['diarrhea', 'vomiting', 'abdominal cramps'],
    ['documented diagnosis', 'diarrhea'],
])
def test_converging_pattern_and_current_documentation_remain_eligible(evidence):
    candidate = item(evidence)
    assert not support_problems(candidate, PatientState(preliminary_rules=True), [candidate])
