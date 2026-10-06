"""A Tier-2 long-tail diagnosis (outside the 34-disease Tier-1 KB) must be reachable by retrieval
from a realistic LAY DESCRIPTION of its presentation -- not just from typing its own formal name.
This is the actual claim this round's retrieval improvements (typical_features indexing + IDF +
multi-query RRF fusion) are meant to support for the long tail, since the 44-case evaluation set's
ground truth is Tier-1-only (see test_retrieval_recall_metrics.py's own honest note about that)."""

from __future__ import annotations

from nova_agent.open_world import OpenWorldRetriever
from nova_agent.ontology.models import Tier
from nova_agent.ontology.registry import get_default_catalog
from nova_agent.retrieval_pipeline import retrieve_high_recall


def _rank_of(concept_id: str, retrieved) -> int:
    ids = [c.concept.concept_id for c in retrieved]
    return ids.index(concept_id) + 1 if concept_id in ids else -1


def test_a_real_tier2_concept_survives_retrieval_from_a_lay_description_of_its_own_symptoms():
    catalog = get_default_catalog()
    concept = catalog.get_condition("tier2:sudden_sensorineural_hearing_loss")
    assert concept is not None and concept.tier == Tier.TIER2_STRUCTURED

    retriever = OpenWorldRetriever(catalog)
    retrieved = retrieve_high_recall(
        retriever, chief_complaint="sudden hearing loss in one ear with ringing and dizziness",
        symptoms=["dizziness"], retrieval_top_k=100,
    )
    rank = _rank_of(concept.concept_id, retrieved)
    assert rank != -1, "the real Tier-2 concept never appeared in top-100 retrieval from a lay description"
    assert rank <= 100


def test_typical_features_are_what_makes_the_long_tail_concept_findable():
    """Directly attributes the win to typical_features indexing: a concept whose typical_features
    are cleared should be materially harder (or impossible) to find from the same lay description
    that its formal name/aliases alone don't share vocabulary with."""
    from nova_agent.ontology.models import ClinicalConcept, SemanticType
    from nova_agent.ontology.search import ConceptSearchIndex

    with_features = ClinicalConcept(
        concept_id="with_features", canonical_name="Rare Cochlear Disorder",
        semantic_type=SemanticType.DISEASE, tier=Tier.TIER2_STRUCTURED,
        curation_status="STRUCTURED",
        typical_features=("sudden hearing loss", "ringing in the ears", "one-sided deafness"),
    )
    without_features = ClinicalConcept(
        concept_id="without_features", canonical_name="Rare Cochlear Disorder Two",
        semantic_type=SemanticType.DISEASE, tier=Tier.TIER2_STRUCTURED,
        curation_status="STRUCTURED",
    )
    index = ConceptSearchIndex()
    index.add(with_features)
    index.add(without_features)

    hits = index.search("sudden hearing loss with ringing in one ear", limit=10)
    ids = [h.concept.concept_id for h in hits]
    assert "with_features" in ids
    assert "without_features" not in ids
