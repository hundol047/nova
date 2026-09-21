"""Optional bridge to the vendored SynexAgent backend (``backend/app``).

nova_agent's core data model (PatientState, Medication, Allergy, VitalSigns -- see
nova_agent/models.py) has NO dependency on backend/ any more (spec section 17): a competition
submission of nova_agent alone works without backend/ present at all.

This module remains only for the few backend pieces nova_agent optionally reuses when backend/
*is* available (this repo's normal layout): SynexAgent's own audit log store and its terminology
reference-table normalizer. Both degrade to a harmless in-memory/no-op fallback when backend/ is
missing, so importing this module never fails and never requires backend/.
"""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if _BACKEND_DIR.is_dir() and str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

try:
    from app.services.audit import AuditStore  # noqa: E402
    from app.services.terminology_mapper import normalize_condition  # noqa: E402

    SYNEX_AVAILABLE = True
except Exception:  # pragma: no cover - exercised by the standalone-without-backend test
    SYNEX_AVAILABLE = False

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


__all__ = ["SYNEX_AVAILABLE", "AuditStore", "normalize_condition"]
