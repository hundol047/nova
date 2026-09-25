"""Backend bridge to the (opt-in) continual-learning subsystem — admin-facing reads + outcome capture.

This is the ONLY backend module that talks to the learning/ package. It is:
  - opt-in: nothing is captured unless NOVA_LEARNING_ENABLED=true (learning.continual.learning_enabled),
  - governed: a clinician-adjudicated label from a PERMITTED source (never a NOVA/LLM prediction) is
    what becomes an eligible learning outcome; the NOVA prediction is stored separately for audit,
  - fail-safe: any error is swallowed so a clinical case-close is NEVER blocked by learning capture,
  - PHI-safe: capture de-identifies (learning.continual.capture_record); coverage-gap analytics use
    a non-reversible fingerprint.

The admin read helpers (status / coverage-gaps / models) back the /v1/admin/learning/* endpoints,
which are gated by the 'learning:admin' RBAC action (admin only) in main.py.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

_MODEL_REGISTRY_DIR = Path(
    os.getenv("NOVA_MODEL_REGISTRY_DIR",
              str(Path(__file__).resolve().parents[2] / "artifacts" / "models" / "registry"))
)


def learning_status() -> Dict:
    """PHI-free governance posture of the learning subsystem (admin surface)."""
    try:
        from learning.continual import governance_report
        from learning.runtime import MLRuntimeConfig
        report = governance_report().as_dict()
        ml = MLRuntimeConfig.from_env()
        report["ml_ranker"] = {
            "enabled": ml.enabled,
            "shadow_mode": ml.shadow_mode,
            "model_path_configured": bool(ml.model_path),
        }
        return report
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}", "capture_enabled": False}


def list_models() -> List[Dict]:
    """Model registry entries (version/status/metrics/dataset_version/created_at). Empty if none."""
    try:
        from learning.registry import ModelRegistry
        reg = ModelRegistry(_MODEL_REGISTRY_DIR)
        out = []
        for e in reg.list_versions():
            d = e.as_dict()
            d["is_production"] = (reg.production_version() == e.version)
            out.append(d)
        return out
    except Exception:  # noqa: BLE001
        return []


def coverage_gaps(limit: int = 50) -> List[Dict]:
    """Aggregated PHI-free coverage-gap fingerprints (where the disease universe is thin).

    Reads persisted gap events if a store is configured; otherwise returns an empty list. Never
    exposes any patient data (only salted fingerprints + outcomes)."""
    try:
        # Coverage-gap events are captured PHI-free (learning.coverage_gap). A DB-backed store is
        # optional; when absent this returns [] rather than fabricating data.
        store_path = os.getenv("NOVA_COVERAGE_GAP_STORE", "")
        if not store_path or not Path(store_path).is_file():
            return []
        import json
        from learning.coverage_gap import CoverageGapEvent, rank_gaps
        rows = [json.loads(l) for l in Path(store_path).read_text(encoding="utf-8").splitlines() if l.strip()]
        events = [
            CoverageGapEvent(
                gap_event_id=r.get("gap_event_id", ""), observed_at=r.get("observed_at", ""),
                outcome=r.get("outcome", ""), query_fingerprint=r.get("query_fingerprint", ""),
                top_candidate_concept_id=r.get("top_candidate_concept_id"),
                top_candidate_score=r.get("top_candidate_score"),
            )
            for r in rows
        ]
        return rank_gaps(events, top_n=limit)
    except Exception:  # noqa: BLE001
        return []


def capture_case_outcome(*, case_id: str, patient_id: str, encounter_time: str,
                         nova_top_concept_id: Optional[str],
                         candidate_concept_ids: List[str],
                         clinician_final_diagnosis_id: Optional[str],
                         clinician_label_source: Optional[str],
                         feature_snapshot: Optional[Dict] = None) -> Optional[Dict]:
    """Build an eligible, de-identified learning outcome IF and ONLY IF capture is enabled and a
    clinician-adjudicated label from a permitted source is present.

    Returns the de-identified record dict on success, or None (silently) when capture is disabled,
    inputs are insufficient, or the label source is forbidden. NEVER raises — a clinical case-close
    must not be blocked by learning capture. A NOVA/LLM prediction can never be the label (enforced
    by learning.continual.capture_record / learning.labels)."""
    try:
        from learning.continual import capture_record, learning_enabled
        from learning.schemas import LabelSource
        if not learning_enabled():
            return None
        if not clinician_final_diagnosis_id or not clinician_label_source:
            return None  # no adjudicated label yet -> nothing eligible to capture
        try:
            source = LabelSource(clinician_label_source)
        except ValueError:
            return None  # unknown label source -> refuse
        record = capture_record(
            raw_patient_record={"patient_id": patient_id},
            encounter_time=encounter_time,
            feature_snapshot=feature_snapshot or {},
            candidate_concept_ids=candidate_concept_ids,
            nova_top_concept_id=nova_top_concept_id,
            clinician_label_concept_id=clinician_final_diagnosis_id,
            clinician_label_source=source,
        )
        return record.as_row()
    except Exception:  # noqa: BLE001 - capture must never break a clinical case-close
        return None
