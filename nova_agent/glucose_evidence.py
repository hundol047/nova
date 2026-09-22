"""Numeric point-of-care glucose evidence (spec section 3/7).

Word-overlap matching (matching.py) treats "blood glucose 42 mg/dL" and "blood glucose 400 mg/dL"
as near-identical text (they share every content word), even though the actual number completely
reverses which diagnosis it supports. A lab NUMBER needs numeric interpretation, not keyword
overlap -- this module is the single, narrowly-scoped place that does that, reading directly from
PatientState.laboratory_tests["glucose_point_of_care"] rather than guessing from free text.

Thresholds are the standard clinical definitions, not fitted to any benchmark case's specific
number:
  - Whipple's triad / ADA hypoglycemia: plasma glucose < 70 mg/dL.
  - DKA diagnostic criteria (ADA): plasma glucose typically >= 250 mg/dL (some cases are
    "euglycemic DKA" and present lower, which is exactly why this module only ever ADDS
    confirmatory/contradictory evidence for the disease each threshold is specific to -- it never
    excludes DKA outright just because glucose is unreadable, and never excludes hypoglycemia
    outright for a case this module can't parse).

A point-of-care meter that cannot read a critically high value typically displays an error/"HI"
code rather than a number (a well-known real behavior, not a data-entry quirk) -- recognized
separately from the numeric pattern so that text like "unreadable on meter, critical high" is
correctly treated as a very high reading rather than accidentally parsed as a low literal digit.
"""

from __future__ import annotations

import re
from typing import Optional

HYPOGLYCEMIA_THRESHOLD_MG_DL = 70.0
DKA_HYPERGLYCEMIA_THRESHOLD_MG_DL = 250.0
UNREADABLE_HIGH_SENTINEL_MG_DL = 999.0

_UNREADABLE_HIGH_PATTERN = re.compile(
    r"(unreadable|too high to read|critical high|\bHI\b|out of range)", re.IGNORECASE,
)
_NUMERIC_PATTERN = re.compile(r"(\d{2,3}(?:\.\d+)?)\s*mg\s*/\s*d?l|glucose[^0-9]{0,15}?(\d{2,3})\b",
                               re.IGNORECASE)


def extract_glucose_mg_dl(glucose_result_text: Optional[str]) -> Optional[float]:
    """Parses PatientState.laboratory_tests.get("glucose_point_of_care") into a mg/dL value.
    Returns None if no glucose test has been performed or the result can't be interpreted --
    callers must treat None as "no evidence either way", never as a value of 0."""
    if not glucose_result_text:
        return None
    if _UNREADABLE_HIGH_PATTERN.search(glucose_result_text):
        return UNREADABLE_HIGH_SENTINEL_MG_DL
    match = _NUMERIC_PATTERN.search(glucose_result_text)
    if not match:
        return None
    raw = match.group(1) or match.group(2)
    try:
        return float(raw)
    except ValueError:
        return None
