"""High-recall competition retrieval -> lightweight deterministic rerank -> safety reinjection.

Three explicit, separately-sized stages, matching the competition architecture spec:

    DiseaseCatalog (real: 34 Tier-1 deep + 1,246 Tier-2 structured [+ any operator-supplied
    Tier-3 terminology snapshot]; test fixtures may add thousands of synthetic Tier-3 concepts --
    never conflated with the real count)
        |
        v  Stage 1: RETRIEVE  (retrieval_top_k, recommended 100-200)
    Multiple BOUNDED, signal-typed sub-queries (chief complaint / symptoms / objective findings /
    history+risk / medications / imaging -- see `build_signal_queries()`), each independently
    retrieved via the existing, already-tested `OpenWorldRetriever.retrieve()` /
    `retrieve_by_code()`, then combined with Weighted Reciprocal Rank Fusion (`_rrf_fuse()`) --
    never one giant concatenated query. This module does not reimplement lexical matching; it only
    decides WHAT to query and HOW to combine independently-ranked results.
        |
        v  Stage 2: RERANK  (rerank_top_k, recommended 20-30)
    lightweight_rerank() -- a transparent, deterministic, non-ML scorer (retrieval match strength +
    match-kind confidence + curation depth + fused-rank prior). Explicitly NOT deep
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
from typing import Dict, List, Sequence, Tuple

from nova_agent.open_world import OpenWorldRetriever, RetrievedCandidate

# Stage 2 scoring weights. A transparent weighted sum, not a learned model -- every term traces to
# a real signal already present on the concept/match (never a fabricated clinical claim).
_MATCH_KIND_WEIGHT = {
    "exact": 1.0, "code": 0.95, "alias": 0.9, "hierarchy": 0.55, "token": 0.6, "fuzzy": 0.4,
}
_CURATION_BONUS = {"DEEP": 0.15, "STRUCTURED": 0.05, "NOT_CURATED": 0.0}
# Fused-retrieval-rank prior (Round M). Stage 1 returns candidates already ordered by weighted RRF,
# but the match-strength/curation/danger terms below ignored that order, so a concept retrieved 1st-5th
# (several independent signals agreeing) could be reranked below dangerous or deeply-curated concepts
# that merely matched one query and then be dropped before scoring. The prior decays smoothly with
# fused rank and is capped well below an exact-name match, so it reorders near-ties without letting
# position alone beat match strength.
_FUSED_RANK_BONUS_MAX = 0.35
_FUSED_RANK_HALF_LIFE = 5.0
_PROTECTED_FUSED_TOP = 8

# Stage 1 multi-query fusion. All weights/constants live here, not scattered as magic numbers.
# SIGNAL_WEIGHTS: how much each independently-retrieved signal type counts in the fused ranking.
# Objective findings (e.g. "critical_high potassium", "elevated troponin" -- ObjectiveFinding.
# evidence_label, already-computed real lab/vital interpretations, never fabricated here) and
# imaging findings carry more discriminating power than a generic symptom word, implemented
# GENERICALLY through signal TYPE (never a disease- or case-specific rule):
SIGNAL_WEIGHTS: Dict[str, float] = {
    "chief_complaint": 0.9,
    "symptom": 1.0,
    "objective_finding": 1.5,
    "imaging": 1.3,
    "history_risk": 0.6,
    "medication": 0.6,
    "code": 1.5,
}
# Reciprocal Rank Fusion constant (standard choice from the IR literature; not tuned per-case --
# larger K flattens the influence of rank position, smaller K sharpens it).
_RRF_K = 60
# Each signal-typed sub-query independently asks the catalog for this many candidates before
# fusion -- bounded so no single signal can dominate purely by returning more raw hits than
# another; the fused, deduplicated result is then truncated to the caller's retrieval_top_k.
_PER_SIGNAL_QUERY_LIMIT = 80


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


def build_signal_queries(*, chief_complaint: str = "", symptoms: Sequence[str] = (),
                          objective_finding_phrases: Sequence[str] = (),
                          history_risk: Sequence[str] = (), medications: Sequence[str] = (),
                          imaging_concepts: Sequence[str] = ()) -> List[Tuple[str, str]]:
    """Builds several BOUNDED, signal-typed queries (Q1 chief complaint, Q2 symptoms, Q3 objective
    findings, Q4 history/risk, Q5 medications, Q6 imaging) instead of concatenating unlimited
    patient text into one giant query. Every input here is already negation-scrubbed, positive-
    evidence-only text: `symptoms`/`history_risk`/`medications` come from
    clinical_presentation.ClinicalPresentation (built by build_clinical_presentation(), whose own
    docstring explains why `pertinent_negatives`/raw unsegmented history text are deliberately
    excluded -- e.g. "denies fever" can never surface here as a positive signal for "fever"), and
    `objective_finding_phrases` should be each abnormal ObjectiveFinding's own `evidence_label`
    (never a raw/normal lab value). This function does not itself interpret or filter for
    negation -- it trusts the caller to pass only already-positive signals, exactly like every
    other consumer of ClinicalPresentation already does."""
    queries: List[Tuple[str, str]] = []
    if chief_complaint.strip():
        queries.append(("chief_complaint", chief_complaint.strip()))
    if symptoms:
        queries.append(("symptom", " ".join(symptoms)))
    if objective_finding_phrases:
        queries.append(("objective_finding", " ".join(objective_finding_phrases)))
    if history_risk:
        queries.append(("history_risk", " ".join(history_risk)))
    if medications:
        queries.append(("medication", " ".join(medications)))
    if imaging_concepts:
        queries.append(("imaging", " ".join(imaging_concepts)))
    return queries


def _rrf_fuse(ranked_lists: List[Tuple[str, List[RetrievedCandidate]]],
              top_k: int) -> List[RetrievedCandidate]:
    """Weighted Reciprocal Rank Fusion across independently-retrieved, per-signal-type ranked
    lists: score(concept) = sum over signals s of SIGNAL_WEIGHTS[s] / (_RRF_K + rank_s(concept)).
    Transparent, deterministic, no learned parameters. A concept's own best-scoring RetrievedCandidate
    (across whichever signals found it) is kept for downstream provenance/rerank scoring; only its
    RANK POSITION within each signal's list feeds the fusion score."""
    fused_scores: Dict[str, float] = {}
    best_candidate: Dict[str, RetrievedCandidate] = {}
    for signal, ranked in ranked_lists:
        weight = SIGNAL_WEIGHTS.get(signal, 1.0)
        for rank, candidate in enumerate(ranked, start=1):
            cid = candidate.concept.concept_id
            fused_scores[cid] = fused_scores.get(cid, 0.0) + weight / (_RRF_K + rank)
            current_best = best_candidate.get(cid)
            if current_best is None or candidate.match_score > current_best.match_score:
                best_candidate[cid] = candidate

    ordered_ids = sorted(fused_scores, key=lambda cid: -fused_scores[cid])
    return [best_candidate[cid] for cid in ordered_ids[:top_k]]


