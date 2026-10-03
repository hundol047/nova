"""End-to-end offline retraining lifecycle tests (vNext PART F) — dependency-free.

Covers the governance state machine that does NOT need torch: register-as-SHADOW, promotion
requires an explicit approver AND a cleared safety gate, critical-recall regression is blocked,
rollback restores the previous production model, and persistence carries code_sha/approved_by.
The torch training itself is covered (and torch-skipped) in test_learning_training.py.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from learning.registry import ModelRegistry, ModelState


def test_register_is_shadow_and_never_auto_promoted(tmp_path):
    reg = ModelRegistry(tmp_path / "reg")
    e = reg.register("v1", "ds1", {"critical_recall": 0.995, "top_1_recall": 0.6},
                     code_sha="abc123", dataset_version="ds1")
    assert e.state == ModelState.SHADOW
    assert reg.production_version() is None  # nothing in production yet
    assert e.code_sha == "abc123" and e.dataset_version == "ds1"


def test_promotion_requires_explicit_approver(tmp_path):
    reg = ModelRegistry(tmp_path / "reg")
    reg.register("v1", "ds1", {"critical_recall": 0.995})
    with pytest.raises(PermissionError):
        reg.promote("v1", approved_by="")  # no approver -> blocked
    assert reg.production_version() is None
    e = reg.promote("v1", approved_by="dr.admin")
    assert e.state == ModelState.PRODUCTION and e.approved_by == "dr.admin" and e.approved_at


def test_promotion_blocked_on_critical_recall_regression_and_floor(tmp_path):
    reg = ModelRegistry(tmp_path / "reg")
    reg.register("v1", "ds1", {"critical_recall": 0.995, "top_1_recall": 0.6})
    reg.promote("v1", approved_by="admin")
    # candidate has higher top-1 but LOWER critical recall -> must be blocked (safety gate).
    reg.register("v2", "ds2", {"critical_recall": 0.80, "top_1_recall": 0.9})
    with pytest.raises(PermissionError):
        reg.promote("v2", approved_by="admin")
    assert reg.production_version() == "v1"
    assert reg.get("v2").state == ModelState.REJECTED
    # a candidate below the absolute floor is also blocked even with no baseline diff.
    reg.register("v3", "ds3", {"critical_recall": 0.5})
    with pytest.raises(PermissionError):
        reg.promote("v3", approved_by="admin")


def test_rollback_restores_previous_production(tmp_path):
    reg = ModelRegistry(tmp_path / "reg")
    reg.register("v1", "ds1", {"critical_recall": 0.995})
    reg.register("v3", "ds3", {"critical_recall": 0.999})
    reg.promote("v1", approved_by="admin")
    reg.promote("v3", approved_by="admin")
    assert reg.production_version() == "v3"
    reg.rollback()
    assert reg.production_version() == "v1"
    assert reg.get("v3").state == ModelState.ARCHIVED


def test_persistence_roundtrip(tmp_path):
    reg = ModelRegistry(tmp_path / "reg")
    reg.register("v1", "ds1", {"critical_recall": 0.995}, code_sha="sha1")
    reg.promote("v1", approved_by="dr.x")
    # reload from disk
    reg2 = ModelRegistry(tmp_path / "reg")
    e = reg2.get("v1")
    assert e.state == ModelState.PRODUCTION and e.approved_by == "dr.x" and e.code_sha == "sha1"
    assert reg2.production_version() == "v1"


def test_retrain_cli_status_and_rollback(tmp_path):
    reg_dir = tmp_path / "reg"
    reg = ModelRegistry(reg_dir)
    reg.register("v1", "ds1", {"critical_recall": 0.995})
    reg.register("v2", "ds2", {"critical_recall": 0.999})
    reg.promote("v1", approved_by="admin")
    reg.promote("v2", approved_by="admin")

    status = subprocess.run(
        [sys.executable, "-m", "learning.retrain", "--registry-dir", str(reg_dir), "status"],
        capture_output=True, text=True,
    )
    assert status.returncode == 0
    data = json.loads(status.stdout)
    assert data["production"] == "v2"

    rb = subprocess.run(
        [sys.executable, "-m", "learning.retrain", "--registry-dir", str(reg_dir), "rollback"],
        capture_output=True, text=True,
    )
    assert rb.returncode == 0 and "restored to v1" in rb.stdout

    # promote CLI without approver is impossible (argparse requires --approved-by); with a bad
    # version it fails cleanly.
    bad = subprocess.run(
        [sys.executable, "-m", "learning.retrain", "--registry-dir", str(reg_dir),
         "promote", "--version", "nope", "--approved-by", "admin"],
        capture_output=True, text=True,
    )
    assert bad.returncode == 1 and "BLOCKED" in bad.stdout + bad.stderr
