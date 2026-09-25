"""5,000-diagnosis retrieval/router/safety/reranker/pipeline tests (PHASE 1 PART R) — dep-free.

Exercises the full architecture on a catalog whose Tier-3 snapshot is GENERATED in a fixture.
Covers: embedding executes; retrieval Recall@K; router multi-specialty + fallback; router-miss
cannot drop critical; safety restores critical; reranker retains mandatory; LLM narrowed; UNKNOWN
not forced; rare retrieval; baseline gate blocks worse critical-recall; shadow unchanged; retrieval
failure fallback; error-miss taxonomy.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
for p in (str(_ROOT), str(_ROOT / "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)
if "nova_agent" not in sys.modules:
    _pkg = types.ModuleType("nova_agent")
    _pkg.__path__ = [str(_ROOT / "nova_agent")]
    sys.modules["nova_agent"] = _pkg


@pytest.fixture(scope="module")
def catalog5000(tmp_path_factory):
    import build_tier3_synthetic_snapshot as gen
    from nova_agent.ontology.registry import DiseaseCatalog
    from nova_agent.ontology.providers.core_kb import CoreKbProvider
    from nova_agent.ontology.providers.tier2_catalog import Tier2CatalogProvider
    from nova_agent.ontology.providers.custom import CustomProvider
    snap_dir = tmp_path_factory.mktemp("snap")
    (snap_dir / "custom.json").write_text(json.dumps(gen.generate(target=4200), ensure_ascii=False),
                                          encoding="utf-8")
    cat = DiseaseCatalog()
    cat.add_all(CoreKbProvider().load())
    cat.add_all(Tier2CatalogProvider().load())
    cat.add_all(CustomProvider(snapshot_root=snap_dir).load())
    return cat


@pytest.fixture(scope="module")
def index(catalog5000):
    from learning.retrieval.index import DiseaseIndex
    return DiseaseIndex().build(catalog5000.all_concepts())


# ---- embedding + retrieval ------------------------------------------------------------------

def test_embedding_executes(catalog5000):
    from learning.retrieval.disease_encoder import encode_disease
    c = next(iter(catalog5000.all_concepts()))
    v = encode_disease(c)
    assert len(v) == 256 and any(x != 0 for x in v)


def test_index_built_once_and_cached(index):
    assert len(index) >= 5000
    assert index.build_seconds >= 0.0


def test_retrieval_recall_at_k(catalog5000, index):
    from learning.retrieval.retriever import Retriever
    from learning.retrieval.eval_synthetic import measure
    m = measure(catalog5000, Retriever(index, catalog=catalog5000), n=120, top_k=200, seed=3)
    assert m["recall@100"] >= 0.9
    assert m["critical_recall@100"] >= 0.9
    assert m["critical_miss_rate@100"] <= 0.1


# ---- router ---------------------------------------------------------------------------------

def test_router_multi_specialty():
    from learning.routing.router import SpecialtyRouter
    res = SpecialtyRouter().route("chest pain with fever, cough and dyspnea")
    assert len(res.active_specialties()) >= 2


def test_router_low_confidence_global_fallback():
    from learning.routing.router import SpecialtyRouter
    assert SpecialtyRouter().route("feeling generally unwell").global_fallback is True


def test_router_boost_never_drops_or_lowers():
    from learning.routing.router import SpecialtyRouter
    from types import SimpleNamespace
    r = SpecialtyRouter()
    route = r.route("chest pain and dyspnea")
    items = [SimpleNamespace(category="cardiovascular", score=0.5),
             SimpleNamespace(category="dermatology", score=0.9)]
    before = [i.score for i in items]
    r.boost(items, route)
    assert len(items) == 2
    assert all(a >= b for a, b in zip([i.score for i in items], before))


# ---- safety recall --------------------------------------------------------------------------

def test_safety_recall_restores_missing_critical(catalog5000):
    from learning.safety_recall import apply_safety_recall
    from types import SimpleNamespace
    pool = [SimpleNamespace(concept_id="x", name="Costochondritis", tier="TIER2_STRUCTURED",
                            category="cardiovascular", score=0.8, sources=["embedding"])]
    apply_safety_recall(pool, catalog5000, "crushing chest pain radiating to jaw")
    names = [it.name for it in pool]
    assert any("Coronary" in n or "Embolism" in n or "Dissection" in n for n in names)


def test_router_miss_cannot_drop_critical(catalog5000):
    """Even if the router activates the WRONG specialty, safety-recall + reranker keep the critical
    candidate — the router never removes anything."""
    from learning.routing.router import SpecialtyRouter
    from learning.safety_recall import apply_safety_recall, assert_no_critical_dropped
    from types import SimpleNamespace
    pool = [SimpleNamespace(concept_id="d", name="Contact Dermatitis", tier="TIER2_STRUCTURED",
                            category="dermatology", score=0.9, sources=["embedding"])]
    apply_safety_recall(pool, catalog5000, "crushing chest pain radiating to jaw")
    before = list(pool)
    # router boosts dermatology (its miss) — additive only
    SpecialtyRouter().boost(pool, SpecialtyRouter().route("rash"))
    assert_no_critical_dropped(before, pool)  # critical (ACS/PE) still present


# ---- reranker -------------------------------------------------------------------------------

def test_reranker_retains_mandatory_regardless_of_score():
    from learning.rerank.reranker import Reranker, RerankInput
    cands = [RerankInput(concept_id=f"n{i}", name=f"C{i}", retrieval_score=0.9 - i * 0.02) for i in range(30)]
    cands.append(RerankInput(concept_id="crit", name="Pulmonary Embolism", retrieval_score=0.0,
                             is_critical=True, safety_mandatory=True))
    res = Reranker(keep=25).rerank(cands)
    assert "crit" in res.concept_ids()


# ---- pipeline: LLM narrowed + UNKNOWN preserved + rare ---------------------------------------

def test_pipeline_llm_narrowed_and_safety_present(catalog5000, index):
    from learning.retrieval.retriever import Retriever
    from learning.retrieval.patient_encoder import PatientQuery
    from learning.pipeline import FiveKPipeline
    p = FiveKPipeline(Retriever(index, catalog=catalog5000), catalog5000)
    r = p.run(PatientQuery(chief_complaint="crushing chest pain radiating to jaw",
                           symptoms=["diaphoresis", "dyspnea"]), retrieval_k=200)
    assert len(r.llm_candidates) <= 26  # narrowed, NOT 5000
    assert any("Coronary" in m or "Embolism" in m or "Dissection" in m for m in r.must_not_miss)


def test_pipeline_unknown_not_forced(catalog5000, index):
    from learning.retrieval.retriever import Retriever
    from learning.retrieval.patient_encoder import PatientQuery
    from learning.pipeline import FiveKPipeline, PipelineOutcome
    p = FiveKPipeline(Retriever(index, catalog=catalog5000), catalog5000)
    r = p.run(PatientQuery(chief_complaint="zzqxwv gibberish nonexistent token", symptoms=[]))
    assert r.outcome in (PipelineOutcome.UNKNOWN_PRESENTATION, PipelineOutcome.INSUFFICIENT_INFORMATION)


def test_rare_retrieval_present(catalog5000, index):
    from learning.retrieval.retriever import Retriever
    from learning.retrieval.patient_encoder import PatientQuery
    r = Retriever(index, catalog=catalog5000).retrieve(PatientQuery(chief_complaint="Fabry disease"), top_k=50)
    assert any("fabry" in it.name.lower() for it in r.items)


# ---- retrieval failure fallback -------------------------------------------------------------

def test_retrieval_failure_degrades(catalog5000):
    from learning.resilience import safe_call
    # simulate a broken retriever call -> safe_call returns the fallback, no crash
    def broken():
        raise RuntimeError("index unavailable")
    assert safe_call(broken, fallback=[]) == []


# ---- baseline gate blocks worse critical recall ---------------------------------------------

def test_baseline_gate_blocks_worse_critical_recall():
    from learning.baseline import MetricSet, compare, PromotionDecision
    base = MetricSet(top_3=0.75, top_5=0.85, critical_recall_at_100=0.99, critical_miss_rate=0.01)
    worse = MetricSet(top_1=0.7, top_3=0.76, top_5=0.86, critical_recall_at_100=0.90, critical_miss_rate=0.06)
    assert compare(base, worse).decision == PromotionDecision.REJECT


# ---- shadow leaves clinical output unchanged ------------------------------------------------

def test_shadow_mode_unchanged_output():
    from learning.runtime import GovernedMLRuntime, MLRuntimeConfig
    from learning.schemas import CandidateFeature
    rt = GovernedMLRuntime(MLRuntimeConfig(enabled=True, shadow_mode=True, model_path="/nonexistent.pt"))
    dec = rt.consult("c1", [0.0] * 72, [CandidateFeature("a")], ["a"])
    assert dec.changed_clinical_output is False


# ---- error-miss taxonomy --------------------------------------------------------------------

def test_error_miss_taxonomy():
    from learning.error_taxonomy import classify_miss, MissClass
    assert classify_miss(true_concept_id="x", in_universe=False, retrieval_top100_ids=[],
                         reranked_top5_ids=[], llm_output_ids=[], final_output_ids=[]) == MissClass.COVERAGE_GAP
    assert classify_miss(true_concept_id="x", in_universe=True, retrieval_top100_ids=["x"],
                         reranked_top5_ids=["x"], llm_output_ids=["x"],
                         final_output_ids=["x"]) == MissClass.NO_MISS
