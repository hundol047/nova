"""Competition-safe CPU latency for the retrieval/rerank stages -- loose bounds (this is a shared
sandbox machine, not a dedicated benchmark rig) that would still catch a real performance
regression (e.g. an accidental per-turn index rebuild, or an unbounded query blow-up)."""

from __future__ import annotations

import time

from nova_agent.differential import DifferentialEngine
from nova_agent.open_world import OpenWorldRetriever
from nova_agent.ontology.registry import get_default_catalog
from nova_agent.retrieval_pipeline import lightweight_rerank, retrieve_high_recall
from nova_agent.state import PatientState


def test_retrieval_and_rerank_stay_well_under_one_second_per_turn():
    retriever = OpenWorldRetriever(get_default_catalog())
    samples = []
    for _ in range(10):
        t0 = time.perf_counter()
        retrieved = retrieve_high_recall(
            retriever, chief_complaint="sudden severe chest pain radiating to the back",
            symptoms=["chest_pain", "dyspnea"], objective_finding_phrases=["elevated troponin"],
            retrieval_top_k=150,
        )
        lightweight_rerank(retrieved, rerank_top_k=25)
        samples.append(time.perf_counter() - t0)
    samples.sort()
    p95 = samples[min(len(samples) - 1, int(len(samples) * 0.95))]
    assert p95 < 1.0, f"retrieval+rerank p95 {p95 * 1000:.1f}ms exceeds the 1s competition-safe budget"


def test_full_differential_update_stays_well_under_two_seconds_in_competition_mode(monkeypatch):
    import os

    saved_env = dict(os.environ)
    try:
        os.environ["NOVA_LLM_PROVIDER"] = "competition"
        os.environ["NOVA_COMPETITION_RETRIEVAL"] = "true"
        from nova_agent.config import get_config
        get_config(reload=True)

        samples = []
        for i in range(5):
            state = PatientState(case_id=f"latency-{i}", chief_complaint="sudden severe chest pain")
            t0 = time.perf_counter()
            DifferentialEngine().update(state)
            samples.append(time.perf_counter() - t0)
        assert max(samples) < 2.0
    finally:
        os.environ.clear()
        os.environ.update(saved_env)
        from nova_agent.config import get_config
        get_config(reload=True)


def test_catalog_index_is_built_once_not_per_call():
    """The catalog (and its search index) must be a cached singleton -- the actual cache-reuse
    guarantee is covered in depth by tests/test_retrieval_cache_reuse.py; this test only asserts
    the specific object identity holds across the retrieval call path used in this file."""
    first = get_default_catalog()
    second = get_default_catalog()
    assert first is second
