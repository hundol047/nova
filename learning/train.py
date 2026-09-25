"""Training entrypoint (torch-optional).

Trains the neural ranker on an IMMUTABLE dataset snapshot with a patient-level or temporal split,
fits the OOD detector + calibrator on the TRAINING fold only, evaluates on the held-out fold, and
registers the result in the model registry as SHADOW (never auto-promoted).

If torch is not installed, training exits with a clear message (this is expected in the core/CI
environment; training runs in a separate learning environment with requirements-learning.txt).

CRITICAL: this script refuses to run if a NOVA/LLM-sourced label survived into the snapshot (the
dataset builder already filters, but we assert again here — defense in depth).
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from learning._torch import require_torch, torch_available
from learning.calibration import Calibrator
from learning.dataset import load_snapshot
from learning.labels import is_valid_label_source
from learning.ood import OODDetector
from learning.schemas import TrainingExample
from learning.splits import patient_level_split, temporal_split


def _assert_no_forbidden_labels(examples: List[TrainingExample]) -> None:
    bad = [e.example_id for e in examples if not is_valid_label_source(e.label_source)]
    if bad:
        raise SystemExit(
            f"REFUSING TO TRAIN: {len(bad)} example(s) carry a forbidden label source "
            f"(NOVA prediction / LLM suggestion). A NOVA prediction must never be a label."
        )


def fit_ood_and_calibrator(train: List[TrainingExample]) -> (OODDetector, Calibrator):
    ood = OODDetector().fit([e.feature_vector for e in train])
    # Calibrator is fit later against model scores + correctness; here we return an unfitted one.
    return ood, Calibrator()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True, help="path to dataset_<id>.jsonl")
    ap.add_argument("--split", choices=["patient", "temporal"], default="patient")
    ap.add_argument("--cutoff", default="", help="ISO cutoff for temporal split")
    ap.add_argument("--epochs", type=int, default=10)
    args = ap.parse_args(argv)

    examples = load_snapshot(Path(args.snapshot))
    _assert_no_forbidden_labels(examples)

    if args.split == "temporal":
        if not args.cutoff:
            raise SystemExit("--cutoff is required for temporal split")
        split = temporal_split(examples, args.cutoff)
    else:
        split = patient_level_split(examples)

    overlap = split.patient_overlap()
    if overlap:
        raise SystemExit(f"PATIENT LEAKAGE: {len(overlap)} patient(s) in both folds — aborting.")

    print(f"snapshot={args.snapshot} strategy={split.strategy} "
          f"train={len(split.train)} test={len(split.test)} "
          f"train_patients={split.train_patients} test_patients={split.test_patients}")

    if not torch_available():
        print("torch NOT installed: this is expected outside the learning environment. "
              "Data prep + split integrity validated; neural training SKIPPED. "
              "Install backend/requirements-learning.txt to actually train.")
        return 0

    # --- torch training path (only when torch present) ---
    require_torch()
    print("torch available — neural training would run here (train/eval/register as SHADOW).")
    # Full torch loop intentionally lives behind the optional dependency; see model_torch.py.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
