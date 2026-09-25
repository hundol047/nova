"""Open-world reasoning expansion tests (vNext PART H) — dependency-free.

Verifies multi-signal retrieval fusion, code retrieval, hierarchy expansion (recall boost),
rare-disease fallback, and — critically — that UNKNOWN/INSUFFICIENT outcomes are PRESERVED (no
patient is force-labelled). Uses a temporary Tier-3 snapshot for hierarchy edges so nothing
license-restricted is committed.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if "nova_agent" not in sys.modules:
    _pkg = types.ModuleType("nova_agent")
    _pkg.__path__ = [str(_ROOT / "nova_agent")]
    sys.modules["nova_agent"] = _pkg

from nova_agent.open_world import OpenWorldOutcome, OpenWorldRetriever  # noqa: E402
from nova_agent.ontology.registry import build_catalog  # noqa: E402


def _retriever():
    return OpenWorldRetriever(build_catalog())


def test_multi_signal_known_condition_via_fused_signals():
    r = _retriever()
    a = r.assess_multi_signal(chief_complaint="chest pain", symptoms=["dyspnea"],
                              codes=[("ICD10", "I50.9")], limit=15)
    assert a.outcome == OpenWorldOutcome.KNOWN_CONDITION
    assert a.top is not None and a.top.is_curated


def test_multi_signal_preserves_unknown_for_nonsense():
    r = _retriever()
    a = r.assess_multi_signal(chief_complaint="zzqxwv nonexistent gibberish token", limit=10)
    assert a.outcome == OpenWorldOutcome.UNKNOWN_PRESENTATION


def test_multi_signal_insufficient_for_empty():
    r = _retriever()
    a = r.assess_multi_signal(chief_complaint="", symptoms=[], limit=10)
    assert a.outcome == OpenWorldOutcome.INSUFFICIENT_INFORMATION


def test_code_retrieval_direct():
    r = _retriever()
    hits = r.retrieve_by_code("ICD-10", "I50.9")  # aliased system id should normalize
    assert hits and any(h.match_kind == "code" for h in hits)


def test_multi_signal_fusion_recall_at_least_single():
    r = _retriever()
    single = r.retrieve("abdominal pain", limit=20)
    multi = r.retrieve_multi_signal(chief_complaint="abdominal pain",
                                    symptoms=["vomiting", "fever"], limit=20)
    assert len(multi) >= len(single)


def test_hierarchy_expansion_surfaces_children(tmp_path, monkeypatch):
    # Build a catalog with a temporary Tier-3 snapshot that has parent/child edges.
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir()
    (snap_dir / "snomed.json").write_text(json.dumps({"concepts": [
        {"code": "P1", "display": "Zzxq parent syndrome", "children": ["C1", "C2"]},
        {"code": "C1", "display": "Zzxq child variant one", "parents": ["P1"]},
        {"code": "C2", "display": "Zzxq child variant two", "parents": ["P1"]},
    ]}), encoding="utf-8")

    from nova_agent.ontology.providers.snomed import SnomedProvider
    from nova_agent.ontology.registry import DiseaseCatalog
    cat = DiseaseCatalog()
    from nova_agent.ontology.providers.core_kb import CoreKbProvider
    from nova_agent.ontology.providers.tier2_catalog import Tier2CatalogProvider
    cat.add_all(CoreKbProvider().load())
    cat.add_all(Tier2CatalogProvider().load())
    cat.add_all(SnomedProvider(snapshot_root=snap_dir).load())

    r = OpenWorldRetriever(cat)
    m = r.retrieve_multi_signal(chief_complaint="Zzxq parent syndrome", expand_hierarchy=True, limit=20)
    kinds = {c.match_kind for c in m}
    assert "hierarchy" in kinds
    child_names = {c.concept.canonical_name for c in m if c.match_kind == "hierarchy"}
    assert "Zzxq child variant one" in child_names


def test_rare_fallback_returns_possible_not_unknown_when_ontology_matches():
    r = _retriever()
    # A Tier-2 structured but non-deep condition should still be retrievable as 'possible'.
    rare = r.retrieve_rare("mesothelioma", limit=10)
    assert rare  # ontology/Tier-2 surfaced it
    assert all(c.tier != "TIER1_DEEP" for c in rare)
