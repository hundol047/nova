"""Structural consistency checks for the v6 release-verification artifact -- never re-asserts the
underlying benchmark numbers (those are separately, honestly measured elsewhere); only checks the
artifact's own internal consistency, that it doesn't repeat v3's "unexplained null" problem, and
that the CURRENT_RELEASE.json pointer file stays in sync with it."""

from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_V6_PATH = _ROOT / "artifacts" / "verification" / "local-release-659c7dc-v6.json"
_V5_PATH = _ROOT / "artifacts" / "verification" / "local-release-202ed76-v5.json"
_POINTER_PATH = _ROOT / "artifacts" / "verification" / "CURRENT_RELEASE.json"


def _load_v6() -> dict:
    return json.loads(_V6_PATH.read_text())


def _load_pointer() -> dict:
    return json.loads(_POINTER_PATH.read_text())


def test_v6_artifact_exists_and_v5_is_preserved():
    assert _V6_PATH.exists()
    assert _V5_PATH.exists(), "v5 must be preserved as historical, never overwritten"


def test_v6_schema_and_current_blind_version():
    data = _load_v6()
    assert data["schema"] == "nova-verification-v6"
    assert data["current_blind_version"] == "v15"


def test_v6_never_leaves_an_unexplained_null():
    """Every null field in the artifact must have an accompanying `<field>_note` explaining why --
    the same discipline v4/v5 established."""
    data = _load_v6()
    for key, value in data.items():
        if value is None:
            note_key = f"{key}_note"
            assert note_key in data and data[note_key], (
                f"{key} is null with no {note_key} explaining why -- this repeats v3's defect"
            )


def test_v6_keeps_v5s_clear_field_names():
    data = _load_v6()
    assert "artifact_commit_sha" not in data
    assert "final_remote_sha" not in data
    assert "artifact_introducing_commit_sha" in data
    assert "current_remote_head_verified_externally" in data


def test_v6_blind_v15_numbers_are_recorded_honestly_including_a_regression():
    """The defining honesty requirement of this round's blind-set discipline: Blind v15's own
    result must NOT be reported as an improvement over v14 when it genuinely is not one. This test
    asserts the artifact records the real, worse number -- never a fabricated or rounded-up one --
    and that its own note does not claim improvement."""
    data = _load_v6()
    v15 = data["blind_v15"]
    v14 = data["blind_v14"]
    assert v15["case_count"] == 61
    assert v15["first_run_status"] == "EXECUTED_ONCE"
    assert v15["critical_miss_rate_pct"] > v14["critical_miss_rate_pct"], (
        "Blind v15's critical miss rate must be honestly recorded as WORSE than v14's -- this "
        "round explicitly must not claim monotonic improvement when the numbers do not show it"
    )
    note = v15["note"].lower()
    assert "worse" in note
    assert "no reasoning" in note or "not remediated" in note


def test_v6_blind_v14_is_carried_forward_as_reference_only():
    data = _load_v6()
    assert data["blind_v14"]["case_count"] == 56
    assert "reference" in data["blind_v14"]["first_run_status"].lower() or \
        "reference" in data["blind_v14"]["note"].lower()


def test_v6_five_defect_fixes_are_listed():
    data = _load_v6()
    fixes = data["generalization_hardening_this_round"]["fixes"]
    assert len(fixes) >= 5
    assert data["generalization_hardening_this_round"]["regression_status"].startswith("No regression")


def test_v6_submission_standalone_full_loop_is_recorded_as_verified():
    data = _load_v6()
    assert data["submission"]["standalone_execution_verified"] is True
    assert data["submission"]["standalone_full_loop_verified"] is True


def test_v6_chief_complaint_routing_benchmark_is_recorded():
    data = _load_v6()
    routing = data["chief_complaint_routing_benchmark"]
    for key in ("known_route_success_rate_pct", "unknown_fallback_rate_pct",
                "specific_over_generic_accuracy_pct", "multi_concept_recall_pct",
                "critical_concept_recall_pct", "end_to_end_candidate_generation_rate_pct"):
        assert routing[key] == 100.0


def test_v6_feature_match_specificity_audit_is_recorded():
    data = _load_v6()
    assert "OK" in data["feature_match_specificity_audit"]["result"]


def test_v6_new_round_e_mechanisms_are_all_recorded():
    data = _load_v6()
    for key in ("morphology_normalization", "short_alias_word_boundary_safety",
                "contextual_safety_activation", "diagnostic_specificity_vs_generic_severity",
                "multilingual_concept_normalization", "forced_low_evidence_diagnosis_metadata"):
        assert key in data


def test_current_release_pointer_no_longer_points_to_v6():
    # v7 (Round F) superseded v6 as the pointer target; v6 stays preserved and unchanged in schema.
    pointer = _load_pointer()
    data = _load_v6()
    assert pointer["current_verification_schema"] != data["schema"]
    assert (_ROOT / pointer["current_verification_artifact"]).resolve() != _V6_PATH.resolve()
    assert data["schema"] == "nova-verification-v6"


def test_current_release_pointer_preserves_v5_and_v4_and_v3_as_previous():
    pointer = _load_pointer()
    previous = pointer["previous_verification_artifacts"]
    assert any("v5" in p for p in previous)
    assert any("v4" in p for p in previous)
    assert any("v3" in p for p in previous)


def test_current_release_pointer_never_creates_a_self_referential_commit_chain():
    pointer = _load_pointer()
    assert not any(k.endswith("_commit_sha") for k in pointer)
