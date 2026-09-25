"""Model registry with shadow-deploy, promotion, and rollback (dependency-free).

A production model is NEVER self-modifying and is NEVER auto-promoted. The lifecycle is explicit:

    register(candidate)  -> state=SHADOW      (evaluated alongside prod, not used for decisions)
    promote(version)     -> state=PRODUCTION  (requires meeting gate criteria; recorded with reason)
    rollback()           -> restore previous PRODUCTION version (kept in history)

The registry is a JSON file on disk (models/registry/registry.json) listing versions + a pointer to
the current production version. Model weights live beside it as opaque artifacts; this module only
manages metadata + the state machine. Promotion demands the caller pass an evaluation report that
clears the gate — the registry will not promote a model that regresses safety-critical metrics.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class ModelState(str, Enum):
    SHADOW = "SHADOW"
    PRODUCTION = "PRODUCTION"
    ARCHIVED = "ARCHIVED"
    REJECTED = "REJECTED"


# Gate: a candidate may be promoted only if it does NOT regress these safety-critical metrics vs the
# current production model (higher is better; critical_recall must never drop).
class PromotionGate:
    MIN_CRITICAL_RECALL = 0.99          # must not miss critical/red-flag conditions
    MAX_CRITICAL_RECALL_REGRESSION = 0.0  # zero tolerance for critical-recall regression

    @staticmethod
    def evaluate(candidate_metrics: Dict[str, float],
                 prod_metrics: Optional[Dict[str, float]]) -> (bool, str):
        cr = candidate_metrics.get("critical_recall", 0.0)
        if cr < PromotionGate.MIN_CRITICAL_RECALL:
            return False, f"critical_recall {cr:.4f} < required {PromotionGate.MIN_CRITICAL_RECALL}"
        if prod_metrics is not None:
            prod_cr = prod_metrics.get("critical_recall", 0.0)
            if cr < prod_cr - PromotionGate.MAX_CRITICAL_RECALL_REGRESSION:
                return False, f"critical_recall regressed {prod_cr:.4f} -> {cr:.4f}"
        return True, "gate cleared"


@dataclass
class ModelEntry:
    version: str
    state: ModelState
    created_utc: str
    dataset_snapshot_id: str
    metrics: Dict[str, float] = field(default_factory=dict)
    notes: str = ""
    code_sha: str = ""            # training-code SHA the model was produced from (provenance)
    dataset_version: str = ""     # human-readable dataset version (mirrors snapshot id)
    approved_by: str = ""         # WHO promoted it to production (empty until promoted)
    approved_at: str = ""         # WHEN it was promoted (UTC ISO; empty until promoted)

    def as_dict(self) -> dict:
        return {
            "version": self.version, "state": self.state.value, "created_utc": self.created_utc,
            "dataset_snapshot_id": self.dataset_snapshot_id, "dataset_version": self.dataset_version,
            "metrics": self.metrics, "notes": self.notes, "code_sha": self.code_sha,
            "approved_by": self.approved_by, "approved_at": self.approved_at,
        }


class ModelRegistry:
    def __init__(self, registry_dir: Path) -> None:
        self._dir = Path(registry_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / "registry.json"
        self._entries: Dict[str, ModelEntry] = {}
        self._production: Optional[str] = None
        self._prod_history: List[str] = []
        self._load()

    def _load(self) -> None:
        if not self._path.is_file():
            return
        data = json.loads(self._path.read_text(encoding="utf-8"))
        for e in data.get("entries", []):
            self._entries[e["version"]] = ModelEntry(
                version=e["version"], state=ModelState(e["state"]), created_utc=e["created_utc"],
                dataset_snapshot_id=e.get("dataset_snapshot_id", ""), metrics=e.get("metrics", {}),
                notes=e.get("notes", ""), code_sha=e.get("code_sha", ""),
                dataset_version=e.get("dataset_version", ""),
                approved_by=e.get("approved_by", ""), approved_at=e.get("approved_at", ""),
            )
        self._production = data.get("production")
        self._prod_history = list(data.get("production_history", []))

    def _save(self) -> None:
        data = {
            "entries": [e.as_dict() for e in self._entries.values()],
            "production": self._production,
            "production_history": self._prod_history,
        }
        self._path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def register(self, version: str, dataset_snapshot_id: str, metrics: Dict[str, float],
                 notes: str = "", code_sha: str = "", dataset_version: str = "") -> ModelEntry:
        """Register a new model in SHADOW state. Never auto-promotes."""
        if version in self._entries:
            raise ValueError(f"version {version} already registered")
        entry = ModelEntry(
            version=version, state=ModelState.SHADOW,
            created_utc=datetime.now(timezone.utc).isoformat(),
            dataset_snapshot_id=dataset_snapshot_id, metrics=dict(metrics), notes=notes,
            code_sha=code_sha, dataset_version=dataset_version or dataset_snapshot_id,
        )
        self._entries[version] = entry
        self._save()
        return entry

    def promote(self, version: str, *, approved_by: str) -> ModelEntry:
        """Promote a SHADOW model to PRODUCTION. Requires BOTH:
          (1) an explicit human approver (`approved_by`, non-empty), and
          (2) clearing the safety gate (critical-recall floor + no regression vs current prod).
        Never auto-promotes; a promotion is always an explicit, attributed human action."""
        entry = self._entries.get(version)
        if entry is None:
            raise ValueError(f"unknown version {version}")
        if not approved_by or not str(approved_by).strip():
            raise PermissionError("promotion requires an explicit approver (approved_by); "
                                  "models are never auto-promoted.")
        prod_metrics = self._entries[self._production].metrics if self._production else None
        ok, reason = PromotionGate.evaluate(entry.metrics, prod_metrics)
        if not ok:
            entry.state = ModelState.REJECTED
            entry.notes = (entry.notes + f" | promotion rejected: {reason}").strip(" |")
            self._save()
            raise PermissionError(f"promotion blocked: {reason}")
        if self._production and self._production != version:
            self._entries[self._production].state = ModelState.ARCHIVED
            self._prod_history.append(self._production)
        entry.state = ModelState.PRODUCTION
        entry.approved_by = str(approved_by).strip()
        entry.approved_at = datetime.now(timezone.utc).isoformat()
        self._production = version
        self._save()
        return entry

    def rollback(self) -> Optional[ModelEntry]:
        """Restore the previous production version. Returns the restored entry or None."""
        if not self._prod_history:
            return None
        prev = self._prod_history.pop()
        if self._production and self._production in self._entries:
            self._entries[self._production].state = ModelState.ARCHIVED
        self._entries[prev].state = ModelState.PRODUCTION
        self._production = prev
        self._save()
        return self._entries[prev]

    def production_version(self) -> Optional[str]:
        return self._production

    def get(self, version: str) -> Optional[ModelEntry]:
        return self._entries.get(version)

    def list_versions(self) -> List[ModelEntry]:
        return list(self._entries.values())