def retrieve_high_recall(retriever: OpenWorldRetriever, *, chief_complaint: str = "",
                          symptoms: Sequence[str] = (), history: Sequence[str] = (),
                          imaging_concepts: Sequence[str] = (), codes: Sequence[tuple] = (),
                          objective_finding_phrases: Sequence[str] = (),
                          medications: Sequence[str] = (),
                          retrieval_top_k: int = 150) -> List[RetrievedCandidate]:
    """Stage 1: high-recall retrieval. Builds bounded, signal-typed sub-queries
    (build_signal_queries()) from whatever positive-evidence signals the caller has this turn,
    retrieves each independently (each still itself hierarchy-expanded via the existing, already-
    tested OpenWorldRetriever.retrieve()/retrieve_by_code()), and fuses them with weighted
    reciprocal rank fusion (_rrf_fuse()) into a single ranked pool bounded at `retrieval_top_k`
    (recommended 100-200) -- so a true long-tail diagnosis has room to survive before any narrowing
    happens, and a decisive objective finding or imaging result carries more weight than a generic
    symptom word without any disease-specific hardcoding.

    `history` is kept as the parameter name for backward compatibility with existing callers that
    pass a combined risk-factor/social-history list; it is treated as the "history_risk" signal.
    """
    if retrieval_top_k <= 0:
        return []

    # Only existing, observed canonical concepts; never infer a diagnosis or
    # generate free-form text. Bound expansion separately from the Top150 pool.
    from nova_agent.clinical_concepts import canonical_findings_for
    expanded = list(dict.fromkeys(c for text in (chief_complaint, *history, *medications)
                                 for c in canonical_findings_for(text)))[:12]
    symptom_terms = list(dict.fromkeys([*symptoms, *expanded]))
    signal_queries = build_signal_queries(
        chief_complaint=chief_complaint, symptoms=symptom_terms,
        objective_finding_phrases=objective_finding_phrases, history_risk=history,
        medications=medications, imaging_concepts=imaging_concepts,
    )
    ranked_lists: List[Tuple[str, List[RetrievedCandidate]]] = []
    for signal, text in signal_queries:
        hits = retriever.retrieve(text, limit=_PER_SIGNAL_QUERY_LIMIT, fuzzy=True)
        if hits:
            ranked_lists.append((signal, hits))
    for entry in codes:
        try:
            system, code = entry
        except (ValueError, TypeError):
            continue
        hits = retriever.retrieve_by_code(str(system), str(code))
        if hits:
            ranked_lists.append(("code", hits))

    if not ranked_lists:
        return []
    fused = _rrf_fuse(ranked_lists, top_k=retrieval_top_k)

    # Bounded ontology hierarchy expansion: reuses OpenWorldRetriever's own existing, already-
    # tested child-expansion helper (a parent match surfaces a few of its more-specific children as
    # lower-confidence siblings -- a recall boost, not a ranking claim) rather than reimplementing
    # hierarchy traversal here. Applied only to the TOP of the fused list (never every result, so
    # one broad parent match can't explode into dozens of children) and never grows the pool past
    # retrieval_top_k. Any failure degrades silently -- hierarchy expansion is a bonus, never load-
    # bearing for this stage.
    if fused:
        try:
            expanded_children = retriever._expand_hierarchy(fused[:8])  # noqa: SLF001
        except Exception:
            expanded_children = []
        seen_ids = {c.concept.concept_id for c in fused}
        for child in expanded_children:
            if len(fused) >= retrieval_top_k:
                break
            if child.concept.concept_id not in seen_ids:
                fused.append(child)
                seen_ids.add(child.concept.concept_id)

    return fused


