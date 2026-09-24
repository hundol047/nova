"""Structured logging + in-process metrics for the /v1/nova/* endpoints (main.py).

Deliberately a small, dependency-free JSON-lines logger + counter/histogram registry -- same shape
as this project's earlier standalone production/logging_config.py and production/metrics.py, but
built fresh here rather than imported from that sibling package: backend/ never depends on the
top-level production/ directory (see docs/NOVA_DEPLOYMENT.md on how the two production paths
relate), and this module is small enough that duplicating the ~80 lines is cheaper than coupling
the two.

Uses a child of the existing 'synexagent' logger (see main.py's `log=logging.getLogger('synexagent')`)
rather than inventing an unrelated logger name, so this app's existing logging configuration
(handlers, level, any log-shipping setup an operator already has) applies to N.O.V.A. log lines too
without extra wiring.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Optional

log = logging.getLogger("synexagent.nova")


class _JSONLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        extra = getattr(record, "nova_extra", None)
        if isinstance(extra, dict):
            payload.update(extra)
        return json.dumps(payload, ensure_ascii=False, default=str)


_configured = False


def _ensure_configured() -> None:
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(_JSONLineFormatter())
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False
    _configured = True


def log_event(component: str, event: str, *, request_id: str = "", case_id: str = "",
              severity: str = "INFO", latency_ms: Optional[float] = None,
              error_code: Optional[str] = None, provider: Optional[str] = None,
              model: Optional[str] = None, **extra: Any) -> None:
    """The one call site every NOVA code path should use for a structured log line. PHI-minimized
    by construction: callers pass identifiers (request_id/case_id) and structured facts (event
    name, latency, error_code, provider/model), never raw patient free text -- there is no
    `chief_complaint` or `result` parameter here on purpose."""
    _ensure_configured()
    level = getattr(logging, severity.upper(), logging.INFO)
    fields = {"request_id": request_id, "case_id": case_id, "component": component, "event": event,
              "latency_ms": latency_ms, "error_code": error_code, "provider": provider, "model": model,
              **extra}
    log.log(level, event, extra={"nova_extra": {k: v for k, v in fields.items() if v is not None}})


class _Percentiles:
    def __init__(self) -> None:
        self._values: list[float] = []

    def add(self, value: float) -> None:
        self._values.append(value)
        if len(self._values) > 2000:
            self._values = self._values[-2000:]

    def percentile(self, p: float) -> float:
        if not self._values:
            return 0.0
        ordered = sorted(self._values)
        idx = min(len(ordered) - 1, int(round(p / 100.0 * (len(ordered) - 1))))
        return ordered[idx]


class NovaMetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, int] = {}
        self._latencies: dict[str, _Percentiles] = {}

    def increment(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + value

    def observe(self, name: str, value: float) -> None:
        with self._lock:
            self._latencies.setdefault(name, _Percentiles()).add(value)

    def snapshot(self) -> dict:
        with self._lock:
            counters = dict(self._counters)
            latencies = {name: {"p50": p.percentile(50), "p95": p.percentile(95), "p99": p.percentile(99),
                                 "count": len(p._values)} for name, p in self._latencies.items()}
        llm_calls = counters.get("nova_llm_calls_total", 0)
        llm_success = counters.get("nova_llm_success_total", 0)
        llm_fallback = counters.get("nova_llm_fallback_total", 0)
        requests = counters.get("nova_requests_total", 0)
        errors = counters.get("nova_errors_total", 0)
        return {
            "counters": counters,
            "latencies_ms": latencies,
            "derived": {
                "nova_error_rate": round(errors / requests, 4) if requests else None,
                "nova_llm_success_rate": round(llm_success / llm_calls, 4) if llm_calls else None,
                "nova_llm_fallback_rate": round(llm_fallback / llm_calls, 4) if llm_calls else None,
            },
        }


_registry: Optional[NovaMetricsRegistry] = None
_registry_lock = threading.Lock()


def get_nova_metrics() -> NovaMetricsRegistry:
    global _registry
    with _registry_lock:
        if _registry is None:
            _registry = NovaMetricsRegistry()
        return _registry
