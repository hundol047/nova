import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def artifact():
    data = json.loads((ROOT / "artifacts/verification/local-release-14e6644-v9.json").read_text())
    assert data["schema"] == "nova-verification-v9"
    return data


def test_historical_v9_artifact_matches_every_runtime_byte():
    data = artifact()
    with zipfile.ZipFile(ROOT / data["submission"]["zip"]) as archive:
        for name, digest in data["runtime_sha256"].items():
            assert hashlib.sha256(archive.read(name.removeprefix("submission/"))).hexdigest() == digest, name



def test_historical_v9_archive_matches_runtime_and_allows_only_submission_files():
    data = artifact(); package = ROOT / data["submission"]["zip"]
    assert package.stat().st_size == data["submission"]["bytes"] < 50 * 1024 * 1024
    assert hashlib.sha256(package.read_bytes()).hexdigest() == data["submission"]["sha256"]
    with zipfile.ZipFile(package) as archive:
        assert {"run.py", "requirements.txt", "MANIFEST.json"} <= set(archive.namelist())
        manifest = json.loads(archive.read("MANIFEST.json"))
        assert set(archive.namelist()) == set(manifest["files"]) | {"MANIFEST.json"}
        for name, digest in manifest["files"].items():
            assert name in {"run.py", "requirements.txt"} or name.startswith(("nova_agent/", "competition/"))
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest


def test_local_stub_and_historical_blind_never_claim_live_model_verification():
    data = artifact()
    assert data["current_blind_status"] == "REFERENCE-ONLY" and data["new_blind_runs"] == 0
    assert not data["v17_rerun"] and not data["v17_cases_changed"]
    assert data["official_api_status"] == "NOT VERIFIED"
    assert data["real_gpt_oss"]["real_gpt_oss"] == "NOT VERIFIED"
    assert "NOT real" in data["runtime_modes"]["C_valid_local_stub_wiring"]
    assert not data["independent_clinical_validation"]
