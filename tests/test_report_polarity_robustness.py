"""Report assertion semantics; does not establish diagnostic accuracy."""
import pytest
from nova_agent.matching import feature_present


@pytest.mark.parametrize('feature', ['focal consolidation', 'pleural effusion', 'ST elevation'])
@pytest.mark.parametrize('template', ['{} is absent', '{} not seen', '{} was not detected',
                                      '{}: negative', '{} is not present'])
def test_postposed_negation_is_not_positive(feature, template):
    assert not feature_present(feature, [template.format(feature)], scrub_negated_spans=True, strict=True)


@pytest.mark.parametrize('separator', ['. ', '; ', ', ', '\n'])
def test_negative_clause_does_not_erase_next_affirmative_clause(separator):
    assert feature_present('focal consolidation',
                           ['No pleural effusion' + separator + 'Focal consolidation is present'],
                           scrub_negated_spans=True, strict=True)


def test_suffix_negation_does_not_erase_next_affirmative_clause():
    assert feature_present('pleural effusion', ['Focal consolidation is absent. Pleural effusion is present'],
                           scrub_negated_spans=True, strict=True)


@pytest.mark.parametrize('separator', ['. ', '\n', '; '])
def test_patient_answer_sentence_boundaries_preserve_positive_and_negative(separator):
    from nova_agent.state import _split_answer_segments, _segment_is_negated
    segments = _split_answer_segments('Itchy rash on arms' + separator + 'Denies cough')
    assert len(segments) == 2
    assert not _segment_is_negated(segments[0])
    assert _segment_is_negated(segments[1])


def test_sentence_split_does_not_split_decimal():
    from nova_agent.state import _split_answer_segments
    assert _split_answer_segments('Temperature 37.2 today. Denies cough') == ['Temperature 37.2 today', 'Denies cough']
