"""Runtime monitoring for the shadow/production ranker (dependency-free).

Tracks lightweight, PHI-free counters so drift and OOD rates are observable without logging any
patient data: total cases, OOD rate, uncalibrated rate, safety-drop count, and a rolling agreement
rate between the shadow model and the current production model. If shadow disagreement or OOD rate
crosses a threshold, `alerts()` surfaces it — a human decides on promotion/rollback, never the code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class MonitorState:
    n_cases: int = 0
    n_ood: int = 0
    n_uncalibrated: int = 0
    n_safety_dropped: int = 0
    n_shadow_disagree: int = 0

    OOD_RATE_ALERT = 0.20
    DISAGREE_RATE_ALERT = 0.30

    def observe(self, *, is_ood: bool, calibrated: bool, safety_dropped: int,
                shadow_disagrees: bool = False) -> None:
        self.n_cases += 1
        if is_ood:
            self.n_ood += 1
        if not calibrated:
            self.n_uncalibrated += 1
        if safety_dropped > 0:
            self.n_safety_dropped += 1
        if shadow_disagrees:
            self.n_shadow_disagree += 1

    def rates(self) -> Dict[str, float]:
        n = max(1, self.n_cases)
        return {
            "ood_rate": self.n_ood / n,
            "uncalibrated_rate": self.n_uncalibrated / n,
            "safety_drop_rate": self.n_safety_dropped / n,
            "shadow_disagree_rate": self.n_shadow_disagree / n,
        }

    def alerts(self) -> List[str]:
        r = self.rates()
        out: List[str] = []
        if r["ood_rate"] > self.OOD_RATE_ALERT:
            out.append(f"HIGH OOD rate {r['ood_rate']:.2f} > {self.OOD_RATE_ALERT}: distribution shift?")
        if r["shadow_disagree_rate"] > self.DISAGREE_RATE_ALERT:
            out.append(f"HIGH shadow/prod disagreement {r['shadow_disagree_rate']:.2f}: review before promotion.")
        return out

    def as_dict(self) -> dict:
        d = {"n_cases": self.n_cases, **self.rates(), "alerts": self.alerts()}
        return d
