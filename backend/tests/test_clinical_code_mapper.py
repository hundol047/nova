"""Unit tests for services/clinical_code_mapper.py: LOINC/display-text -> nova_agent canonical
clinical ID mapping. Never fabricated -- an unmapped code/display must come back with
canonical_id=None while still preserving the raw code/display, never silently discarded.
"""

from app.services.clinical_code_mapper import map_lab


def test_known_loinc_code_maps_to_canonical_id_and_nova_state_key():
    result = map_lab("Potassium", loinc="2823-3")
    assert result.canonical_id == "lab.potassium"
    assert result.nova_state_key == "potassium"
    assert result.normalized_by == "LOINC"
    assert result.raw_code == "2823-3"


def test_loinc_mapping_covers_every_lab_objective_evidence_understands():
    from app.services.clinical_code_mapper import LOINC_TO_NOVA_LAB
    from nova_agent.objective_evidence import LAB_SPECS

    mapped_canonical_ids = {row[0] for row in LOINC_TO_NOVA_LAB.values()}
    for canonical_id in LAB_SPECS:
        assert canonical_id in mapped_canonical_ids, f"{canonical_id} has no LOINC row"
    # glucose/lactate are handled separately (delegating to their own verified extractors) but
    # still covered by this table for FHIR Observation ingestion.
    assert "lab.glucose" in mapped_canonical_ids
    assert "lab.lactate" in mapped_canonical_ids


def test_falls_back_to_display_text_when_no_loinc_given():
    result = map_lab("troponin", loinc=None)
    assert result.canonical_id == "lab.troponin"
    assert result.nova_state_key == "troponin"
    assert result.normalized_by == "display-text"


def test_display_text_fallback_is_case_insensitive():
    result = map_lab("TROPONIN")
    assert result.canonical_id == "lab.troponin"


def test_unknown_lab_is_never_fabricated_but_preserves_raw_facts():
    result = map_lab("Erythrocyte Sedimentation Rate", loinc="4537-7")
    assert result.canonical_id is None
    assert result.nova_state_key is None
    assert result.normalized_by == "unmapped"
    assert result.raw_code == "4537-7"
    assert result.raw_display == "Erythrocyte Sedimentation Rate"


def test_unrecognized_loinc_falls_back_to_display_text_match():
    """A LOINC code not in this table but a recognizable display name should still resolve via
    the display-text fallback rather than being marked unmapped outright."""
    result = map_lab("sodium", loinc="99999-9")
    assert result.canonical_id == "lab.sodium"
    assert result.normalized_by == "display-text"
