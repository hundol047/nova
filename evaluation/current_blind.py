"""Single source of truth for the CURRENT untouched blind evaluation set.

Historically the blind version was hard-coded in several places (verifier, docs, leakage scanner),
which drifted (the verifier kept checking v9 after v10 was frozen). This module fixes that: every
consumer derives the current blind version from CURRENT_BLIND_VERSION here, so promoting a new blind
set (e.g. v10 -> v11) is a one-line change that the verifier, leakage scanner, and reporting all
follow automatically.

Discipline reminder (unchanged): a blind set frozen BEFORE a reasoning change can no longer be the
untouched measure of the changed code. When reasoning/candidate/ranking code changes, the current
set becomes REFERENCE-ONLY and a fresh set is authored and set here.
"""

from __future__ import annotations

# The current untouched blind set. Bump this ONLY after a fresh set has been authored, frozen
# (SHA-256 in its manifest), and leakage-checked — never to point at an edited set.
CURRENT_BLIND_VERSION = "v11"

# Every blind set this repo has authored, oldest -> newest. All except CURRENT_BLIND_VERSION are
# REFERENCE-ONLY (each was frozen before a later reasoning change).
ALL_BLIND_VERSIONS = ("v3", "v4", "v5", "v6", "v8", "v9", "v10", "v11")


def reference_only_versions() -> tuple:
    """Blind versions that are REFERENCE-ONLY (everything except the current one)."""
    return tuple(v for v in ALL_BLIND_VERSIONS if v != CURRENT_BLIND_VERSION)


def blind_module_names() -> list:
    """Dotted module names for the leakage scanner (all authored sets are scanned)."""
    return [f"evaluation.blind_cases_{v}" for v in ALL_BLIND_VERSIONS]
