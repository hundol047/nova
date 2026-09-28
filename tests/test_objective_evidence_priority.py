"""Round-C generalization hardening: objective_evidence.py's qualitative-only, single-abnormal-
direction labs (troponin/D-dimer/CRP/lipase/ketones/beta-hCG/urinalysis) now recognize a shared,
generic vocabulary for "abnormal"/"normal" (see `_direction_words`/`_GENERIC_NORMAL_WORDS`), not
just each lab's own one or two hand-picked phrases -- a report phrased "troponin above the
reference range" is exactly as real and exactly as decisive as one phrased "elevated troponin", and
failing to recognize it previously meant a genuinely abnormal, disease-confirming result silently
scored as `missing` evidence instead of `supporting` (differential.py's `_score_lab_aware_phrase`).

Independently written wording -- not copied from any blind_cases_v*.py vignette."""

from __future__ import annotations

from nova_agent.differential import DifferentialEngine
from nova_agent.objective_evidence import normalize_objective_evidence
from nova_agent.state import PatientState


def _state_with_lab(lab_key: str, lab_text: str):
    state = PatientState(case_id=f"objev_{lab_key}", chief_complaint="generic presentation")
    state.laboratory_tests[lab_key] = lab_text
    return state


def test_troponin_above_reference_range_phrasing_is_recognized_as_high():
    state = _state_with_lab("troponin", "troponin above the reference range")
    findings = normalize_objective_evidence(state)
    assert findings["lab.troponin"].interpretation == "high"


def test_troponin_flagged_high_phrasing_is_recognized():
    state = _state_with_lab("troponin", "troponin flagged high on the panel")
    findings = normalize_objective_evidence(state)
    assert findings["lab.troponin"].interpretation == "high"


def test_d_dimer_out_of_range_phrasing_is_recognized_as_high():
    state = _state_with_lab("d_dimer", "d-dimer out of range")
    findings = normalize_objective_evidence(state)
    assert findings["lab.d_dimer"].interpretation == "high"


def test_troponin_within_reference_range_phrasing_is_recognized_as_normal():
    state = _state_with_lab("troponin", "troponin within reference range")
    findings = normalize_objective_evidence(state)
    assert findings["lab.troponin"].interpretation == "normal"


def test_an_unrecognizable_troponin_report_still_stays_unknown_not_normal_or_high():
    """Negative control: broadening the vocabulary must never make an UNREADABLE result silently
    count as either direction."""
    state = _state_with_lab("troponin", "troponin pending, sample hemolyzed")
    findings = normalize_objective_evidence(state)
    assert findings["lab.troponin"].interpretation == "unknown"


def test_broadened_troponin_phrasing_reaches_differential_scoring_as_real_support():
    """End-to-end: the broadened vocabulary must actually reach differential.py's confirmatory-
    finding scoring (_score_lab_aware_phrase), not just objective_evidence.py's own normalizer."""
    state = PatientState(case_id="objev_e2e", chief_complaint="chest pressure that won't let up",
                          demographics={"age": 58, "sex": "male"})
    state.symptoms = ["substernal pressure"]
    state.laboratory_tests["troponin"] = "troponin above the reference range"
    items = DifferentialEngine().update(state)
    acs = next(i for i in items if i.diagnosis_id == "acute_coronary_syndrome")
    assert any("troponin" in s.lower() for s in acs.supporting_evidence), acs.supporting_evidence
    assert not any("troponin" in m.lower() for m in acs.missing_discriminative_evidence)
