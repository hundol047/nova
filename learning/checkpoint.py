"""Model checkpoint save/load + compatibility guard (torch-optional at import).

A checkpoint bundles everything an inference process needs to safely load a trained ranker and
KNOW it is compatible with the current code/feature schema:

    model weights (torch state_dict, saved separately as <name>.pt)
    model config (hidden size, dropout, per-candidate feature layout)
    input_dim / feature_version / dataset_version / schema_version / model_arch
    training code SHA (git) + metrics + created_at (UTC ISO)

The metadata sidecar (<name>.json) is plain JSON and can be inspected WITHOUT torch. Loading the
weights requires torch. `check_compatibility()` refuses a checkpoint whose feature_version /
input_dim / schema_version / model_arch does not match what the running code expects — a stale or
mismatched model must never be silently loaded into a clinical inference path.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from learning.encoder import FEATURE_DIM

# Bump these when the corresponding contract changes; a checkpoint carrying an older value is
# refused by check_compatibility() rather than silently loaded.
FEATURE_VERSION = "feat.v1"      # encoder feature layout
SCHEMA_VERSION = "sched.v1"      # TrainingExample / candidate-row schema
MODEL_ARCH = "candidate_scorer_mlp.v1"

# Per-candidate model input = encoder feature vector (FEATURE_DIM) + [base_evidence, retrieval, prior]
PER_CANDIDATE_EXTRA = 3
MODEL_INPUT_DIM = FEATURE_DIM + PER_CANDIDATE_EXTRA


def training_code_sha() -> str:
    """Best-effort git SHA of the current tree; 'unknown' if git is unavailable."""
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5)
        return out.stdout.strip() if out.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


@dataclass
class CheckpointMeta:
    model_version: str
    input_dim: int
    hidden: int
    dropout: float
    feature_version: str = FEATURE_VERSION
    schema_version: str = SCHEMA_VERSION
    model_arch: str = MODEL_ARCH
    dataset_version: str = ""
    code_sha: str = field(default_factory=training_code_sha)
    metrics: Dict[str, float] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict:
        return {
            "model_version": self.model_version,
            "input_dim": self.input_dim,
            "hidden": self.hidden,
            "dropout": self.dropout,
            "feature_version": self.feature_version,
            "schema_version": self.schema_version,
            "model_arch": self.model_arch,
            "dataset_version": self.dataset_version,
            "code_sha": self.code_sha,
            "metrics": self.metrics,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CheckpointMeta":
        return cls(
            model_version=d["model_version"],
            input_dim=int(d["input_dim"]),
            hidden=int(d.get("hidden", 64)),
            dropout=float(d.get("dropout", 0.1)),
            feature_version=d.get("feature_version", ""),
            schema_version=d.get("schema_version", ""),
            model_arch=d.get("model_arch", ""),
            dataset_version=d.get("dataset_version", ""),
            code_sha=d.get("code_sha", ""),
            metrics=dict(d.get("metrics", {})),
            created_at=d.get("created_at", ""),
        )


class CheckpointIncompatibleError(RuntimeError):
    pass


def check_compatibility(meta: CheckpointMeta) -> None:
    """Raise CheckpointIncompatibleError unless the checkpoint matches the running code's contract.

    Guards: feature_version, input_dim, schema_version, model_arch. This is the fail-safe that
    keeps a stale/mismatched model out of the inference path."""
    problems = []
    if meta.feature_version != FEATURE_VERSION:
        problems.append(f"feature_version {meta.feature_version!r} != {FEATURE_VERSION!r}")
    if meta.schema_version != SCHEMA_VERSION:
        problems.append(f"schema_version {meta.schema_version!r} != {SCHEMA_VERSION!r}")
    if meta.model_arch != MODEL_ARCH:
        problems.append(f"model_arch {meta.model_arch!r} != {MODEL_ARCH!r}")
    if meta.input_dim != MODEL_INPUT_DIM:
        problems.append(f"input_dim {meta.input_dim} != {MODEL_INPUT_DIM}")
    if problems:
        raise CheckpointIncompatibleError(
            "Refusing to load checkpoint (incompatible with running code): " + "; ".join(problems)
        )


def meta_path(weights_path: Path) -> Path:
    return Path(weights_path).with_suffix(".json")


def save_meta(weights_path: Path, meta: CheckpointMeta) -> Path:
    p = meta_path(weights_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(meta.as_dict(), indent=2) + "\n", encoding="utf-8")
    return p


def load_meta(weights_path: Path) -> CheckpointMeta:
    return CheckpointMeta.from_dict(json.loads(meta_path(weights_path).read_text(encoding="utf-8")))


# ---- torch-dependent save/load (imported lazily so this module needs no torch) --------------

def save_checkpoint(model, weights_path: Path, meta: CheckpointMeta) -> Path:
    """Save torch weights (<name>.pt) + JSON metadata sidecar. Requires torch."""
    from learning._torch import require_torch
    torch = require_torch()
    weights_path = Path(weights_path)
    weights_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), str(weights_path))
    save_meta(weights_path, meta)
    return weights_path


def load_checkpoint(weights_path: Path):
    """Load metadata, ENFORCE compatibility, then rebuild the model and load weights.

    Returns (model, meta). Raises CheckpointIncompatibleError before touching weights if the
    checkpoint does not match the running code. Requires torch."""
    from learning._torch import require_torch
    from learning.model_torch import build_mlp
    torch = require_torch()
    weights_path = Path(weights_path)
    meta = load_meta(weights_path)
    check_compatibility(meta)  # fail-safe BEFORE loading weights
    model = build_mlp(meta.input_dim, hidden=meta.hidden, dropout=meta.dropout)
    state = torch.load(str(weights_path), map_location="cpu")
    model.load_state_dict(state)
    model.eval()
    return model, meta
