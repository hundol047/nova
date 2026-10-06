"""IDF-like corpus-frequency-aware token weighting in nova_agent.ontology.search.ConceptSearchIndex
-- a rare, distinctive shared term must outrank a common/generic shared term, computed ENTIRELY
from the local catalog's own token document-frequencies (no external corpus, no fabricated
synonyms). Uses constructed fixture concepts so the assertion doesn't depend on the real bundled
catalog's current exact content."""

from __future__ import annotations

from nova_agent.ontology.models import ClinicalConcept, SemanticType, Tier
from nova_agent.ontology.search import ConceptSearchIndex


def _concept(cid: str, name: str) -> ClinicalConcept:
    return ClinicalConcept(concept_id=cid, canonical_name=name, semantic_type=SemanticType.DISEASE,
                            tier=Tier.TIER2_STRUCTURED, curation_status="STRUCTURED")


def test_rare_shared_term_outranks_common_shared_term():
    index = ConceptSearchIndex()
    # "syndrome" is common (appears in many concepts); "zzyx" is rare (appears in exactly one).
    index.add(_concept("c1", "Zzyx Fever Syndrome"))
    for i in range(10):
        index.add(_concept(f"generic{i}", f"Generic Condition {i} Syndrome"))

    hits = index.search("zzyx syndrome", limit=20)
    ranked_ids = [h.concept.concept_id for h in hits]
    assert ranked_ids[0] == "c1", "the concept sharing the RARE term should rank above ones sharing only the common term"


def test_a_query_matching_only_a_common_token_does_not_score_as_a_perfect_match():
    """Regression guard for the exact bug this weighting scheme could introduce: normalizing only
    by tokens that exist somewhere in the catalog (instead of by ALL query tokens) would let a
    single common-word match look like a complete match just because the other query words were
    silently excluded from the denominator."""
    index = ConceptSearchIndex()
    index.add(_concept("c1", "Some Syndrome"))
    for i in range(5):
        index.add(_concept(f"other{i}", f"Other Condition {i} Syndrome"))

    hits = index.search("entirely fabricated syndrome qzxwv", limit=5, fuzzy=False)
    token_hits = [h for h in hits if h.match_kind == "token"]
    assert token_hits, "expected at least a weak token match on the shared word 'syndrome'"
    assert token_hits[0].score < 0.85, (
        "a match on only one of four query tokens must not score as if it were nearly complete"
    )


def test_a_token_absent_from_the_whole_catalog_does_not_inflate_partial_matches():
    index = ConceptSearchIndex()
    index.add(_concept("c1", "Common Pain Syndrome"))
    hits = index.search("completely unrelated made up phrase pain", limit=5, fuzzy=False)
    assert hits
    # Only "pain" is shared; the other four words exist nowhere in this tiny catalog. The match
    # must still reflect that most of the query went unmatched.
    assert hits[0].score < 0.85
