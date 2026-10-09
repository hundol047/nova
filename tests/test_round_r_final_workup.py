"""Do not turn action coverage or general support into a specific final diagnosis."""
from types import SimpleNamespace
import pytest
from nova_agent.state import PatientState
from nova_agent.differential import DifferentialEngine, _score_disease
from nova_agent.final_decision import decide_final, support_problems
from nova_agent.resolution import workup_coverage, is_resolved
from nova_agent.missing_info import MissingInformationAnalyzer, _resolve_entry
from nova_agent.history_followup import SHORT_FOLLOWUPS, followup_questions
from nova_agent.preliminary import question_is_faithful, _say_core

@pytest.fixture(autouse=True)
def competition(monkeypatch):
    from nova_agent.config import get_config
    monkeypatch.setenv('NOVA_COMPETITION_RETRIEVAL','1');get_config(reload=True)
    yield
    monkeypatch.undo();get_config(reload=True)

@pytest.mark.parametrize('text', ['I have associated lightheadedness.',
    'The previous diagnosis was atrial fibrillation five years ago.',
    'My father has atrial fibrillation.'])
def test_sparse_history_never_names_danger(text):
    s=PatientState(chief_complaint=text,preliminary_rules=True)
    assert decide_final(s,DifferentialEngine().update(s),'information_exhausted').undifferentiated

def test_current_documented_arrhythmia_beats_comorbidity_only_mesenteric():
    s=PatientState(chief_complaint='The letter confirms atrial fibrillation; there is no fever.',preliminary_rules=True)
    assert decide_final(s,DifferentialEngine().update(s)).primary_id=='cardiac_arrhythmia'

def test_unknown_history_and_unavailable_chemistry_are_not_observed():
    s=PatientState(chief_complaint='Weakness',preliminary_rules=True)
    for k in ('past_medical_history','medication','associated_symptoms'):
        s.record_ask(k,'Please describe.','I do not know.')
    assert not is_resolved('severe_electrolyte_disorder',[],s)
    coverage=workup_coverage('severe_electrolyte_disorder',s)
    assert len(coverage['unknown'])==3 and 'bmp' in coverage['unavailable']
    assert not coverage['disease_excluded']

def test_murmur_has_a_feasible_exam_and_rejection_does_not_resolve_it():
    s=PatientState(chief_complaint='Exertional syncope with exertional chest pain',preliminary_rules=True)
    did='onto::tier2:aortic_stenosis'
    assert 'cardiac_auscultation' in _resolve_entry(did)['discriminating_exams']
    d=DifferentialEngine().update(s)
    actions=MissingInformationAnalyzer().analyze(s,d,[])
    assert any(a.key=='cardiac_auscultation' and did in a.disease_ids_discriminated for a in actions)
    s.record_exam_rejected('cardiac_auscultation')
    assert not is_resolved(did,[],s)
    assert 'cardiac_auscultation' in workup_coverage(did,s)['rejected']

def test_family_risk_is_preserved_without_patient_migraine():
    s=PatientState(chief_complaint='I feel tired')
    s.record_ask('family_history','Family illnesses?','My mother has migraine')
    score,_,support,_,_=_score_disease(_resolve_entry('migraine'),s)
    assert 'family history of migraine' in support
    assert s.family_history[0] in s.all_findings_text()
    assert not any('migraine' in f.lower() for f in s.all_findings_text(include_family=False))

@pytest.mark.parametrize('key',list(SHORT_FOLLOWUPS))
def test_followups_have_faithful_single_short_questions(key):
    for lang in ('en','ko','ja','zh'):
        text=_say_core(key,lang,'')
        assert len(text)<=30 and question_is_faithful(key,lang)
        assert text.endswith(('?','？'))

def test_followup_needs_clinical_cluster_and_preserves_drug_information():
    s=PatientState(chief_complaint='Muscle cramps and muscle weakness',preliminary_rules=True)
    s.record_ask('medication','Medicines?','I take furosemide')
    item=next(d for d in DifferentialEngine().update(s) if d.diagnosis_id=='severe_electrolyte_disorder')
    keys=followup_questions(s,item)
    assert 'medication:recent medication changes' in keys
    assert 'associated_symptoms:vomiting' in keys and 'associated_symptoms:diarrhea' in keys
    single=SimpleNamespace(diagnosis_id=item.diagnosis_id,rank=1,supporting_evidence=['diuretic use'])
    assert followup_questions(s,single)==[]
