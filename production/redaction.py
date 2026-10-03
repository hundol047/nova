"""Logging/PHI redaction (spec: minimize sensitive identifiers reaching logs, never assume free
text is safe to log verbatim).

Deliberately conservative and pattern-based (no NLP dependency, consistent with the rest of this
codebase's determinism requirements) -- it cannot catch every possible identifier in free text
(that is an open research problem), so the real privacy control is `production/config.py`'s
`log_raw_chief_complaint_text` (defaults to False): structured clinical fields are logged, raw
patient-authored free text is not, by default. This module is a defense-in-depth layer for the
cases where some free text is logged anyway (e.g. an explicit debug flag), not the primary control.
"""

from __future__ import annotations

import re

_EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE_PATTERN = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{4}\b")
_SSN_LIKE_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b|\b\d{6}-\d{7}\b")  # US SSN / KR resident-registration shape
_LONG_DIGIT_RUN_PATTERN = re.compile(r"\b\d{9,}\b")  # any other long identifier-shaped digit run

_REDACTION_PATTERNS = [
    (_EMAIL_PATTERN, "[REDACTED_EMAIL]"),
    (_SSN_LIKE_PATTERN, "[REDACTED_ID]"),
    (_PHONE_PATTERN, "[REDACTED_PHONE]"),
    (_LONG_DIGIT_RUN_PATTERN, "[REDACTED_NUMBER]"),
]


def redact(text: str) -> str:
    """Best-effort redaction of common structured-identifier SHAPES (email/phone/national-ID-like
    digit runs) from free text. Never a substitute for not logging raw PHI in the first place."""
    if not text:
        return text
    redacted = text
    for pattern, replacement in _REDACTION_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def redact_dict(data: dict, *, free_text_keys: tuple = ("chief_complaint", "content", "message", "text")) -> dict:
    """Applies `redact()` to string values under the given keys (recursively for nested dicts) --
    used by logging_config.py's structured log formatter, never mutates the caller's object."""
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = redact_dict(value, free_text_keys=free_text_keys)
        elif isinstance(value, str) and key in free_text_keys:
            result[key] = redact(value)
        else:
            result[key] = value
    return result
