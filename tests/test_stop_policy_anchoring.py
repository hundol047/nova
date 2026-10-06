"""StopPolicy: a genuinely unresolved dangerous alternative must ALWAYS block DIAGNOSE (spec: DIAGNOSE
allowed only when strong evidence + top margin + critical alternatives resolved + low remaining
info gain hold SIMULTANEOUSLY -- never any one of them substituting for another). This is the
generic form of the "prior benign-diagnosis anchoring must never suppress a genuinely unresolved
red flag" requirement: these cases are hand-built generic scenarios (a benign top pick + an
actively-flagged, unresolved dangerous alternative), never phrased from or copied out of any
frozen blind evaluation set.
"""

from __future__ import annotations

from nova_agent.differential import DifferentialItem
from nova_agent.safety import SafetyFinding
from nova_agent.state import PatientState
from nova_agent.stop_policy import StopPolicy


def _benign_top(score_ratio: float = 0.9) -> DifferentialItem:
    return DifferentialItem(
        diagnosis="Migraine", diagnosis_id="migraine", rank=1, score=5.0, score_ratio=score_ratio,
        supporting_evidence=["unilateral pulsating headache", "photophobia", "known migraine history"],
        contradictory_evidence=[], missing_discriminative_evidence=[], urgency="LOW",
        dangerous_if_missed=False, confidence_band="HIGH", candidate_sources=["symptom_match", "history_match"],
    )


def test_unresolved_active_safety_flag_blocks_diagnose_even_with_zero_remaining_info_gain():
    """A dangerous alternative (here: ischemic stroke) that SafetyLayer has actively flagged --
    real matched red-flag evidence, e.g. a NEW focal deficit -- and that has neither contradictory
    evidence nor a completed minimum workup must keep blocking DIAGNOSE even once the agent has
    run out of further USEFUL questions to ask (best_info_gain <= 0.0). Before this module's fix,
    `no_more_value` alone (best_info_gain <= 0.0) could bypass the dangerous-alternative check
    entirely -- letting a well-matched benign top pick (e.g. a patient's own known migraine
    history) get diagnosed while a newly-flagged, still-uninvestigated stroke red flag was simply
    walked past. The forced-remaining-turns fallback (a separate, always-active check earlier in
    evaluate()) still guarantees the agent never stalls forever -- this only stops it from closing
    EARLY while a real danger sits unresolved."""
    state = PatientState(case_id="c", chief_complaint="bad headache",
                          demographics={"age": 45, "sex": "female"})
    state.turn_count = 10  # comfortably above min_turns_before_diagnose and forced_diagnose_remaining_turns,
    # so this exercises the real readiness-vs-danger logic, not the separate turn-limit fallbacks.
    differential = [_benign_top()]
    safety_findings = [
        SafetyFinding(diagnosis_id="ischemic_stroke", condition="Ischemic Stroke",
                       reason="Symptom findings overlap with red-flag features for Ischemic Stroke",
                       evidence=["new focal weakness"], source="symptom_keyword", urgency="CRITICAL"),
    ]
    decision = StopPolicy().evaluate(state, differential, safety_findings, best_info_gain=0.0)
    assert decision.should_diagnose is False
    assert decision.forced is False


def test_diagnose_allowed_once_the_active_safety_flag_is_actually_resolved():
    """Negative control: once the same dangerous alternative IS resolved (here: explicit
    contradictory evidence from a completed workup), the benign top pick's own strong evidence and
    zero remaining info gain are sufficient and DIAGNOSE is allowed normally -- this fix must not
    make the agent stall forever once a red flag has genuinely been ruled out."""
    state = PatientState(case_id="c", chief_complaint="bad headache",
                          demographics={"age": 45, "sex": "female"})
    top = _benign_top()
    resolved_alternative = DifferentialItem(
        diagnosis="Ischemic Stroke", diagnosis_id="ischemic_stroke", rank=2, score=0.5, score_ratio=0.1,
        supporting_evidence=[], contradictory_evidence=["CT head: no acute infarct"],
        missing_discriminative_evidence=[], urgency="CRITICAL", dangerous_if_missed=True,
        confidence_band="LOW", candidate_sources=["safety_candidate"],
    )
    differential = [top, resolved_alternative]
    safety_findings = [
        SafetyFinding(diagnosis_id="ischemic_stroke", condition="Ischemic Stroke",
                       reason="Symptom findings overlap with red-flag features for Ischemic Stroke",
                       evidence=["new focal weakness"], source="symptom_keyword", urgency="CRITICAL"),
    ]
    state.turn_count = 10
    decision = StopPolicy().evaluate(state, differential, safety_findings, best_info_gain=0.0)
    assert decision.should_diagnose is True
