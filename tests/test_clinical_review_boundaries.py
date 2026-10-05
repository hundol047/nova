"""Prevent review leads from becoming fabricated clinical approval."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_review_packet_covers_current_core_without_inventing_reviewers():
    forms = json.loads((ROOT / "docs/clinical_review/CLINICAL_REVIEW_FORM.json").read_text())
    profiles = {r["id"]: r for p in (ROOT / "nova_agent/knowledge/diseases").glob("*.json")
                for r in json.loads(p.read_text())}
    assert {r["disease_id"] for r in forms} == set(profiles)
    for row in forms:
        assert row["current_profile"] == profiles[row["disease_id"]]
        assert row["source_sha256"] == hashlib.sha256((ROOT / row["source_path"]).read_bytes()).hexdigest()
        assert row["review"]["reviewer_name"] is None
        assert row["review"]["approval"] == "PENDING"
        assert all(r["relationship"].endswith("NOT_VERIFIED_CLINICAL_EQUIVALENCE") for r in row["source_leads"])


def test_background_candidates_cannot_clear_original_diagnostic_rules():
    data = json.loads((ROOT / "docs/clinical_review/TEST_NOTE_REPLACEMENT_CANDIDATES.json").read_text())
    assert not data["runtime_modified"]
    assert data["original_notes_sha256"] == hashlib.sha256(
        (ROOT / "nova_agent/knowledge/diagnostic_tests/notes.json").read_bytes()).hexdigest()
    for row in data["candidates"]:
        assert row["original_provenance"] == "UNRESOLVED"
        assert row["promotion"] == "BLOCKED_PENDING_SCOPE_AND_SAFETY_REVIEW"
        assert not row["submission_included_as_replacement"]
        assert row["clinician_review"] == "PENDING"
