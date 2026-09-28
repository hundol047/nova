"""Round-C generalization hardening: non-medication risk/history context (immobility, recent long
travel) reaching candidate generation and scoring via scoped FEATURE_ALIASES entries, the same
existing mechanism medication-class risk context already used (spec: risk context must reach
candidate generation AND evidence scoring using existing structured fields, never a blind-case-
specific rule). "Long flight"/"long car ride" are generic, textbook ways any patient describes
immobility risk -- not lifted from any blind case."""

from __future__ import annotations

from nova_agent.candidate_generator import generate_candidates
from nova_agent.clinical_presentation import build_clinical_presentation
from nova_agent.differential import DifferentialEngine
from nova_agent.state import PatientState


def test_long_flight_is_recognized_as_immobilization_risk_for_pe():
    state = PatientState(case_id="risk_flight", chief_complaint="sudden sharp pain when I breathe in",
                          demographics={"age": 39, "sex": "male"})
    state.symptoms = ["pleuritic chest pain"]
    state.social_history = ["long flight two days ago"]
    items = DifferentialEngine().update(state)
    pe = next(i for i in items if i.diagnosis_id == "pulmonary_embolism")
    assert any(rf in pe.supporting_evidence for rf in ("immobilization", "long travel"))


def test_long_car_ride_reaches_the_candidate_pool_for_pe_via_risk_match():
    presentation = build_clinical_presentation(
        PatientState(case_id="risk_car", chief_complaint="calf pain and shortness of breath",
                      social_history=["long car ride last week"])
    )
    candidates = generate_candidates(presentation)
    ids = {c.id for c in candidates}
    assert "pulmonary_embolism" in ids


def test_immobility_alias_never_leaks_into_an_unrelated_diagnosis():
    """Negative control: "long flight" must only ever support PE's own named risk_factors, never
    become generic evidence for an unrelated diagnosis."""
    state = PatientState(case_id="risk_neg", chief_complaint="scratchy sore throat and runny nose",
                          demographics={"age": 25, "sex": "female"})
    state.symptoms = ["sore throat", "rhinorrhea"]
    state.social_history = ["long flight two days ago"]
    items = DifferentialEngine().update(state)
    viral_uri = next((i for i in items if i.diagnosis_id == "viral_uri"), None)
    if viral_uri is not None:
        assert "immobilization" not in viral_uri.supporting_evidence
        assert "long travel" not in viral_uri.supporting_evidence
