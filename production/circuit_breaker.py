"""Circuit breaker for repeated LLM failures (spec: reliability -- a persistently failing LLM
provider must not be hammered forever; fail fast during an outage instead of piling up latency).

CLOSED (normal) -> after `failure_threshold` consecutive failures -> OPEN (calls short-circuit
immediately, raising CircuitOpenError, for `cooldown_seconds`) -> HALF_OPEN (one trial call allowed)
-> success closes it again, failure re-opens it for another cooldown window.

Deliberately does not sit in front of nova_agent.orchestrator.DoctorAgent.decide() itself, since
that call already never raises and already has its own internal budget/timeout degradation (spec
section 20) -- wrapping it here would just silently swallow a signal this breaker needs to see.
Instead this wraps the underlying LLM provider call in nova_agent/llm_client.py's real-provider
classes at the production call site (production/api.py), so an open circuit is visible in metrics
and in the API's /ready response rather than hidden behind decide()'s own fallback.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, TypeVar

from production.errors import CircuitOpenError

T = TypeVar("T")


@dataclass
class CircuitBreakerState:
    state: str  # "closed" | "open" | "half_open"
    consecutive_failures: int
    opened_at: float | None


class CircuitBreaker:
    def __init__(self, *, failure_threshold: int, cooldown_seconds: float, name: str = "default") -> None:
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.name = name
        self._lock = threading.Lock()
        self._state = "closed"
        self._consecutive_failures = 0
        self._opened_at: float | None = None

    def snapshot(self) -> CircuitBreakerState:
        with self._lock:
            return CircuitBreakerState(self._state, self._consecutive_failures, self._opened_at)

    def _transition_if_cooldown_elapsed(self) -> None:
        # Caller already holds self._lock.
        if self._state == "open" and self._opened_at is not None:
            if time.monotonic() - self._opened_at >= self.cooldown_seconds:
                self._state = "half_open"

    def call(self, fn: Callable[[], T]) -> T:
        with self._lock:
            self._transition_if_cooldown_elapsed()
            if self._state == "open":
                raise CircuitOpenError(
                    f"Circuit {self.name!r} is open (cooling down after {self._consecutive_failures} "
                    "consecutive failures); short-circuiting to fail fast."
                )
        try:
            result = fn()
        except Exception:
            with self._lock:
                self._consecutive_failures += 1
                if self._state == "half_open" or self._consecutive_failures >= self.failure_threshold:
                    self._state = "open"
                    self._opened_at = time.monotonic()
            raise
        else:
            with self._lock:
                self._consecutive_failures = 0
                self._state = "closed"
                self._opened_at = None
            return result

    def reset(self) -> None:
        with self._lock:
            self._state = "closed"
            self._consecutive_failures = 0
            self._opened_at = None


_breakers: dict[str, CircuitBreaker] = {}
_breakers_lock = threading.Lock()


def get_circuit_breaker(name: str, *, failure_threshold: int, cooldown_seconds: float) -> CircuitBreaker:
    with _breakers_lock:
        breaker = _breakers.get(name)
        if breaker is None:
            breaker = CircuitBreaker(failure_threshold=failure_threshold, cooldown_seconds=cooldown_seconds, name=name)
            _breakers[name] = breaker
        return breaker


def reset_all_circuit_breakers() -> None:
    """Test-only: clears the process-wide breaker registry between test cases."""
    with _breakers_lock:
        _breakers.clear()
