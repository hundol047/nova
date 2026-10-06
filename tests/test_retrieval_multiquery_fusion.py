"""Multi-query construction + Weighted Reciprocal Rank Fusion
(nova_agent/retrieval_pipeline.py's build_signal_queries()/_rrf_fuse()/retrieve_high_recall()).

Patient information is built into several BOUNDED, signal-typed queries (chief complaint /
symptoms / objective findings / history-risk / medications / imaging) instead of one giant
concatenated query, then fused deterministically by rank position -- never by re-scoring with a
learned model."""

from __future__ import annotations

from nova_agent.ontology.models import ClinicalConcept, ConceptMatch, SemanticType, Tier
from nova_agent.open_world import OpenWorldRetriever, RetrievedCandidate
from nova_agent.ontology.registry import get_default_catalog
from nova_agent.retrieval_pipeline import (
    SIGNAL_WEIGHTS,
    _rrf_fuse,
    build_signal_queries,
    retrieve_high_recall,
)


def _candidate(cid: str, score: float, match_kind: str = "token") -> RetrievedCandidate:
    concept = ClinicalConcept(
        concept_id=cid, canonical_name=cid, semantic_type=SemanticType.DISEASE,
        tier=Tier.TIER2_STRUCTURED, curation_status="STRUCTURED",
    )
    return RetrievedCandidate.from_match(
        ConceptMatch(concept=concept, score=score, matched_term=cid, match_kind=match_kind)
    )


def test_build_signal_queries_never_concatenates_everything_into_one_giant_query():
    queries = build_signal_queries(
        chief_complaint="chest pain", symptoms=["dyspnea", "diaphoresis"],
        objective_finding_phrases=["elevated troponin"], history_risk=["hypertension"],
        medications=["aspirin"], imaging_concepts=["widened mediastinum"],
    )
    # Six distinct, bounded, independently-labeled queries -- not one combined string.
    assert len(queries) == 6
    signals = {signal for signal, _ in queries}
    assert signals == {"chief_complaint", "symptom", "objective_finding", "history_risk",
                        "medication", "imaging"}
    for _signal, text in queries:
        assert text.strip(), "no query should be empty"


def test_build_signal_queries_omits_empty_signals():
    queries = build_signal_queries(chief_complaint="chest pain")
    assert queries == [("chief_complaint", "chest pain")]


def test_rrf_fuse_combines_rank_positions_across_signals_not_raw_scores():
    """A concept ranked #1 in TWO independent signals should outrank one ranked #1 in only ONE,
    even if the single-signal one has a nominally higher raw match_score -- this is what
    distinguishes RRF from a naive max-score merge."""
    only_in_one = _candidate("only_in_one", score=0.95)
    in_both_a = _candidate("in_both", score=0.6)
    in_both_b = _candidate("in_both", score=0.6)

    ranked_lists = [
        ("chief_complaint", [only_in_one]),
        ("symptom", [in_both_a]),
        ("history_risk", [in_both_b]),
    ]
    fused = _rrf_fuse(ranked_lists, top_k=10)
    fused_ids = [c.concept.concept_id for c in fused]
    assert fused_ids[0] == "in_both", "a concept found by multiple independent signals should rank first"


def test_rrf_fuse_is_bounded_at_top_k():
    ranked_lists = [("symptom", [_candidate(f"c{i}", score=0.5) for i in range(50)])]
    fused = _rrf_fuse(ranked_lists, top_k=10)
    assert len(fused) == 10


def test_signal_weights_are_centrally_configured_not_scattered_magic_numbers():
    """All signal weights live in one named constant -- this test just pins the contract that they
    exist and are configurable, not any specific value (which may reasonably be tuned)."""
    assert set(SIGNAL_WEIGHTS) >= {
        "chief_complaint", "symptom", "objective_finding", "imaging", "history_risk", "medication",
    }
    assert all(isinstance(w, (int, float)) and w > 0 for w in SIGNAL_WEIGHTS.values())


def test_retrieve_high_recall_with_real_catalog_uses_multiple_signals():
    """End-to-end smoke test against the real bundled catalog: passing several distinct signal
    types must not crash and must produce a bounded, non-empty result when at least one signal
    plausibly matches something."""
    retriever = OpenWorldRetriever(get_default_catalog())
    retrieved = retrieve_high_recall(
        retriever, chief_complaint="sudden severe chest pain radiating to the back",
        symptoms=["chest_pain"], objective_finding_phrases=["elevated troponin"],
        retrieval_top_k=50,
    )
    assert retrieved
    assert len(retrieved) <= 50
