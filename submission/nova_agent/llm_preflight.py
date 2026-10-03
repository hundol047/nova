"""Transport readiness facts, not proof of model weights or a competition wire contract."""
from dataclasses import asdict, dataclass
from enum import Enum


class PreflightStatus(str, Enum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    INVALID_CONFIGURATION = "INVALID_CONFIGURATION"
    ENDPOINT_UNREACHABLE = "ENDPOINT_UNREACHABLE"
    AUTH_FAILED = "AUTH_FAILED"
    MODEL_MISMATCH = "MODEL_MISMATCH"
    REVISION_MISMATCH = "REVISION_MISMATCH"
    STRUCTURED_OUTPUT_FAILED = "STRUCTURED_OUTPUT_FAILED"
    REAL_CALL_FAILED = "REAL_CALL_FAILED"
    REAL_CALL_VERIFIED = "REAL_CALL_VERIFIED"
    OFFICIAL_SCHEMA_UNVERIFIED = "OFFICIAL_SCHEMA_UNVERIFIED"
    READY = "READY"


class ProbeFailure(ValueError):
    def __init__(self, status):
        self.status = status
        super().__init__(status.value)


@dataclass
class PreflightResult:
    status: PreflightStatus
    endpoint_configured: bool
    host: str | None = None
    model: str | None = None
    expected_revision: str | None = None
    revision_status: str = "NOT_VERIFIABLE_FROM_RUNTIME"
    attempts: int = 0
    latency_seconds: float | None = None
    http_status_category: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    identity_basis: str = "SERVER_REPORTED; NOT WEIGHT ATTESTATION"

    @property
    def runtime_ready(self):
        return self.status == PreflightStatus.REAL_CALL_VERIFIED

    def as_dict(self):
        return {**asdict(self), "status": self.status.value, "runtime_ready": self.runtime_ready}
