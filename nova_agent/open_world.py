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

    def retrieve_by_code(self, system: str, code: str) -> List[RetrievedCandidate]:
        """Direct code match (SNOMED/ICD). A high-confidence retrieval signal independent of text."""
        out = []
        for concept in self._catalog.map_external_code(system, code):
            out.append(RetrievedCandidate(
                concept=concept, match_score=0.97, match_kind="code",
                tier=concept.tier.value, curation_status=concept.curation_status,
                is_curated=concept.curation_status in ("DEEP", "STRUCTURED"),
            ))
        return out

    def _expand_hierarchy(self, candidates: List[RetrievedCandidate],
                          per_parent: int = 2) -> List[RetrievedCandidate]:
        """Add ontology CHILDREN of matched concepts as lower-scored siblings, so a match on a
        parent concept surfaces its more-specific descendants too (a retrieval-recall boost, not a
        ranking claim). Children are scored below their parent and tagged match_kind='hierarchy'."""
        extra: List[RetrievedCandidate] = []
        seen = {c.concept.concept_id for c in candidates}
        for cand in candidates[:8]:  # bound the expansion
            for child in self._catalog.get_children(cand.concept.concept_id)[:per_parent]:
                if child.concept_id in seen:
                    continue
                seen.add(child.concept_id)
                extra.append(RetrievedCandidate(
                    concept=child, match_score=max(0.4, cand.match_score - 0.2),
                    match_kind="hierarchy", tier=child.tier.value,
                    curation_status=child.curation_status,
                    is_curated=child.curation_status in ("DEEP", "STRUCTURED"),
                ))
        return extra

    def retrieve_multi_signal(self, *, chief_complaint: str = "", symptoms: Sequence[str] = (),
                              history: Sequence[str] = (), lab_concepts: Sequence[str] = (),
                              imaging_concepts: Sequence[str] = (),
                              codes: Sequence[tuple] = (), limit: int = 20,
                              expand_hierarchy: bool = True) -> List[RetrievedCandidate]:
        """Fuse MULTIPLE retrieval signals into one deduplicated, best-score-per-concept candidate
        list. Signals: chief complaint text, symptom concepts, history concepts, lab/imaging finding
        concepts, and external codes (system, code). Optionally expands the ontology hierarchy of the
        strongest matches. This raises retrieval RECALL (getting the true diagnosis into the pool),
        which is distinct from ranking — the deep re-ranker/LLM/safety layers decide final order.

        Every signal is text/code lookup against the catalog; there is no external call. A weak or
        empty signal simply contributes nothing (never fabricates)."""
        best: dict = {}

        def offer(cands: List[RetrievedCandidate]) -> None:
            for c in cands:
                cur = best.get(c.concept.concept_id)
                if cur is None or c.match_score > cur.match_score:
                    best[c.concept.concept_id] = c

        if chief_complaint:
            offer(self.retrieve(chief_complaint, limit=limit))
        for term in list(symptoms) + list(history) + list(lab_concepts) + list(imaging_concepts):
            if term and len(str(term).strip()) >= MIN_QUERY_SIGNAL_CHARS:
                offer(self.retrieve(str(term), limit=max(5, limit // 2)))
        for entry in codes:
            try:
                system, code = entry
            except (ValueError, TypeError):
                continue
            offer(self.retrieve_by_code(str(system), str(code)))

        merged = list(best.values())
        if expand_hierarchy and merged:
            merged.extend(self._expand_hierarchy(sorted(merged, key=lambda c: -c.match_score)))
            # de-dup again after expansion (children may already have been offered)
            dedup: dict = {}
            for c in merged:
                cur = dedup.get(c.concept.concept_id)
                if cur is None or c.match_score > cur.match_score:
                    dedup[c.concept.concept_id] = c
            merged = list(dedup.values())

        merged.sort(key=lambda c: (-c.match_score, c.concept.canonical_name))
        return merged[:limit]

    def assess_multi_signal(self, *, chief_complaint: str = "", symptoms: Sequence[str] = (),
                            history: Sequence[str] = (), lab_concepts: Sequence[str] = (),
                            imaging_concepts: Sequence[str] = (), codes: Sequence[tuple] = (),
                            limit: int = 20, rare_fallback: bool = True) -> OpenWorldAssessment:
        """Open-world classification over FUSED signals, with a rare-disease fallback: if no
        curated candidate is confident enough, retry the rare/ontology path before concluding.
        UNKNOWN_PRESENTATION is still a permitted final outcome — we never force a label."""
        query_repr = chief_complaint or " ".join(symptoms) or " ".join(history)
        candidates = self.retrieve_multi_signal(
            chief_complaint=chief_complaint, symptoms=symptoms, history=history,
            lab_concepts=lab_concepts, imaging_concepts=imaging_concepts, codes=codes, limit=limit)

        if not candidates:
            if rare_fallback and query_repr:
                rare = self.retrieve_rare(query_repr, limit=limit)
                if rare:
                    return OpenWorldAssessment(
                        outcome=OpenWorldOutcome.POSSIBLE_UNMAPPED_CONDITION, query=query_repr,
                        candidates=rare,
                        rationale="No curated candidate matched the fused signals; rare/ontology "
                                  "retrieval surfaced possibilities (not confirmed).")
            if not query_repr or len(query_repr.strip()) < MIN_QUERY_SIGNAL_CHARS:
                return OpenWorldAssessment(outcome=OpenWorldOutcome.INSUFFICIENT_INFORMATION,
                                           query=query_repr,
                                           rationale="Too little signal to retrieve responsibly.")
            return OpenWorldAssessment(outcome=OpenWorldOutcome.UNKNOWN_PRESENTATION, query=query_repr,
                                       rationale="No plausible match across all signals; outside "
                                                 "known coverage. Escalate to human differential.")

        top = candidates[0]
        curated_confident = [c for c in candidates if c.is_curated and c.match_score >= KNOWN_MATCH_THRESHOLD]
        if curated_confident:
            outcome = OpenWorldOutcome.KNOWN_CONDITION
            rationale = (f"Confident curated match '{curated_confident[0].concept.canonical_name}' "
                         f"across fused signals.")
        elif top.match_score >= POSSIBLE_MATCH_THRESHOLD:
            outcome = OpenWorldOutcome.POSSIBLE_UNMAPPED_CONDITION
            rationale = (f"Candidates found but none confidently curated; highest "
                         f"'{top.concept.canonical_name}' ({top.tier}, {top.match_score:.2f}). "
                         "Treat as possible.")
        else:
            # weak matches only -> try rare path before declaring unknown
            if rare_fallback and query_repr:
                rare = self.retrieve_rare(query_repr, limit=limit)
                if rare and rare[0].match_score >= POSSIBLE_MATCH_THRESHOLD:
                    return OpenWorldAssessment(
                        outcome=OpenWorldOutcome.POSSIBLE_UNMAPPED_CONDITION, query=query_repr,
                        candidates=rare, rationale="Rare/ontology retrieval surfaced a possibility.")
            outcome = OpenWorldOutcome.UNKNOWN_PRESENTATION
            rationale = ("Only weak matches across all signals; prefer explicit uncertainty over a "
                         "low-confidence label.")
        return OpenWorldAssessment(outcome=outcome, query=query_repr, candidates=candidates,
                                   rationale=rationale)

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
