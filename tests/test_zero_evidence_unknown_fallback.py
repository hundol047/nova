"""Zero-evidence / UNKNOWN_PRESENTATION fallback (Round D generalization-hardening mandate, defect
class 4): when candidate_generator.py's whole-catalog `if not pool:` branch fires, every resulting
DifferentialItem must be explicitly marked `fallback_candidate=True` with zero score/empty
supporting_evidence ("evidence_score=0, diagnostic_support=none" per spec), and BOTH DIAGNOSE paths
-- the deterministic StopPolicy and the LLM-selected-diagnosis safety_validator.py gate -- must
refuse to let it trigger a confident DIAGNOSE. See test_zero_evidence_file_order_independence.py
for the complementary proof that this holds regardless of disease KB file load order.
"""

from __future__ import annotations

from nova_agent.differential import DifferentialEngine
from nova_agent.llm_schema import AgentTurnOutput, SelectedActionOutput
from nova_agent.safety_validator import SafetyValidator
from nova_agent.state import PatientState
from nova_agent.stop_policy import StopPolicy


def _zero_evidence_state() -> PatientState:
    return PatientState(case_id="unknown-fallback-test", chief_complaint="zzyzx frobnicate quibble",
                         demographics={"age": 55, "sex": "male"})


def test_zero_evidence_presentation_marks_every_candidate_as_fallback():
    state = _zero_evidence_state()
    differential = DifferentialEngine().update(state)
    assert differential, "the whole-catalog fallback must still produce a non-empty differential"
    for item in differential:
        assert item.fallback_candidate is True
        assert item.score == 0.0
        assert item.score_ratio == 0.0
        assert item.supporting_evidence == []
        assert item.confidence_band == "LOW"
        assert set(item.candidate_sources) == {"zero_evidence_fallback"}


def test_zero_evidence_presentation_never_triggers_deterministic_should_diagnose():
    state = _zero_evidence_state()
    state.turn_count = 5  # comfortably above min_turns_before_diagnose, so this exercises the real
    # zero-evidence gate, not the separate "too early to diagnose" check.
    differential = DifferentialEngine().update(state)
    decision = StopPolicy().evaluate(state, differential, safety_findings=[], best_info_gain=0.0)
    assert decision.should_diagnose is False
    assert decision.forced is False
    assert "UNKNOWN_PRESENTATION" in decision.reason


def test_forced_diagnose_at_turn_limit_still_overrides_zero_evidence_gate():
    """The zero-evidence gate must never cause an infinite stall: the existing hard
    forced-diagnose-at-low-remaining-turns fallback (spec: the agent must always submit SOME final
    diagnosis before the turn budget runs out) still applies on top of it."""
    state = _zero_evidence_state()
    state.turn_count = 58  # max_turns(60) - 58 == 2 <= forced_diagnose_remaining_turns(3)
    differential = DifferentialEngine().update(state)
    decision = StopPolicy().evaluate(state, differential, safety_findings=[], best_info_gain=0.0)
    assert decision.should_diagnose is True
    assert decision.forced is True


def test_llm_selected_zero_evidence_diagnosis_is_blocked_by_safety_validator():
    """Even if the LLM's own free-form output independently picks a diagnosis that only exists in
    the differential via the zero-evidence fallback, safety_validator.py's DIAGNOSE gate must
    refuse it and fall back to the deterministic action -- this must hold unconditionally, never
    bypassable via the turn-count/evidence-count minimum-readiness fallback path."""
    from nova_agent.action_selector import AgentAction
    from nova_agent.candidate_generator import generate_candidates
    from nova_agent.clinical_presentation import build_clinical_presentation

    state = _zero_evidence_state()
    state.turn_count = 30  # comfortably past min_turns_before_diagnose
    differential = DifferentialEngine().update(state)
    assert differential and differential[0].fallback_candidate

    presentation = build_clinical_presentation(state)
    candidates = generate_candidates(presentation)
    assert candidates, "sanity: whole-catalog fallback pool must be non-empty"

    picked_id = differential[0].diagnosis_id
    picked_name = differential[0].diagnosis
    llm_output = AgentTurnOutput(
        differential=[], selected_action=SelectedActionOutput(type="DIAGNOSE", key=picked_id, content=picked_name),
    )
    deterministic_action = AgentAction(action_type="ASK", key="onset", content="onset?", rationale="test")
    stop_decision = StopPolicy().evaluate(state, differential, safety_findings=[], best_info_gain=0.0)

    result = SafetyValidator().validate_action(
        state, llm_output, candidate_pool={}, deterministic_action=deterministic_action,
        merged_differential=differential, stop_decision=stop_decision,
    )
    assert result.action.action_type != "DIAGNOSE"
    assert result.overridden is True
    assert "UNKNOWN_PRESENTATION" in (result.override_reason or "")
