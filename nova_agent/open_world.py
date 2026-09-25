"""Open-world reasoning outcomes + LLM-diagnosis normalization (vNext PART A).

The 34-disease closed world forced every presentation into a known bucket. This module makes
"I don't confidently know this" a FIRST-CLASS result and gives the engine/adapter a safe way to:

  1. Classify a presentation into an open-world OUTCOME (see OpenWorldOutcome), rather than always
     asserting a KNOWN_CONDITION.
  2. Retrieve broad differential candidates (including rare conditions) from the DiseaseCatalog by
     free-text query, tagged with provenance (which tier / how it matched).
  3. Normalize an LLM's free-text diagnosis string to a canonical catalog concept, or explicitly
     mark it UNMAPPED_LLM_DIAGNOSIS when no confident concept exists -- we never silently coerce an
     LLM label into a nearby known disease.

Design constraints:
  - Dependency-free (stdlib dataclasses/enums). Safe to import anywhere, including the submission.
  - PURE / SIDE-EFFECT-FREE and ADDITIVE: this module does not modify differential.py, orchestrator,
    or the safety validator. It provides helpers those layers (or the competition adapter) MAY call.
    The existing engine's behavior contract is unchanged unless a caller opts in.
  - A lexical match score is NOT a diagnostic probability. Outcomes never emit a calibrated percent;
    they emit a qualitative confidence + the evidence for it. Calibration lives in learning/.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Sequence

from nova_agent.ontology.models import ClinicalConcept, ConceptMatch
from nova_agent.ontology.registry import DiseaseCatalog


class OpenWorldOutcome(str, Enum):
    """The four possible epistemic states of an open-world differential."""

    KNOWN_CONDITION = "KNOWN_CONDITION"
    # A confident match to a curated (Tier-1/2) concept.
    POSSIBLE_UNMAPPED_CONDITION = "POSSIBLE_UNMAPPED_CONDITION"
    # Candidates exist but only as Tier-3 ontology concepts / weak matches -> named but not curated.
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    # Too little signal to retrieve or rank anything meaningfully -> need more data, not a guess.
    UNKNOWN_PRESENTATION = "UNKNOWN_PRESENTATION"
    # We searched and found nothing that plausibly matches -> explicitly "outside known coverage".


# Confidence thresholds on the lexical/structural match score. These gate the OUTCOME, not a
# clinical probability. Deliberately conservative: we would rather say "possible/unknown" than
# over-claim KNOWN.
KNOWN_MATCH_THRESHOLD = 0.90       # exact/alias/code-strength match to a curated concept
POSSIBLE_MATCH_THRESHOLD = 0.55    # some lexical overlap, or a Tier-3-only match
MIN_QUERY_SIGNAL_CHARS = 3         # below this we cannot retrieve responsibly


@dataclass(frozen=True)
class RetrievedCandidate:
    """A catalog candidate with open-world provenance."""

    concept: ClinicalConcept
    match_score: float
    match_kind: str
    tier: str
    curation_status: str
    is_curated: bool

    @classmethod
    def from_match(cls, m: ConceptMatch) -> "RetrievedCandidate":
        return cls(
            concept=m.concept,
            match_score=m.score,
            match_kind=m.match_kind,
            tier=m.concept.tier.value,
            curation_status=m.concept.curation_status,
            is_curated=m.concept.curation_status in ("DEEP", "STRUCTURED"),
        )

    def as_dict(self) -> dict:
        return {
            "concept_id": self.concept.concept_id,
            "name": self.concept.canonical_name,
            "match_score": round(self.match_score, 4),
            "match_kind": self.match_kind,
            "tier": self.tier,
            "curation_status": self.curation_status,
            "is_curated": self.is_curated,
        }


@dataclass(frozen=True)
class OpenWorldAssessment:
    """Result of classifying a presentation/query against the open-world catalog."""

    outcome: OpenWorldOutcome
    query: str
    candidates: List[RetrievedCandidate] = field(default_factory=list)
    rationale: str = ""

    @property
    def top(self) -> Optional[RetrievedCandidate]:
        return self.candidates[0] if self.candidates else None

    def as_dict(self) -> dict:
        return {
            "outcome": self.outcome.value,
            "query": self.query,
            "rationale": self.rationale,
            "candidates": [c.as_dict() for c in self.candidates],
        }


@dataclass(frozen=True)
class NormalizedDiagnosis:
    """Result of normalizing an LLM's free-text diagnosis to a canonical concept.

    When `mapped` is False the outcome is UNMAPPED_LLM_DIAGNOSIS: the LLM's label is preserved
    verbatim in `raw_text` and is NEVER coerced into a nearby known disease. Downstream must treat
    it as an unverified free-text hypothesis, not a catalog diagnosis.
    """

    raw_text: str
    mapped: bool
    concept: Optional[ClinicalConcept] = None
    match_score: float = 0.0
    match_kind: str = "none"
    status: str = "UNMAPPED_LLM_DIAGNOSIS"  # or 'MAPPED'

    def as_dict(self) -> dict:
        return {
            "raw_text": self.raw_text,
            "mapped": self.mapped,
            "status": self.status,
            "concept_id": self.concept.concept_id if self.concept else None,
            "concept_name": self.concept.canonical_name if self.concept else None,
            "match_score": round(self.match_score, 4),
            "match_kind": self.match_kind,
        }


class OpenWorldRetriever:
    """Stateless helper over a DiseaseCatalog. Cheap to construct; holds no per-patient state."""

    def __init__(self, catalog: DiseaseCatalog) -> None:
        self._catalog = catalog

    # -- broad candidate retrieval (includes rare/Tier-3 conditions) -------
    def retrieve(self, query: str, limit: int = 15, fuzzy: bool = True) -> List[RetrievedCandidate]:
        matches = self._catalog.search_conditions(query, limit=limit, fuzzy=fuzzy)
        return [RetrievedCandidate.from_match(m) for m in matches]

    def retrieve_rare(self, query: str, limit: int = 15) -> List[RetrievedCandidate]:
        """Rare-disease path: return only NOT-deeply-curated candidates (Tier-2 structured or
        Tier-3 ontology). Used when the deep KB has no confident answer but the ontology might name
        the condition. These are surfaced as 'possible', never as confirmed."""
        cands = self.retrieve(query, limit=limit * 2)
        rare = [c for c in cands if c.tier != "TIER1_DEEP"]
        return rare[:limit]

    # -- open-world classification ----------------------------------------
    def assess(self, query: str, limit: int = 15) -> OpenWorldAssessment:
        q = (query or "").strip()
        if len(q) < MIN_QUERY_SIGNAL_CHARS:
            return OpenWorldAssessment(
                outcome=OpenWorldOutcome.INSUFFICIENT_INFORMATION,
                query=q,
                rationale="Query too short to retrieve responsibly; gather more clinical signal.",
            )
        candidates = self.retrieve(q, limit=limit)
        if not candidates:
            return OpenWorldAssessment(
                outcome=OpenWorldOutcome.UNKNOWN_PRESENTATION,
                query=q,
                rationale="No catalog concept plausibly matched; presentation is outside known "
                          "coverage. Escalate to human differential rather than force a label.",
            )
        top = candidates[0]
        if top.match_score >= KNOWN_MATCH_THRESHOLD and top.is_curated:
            outcome = OpenWorldOutcome.KNOWN_CONDITION
            rationale = (
                f"Confident match to curated {top.tier} concept "
                f"'{top.concept.canonical_name}' ({top.match_kind}, {top.match_score:.2f})."
            )
        elif top.match_score >= POSSIBLE_MATCH_THRESHOLD:
            outcome = OpenWorldOutcome.POSSIBLE_UNMAPPED_CONDITION
            rationale = (
                "Candidate(s) found but none is a confident curated match; treat as possible, "
                "not established. Highest is "
                f"'{top.concept.canonical_name}' ({top.tier}, {top.match_score:.2f})."
            )
        else:
            outcome = OpenWorldOutcome.UNKNOWN_PRESENTATION
            rationale = (
                "Only weak lexical matches; insufficient to name a condition. Prefer explicit "
                "uncertainty over a low-confidence label."
            )
        return OpenWorldAssessment(outcome=outcome, query=q, candidates=candidates, rationale=rationale)

    # -- LLM free-text diagnosis normalization ----------------------------
    def normalize_llm_diagnosis(self, raw_text: str) -> NormalizedDiagnosis:
        raw = (raw_text or "").strip()
        if len(raw) < MIN_QUERY_SIGNAL_CHARS:
            return NormalizedDiagnosis(raw_text=raw, mapped=False, status="UNMAPPED_LLM_DIAGNOSIS")
        matches = self._catalog.search_conditions(raw, limit=1, fuzzy=True)
        if matches and matches[0].score >= KNOWN_MATCH_THRESHOLD:
            m = matches[0]
            return NormalizedDiagnosis(
                raw_text=raw,
                mapped=True,
                concept=m.concept,
                match_score=m.score,
                match_kind=m.match_kind,
                status="MAPPED",
            )
        # No confident concept -> preserve verbatim, do NOT coerce to a nearby disease.
        return NormalizedDiagnosis(raw_text=raw, mapped=False, status="UNMAPPED_LLM_DIAGNOSIS")

    def normalize_many(self, raw_texts: Sequence[str]) -> List[NormalizedDiagnosis]:
        return [self.normalize_llm_diagnosis(t) for t in raw_texts]
