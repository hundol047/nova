"""Round-C generalization hardening: gi_bleeding's knowledge-base risk_factors now include
"antiplatelet use" alongside the pre-existing "NSAID use"/"anticoagulant use" (a genuine KB
completeness fix, not a blind-case rule -- antiplatelets are a textbook GI bleeding risk factor).
Combined with the pre-existing FEATURE_ALIASES medication-class normalization, a patient on
warfarin + aspirin + ibuprofen now gets full, additive credit for ALL THREE independently
KB-recognized bleeding-risk factors, never just one -- medication context still only ever modifies
risk/prior relevance, never directly equals a diagnosis."""

from __future__ import annotations

from nova_agent.differential import DifferentialEngine
from nova_agent.state import PatientState


def test_combined_anticoagulant_antiplatelet_nsaid_all_score_as_gi_bleeding_risk():
    state = PatientState(case_id="polypharm_combo", chief_complaint="dark stool and feeling tired",
                          demographics={"age": 71, "sex": "male"})
    state.symptoms = ["melena"]
    state.medication_text = ["warfarin", "aspirin", "ibuprofen"]
    items = DifferentialEngine().update(state)
    gi_bleed = next(i for i in items if i.diagnosis_id == "gi_bleeding")
    assert "anticoagulant use" in gi_bleed.supporting_evidence
    assert "antiplatelet use" in gi_bleed.supporting_evidence
    assert "NSAID use" in gi_bleed.supporting_evidence


def test_a_single_bleeding_risk_medication_alone_still_scores_correctly():
    """Negative control / no-regression check: a lone anticoagulant, with no antiplatelet or NSAID
    on board, must still score its own single risk factor -- the combined case above is additive,
    not a replacement for the pre-existing single-medication path."""
    state = PatientState(case_id="polypharm_single", chief_complaint="dark stool",
                          demographics={"age": 68, "sex": "female"})
    state.symptoms = ["melena"]
    state.medication_text = ["warfarin"]
    items = DifferentialEngine().update(state)
    gi_bleed = next(i for i in items if i.diagnosis_id == "gi_bleeding")
    assert "anticoagulant use" in gi_bleed.supporting_evidence
    assert "antiplatelet use" not in gi_bleed.supporting_evidence
    assert "NSAID use" not in gi_bleed.supporting_evidence


def test_more_bleeding_risk_medications_score_at_least_as_high_as_fewer():
    def _score_for(meds):
        state = PatientState(case_id=f"polypharm_{len(meds)}", chief_complaint="dark stool",
                              demographics={"age": 70, "sex": "male"})
        state.symptoms = ["melena"]
        state.medication_text = list(meds)
        items = DifferentialEngine().update(state)
        return next(i for i in items if i.diagnosis_id == "gi_bleeding").score

    single = _score_for(["warfarin"])
    triple = _score_for(["warfarin", "aspirin", "ibuprofen"])
    assert triple > single, (
        f"three independently-recognized bleeding-risk medications ({triple}) should score higher "
        f"than one alone ({single})"
    )


def test_antiplatelet_alone_reaches_the_gi_bleeding_candidate_pool():
    """The new "antiplatelet use" KB risk_factor must itself pull gi_bleeding into the candidate
    pool via medication_match, exactly like the pre-existing anticoagulant/NSAID risk_factors do,
    even with no symptom-concept hit naming GI bleeding directly."""
    from nova_agent.candidate_generator import generate_candidates
    from nova_agent.clinical_presentation import build_clinical_presentation

    state = PatientState(case_id="polypharm_pool", chief_complaint="feeling generally tired lately",
                          medication_text=["aspirin", "clopidogrel"])
    presentation = build_clinical_presentation(state)
    candidates = generate_candidates(presentation)
    matched = next(c for c in candidates if c.id == "gi_bleeding")
    assert "medication_match" in matched.sources
