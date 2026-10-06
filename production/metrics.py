"""In-process metrics (spec: request count, error rate, latency percentiles, LLM success/fallback/
parse-failure rates, avg turns, critical safety blocks, token usage).

Deliberately a small, dependency-free counter/histogram implementation (no prometheus_client
requirement) -- exposed as a plain dict via `snapshot()`, which `production/api.py`'s `/metrics`
(or a real deployment's Prometheus exporter sitting in front of it) can format however the
surrounding infrastructure expects. In-process only: a multi-replica deployment aggregates at the
infrastructure layer (a real Prometheus scrape per pod), not here -- this module never pretends to
be a distributed metrics store.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import Dict, List


class _Percentiles:
    def __init__(self) -> None:
        self._values: List[float] = []

    def add(self, value: float) -> None:
        self._values.append(value)
        # Bounded memory: keep only the most recent 2000 samples per series -- a percentile over a
        # recent rolling window is what an operator actually wants, not unbounded growth.
        if len(self._values) > 2000:
            self._values = self._values[-2000:]

    def percentile(self, p: float) -> float:
        if not self._values:
            return 0.0
        ordered = sorted(self._values)
        idx = min(len(ordered) - 1, int(round(p / 100.0 * (len(ordered) - 1))))
        return ordered[idx]


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = defaultdict(int)
        self._latencies: Dict[str, _Percentiles] = defaultdict(_Percentiles)

    def increment(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counters[name] += value

    def observe_latency(self, name: str, milliseconds: float) -> None:
        with self._lock:
            self._latencies[name].add(milliseconds)

    def snapshot(self) -> dict:
        with self._lock:
            counters = dict(self._counters)
            latencies = {
                name: {"p50": p.percentile(50), "p95": p.percentile(95), "p99": p.percentile(99),
                       "count": len(p._values)}
                for name, p in self._latencies.items()
            }
        request_count = counters.get("requests_total", 0)
        error_count = counters.get("errors_total", 0)
        llm_calls = counters.get("llm_calls_total", 0)
        llm_success = counters.get("llm_success_total", 0)
        llm_fallback = counters.get("llm_fallback_total", 0)
        llm_parse_failure = counters.get("llm_parse_failure_total", 0)
        return {
            "counters": counters,
            "latencies_ms": latencies,
            "derived": {
                "error_rate": round(error_count / request_count, 4) if request_count else None,
                "llm_success_rate": round(llm_success / llm_calls, 4) if llm_calls else None,
                "llm_fallback_rate": round(llm_fallback / llm_calls, 4) if llm_calls else None,
                "llm_parse_failure_rate": round(llm_parse_failure / llm_calls, 4) if llm_calls else None,
            },
        }


_registry: MetricsRegistry | None = None


def get_metrics() -> MetricsRegistry:
    global _registry
    if _registry is None:
        _registry = MetricsRegistry()
    return _registry
