"""Out-of-distribution (OOD) detection (dependency-free).

If a presentation is far from the training distribution, the ranker's scores are untrustworthy and
must be flagged so the engine defers to deterministic reasoning + explicit uncertainty rather than
a confident-looking ML ordering. This uses a simple, transparent distance-to-training-centroid
score (Mahalanobis-lite with per-dimension variance) — no torch, fully reproducible.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Sequence


@dataclass
class OODDetector:
    mean: List[float] = field(default_factory=list)
    var: List[float] = field(default_factory=list)
    threshold: float = 0.0
    fitted: bool = False

    def fit(self, vectors: Sequence[Sequence[float]], quantile: float = 0.975) -> "OODDetector":
        if not vectors:
            self.fitted = False
            return self
        dim = len(vectors[0])
        n = len(vectors)
        mean = [0.0] * dim
        for v in vectors:
            for i in range(dim):
                mean[i] += v[i]
        mean = [m / n for m in mean]
        var = [0.0] * dim
        for v in vectors:
            for i in range(dim):
                var[i] += (v[i] - mean[i]) ** 2
        var = [(s / max(1, n - 1)) + 1e-6 for s in var]  # epsilon to avoid div0
        self.mean, self.var = mean, var
        dists = sorted(self._dist(v) for v in vectors)
        idx = min(len(dists) - 1, int(quantile * len(dists)))
        self.threshold = dists[idx]
        self.fitted = True
        return self

    def _dist(self, v: Sequence[float]) -> float:
        if not self.mean:
            return 0.0
        acc = 0.0
        for i in range(min(len(v), len(self.mean))):
            acc += (v[i] - self.mean[i]) ** 2 / self.var[i]
        return math.sqrt(acc)

    def score(self, v: Sequence[float]) -> float:
        """Normalized OOD score in [0,1] (1 = at/above the fitted threshold distance)."""
        if not self.fitted or self.threshold <= 0:
            return 0.0
        return max(0.0, min(1.0, self._dist(v) / self.threshold))

    def is_ood(self, v: Sequence[float]) -> bool:
        if not self.fitted:
            return False
        return self._dist(v) > self.threshold

    def as_dict(self) -> dict:
        return {"mean": self.mean, "var": self.var, "threshold": self.threshold, "fitted": self.fitted}

    @classmethod
    def from_dict(cls, d: dict) -> "OODDetector":
        return cls(
            mean=list(d.get("mean", [])),
            var=list(d.get("var", [])),
            threshold=float(d.get("threshold", 0.0)),
            fitted=bool(d.get("fitted", False)),
        )
