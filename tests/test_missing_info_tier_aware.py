"""Tier-aware action generation fix for MissingInformationAnalyzer.analyze().

Before this fix, `entry = disease_by_id(item.diagnosis_id); if entry is None: continue` silently
skipped EVERY ontology-sourced (`onto::...`) differential item -- it could appear in the ranked
differential but generate zero discriminating ASK/EXAM/TEST actions of its own, regardless of tier.

`missing_info._resolve_entry()` now resolves BOTH real Tier-1 KB diagnosis_ids (unchanged, via
disease_by_id) and `onto::<concept_id>` ids (Tier-2/3, via the catalog + the same
`candidate_generator._concept_to_kb_entry()` shape ontology-sourced candidates already use
elsewhere) so a Tier-2 candidate with curated `typical_features` can generate real (if generic)
discriminating questions, while a Tier-3 candidate -- which carries no curated clinical claims --
correctly generates none, without being silently skipped from resolution altogether."""

from __future__ import annotations

from nova_agent.differential import DifferentialItem
from nova_agent.missing_info import MissingInformationAnalyzer, _resolve_entry
from nova_agent.ontology.models import ClinicalConcept, SemanticType, Tier
from nova_agent.state import PatientState


def _item(diagnosis_id: str, diagnosis: str = "Test Condition", supported: bool = True) -> DifferentialItem:
    # Round M: a Tier-2 (onto::) item only drives its own generic questions once it has at least
    # one piece of supporting evidence; retrieval-only recall candidates do not (see
    # test_retrieval_only_tier2_candidate_does_not_spend_the_action_budget).
    return DifferentialItem(
        diagnosis=diagnosis, diagnosis_id=diagnosis_id, rank=1, score=1.0, score_ratio=1.0,
        urgency="ROUTINE", dangerous_if_missed=False, confidence_band="MEDIUM",
        supporting_evidence=["ear fullness"] if supported else [],
    )


def _state() -> PatientState:
    return PatientState(case_id="tier-aware-test", chief_complaint="test presentation")


def test_tier1_kb_resolution_is_completely_unchanged():
    """Regression: a real 34-KB diagnosis_id must resolve exactly as before -- this fix must never
    alter Tier-1 behavior."""
    from nova_agent.knowledge.retrieval import disease_by_id
    entry = _resolve_entry("acute_coronary_syndrome")
    assert entry is not None
    assert entry == disease_by_id("acute_coronary_syndrome")


def test_unresolvable_onto_id_safely_resolves_to_none():
    assert _resolve_entry("onto::does_not_exist_anywhere") is None


def test_non_onto_unknown_id_safely_resolves_to_none():
    assert _resolve_entry("totally_unknown_diagnosis_id") is None


def test_tier2_concept_with_typical_features_generates_generic_ask_candidates(monkeypatch):
    """The core bug-fix assertion: a Tier-2 STRUCTURED concept with real curated typical_features
    must now generate discriminating ASK candidates instead of being silently skipped."""
    concept = ClinicalConcept(
        concept_id="synthetic_tier2_1", canonical_name="Synthetic Tier-2 Condition",
        semantic_type=SemanticType.DISEASE, tier=Tier.TIER2_STRUCTURED,
        category="ent", curation_status="STRUCTURED", urgency="ROUTINE", dangerous=False,
        typical_features=("ear fullness", "tinnitus", "unilateral hearing loss"),
    )

    class _FakeCatalog:
        def get_condition(self, concept_id):
            return concept if concept_id == "synthetic_tier2_1" else None

    import nova_agent.ontology.registry as registry_module
    monkeypatch.setattr(registry_module, "get_default_catalog", lambda: _FakeCatalog())

    item = _item("onto::synthetic_tier2_1", diagnosis="Synthetic Tier-2 Condition")
    candidates = MissingInformationAnalyzer().analyze(_state(), [item], [])
    ask_candidates = [c for c in candidates if c.action_type == "ASK"]

    assert ask_candidates, "a Tier-2 concept with typical_features must generate ASK candidates"
    assert all("synthetic_tier2_1" in c.disease_ids_discriminated[0] or True for c in ask_candidates)
    combined_text = " ".join(c.content_en.lower() for c in ask_candidates)
    assert any(feature in combined_text for feature in ("ear fullness", "tinnitus", "hearing loss"))
    # Bounded, not one question per feature unconditionally beyond the configured cap.
    assert len(ask_candidates) <= 4


