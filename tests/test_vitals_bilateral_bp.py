"""Bilateral (inter-arm) blood-pressure parsing (nova_agent/vitals_parser.py).

Generic vitals-parsing capability, not tied to any one diagnosis -- a real objective sign
(inter-arm systolic differential) that word-overlap matching alone can never see from a raw
"BP 180/60 right arm, 130/50 left arm" string, since the KB's confirmatory phrase ("unequal blood
pressure between arms") shares no useful words with a bare number pair. Exercised end to end
through DifferentialEngine so the fix is proven to actually reach the ranking, not just the parser.
"""

from __future__ import annotations

from nova_agent.differential import DifferentialEngine
from nova_agent.state import PatientState
from nova_agent.vitals_parser import describe_vital_sign_abnormalities, parse_vital_signs


def test_parses_two_bp_readings_into_an_arm_differential():
    vitals = parse_vital_signs("BP 180/60 right arm, 130/50 left arm, HR 110, RR 20, SpO2 97%")
    assert vitals is not None
    assert vitals.sbp == 180 and vitals.dbp == 60  # first reading still kept as the primary one
    assert vitals.sbp_arm_differential == 50


def test_small_bilateral_differential_is_not_flagged():
    vitals = parse_vital_signs("BP 120/80 right arm, 118/78 left arm, HR 76")
    assert vitals is not None
    assert vitals.sbp_arm_differential == 2
    assert describe_vital_sign_abnormalities(vitals) == []


def test_a_single_bp_trend_note_is_never_misread_as_two_limbs():
    """A same-arm reading mentioned twice (e.g. a before/after trend note) must not be
    misinterpreted as a bilateral measurement just because two BP-shaped number pairs appear."""
    vitals = parse_vital_signs("BP 150/95, improved from 120/80 on arrival, HR 88")
    assert vitals is not None
    assert vitals.sbp_arm_differential is None


def test_significant_arm_differential_produces_a_descriptive_finding():
    vitals = parse_vital_signs("BP 180/60 right arm, 130/50 left arm, HR 110")
    findings = describe_vital_sign_abnormalities(vitals)
    assert "Unequal blood pressure between arms" in findings


def test_arm_differential_finding_reaches_the_differential_ranking():
    """End-to-end: the vital_signs EXAM result flows through state.py -> vitals_parser.py ->
    all_findings_text() -> differential.py's word-overlap matcher, and actually changes
    supporting_evidence for whichever KB entries name this finding -- never asserts on the exact
    disease, since that would make this a disease-specific hardcode; only that the objective
    finding text is now visible to the ranking engine at all."""
    state = PatientState(case_id="bp-diff", chief_complaint="chest pain radiating to the back")
    state.record_exam("vital_signs", "BP 180/60 right arm, 130/50 left arm, HR 110, RR 20, SpO2 97%")

    items = DifferentialEngine().update(state)
    matched = [d for d in items if "unequal blood pressure between arms" in
               [s.lower() for s in d.supporting_evidence]]
    assert matched, (
        "expected at least one differential item to credit the inter-arm BP finding as supporting "
        f"evidence; got supporting_evidence={[d.supporting_evidence for d in items]}"
    )
