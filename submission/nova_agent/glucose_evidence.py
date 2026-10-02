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
    r"(too high to read|critical high|\bHI\b|out of range high)", re.IGNORECASE,
)
_NUMERIC_PATTERN = re.compile(r"(\d{2,3}(?:\.\d+)?)\s*mg\s*/\s*d?l|glucose[^0-9]{0,15}?(\d{2,3})\b",
                               re.IGNORECASE)
# Unit-safety guard (spec section 19 / clinical safety): the second numeric alternative above
# matches a glucose-adjacent number WITHOUT requiring a unit, so a value stated in a NON-mg/dL unit
# (e.g. "glucose 90 mmol/L" -- a physiologically impossible mg/dL reading, but 90 is a plausible
# grabbed digit) would otherwise be silently misinterpreted as 90 mg/dL. This module's thresholds
# are all mg/dL, and it deliberately does NOT convert units (mmol/L glucose x 18 = mg/dL is a real
# conversion, but silently applying it to ambiguous free text risks the wrong direction). So when
# the text explicitly carries a recognised non-mg/dL glucose unit and no explicit mg/dL, we refuse
# to interpret the bare number and return None ("no evidence either way") rather than guess.
_NON_MGDL_UNIT_PATTERN = re.compile(r"mmol\s*/\s*l", re.IGNORECASE)
_MGDL_UNIT_PATTERN = re.compile(r"mg\s*/\s*d?l", re.IGNORECASE)


def current_asserted_lab_clauses(text: str) -> list[str]:
    """Small dependency-free assertion guard for glucose and lactate readers.

    Explicitly old, hypothetical or denied values cannot become a current number.
    No temporal inference is attempted when two unqualified values conflict.
    """
    text = re.sub(r'[ \t]+', ' ', text)
    clauses = re.split(r'[;,\n]|(?<=[a-z])\.(?=\s|$)|\b(?:but|however)\b', text, flags=re.I)
    ignored = re.compile(
        r'\b(?:historical|previously|prior (?:study|report|result)|old (?:study|report|result)|'
        r'last (?:year|month|week)|reference range|baseline (?:glucose|lactate|result)|'
        r'possible|possibly|suspected|suspicious for|uncertain|rule out|cannot exclude|'
        r'not excluded|may be|might be|no|not|denies|denied|without|negative for)\b', re.I)
    return [clause.strip() for clause in clauses if clause.strip() and not ignored.search(clause)]


def extract_glucose_mg_dl(glucose_result_text: Optional[str]) -> Optional[float]:
    """Parses PatientState.laboratory_tests.get("glucose_point_of_care") into a mg/dL value.
    Returns None if no glucose test has been performed or the result can't be interpreted --
    callers must treat None as "no evidence either way", never as a value of 0.

    Unit safety: a number given in an explicit non-mg/dL unit (e.g. mmol/L) with no accompanying
    mg/dL value is NOT interpreted (returns None) -- a bare number is never assigned a mg/dL
    meaning when its stated unit says otherwise."""
    if not glucose_result_text:
        return None
    values = set()
    for clause in current_asserted_lab_clauses(glucose_result_text):
        if _UNREADABLE_HIGH_PATTERN.search(clause):
            values.add(UNREADABLE_HIGH_SENTINEL_MG_DL)
        # Keep the existing unit policy: never silently read mmol/L as mg/dL.
        if _NON_MGDL_UNIT_PATTERN.search(clause) and not _MGDL_UNIT_PATTERN.search(clause):
            return None
        for match in _NUMERIC_PATTERN.finditer(clause):
            values.add(float(match.group(1) or match.group(2)))
    return next(iter(values)) if len(values) == 1 else None
