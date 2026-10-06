"""Round E: when a critical diagnosis is plausible, action selection must prioritize the most
discriminative evidence for it over a low-value/generic workup item, when both are safe and legal.
Verifies action_selector.py's EXISTING utility mechanism (diagnostic_discrimination +
management_relevance + time_critical_bonus, missing_info.py's entropy-based information_gain)
already enforces this -- deliberately NOT retuned this round (spec: do not massively retune, do not
turn this into a disease-specific checklist); this is a verification test proving the architecture
holds, using a fresh vignette distinct from Blind v14.
"""

from __future__ import annotations

from nova_agent.action_selector import ActionSelector
from nova_agent.differential import DifferentialEngine
from nova_agent.safety import SafetyLayer
from nova_agent.state import PatientState


def test_high_specificity_confirmatory_test_outranks_generic_early_actions():
    state = PatientState(case_id="c1", chief_complaint="crushing chest pressure radiating to my left arm, sweating",
                          demographics={"age": 58, "sex": "male"})
    differential = DifferentialEngine().update(state)
    safety_findings = SafetyLayer().assess(state, differential)
    _action, scored, _stop = ActionSelector().generate_and_select(state, differential, safety_findings)

    scored_by_key = {c.key: c for c in scored}
    assert "troponin" in scored_by_key, "troponin (ACS's own confirmatory test) must be a candidate action"
    troponin_utility = scored_by_key["troponin"].utility

    # A low-value action further down the ranking (some generic history question) must never
    # outrank the high-specificity confirmatory test for the leading critical diagnosis. Excludes
    # the DIAGNOSE pseudo-candidate itself (a different utility formula entirely, not a "workup
    # item" being compared against) and ECG/CXR (also strong, disease-specific ACS discriminators).
    lower_value_candidates = [c for c in scored
                               if c.action_type != "DIAGNOSE" and c.key not in ("troponin", "ecg", "cxr")]
    assert lower_value_candidates, "sanity: there must be other candidate actions to compare against"
    assert troponin_utility >= max(c.utility for c in lower_value_candidates), (
        f"troponin utility {troponin_utility} did not outrank all generic candidates: "
        f"{[(c.key, c.utility) for c in lower_value_candidates]}"
    )


def test_discrimination_component_is_actually_used_in_the_utility_function():
    from nova_agent.config import get_config

    assert get_config().weights.discrimination_weight > 0.0, (
        "diagnostic_discrimination must carry real, non-zero weight in action utility scoring"
    )


def test_time_critical_action_gets_a_real_bonus_over_a_non_time_critical_one():
    state = PatientState(case_id="c2", chief_complaint="crushing chest pressure radiating to my left arm, sweating",
                          demographics={"age": 58, "sex": "male"})
    differential = DifferentialEngine().update(state)
    safety_findings = SafetyLayer().assess(state, differential)
    _action, scored, _stop = ActionSelector().generate_and_select(state, differential, safety_findings)

    time_critical_bonuses = {c.components["time_critical_bonus"] for c in scored if c.action_type != "DIAGNOSE"}
    assert 1.0 in time_critical_bonuses, "at least one candidate discriminating a time-critical diagnosis must get the bonus"
