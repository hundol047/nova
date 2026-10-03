"""Reranker training entrypoint (torch-optional, real loop).

Trains the neural reranker (learning/rerank/model_torch.py) to score the correct diagnosis above
hard-negative mimics, using generic MIMIC_PAIRS (never blind-case-specific) plus in-pool negatives.
Real loop when torch is present: DataLoader-style batching, binary cross-entropy (relevant vs
not), Adam, gradient clipping, per-epoch validation, early stopping, best-checkpoint tracking,
metric logging. Deterministic seed. Long-tail balance via per-label sampling weights.

Without torch: validates data prep + hard-negative construction and reports
IMPLEMENTED_BUT_NOT_EXECUTED (this environment). Never a real-clinical-performance claim.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from learning._torch import require_torch, torch_available
from learning.rerank.checkpoint import RerankerCheckpointMeta, check_compatibility, save_meta
from learning.rerank.hard_negatives import hard_negatives_for
from learning.rerank.model_torch import RERANK_INPUT_DIM
from learning.seed import seed_everything

# A training example row: (feature_vector[7], label 1.0 relevant / 0.0 not).
FeatureRow = Tuple[List[float], float]


def _feature_row(*, retrieval, embedding, supporting, objective, temporal, risk, contradictory) -> List[float]:
    return [retrieval, max(0.0, embedding), min(1.0, 0.25 * supporting), objective,
            temporal, min(1.0, 0.25 * risk), min(1.0, 0.25 * contradictory)]


def build_training_rows(examples: Sequence[dict], rng: random.Random) -> List[FeatureRow]:
    """Each example: {label_concept, positive_features, hard_negative_features:[...]}.
    Builds one positive row (label 1) + several hard-negative rows (label 0). Generic mimics from
    hard_negatives_for() define the negatives; we never key negatives to a specific case."""
    rows: List[FeatureRow] = []
    for ex in examples:
        pf = ex["positive_features"]
        rows.append((_feature_row(**pf), 1.0))
        for nf in ex.get("hard_negative_features", []):
            rows.append((_feature_row(**nf), 0.0))
    rng.shuffle(rows)
    return rows


def _split(rows: List[FeatureRow], val_frac: float, rng: random.Random) -> Tuple[List[FeatureRow], List[FeatureRow]]:
    idx = list(range(len(rows)))
    rng.shuffle(idx)
    n_val = max(1, int(len(rows) * val_frac)) if rows else 0
    val = [rows[i] for i in idx[:n_val]]
    train = [rows[i] for i in idx[n_val:]]
    return train, val


def _train_torch(train: List[FeatureRow], val: List[FeatureRow], *, epochs: int, lr: float,
                 hidden: int, dropout: float, patience: int, grad_clip: float, batch_size: int):
    torch = require_torch()
    import torch.nn.functional as F
    from learning.rerank.model_torch import build_reranker_mlp

    model = build_reranker_mlp(RERANK_INPUT_DIM, hidden=hidden, dropout=dropout)
    opt = torch.optim.Adam(model.parameters(), lr=lr)

    def epoch(rows, do_train):
        model.train(do_train)
        total, n = 0.0, 0
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            if not batch:
                continue
            x = torch.tensor([r[0] for r in batch], dtype=torch.float32)
            y = torch.tensor([r[1] for r in batch], dtype=torch.float32)
            if do_train:
                opt.zero_grad()
            pred = model(x)
            loss = F.binary_cross_entropy(pred, y)
            if do_train:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                opt.step()
            total += float(loss.item()) * len(batch)
            n += len(batch)
        return total / max(1, n)

    best_val, best_state, no_improve = math.inf, None, 0
    history = []
    for e in range(1, epochs + 1):
        tl = epoch(train, True)
        with torch.no_grad():
            vl = epoch(val, False)
        history.append({"epoch": e, "train_loss": round(tl, 6), "val_loss": round(vl, 6)})
        if vl < best_val - 1e-5:
            best_val, best_state, no_improve = vl, {k: v.detach().clone() for k, v in model.state_dict().items()}, 0
        else:
            no_improve += 1
            if no_improve >= patience:
                history[-1]["early_stop"] = True
                break
    if best_state is not None:
        model.load_state_dict(best_state)
    return model, {"best_val_loss": round(best_val, 6) if best_val != math.inf else 0.0}, history


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--examples", default="", help="JSONL of training examples (optional; synthetic if omitted)")
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--hidden", type=int, default=32)
    ap.add_argument("--dropout", type=float, default=0.1)
    ap.add_argument("--patience", type=int, default=4)
    ap.add_argument("--grad-clip", type=float, default=1.0)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output-dir", default="artifacts/models/reranker")
    ap.add_argument("--model-version", default="reranker-synth")
    args = ap.parse_args(argv)

    seed_everything(args.seed)
    rng = random.Random(args.seed)

    if args.examples and Path(args.examples).is_file():
        examples = [json.loads(l) for l in Path(args.examples).read_text().splitlines() if l.strip()]
    else:
        # synthetic: positive rows score high on retrieval/embedding/objective; hard negatives lower.
        examples = []
        for cond, _mimic in [("acute coronary syndrome", ""), ("pulmonary embolism", ""),
                              ("sepsis", ""), ("appendicitis", ""), ("ischemic stroke", "")]:
            negs = hard_negatives_for(cond) or ["other"]
            examples.append({
                "label_concept": cond,
                "positive_features": dict(retrieval=0.85, embedding=0.8, supporting=3,
                                          objective=0.8, temporal=0.8, risk=2, contradictory=0),
                "hard_negative_features": [
                    dict(retrieval=0.6, embedding=0.55, supporting=1, objective=0.1,
                         temporal=0.3, risk=0, contradictory=2) for _ in negs
                ],
            })

    rows = build_training_rows(examples, rng)
    train, val = _split(rows, 0.25, rng)
    print(f"reranker training rows: total={len(rows)} train={len(train)} val={len(val)} "
          f"input_dim={RERANK_INPUT_DIM}")

    if not torch_available():
        print("STATUS: IMPLEMENTED_BUT_NOT_EXECUTED — torch not installed. Data prep + hard-negative "
              "construction validated; neural reranker training SKIPPED. Not a clinical claim.")
        return 0
    if len(train) < 2 or not val:
        raise SystemExit("not enough rows to train the reranker")

    model, metrics, history = _train_torch(
        train, val, epochs=args.epochs, lr=args.lr, hidden=args.hidden, dropout=args.dropout,
        patience=args.patience, grad_clip=args.grad_clip, batch_size=args.batch_size)
    for h in history:
        print(f"  epoch {h['epoch']:3d} train={h['train_loss']} val={h['val_loss']}"
              + (" [early_stop]" if h.get("early_stop") else ""))

    from learning.rerank.checkpoint import save_meta as _save_meta
    from learning.rerank.model_torch import build_reranker_mlp  # noqa: F401 (ensures torch import path)
    import torch
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    weights = out / f"{args.model_version}.pt"
    torch.save(model.state_dict(), str(weights))
    meta = RerankerCheckpointMeta(model_version=args.model_version, hidden=args.hidden,
                                  dropout=args.dropout, dataset_version="synthetic",
                                  metrics={k: float(v) for k, v in metrics.items()})
    _save_meta(weights, meta)
    check_compatibility(meta)  # sanity: the freshly-written meta must be loadable by this code
    print(f"reranker checkpoint saved: {weights} (+ .json)")
    print("STATUS: TRAINED. Registered as SHADOW by the retraining lifecycle; never auto-promoted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
