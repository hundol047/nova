"""Continual-learning validation (vNext PART G) — dependency-free.

Verifies the leakage/holdout guards that protect training integrity:
  - patient-level split never places one patient in both folds,
  - temporal split keeps a patient wholly on one side of the cutoff,
  - the training entrypoint ABORTS on any cross-fold patient overlap,
  - a NOVA/LLM-sourced label is refused before training.

REAL PATIENT TRAINING is explicitly NOT VERIFIED here: this repository has no real hospital patient
data, and synthetic runs never constitute a clinical-performance claim (asserted by the marker
constant below so the intent is discoverable in code, not only docs).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from learning.dataset import build_snapshot
from learning.schemas import LabelSource, TrainingExample
from learning.splits import patient_level_split, temporal_split

# Discoverable marker: synthetic training is NOT a clinical-performance claim.
REAL_PATIENT_TRAINING = "NOT VERIFIED"


def _ex(ex_id, patient, when, label, source=LabelSource.CLINICIAN_CONFIRMED):
    return TrainingExample(ex_id, patient, when, [0.0], ["a", "b"], label, source)


def test_patient_level_split_no_overlap():
    exs = [_ex(f"e{i}", f"p{i % 8}", "2025-01-01", "a") for i in range(80)]
    sp = patient_level_split(exs, test_frac=0.25)
    assert not sp.patient_overlap()


def test_temporal_split_keeps_patient_on_one_side():
    exs = [
        _ex("e1", "p1", "2023-01-01", "a"),
        _ex("e2", "p1", "2025-06-01", "a"),  # same patient, later — must not straddle
        _ex("e3", "p2", "2025-07-01", "a"),
    ]
    sp = temporal_split(exs, cutoff_iso="2025-01-01")
    assert not sp.patient_overlap()


def test_real_patient_training_marker_is_not_verified():
    assert REAL_PATIENT_TRAINING == "NOT VERIFIED"


def _write_snapshot_with_leak(tmp_path) -> Path:
    """Build a snapshot then hand-edit it so the SAME patient appears with encounter times that a
    patient-level split would keep together — but we force a leak by writing a second snapshot line
    for a patient already in the file under a different example. patient_level_split is deterministic
    by pseudonym, so to exercise the ABORT path we construct a snapshot the splitter would split
    without leak, then verify the abort triggers only on an actual constructed overlap via the
    splits API (covered above). Here we assert the train entrypoint refuses forbidden labels."""
    raw = [{
        "example_id": "e1", "patient_id": "p1", "encounter_time": "2025-01-01",
        "label_concept_id": "core:sepsis", "label_source": "NOVA_PREDICTION",  # forbidden
        "candidate_ids": ["core:sepsis", "tier2:migraine"], "age_years": 50,
    }]
    snap = build_snapshot(raw, tmp_path / "ds")
    return snap.path


def test_forbidden_label_filtered_before_training(tmp_path):
    # build_snapshot drops the NOVA-sourced row -> resulting snapshot has 0 examples.
    path = _write_snapshot_with_leak(tmp_path)
    from learning.dataset import load_snapshot
    rows = load_snapshot(path)
    assert rows == []  # NOVA_PREDICTION label never survives into a training snapshot


def test_train_entrypoint_aborts_on_patient_leakage(tmp_path, monkeypatch):
    """Directly exercise the train module's leakage guard by monkeypatching the split to return an
    overlapping fold, proving the entrypoint aborts rather than training on leaked patients."""
    import learning.train as train_mod
    from learning.splits import SplitResult

    exs = [
        _ex("e1", "p1", "2025-01-01", "core:sepsis"),
        _ex("e2", "p1", "2025-02-01", "tier2:migraine"),
    ]
    snap = build_snapshot(
        [{"example_id": e.example_id, "patient_id": "p1", "encounter_time": e.encounter_time,
          "label_concept_id": e.label_concept_id, "label_source": "CLINICIAN_CONFIRMED",
          "candidate_ids": ["core:sepsis", "tier2:migraine"], "age_years": 50} for e in exs],
        tmp_path / "ds",
    )

    def _leaky_split(examples, *a, **k):
        # same patient in BOTH folds -> must abort
        return SplitResult(train=list(examples), test=list(examples),
                           strategy="leaky", train_patients=1, test_patients=1)

    monkeypatch.setattr(train_mod, "patient_level_split", _leaky_split)
    rc = None
    with pytest.raises(SystemExit) as ei:
        train_mod.main(["--snapshot", str(snap.path), "--split", "patient"])
    assert "PATIENT LEAKAGE" in str(ei.value)
