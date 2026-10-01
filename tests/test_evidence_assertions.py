"""Assertions must preserve uncertainty, polarity and reported magnitude."""
import pytest
from evaluation.evidence_challenge import PROBES
from nova_agent.state import PatientState
from nova_agent.differential import _score_disease
from nova_agent.knowledge.retrieval import disease_by_id
from nova_agent.evidence_interpreter import concept_present


@pytest.mark.parametrize('key,procedure,diagnosis,text,label,expected', PROBES, ids=[r[0] for r in PROBES])
def test_asserted_evidence(key, procedure, diagnosis, text, label, expected):
    if procedure == 'concept':
        actual=concept_present(diagnosis,[text])
    else:
        state=PatientState()
        state.record_test(procedure,text)
        actual=label in _score_disease(disease_by_id(diagnosis),state)[2]
    assert actual is expected


def test_observed_positional_trigger_and_calendar_month_are_not_hypotheticals():
    from nova_agent.evidence_interpreter import asserted_clauses
    assert asserted_clauses('symptoms worsen if lying flat')
    assert asserted_clauses('asthma diagnosed in May')
    assert 'if elevated troponin' not in asserted_clauses('if elevated troponin, reassess')
