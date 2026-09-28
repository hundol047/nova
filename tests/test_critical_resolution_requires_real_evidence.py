"""Round-C generalization hardening: two related guarantees, both generic (never keyed to a
specific diagnosis id or blind case):

  1. resolution.py's `is_resolved()` already only resolves a dangerous diagnosis via explicit
     contradictory evidence or (for a known diagnosis) its own completed minimum_workup -- "lack of
     evidence" never masquerades as "evidence against" (pre-existing, re-verified here as a
     regression guard since action_selector.py's utility math now depends on the same distinction).

  2. action_selector.py's new `_decisively_supported_dangerous_ids` only stops treating further
     discrimination as automatically management-relevant for a dangerous diagnosis that is BOTH
     the clear top pick AND has no competing unresolved dangerous alternative -- an item still in
     that diagnosis's own minimum_workup keeps full priority even then, and a genuinely still-
     uncertain dangerous diagnosis (LOW/MEDIUM confidence, or a real competing alternative present)
     is completely unaffected."""

from __future__ import annotations

from nova_agent.action_selector import ActionSelector
from nova_agent.differential import DifferentialItem
from nova_agent.missing_info import CandidateInfo
from nova_agent.resolution import is_resolved
from nova_agent.state import PatientState


def _item(diagnosis_id, *, rank=1, score_ratio=0.9, dangerous=True, band="HIGH",
          contradictory=None, name=None):
    return DifferentialItem(
        diagnosis=name or diagnosis_id, diagnosis_id=diagnosis_id, rank=rank, score=score_ratio * 5,
        score_ratio=score_ratio, contradictory_evidence=contradictory or [],
        urgency="CRITICAL" if dangerous else "LOW", dangerous_if_missed=dangerous, confidence_band=band,
    )


def test_is_resolved_requires_contradictory_evidence_or_completed_minimum_workup():
    state = PatientState(case_id="resolve_1", chief_complaint="chest pain")
    # No workup done at all, no contradictory evidence -- must NOT be resolved.
    assert not is_resolved("acute_coronary_syndrome", [], state)
    # Contradictory evidence alone resolves it, even mid-workup.
    assert is_resolved("acute_coronary_syndrome", ["ST elevation"], state)


def test_is_resolved_via_completed_minimum_workup_only_when_actually_completed():
    state = PatientState(case_id="resolve_2", chief_complaint="chest pain")
    state.completed_tests = ["ecg"]  # ACS's minimum_workup is ["ecg", "troponin"] -- only half done.
    assert not is_resolved("acute_coronary_syndrome", [], state)
    state.completed_tests = ["ecg", "troponin"]
    assert is_resolved("acute_coronary_syndrome", [], state)


def test_novel_unknown_diagnosis_is_never_auto_resolved_for_lack_of_a_kb_entry():
    state = PatientState(case_id="resolve_3", chief_complaint="chest pain")
    assert not is_resolved("onto::some_novel_concept_not_in_kb", [], state)


def test_decisively_supported_requires_high_confidence_and_no_unresolved_alternative():
    selector = ActionSelector()
    # Top pick is dangerous but only MEDIUM confidence -- not decisively supported.
    differential = [_item("acute_coronary_syndrome", band="MEDIUM")]
    assert selector._decisively_supported_dangerous_ids(differential) == {}


def test_decisively_supported_blocked_by_a_real_unresolved_alternative():
    selector = ActionSelector()
    differential = [
        _item("acute_coronary_syndrome", rank=1, score_ratio=0.9, band="HIGH"),
        _item("pulmonary_embolism", rank=2, score_ratio=0.5, band="MEDIUM", contradictory=[]),
    ]
    assert selector._decisively_supported_dangerous_ids(differential) == {}


def test_decisively_supported_when_top_pick_clear_and_alternative_already_contradicted():
    selector = ActionSelector()
    differential = [
        _item("acute_coronary_syndrome", rank=1, score_ratio=0.9, band="HIGH"),
        _item("pulmonary_embolism", rank=2, score_ratio=0.1, band="LOW", contradictory=["normal D-dimer"]),
    ]
    result = selector._decisively_supported_dangerous_ids(differential)
    assert "acute_coronary_syndrome" in result
    assert result["acute_coronary_syndrome"] == {"ecg", "troponin"}


def test_minimum_workup_item_keeps_full_relevance_even_once_decisively_supported():
    selector = ActionSelector()
    differential = [_item("acute_coronary_syndrome", rank=1, score_ratio=0.9, band="HIGH")]
    decisively_supported = selector._decisively_supported_dangerous_ids(differential)
    still_needed = CandidateInfo(
        action_type="TEST", key="troponin", content_en="Order troponin", content_ko="",
        disease_ids_discriminated=["acute_coronary_syndrome"], diagnostic_discrimination=0.3,
        safety_relevance=0.0, information_gain=0.1, redundancy=0.0, turn_cost=1,
    )
    relevance = selector._management_relevance(
        still_needed, {"acute_coronary_syndrome"}, differential, decisively_supported)
    assert relevance == 1.0


def test_non_minimum_workup_item_is_deprioritized_once_decisively_supported():
    selector = ActionSelector()
    differential = [_item("acute_coronary_syndrome", rank=1, score_ratio=0.9, band="HIGH")]
    decisively_supported = selector._decisively_supported_dangerous_ids(differential)
    redundant = CandidateInfo(
        action_type="TEST", key="cxr", content_en="Order CXR", content_ko="",
        disease_ids_discriminated=["acute_coronary_syndrome"], diagnostic_discrimination=0.1,
        safety_relevance=0.0, information_gain=0.0, redundancy=0.0, turn_cost=1,
    )
    relevance = selector._management_relevance(
        redundant, {"acute_coronary_syndrome"}, differential, decisively_supported)
    assert relevance < 1.0


def test_still_genuinely_uncertain_dangerous_diagnosis_keeps_full_relevance():
    """A dangerous diagnosis that is NOT decisively supported (e.g. it's a real, unresolved
    alternative, not the top pick) must always get the full 1.0 -- this must never regress."""
    selector = ActionSelector()
    differential = [
        _item("acute_coronary_syndrome", rank=1, score_ratio=0.6, band="MEDIUM"),
        _item("pulmonary_embolism", rank=2, score_ratio=0.5, band="MEDIUM"),
    ]
    cand = CandidateInfo(
        action_type="TEST", key="d_dimer", content_en="Order D-dimer", content_ko="",
        disease_ids_discriminated=["pulmonary_embolism"], diagnostic_discrimination=0.4,
        safety_relevance=0.0, information_gain=0.3, redundancy=0.0, turn_cost=1,
    )
    relevance = selector._management_relevance(cand, {"pulmonary_embolism"}, differential, {})
    assert relevance == 1.0
