"""Structural consistency checks for the v7 verification artifact and CURRENT_RELEASE.json pointer."""

from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_V7 = _ROOT / "artifacts" / "verification" / "local-release-659c7dc-v7.json"
_POINTER = _ROOT / "artifacts" / "verification" / "CURRENT_RELEASE.json"


def _v7() -> dict:
    return json.loads(_V7.read_text())


def test_v7_schema_blind_version_and_history_preserved():
    d = _v7()
    assert d["schema"] == "nova-verification-v7"
    assert d["current_blind_version"] == "v16"
    assert (_ROOT / "artifacts" / "verification" / "local-release-659c7dc-v6.json").exists()


def test_v7_never_leaves_an_unexplained_null():
    d = _v7()
    for key, value in d.items():
        if value is None:
            assert d.get(f"{key}_note"), f"{key} is null with no explanation"


def test_v7_blind_v16_records_both_declared_runs_honestly():
    b = _v7()["blind_v16"]
    assert b["declared_runs"] == 2
    # honesty: the competition-like run costs materially more turns; never hidden
    assert b["competition_like"]["avg_turns"] > b["default_legacy"]["avg_turns"]
    assert "noise" in b["note"]


def test_v7_runtime_unchanged_since_freeze():
    d = _v7()
    assert d["verified_runtime_sha"] == "659c7dc6cdb484dc7dc351a39c52eea71a5b621f"
    assert d["runtime_files_changed_after_verification"] is False


def test_pointer_supersedes_historical_v7():
    p = json.loads(_POINTER.read_text())
    d = _v7()
    assert p["current_verification_schema"] in {"nova-verification-v8", "nova-verification-v9", "nova-verification-v10", "nova-verification-v11", "nova-verification-v12", "nova-verification-v13", "nova-verification-v14", "nova-verification-v15", "nova-verification-v16", "nova-verification-v17", "nova-verification-v18", "nova-verification-v19", "nova-verification-v20", "nova-verification-v21", "nova-verification-v22", "nova-verification-v23", "nova-verification-v24", "nova-verification-v25"}
    assert p["current_blind_version"] in {"v17", "v18", "v19"}
    assert str(_V7.relative_to(_ROOT)) in p["previous_verification_artifacts"]
    assert not any(k.endswith("_commit_sha") for k in p)
