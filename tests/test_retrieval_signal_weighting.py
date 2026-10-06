"""Objective/imaging evidence must carry more retrieval influence than a generic symptom word --
implemented GENERICALLY through per-signal-type weights (retrieval_pipeline.SIGNAL_WEIGHTS), never
a disease-specific rule. This is exactly the "positive troponin should matter more than 'pain'"
requirement, verified at the fusion-scoring level (not dependent on any particular catalog
content)."""

from __future__ import annotations

from nova_agent.ontology.models import ClinicalConcept, ConceptMatch, SemanticType, Tier
from nova_agent.open_world import RetrievedCandidate
from nova_agent.retrieval_pipeline import SIGNAL_WEIGHTS, _rrf_fuse


def _candidate(cid: str, score: float = 0.6) -> RetrievedCandidate:
    concept = ClinicalConcept(
        concept_id=cid, canonical_name=cid, semantic_type=SemanticType.DISEASE,
        tier=Tier.TIER2_STRUCTURED, curation_status="STRUCTURED",
    )
    return RetrievedCandidate.from_match(
        ConceptMatch(concept=concept, score=score, matched_term=cid, match_kind="token")
    )


def test_objective_finding_signal_outweighs_generic_symptom_signal_at_equal_rank():
    assert SIGNAL_WEIGHTS["objective_finding"] > SIGNAL_WEIGHTS["symptom"]
    assert SIGNAL_WEIGHTS["objective_finding"] > SIGNAL_WEIGHTS["chief_complaint"]
    assert SIGNAL_WEIGHTS["objective_finding"] > SIGNAL_WEIGHTS["history_risk"]


def test_imaging_signal_outweighs_generic_symptom_signal():
    assert SIGNAL_WEIGHTS["imaging"] > SIGNAL_WEIGHTS["symptom"]


def test_a_top_ranked_objective_finding_hit_beats_a_top_ranked_generic_symptom_hit():
    """Same rank position (#1) in two different single-signal lists -- the objective-finding one
    must win the fused ranking purely from its higher signal weight, proving the weighting is
    actually load-bearing in the fusion, not just a documented constant."""
    from_objective = _candidate("from_objective_finding")
    from_symptom = _candidate("from_generic_symptom")
    fused = _rrf_fuse(
        [("objective_finding", [from_objective]), ("symptom", [from_symptom])], top_k=10,
    )
    assert fused[0].concept.concept_id == "from_objective_finding"


def test_history_risk_and_medication_weighted_lower_than_chief_complaint():
    """History/risk-factor and medication context are real, useful signals but less specific to
    the CURRENT presentation than the chief complaint itself -- weighted accordingly."""
    assert SIGNAL_WEIGHTS["history_risk"] < SIGNAL_WEIGHTS["chief_complaint"]
    assert SIGNAL_WEIGHTS["medication"] < SIGNAL_WEIGHTS["chief_complaint"]
