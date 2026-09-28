"""Round-C generalization hardening: scoped lay-language aliases and KB completeness additions in
differential.py's FEATURE_ALIASES / knowledge/diseases/*.json (never a global finding-text
substitution -- see differential.py's own module docstring for why that pattern was reverted
before). Each alias here is keyed to the ONE named risk_factor/typical_feature it stands for, so it
can only ever help that one phrase, never widen matching for an unrelated diagnosis.

Fresh, independently-written vignettes -- none of this wording is copied from any blind_cases_v*.py
file (see evaluation/blind_cases_v12.py's own authoring-discipline docstring for what that
constraint means and scripts/check_eval_leakage.py for the automated check)."""

from __future__ import annotations

from nova_agent.differential import DifferentialEngine
from nova_agent.state import PatientState


def _state(case_id, chief_complaint, symptoms=(), pmh=(), meds=(), vitals=None, exam=None):
    state = PatientState(case_id=case_id, chief_complaint=chief_complaint,
                          demographics={"age": 60, "sex": "male"})
    state.symptoms = list(symptoms)
    state.past_medical_history = list(pmh)
    state.medication_text = list(meds)
    if vitals:
        state.record_exam("vital_signs", vitals)
    if exam:
        for exam_id, result in exam.items():
            state.physical_examinations[exam_id] = result
    return state


def test_high_cholesterol_is_recognized_as_hyperlipidemia_risk_factor():
    """"High cholesterol" is the near-universal way a patient reports hyperlipidemia; the KB's own
    risk_factor phrase is the clinical term "hyperlipidemia", which most patients never say."""
    state = _state("lay_chol", "occasional chest tightness when climbing stairs",
                    symptoms=["exertional chest pain"], pmh=["high cholesterol"])
    items = DifferentialEngine().update(state)
    acs = next(i for i in items if i.diagnosis_id == "acute_coronary_syndrome")
    assert "hyperlipidemia" in acs.supporting_evidence


def test_high_blood_pressure_is_recognized_as_hypertension_risk_factor():
    state = _state("lay_bp", "sudden weakness on one side of my body",
                    symptoms=["sudden onset focal weakness"], pmh=["high blood pressure"])
    items = DifferentialEngine().update(state)
    stroke = next(i for i in items if i.diagnosis_id == "ischemic_stroke")
    assert "hypertension" in stroke.supporting_evidence


def test_aphasia_is_a_typical_feature_of_stroke_distinct_from_slurred_speech():
    """Aphasia (word-finding/expressive language difficulty) is a distinct classic stroke sign
    from dysarthria ("slurred speech") -- the KB previously named only the latter, so a case
    presenting with pure aphasia and no dysarthria at all would have scored no credit for either."""
    state = _state("lay_aphasia", "trouble finding the right words since this afternoon",
                    symptoms=["aphasia"])
    items = DifferentialEngine().update(state)
    stroke = next(i for i in items if i.diagnosis_id == "ischemic_stroke")
    assert "aphasia" in stroke.supporting_evidence


def test_atrial_fibrillation_abbreviation_is_recognized():
    state = _state("lay_afib", "sudden onset slurred speech and right-sided weakness",
                    symptoms=["sudden onset focal weakness", "slurred speech"], pmh=["afib"])
    items = DifferentialEngine().update(state)
    stroke = next(i for i in items if i.diagnosis_id == "ischemic_stroke")
    assert "atrial fibrillation" in stroke.supporting_evidence


def test_alias_never_leaks_into_an_unrelated_diagnosis():
    """Negative control: "high cholesterol" must only ever support hyperlipidemia -- it must not
    become generic evidence for an unrelated diagnosis that has no such risk_factor at all."""
    state = _state("lay_neg", "burning when I pass water since this morning",
                    symptoms=["dysuria", "urinary frequency"], pmh=["high cholesterol"])
    items = DifferentialEngine().update(state)
    cystitis = next(i for i in items if i.diagnosis_id == "uncomplicated_cystitis")
    assert "hyperlipidemia" not in cystitis.supporting_evidence
    assert "high cholesterol" not in cystitis.supporting_evidence
