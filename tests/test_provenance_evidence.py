import json
from pathlib import Path
from scripts.validate_runtime_provenance import validate


def test_current_inventory_has_complete_hash_coverage_but_no_fake_clearance():
    result = validate()
    assert result["coverage_status"] == "PASS"
    assert result["permission_status"] == "BLOCKED"
    assert result["unresolved_assets"] and not result["official_submission_allowed"]


def test_new_unrecorded_clinical_file_cannot_silently_enter(tmp_path):
    directory = tmp_path / "artifacts/compliance_hardening"
    directory.mkdir(parents=True)
    (directory / "clinical_asset_inventory.json").write_text(json.dumps({"assets": []}))
    runtime = tmp_path / "nova_agent"
    runtime.mkdir()
    (runtime / "new_heuristic.py").write_text("# synthetic fixture\n")
    result = validate(tmp_path)
    assert result["coverage_status"] == "FAIL"
    assert result["errors"] == [{"path": "nova_agent/new_heuristic.py", "error": "not inventoried"}]
