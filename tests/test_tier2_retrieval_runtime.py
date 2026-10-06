"""A REAL (not synthetic) Tier-2 structured concept from the bundled catalog
(nova_agent/knowledge/tier2_catalog.json) must be able to flow through the actual competition
retrieval runtime -- Stage 1 retrieval -> Stage 2/3 rerank -> candidate_generator pool -- and reach
the final differential, proving Tier-2 concepts are not merely theoretically reachable but actually
do reach the real reasoning path against real bundled data (distinct from the synthetic-concept
unit tests in tests/test_missing_info_tier_aware.py, which prove the MECHANISM in isolation)."""

from __future__ import annotations

from nova_agent.candidate_generator import generate_candidates
from nova_agent.clinical_presentation import extract_presentation
from nova_agent.ontology.models import Tier
from nova_agent.ontology.registry import get_default_catalog


def test_a_real_bundled_tier2_concept_exists_and_is_reachable_by_search():
    catalog = get_default_catalog()
    hits = catalog.search_conditions("sudden sensorineural hearing loss", limit=3)
    assert hits, "expected the real bundled Tier-2 catalog to contain this concept"
    assert hits[0].concept.tier == Tier.TIER2_STRUCTURED
    # PR #15's audit correction: every bundled Tier-2 record is an UNVERIFIED structured candidate
    # (clinical_validation_status NOT_VERIFIED), so it is searchable but never labelled curated.
    assert hits[0].concept.curation_status == "NOT_CURATED"


def test_a_real_tier2_concept_reaches_the_runtime_candidate_pool():
    text = "progressive hearing loss and ringing in the ears with vertigo"
    presentation = extract_presentation(text)
    # pool_target_size=25 mirrors what differential.py's real runtime call site passes when
    # competition retrieval is enabled (the configured reasoning_top_k) -- the legacy default
    # (12) is sized for the closed-KB-only path and can otherwise leave no budget for retrieval
    # additions once enough Tier-1 symptom-matched candidates already fill it (a separate,
    # pre-existing trim-budget trade-off covered by tests/test_competition_5k_integration.py).
    records = generate_candidates(
        presentation, competition_retrieval=True, retrieval_top_k=150, rerank_top_k=25,
        chief_complaint_text=text, pool_target_size=25,
    )
    tier2_ids = {c.id for c in records if c.id.startswith("onto::tier2:")}
    assert tier2_ids, "expected at least one real Tier-2 concept to reach the candidate pool"
