"""P1 safety regressions for mixed lay-language presentations.

These are deterministic software regressions, not clinical-validation cases.  They protect the
invariant that an actively flagged dangerous diagnosis remains actionable even when it is below
the displayed differential top-K.
"""

from nova_agent.action_selector import ActionSelector
from nova_agent.differential import DifferentialEngine
from nova_agent.missing_info import MissingInformationAnalyzer
from nova_agent.safety import SafetyLayer
from nova_agent.state import PatientState


def _mixed_state(text: str) -> PatientState:
    return PatientState(
        case_id="mixed-safety",
        chief_complaint=text,
        demographics={"age": 44, "sex": "female"},
    )


def test_lay_sudden_dyspnea_and_racing_heart_raise_pe_safety_finding():
    state = _mixed_state("sudden shortness of breath and racing heart; I also have panic attacks")
    differential = DifferentialEngine().update(state)
    findings = SafetyLayer().assess(state, differential)

    assert "pulmonary_embolism" in {finding.diagnosis_id for finding in findings}
    pe = next(finding for finding in findings if finding.diagnosis_id == "pulmonary_embolism")
    assert "sudden onset dyspnea" in pe.evidence
    assert "tachycardia" in pe.evidence


def test_composed_and_korean_sudden_dyspnea_phrases_raise_pe_safety_finding():
    for text in (
        "can't breathe, came on suddenly",
        "갑자기 숨이 차고 숨 쉴 때 가슴이 아파요",
    ):
        state = _mixed_state(text)
        differential = DifferentialEngine().update(state)
        findings = SafetyLayer().assess(state, differential)
        assert "pulmonary_embolism" in {finding.diagnosis_id for finding in findings}


def test_secondary_mixed_presentation_tag_keeps_pe_relevant():
    state = _mixed_state("low fever and a cough but also sudden sharp pain when I breathe in")
    differential = DifferentialEngine().update(state)
    findings = SafetyLayer().assess(state, differential)

    # Fever wins the single-tag router tie, but cough/dyspnea/pleuritic wording still makes PE a
    # relevant safety alternative.  This must not depend on copying a specific case vignette.
    assert "pulmonary_embolism" in {finding.diagnosis_id for finding in findings}


def test_negated_lay_safety_features_do_not_raise_pe():
    state = _mixed_state("no sudden shortness of breath and no racing heart")
    differential = DifferentialEngine().update(state)
    findings = SafetyLayer().assess(state, differential)

    assert "pulmonary_embolism" not in {finding.diagnosis_id for finding in findings}


def test_safety_only_pe_stays_actionable_and_vitals_are_first():
    state = _mixed_state("sudden shortness of breath and racing heart; I also have panic attacks")
    differential = DifferentialEngine().update(state)
    assert "pulmonary_embolism" not in {item.diagnosis_id for item in differential}

    findings = SafetyLayer().assess(state, differential)
    candidates = MissingInformationAnalyzer().analyze(state, differential, findings)
    candidate_keys = {(candidate.action_type, candidate.key) for candidate in candidates}
    assert ("EXAM", "vital_signs") in candidate_keys
    assert ("TEST", "d_dimer") in candidate_keys

    action, _candidates, _stop = ActionSelector().generate_and_select(state, differential, findings)
    assert (action.action_type, action.key) == ("EXAM", "vital_signs")
