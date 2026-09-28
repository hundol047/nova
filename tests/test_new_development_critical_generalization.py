"""Round-C independent DEVELOPMENT cases (not Blind v13 -- distinct wording, demographics,
chronology, and values from every blind_cases_v*.py vignette; see scripts/check_eval_leakage.py).
Integration-level proof that this round's generic mechanisms (broadened objective-evidence
vocabulary, scoped lay-language/risk aliases, KB completeness fixes, the typical_feature
contribution cap, and the final-differential safety reinjection) combine correctly end-to-end
through DifferentialEngine, covering the category spread the round's generalization audit
targeted: critical-cardiovascular phrasing variation, thromboembolic phrasing variation,
bleeding-risk context variation, neurologic-deficit variation, objective-evidence dominance,
lay-language symptom mapping, polypharmacy, and a benign-mimic negative control."""

from __future__ import annotations

from nova_agent.differential import DifferentialEngine
from nova_agent.state import PatientState


def _run(case_id, chief_complaint, *, age, sex, symptoms=(), pmh=(), meds=(), social=(),
         vitals=None, exam=None, labs=None, imaging=None):
    state = PatientState(case_id=case_id, chief_complaint=chief_complaint,
                          demographics={"age": age, "sex": sex})
    state.symptoms = list(symptoms)
    state.past_medical_history = list(pmh)
    state.medication_text = list(meds)
    state.social_history = list(social)
    if vitals:
        state.record_exam("vital_signs", vitals)
    for exam_id, result in (exam or {}).items():
        state.physical_examinations[exam_id] = result
    for lab_id, result in (labs or {}).items():
        state.laboratory_tests[lab_id] = result
    for img_id, result in (imaging or {}).items():
        state.imaging[img_id] = result
    return DifferentialEngine().update(state)


def test_critical_cardiovascular_lay_phrasing_with_broadened_lab_vocabulary():
    """An elephant-on-my-chest lay phrasing, elevated cholesterol (not "hyperlipidemia"), and lab
    text phrased in the newly-recognized generic vocabulary rather than the KB's own exact words."""
    items = _run(
        "dev_acs", "it feels like an elephant is sitting on my chest and I can't shake it off",
        age=64, sex="female", symptoms=["exertional chest pain", "diaphoresis"],
        pmh=["elevated cholesterol", "type 2 diabetes"],
        labs={"ecg": "ST elevation across the anterior leads", "troponin": "cardiac troponin flagged high"},
    )
    assert items[0].diagnosis_id == "acute_coronary_syndrome"


def test_thromboembolic_lay_phrasing_with_immobility_risk_and_broadened_d_dimer_vocabulary():
    items = _run(
        "dev_pe", "out of nowhere I can't get a full breath in and it stabs when I try",
        age=33, sex="female", symptoms=["sudden onset dyspnea", "pleuritic chest pain", "tachycardia"],
        social=["12-hour bus trip two days ago"], meds=["oral contraceptive"],
        vitals="BP 108/68, HR 122, RR 28, Temp 37.0, SpO2 89%",
        labs={"d_dimer": "d-dimer above the upper limit of normal"},
    )
    assert items[0].diagnosis_id == "pulmonary_embolism"


def test_bleeding_risk_polypharmacy_with_numeric_hemoglobin_and_lay_stool_description():
    items = _run(
        "dev_gib", "my stools have looked really dark and tarry the past couple days and I feel wiped out",
        age=77, sex="male", symptoms=["melena", "lightheadedness"],
        meds=["clopidogrel", "naproxen"],
        vitals="BP 98/60, HR 112, RR 18, Temp 36.9, SpO2 97%",
        labs={"hemoglobin": "hemoglobin 6.9 g/dL"},
    )
    assert items[0].diagnosis_id == "gi_bleeding"


def test_neurologic_deficit_variation_pure_aphasia_without_dysarthria():
    """Pure word-finding difficulty (no dysarthria at all) plus a lay "irregular heart rhythm"
    phrasing for a known arrhythmia history -- previously uncredited by the KB's typical_features
    (only "slurred speech" existed) and by FEATURE_ALIASES (no atrial fibrillation alias)."""
    items = _run(
        "dev_stroke", "he suddenly can't get the words out right and his face looks different on one side",
        age=73, sex="male", symptoms=["aphasia", "facial droop"],
        pmh=["irregular heart rhythm"],
        vitals="BP 164/92, HR 96 irregular, RR 18, Temp 36.8, SpO2 97%",
        imaging={"ct_head": "no acute hemorrhage"},
    )
    assert items[0].diagnosis_id == "ischemic_stroke"


def test_objective_evidence_dominance_over_vague_nonspecific_symptoms():
    """A vague, low-information chief complaint plus one decisive, unambiguous lab abnormality
    must not be drowned out by the low specificity of the presenting words."""
    items = _run(
        "dev_potassium", "I just don't feel like myself today, hard to put my finger on it",
        age=59, sex="male", pmh=["chronic kidney disease"], meds=["lisinopril", "spironolactone"],
        labs={"potassium": "potassium 7.3 mEq/L", "ecg": "peaked T waves"},
    )
    assert items[0].diagnosis_id == "severe_electrolyte_disorder"


def test_benign_mimic_negative_control_reassuring_evidence_must_not_be_overridden():
    """A racing-heart presentation with clearly reassuring findings (sinus tachycardia, no
    ischemic changes, situational trigger) must still resolve to the benign diagnosis, not be
    dragged toward a dangerous mimic purely by the alarming chief complaint wording."""
    items = _run(
        "dev_panic", "out of nowhere I got hit with intense fear like something terrible was about to happen",
        age=24, sex="female",
        symptoms=["sudden onset intense anxiety or fear", "hyperventilation",
                  "tingling around the mouth or fingers", "chest tightness", "palpitations",
                  "fear of dying or losing control"],
        social=["final exam this morning", "three energy drinks today"],
        vitals="BP 124/80, HR 108, RR 22, Temp 36.8, SpO2 99%",
        labs={"ecg": "sinus tachycardia, no ischemic changes"},
    )
    assert items[0].diagnosis_id == "panic_attack"
