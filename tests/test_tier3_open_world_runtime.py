"""A Tier-3 ontology-only concept -- named only from a terminology snapshot, no curated clinical
claims -- must be able to reach the LLM candidate bundle as a shallow, provenance-tagged
possibility, and must NEVER cause a fabricated deterministic clinical action (question/exam/test)
to be generated.

This sandbox's default catalog has 0 real Tier-3 concepts (nova_agent/ontology/providers/{icd10,
icd11,snomed}.py require an operator-supplied local terminology snapshot, deliberately not bundled
for licensing/provenance reasons -- see scripts/report_disease_coverage.py). A synthetic Tier-3
concept, injected via the same catalog-lookup seam the runtime uses, is therefore the only way to
exercise this path in this environment; the mechanism itself is identical to whatever a real
Tier-3 snapshot would provide."""

from __future__ import annotations

from nova_agent.candidate_generator import _concept_to_kb_entry
from nova_agent.differential import DifferentialItem
from nova_agent.missing_info import MissingInformationAnalyzer, _resolve_entry
from nova_agent.ontology.models import ClinicalConcept, SemanticType, Tier
from nova_agent.retrieval_pipeline import RerankedCandidate
from nova_agent.state import PatientState


def _tier3_concept() -> ClinicalConcept:
    return ClinicalConcept(
        concept_id="synthetic_tier3_runtime", canonical_name="Synthetic Tier-3 Runtime Concept",
        semantic_type=SemanticType.DISEASE, tier=Tier.TIER3_ONTOLOGY, curation_status="NOT_CURATED",
        aliases=("a rare named condition",),
    )


def test_tier3_candidate_enters_the_candidate_bundle_as_a_shallow_possibility():
    concept = _tier3_concept()
    entry = _concept_to_kb_entry(concept)
    assert entry["id"] == "onto::synthetic_tier3_runtime"
    assert entry["evidence_level"] == "ontology_tier3"
    # No fabricated deep clinical data of any kind.
    for key in ("discriminating_questions", "discriminating_exams", "discriminating_tests",
                "confirmatory_findings", "red_flag_keywords", "minimum_workup"):
        assert entry[key] == [], f"Tier-3 must never carry fabricated {key}"


def test_tier3_candidate_cannot_generate_a_fabricated_deterministic_action(monkeypatch):
    concept = _tier3_concept()

    class _FakeCatalog:
        def get_condition(self, concept_id):
            return concept if concept_id == "synthetic_tier3_runtime" else None

    import nova_agent.ontology.registry as registry_module
    monkeypatch.setattr(registry_module, "get_default_catalog", lambda: _FakeCatalog())

    item = DifferentialItem(
        diagnosis="Synthetic Tier-3 Runtime Concept", diagnosis_id="onto::synthetic_tier3_runtime",
        rank=1, score=0.1, score_ratio=0.1, urgency="ROUTINE", dangerous_if_missed=False,
        confidence_band="LOW",
    )
    state = PatientState(case_id="tier3-runtime", chief_complaint="a rare named condition")
    candidates = MissingInformationAnalyzer().analyze(state, [item], [])
    assert candidates == [], "a Tier-3 candidate must never generate a deterministic action on its own"


def test_reranked_tier3_candidate_type_carries_no_fabricated_clinical_fields():
    """Confirms retrieval_pipeline.RerankedCandidate itself only ever carries the concept + a
    transparent ranking score/reasons -- never a clinical claim it would need to invent."""
    concept = _tier3_concept()
    rc = RerankedCandidate(concept=concept, retrieval_score=0.4, rerank_score=0.4,
                            match_kind="fuzzy", reasons=["retrieval:fuzzy"])
    assert rc.concept.curation_status == "NOT_CURATED"
    assert not rc.concept.typical_features
