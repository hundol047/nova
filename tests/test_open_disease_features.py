"""Provenance, precedence and quality guards of the Disease Ontology (CC0) sidecar."""
import json
from pathlib import Path

from scripts.build_open_disease_features import (AMBIGUOUS_SYNONYMS, MAX_FEATURES, build, clean_features,
                                                  parse_obo, usable_features, usable_synonym)
from nova_agent.ontology.providers.tier2_catalog import Tier2CatalogProvider

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "nova_agent/knowledge/tier2_open_features.json"


def _sidecar():
    return json.loads(SIDECAR.read_text(encoding="utf-8"))


def test_sidecar_provenance_is_cc0_and_unreviewed():
    prov = _sidecar()["provenance"]
    assert prov["clinician_reviewed"] is False
    assert "CC0" in prov["license"] and len(prov["source_file_sha256"]) == 64
    assert any("publicdomain/zero/1.0" in line or "CC0" in line for line in prov["license_evidence"])
    assert prov["source_url"].startswith("https://raw.githubusercontent.com/DiseaseOntology/")


def test_sidecar_entries_respect_quality_guards():
    for entry in _sidecar()["entries"]:
        assert len(entry["typical_features"]) <= MAX_FEATURES
        assert not entry["typical_features"] or len(entry["typical_features"]) >= 2
        assert all("_" not in f and len(f.split()) <= 8 for f in entry["typical_features"])
        assert all(usable_synonym(s) for s in entry["synonyms"])


def test_guards_drop_generic_and_ambiguous():
    assert clean_features(["fever", "pain", "lesions", "Carditis", "results_in_formation_of skin nodules"]) == ["carditis"]
    assert usable_features(["carditis"]) == []
    assert not usable_synonym("chest cold") and "cold" in AMBIGUOUS_SYNONYMS
    assert not usable_synonym("malignant melanoma of ear and/or external auricular canal")
    assert not usable_synonym("Heart Malformation 2")


def test_provider_precedence_catalog_over_open(tmp_path):
    concepts = {c.concept_id: c for c in Tier2CatalogProvider().load()}
    catalog = json.loads((ROOT / "nova_agent/knowledge/tier2_catalog.json").read_text())["conditions"]
    own = {c["id"] for c in catalog if c.get("typical_features")}
    for entry in _sidecar()["entries"]:
        concept = concepts.get(f"tier2:{entry['id']}")
        assert concept is not None
        if entry["id"] in own:
            assert "open_disease_ontology" not in concept.source or "synonyms" in concept.source
        elif entry["typical_features"] and "enrichment" not in concept.source:
            assert tuple(entry["typical_features"]) == concept.typical_features
            assert "open_disease_ontology_cc0" in concept.source


def test_builder_on_fixture_obo(tmp_path):
    obo = tmp_path / "mini.obo"
    obo.write_text(
        "data-version: test\nremark: The Disease Ontology content is available via the Creative Commons "
        "Public Domain Dedication CC0 1.0 Universal license\nproperty_value: terms:license "
        "https://creativecommons.org/publicdomain/zero/1.0/\n\n[Term]\nid: DOID:1\nname: rabies\n"
        'def: "A viral infection that has_symptom hydrophobia, has_symptom aerophobia, and has_symptom fever." []\n'
        'synonym: "Lyssa" EXACT []\n', encoding="utf-8")
    terms = parse_obo(obo)
    assert terms[0]["symptoms"] == ["hydrophobia", "aerophobia", "fever"]
    result = build(obo)
    assert result["schema"] == "nova-open-disease-features-v1"
