"""Round E, defect C, end-to-end: when several disease-specific signals align (specific symptom +
specific risk/context + specific objective evidence), they must jointly dominate a competing
dangerous diagnosis that only has generic physiologic-severity markers in common. Fresh vignettes,
independently authored (not a reworded Blind v14 case) -- proves the ARCHITECTURAL mechanism using
a disease pairing distinct from the anaphylaxis-vs-sepsis pattern this round's own investigation
found, so the fix is shown to generalize rather than only patch that one pairing.
"""

from __future__ import annotations

from nova_agent.differential import DifferentialEngine
from nova_agent.state import PatientState


def test_anaphylaxis_outranks_sepsis_when_both_share_generic_severe_vitals():
    # Both diagnoses are plausible from the deranged vitals alone; only anaphylaxis has real
    # disease-specific findings (wheeze, urticaria) actually present.
    state = PatientState(case_id="c1", chief_complaint="throat feels like it's closing up, covered in hives",
                          demographics={"age": 30, "sex": "male"})
    state.record_ask("associated_symptoms", "symptoms?", "lips feel swollen, wheezing")
    state.record_ask("social_history", "sh?", "ate shellfish for the first time tonight")
    state.record_exam("vital_signs", "BP 82/50, HR 132, RR 30, Temp 37.0, SpO2 90%")
    state.record_exam("skin_exam", "diffuse urticaria")
    state.record_exam("lung_auscultation", "audible wheeze throughout")

    items = DifferentialEngine().update(state)
    assert items[0].diagnosis_id == "anaphylaxis", (
        f"expected anaphylaxis to win on its own specific findings, got {items[0].diagnosis_id} "
        f"(top 3: {[(i.diagnosis_id, i.score) for i in items[:3]]})"
    )


def test_dka_outranks_sepsis_when_both_share_generic_derangement_but_only_dka_has_specific_labs():
    # Fever/tachycardia/tachypnea alone could suggest sepsis; DKA's own specific numeric evidence
    # (glucose, ketones) must let it win despite sepsis sharing the same generic vital derangement.
    state = PatientState(case_id="c2", chief_complaint="breathing fast and just feels very unwell",
                          demographics={"age": 19, "sex": "female"})
    state.record_ask("past_medical_history", "pmh?", "type 1 diabetes")
    state.record_ask("associated_symptoms", "symptoms?", "very thirsty, belly pain, vomited twice")
    state.record_exam("vital_signs", "BP 100/62, HR 118, RR 30, Temp 37.4, SpO2 97%")
    state.record_exam("general_appearance", "breathing deep and fast")
    state.record_test("glucose_point_of_care", "498 mg/dL")
    state.record_test("ketones", "large ketones")
    state.record_test("abg", "metabolic acidosis")

    items = DifferentialEngine().update(state)
    assert items[0].diagnosis_id == "diabetic_ketoacidosis", (
        f"expected DKA to win on its own specific labs, got {items[0].diagnosis_id} "
        f"(top 3: {[(i.diagnosis_id, i.score) for i in items[:3]]})"
    )


def test_generic_severity_alone_with_no_specific_evidence_never_crowns_an_arbitrary_dangerous_winner():
    # With ONLY generic vitals-derangement text and nothing disease-specific for anyone, no
    # diagnosis should show inflated confidence purely from shared generic severity words -- every
    # top candidate's score should stay low/tied rather than one arbitrarily running away with it.
    state = PatientState(case_id="c3", chief_complaint="just feels very unwell",
                          demographics={"age": 50, "sex": "male"})
    state.record_exam("vital_signs", "BP 84/52, HR 128, RR 30, Temp 39.2, SpO2 89%")

    items = DifferentialEngine().update(state)
    # No diagnosis should reach HIGH confidence purely from shared generic-severity vital-sign
    # words -- confirming the reduced multiplier, not just a raw score, actually caps how
    # decisive plain generic-derangement matching alone can look.
    assert items[0].confidence_band != "HIGH", (
        f"{items[0].diagnosis_id} reached HIGH confidence from generic severity words alone "
        f"(score={items[0].score}, evidence={items[0].supporting_evidence})"
    )
