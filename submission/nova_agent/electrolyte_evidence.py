"""Numeric potassium evidence from the BMP, never symptom-keyword inference.

Severe hyperkalaemia threshold: UK Kidney Association, 2023 guideline 4.1,
https://www.ukkidney.org/sites/default/files/FINAL%20VERSION%20-%20UKKA%20CLINICAL%20PRACTICE%20GUIDELINE%20-%20MANAGEMENT%20OF%20HYPERKALAEMIA%20IN%20ADULTS%20-%20191223.pdf
Only an internal diagnostic evidence feature, not a treatment recommendation.
Unitless BMP potassium is assumed mmol/L (same numeric scale as mEq/L).
Explicit unsupported units, ranges, historical/hemolysed results stay unknown.
"""
import re
from typing import Optional

SEVERE_POTASSIUM_MMOL_L = 6.5

def extract_potassium_mmol_l(text: Optional[str]) -> Optional[float]:
    """Accept only unambiguous point values in supported units, never guess a conversion."""
    if not text or re.search(r'hemoly|haemoly|pending|previous|historical|yesterday|reference|not available|'
                             r'possibl|suspect|unconfirmed|not confirmed|inconclusive|\?', text, re.I):
        return None
    matches = list(re.finditer(r'\b(?:potassium|K\+?)\s*(?:is|of|=|:)?\s*'
                               r'(\d+(?:\.\d+)?)(?![\d.])\s*([^,;\n]*)', text, re.I))
    if not matches:
        return None
    values = []
    for match in matches:
        prefix = re.split(r'[,;\n]', text[:match.start()])[-1]
        if re.search(r'\b(?:no|not|without|denies)\b', prefix, re.I):
            return None
        # Decimal commas cannot be silently truncated to an integer.
        if re.match(r',\d', text[match.end():]):
            return None
        tail = match.group(2).strip()
        # A closed unit grammar rejects mol/L, mEq/dL, ranges and scientific notation.
        # Missing units retain the existing BMP mmol/L convention.
        if not re.fullmatch(r'(?:(?:mmol|mEq)\s*/\s*L)?\s*(?:high|elevated|normal|low)?\s*\.?', tail, re.I):
            return None
        value = float(match.group(1))
        if not 0 < value <= 15:
            return None
        values.append(value)
    # Conflicting repeats require clarification; taking the first can reverse the result.
    return values[0] if len(set(values)) == 1 else None
