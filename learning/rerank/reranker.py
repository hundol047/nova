"""Deep clinical reranker: Top-100~200 -> Top-20~30 (dependency-free default; torch-optional).

Scores each retrieved candidate from a combination of clinical signals and truncates to the top
`keep` for the LLM. The dependency-free scorer is a transparent weighted combination; a torch
reranker (learning/rerank/model_torch.py-style) can replace the scorer without changing the
interface. Either way, the SAFETY INVARIANT holds: safety_mandatory candidates are always retained
regardless of score (Safety > ML).

Inputs per candidate: retrieval score, embedding cosine, supporting/contradictory evidence counts,
objective-finding support, temporal consistency, risk-factor match, and the safety flag.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from learning._torch import torch_available


@dataclass
class RerankInput:
    concept_id: str
    name: str
    tier: str = ""
    category: str = ""
    retrieval_score: float = 0.0
    embedding_cosine: float = 0.0
    supporting_evidence: int = 0
    contradictory_evidence: int = 0
    objective_support: float = 0.0     # decisive lab/imaging support in [0,1]
    temporal_consistency: float = 0.0  # onset/course consistency in [0,1]
    risk_factor_match: int = 0
    is_critical: bool = False
    safety_mandatory: bool = False


@dataclass
class RerankedCandidate:
    concept_id: str
    name: str
    rank: int
    score: float
    is_critical: bool
    safety_mandatory: bool
    retained_reason: str = "score"     # 'score' | 'safety_mandatory'

    def as_dict(self) -> dict:
        return {
            "concept_id": self.concept_id, "name": self.name, "rank": self.rank,
            "score": round(self.score, 4), "is_critical": self.is_critical,
            "safety_mandatory": self.safety_mandatory, "retained_reason": self.retained_reason,
        }


@dataclass
class RerankResult:
    ranked: List[RerankedCandidate]
    backend: str                       # 'deterministic' | 'torch'
    kept: int
    dropped_nonmandatory: int
    notes: List[str] = field(default_factory=list)

    def concept_ids(self) -> List[str]:
        return [r.concept_id for r in self.ranked]


# Deterministic scorer weights (interpretable; the point is that a learned model CAN replace these,
# not that these are optimal).
_W = {
    "retrieval": 0.30, "embedding": 0.25, "supporting": 0.15, "objective": 0.20,
    "temporal": 0.05, "risk": 0.05,
}


def _deterministic_score(c: RerankInput) -> float:
    s = (_W["retrieval"] * c.retrieval_score
         + _W["embedding"] * max(0.0, c.embedding_cosine)
         + _W["supporting"] * min(1.0, 0.25 * c.supporting_evidence)
         + _W["objective"] * c.objective_support
         + _W["temporal"] * c.temporal_consistency
         + _W["risk"] * min(1.0, 0.25 * c.risk_factor_match))
    # contradictory evidence penalizes (but never below 0)
    s -= 0.15 * min(1.0, 0.25 * c.contradictory_evidence)
    return max(0.0, s)


class Reranker:
    def __init__(self, keep: int = 25, torch_model=None) -> None:
        self.keep = keep
        self._torch_model = torch_model  # optional; if provided, used for scoring

    def _score(self, c: RerankInput) -> float:
        if self._torch_model is not None and torch_available():
            try:
                import torch
                row = [c.retrieval_score, max(0.0, c.embedding_cosine),
                       min(1.0, 0.25 * c.supporting_evidence), c.objective_support,
                       c.temporal_consistency, min(1.0, 0.25 * c.risk_factor_match),
                       min(1.0, 0.25 * c.contradictory_evidence)]
                self._torch_model.eval()
                with torch.no_grad():
                    return float(self._torch_model(torch.tensor([row], dtype=torch.float32)).item())
            except Exception:
                pass  # fall back to deterministic on any torch error
        return _deterministic_score(c)

    def rerank(self, candidates: Sequence[RerankInput]) -> RerankResult:
        scored = [(c, self._score(c)) for c in candidates]
        # Safety-mandatory candidates are ALWAYS retained regardless of score. Rank them within the
        # top band (by score) but they can never be truncated out.
        mandatory = [(c, s) for (c, s) in scored if c.safety_mandatory]
        normal = [(c, s) for (c, s) in scored if not c.safety_mandatory]
        normal.sort(key=lambda t: -t[1])
        mandatory.sort(key=lambda t: -t[1])

        # keep budget: mandatory always kept; fill the rest from normal up to `keep`.
        keep_normal = max(0, self.keep - len(mandatory))
        kept_normal = normal[:keep_normal]
        dropped = len(normal) - len(kept_normal)

        # merge: interleave so critical/mandatory float to the top band, then by score.
        merged = mandatory + kept_normal
        merged.sort(key=lambda t: (0 if (t[0].safety_mandatory or t[0].is_critical) else 1, -t[1]))

        ranked: List[RerankedCandidate] = []
        for i, (c, s) in enumerate(merged, 1):
            ranked.append(RerankedCandidate(
                concept_id=c.concept_id, name=c.name, rank=i, score=s,
                is_critical=c.is_critical, safety_mandatory=c.safety_mandatory,
                retained_reason="safety_mandatory" if c.safety_mandatory else "score",
            ))
        backend = "torch" if (self._torch_model is not None and torch_available()) else "deterministic"
        notes = []
        if mandatory:
            notes.append(f"{len(mandatory)} safety-mandatory candidate(s) retained regardless of "
                         "score (Safety > ML).")
        return RerankResult(ranked=ranked, backend=backend, kept=len(merged),
                            dropped_nonmandatory=dropped, notes=notes)
