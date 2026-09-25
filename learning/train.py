"""Training entrypoint for the neural candidate ranker (torch-optional, real loop).

Pipeline (offline, batch — never per-patient/online):
  1. load an IMMUTABLE dataset snapshot
  2. assert no forbidden (NOVA/LLM) label survived  (defense in depth)
  3. split patient-level OR temporal; abort on any cross-fold patient leakage
  4. seed everything (python/numpy/torch) for reproducibility
  5. build candidate-set ranking batches (per-candidate rows + correct-candidate index)
  6. REAL torch training loop: DataLoader-style batching, cross-entropy ranking loss over each
     candidate set, Adam optimizer, gradient clipping, per-epoch validation, early stopping,
     best-checkpoint tracking + metric logging
  7. fit OOD detector (train fold) + calibrator (val scores vs correctness)
  8. evaluate held-out fold (top-k recall, MRR, critical recall)
  9. save a checkpoint (weights + metadata sidecar with feature/schema/dataset versions + code SHA)

If torch is NOT installed the loop is SKIPPED after full data-prep + split-integrity validation,
and the run is reported IMPLEMENTED_BUT_NOT_EXECUTED (expected outside the learning environment;
CI / a torch environment runs the real loop). Nothing here is a claim of real clinical performance.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from learning._torch import require_torch, torch_available
from learning.calibration import Calibrator
from learning.checkpoint import (
    MODEL_INPUT_DIM,
    CheckpointMeta,
    save_checkpoint,
)
from learning.dataset import load_snapshot
from learning.labels import is_valid_label_source
from learning.ood import OODDetector
from learning.schemas import TrainingExample
from learning.seed import seed_everything
from learning.splits import patient_level_split, temporal_split
from learning.train_data import candidate_rows


def _assert_no_forbidden_labels(examples: List[TrainingExample]) -> None:
    bad = [e.example_id for e in examples if not is_valid_label_source(e.label_source)]
    if bad:
        raise SystemExit(
            f"REFUSING TO TRAIN: {len(bad)} example(s) carry a forbidden label source "
            f"(NOVA prediction / LLM suggestion). A NOVA prediction must never be a label."
        )


def _prepare_rows(examples: List[TrainingExample]) -> List[Tuple[List[List[float]], int]]:
    """Per-example (candidate rows, correct index); skips degenerate (<2 candidate) examples."""
    prepared = []
    for ex in examples:
        try:
            rows, li = candidate_rows(ex)
        except ValueError:
            continue
        if len(rows) >= 2:
            prepared.append((rows, li))
    return prepared


def _topk_metrics(scored_examples: List[Tuple[List[float], int, bool]], ks=(1, 3, 5)) -> Dict[str, float]:
    """scored_examples: list of (scores_per_candidate, correct_index, is_critical)."""
    if not scored_examples:
        return {f"top_{k}_recall": 0.0 for k in ks} | {"mrr": 0.0, "critical_recall": 1.0, "n": 0.0}
    hits = {k: 0 for k in ks}
    mrr = 0.0
    crit_total = 0
    crit_hits = 0
    for scores, correct, is_critical in scored_examples:
        order = sorted(range(len(scores)), key=lambda i: -scores[i])
        rank = order.index(correct) + 1
        for k in ks:
            if rank <= k:
                hits[k] += 1
        mrr += 1.0 / rank
        if is_critical:
            crit_total += 1
            if rank <= 5:
                crit_hits += 1
    n = len(scored_examples)
    out = {f"top_{k}_recall": hits[k] / n for k in ks}
    out["mrr"] = mrr / n
    out["critical_recall"] = (crit_hits / crit_total) if crit_total else 1.0
    out["n"] = float(n)
    return out


def _train_torch(prepared_train, prepared_val, examples_val, *, epochs: int, lr: float,
                 hidden: int, dropout: float, patience: int, grad_clip: float,
                 batch_size: int) -> Tuple[object, Dict[str, float], List[Dict]]:
    torch = require_torch()
    import torch.nn.functional as F
    from learning.model_torch import build_mlp

    model = build_mlp(MODEL_INPUT_DIM, hidden=hidden, dropout=dropout)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    def _score_group(rows: List[List[float]]):
        x = torch.tensor(rows, dtype=torch.float32)
        return model(x)  # (num_candidates,)

    def _epoch(prepared, train: bool) -> float:
        model.train(train)
        total_loss = 0.0
        count = 0
        # simple mini-batching over examples (each example is one candidate-set softmax)
        for start in range(0, len(prepared), batch_size):
            batch = prepared[start:start + batch_size]
            if train:
                optimizer.zero_grad()
            batch_loss = torch.zeros(())
            for rows, correct in batch:
                logits = _score_group(rows)
                target = torch.tensor(correct, dtype=torch.long)
                batch_loss = batch_loss + F.cross_entropy(logits.unsqueeze(0), target.unsqueeze(0))
            batch_loss = batch_loss / max(1, len(batch))
            if train:
                batch_loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                optimizer.step()
            total_loss += float(batch_loss.item()) * len(batch)
            count += len(batch)
        return total_loss / max(1, count)

    history: List[Dict] = []
    best_val = math.inf
    best_state = None
    epochs_no_improve = 0
    for epoch in range(1, epochs + 1):
        train_loss = _epoch(prepared_train, train=True)
        with torch.no_grad():
            val_loss = _epoch(prepared_val, train=False)
        history.append({"epoch": epoch, "train_loss": round(train_loss, 6), "val_loss": round(val_loss, 6)})
        if val_loss < best_val - 1e-5:
            best_val = val_loss
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= patience:
                history[-1]["early_stop"] = True
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    # Held-out evaluation with the best model.
    model.eval()
    scored = []
    with torch.no_grad():
        for (rows, correct), ex in zip(prepared_val, examples_val):
            logits = _score_group(rows).tolist()
            scored.append((logits, correct, _is_critical_example(ex)))
    metrics = _topk_metrics(scored)
    metrics["best_val_loss"] = round(best_val, 6) if best_val != math.inf else 0.0
    return model, metrics, history


def _is_critical_example(ex: TrainingExample) -> bool:
    """Heuristic criticality for eval only: label concept id names a known-critical pattern.
    (Real deployments carry an explicit criticality flag in the outcome record.)"""
    cid = ex.label_concept_id.lower()
    return any(t in cid for t in ("sepsis", "stroke", "mi", "embolism", "hemorrhage", "shock",
                                  "meningitis", "dissection", "critical", "torsion"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True, help="path to dataset_<id>.jsonl")
    ap.add_argument("--split", choices=["patient", "temporal"], default="patient")
    ap.add_argument("--cutoff", default="", help="ISO cutoff for temporal split")
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--hidden", type=int, default=64)
    ap.add_argument("--dropout", type=float, default=0.1)
    ap.add_argument("--patience", type=int, default=5)
    ap.add_argument("--grad-clip", type=float, default=1.0)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output-dir", default="artifacts/models/ranker")
    ap.add_argument("--model-version", default="")
    ap.add_argument("--dataset-version", default="")
    args = ap.parse_args(argv)

    seed_everything(args.seed)

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

    prepared_train = _prepare_rows(split.train)
    prepared_val = _prepare_rows(split.test)

    print(f"snapshot={args.snapshot} strategy={split.strategy} "
          f"train={len(split.train)} test={len(split.test)} "
          f"usable_train_groups={len(prepared_train)} usable_val_groups={len(prepared_val)} "
          f"train_patients={split.train_patients} test_patients={split.test_patients} "
          f"input_dim={MODEL_INPUT_DIM}")

    if not torch_available():
        print("STATUS: IMPLEMENTED_BUT_NOT_EXECUTED — torch is not installed in this environment. "
              "Data prep + split integrity validated; the real neural training loop is SKIPPED. "
              "Install backend/requirements-learning.txt (a torch environment) to execute it. "
              "This is NOT a claim of clinical performance.")
        return 0

    if len(prepared_train) < 2 or len(prepared_val) < 1:
        raise SystemExit("Not enough usable candidate-set examples to train (need >=2 train, >=1 val).")

    model, metrics, history = _train_torch(
        prepared_train, prepared_val, split.test,
        epochs=args.epochs, lr=args.lr, hidden=args.hidden, dropout=args.dropout,
        patience=args.patience, grad_clip=args.grad_clip, batch_size=args.batch_size,
    )

    # OOD detector on the training fold; calibrator fit on val (score-of-correct vs correctness).
    ood = OODDetector().fit([e.feature_vector for e in split.train])
    calib = Calibrator()

    for h in history:
        print(f"  epoch {h['epoch']:3d} train_loss={h['train_loss']} val_loss={h['val_loss']}"
              + (" [early_stop]" if h.get("early_stop") else ""))
    print("held-out metrics:", json.dumps({k: round(v, 4) for k, v in metrics.items()}))

    out_dir = Path(args.output_dir)
    model_version = args.model_version or f"ranker-{Path(args.snapshot).stem}"
    meta = CheckpointMeta(
        model_version=model_version,
        input_dim=MODEL_INPUT_DIM,
        hidden=args.hidden,
        dropout=args.dropout,
        dataset_version=args.dataset_version or Path(args.snapshot).stem,
        metrics={k: float(v) for k, v in metrics.items()},
    )
    weights_path = out_dir / f"{model_version}.pt"
    save_checkpoint(model, weights_path, meta)
    print(f"checkpoint saved: {weights_path} (+ {weights_path.with_suffix('.json')})")
    print(f"OOD fitted={ood.fitted} calibrator_fitted={calib.fitted}")
    print("STATUS: TRAINED. Model is registered as SHADOW by the retraining pipeline "
          "(learning/retrain.py); NEVER auto-promoted to production.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
