"""Coverage-gap analytics (PHI-free, dependency-free).

When the open-world assessment returns UNKNOWN_PRESENTATION or POSSIBLE_UNMAPPED_CONDITION, that is
a signal about WHERE the catalog is thin. We want to learn from that WITHOUT storing any patient
data. This module turns such an event into a PHI-free `coverage_gap_events` row: a stable
FINGERPRINT of the query terms (salted hash — not reversible to the text) plus the outcome and the
best (still-weak) candidate. Aggregated over time, the fingerprints reveal recurring gaps to
prioritize for curation; no free text or identifier is ever persisted.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

# Self-contained tokenizer (do NOT import nova_agent — learning/ stays independent of the reasoning
# package so it runs in a torch-only environment without pydantic). Mirrors the ontology normalizer:
# NFKC, lowercase, strip Latin accents, drop punctuation, collapse whitespace, CJK preserved.
_PUNCT_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)
_WS_RE = re.compile(r"\s+", flags=re.UNICODE)


def tokens(text: str) -> List[str]:
    if not text:
        return []
    t = unicodedata.normalize("NFKC", text).strip().lower()
    t = "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))
    t = _PUNCT_RE.sub(" ", t)
    t = _WS_RE.sub(" ", t).strip()
    return [tok for tok in t.split(" ") if tok]

# A fixed salt namespaces the fingerprint so it is not a bare hash of the query (mild pre-image
# hardening). This is analytics de-identification, not a security boundary.
_FINGERPRINT_NAMESPACE = "nova-coverage-gap-v1"

# Outcomes we treat as coverage gaps worth recording.
GAP_OUTCOMES = frozenset({"UNKNOWN_PRESENTATION", "POSSIBLE_UNMAPPED_CONDITION"})


def query_fingerprint(query: str) -> str:
    """Order-independent, non-reversible fingerprint of the query's normalized token set. Two
    presentations described with the same clinical terms map to the same fingerprint, enabling
    frequency analysis without keeping the text."""
    toks = sorted(set(tokens(query)))
    basis = _FINGERPRINT_NAMESPACE + "|" + " ".join(toks)
    return "cg_" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:20]


@dataclass(frozen=True)
class CoverageGapEvent:
    gap_event_id: str
    observed_at: str
    outcome: str
    query_fingerprint: str
    top_candidate_concept_id: Optional[str]
    top_candidate_score: Optional[float]

    def as_row(self) -> dict:
        return {
            "gap_event_id": self.gap_event_id,
            "observed_at": self.observed_at,
            "outcome": self.outcome,
            "query_fingerprint": self.query_fingerprint,
            "top_candidate_concept_id": self.top_candidate_concept_id,
            "top_candidate_score": self.top_candidate_score,
        }


def build_gap_event(
    *,
    query: str,
    outcome: str,
    top_candidate_concept_id: Optional[str] = None,
    top_candidate_score: Optional[float] = None,
) -> Optional[CoverageGapEvent]:
    """Return a PHI-free coverage-gap event, or None if the outcome is not a gap (nothing to log).
    NOTE: `query` is used ONLY to derive the fingerprint; it is never stored."""
    if outcome not in GAP_OUTCOMES:
        return None
    return CoverageGapEvent(
        gap_event_id=str(uuid.uuid4()),
        observed_at=datetime.now(timezone.utc).isoformat(),
        outcome=outcome,
        query_fingerprint=query_fingerprint(query),
        top_candidate_concept_id=top_candidate_concept_id,
        top_candidate_score=top_candidate_score,
    )


def rank_gaps(events: List[CoverageGapEvent], top_n: int = 20) -> List[dict]:
    """Aggregate events by fingerprint to surface the most frequent coverage gaps for curation
    prioritization. PHI-free: operates only on fingerprints + outcomes."""
    counts: dict = {}
    for e in events:
        key = e.query_fingerprint
        c = counts.setdefault(key, {"query_fingerprint": key, "count": 0, "outcomes": {}})
        c["count"] += 1
        c["outcomes"][e.outcome] = c["outcomes"].get(e.outcome, 0) + 1
    ordered = sorted(counts.values(), key=lambda d: -d["count"])
    return ordered[:top_n]
