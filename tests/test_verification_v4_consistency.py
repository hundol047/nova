"""Structural consistency checks for the v4 release-verification artifact -- never re-asserts the
underlying benchmark numbers (those are separately, honestly measured elsewhere); only checks the
artifact's own internal consistency and that it doesn't repeat v3's "unexplained null" problem."""

from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_V4_PATH = _ROOT / "artifacts" / "verification" / "local-release-faa1701-v4.json"


def _load_v4() -> dict:
    return json.loads(_V4_PATH.read_text())


def test_v4_artifact_exists_and_v3_is_preserved():
    assert _V4_PATH.exists()
    v3_path = _ROOT / "artifacts" / "verification" / "local-release-b3fdccd37519-v3.json"
    assert v3_path.exists(), "v3 must be preserved as historical, never overwritten"


def test_v4_schema_and_current_blind_version():
    data = _load_v4()
    assert data["schema"] == "nova-verification-v4"
    assert data["current_blind_version"] == "v13"


def test_v4_never_leaves_an_unexplained_null():
    """Every null field in the artifact must have an accompanying `<field>_note` explaining why --
    this is the explicit fix for the exact problem v3 left (artifact_commit_sha/final_remote_sha
    null with no explanation)."""
    data = _load_v4()
    for key, value in data.items():
        if value is None:
            note_key = f"{key}_note"
            assert note_key in data and data[note_key], (
                f"{key} is null with no {note_key} explaining why -- this repeats v3's defect"
            )


def test_v4_blind_v13_numbers_are_recorded_and_honest():
    data = _load_v4()
    blind = data["blind_v13"]
    assert blind["case_count"] == 52
    assert blind["first_run_status"] == "EXECUTED_ONCE"
    # Honesty check: this round's own artifact must not claim v13 beat v12 when it didn't.
    assert blind["critical_miss_rate_pct"] > 22.2, "v13 was materially worse than v12 -- must not be misreported as better"


def test_v4_generalization_fixes_are_listed():
    data = _load_v4()
    fixes = data["generalization_hardening_this_round"]["fixes"]
    assert len(fixes) >= 5
    assert data["generalization_hardening_this_round"]["regression_status"].startswith("No regression")


def test_v4_submission_standalone_execution_is_recorded_as_verified():
    data = _load_v4()
    assert data["submission"]["standalone_execution_verified"] is True
