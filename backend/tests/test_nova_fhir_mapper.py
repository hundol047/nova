"""Unit tests for services/nova_fhir_mapper.py: Patient/ClinicalEncounter -> PatientState mapping.
No FastAPI app involved -- constructs Patient/ClinicalEncounter/VitalSigns objects directly and
inspects the resulting PatientState fields.
"""

from app.schemas import Allergy, ClinicalEncounter, DiagnosticReport, ImagingStudy, Lab, Medication, Patient, VitalSigns
from app.services.nova_fhir_mapper import apply_patient_context, demographics_for


def _patient(**overrides):
    base = dict(id='TEST-1', name='Test Patient', age=55, sex='female', diagnosis='', medications=[],
                conditions=[], allergies=[], labs=[])
    base.update(overrides)
    return Patient(**base)


def test_demographics_maps_age_and_sex():
    p = _patient(age=42, sex='male')
    d = demographics_for(p)
    assert d == {'age': 42, 'sex': 'male'}


def test_demographics_handles_unrecognized_sex_as_none():
    p = _patient(sex='unknown')
    assert demographics_for(p)['sex'] is None


def test_conditions_become_past_medical_history():
    from nova_agent.orchestrator import DoctorAgent
    p = _patient(conditions=['Atrial fibrillation', 'Hypertension'])
    state = DoctorAgent().new_case(case_id='c1', chief_complaint='palpitations', demographics=demographics_for(p))
    apply_patient_context(state, p, None)
    assert 'Atrial fibrillation' in state.past_medical_history
    assert 'Hypertension' in state.past_medical_history


def test_active_medications_populate_structured_and_text_fields():
    from nova_agent.orchestrator import DoctorAgent
    p = _patient(medications=[Medication(drug_id='warfarin', status='active'),
                               Medication(drug_id='aspirin', status='stopped')])
    state = DoctorAgent().new_case(case_id='c2', chief_complaint='bruising', demographics=demographics_for(p))
    apply_patient_context(state, p, None)
    names = [m.name for m in state.medications]
    assert 'warfarin' in names
    assert 'aspirin' not in names  # stopped medications are not surfaced as active context
    assert any('warfarin' in t for t in state.medication_text)


def test_allergies_map_directly_with_matching_field_names():
    from nova_agent.orchestrator import DoctorAgent
    p = _patient(allergies=[Allergy(substance='penicillin', category='medication', severity='SEVERE', reaction='anaphylaxis')])
    state = DoctorAgent().new_case(case_id='c3', chief_complaint='rash', demographics=demographics_for(p))
    apply_patient_context(state, p, None)
    assert state.allergies[0].substance == 'penicillin'
    assert state.allergies[0].severity == 'SEVERE'
    assert any('penicillin' in t for t in state.allergy_text)


def test_labs_populate_laboratory_tests_dict_with_reference_range():
    from nova_agent.orchestrator import DoctorAgent
    p = _patient(labs=[Lab(name='potassium', value=6.8, unit='mmol/L', date='2026-01-01', low=3.5, high=5.0)])
    state = DoctorAgent().new_case(case_id='c4', chief_complaint='weakness', demographics=demographics_for(p))
    apply_patient_context(state, p, None)
    assert 'potassium' in state.laboratory_tests
    assert '6.8' in state.laboratory_tests['potassium']
    assert 'ref' in state.laboratory_tests['potassium']


def test_latest_encounter_vitals_populate_structured_vitals_and_findings():
    from nova_agent.orchestrator import DoctorAgent
    vitals = VitalSigns(id='V1', encounter_id='E1', sbp=88, dbp=54, heart_rate=128, respiratory_rate=26,
                         temperature_c=39.2, spo2=89, measured_at='2026-01-01T00:00:00Z')
    enc = ClinicalEncounter(id='E1', patient_id='TEST-1', encounter_type='emergency', started_at='2026-01-01T00:00:00Z',
                             chief_complaint='fever and confusion', vital_signs=[vitals])
    p = _patient()
    state = DoctorAgent().new_case(case_id='c5', chief_complaint='fever', demographics=demographics_for(p))
    apply_patient_context(state, p, enc)
    assert state.vital_signs[0].sbp == 88
    assert state.vital_signs[0].spo2 == 89
    assert 'vital_signs' in state.physical_examinations
    assert state.vital_sign_findings, 'severely deranged vitals should produce at least one abnormality finding'


