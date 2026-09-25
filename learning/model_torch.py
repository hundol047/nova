"""Neural ranker backend — loaded ONLY when torch is installed (optional).

Defines a small MLP scorer over the encoder feature vector plus per-candidate features, and a
TorchRanker that produces the SAME RankerOutput contract as LinearRanker (including the mandatory
safety-ordering guarantee). Importing this module does not import torch at module load; torch is
required lazily inside the functions/classes that need it.
"""

from __future__ import annotations

from typing import List, Optional

from learning._torch import require_torch, torch_available
from learning.calibration import Calibrator
from learning.ood import OODDetector
from learning.ranker import _enforce_safety_ordering
from learning.schemas import CandidateFeature, RankedCandidate, RankerInput, RankerOutput


def build_mlp(input_dim: int, hidden: int = 64):
    """Construct the scorer network. Requires torch."""
    torch = require_torch()
    import torch.nn as nn

    class CandidateScorer(nn.Module):
        def __init__(self, in_dim: int, h: int):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(in_dim, h),
                nn.ReLU(),
                nn.Dropout(0.1),
                nn.Linear(h, h // 2),
                nn.ReLU(),
                nn.Linear(h // 2, 1),
            )

        def forward(self, x):
            return self.net(x).squeeze(-1)

    return CandidateScorer(input_dim, hidden)


class TorchRanker:
    """Wraps a trained torch scorer. `candidate_feature_fn` maps (feature_vector, CandidateFeature)
    to the model's per-candidate input row (kept explicit so training/inference agree)."""

    def __init__(
        self,
        model,
        model_version: str,
        calibrator: Optional[Calibrator] = None,
        ood: Optional[OODDetector] = None,
    ) -> None:
        self._model = model
        self.model_version = model_version
        self.calibrator = calibrator or Calibrator()
        self.ood = ood or OODDetector()

    @staticmethod
    def available() -> bool:
        return torch_available()

    def _candidate_row(self, feature_vector: List[float], c: CandidateFeature) -> List[float]:
        return list(feature_vector) + [c.base_evidence_score, c.retrieval_score, c.prior]

    def rank(self, inp: RankerInput) -> RankerOutput:
        torch = require_torch()
        notes: List[str] = []
        is_ood = self.ood.is_ood(inp.feature_vector) if self.ood.fitted else False
        ood_score = self.ood.score(inp.feature_vector) if self.ood.fitted else 0.0
        if is_ood:
            notes.append("Presentation flagged OUT-OF-DISTRIBUTION; deferring trust to deterministic layer.")

        rows = [self._candidate_row(inp.feature_vector, c) for c in inp.candidates]
        self._model.eval()
        with torch.no_grad():
            raw = self._model(torch.tensor(rows, dtype=torch.float32)).tolist() if rows else []
        scored = list(zip(inp.candidates, raw))
        ordered = _enforce_safety_ordering(scored)

        calibrated = self.calibrator.fitted and not is_ood
        ranked: List[RankedCandidate] = []
        for rank_idx, (c, s) in enumerate(ordered, start=1):
            cal = self.calibrator.calibrated(s) if calibrated else None
            ranked.append(RankedCandidate(
                concept_id=c.concept_id, rank=rank_idx, raw_score=float(s),
                calibrated_score=cal, is_red_flag=c.is_red_flag, is_critical=c.is_critical,
            ))
        if not self.calibrator.fitted:
            notes.append("No fitted calibrator: ordinal scores only, not probabilities.")
        return RankerOutput(
            case_id=inp.case_id, ranked=ranked, ood_score=ood_score, is_ood=is_ood,
            calibrated=calibrated, model_version=self.model_version, notes=notes,
        )
