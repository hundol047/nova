"""Real turn-state -> observed bedside feature -> retrieval -> active reasoning."""
import pytest
from nova_agent.config import get_config
from nova_agent.state import PatientState
from nova_agent.differential import DifferentialEngine
from nova_agent.candidate_generator import _catalogued_exam_features
from nova_agent.ontology.registry import get_default_catalog


@pytest.fixture(autouse=True)
def config(monkeypatch):
    monkeypatch.setenv('NOVA_LLM_PROVIDER', 'mock')
    monkeypatch.setenv('NOVA_COMPETITION_RETRIEVAL', '1')
    get_config(reload=True)
    yield
    monkeypatch.undo(); get_config(reload=True)


def test_specific_obtained_exam_reintroduces_a_previously_absent_candidate():
    s = PatientState(chief_complaint='An unclear discomfort.', preliminary_rules=True)
    engine = DifferentialEngine()
    assert not any(d.diagnosis_id == 'onto::tier2:pericarditis' for d in engine.update(s))
    s.record_exam('cardiac_auscultation', 'A pericardial friction rub is heard.')
    candidate = next(d for d in engine.update(s) if d.diagnosis_id == 'onto::tier2:pericarditis')
    assert 'friction rub' in candidate.supporting_evidence
    assert candidate.rank <= 25
    assert not s.laboratory_tests and not s.imaging


@pytest.mark.parametrize('result', ['No friction rub.', 'A friction rub cannot be confirmed.',
                                   'Not assessed.', 'My brother had a friction rub years ago.'])
def test_unobserved_denied_and_other_subject_findings_do_not_expand(result):
    from nova_agent.clinical_presentation import build_clinical_presentation
    s = PatientState(chief_complaint='An unclear discomfort.', preliminary_rules=True)
    s.record_exam('cardiac_auscultation', result)
    p = build_clinical_presentation(s)
    assert 'friction rub' not in _catalogued_exam_features(get_default_catalog(), p.observed_exam_text)
    assert not any('friction rub' in d.supporting_evidence for d in DifferentialEngine().update(s))


def test_exam_expansion_has_a_bounded_existing_vocabulary():
    catalog = get_default_catalog()
    vocabulary = {f.lower() for c in catalog.all_concepts() for f in (*c.typical_features, *c.confirmatory_findings)}
    result = _catalogued_exam_features(catalog, sorted(vocabulary))
    assert len(result) == 12 and set(result) <= vocabulary
    assert result == _catalogued_exam_features(catalog, sorted(vocabulary))


def test_bare_patient_claim_is_not_passed_as_an_observed_bedside_result():
    from nova_agent.clinical_presentation import build_clinical_presentation
    s = PatientState(chief_complaint='I think I have a friction rub.')
    assert not build_clinical_presentation(s).observed_exam_text


def test_unconfirmed_other_finding_does_not_erase_a_separate_positive_clause():
    from nova_agent.clinical_presentation import build_clinical_presentation
    s = PatientState(chief_complaint='An unclear discomfort.')
    s.record_exam('cardiac_auscultation', 'Fever cannot be confirmed; a friction rub is present.')
    p = build_clinical_presentation(s)
    assert 'friction rub' in _catalogued_exam_features(get_default_catalog(), p.observed_exam_text)


@pytest.mark.parametrize('text', [
    'The report says atrial fibrillation cannot be confirmed.',
    'The letter says pulmonary embolism is not yet confirmed.',
    'The report states the clinician could not establish atrial fibrillation.',
])
def test_unconfirmed_is_neither_documented_positive_nor_definite_exclusion(text):
    from nova_agent.documented_diagnosis import documented_diagnosis_ids, documented_diagnosis_mentions
    assert not documented_diagnosis_ids([text])
    mentions = documented_diagnosis_mentions([text])
    assert mentions and all(m.assertion == 'UNCERTAIN' for m in mentions)
