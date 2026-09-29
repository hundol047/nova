"""Reproductive-age emergency safety (Round E, defect B): ectopic pregnancy specifically, as the
concrete implementation of nova_agent/contextual_safety.py's general contextual-activation
architecture. Never assumes every reproductive-age patient has an ectopic pregnancy -- activation
requires a plausible presenting concept too, and (per existing resolution.py semantics, unchanged
this round) activation is never permanent: real contradictory evidence or a completed workup lets
it leave the active differential exactly like any other dangerous diagnosis. Fresh vignette wording,
none copied from Blind v14.
"""

from __future__ import annotations

from nova_agent.clinical_presentation import extract_presentation
from nova_agent.contextual_safety import contextually_activated_diagnosis_ids
from nova_agent.differential import DifferentialItem
from nova_agent.resolution import is_resolved
from nova_agent.state import PatientState


def test_ectopic_pregnancy_activates_for_abdominal_pain_in_reproductive_age_female():
    presentation = extract_presentation(
        "sharp lower belly pain, comes and goes since yesterday",
        demographics={"age": 24, "sex": "female"},
    )
    assert "ectopic_pregnancy" in contextually_activated_diagnosis_ids(presentation)


def test_ectopic_pregnancy_does_not_activate_without_a_plausible_concept():
    # Reproductive-age + female alone is NOT sufficient -- a wholly unrelated complaint (sore
    # throat) must not activate ectopic-pregnancy safety logic.
    presentation = extract_presentation(
        "sore throat and a cough for two days",
        demographics={"age": 24, "sex": "female"},
    )
    assert "ectopic_pregnancy" not in contextually_activated_diagnosis_ids(presentation)


def test_ectopic_pregnancy_resolves_once_a_negative_workup_is_complete():
    # Generic resolution.py semantics, unchanged this round: explicit contradictory evidence (e.g.
    # a negative pelvic ultrasound / beta-hCG workup) lets a contextually-activated dangerous
    # diagnosis leave the active differential exactly like any symptom-matched one would.
    assert is_resolved("ectopic_pregnancy", ["negative beta-hCG, no adnexal mass on ultrasound"],
                        state=PatientState(case_id="c", chief_complaint="lower abdominal pain",
                                            demographics={"age": 24, "sex": "female"})) is True


def test_ectopic_pregnancy_stays_unresolved_with_no_workup_and_no_contradictory_evidence():
    assert is_resolved("ectopic_pregnancy", [],
                        state=PatientState(case_id="c", chief_complaint="lower abdominal pain",
                                            demographics={"age": 24, "sex": "female"})) is False


def test_contextually_activated_ectopic_pregnancy_can_still_be_the_stop_policy_blocker():
    # An activated-but-unresolved dangerous diagnosis with real supporting evidence behaves exactly
    # like any other unresolved dangerous alternative in stop_policy.py's readiness gate -- proving
    # the contextual-activation path integrates with the SAME safety machinery, not a special case.
    from nova_agent.stop_policy import StopPolicy

    benign_top = DifferentialItem(
        diagnosis="Gastroenteritis", diagnosis_id="gastroenteritis", rank=1, score=3.0, score_ratio=0.8,
        supporting_evidence=["crampy abdominal pain", "nausea"], contradictory_evidence=[],
        missing_discriminative_evidence=[], urgency="LOW", dangerous_if_missed=False,
        confidence_band="HIGH", candidate_sources=["symptom_match"],
    )
    activated_ectopic = DifferentialItem(
        diagnosis="Ectopic Pregnancy", diagnosis_id="ectopic_pregnancy", rank=2, score=2.0, score_ratio=0.5,
        supporting_evidence=["lower abdominal pain", "unilateral pelvic pain"], contradictory_evidence=[],
        missing_discriminative_evidence=[], urgency="CRITICAL", dangerous_if_missed=True,
        confidence_band="MEDIUM", candidate_sources=["symptom_match", "contextual_safety"],
    )
    state = PatientState(case_id="c", chief_complaint="crampy abdominal pain",
                          demographics={"age": 24, "sex": "female"})
    state.turn_count = 10
    decision = StopPolicy().evaluate(state, [benign_top, activated_ectopic], safety_findings=[], best_info_gain=0.0)
    assert decision.should_diagnose is False
