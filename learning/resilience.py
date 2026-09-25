"""Failure-mode degradation + rare-disease mode (PHASE 1 PART O+Q).

Every optional 5,000-diagnosis component can fail (ML ranker unavailable, retrieval index missing,
ontology snapshot corrupt, LLM timeout/unavailable, incompatible checkpoint). None of these may
crash a clinical decision — each degrades to a safe fallback. This module centralizes the
degradation policy + a rare-disease-mode decision.

The invariant under EVERY failure mode: the deterministic + safety layers still run, so a
must-not-miss diagnosis is never lost because an optional ML component failed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, List, Optional, Sequence


class ComponentStatus(str, Enum):
    OK = "OK"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"
    INCOMPATIBLE = "INCOMPATIBLE"


@dataclass
class DegradationReport:
    retrieval_index: ComponentStatus = ComponentStatus.OK
    ml_reranker: ComponentStatus = ComponentStatus.OK
    ontology: ComponentStatus = ComponentStatus.OK
    llm: ComponentStatus = ComponentStatus.OK
    checkpoint: ComponentStatus = ComponentStatus.OK
    notes: List[str] = field(default_factory=list)

    @property
    def degraded(self) -> bool:
        return any(s != ComponentStatus.OK for s in
                   (self.retrieval_index, self.ml_reranker, self.ontology, self.llm, self.checkpoint))

    def as_dict(self) -> dict:
        return {
            "retrieval_index": self.retrieval_index.value, "ml_reranker": self.ml_reranker.value,
            "ontology": self.ontology.value, "llm": self.llm.value, "checkpoint": self.checkpoint.value,
            "degraded": self.degraded, "notes": list(self.notes),
        }


def safe_call(fn: Callable, *args, fallback=None, on_error: Optional[Callable] = None, **kwargs):
    """Run fn(*args, **kwargs); on ANY exception return `fallback` and (optionally) record via
    on_error(exc). Never raises. Used to wrap every optional-component call in the pipeline."""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        if on_error is not None:
            try:
                on_error(exc)
            except Exception:
                pass
        return fallback


# --- rare-disease mode (PART O) --------------------------------------------------------------

@dataclass(frozen=True)
class RareModeDecision:
    activate: bool
    reason: str


def decide_rare_mode(*, top_score: float, curated_top_score: float,
                     n_curated_candidates: int,
                     known_threshold: float = 0.6) -> RareModeDecision:
    """Activate rare-disease expansion when the common/curated candidates do NOT adequately explain
    the patient (no confident curated match), so the long tail (Tier-3) is searched. Rare disease is
    NEVER placed at the top purely for rarity, and NEVER excluded purely for rarity — activation only
    widens retrieval; ranking still decides order on evidence."""
    if curated_top_score >= known_threshold:
        return RareModeDecision(False, "A curated candidate confidently explains the presentation; "
                                       "no rare expansion needed.")
    if n_curated_candidates == 0 or top_score < known_threshold:
        return RareModeDecision(True, "No confident curated explanation; expanding to rare/ontology "
                                      "long tail (surfaced as possibilities, not forced to top).")
    return RareModeDecision(False, "Curated candidates adequate.")
