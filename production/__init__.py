"""Production runtime for the N.O.V.A. Doctor Agent -- a separate deployment surface from
`competition/` (the competition-protocol adapter) and `submission/` (the minimal-dependency
competition artifact).

This package is NEVER imported by `nova_agent/`, `competition/`, or `submission/`, and
`scripts/build_nova_submission.py` never copies it into `submission/` -- production-only
dependencies (FastAPI, uvicorn, a persistence driver) and features (auth, audit, observability)
must never add weight to or risk breaking the competition artifact's minimal-dependency, rules-
compliant footprint. See docs/nova/architecture.md for the full production/competition split.
"""

from __future__ import annotations

AGENT_VERSION = "0.1.0"
SCHEMA_VERSION = "1"
