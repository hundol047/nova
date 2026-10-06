"""Distinct production error types (spec: reliability -- a caller/operator must be able to tell an
LLM timeout apart from a KB load failure apart from a bad request, not see one generic 500 for
everything).

Deliberately NOT used to wrap nova_agent.orchestrator.DoctorAgent.decide() itself -- that function
already guarantees it never raises (see its own docstring/try-except), which is a deliberate
competition-mode safety property this layer must not disturb. These types are for the PRODUCTION
API/persistence/auth layer that sits around it: request validation, repository access, and the rare
case where a caller explicitly wants to distinguish "the LLM provider is down" from "the database is
down" in a health/readiness response.
"""

from __future__ import annotations


class NovaProductionError(Exception):
    """Base class for every production-layer error. Carries an `error_code` (stable, machine-
    readable, safe to put in an API response body) separate from the human-readable message."""

    error_code = "internal_error"
    http_status = 500

    def __init__(self, message: str, *, error_code: str | None = None) -> None:
        super().__init__(message)
        if error_code:
            self.error_code = error_code


class ValidationError(NovaProductionError):
    error_code = "validation_error"
    http_status = 422


class AuthenticationError(NovaProductionError):
    error_code = "authentication_error"
    http_status = 401


class AuthorizationError(NovaProductionError):
    error_code = "authorization_error"
    http_status = 403


class NotFoundError(NovaProductionError):
    error_code = "not_found"
    http_status = 404


class ConflictError(NovaProductionError):
    """Raised on an idempotency violation (a request/observation id reused with different
    content) -- distinct from a plain duplicate (which is a silent no-op, not an error)."""

    error_code = "conflict"
    http_status = 409


class LLMTimeoutError(NovaProductionError):
    error_code = "llm_timeout"
    http_status = 503


class LLMUnavailableError(NovaProductionError):
    error_code = "llm_unavailable"
    http_status = 503


class LLMInvalidOutputError(NovaProductionError):
    error_code = "llm_invalid_output"
    http_status = 502


class KnowledgeBaseError(NovaProductionError):
    error_code = "knowledge_base_error"
    http_status = 500


class PersistenceError(NovaProductionError):
    error_code = "persistence_error"
    http_status = 503


class CircuitOpenError(NovaProductionError):
    error_code = "circuit_open"
    http_status = 503
