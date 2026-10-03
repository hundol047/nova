"""Structured JSON logging (spec: observability -- every log line machine-parseable, PHI-minimized
by default).

Deliberately stdlib-`logging`-based (a `logging.Formatter` subclass), not a third-party structured-
logging dependency -- keeps the production extra dependency surface small and auditable.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any, Optional

from production.redaction import redact_dict

_REQUIRED_FIELDS = ("request_id", "case_id", "component", "event")


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # logging.Formatter.formatTime() delegates to time.strftime(), which does not support
        # %f (microseconds) -- it would render the literal string "%f" instead. Use datetime
        # directly for a real, parseable ISO-8601 timestamp with microsecond precision.
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )
        payload: dict[str, Any] = {
            "timestamp": timestamp,
            "severity": record.levelname,
            "message": record.getMessage(),
        }
        extra = getattr(record, "nova_extra", None)
        if isinstance(extra, dict):
            payload.update(redact_dict(extra))
        if record.exc_info:
            payload["error_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("nova.production")
    logger.setLevel(level)
    logger.handlers.clear()
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger


_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    global _logger
    if _logger is None:
        _logger = configure_logging()
    return _logger


def log_event(component: str, event: str, *, request_id: str = "", case_id: str = "",
              severity: str = "INFO", latency_ms: Optional[float] = None,
              error_type: Optional[str] = None, **extra: Any) -> None:
    """The single call site every production module should use for a structured log line --
    consistent shape (request_id/case_id/component/event/latency/error_type), never an ad hoc
    `logger.info(f"...")` string that a log pipeline can't reliably parse."""
    logger = get_logger()
    level = getattr(logging, severity.upper(), logging.INFO)
    fields = {
        "request_id": request_id, "case_id": case_id, "component": component, "event": event,
        "latency_ms": latency_ms, "error_type": error_type, **extra,
    }
    logger.log(level, event, extra={"nova_extra": {k: v for k, v in fields.items() if v is not None}})


def timed_event(component: str, event: str, start_time: float, **extra: Any) -> None:
    log_event(component, event, latency_ms=round((time.monotonic() - start_time) * 1000, 2), **extra)
