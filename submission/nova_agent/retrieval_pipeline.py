"""High-recall competition retrieval -> lightweight deterministic rerank -> safety reinjection.

Three explicit, separately-sized stages, matching the competition architecture spec:

    DiseaseCatalog (real: 34 Tier-1 deep + 1,246 Tier-2 structured [+ any operator-supplied
    Tier-3 terminology snapshot]; test fixtures may add thousands of synthetic Tier-3 concepts --
    never conflated with the real count)
        |
        v  Stage 1: RETRIEVE  (retrieval_top_k, recommended 100-200)
    nova_agent.open_world.OpenWorldRetriever.retrieve_multi_signal() -- already-tested, already
    dependency-free multi-signal fusion (chief complaint + symptoms + history + imaging + codes),
    unchanged here. This module does not reimplement retrieval; it only widens how many hits the
    caller asks for and adds the next two stages on top.
        |
        v  Stage 2: RERANK  (rerank_top_k, recommended 20-30)
    lightweight_rerank() -- a transparent, deterministic, non-ML scorer (retrieval match strength +
    match-kind confidence + curation depth + a small dangerous/urgency nudge). Explicitly NOT deep
    learning; the module and its output type are named accordingly.
        |
        v  Stage 3: SAFETY REINJECTION
    a `dangerous: true` concept from the Stage-1 pool that reranking would otherwise drop is put
    back, swapping out the weakest non-dangerous survivor so the stage stays bounded at
    (rerank_top_k + a small documented overflow only when there are more dangerous drops than
    non-dangerous survivors to swap -- an extremely rare edge case for a real catalog).

Dependency-light by construction: only nova_agent.open_world / nova_agent.ontology, which are
themselves stdlib-only (dataclasses, enum, typing). No torch, no embeddings, no network, no
database -- CPU-friendly and offline, safe for the competition submission.

This pipeline governs ONLY the ontology-sourced ("onto::...") portion of a turn's candidate pool.
It never touches the deterministic 34-disease KB path (symptom_match / risk_match / safety_candidate
/ objective_finding) that candidate_generator.py already builds independently -- see that module's
`_broaden_with_open_world()` for how the two are combined, and its `trimmable_only_sources` handling
for why an ontology-sourced candidate here can never displace a must-not-miss or evidenced Tier-1
diagnosis from the FINAL pool regardless of what this pipeline does upstream."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence

from nova_agent.open_world import OpenWorldRetriever, RetrievedCandidate

# Stage 2 scoring weights. A transparent weighted sum, not a learned model -- every term traces to
# a real signal already present on the concept/match (never a fabricated clinical claim).
_MATCH_KIND_WEIGHT = {
    "exact": 1.0, "code": 0.95, "alias": 0.9, "hierarchy": 0.55, "token": 0.6, "fuzzy": 0.4,
}
_CURATION_BONUS = {"DEEP": 0.15, "STRUCTURED": 0.05, "NOT_CURATED": 0.0}
_DANGEROUS_BONUS = 0.12
_CRITICAL_URGENCY_BONUS = 0.08


@dataclass
class RerankedCandidate:
    """One Stage-2/3 survivor, with WHY it survived (for provenance/debugging, never shown to the
    clinician as a calibrated probability -- `rerank_score` is a ranking/match-strength number,
    exactly like OpenWorldRetriever's own `match_score` it is derived from)."""

    concept: object  # nova_agent.ontology.models.ClinicalConcept
    retrieval_score: float
    rerank_score: float
    match_kind: str
    reasons: List[str] = field(default_factory=list)


def retrieve_high_recall(retriever: OpenWorldRetriever, *, chief_complaint: str = "",
                          symptoms: Sequence[str] = (), history: Sequence[str] = (),
                          imaging_concepts: Sequence[str] = (), codes: Sequence[tuple] = (),
                          retrieval_top_k: int = 150) -> List[RetrievedCandidate]:
    """Stage 1: high-recall retrieval. A thin, explicit wrapper over the existing, already-tested
    OpenWorldRetriever.retrieve_multi_signal() -- the only thing this function changes is asking for
    a MUCH larger `limit` (100-200, configurable) than a final candidate bundle would ever need, so
    a true long-tail diagnosis has room to survive into the pool before any narrowing happens."""
    if retrieval_top_k <= 0:
        return []
    return retriever.retrieve_multi_signal(
        chief_complaint=chief_complaint, symptoms=symptoms, history=history,
        imaging_concepts=imaging_concepts, codes=codes, limit=retrieval_top_k,
    )


def _rerank_score(candidate: RetrievedCandidate) -> float:
    concept = candidate.concept
    score = candidate.match_score * _MATCH_KIND_WEIGHT.get(candidate.match_kind, 0.5)
    score += _CURATION_BONUS.get(concept.curation_status, 0.0)
    if concept.dangerous is True:
        score += _DANGEROUS_BONUS
    if concept.urgency == "CRITICAL":
        score += _CRITICAL_URGENCY_BONUS
    return score


def lightweight_rerank(retrieved: List[RetrievedCandidate], *,
                        rerank_top_k: int = 25) -> List[RerankedCandidate]:
    """Stage 2 + Stage 3. Deterministic, non-ML: see module docstring for the scoring terms. Never
    silently drops a `dangerous: true` Stage-1 candidate -- Stage 3 (safety reinjection) puts it
    back in place of the weakest non-dangerous survivor. Explicitly bounded at `rerank_top_k` in the
    common case; only exceeds it when dangerous drops outnumber non-dangerous survivors to swap
    (documented, extremely rare in practice for a real catalog -- most retrieval hits are routine)."""
    if rerank_top_k <= 0 or not retrieved:
        return []

    scored = [
        RerankedCandidate(concept=c.concept, retrieval_score=c.match_score,
                           rerank_score=round(_rerank_score(c), 4), match_kind=c.match_kind,
                           reasons=[f"retrieval:{c.match_kind}"])
        for c in retrieved
    ]
    scored.sort(key=lambda rc: -rc.rerank_score)
    kept = scored[:rerank_top_k]
    kept_ids = {rc.concept.concept_id for rc in kept}

    dangerous_missing = [
        rc for rc in scored[rerank_top_k:]
        if rc.concept.dangerous is True and rc.concept.concept_id not in kept_ids
    ]
    if dangerous_missing:
        non_dangerous_kept = sorted(
            (rc for rc in kept if not rc.concept.dangerous), key=lambda rc: rc.rerank_score
        )
        for missing in dangerous_missing:
            if non_dangerous_kept:
                weakest = non_dangerous_kept.pop(0)
                kept.remove(weakest)
            missing.reasons.append("safety_reinjection")
            kept.append(missing)
        kept.sort(key=lambda rc: -rc.rerank_score)

    return kept


def retrieve_and_rerank(retriever: OpenWorldRetriever, *, chief_complaint: str = "",
                         symptoms: Sequence[str] = (), history: Sequence[str] = (),
                         imaging_concepts: Sequence[str] = (), codes: Sequence[tuple] = (),
                         retrieval_top_k: int = 150, rerank_top_k: int = 25) -> List[RerankedCandidate]:
    """The full 3-stage pipeline as one call -- what candidate_generator.py's competition-retrieval
    step actually invokes each turn."""
    retrieved = retrieve_high_recall(
        retriever, chief_complaint=chief_complaint, symptoms=symptoms, history=history,
        imaging_concepts=imaging_concepts, codes=codes, retrieval_top_k=retrieval_top_k,
    )
    return lightweight_rerank(retrieved, rerank_top_k=rerank_top_k)
