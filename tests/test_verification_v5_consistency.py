"""Structural consistency checks for the v5 release-verification artifact -- never re-asserts the
underlying benchmark numbers (those are separately, honestly measured elsewhere); only checks the
artifact's own internal consistency, that it doesn't repeat v3's "unexplained null" problem, and
that the new CURRENT_RELEASE.json pointer file stays in sync with it."""

from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_V5_PATH = _ROOT / "artifacts" / "verification" / "local-release-202ed76-v5.json"
_POINTER_PATH = _ROOT / "artifacts" / "verification" / "CURRENT_RELEASE.json"


def _load_v5() -> dict:
    return json.loads(_V5_PATH.read_text())


def _load_pointer() -> dict:
    return json.loads(_POINTER_PATH.read_text())


def test_v5_artifact_exists_and_v4_is_preserved():
    assert _V5_PATH.exists()
    v4_path = _ROOT / "artifacts" / "verification" / "local-release-faa1701-v4.json"
    assert v4_path.exists(), "v4 must be preserved as historical, never overwritten"


def test_v5_schema_and_current_blind_version():
    data = _load_v5()
    assert data["schema"] == "nova-verification-v5"
    assert data["current_blind_version"] == "v14"


def test_v5_never_leaves_an_unexplained_null():
    """Every null field in the artifact must have an accompanying `<field>_note` explaining why --
    the same discipline v4 introduced, carried forward under the clearer field names
    (artifact_introducing_commit_sha / current_remote_head_verified_externally) that replace v4's
    self-referential-but-ambiguously-named artifact_commit_sha / final_remote_sha."""
    data = _load_v5()
    for key, value in data.items():
        if value is None:
            note_key = f"{key}_note"
            assert note_key in data and data[note_key], (
                f"{key} is null with no {note_key} explaining why -- this repeats v3's defect"
            )


def test_v5_never_reintroduces_v4s_ambiguous_field_names():
    # v4 used artifact_commit_sha/final_remote_sha, whose names didn't make clear WHICH commit's
    # SHA each one refers to (the artifact's own introducing commit vs. the round's eventual final
    # remote HEAD) -- v5 must use the renamed, clearer fields instead, never fall back to the old
    # ambiguous names.
    data = _load_v5()
    assert "artifact_commit_sha" not in data
    assert "final_remote_sha" not in data
    assert "artifact_introducing_commit_sha" in data
    assert "current_remote_head_verified_externally" in data


def test_v5_blind_v14_numbers_are_recorded_and_honest():
    data = _load_v5()
    blind = data["blind_v14"]
    assert blind["case_count"] == 56
    assert blind["first_run_status"] == "EXECUTED_ONCE"
    # Honesty check: this round's own artifact must not overstate v14's result -- it should be
    # reported as better than v13/v12 (it genuinely is) but never claimed to hit the 0% floor the
    # regression suites hit, since it didn't.
    assert blind["critical_miss_rate_pct"] > 0.0
    assert blind["critical_miss_rate_pct"] < 22.2  # genuinely better than both v12 and v13


def test_v5_generalization_fixes_are_listed():
    data = _load_v5()
    fixes = data["generalization_hardening_this_round"]["fixes"]
    assert len(fixes) >= 4
    assert data["generalization_hardening_this_round"]["regression_status"].startswith("No regression")


def test_v5_submission_standalone_full_loop_is_recorded_as_verified():
    data = _load_v5()
    assert data["submission"]["standalone_execution_verified"] is True
    assert data["submission"]["standalone_full_loop_verified"] is True


def test_v5_chief_complaint_routing_benchmark_is_recorded():
    data = _load_v5()
    routing = data["chief_complaint_routing_benchmark"]
    for key in ("known_route_success_rate_pct", "unknown_fallback_rate_pct",
                "specific_over_generic_accuracy_pct", "multi_concept_recall_pct",
                "critical_concept_recall_pct", "end_to_end_candidate_generation_rate_pct"):
        assert routing[key] == 100.0


def test_current_release_pointer_matches_v5_artifact():
    pointer = _load_pointer()
    data = _load_v5()
    assert pointer["current_verification_schema"] == data["schema"]
    assert pointer["verified_runtime_sha"] == data["verified_runtime_sha"]
    assert pointer["current_blind_version"] == data["current_blind_version"]
    referenced = _ROOT / pointer["current_verification_artifact"]
    assert referenced.resolve() == _V5_PATH.resolve()


def test_current_release_pointer_never_creates_a_self_referential_commit_chain():
    # The pointer file points to an artifact by PATH/SHA references, never by embedding its own
    # commit hash -- so it never needs the same "populate in a follow-up commit" dance the
    # artifact's own artifact_introducing_commit_sha does. No field named *_commit_sha here at all.
    pointer = _load_pointer()
    assert not any(k.endswith("_commit_sha") for k in pointer)
