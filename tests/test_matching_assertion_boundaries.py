"""Unrelated assertions must not jointly create a diagnostic feature."""
import pytest
from nova_agent.matching import feature_present


@pytest.mark.parametrize('boundary', ['. ', '; ', '\n'])
@pytest.mark.parametrize('scrub', [False, True])
def test_unrelated_location_and_pain_do_not_combine(boundary, scrub):
    assert not feature_present('left arm pain',
        ['Blood pressure measured in the left arm' + boundary + 'Abdominal pain persists'],
        scrub_negated_spans=scrub)


def test_strict_overlap_cannot_borrow_qualifier_from_another_sentence():
    assert not feature_present('ST elevation',
        ['ST segments were assessed. Elevation of liver enzymes was detected.'], strict=True)


@pytest.mark.parametrize('text', [
    'Left arm pain persists. Blood pressure is normal.',
    'No chest pain; left arm pain persists.',
    'Temperature 37.5 degrees. Left arm pain persists.',
])
def test_local_positive_evidence_survives(text):
    assert feature_present('left arm pain', [text], scrub_negated_spans=True)


def test_negated_local_evidence_stays_negative():
    assert not feature_present('left arm pain',
        ['No left arm pain. Abdominal pain persists.'], scrub_negated_spans=True)


def test_decimal_not_split():
    assert feature_present('3.5 mmol', ['Potassium 3.5 mmol/L'], strict=True)


def test_comma_linked_modifier_is_not_a_separate_assertion():
    assert feature_present('sudden dyspnea', ['Dyspnea, sudden onset'],
                           scrub_negated_spans=True, strict=True)
