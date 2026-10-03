"""De-identification for the learning pipeline (dependency-free).

Before ANY clinical record enters the training data path it must be stripped of direct identifiers
and its patient id replaced with a stable, non-reversible pseudonym (HMAC-SHA256 with an operator
secret). This lets us do patient-level splitting without ever storing PHI in the dataset.

This module NEVER emits the removed identifiers. If the operator secret is not configured, keying
falls back to a per-run random salt (still non-reversible) but WITHOUT cross-run stability — callers
that need stable patient-level splits must configure NOVA_DEID_SECRET.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from typing import Dict, List

# Fields that must never survive into the dataset. Not exhaustive of all PHI, but the direct
# identifiers we explicitly refuse to carry. Free-text fields are dropped wholesale by allow-listing
# clinical features instead of block-listing identifiers (see build_feature_record).
DIRECT_IDENTIFIER_KEYS = frozenset({
    "name", "first_name", "last_name", "full_name", "mrn", "ssn", "phone", "email",
    "address", "dob", "date_of_birth", "national_id", "insurance_id", "face_photo",
    "device_id", "ip_address",
})

_RUN_SALT = secrets.token_hex(16)  # per-process fallback salt (non-stable across runs)


def _key() -> bytes:
    secret = os.environ.get("NOVA_DEID_SECRET")
    if secret:
        return secret.encode("utf-8")
    return _RUN_SALT.encode("utf-8")


def pseudonymize(patient_id: str) -> str:
    """Stable (if NOVA_DEID_SECRET set) non-reversible pseudonym for a patient id."""
    mac = hmac.new(_key(), str(patient_id).encode("utf-8"), hashlib.sha256).hexdigest()
    return f"pt_{mac[:24]}"


def has_stable_secret() -> bool:
    return bool(os.environ.get("NOVA_DEID_SECRET"))


def strip_identifiers(record: Dict) -> Dict:
    """Return a copy with direct-identifier keys removed. Does NOT attempt to scrub free text —
    the feature builder allow-lists clinical fields rather than trusting this to catch everything."""
    return {k: v for k, v in record.items() if k.lower() not in DIRECT_IDENTIFIER_KEYS}


@dataclass(frozen=True)
class DeidReport:
    removed_keys: List[str]
    stable: bool


def audit_record(record: Dict) -> DeidReport:
    removed = [k for k in record if k.lower() in DIRECT_IDENTIFIER_KEYS]
    return DeidReport(removed_keys=sorted(removed), stable=has_stable_secret())
