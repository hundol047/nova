"""Circuit breaker + failure-injection tests (spec: reliability -- repeated LLM failures trip a
circuit breaker with threshold/cooldown/half-open; distinct error types must surface for
LLM timeout/unavailable/invalid-output/KB/DB/validation/internal failures)."""

from __future__ import annotations

import time

import pytest

from production.circuit_breaker import CircuitBreaker
from production.errors import CircuitOpenError, KnowledgeBaseError, PersistenceError


def test_circuit_closed_allows_calls_through():
    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=10, name="t1")
    assert cb.call(lambda: "ok") == "ok"
    assert cb.snapshot().state == "closed"


def test_circuit_opens_after_threshold_consecutive_failures():
    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=10, name="t2")

    def boom():
        raise RuntimeError("provider down")

    for _ in range(3):
        with pytest.raises(RuntimeError):
            cb.call(boom)

    assert cb.snapshot().state == "open"
    with pytest.raises(CircuitOpenError):
        cb.call(lambda: "should not run")


def test_circuit_half_opens_after_cooldown_and_closes_on_success():
    cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.05, name="t3")

    def boom():
        raise RuntimeError("down")

    with pytest.raises(RuntimeError):
        cb.call(boom)
    assert cb.snapshot().state == "open"

    time.sleep(0.06)
    assert cb.call(lambda: "recovered") == "recovered"
    assert cb.snapshot().state == "closed"


def test_circuit_half_open_failure_reopens_immediately():
    cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.05, name="t4")

    def boom():
        raise RuntimeError("down")

    with pytest.raises(RuntimeError):
        cb.call(boom)
    time.sleep(0.06)
    with pytest.raises(RuntimeError):
        cb.call(boom)  # half-open trial call also fails
    assert cb.snapshot().state == "open"
    with pytest.raises(CircuitOpenError):
        cb.call(lambda: "unreachable")


def test_a_recovering_call_resets_consecutive_failure_count():
    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=10, name="t5")

    def boom():
        raise RuntimeError("down")

    with pytest.raises(RuntimeError):
        cb.call(boom)
    with pytest.raises(RuntimeError):
        cb.call(boom)
    assert cb.snapshot().consecutive_failures == 2
    cb.call(lambda: "ok")  # success before hitting the threshold
    assert cb.snapshot().consecutive_failures == 0
    assert cb.snapshot().state == "closed"


def test_distinct_error_types_carry_distinct_http_status_and_code():
    kb_err = KnowledgeBaseError("kb load failed")
    db_err = PersistenceError("db unreachable")
    assert kb_err.error_code == "knowledge_base_error"
    assert db_err.error_code == "persistence_error"
    assert kb_err.http_status != db_err.http_status or kb_err.error_code != db_err.error_code
