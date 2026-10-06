"""Error taxonomy + coverage-gap review queue (PHASE 1 PART M+N).

When a clinician's adjudicated final diagnosis does not match what the pipeline surfaced, classify
WHERE the pipeline failed so improvement is targeted, not blind:

    RETRIEVAL_MISS          true dx not even in the Top-100 retrieval pool
    RANKING_MISS            in Top-100 but not in the Top-5 reranked bundle
    REASONING_MISS          in Top-5 but the LLM/final reasoning dropped it
    PIPELINE_INTEGRATION_MISS  LLM produced it correctly but safety/final output lost it
    COVERAGE_GAP            true dx is not in the 5,000+ disease universe at all

COVERAGE_GAP feeds a REVIEW QUEUE for a human curator — the KB is NEVER auto-edited. All records are
de-identified / PHI-free (only concept ids + ranks + the miss class).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List, Optional, Sequence


class MissClass(str, Enum):
    RETRIEVAL_MISS = "RETRIEVAL_MISS"
    RANKING_MISS = "RANKING_MISS"
    REASONING_MISS = "REASONING_MISS"
    PIPELINE_INTEGRATION_MISS = "PIPELINE_INTEGRATION_MISS"
    COVERAGE_GAP = "COVERAGE_GAP"
    NO_MISS = "NO_MISS"


def classify_miss(*, true_concept_id: str, in_universe: bool,
                  retrieval_top100_ids: Sequence[str], reranked_top5_ids: Sequence[str],
                  llm_output_ids: Sequence[str], final_output_ids: Sequence[str]) -> MissClass:
    """Classify where the true diagnosis was lost. Order matters: earliest failing stage wins."""
    if not in_universe:
        return MissClass.COVERAGE_GAP
    if true_concept_id in final_output_ids:
        return MissClass.NO_MISS
    if true_concept_id not in retrieval_top100_ids:
        return MissClass.RETRIEVAL_MISS
    if true_concept_id not in reranked_top5_ids:
        return MissClass.RANKING_MISS
    if true_concept_id not in llm_output_ids:
        return MissClass.REASONING_MISS
    # was in the LLM output but lost before the final clinician-facing output
    return MissClass.PIPELINE_INTEGRATION_MISS


@dataclass
class CoverageGapItem:
    """A PHI-free coverage-gap review-queue entry (a real dx outside the 5,000 universe)."""

    gap_id: str
    observed_at: str
    query_fingerprint: str          # non-reversible fingerprint (no raw text)
    proposed_name: str              # clinician-provided dx name (curator reviews)
    status: str = "PENDING_REVIEW"  # PENDING_REVIEW | ADD_ALIAS | ADD_TIER3 | ADD_TIER2 | ADD_TIER1 | REJECTED
    reviewer: str = ""
    decided_at: str = ""

    def as_row(self) -> dict:
        return {
            "gap_id": self.gap_id, "observed_at": self.observed_at,
            "query_fingerprint": self.query_fingerprint, "proposed_name": self.proposed_name,
            "status": self.status, "reviewer": self.reviewer, "decided_at": self.decided_at,
        }


VALID_REVIEW_ACTIONS = {"ADD_ALIAS", "ADD_TIER3", "ADD_TIER2", "ADD_TIER1", "REJECTED"}


class CoverageGapQueue:
    """A human-in-the-loop review queue. NEVER edits the KB automatically — it only records
    proposals and a curator's decision. Applying a decision to the catalog is a separate, manual,
    reviewed step (out of scope here by design)."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = Path(path) if path else None
        self._items: List[CoverageGapItem] = []
        if self._path and self._path.is_file():
            for line in self._path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    d = json.loads(line)
                    self._items.append(CoverageGapItem(**d))

    def enqueue(self, *, query_fingerprint: str, proposed_name: str) -> CoverageGapItem:
        import uuid
        item = CoverageGapItem(
            gap_id=str(uuid.uuid4()), observed_at=datetime.now(timezone.utc).isoformat(),
            query_fingerprint=query_fingerprint, proposed_name=proposed_name)
        self._items.append(item)
        self._persist()
        return item

    def review(self, gap_id: str, action: str, reviewer: str) -> CoverageGapItem:
        if action not in VALID_REVIEW_ACTIONS:
            raise ValueError(f"invalid review action {action!r}")
        if not reviewer:
            raise ValueError("review requires a reviewer (human accountability)")
        for it in self._items:
            if it.gap_id == gap_id:
                it.status = action
                it.reviewer = reviewer
                it.decided_at = datetime.now(timezone.utc).isoformat()
                self._persist()
                return it
        raise KeyError(gap_id)

    def pending(self) -> List[CoverageGapItem]:
        return [it for it in self._items if it.status == "PENDING_REVIEW"]

    def _persist(self) -> None:
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text("\n".join(json.dumps(it.as_row()) for it in self._items) + "\n",
                              encoding="utf-8")
