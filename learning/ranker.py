"""Disease candidate RANKER (torch-optional).

Contract (safety-critical — enforced here and in tests):
  1. Input is an ALREADY-SAFETY-VETTED candidate list. The ranker RE-ORDERS it and attaches scores.
  2. The ranker MUST NOT:
       - include any candidate whose `safety_excluded` is True (it drops them, never resurrects),
       - demote a red-flag / critical candidate below a non-critical one (critical always floats to
         the top band), or
       - emit a calibrated percentage when no calibrator is fitted.
  3. Priority is Safety Guard > ML Ranker > LLM. The ranker cannot auto-confirm; it only informs
     ordering. Whatever consumes RankerOutput must still run the deterministic safety checks.

Two backends:
  - LinearRanker: dependency-free weighted combination of the candidate features. Always available;
    used as the default and as a deterministic fallback / for local testing.
  - TorchRanker (in model_torch.py): loaded lazily only if torch is installed. Same output contract.
"""

from __future__ import annotations

from typing import List, Optional

from learning.calibration import Calibrator
from learning.ood import OODDetector
from learning.schemas import (
    CandidateFeature,
    RankedCandidate,
    RankerInput,
    RankerOutput,
)


def _enforce_safety_ordering(
    scored: List[tuple],  # (CandidateFeature, raw_score)
) -> List[tuple]:
    """Drop safety-excluded candidates and guarantee critical/red-flag candidates rank in the top
    band regardless of learned score. Within a band we sort by score desc."""
    kept = [(c, s) for (c, s) in scored if not c.safety_excluded]
    critical = [(c, s) for (c, s) in kept if c.is_critical or c.is_red_flag]
    normal = [(c, s) for (c, s) in kept if not (c.is_critical or c.is_red_flag)]
    critical.sort(key=lambda t: -t[1])
    normal.sort(key=lambda t: -t[1])
    return critical + normal


class LinearRanker:
    """Deterministic weighted-sum ranker. Weights are simple and interpretable; the point of the
    ML pipeline is that these CAN be replaced by a learned model, but safety ordering is applied on
    top of ANY backend's raw scores."""

    def __init__(
        self,
        w_evidence: float = 0.6,
        w_retrieval: float = 0.25,
        w_prior: float = 0.15,
        model_version: str = "linear-fallback-v1",
        calibrator: Optional[Calibrator] = None,
        ood: Optional[OODDetector] = None,
    ) -> None:
        self.w_evidence = w_evidence
        self.w_retrieval = w_retrieval
        self.w_prior = w_prior
        self.model_version = model_version
        self.calibrator = calibrator or Calibrator()
        self.ood = ood or OODDetector()

    def _raw_score(self, c: CandidateFeature) -> float:
        return (
            self.w_evidence * c.base_evidence_score
            + self.w_retrieval * c.retrieval_score
            + self.w_prior * c.prior
        )

    def rank(self, inp: RankerInput) -> RankerOutput:
        notes: List[str] = []
        ood_score = self.ood.score(inp.feature_vector) if self.ood.fitted else 0.0
        is_ood = self.ood.is_ood(inp.feature_vector) if self.ood.fitted else False
        if is_ood:
            notes.append("Presentation flagged OUT-OF-DISTRIBUTION; ranker scores are low-trust. "
                         "Defer to deterministic reasoning and explicit uncertainty.")

        scored = [(c, self._raw_score(c)) for c in inp.candidates]
        ordered = _enforce_safety_ordering(scored)

        dropped = len(inp.candidates) - len(ordered)
        if dropped > 0:
            notes.append(f"Dropped {dropped} safety-excluded candidate(s); ranker never resurrects them.")

        calibrated = self.calibrator.fitted and not is_ood
        if self.calibrator.fitted and is_ood:
            notes.append("Calibrator suppressed for OOD case (no trustworthy probability).")

        ranked: List[RankedCandidate] = []
        for rank_idx, (c, raw) in enumerate(ordered, start=1):
            cal = self.calibrator.calibrated(raw) if calibrated else None
            ranked.append(
                RankedCandidate(
                    concept_id=c.concept_id,
                    rank=rank_idx,
                    raw_score=raw,
                    calibrated_score=cal,
                    is_red_flag=c.is_red_flag,
                    is_critical=c.is_critical,
                )
            )

        if not self.calibrator.fitted:
            notes.append("No fitted calibrator: scores are ordinal only, NOT probabilities. "
                         "UI must show a qualitative confidence, never a percent.")

        return RankerOutput(
            case_id=inp.case_id,
            ranked=ranked,
            ood_score=ood_score,
            is_ood=is_ood,
            calibrated=calibrated,
            model_version=self.model_version,
            notes=notes,
        )


def get_default_ranker() -> LinearRanker:
    """The always-available, dependency-free ranker. Training may produce a TorchRanker that is
    loaded from the model registry; absent that, this is used."""
    return LinearRanker()
