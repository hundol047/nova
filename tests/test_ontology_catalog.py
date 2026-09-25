"""Tests for the vNext ontology layer + tiered disease catalog (nova_agent/ontology/).

These import nova_agent.ontology.* which, via the package __init__, pulls in pydantic (present in
CI). They validate catalog integrity, tier precedence, search behavior, code mapping, open-world
outcomes, and LLM-diagnosis normalization. All queries are written fresh here (not copied from any
evaluation/blind case file)."""

from __future__ import annotations

from nova_agent.ontology.registry import build_catalog
from nova_agent.ontology.models import Tier
from nova_agent.open_world import OpenWorldOutcome, OpenWorldRetriever


def _catalog():
    return build_catalog()


def test_core_34_present_as_tier1_deep():
    cat = _catalog()
    tiers = cat.counts_by_tier()
    assert tiers[Tier.TIER1_DEEP.value] == 34, "the 34 core deep profiles must be preserved as Tier-1"


def test_tier2_catalog_loaded_and_no_duplicate_concept_ids():
    cat = _catalog()
    ids = [c.concept_id for c in cat.all_concepts()]
    assert len(ids) == len(set(ids)), "concept ids must be unique across all tiers"
    assert cat.counts_by_tier()[Tier.TIER2_STRUCTURED.value] > 100, "broad Tier-2 catalog expected"


def test_exact_alias_search_prefers_curated_concept():
    cat = _catalog()
    hits = cat.search_conditions("appendicitis", limit=3)
    assert hits, "should find a match for appendicitis"
    assert hits[0].concept.curation_status in ("DEEP", "STRUCTURED")


def test_korean_alias_search_matches():
    cat = _catalog()
    hits = cat.search_conditions("통풍", limit=3)  # gout
    assert any("Gout" in h.concept.canonical_name for h in hits)


def test_external_code_mapping_roundtrips():
    cat = _catalog()
    # Every Tier-2 ICD-10 anchor should be resolvable via map_external_code.
    coded = [c for c in cat.all_concepts() if c.external_codes]
    assert coded, "expected concepts carrying ICD-10 codes"
    sample = coded[0]
    code = sample.external_codes[0]
    mapped = cat.map_external_code(code.system, code.code)
    assert sample.concept_id in {m.concept_id for m in mapped}


def test_uncurated_concept_not_marked_curated():
    cat = _catalog()
    for c in cat.all_concepts():
        if c.curation_status == "NOT_CURATED":
            # NOT_CURATED concepts must not masquerade as deep/structured curation.
            assert c.tier == Tier.TIER3_ONTOLOGY


def test_open_world_known_condition():
    r = OpenWorldRetriever(_catalog())
    a = r.assess("acute appendicitis")
    assert a.outcome == OpenWorldOutcome.KNOWN_CONDITION
    assert a.top is not None and a.top.is_curated


def test_open_world_unknown_presentation_for_nonsense():
    r = OpenWorldRetriever(_catalog())
    a = r.assess("zzqxwv nonexistent gibberish token")
    assert a.outcome == OpenWorldOutcome.UNKNOWN_PRESENTATION
    assert a.top is None


def test_open_world_insufficient_information_for_tiny_query():
    r = OpenWorldRetriever(_catalog())
    a = r.assess("ch")
    assert a.outcome == OpenWorldOutcome.INSUFFICIENT_INFORMATION


def test_llm_diagnosis_mapped_and_unmapped():
    r = OpenWorldRetriever(_catalog())
    mapped = r.normalize_llm_diagnosis("acute cholecystitis")
    assert mapped.mapped and mapped.status == "MAPPED" and mapped.concept is not None

    unmapped = r.normalize_llm_diagnosis("entirely invented syndrome qzx")
    assert not unmapped.mapped and unmapped.status == "UNMAPPED_LLM_DIAGNOSIS"
    # Never coerced to a nearby known disease.
    assert unmapped.concept is None
