"""Reranker checkpoint metadata + compatibility guard (torch-optional at import).

Per-component checkpoint: each learned component (reranker, and by the same pattern the retrieval
encoders) records its own model/dataset/feature/ontology/code/arch versions + metrics, and refuses
to load into incompatible running code. Mirrors learning/checkpoint.py for the ranker.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from learning.rerank.model_torch import RERANK_ARCH, RERANK_FEATURE_VERSION, RERANK_INPUT_DIM

RERANK_SCHEMA_VERSION = "rerank-sched.v1"
# The ontology/catalog version the reranker's features were derived against. Bumped when the disease
# universe schema changes in a way that would invalidate a trained reranker.
ONTOLOGY_VERSION = "onto.5k.v1"


def _code_sha() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5)
        return out.stdout.strip() if out.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


@dataclass
class RerankerCheckpointMeta:
    model_version: str
    input_dim: int = RERANK_INPUT_DIM
    hidden: int = 32
    dropout: float = 0.1
    feature_version: str = RERANK_FEATURE_VERSION
    schema_version: str = RERANK_SCHEMA_VERSION
    model_arch: str = RERANK_ARCH
    ontology_version: str = ONTOLOGY_VERSION
    dataset_version: str = ""
    code_sha: str = field(default_factory=_code_sha)
    metrics: Dict[str, float] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict:
        return {
            "model_version": self.model_version, "input_dim": self.input_dim, "hidden": self.hidden,
            "dropout": self.dropout, "feature_version": self.feature_version,
            "schema_version": self.schema_version, "model_arch": self.model_arch,
            "ontology_version": self.ontology_version, "dataset_version": self.dataset_version,
            "code_sha": self.code_sha, "metrics": self.metrics, "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RerankerCheckpointMeta":
        return cls(
            model_version=d["model_version"], input_dim=int(d.get("input_dim", RERANK_INPUT_DIM)),
            hidden=int(d.get("hidden", 32)), dropout=float(d.get("dropout", 0.1)),
            feature_version=d.get("feature_version", ""), schema_version=d.get("schema_version", ""),
            model_arch=d.get("model_arch", ""), ontology_version=d.get("ontology_version", ""),
            dataset_version=d.get("dataset_version", ""), code_sha=d.get("code_sha", ""),
            metrics=dict(d.get("metrics", {})), created_at=d.get("created_at", ""),
        )


class RerankerIncompatibleError(RuntimeError):
    pass


def check_compatibility(meta: RerankerCheckpointMeta) -> None:
    problems = []
    if meta.feature_version != RERANK_FEATURE_VERSION:
        problems.append(f"feature_version {meta.feature_version!r} != {RERANK_FEATURE_VERSION!r}")
    if meta.schema_version != RERANK_SCHEMA_VERSION:
        problems.append(f"schema_version {meta.schema_version!r} != {RERANK_SCHEMA_VERSION!r}")
    if meta.model_arch != RERANK_ARCH:
        problems.append(f"model_arch {meta.model_arch!r} != {RERANK_ARCH!r}")
    if meta.ontology_version != ONTOLOGY_VERSION:
        problems.append(f"ontology_version {meta.ontology_version!r} != {ONTOLOGY_VERSION!r}")
    if meta.input_dim != RERANK_INPUT_DIM:
        problems.append(f"input_dim {meta.input_dim} != {RERANK_INPUT_DIM}")
    if problems:
        raise RerankerIncompatibleError("Refusing to load reranker checkpoint: " + "; ".join(problems))


def meta_path(weights_path: Path) -> Path:
    return Path(weights_path).with_suffix(".json")


def save_meta(weights_path: Path, meta: RerankerCheckpointMeta) -> Path:
    p = meta_path(weights_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(meta.as_dict(), indent=2) + "\n", encoding="utf-8")
    return p


def load_meta(weights_path: Path) -> RerankerCheckpointMeta:
    return RerankerCheckpointMeta.from_dict(json.loads(meta_path(weights_path).read_text(encoding="utf-8")))
