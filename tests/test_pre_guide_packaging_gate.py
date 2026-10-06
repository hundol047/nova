"""Packaging must fail closed independently of inference and mock smoke success."""
import json
import re
from pathlib import Path
import zipfile

import pytest
from scripts import build_nova_submission as build


def staging(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "SUBMISSION", tmp_path)
    (tmp_path / "run.py").write_text("# local fixture\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pydantic>=2.6,<3\n", encoding="utf-8")
    return tmp_path


def test_official_build_refuses_before_any_write(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "SUBMISSION", tmp_path / "absent")
    monkeypatch.setenv("NOVA_LLM_PROVIDER", "mock")
    with pytest.raises(SystemExit, match="NOT READY"):
        build.main(["--official"])
    assert not build.SUBMISSION.exists()


@pytest.mark.parametrize("name", ["answers.json", "evaluation/cases.py", "model.safetensors",
                                  "competition/untracked.py", "notes.txt"])
def test_unapproved_staging_payload_rejected(tmp_path, monkeypatch, name):
    root = staging(tmp_path, monkeypatch)
    extra = root / name
    extra.parent.mkdir(parents=True, exist_ok=True)
    extra.write_text("not a runtime asset", encoding="utf-8")
    with pytest.raises(SystemExit, match="Unapproved staging files"):
        build._build_zip_and_manifest()
    assert not (root / "submission.zip").exists()


def test_symlink_in_allowed_entrypoint_rejected(tmp_path, monkeypatch):
    root = staging(tmp_path, monkeypatch)
    (root / "run.py").unlink()
    (root / "run.py").symlink_to(Path(__file__))
    with pytest.raises(SystemExit, match="symlinks"):
        build._submission_files()


@pytest.mark.parametrize("name", ["nova_agent/knowledge/PROVENANCE.md",
                                  "nova_agent/ontology/snapshots/README.md"])
def test_tracked_runtime_provenance_documents_preserved(tmp_path, monkeypatch, name):
    root = staging(tmp_path, monkeypatch)
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Provenance fixture\n")
    assert path in build._submission_files()


def test_local_archive_self_identifies_as_unverified(tmp_path, monkeypatch):
    root = staging(tmp_path, monkeypatch)
    build._build_zip_and_manifest()
    with zipfile.ZipFile(root / "submission.zip") as archive:
        manifest = json.loads(archive.read("MANIFEST.json"))
        assert manifest["artifact_status"] == "LOCAL_PRE_GUIDE_CANDIDATE_ONLY"
        assert manifest["official_submission_allowed"] is False
        assert manifest["source_license_clearance"] == "UNRESOLVED"
        assert manifest["real_model_status"] == "NOT VERIFIED"
        assert set(archive.namelist()) == set(manifest["files"]) | {"MANIFEST.json"}


def test_unresolved_repository_scan_fails_process(tmp_path, monkeypatch):
    from scripts import audit_pre_guide_package as audit
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    monkeypatch.setattr(audit, "_SECRET_PATTERNS", [re.compile("sensitive_test_marker")])
    monkeypatch.setattr(audit.subprocess, "check_output", lambda *a, **kw: "example.txt\n")
    (tmp_path / "example.txt").write_text("sensitive_test_marker\n")
    (tmp_path / "docs/compliance").mkdir(parents=True)
    (tmp_path / "docs/compliance/SECRET_SCAN_FIXTURES.json").write_text("[]")
    (tmp_path / "submission").mkdir()
    with zipfile.ZipFile(tmp_path / "submission/submission.zip", "w") as archive:
        archive.writestr("run.py", "# fixture\n")
        archive.writestr("requirements.txt", "pydantic\n")
    with pytest.raises(SystemExit) as result:
        audit.main(["--output", "audit.json"])
    assert result.value.code == 1
    assert json.loads((tmp_path / "audit.json").read_text())["secret_scan"]["status"] == "REVIEW_REQUIRED"
