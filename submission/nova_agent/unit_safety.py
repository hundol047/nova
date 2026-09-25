"""Deterministic lab-unit safety guard (spec section 19 / clinical safety).

A numeric lab interpretation is only valid in the unit its thresholds are defined for. A bare number
grabbed out of free text can carry a DIFFERENT unit than expected -- e.g. creatinine reported in the
SI unit "90 umol/L" (= 1.0 mg/dL, normal) would, against mg/dL thresholds, look like 90 (>> a
critical value); or hemoglobin "70 g/L" (= 7 g/dL, critically low) would look like 70 (normal),
HIDING a critical anemia. This is the same bug class already fixed for glucose (mmol/L vs mg/dL).

This module is intentionally dependency-free (no pydantic, no PatientState import) so its logic can
be unit-tested in isolation in any environment. It never CONVERTS units (silently applying a
conversion factor to ambiguous free text risks the wrong direction); when it detects a value stated
in a disallowed unit and no accompanying value in an allowed unit, it reports that the number must
NOT be interpreted -- callers then treat it as "no numeric evidence either way", never fabricate a
value.
"""

from __future__ import annotations

import re
from typing import Iterable, Optional

# Canonical unit token patterns. Kept as word/symbol-boundary-ish regexes so "mg/dl" matches
# "mg/dL", "mg / dL", "mg/dl" but not a substring of another token.
_UNIT_PATTERNS = {
    "mg/dl": re.compile(r"mg\s*/\s*d?l", re.IGNORECASE),
    "mmol/l": re.compile(r"mmol\s*/\s*l", re.IGNORECASE),
    "umol/l": re.compile(r"(?:umol|µmol|μmol)\s*/\s*l", re.IGNORECASE),
    "meq/l": re.compile(r"meq\s*/\s*l", re.IGNORECASE),
    "g/dl": re.compile(r"\bg\s*/\s*dl", re.IGNORECASE),           # requires the 'd' (dL), not g/L
    "g/l": re.compile(r"(?<![mµμa-z])g\s*/\s*l\b", re.IGNORECASE), # g/L but not mg/L / µg/L / dg/L
}


def unit_present(text: str, unit_key: str) -> bool:
    """True if `text` contains the given canonical unit token."""
    pat = _UNIT_PATTERNS.get(unit_key)
    return bool(pat and text and pat.search(text))


def value_is_in_disallowed_unit(text: Optional[str], allowed_units: Iterable[str],
                                 disallowed_units: Iterable[str]) -> bool:
    """Returns True when the text explicitly states a DISALLOWED unit and does NOT also state any
    ALLOWED unit -- i.e. the bare number would be misinterpreted if read against the allowed-unit
    thresholds, so the caller must refuse to interpret it.

    - If an allowed unit IS present (even alongside a disallowed one, e.g. "1.0 mg/dL (90 umol/L)"),
      returns False -- the allowed-unit value can be parsed safely.
    - If neither an allowed nor a disallowed unit is stated, returns False -- unit is unspecified,
      and the existing name-anchored numeric parse proceeds (unchanged behavior; this guard only
      fires on an explicit wrong unit).
    """
    if not text:
        return False
    allowed = list(allowed_units or [])
    disallowed = list(disallowed_units or [])
    if any(unit_present(text, u) for u in allowed):
        return False
    return any(unit_present(text, u) for u in disallowed)
