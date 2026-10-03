"""Baseline performance lock + multi-metric promotion gate (PHASE 1 PART K+L).

Freezes the current architecture as BASELINE and evaluates a CANDIDATE (e.g. the 5,000-disease
retrieval architecture) against it. A candidate may be promoted ONLY if it does not regress the
safety-critical metrics — a Top-1 improvement alone can NEVER promote a model that regresses
critical recall / critical miss rate / top-3 / top-5, or that catastrophically regresses any
specialty or subgroup.

This is dependency-free and metric-driven. Thresholds are declared here and are NOT to be adjusted
after seeing a candidate's results (that would be tuning-to-the-eval); they are set from clinical
safety principle (critical recall must not drop, critical miss must not rise).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class MetricSet:
    """A comparable metric bundle for an architecture on a fixed eval set."""

    top_1: float = 0.0
    top_3: float = 0.0
    top_5: float = 0.0
    top_10: float = 0.0
    recall_at_20: float = 0.0
    recall_at_50: float = 0.0
    recall_at_100: float = 0.0
    critical_recall_at_5: float = 0.0
    critical_recall_at_20: float = 0.0
    critical_recall_at_100: float = 0.0
    critical_miss_rate: float = 0.0
    ood_flag_rate: float = 0.0
    mean_latency_ms: float = 0.0
    per_specialty_recall_at_100: Dict[str, float] = field(default_factory=dict)
    per_subgroup_recall_at_100: Dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict:
        d = {k: getattr(self, k) for k in (
            "top_1", "top_3", "top_5", "top_10", "recall_at_20", "recall_at_50", "recall_at_100",
            "critical_recall_at_5", "critical_recall_at_20", "critical_recall_at_100",
            "critical_miss_rate", "ood_flag_rate", "mean_latency_ms")}
        d["per_specialty_recall_at_100"] = dict(self.per_specialty_recall_at_100)
        d["per_subgroup_recall_at_100"] = dict(self.per_subgroup_recall_at_100)
        return d


class PromotionDecision(str):
    PROMOTE = "PROMOTE"
    SHADOW = "SHADOW"
    REJECT = "REJECT"


@dataclass
class MultiMetricGate:
    """Configurable safety-first promotion gate. Thresholds are principle-driven, not eval-tuned."""

    # Absolute floors the candidate must meet.
    min_critical_recall_at_100: float = 0.99
    max_critical_miss_rate: float = 0.01
    # Regression tolerances vs baseline (candidate may not drop these by more than tol).
    max_critical_recall_regression: float = 0.0     # zero tolerance on critical recall
    max_critical_miss_increase: float = 0.0         # zero tolerance on critical miss increase
    max_top3_regression: float = 0.02
    max_top5_regression: float = 0.02
    max_specialty_regression: float = 0.10          # per-specialty recall@100 catastrophic threshold
    max_subgroup_regression: float = 0.10

    def evaluate(self, candidate: MetricSet, baseline: MetricSet) -> Tuple[str, List[str]]:
        reasons: List[str] = []

        # 1) absolute safety floors
        if candidate.critical_recall_at_100 < self.min_critical_recall_at_100:
            reasons.append(f"critical_recall@100 {candidate.critical_recall_at_100:.4f} < floor "
                           f"{self.min_critical_recall_at_100}")
        if candidate.critical_miss_rate > self.max_critical_miss_rate:
            reasons.append(f"critical_miss_rate {candidate.critical_miss_rate:.4f} > max "
                           f"{self.max_critical_miss_rate}")

        # 2) safety-critical regression vs baseline (zero tolerance)
        if candidate.critical_recall_at_100 < baseline.critical_recall_at_100 - self.max_critical_recall_regression:
            reasons.append(f"critical_recall@100 regressed {baseline.critical_recall_at_100:.4f} -> "
                           f"{candidate.critical_recall_at_100:.4f}")
        if candidate.critical_miss_rate > baseline.critical_miss_rate + self.max_critical_miss_increase:
            reasons.append(f"critical_miss_rate increased {baseline.critical_miss_rate:.4f} -> "
                           f"{candidate.critical_miss_rate:.4f}")

        # 3) accuracy regression (Top-1-only improvement can NEVER carry a top-3/top-5 regression)
        if candidate.top_3 < baseline.top_3 - self.max_top3_regression:
            reasons.append(f"top_3 regressed {baseline.top_3:.4f} -> {candidate.top_3:.4f}")
        if candidate.top_5 < baseline.top_5 - self.max_top5_regression:
            reasons.append(f"top_5 regressed {baseline.top_5:.4f} -> {candidate.top_5:.4f}")

        # 4) no catastrophic per-specialty / per-subgroup regression
        for spec, base_v in baseline.per_specialty_recall_at_100.items():
            cand_v = candidate.per_specialty_recall_at_100.get(spec, 0.0)
            if cand_v < base_v - self.max_specialty_regression:
                reasons.append(f"specialty '{spec}' recall@100 regressed {base_v:.3f} -> {cand_v:.3f}")
        for sub, base_v in baseline.per_subgroup_recall_at_100.items():
            cand_v = candidate.per_subgroup_recall_at_100.get(sub, 0.0)
            if cand_v < base_v - self.max_subgroup_regression:
                reasons.append(f"subgroup '{sub}' recall@100 regressed {base_v:.3f} -> {cand_v:.3f}")

        if reasons:
            # Any safety/critical failure -> REJECT; otherwise a non-safety regression -> keep SHADOW.
            safety_fail = any(("critical" in r or "floor" in r or "miss_rate" in r) for r in reasons)
            return (PromotionDecision.REJECT if safety_fail else PromotionDecision.SHADOW), reasons
        return PromotionDecision.PROMOTE, ["all gate criteria satisfied"]


@dataclass
class BaselineComparison:
    baseline: MetricSet
    candidate: MetricSet
    decision: str
    reasons: List[str]

    def as_dict(self) -> dict:
        return {
            "baseline": self.baseline.as_dict(),
            "candidate": self.candidate.as_dict(),
            "decision": self.decision,
            "reasons": self.reasons,
        }


def compare(baseline: MetricSet, candidate: MetricSet,
            gate: Optional[MultiMetricGate] = None) -> BaselineComparison:
    gate = gate or MultiMetricGate()
    decision, reasons = gate.evaluate(candidate, baseline)
    return BaselineComparison(baseline=baseline, candidate=candidate, decision=decision, reasons=reasons)
