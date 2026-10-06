"""Stage 2/3 of the competition retrieval pipeline: nova_agent.retrieval_pipeline.
lightweight_rerank(). Deterministic (no torch/embeddings), bounded output, and MUST NOT silently
drop a `dangerous: true` Stage-1 candidate -- see the module docstring for the reinjection
contract this exercises directly against constructed ClinicalConcept fixtures (so the assertions
are exact and don't depend on the real catalog's current content)."""

from __future__ import annotations

from nova_agent.ontology.models import ClinicalConcept, ConceptMatch, SemanticType, Tier
from nova_agent.open_world import RetrievedCandidate
from nova_agent.retrieval_pipeline import lightweight_rerank


def _candidate(cid: str, *, score: float, dangerous: bool = False, urgency: str = "ROUTINE",
               curation_status: str = "STRUCTURED", match_kind: str = "token") -> RetrievedCandidate:
    concept = ClinicalConcept(
        concept_id=cid, canonical_name=cid.replace("_", " ").title(),
        semantic_type=SemanticType.DISEASE, tier=Tier.TIER2_STRUCTURED,
        curation_status=curation_status, dangerous=dangerous, urgency=urgency,
    )
    return RetrievedCandidate.from_match(
        ConceptMatch(concept=concept, score=score, matched_term=cid, match_kind=match_kind)
    )


def test_rerank_is_deterministic_and_bounded_by_rerank_top_k():
    retrieved = [_candidate(f"c{i}", score=1.0 - i * 0.01) for i in range(80)]
    reranked = lightweight_rerank(retrieved, rerank_top_k=25)
    assert len(reranked) == 25
    # Deterministic: running it again on the same input produces the identical ordered result.
    again = lightweight_rerank(retrieved, rerank_top_k=25)
    assert [rc.concept.concept_id for rc in reranked] == [rc.concept.concept_id for rc in again]


def test_rerank_never_silently_drops_a_dangerous_candidate():
    """25 routine candidates all scored higher than one dangerous long-shot -- naive top-K would
    drop the dangerous one entirely. The reranker must reinject it."""
    routine = [_candidate(f"routine_{i}", score=0.9) for i in range(25)]
    dangerous = _candidate("dangerous_long_shot", score=0.1, dangerous=True, urgency="CRITICAL")
    reranked = lightweight_rerank(routine + [dangerous], rerank_top_k=25)
    kept_ids = {rc.concept.concept_id for rc in reranked}
    assert "dangerous_long_shot" in kept_ids, "a dangerous Stage-1 candidate must survive reranking"
    reinjected = next(rc for rc in reranked if rc.concept.concept_id == "dangerous_long_shot")
    assert "safety_reinjection" in reinjected.reasons


def test_rerank_stays_bounded_even_with_reinjection():
    routine = [_candidate(f"routine_{i}", score=0.9) for i in range(25)]
    dangerous = [_candidate(f"dangerous_{i}", score=0.05, dangerous=True) for i in range(3)]
    reranked = lightweight_rerank(routine + dangerous, rerank_top_k=25)
    assert len(reranked) == 25, "reinjection must swap out weak non-dangerous survivors, not just grow the bundle"
    dangerous_ids = {rc.concept.concept_id for rc in reranked if rc.concept.dangerous}
    assert len(dangerous_ids) == 3


def test_rerank_never_removes_an_already_kept_dangerous_candidate_to_make_room():
    strong_dangerous = [_candidate(f"strong_dangerous_{i}", score=0.95, dangerous=True) for i in range(25)]
    weak_dangerous = _candidate("weak_dangerous", score=0.05, dangerous=True)
    reranked = lightweight_rerank(strong_dangerous + [weak_dangerous], rerank_top_k=25)
    kept_ids = {rc.concept.concept_id for rc in reranked}
    assert all(f"strong_dangerous_{i}" in kept_ids for i in range(25)), (
        "reinjection must never evict an already-kept dangerous candidate"
    )


def test_zero_keep_budget_returns_nothing():
    retrieved = [_candidate("c1", score=0.9)]
    assert lightweight_rerank(retrieved, rerank_top_k=0) == []


def test_empty_input_returns_nothing():
    assert lightweight_rerank([], rerank_top_k=25) == []


def test_higher_curation_and_match_kind_rank_above_weaker_equal_score_matches():
    """Not a learned model -- a transparent, checkable ordering: an exact/DEEP-curated match should
    outrank a fuzzy/NOT_CURATED one even at the same raw retrieval score."""
    strong = _candidate("strong", score=0.6, curation_status="DEEP", match_kind="exact")
    weak = _candidate("weak", score=0.6, curation_status="NOT_CURATED", match_kind="fuzzy")
    reranked = lightweight_rerank([weak, strong], rerank_top_k=2)
    assert [rc.concept.concept_id for rc in reranked] == ["strong", "weak"]
