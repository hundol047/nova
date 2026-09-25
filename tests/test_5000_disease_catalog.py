"""5,000-disease universe catalog tests (PHASE 1 PART R1) — dependency-free.

Generates the synthetic Tier-3 snapshot into a TEMP snapshot_root inside a fixture (custom.json is
git-ignored, so the test must produce it) and builds a catalog over it, then asserts:
  total_searchable >= 5000, 0 duplicate canonical ids, all 34 Tier-1 deep preserved, valid tiers,
  valid hierarchy references, valid source/curation on Tier-3.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_ROOT / "scripts"))
if "nova_agent" not in sys.modules:
    _pkg = types.ModuleType("nova_agent")
    _pkg.__path__ = [str(_ROOT / "nova_agent")]
    sys.modules["nova_agent"] = _pkg


@pytest.fixture(scope="module")
def catalog_5000(tmp_path_factory):
    """Build a catalog with a freshly-GENERATED synthetic Tier-3 snapshot (>=5000 total)."""
    import build_tier3_synthetic_snapshot as gen
    from nova_agent.ontology.registry import DiseaseCatalog
    from nova_agent.ontology.providers.core_kb import CoreKbProvider
    from nova_agent.ontology.providers.tier2_catalog import Tier2CatalogProvider
    from nova_agent.ontology.providers.custom import CustomProvider

    snap_dir = tmp_path_factory.mktemp("snapshots")
    snapshot = gen.generate(target=4200)
    import json
    (snap_dir / "custom.json").write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")

    cat = DiseaseCatalog()
    cat.add_all(CoreKbProvider().load())
    cat.add_all(Tier2CatalogProvider().load())
    cat.add_all(CustomProvider(snapshot_root=snap_dir).load())
    return cat


def test_total_searchable_at_least_5000(catalog_5000):
    assert len(catalog_5000) >= 5000, f"total_searchable must be >=5000, got {len(catalog_5000)}"


def test_no_duplicate_concept_ids(catalog_5000):
    ids = [c.concept_id for c in catalog_5000.all_concepts()]
    assert len(ids) == len(set(ids))


def test_all_34_tier1_deep_preserved(catalog_5000):
    from nova_agent.ontology.models import Tier
    tier1 = [c for c in catalog_5000.all_concepts() if c.tier == Tier.TIER1_DEEP]
    assert len(tier1) == 34


def test_tier_breakdown_reasonable(catalog_5000):
    t = catalog_5000.counts_by_tier()
    assert t["TIER1_DEEP"] == 34
    assert t["TIER2_STRUCTURED"] >= 1000
    assert t["TIER3_ONTOLOGY"] >= 3000


def test_every_concept_valid_tier_and_source(catalog_5000):
    valid_tiers = {"TIER1_DEEP", "TIER2_STRUCTURED", "TIER3_ONTOLOGY"}
    for c in catalog_5000.all_concepts():
        assert c.tier.value in valid_tiers
        assert c.canonical_name and c.canonical_name.strip()
        assert c.source  # provenance present


def test_tier3_hierarchy_references_resolve(catalog_5000):
    """Every Tier-3 parent reference that is set should resolve to a concept in the catalog (the
    generator only emits parents for concepts whose family parent it also emits)."""
    all_ids = {c.concept_id for c in catalog_5000.all_concepts()}
    dangling = 0
    checked = 0
    for c in catalog_5000.all_concepts():
        for p in c.parents:
            checked += 1
            if p not in all_ids:
                dangling += 1
    # allow zero dangling references in the synthetic snapshot
    assert dangling == 0, f"{dangling}/{checked} dangling parent references"


def test_tier3_is_not_curated(catalog_5000):
    from nova_agent.ontology.models import Tier
    for c in catalog_5000.all_concepts():
        if c.tier == Tier.TIER3_ONTOLOGY:
            assert c.curation_status == "NOT_CURATED"


@pytest.mark.parametrize("query,expect", [
    ("myocarditis", "Myocarditis"),
    ("cholangitis", "Cholangitis"),
    ("Guillain-Barre", "Guillain"),
    ("ovarian torsion", "Ovarian Torsion"),
    ("TTP", "Thrombotic Thrombocytopenic"),
    ("carbon monoxide poisoning", "Carbon Monoxide"),
    ("Kawasaki disease", "Kawasaki"),
    ("Stevens-Johnson", "Stevens-Johnson"),
    ("Fabry disease", "Fabry"),                  # rare / Tier-3 present
])
def test_representative_search(catalog_5000, query, expect):
    hits = catalog_5000.search_conditions(query, limit=3)
    assert hits, f"no match for {query!r}"
    assert any(expect.lower() in h.concept.canonical_name.lower() for h in hits)