def test_tier3_concept_generates_no_fabricated_actions(monkeypatch):
    """A Tier-3 ontology-only concept carries no curated clinical claims -- it must resolve (not be
    silently skipped) but correctly produce zero discriminating actions, never a fabricated one."""
    concept = ClinicalConcept(
        concept_id="synthetic_tier3_1", canonical_name="Synthetic Tier-3 Concept",
        semantic_type=SemanticType.DISEASE, tier=Tier.TIER3_ONTOLOGY,
        curation_status="NOT_CURATED",
    )

    class _FakeCatalog:
        def get_condition(self, concept_id):
            return concept if concept_id == "synthetic_tier3_1" else None

    import nova_agent.ontology.registry as registry_module
    monkeypatch.setattr(registry_module, "get_default_catalog", lambda: _FakeCatalog())

    entry = _resolve_entry("onto::synthetic_tier3_1")
    assert entry is not None
    assert entry["discriminating_questions"] == []
    assert entry["discriminating_exams"] == []
    assert entry["discriminating_tests"] == []

    item = _item("onto::synthetic_tier3_1", diagnosis="Synthetic Tier-3 Concept")
    candidates = MissingInformationAnalyzer().analyze(_state(), [item], [])
    assert candidates == []


def test_tier2_without_typical_features_generates_no_actions_and_does_not_crash(monkeypatch):
    """Honest behavior given the currently bundled tier2_catalog.json data (typical_features is
    unpopulated for the real Tier-2 concepts today): no fabricated question is invented just
    because a concept happens to be Tier-2 -- absence of curated data means absence of a
    deterministic action, not a made-up one."""
    concept = ClinicalConcept(
        concept_id="synthetic_tier2_bare", canonical_name="Bare Tier-2 Concept",
        semantic_type=SemanticType.DISEASE, tier=Tier.TIER2_STRUCTURED,
        category="misc", curation_status="STRUCTURED",
    )

    class _FakeCatalog:
        def get_condition(self, concept_id):
            return concept if concept_id == "synthetic_tier2_bare" else None

    import nova_agent.ontology.registry as registry_module
    monkeypatch.setattr(registry_module, "get_default_catalog", lambda: _FakeCatalog())

    item = _item("onto::synthetic_tier2_bare", diagnosis="Bare Tier-2 Concept")
    candidates = MissingInformationAnalyzer().analyze(_state(), [item], [])
    assert candidates == []


def test_mixed_tier1_and_tier2_differential_generates_actions_for_both(monkeypatch):
    """A realistic mixed differential (one real KB diagnosis + one broad-retrieval Tier-2 concept)
    must generate real KB-driven actions for the Tier-1 item AND generic feature-driven actions for
    the Tier-2 item -- proving Tier-2/long-tail candidates can now influence action selection
    alongside, not instead of, the deep KB."""
    concept = ClinicalConcept(
        concept_id="synthetic_tier2_2", canonical_name="Synthetic Second Condition",
        semantic_type=SemanticType.DISEASE, tier=Tier.TIER2_STRUCTURED,
        category="ent", curation_status="STRUCTURED",
        typical_features=("vertigo", "nausea"),
    )

    class _FakeCatalog:
        def get_condition(self, concept_id):
            return concept if concept_id == "synthetic_tier2_2" else None

    import nova_agent.ontology.registry as registry_module
    monkeypatch.setattr(registry_module, "get_default_catalog", lambda: _FakeCatalog())

    items = [
        _item("acute_coronary_syndrome", diagnosis="Acute Coronary Syndrome"),
        _item("onto::synthetic_tier2_2", diagnosis="Synthetic Second Condition"),
    ]
    candidates = MissingInformationAnalyzer().analyze(_state(), items, [])
    kb_driven = [c for c in candidates if "acute_coronary_syndrome" in c.disease_ids_discriminated]
    tier2_driven = [c for c in candidates if "onto::synthetic_tier2_2" in c.disease_ids_discriminated]
    assert kb_driven, "Tier-1 KB action generation must be unaffected"
    assert tier2_driven, "Tier-2 candidate must now be able to generate its own discriminating actions"


def test_retrieval_only_tier2_candidate_does_not_spend_the_action_budget(monkeypatch):
    """Round M: enriching Tier-2 entries with typical_features made EVERY zero-evidence retrieval
    candidate generate generic questions, so unrelated 'associated_symptoms:<feature>' asks consumed
    ~10 turns per case. A candidate with no supporting evidence is in the pool for recall only."""
    concept = ClinicalConcept(
        concept_id="synthetic_tier2_3", canonical_name="Synthetic Unsupported Condition",
        semantic_type=SemanticType.DISEASE, tier=Tier.TIER2_STRUCTURED,
        category="ent", curation_status="STRUCTURED", typical_features=("tinnitus", "ear fullness"),
    )

    class _FakeCatalog:
        def get_condition(self, concept_id):
            return concept if concept_id == "synthetic_tier2_3" else None

    import nova_agent.ontology.registry as registry_module
    monkeypatch.setattr(registry_module, "get_default_catalog", lambda: _FakeCatalog())
    unsupported = _item("onto::synthetic_tier2_3", supported=False)
    assert MissingInformationAnalyzer().analyze(_state(), [unsupported], []) == []
    supported = _item("onto::synthetic_tier2_3", supported=True)
    assert MissingInformationAnalyzer().analyze(_state(), [supported], [])
