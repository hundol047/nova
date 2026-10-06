"""Current localized imaging evidence; no case labels or benchmark inputs."""
import pytest
from nova_agent.differential import _score_disease
from nova_agent.state import PatientState

ENTRY = {'id':'test_only', 'confirmatory_findings':['focal consolidation']}


def support(text):
    state=PatientState(case_id='imaging-language',chief_complaint='cough',imaging={'cxr':text})
    return _score_disease(ENTRY,state)[2]


@pytest.mark.parametrize('region',['right upper lobe','right middle lobe','right lower lobe','left upper lobe','left lower lobe','lobar'])
def test_localized_consolidation_is_recognized(region):
    assert 'focal consolidation' in support(region+' consolidation')


@pytest.mark.parametrize('text',[
    'no right upper lobe consolidation', 'possible left lower lobe consolidation',
    'historical report: focal consolidation; current result: clear lungs',
    'prior result: right middle lobe consolidation; current result: normal',
    'reference range: focal consolidation', 'right upper lobe nodule',
])
def test_negated_historical_uncertain_or_different_finding_not_positive(text):
    assert 'focal consolidation' not in support(text)


def test_current_positive_retained_after_historical_negative():
    assert 'focal consolidation' in support('historical report: no consolidation; current result: left lower lobe consolidation')
