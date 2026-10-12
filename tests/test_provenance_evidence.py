import json
from pathlib import Path
from scripts.validate_runtime_provenance import validate


def test_current_inventory_has_complete_hash_coverage_but_no_fake_clearance():
    result = validate()
    assert result["coverage_status"] == "PASS"
    assert result["permission_status"] in {"BLOCKED", "DOCUMENTED_FOR_STATED_SCOPE"}
    assert not result["official_submission_allowed"]
    assets = json.loads((Path(__file__).resolve().parents[1] / 'artifacts/compliance_hardening/clinical_asset_inventory.json').read_text())['assets']
    for asset in assets:
        if asset['status'] == 'TEAM_ORIGINAL_VERIFIED':
            assert asset['owner_evidence']
            assert asset['authorship_status'] == 'OWNER_DECLARED_NOT_INDEPENDENTLY_AUDITED'
            assert 'clinician' in asset['clinician_review'].lower() or asset['clinician_review'] == 'NOT_REVIEWED'


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
