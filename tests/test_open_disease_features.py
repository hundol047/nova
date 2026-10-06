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


MONDO = ROOT / "nova_agent/knowledge/tier2_mondo_synonyms.json"


def test_mondo_sidecar_provenance_and_guards():
    from scripts.build_mondo_synonyms import build  # noqa: F401  (import check: builder stays runnable)
    data = json.loads(MONDO.read_text(encoding="utf-8"))
    prov = data["provenance"]
    assert prov["clinician_reviewed"] is False and "CC BY 4.0" in prov["license"]
    assert any("creativecommons.org/licenses/by/4.0" in line for line in prov["license_evidence"])
    assert "Monarch Initiative" in prov["attribution"] and len(prov["source_file_sha256"]) == 64
    for entry in data["entries"]:
        assert 1 <= len(entry["synonyms"]) <= 5
        assert all(usable_synonym(s) and "(" not in s and "," not in s for s in entry["synonyms"])


def test_short_acronyms_and_disjunctions_are_rejected():
    assert not usable_synonym("OI") and not usable_synonym("MAS") and not usable_synonym("Leptospira disease or disorder")
    assert not usable_synonym("Graves’ eye disease")  # typographic quote: not ASCII
    assert usable_synonym("GERD") and usable_synonym("Hansen disease")


def test_sidecar_synonyms_never_collide_across_concepts():
    """After merging both sidecars, an adopted synonym belongs to exactly one concept."""
    sidecar_sources = ("open_disease_ontology", "mondo_cc_by")
    concepts = Tier2CatalogProvider().load()
    catalog = {c["id"]: c for c in json.loads((ROOT / "nova_agent/knowledge/tier2_catalog.json").read_text())["conditions"]}
    owners = {}
    for c in concepts:
        for name in (c.canonical_name,) + tuple(c.aliases):
            owners.setdefault(name.lower(), set()).add(c.concept_id)
    adopted = 0
    for c in concepts:
        if not any(tag in c.source for tag in sidecar_sources):
            continue
        original = {a.lower() for a in catalog[c.concept_id.split(":", 1)[1]].get("aliases", [])}
        for alias in c.aliases:
            if alias.lower() not in original:
                adopted += 1
                assert owners[alias.lower()] == {c.concept_id}, alias
    assert adopted > 500
