"""Round M: the reranker keeps Stage 1's fused-retrieval order as a bounded prior."""

from __future__ import annotations

from nova_agent.ontology.models import ClinicalConcept, Tier
from nova_agent.open_world import RetrievedCandidate
from nova_agent.retrieval_pipeline import _FUSED_RANK_BONUS_MAX, _rerank_score, lightweight_rerank


def _cand(cid, kind="token", score=0.7, dangerous=False):
    concept = ClinicalConcept(concept_id=cid, canonical_name=cid, tier=Tier.TIER2_STRUCTURED,
                              curation_status="STRUCTURED", dangerous=dangerous)
    return RetrievedCandidate(concept=concept, match_score=score, match_kind=kind,
                              tier=concept.tier.value, curation_status="STRUCTURED", is_curated=True)


def test_prior_decays_with_fused_rank_and_is_bounded():
    c = _cand("x")
    scores = [_rerank_score(c, r) for r in (1, 2, 5, 20, 100)]
    assert all(a > b for a, b in zip(scores, scores[1:]))
    assert scores[0] - _rerank_score(c, 0) <= _FUSED_RANK_BONUS_MAX + 1e-9


def test_top_fused_candidate_survives_a_crowd_of_slightly_stronger_lexical_matches():
    crowd = [_cand(f"c{i}", score=0.8) for i in range(40)]
    top = _cand("top", score=0.7)
    kept = lightweight_rerank([top] + crowd, rerank_top_k=25)
    assert "top" in {k.concept.concept_id for k in kept}
    # and without the prior (rank 0 for everyone) it would have been dropped
    no_prior = sorted([top] + crowd, key=lambda c: -_rerank_score(c, 0))
    assert "top" not in {c.concept.concept_id for c in no_prior[:25]}


def test_position_alone_cannot_beat_an_exact_name_match():
    exact = _cand("exact", kind="exact", score=1.0)
    token = _cand("token", kind="token", score=0.7)
    ranked = lightweight_rerank([token, exact], rerank_top_k=1)
    assert ranked[0].concept.concept_id == "exact"
