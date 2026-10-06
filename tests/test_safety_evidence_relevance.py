"""Software regressions: candidate provenance cannot override present evidence."""
import pytest
from nova_agent.state import PatientState
from nova_agent.differential import DifferentialEngine
from nova_agent.safety import SafetyLayer


def flags(text, **kwargs):
    state = PatientState(case_id='evidence-relevance', chief_complaint=text,
                         demographics={'age':55,'sex':'male'}, **kwargs)
    return {f.diagnosis_id for f in SafetyLayer().assess(state, DifferentialEngine().update(state))}


@pytest.mark.parametrize('text', ['黒色便', '黒い便が出る', '흑변', '검은 변'])
def test_current_melena_supported_even_when_candidate_started_as_safety_only(text):
    assert 'gi_bleeding' in flags(text)


@pytest.mark.parametrize('text', ['黒色便はありません', '흑변은 없습니다', 'no melena'])
def test_negated_bleeding_is_not_evidence(text):
    assert 'gi_bleeding' not in flags(text)


def test_family_history_does_not_supply_current_bleeding_evidence():
    assert 'gi_bleeding' not in flags('routine check', family_history=['melena'])


def test_empty_safety_candidates_are_not_blanket_flags():
    assert not flags('routine check')


def test_new_speech_deficit_in_dizziness_is_safety_relevant():
    assert 'ischemic_stroke' in flags('sudden dizziness', physical_examinations={'neuro_exam':'dysarthria'})


def test_denied_speech_deficit_does_not_add_stroke_flag():
    assert 'ischemic_stroke' not in flags('routine check', physical_examinations={'neuro_exam':'no dysarthria'})


def test_korean_denied_cold_sweat():
    assert 'acute_coronary_syndrome' not in flags('가슴 통증', associated_symptoms=['식은땀은 없습니다'])


@pytest.mark.parametrize('text', ['sweating and tremor', 'palpitations and tachycardia', '식은땀'])
def test_nonspecific_features_alone_do_not_bypass_relevance(text):
    assert 'acute_coronary_syndrome' not in flags(text)
