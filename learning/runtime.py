"""Governed ML ranker runtime integration for HOSPITAL deployment (torch-optional).

This is the ONLY place the optional ML ranker is wired toward a live inference path, and it is
built so the ML subsystem can NEVER weaken clinical safety:

  MODES (from NovaConfig / env):
    - disabled            NOVA_ML_RANKER_ENABLED=false (default) -> ML never runs; None returned.
    - shadow (default on) NOVA_ML_RANKER_ENABLED=true, NOVA_ML_SHADOW_MODE=true -> ML ordering is
                          computed and AUDITED, but the clinician-facing result is unchanged.
    - active              NOVA_ML_RANKER_ENABLED=true, NOVA_ML_SHADOW_MODE=false, AND an approved
                          model at NOVA_ML_MODEL_PATH -> ML MAY re-order the candidate list, but:
                            * the deterministic Safety Guard result is applied AFTER ML (authoritative),
                            * a critical / red-flag candidate can never be dropped or demoted below a
                              non-critical one by ML,
                            * no calibrated probability is shown unless a calibrator is fitted,
                            * OOD cases fall back to the deterministic ordering.

  Priority invariant (unconditional): Safety Guard > ML Ranker > LLM.

  This module is NEVER imported by the competition submission (submission/ excludes learning/).
  It degrades gracefully: if torch or the model is missing, shadow/active silently fall back to the
  deterministic ordering and record why.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from learning._torch import torch_available
from learning.schemas import CandidateFeature, RankerInput, RankerOutput


def _bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class MLRuntimeConfig:
    enabled: bool = False
    shadow_mode: bool = True
    model_path: str = ""

    @classmethod
    def from_env(cls) -> "MLRuntimeConfig":
        return cls(
            enabled=_bool_env("NOVA_ML_RANKER_ENABLED", False),
            shadow_mode=_bool_env("NOVA_ML_SHADOW_MODE", True),
            model_path=os.environ.get("NOVA_ML_MODEL_PATH", "").strip(),
        )


@dataclass
class MLDecision:
    """The outcome of consulting the ML ranker for one case."""

    mode: str                       # 'disabled' | 'shadow' | 'active' | 'fallback'
    changed_clinical_output: bool   # True ONLY in active mode when ML actually reordered
    ml_output: Optional[RankerOutput] = None
    ordered_concept_ids: Optional[List[str]] = None  # ML ordering (audit / active reorder)
    notes: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "mode": self.mode,
            "changed_clinical_output": self.changed_clinical_output,
            "ordered_concept_ids": self.ordered_concept_ids,
            "ml_output": self.ml_output.as_dict() if self.ml_output else None,
            "notes": list(self.notes),
        }


class GovernedMLRuntime:
    """Loads (once) an approved model if configured, and consults it under the governance rules."""

    def __init__(self, config: Optional[MLRuntimeConfig] = None) -> None:
        self.config = config or MLRuntimeConfig.from_env()
        self._ranker = None
        self._load_error: Optional[str] = None
        self._loaded = False

    # -- model loading (lazy, guarded) ------------------------------------
    def _ensure_model(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not self.config.model_path:
            self._load_error = "no NOVA_ML_MODEL_PATH configured"
            return
        if not torch_available():
            self._load_error = "torch not installed"
            return
        try:
            from learning.model_torch import TorchRanker
            # TorchRanker.load enforces the checkpoint compatibility guard (feature/schema/arch/dim).
            self._ranker = TorchRanker.load(self.config.model_path)
        except Exception as exc:  # noqa: BLE001
            self._load_error = f"{type(exc).__name__}: {exc}"
            self._ranker = None

    # -- the single entry point the backend calls ------------------------
    def consult(self, case_id: str, feature_vector: Sequence[float],
                candidates: Sequence[CandidateFeature],
                deterministic_order: Sequence[str]) -> MLDecision:
        """Consult the ML ranker under governance. `deterministic_order` is the current
        clinician-facing candidate ordering (concept ids) produced by the deterministic + LLM +
        safety pipeline. Returns an MLDecision describing what (if anything) ML contributed."""
        if not self.config.enabled:
            return MLDecision(mode="disabled", changed_clinical_output=False,
                              notes=["ML ranker disabled (NOVA_ML_RANKER_ENABLED=false)."])

        self._ensure_model()
        if self._ranker is None:
            # Enabled but no usable model -> deterministic fallback (never crash the case).
            return MLDecision(mode="fallback", changed_clinical_output=False,
                              ordered_concept_ids=list(deterministic_order),
                              notes=[f"ML fallback to deterministic ordering ({self._load_error})."])

        ml_out = self._ranker.rank(RankerInput(case_id, list(feature_vector), list(candidates)))
        ml_order = [r.concept_id for r in ml_out.ranked]

        if self.config.shadow_mode:
            # SHADOW: compute + audit only; clinician-facing output is unchanged.
            return MLDecision(mode="shadow", changed_clinical_output=False,
                              ml_output=ml_out, ordered_concept_ids=ml_order,
                              notes=["SHADOW mode: ML ordering audited; clinical output unchanged."])

        if ml_out.is_ood:
            # OOD in active mode -> do not trust ML; keep deterministic ordering.
            return MLDecision(mode="active", changed_clinical_output=False,
                              ml_output=ml_out, ordered_concept_ids=list(deterministic_order),
                              notes=["ACTIVE mode but case is OOD; kept deterministic ordering."])

        # ACTIVE: ML may reorder, but safety ordering already floated critical/red-flag candidates
        # to the top band inside the ranker, and the deterministic Safety Guard is applied by the
        # caller AFTER this. We additionally guarantee here that every deterministic candidate is
        # preserved (ML can reorder, never drop).
        safe_order = _merge_preserving(ml_order, deterministic_order)
        changed = safe_order != list(deterministic_order)
        return MLDecision(mode="active", changed_clinical_output=changed,
                          ml_output=ml_out, ordered_concept_ids=safe_order,
                          notes=["ACTIVE mode: ML reordered; Safety Guard remains authoritative "
                                 "and is applied after ML."])


def _merge_preserving(ml_order: List[str], deterministic_order: Sequence[str]) -> List[str]:
    """ML ordering, then any deterministic candidates ML omitted, appended in their original order.
    Guarantees ML can reorder but NEVER drop a candidate the deterministic pipeline surfaced."""
    seen = set()
    merged: List[str] = []
    det = list(deterministic_order)
    det_set = set(det)
    for cid in ml_order:
        if cid in det_set and cid not in seen:
            merged.append(cid)
            seen.add(cid)
    for cid in det:
        if cid not in seen:
            merged.append(cid)
            seen.add(cid)
    return merged
