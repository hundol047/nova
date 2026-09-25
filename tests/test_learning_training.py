"""Tests for the real training loop, checkpoint save/load, and compatibility guard (vNext PART C).

Dependency-free parts run everywhere; torch-dependent parts (actual training + weight save/load)
are gated on torch and SKIPPED with a clear marker when torch is absent (IMPLEMENTED_BUT_NOT_
EXECUTED in this environment; CI / a torch env runs them).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from learning._torch import torch_available
from learning.checkpoint import (
    FEATURE_VERSION,
    MODEL_ARCH,
    MODEL_INPUT_DIM,
    SCHEMA_VERSION,
    CheckpointIncompatibleError,
    CheckpointMeta,
    check_compatibility,
    load_meta,
    save_meta,
)
from learning.encoder import FEATURE_DIM
from learning.schemas import LabelSource, TrainingExample
from learning.seed import seed_everything
from learning.train_data import build_batch, candidate_rows


# ---- dependency-free: candidate row construction --------------------------------------------

def _example(cands, label, ex_id="e1"):
    return TrainingExample(
        example_id=ex_id, patient_pseudonym="pt_x", encounter_time="2025-01-01",
        feature_vector=[0.0] * FEATURE_DIM, candidate_concept_ids=cands,
        label_concept_id=label, label_source=LabelSource.CLINICIAN_CONFIRMED,
    )


def test_candidate_rows_layout_and_label_index():
    ex = _example(["a", "b", "c"], "b")
    rows, li = candidate_rows(ex)
    assert li == 1
    assert len(rows) == 3
    assert all(len(r) == MODEL_INPUT_DIM for r in rows)  # FEATURE_DIM + 3
    # pseudo per-candidate signal does NOT encode the label (rows for a/c are not systematically
    # smaller than b) — just check it's label-free by construction: different candidates differ.
    assert rows[0][-3:] != rows[1][-3:]


def test_candidate_rows_missing_label_raises():
    ex = _example(["a", "b"], "zzz")
    with pytest.raises(ValueError):
        candidate_rows(ex)


def test_build_batch_skips_degenerate_and_groups():
    exs = [_example(["a", "b"], "a", "e1"), _example(["x"], "x", "e2")]  # e2 has <2 candidates
    batch = build_batch(exs)
    assert batch.group_sizes == [2]  # e2 skipped
    assert batch.label_indices == [0]
    assert len(batch.rows) == 2


def test_seed_is_deterministic():
    import random
    seed_everything(123)
    a = [random.random() for _ in range(5)]
    seed_everything(123)
    b = [random.random() for _ in range(5)]
    assert a == b


# ---- checkpoint metadata + compatibility guard (dependency-free) ----------------------------

def test_checkpoint_meta_roundtrip(tmp_path):
    meta = CheckpointMeta(model_version="v1", input_dim=MODEL_INPUT_DIM, hidden=64, dropout=0.1,
                          dataset_version="ds1", metrics={"top_1_recall": 0.5})
    weights = tmp_path / "model.pt"
    save_meta(weights, meta)
    loaded = load_meta(weights)
    assert loaded.model_version == "v1"
    assert loaded.input_dim == MODEL_INPUT_DIM
    assert loaded.feature_version == FEATURE_VERSION
    assert loaded.metrics["top_1_recall"] == 0.5
    assert loaded.code_sha  # populated (git sha or 'unknown')


def test_check_compatibility_accepts_matching():
    meta = CheckpointMeta(model_version="v1", input_dim=MODEL_INPUT_DIM, hidden=64, dropout=0.1)
    check_compatibility(meta)  # no raise


@pytest.mark.parametrize("mutate", [
    {"feature_version": "OLD"},
    {"schema_version": "OLD"},
    {"model_arch": "OLD"},
    {"input_dim": MODEL_INPUT_DIM + 1},
])
def test_check_compatibility_rejects_mismatch(mutate):
    meta = CheckpointMeta(model_version="v1", input_dim=MODEL_INPUT_DIM, hidden=64, dropout=0.1)
    for k, v in mutate.items():
        setattr(meta, k, v)
    with pytest.raises(CheckpointIncompatibleError):
        check_compatibility(meta)


# ---- torch-gated: real training loop + checkpoint weight roundtrip --------------------------

@pytest.mark.skipif(not torch_available(), reason="torch not installed (IMPLEMENTED_BUT_NOT_EXECUTED)")
def test_torch_training_and_checkpoint_roundtrip(tmp_path):
    import subprocess
    import sys
    from learning.dataset import build_snapshot

    raw = []
    for i in range(40):
        raw.append({
            "example_id": f"e{i}", "patient_id": f"p{i % 20}", "encounter_time": f"2025-01-{(i % 28) + 1:02d}",
            "label_concept_id": "core:sepsis" if i % 2 else "tier2:migraine",
            "label_source": "CLINICIAN_CONFIRMED",
            "candidate_ids": ["core:sepsis", "tier2:migraine", "tier2:gout"],
            "age_years": 40 + i, "symptom_flags": ["fever"] if i % 2 else ["headache"],
        })
    snap = build_snapshot(raw, tmp_path / "ds")
    out_dir = tmp_path / "models"
    proc = subprocess.run(
        [sys.executable, "-m", "learning.train", "--snapshot", str(snap.path),
         "--split", "patient", "--epochs", "3", "--output-dir", str(out_dir),
         "--model-version", "test-ranker"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "STATUS: TRAINED" in proc.stdout
    weights = out_dir / "test-ranker.pt"
    assert weights.is_file() and weights.with_suffix(".json").is_file()

    # Load back through the compatibility-guarded factory and run inference.
    from learning.model_torch import TorchRanker
    from learning.schemas import CandidateFeature, RankerInput
    ranker = TorchRanker.load(weights)
    out = ranker.rank(RankerInput("c1", [0.0] * FEATURE_DIM,
                                  [CandidateFeature("core:sepsis"), CandidateFeature("tier2:migraine")]))
    assert len(out.ranked) == 2
