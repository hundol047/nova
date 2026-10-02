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


def test_heartbeat_and_recurrence_do_not_imply_headache():
    state=PatientState(chief_complaint='my heart is pounding',past_medical_history=['similar episodes before'])
    scored=_score_disease(disease_by_id('migraine'),state)
    assert 'unilateral pulsating headache' not in scored[2]
    assert 'recurrent similar episodes' not in scored[2]


def test_sudden_onset_does_not_invent_dyspnea_or_palpitations():
    from nova_agent.matching import feature_present
    assert not feature_present('sudden onset dyspnea',['sudden onset abdominal pain'])
    assert not feature_present('sudden onset palpitations',['sudden onset abdominal pain'])


def test_named_elevated_lipase_is_interpreted_without_copying_test_name():
    s=PatientState(chief_complaint='epigastric pain radiating to back')
    s.record_test('lipase','high')
    assert 'elevated lipase' in _score_disease(disease_by_id('acute_pancreatitis'),s)[2]
    s.laboratory_tests['lipase']='not elevated'
    assert 'elevated lipase' not in _score_disease(disease_by_id('acute_pancreatitis'),s)[2]


def test_appendix_imaging_outweighs_nonspecific_white_cells():
    s=PatientState(chief_complaint='abdominal pain')
    s.record_test('cbc','elevated white blood cell count')
    s.record_test('ct_abdomen','dilated thickened appendix')
    assert DifferentialEngine().update(s)[0].diagnosis_id=='appendicitis'


def test_abdominal_complaint_always_has_abdominal_examination_candidate():
    from nova_agent.missing_info import MissingInformationAnalyzer
    s=PatientState(chief_complaint='severe stomach pain')
    candidates=MissingInformationAnalyzer().analyze(s,[],[])
    assert any(c.key=='abdominal_exam' for c in candidates)


def test_explicit_absent_breath_sounds_support_pathology_not_clear_lungs():
    s=PatientState(chief_complaint='shortness of breath')
    s.record_exam('lung_auscultation','absent breath sounds on the left side')
    assert 'absent breath sounds' in _score_disease(disease_by_id('tension_pneumothorax'),s)[2]
    s.physical_examinations['lung_auscultation']='clear breath sounds bilaterally'
    assert 'absent breath sounds' not in _score_disease(disease_by_id('tension_pneumothorax'),s)[2]


def test_wheezing_and_band_pressure_keep_their_clinical_concepts():
    from nova_agent.matching import feature_present
    assert feature_present('wheeze',['wheezing'])
    assert concept_present('bilateral band-like pressure',['tight band around my head'])
    assert concept_present('polydipsia',['unusually thirsty'])


def test_acronym_case_does_not_hide_asthma_history():
    assert concept_present('known asthma or COPD',['asthma since childhood'])
    assert concept_present('KNOWN ASTHMA OR COPD',['history of COPD'])
    assert not concept_present('known asthma or COPD',['no history of COPD'])


def test_migration_binds_temporal_locations_across_clauses():
    feature='periumbilical pain migrating to right lower quadrant'
    assert concept_present(feature,['started near the navel, now in the lower right abdomen'])
    assert not concept_present(feature,['no pain near the navel, no pain in the lower right'])
    assert not concept_present(feature,['navel and lower right abdomen examined'])


def test_resolved_nasal_symptom_is_history_not_current_uri_support():
    s=PatientState(chief_complaint='cough')
    s.record_ask('onset','onset?','after a cold; nasal congestion has resolved, cough persists')
    assert 'rhinorrhea' not in _score_disease(disease_by_id('viral_uri'),s)[2]
    assert 'recent viral illness' in _score_disease(disease_by_id('acute_bronchitis'),s)[2]


def test_sepsis_pattern_requires_specimen_pressure_and_mental_evidence_together():
    from nova_agent.evidence_interpreter import infection_with_circulatory_and_mental_change as pattern
    s=PatientState()
    s.record_exam('vital_signs','BP 84/52, HR 120, RR 25, Temp 39.0, SpO2 95%')
    s.record_exam('mental_status_exam','confused')
    s.record_test('blood_culture','pending')
    assert not pattern(s)
    s.record_test('urinalysis','positive nitrites')
    assert pattern(s)
    s.laboratory_tests['urinalysis']='not positive nitrites'
    assert not pattern(s)
    s.laboratory_tests['urinalysis']='positive nitrites'
    s.physical_examinations['mental_status_exam']='not confused'
    assert not pattern(s)


def test_tentative_culture_does_not_supply_combined_infection_evidence():
    from nova_agent.evidence_interpreter import infection_with_circulatory_and_mental_change as pattern
    s=PatientState()
    s.record_exam('vital_signs','BP 80/50, HR 120')
    s.record_exam('mental_status_exam','confused')
    s.record_test('blood_culture','possible positive, identification pending')
    assert not pattern(s)
