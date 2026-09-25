"""Score calibration (dependency-free).

Rule: N.O.V.A. must NEVER present a percentage/probability to a clinician unless it is CALIBRATED.
Raw ranker scores are not probabilities. A Calibrator maps raw scores -> calibrated probabilities
using a fitted, monotonic isotonic-style mapping. Until fitted, `calibrated()` returns None and the
ranker reports calibrated=False so the UI shows a qualitative label instead of a fake number.

Isotonic regression here is implemented with a small stdlib pool-adjacent-violators (PAV) routine —
no numpy/sklearn — because the pipeline must run without heavy deps.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple


def _pav(scores: Sequence[float], targets: Sequence[float]) -> Tuple[List[float], List[float]]:
    """Pool-Adjacent-Violators isotonic fit. Returns (sorted_score_thresholds, fitted_values)."""
    pairs = sorted(zip(scores, targets), key=lambda p: p[0])
    xs = [p[0] for p in pairs]
    ys = [float(p[1]) for p in pairs]
    # weights and running blocks
    values = list(ys)
    weights = [1.0] * len(ys)
    i = 0
    # merge adjacent violators
    blocks_val: List[float] = []
    blocks_w: List[float] = []
    blocks_x: List[float] = []
    for k in range(len(xs)):
        blocks_val.append(values[k])
        blocks_w.append(weights[k])
        blocks_x.append(xs[k])
        while len(blocks_val) > 1 and blocks_val[-2] > blocks_val[-1]:
            v2, w2 = blocks_val.pop(), blocks_w.pop()
            x2 = blocks_x.pop()
            v1, w1 = blocks_val.pop(), blocks_w.pop()
            x1 = blocks_x.pop()
            w = w1 + w2
            blocks_val.append((v1 * w1 + v2 * w2) / w)
            blocks_w.append(w)
            blocks_x.append(x1)  # keep left threshold
    return blocks_x, blocks_val


@dataclass
class Calibrator:
    """Monotonic score->probability calibrator. `fitted` gates whether calibrated() returns a value."""

    thresholds: List[float] = field(default_factory=list)
    values: List[float] = field(default_factory=list)
    fitted: bool = False
    n_fit: int = 0

    MIN_FIT_SAMPLES = 30  # below this we do not trust a calibration -> stay uncalibrated (honesty)

    def fit(self, scores: Sequence[float], correct: Sequence[int]) -> "Calibrator":
        if len(scores) != len(correct):
            raise ValueError("scores and correct must be the same length")
        if len(scores) < self.MIN_FIT_SAMPLES:
            self.fitted = False
            self.n_fit = len(scores)
            return self
        thr, vals = _pav(scores, [float(c) for c in correct])
        self.thresholds = thr
        self.values = [max(0.0, min(1.0, v)) for v in vals]
        self.fitted = True
        self.n_fit = len(scores)
        return self

    def calibrated(self, raw_score: float) -> Optional[float]:
        """Return a calibrated probability in [0,1], or None if not fitted (never fake a number)."""
        if not self.fitted or not self.thresholds:
            return None
        idx = bisect_right(self.thresholds, raw_score) - 1
        idx = max(0, min(idx, len(self.values) - 1))
        return self.values[idx]

    def as_dict(self) -> dict:
        return {
            "fitted": self.fitted,
            "n_fit": self.n_fit,
            "thresholds": self.thresholds,
            "values": self.values,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Calibrator":
        c = cls(
            thresholds=list(d.get("thresholds", [])),
            values=list(d.get("values", [])),
            fitted=bool(d.get("fitted", False)),
            n_fit=int(d.get("n_fit", 0)),
        )
        return c
