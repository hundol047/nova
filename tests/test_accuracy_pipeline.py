"""Behavioral regressions for evidence transport and open candidate reasoning."""
from nova_agent.state import PatientState
from nova_agent.clinical_summary import build_clinical_summary
from nova_agent.differential import DifferentialEngine, _score_disease
from nova_agent.knowledge.retrieval import disease_by_id
from nova_agent.evidence_interpreter import concept_present, objective_findings
from nova_agent.orchestrator import DoctorAgent
from nova_agent.llm_client import build_reasoning_prompt, MockLLMClient


def test_model_receives_medication_history_timing_and_negations():
    state=PatientState(chief_complaint='weakness',demographics={'pregnant':False})
    state.record_ask('medication','Medication?','warfarin')
    state.record_ask('past_medical_history','History?','chronic kidney disease; no surgery')
    state.record_ask('onset','Onset?','about 90 minutes ago')
    state.record_ask('allergy','Allergies?','penicillin rash')
    summary=build_clinical_summary(state,[],[]).to_text()
    for fact in ['warfarin','chronic kidney disease','no surgery','90 minutes','penicillin','not pregnant']:
        assert fact in summary


def test_csf_cells_do_not_become_urinary_infection_evidence():
    state=PatientState(chief_complaint='fever')
    state.record_test('lumbar_puncture','CSF: elevated white cell count')
    pyelo=_score_disease(disease_by_id('pyelonephritis'),state)
    meningitis=_score_disease(disease_by_id('meningitis'),state)
    assert 'elevated white blood cell count' not in pyelo[2]
    assert 'CSF pleocytosis' in meningitis[2]


def test_new_objective_evidence_recovers_a_diagnosis_outside_initial_route():
    state=PatientState(chief_complaint='cough')
    state.record_test('ecg','ST elevation')
    state.record_test('troponin','elevated troponin')
    candidates=DifferentialEngine().update(state)
    assert candidates[0].diagnosis_id=='acute_coronary_syndrome'


def test_concept_variants_keep_negation_local():
    assert concept_present('diarrhea',['watery stools'])
    assert not concept_present('diarrhea',['denies watery stools'])
    assert concept_present('neck stiffness',['no rash but a stiff neck'])
    assert not concept_present('neck stiffness',["I don't have a stiff neck"])


def test_initial_action_collects_vitals_without_matching_complaint():
    a=DoctorAgent();s=a.new_case('neutral','I feel strange')
    action,_,_=a.decide(s)
    assert action.action_type=='EXAM' and action.key=='vital_signs'


def test_known_positive_result_name_is_retained():
    state=PatientState();state.record_test('beta_hcg','positive')
    assert 'positive beta-hCG' in objective_findings(disease_by_id('ectopic_pregnancy'),state)
    state.laboratory_tests['beta_hcg']='not positive'
    assert 'positive beta-hCG' not in objective_findings(disease_by_id('ectopic_pregnancy'),state)


def test_disease_names_do_not_collide_through_truncation():
    from nova_agent.matching import feature_present
    assert not feature_present('hyperthyroidism',['hypertension'])
    assert not feature_present('hypertriglyceridemia',['hypertension'])
    assert feature_present('exertional chest pain',['chest pain with exertion'])


def test_anatomy_is_not_erased_by_phrase_similarity():
    from nova_agent.matching import feature_present
    assert not feature_present('worst headache of life',['worst stomach pain of my life'])


def test_postural_pressure_drop_requires_two_position_bound_readings():
    from nova_agent.postural_evidence import postural_drop
    assert postural_drop('BP 140/82 supine; BP 112/68 standing after 2 minutes') == (28,14)
    assert postural_drop('BP 110/70 HR 90') is None
    assert postural_drop('BP 120/80 supine; BP 116/78 standing') is None
    assert postural_drop('BP 120/80 standing; BP 116/78 supine') is None
