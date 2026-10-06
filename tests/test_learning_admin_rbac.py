"""RBAC + outcome-capture governance tests for the admin learning surface (vNext PART E).

auth.py imports httpx/fastapi at module top (not installed in this dependency-free environment), so
the pure permission logic is reconstructed here by exec-ing ONLY the ROLE_PERMISSIONS definition
block from the source — this verifies the actual grant table without importing the web stack. The
learning_admin service logic (capture gating / de-id / NOVA-never-a-label) is imported directly
(it is dependency-free).
"""

from __future__ import annotations

import re
import sys
import types
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
# Bootstrap a light nova_agent package so learning_admin's transitive imports stay dependency-free.
if "nova_agent" not in sys.modules:
    _pkg = types.ModuleType("nova_agent")
    _pkg.__path__ = [str(_ROOT / "nova_agent")]
    sys.modules["nova_agent"] = _pkg


def _extract_role_permissions() -> dict:
    """Exec just the action-set + ROLE_PERMISSIONS assignments from auth.py, in isolation."""
    src = (_ROOT / "backend" / "app" / "services" / "auth.py").read_text(encoding="utf-8")
    lines = src.splitlines()
    wanted = []
    capture = False
    for line in lines:
        if re.match(r"^_[A-Z_]+ ?= ?", line) or line.startswith("ROLE_PERMISSIONS = {"):
            capture = True
        if capture:
            wanted.append(line)
        if capture and line.startswith("}") and "ROLE_PERMISSIONS" not in line and "{" not in line:
            # end of the ROLE_PERMISSIONS dict (a lone closing brace)
            if any("ROLE_PERMISSIONS = {" in w for w in wanted):
                break
    ns: dict = {}
    exec("\n".join(wanted), ns)  # noqa: S102 - trusted first-party source, isolated namespace
    return ns["ROLE_PERMISSIONS"]


def test_learning_admin_action_is_admin_only():
    perms = _extract_role_permissions()
    assert "learning:admin" in perms["admin"], "admin must have learning:admin"
    for role in ("clinician", "clinician_readonly", "pharmacist"):
        assert "learning:admin" not in perms.get(role, set()), f"{role} must NOT have learning:admin"


def test_capture_disabled_by_default(monkeypatch):
    monkeypatch.delenv("NOVA_LEARNING_ENABLED", raising=False)
    from backend.app.services.learning_admin import capture_case_outcome
    assert capture_case_outcome(
        case_id="c1", patient_id="p1", encounter_time="2025-01-01",
        nova_top_concept_id="core:sepsis", candidate_concept_ids=["core:sepsis"],
        clinician_final_diagnosis_id="core:sepsis", clinician_label_source="CLINICIAN_CONFIRMED",
    ) is None


def test_capture_deidentifies_and_separates_nova_prediction(monkeypatch):
    monkeypatch.setenv("NOVA_LEARNING_ENABLED", "true")
    from backend.app.services.learning_admin import capture_case_outcome
    rec = capture_case_outcome(
        case_id="c1", patient_id="patient-123", encounter_time="2025-01-01",
        nova_top_concept_id="core:sepsis", candidate_concept_ids=["core:sepsis", "tier2:migraine"],
        clinician_final_diagnosis_id="core:sepsis", clinician_label_source="CLINICIAN_CONFIRMED",
    )
    assert rec is not None
    assert "patient-123" not in str(rec)  # de-identified
    assert rec["patient_pseudonym"].startswith("pt_")
    assert rec["nova_top_concept_id"] == "core:sepsis"     # prediction stored separately
    assert rec["label_concept_id"] == "core:sepsis"        # clinician label
    assert rec["label_status"] == "ADJUDICATED"


def test_nova_prediction_can_never_be_label(monkeypatch):
    monkeypatch.setenv("NOVA_LEARNING_ENABLED", "true")
    from backend.app.services.learning_admin import capture_case_outcome
    assert capture_case_outcome(
        case_id="c1", patient_id="p2", encounter_time="2025-01-01",
        nova_top_concept_id="x", candidate_concept_ids=["x"],
        clinician_final_diagnosis_id="x", clinician_label_source="NOVA_PREDICTION",
    ) is None
    assert capture_case_outcome(
        case_id="c1", patient_id="p2", encounter_time="2025-01-01",
        nova_top_concept_id="x", candidate_concept_ids=["x"],
        clinician_final_diagnosis_id="x", clinician_label_source="LLM_SUGGESTION",
    ) is None


def test_status_and_models_and_gaps_are_phi_free(monkeypatch):
    monkeypatch.delenv("NOVA_LEARNING_ENABLED", raising=False)
    from backend.app.services.learning_admin import learning_status, list_models, coverage_gaps
    status = learning_status()
    assert "capture_enabled" in status
    assert isinstance(list_models(), list)
    assert isinstance(coverage_gaps(), list)