def _rerank_score(candidate: RetrievedCandidate, fused_rank: int = 0) -> float:
    concept = candidate.concept
    score = candidate.match_score * _MATCH_KIND_WEIGHT.get(candidate.match_kind, 0.5)
    if fused_rank > 0:
        score += _FUSED_RANK_BONUS_MAX / (1.0 + (fused_rank - 1) / _FUSED_RANK_HALF_LIFE)
    score += _CURATION_BONUS.get(concept.curation_status, 0.0)
    # Dangerousness governs the separately tagged safety-retention step below.
    # It is not evidence for a diagnostic rank.
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
                           rerank_score=round(_rerank_score(c, rank), 4), match_kind=c.match_kind,
                           reasons=[f"retrieval:{c.match_kind}"])
        for rank, c in enumerate(retrieved, start=1)
    ]
    scored.sort(key=lambda rc: -rc.rerank_score)
    kept = scored[:rerank_top_k]
    kept_ids = {rc.concept.concept_id for rc in kept}

    dangerous_missing = [
        rc for rc in scored[rerank_top_k:]
        if rc.concept.dangerous is True and rc.concept.concept_id not in kept_ids
    ]
    if dangerous_missing:
        # Round M: the best-retrieved few are never evicted to make room (reinjection is about
        # SAFETY retention; it must not be able to erase the candidates several independent
        # signals agreed on -- with dozens of dangerous concepts retrieved it used to evict every
        # non-dangerous survivor, including a rank-2 retrieval hit). If nothing evictable is left the
        # dangerous candidate is appended instead (bounded overflow, as documented above).
        top_fused_ids = {c.concept.concept_id for c in retrieved[:_PROTECTED_FUSED_TOP]}
        non_dangerous_kept = sorted(
            (rc for rc in kept if not rc.concept.dangerous and rc.concept.concept_id not in top_fused_ids),
            key=lambda rc: rc.rerank_score
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
                         objective_finding_phrases: Sequence[str] = (),
                         medications: Sequence[str] = (),
                         retrieval_top_k: int = 150, rerank_top_k: int = 25) -> List[RerankedCandidate]:
    """The full 3-stage pipeline as one call -- what candidate_generator.py's competition-retrieval
    step actually invokes each turn."""
    retrieved = retrieve_high_recall(
        retriever, chief_complaint=chief_complaint, symptoms=symptoms, history=history,
        imaging_concepts=imaging_concepts, codes=codes,
        objective_finding_phrases=objective_finding_phrases, medications=medications,
        retrieval_top_k=retrieval_top_k,
    )
    return lightweight_rerank(retrieved, rerank_top_k=rerank_top_k)
