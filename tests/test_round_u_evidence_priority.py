"""Specific observed pattern vs a fragment, without changing negative scores."""
import pytest
from nova_agent.differential import _apply_observed_detail_priority, _score_disease
from nova_agent.state import PatientState


def row(identifier, feature, state, optional=()):
    e = dict(id=identifier, typical_features=[feature, *optional], risk_factors=[], confirmatory_findings=[])
    score, maximum, support, contra, missing = _score_disease(e, state)
    return score, score/maximum, e, support, contra, missing, 'LOW'


def test_optional_absence_does_not_make_a_fragment_more_explanatory():
    s = PatientState(chief_complaint='A mottled copper discoloration on the forearm')
    s.pertinent_negatives = ['no nausea']
    full = row('pattern', 'mottled copper discoloration on the forearm', s, ('nausea',))
    fragment = row('fragment', 'copper discoloration', s)
    original_scores = full[0], fragment[0]
    result = _apply_observed_detail_priority([fragment, full], s)
    assert result == [full, fragment]
    assert 'nausea' in result[0][4] and (full[0], fragment[0]) == original_scores


@pytest.mark.parametrize('negative', ['no mottled copper discoloration on the forearm', 'no unilateral swelling'])
def test_real_conflict_or_specific_contradiction_prevents_precedence(negative):
    s = PatientState(chief_complaint='A mottled copper discoloration on the forearm')
    s.pertinent_negatives = [negative]
    full = row('pattern', 'mottled copper discoloration on the forearm', s, ('unilateral swelling',))
    fragment = row('fragment', 'copper discoloration', s)
    assert _apply_observed_detail_priority([fragment, full], s) == [fragment, full]


def test_previously_positive_generic_symptom_is_a_direct_conflict():
    s = PatientState(chief_complaint='Mottled copper discoloration on the forearm with nausea')
    s.pertinent_negatives = ['no nausea']
    full = row('pattern', 'mottled copper discoloration on the forearm', s, ('nausea',))
    fragment = row('fragment', 'copper discoloration', s)
    assert _apply_observed_detail_priority([fragment, full], s) == [fragment, full]


def test_unrelated_positive_pattern_does_not_get_priority():
    s = PatientState(chief_complaint='Mottled copper discoloration on the forearm and a broad silver stripe')
    s.pertinent_negatives = ['no nausea']
    full = row('pattern', 'mottled copper discoloration on the forearm', s, ('nausea',))
    separate = row('separate', 'broad silver stripe', s)
    assert _apply_observed_detail_priority([separate, full], s) == [separate, full]
