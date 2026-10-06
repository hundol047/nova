"""Retrieval index caching: the DiseaseCatalog (and the search index it builds once from bundled
JSON) must be a process-wide singleton, never rebuilt on every turn. See
nova_agent/ontology/registry.py's get_default_catalog()."""

from __future__ import annotations

import time

from nova_agent.ontology.registry import get_default_catalog
from nova_agent.open_world import OpenWorldRetriever


def test_get_default_catalog_returns_the_same_cached_object_across_calls():
    first = get_default_catalog()
    second = get_default_catalog()
    assert first is second, "the catalog (and its search index) must be built once and reused"


def test_repeated_retrieval_does_not_pay_a_rebuild_cost_each_call():
    """Not a strict performance assertion (timing is environment-dependent) -- just proves later
    calls are not paying a repeated index-construction cost an order of magnitude larger than a
    plain search, which is what a per-turn rebuild would look like."""
    retriever = OpenWorldRetriever(get_default_catalog())
    # Warm up (first call may pay any one-time lazy-init cost inside the search path itself).
    retriever.retrieve("chest pain", limit=10)

    samples = []
    for _ in range(20):
        t0 = time.perf_counter()
        retriever.retrieve("chest pain", limit=10)
        samples.append(time.perf_counter() - t0)

    avg = sum(samples) / len(samples)
    assert avg < 0.05, f"a single retrieval call averaged {avg * 1000:.2f}ms -- looks like a rebuild, not a lookup"
