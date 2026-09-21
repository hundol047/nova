"""Bootstraps imports from the vendored SynexAgent backend (``backend/app``) so nova_agent can
reuse its patient-data schemas, deterministic clinical-summary style, terminology reference
tables, and audit log store instead of re-implementing them.

SynexAgent's own test suite (backend/tests/conftest.py) establishes the convention of putting
``backend/`` on sys.path and importing its FastAPI package as top-level ``app`` -- this module
follows the same convention so nova_agent and backend never diverge on how they reach each other.
"""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if _BACKEND_DIR.is_dir() and str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

try:
    from app.schemas import (  # noqa: E402
        Allergy,
        Diagnosis as SynexDiagnosis,
        Lab,
        Medication,
        VitalSigns,
    )
    from app.services.audit import AuditStore  # noqa: E402
    from app.services.terminology_mapper import normalize_condition  # noqa: E402
    from app.services.vitals import assess as assess_vitals  # noqa: E402

    SYNEX_AVAILABLE = True
except Exception:  # pragma: no cover - defensive: nova_agent must run even if backend/ is absent
    SYNEX_AVAILABLE = False

    Allergy = Medication = Lab = VitalSigns = SynexDiagnosis = None  # type: ignore

    class AuditStore:  # type: ignore
        """Fallback no-op store used only if the vendored backend package is missing."""

        def __init__(self, *a, **k):
            self._events: list = []

        def record(self, pid, event, detail, user_id=None, role=None):
            self._events.append((pid, event, detail))

        def list(self, pid):
            return [e for e in self._events if e[0] == pid]

    def normalize_condition(text):  # type: ignore
        return []

    def assess_vitals(vitals):  # type: ignore
        return {"flags": {}, "bmi": None}


__all__ = [
    "SYNEX_AVAILABLE",
    "Allergy",
    "Medication",
    "Lab",
    "VitalSigns",
    "SynexDiagnosis",
    "AuditStore",
    "normalize_condition",
    "assess_vitals",
]
