"""Tests for the vNext learning subsystem (learning/ package) — torch-free paths only.

These exercise the SAFETY-CRITICAL invariants of the pipeline without requiring torch:
  - ranker safety ordering (drop excluded, float critical, no fake calibrated score),
  - label provenance (NOVA/LLM never a label),
  - patient-level + temporal split integrity (no leakage),
  - immutable dataset snapshots + forbidden-label filtering,
  - model registry promotion gate (critical-recall) + rollback,
  - continual-learning capture gating + de-identification,
  - coverage-gap analytics are PHI-free.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from learning.calibration import Calibrator
from learning.continual import (
    LABEL_ADJUDICATED,
    LearningDisabledError,
    OnlineTrainingForbiddenError,
    assert_offline_training,
    capture_record,
    learning_enabled,
)
from learning.coverage_gap import build_gap_event, query_fingerprint
from learning.dataset import build_snapshot, load_snapshot
from learning.labels import filter_valid_examples, is_valid_label_source
from learning.ranker import get_default_ranker
from learning.registry import ModelRegistry
from learning.schemas import CandidateFeature, LabelSource, RankerInput, TrainingExample
from learning.splits import patient_level_split, temporal_split


# ---- ranker safety invariant ---------------------------------------------------------------

def test_ranker_drops_safety_excluded_and_floats_critical():
    cands = [
        CandidateFeature("normal_high", base_evidence_score=0.95, retrieval_score=0.9),
        CandidateFeature("critical_low", base_evidence_score=0.05, is_critical=True),
        CandidateFeature("excluded", base_evidence_score=0.99, safety_excluded=True),
    ]
    out = get_default_ranker().rank(RankerInput("c1", [0.0] * 72, cands))
    ids = [r.concept_id for r in out.ranked]
    assert "excluded" not in ids, "safety-excluded candidate must never be ranked"
    assert out.ranked[0].concept_id == "critical_low", "critical must float above a high-scored normal"


def test_ranker_emits_no_calibrated_score_without_fitted_calibrator():
    out = get_default_ranker().rank(
        RankerInput("c2", [0.0] * 72, [CandidateFeature("a", base_evidence_score=0.5)])
    )
    assert out.calibrated is False
    assert all(r.calibrated_score is None for r in out.ranked)


# ---- label provenance -----------------------------------------------------------------------

def test_nova_and_llm_labels_are_forbidden():
    assert not is_valid_label_source(LabelSource.NOVA_PREDICTION)
    assert not is_valid_label_source(LabelSource.LLM_SUGGESTION)
    assert is_valid_label_source(LabelSource.CLINICIAN_CONFIRMED)


def test_filter_valid_examples_rejects_model_labels():
    exs = [
        TrainingExample("e1", "p1", "2024-01-01", [0.0], ["x"], "d1", LabelSource.CLINICIAN_CONFIRMED),
        TrainingExample("e2", "p1", "2024-02-01", [0.0], ["x"], "d2", LabelSource.NOVA_PREDICTION),
    ]
    kept, rejected = filter_valid_examples(exs)
    assert [e.example_id for e in kept] == ["e1"]
    assert [e.example_id for e in rejected] == ["e2"]


# ---- split integrity ------------------------------------------------------------------------

def test_patient_level_split_has_no_patient_overlap():
    exs = [
        TrainingExample(f"e{i}", f"p{i % 5}", "2024-01-01", [0.0], ["x"], "d", LabelSource.CODED_DISCHARGE_DX)
        for i in range(50)
    ]
    sp = patient_level_split(exs, test_frac=0.3)
    assert not sp.patient_overlap()


def test_temporal_split_keeps_patient_on_one_side():
    exs = [
        TrainingExample("e1", "p1", "2023-01-01", [0.0], ["x"], "d", LabelSource.CODED_DISCHARGE_DX),
        TrainingExample("e2", "p1", "2025-06-01", [0.0], ["x"], "d", LabelSource.CODED_DISCHARGE_DX),
        TrainingExample("e3", "p2", "2025-06-01", [0.0], ["x"], "d", LabelSource.CODED_DISCHARGE_DX),
    ]
    sp = temporal_split(exs, cutoff_iso="2025-01-01")
    assert not sp.patient_overlap(), "a patient must not straddle the temporal cutoff"


# ---- immutable dataset snapshot -------------------------------------------------------------

def test_snapshot_filters_forbidden_labels_and_is_immutable():
    raw = [
        {"example_id": "e1", "patient_id": "P1", "encounter_time": "2024-01-01",
         "label_concept_id": "d1", "label_source": "CLINICIAN_CONFIRMED",
         "candidate_ids": ["d1"], "age_years": 60, "symptom_flags": ["chest_pain"]},
        {"example_id": "e2", "patient_id": "P2", "encounter_time": "2024-02-01",
         "label_concept_id": "d2", "label_source": "NOVA_PREDICTION",
         "candidate_ids": ["d2"], "age_years": 40},
    ]
    d = Path(tempfile.mkdtemp())
    snap = build_snapshot(raw, d)
    assert snap.n_examples == 1 and snap.n_rejected_label == 1
    rows = load_snapshot(snap.path)
    assert len(rows) == 1 and rows[0].label_source == LabelSource.CLINICIAN_CONFIRMED
    # immutability: rebuilding the same snapshot id must refuse to overwrite
    with pytest.raises(SystemExit):
        build_snapshot(raw, d, snapshot_id=snap.snapshot_id)


# ---- registry promotion gate + rollback -----------------------------------------------------

def test_registry_blocks_critical_recall_regression_and_supports_rollback():
    d = Path(tempfile.mkdtemp())
    reg = ModelRegistry(d / "registry")
    reg.register("v1", "snapA", {"critical_recall": 0.995, "top_k_accuracy": 0.7})
    reg.promote("v1")
    assert reg.production_version() == "v1"

    reg.register("v2", "snapB", {"critical_recall": 0.80, "top_k_accuracy": 0.95})
    with pytest.raises(PermissionError):
        reg.promote("v2")  # regresses critical recall -> blocked
    assert reg.production_version() == "v1"

    reg.register("v3", "snapC", {"critical_recall": 0.999, "top_k_accuracy": 0.85})
    reg.promote("v3")
    assert reg.production_version() == "v3"
    reg.rollback()
    assert reg.production_version() == "v1"


# ---- continual-learning governance ----------------------------------------------------------

def test_capture_disabled_by_default(monkeypatch):
    monkeypatch.delenv("NOVA_LEARNING_ENABLED", raising=False)
    assert learning_enabled() is False
    with pytest.raises(LearningDisabledError):
        capture_record(raw_patient_record={"patient_id": "P1"}, encounter_time="2025-01-01",
                       feature_snapshot={"age_years": 60}, candidate_concept_ids=["c1"],
                       nova_top_concept_id="c1")


def test_capture_deidentifies_and_never_labels_with_nova(monkeypatch):
    monkeypatch.setenv("NOVA_LEARNING_ENABLED", "true")
    rec = capture_record(
        raw_patient_record={"patient_id": "P1", "name": "Real Name", "mrn": "M1"},
        encounter_time="2025-01-01",
        feature_snapshot={"age_years": 60, "mrn": "M1", "heart_rate": 100},
        candidate_concept_ids=["c1"], nova_top_concept_id="c1",
    )
    assert rec.patient_pseudonym.startswith("pt_") and "P1" not in rec.patient_pseudonym
    assert "mrn" not in rec.feature_snapshot and "name" not in rec.feature_snapshot
    assert rec.nova_top_concept_id == "c1" and rec.label_concept_id is None
    assert rec.training_eligible() is False

    with pytest.raises(ValueError):
        capture_record(raw_patient_record={"patient_id": "P2"}, encounter_time="2025-02-01",
                       feature_snapshot={}, candidate_concept_ids=[], nova_top_concept_id="c9",
                       clinician_label_concept_id="c9", clinician_label_source=LabelSource.NOVA_PREDICTION)


def test_adjudicated_clinician_label_is_training_eligible(monkeypatch):
    monkeypatch.setenv("NOVA_LEARNING_ENABLED", "true")
    rec = capture_record(
        raw_patient_record={"patient_id": "P3"}, encounter_time="2025-03-01",
        feature_snapshot={"age_years": 30}, candidate_concept_ids=["c3"], nova_top_concept_id="c3",
        clinician_label_concept_id="c3", clinician_label_source=LabelSource.CLINICIAN_CONFIRMED,
    )
    assert rec.label_status == LABEL_ADJUDICATED and rec.training_eligible() is True


def test_online_training_tripwire(monkeypatch):
    monkeypatch.delenv("NOVA_ONLINE_TRAINING", raising=False)
    assert_offline_training("test")  # no raise
    monkeypatch.setenv("NOVA_ONLINE_TRAINING", "true")
    with pytest.raises(OnlineTrainingForbiddenError):
        assert_offline_training("test")


# ---- coverage-gap analytics are PHI-free ----------------------------------------------------

def test_coverage_gap_fingerprint_is_stable_and_textless():
    f1 = query_fingerprint("sudden severe headache")
    f2 = query_fingerprint("Headache SEVERE sudden")
    assert f1 == f2
    ev = build_gap_event(query="weird rash and joint pain", outcome="UNKNOWN_PRESENTATION")
    assert ev is not None
    assert "weird" not in str(ev.as_row()) and "rash" not in str(ev.as_row())
    assert build_gap_event(query="x", outcome="KNOWN_CONDITION") is None


# ---- calibrator honesty ---------------------------------------------------------------------

def test_calibrator_returns_none_until_fitted():
    c = Calibrator()
    assert c.calibrated(0.5) is None
    # too few samples -> stays unfitted
    c.fit([0.1, 0.9], [0, 1])
    assert c.fitted is False and c.calibrated(0.5) is None