def test_no_encounter_means_no_vitals_populated():
    from nova_agent.orchestrator import DoctorAgent
    p = _patient()
    state = DoctorAgent().new_case(case_id='c6', chief_complaint='cough', demographics=demographics_for(p))
    apply_patient_context(state, p, None)
    assert state.vital_signs == []


def test_lab_with_recognized_loinc_gets_additional_canonical_key():
    from nova_agent.orchestrator import DoctorAgent
    p = _patient(labs=[Lab(name='Potassium', value=6.9, unit='mEq/L', date='2026-01-01', loinc='2823-3')])
    state = DoctorAgent().new_case(case_id='c7', chief_complaint='weakness', demographics=demographics_for(p))
    apply_patient_context(state, p, None)
    # Raw display-name key is always still populated (unchanged existing behavior).
    assert 'Potassium' in state.laboratory_tests
    # ADDITIONALLY keyed under nova_agent's own canonical raw key.
    assert 'potassium' in state.laboratory_tests
    assert '6.9' in state.laboratory_tests['potassium']


def test_unmapped_lab_is_reported_not_discarded():
    from nova_agent.orchestrator import DoctorAgent
    p = _patient(labs=[Lab(name='Erythrocyte Sedimentation Rate', value=40, unit='mm/hr', date='2026-01-01',
                            loinc='4537-7')])
    state = DoctorAgent().new_case(case_id='c8', chief_complaint='fatigue', demographics=demographics_for(p))
    unmapped = apply_patient_context(state, p, None)
    # Raw display-name key is still populated -- the fact is never lost even though unmapped.
    assert 'Erythrocyte Sedimentation Rate' in state.laboratory_tests
    assert unmapped == [{'raw_code': '4537-7', 'raw_display': 'Erythrocyte Sedimentation Rate'}]


def test_diagnostic_report_populates_state_imaging_with_status_and_date():
    from nova_agent.orchestrator import DoctorAgent
    p = _patient(diagnostic_reports=[
        DiagnosticReport(id='DR1', date='2026-01-02', name='CT Head', status='final',
                          conclusion='No acute intracranial hemorrhage'),
    ])
    state = DoctorAgent().new_case(case_id='c9', chief_complaint='headache', demographics=demographics_for(p))
    apply_patient_context(state, p, None)
    matches = [v for v in state.imaging.values() if 'CT Head' in v]
    assert len(matches) == 1
    assert 'No acute intracranial hemorrhage' in matches[0]
    assert 'final' in matches[0]
    assert '2026-01-02' in matches[0]


def test_imaging_study_populates_state_imaging_with_modality_and_description():
    from nova_agent.orchestrator import DoctorAgent
    p = _patient(imaging_studies=[
        ImagingStudy(id='IS1', date='2026-01-03', modality='CXR', description='Widened mediastinum'),
    ])
    state = DoctorAgent().new_case(case_id='c10', chief_complaint='chest pain', demographics=demographics_for(p))
    apply_patient_context(state, p, None)
    matches = [v for v in state.imaging.values() if 'Widened mediastinum' in v]
    assert len(matches) == 1
    assert 'CXR' in matches[0]


def test_imaging_study_feeds_candidate_pool_via_imaging_match():
    """End-to-end: a diagnosis-confirming imaging finding recorded at case-creation time (before any
    ASK/EXAM/TEST) must be visible to nova_agent's candidate_generator.py imaging_match source, not
    just to scoring -- proves DiagnosticReport/ImagingStudy are actually wired into reasoning, not
    just stored inertly on PatientState."""
    from nova_agent.candidate_generator import generate_candidates
    from nova_agent.clinical_presentation import build_clinical_presentation
    from nova_agent.orchestrator import DoctorAgent

    p = _patient(diagnostic_reports=[
        DiagnosticReport(id='DR2', date='2026-01-02', name='CT Chest', status='final',
                          conclusion='widened mediastinum'),
    ])
    state = DoctorAgent().new_case(case_id='c11', chief_complaint='tearing back pain',
                                    demographics=demographics_for(p))
    apply_patient_context(state, p, None)
    presentation = build_clinical_presentation(state)
    candidates = generate_candidates(presentation, imaging_text=list(state.imaging.values()))
    matched = [c for c in candidates if c.id == 'aortic_dissection' and 'imaging_match' in c.sources]
    assert matched, 'aortic_dissection should be pulled into the pool via imaging_match'
