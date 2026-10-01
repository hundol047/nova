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
    if not text or re.search(r'hemoly|haemoly|pending|previous|historical|yesterday|reference|not available', text, re.I):
        return None
    match = re.search(r'\b(?:potassium|K\+?)\s*(?:is|of|=|:)?\s*(\d+(?:\.\d+)?)(?![\d.])\s*([^,;]*)', text, re.I)
    if not match:
        return None
    tail = match.group(2).strip()
    if re.match(r'(?:-|to\b|mg|g/)', tail, re.I):
        return None
    value = float(match.group(1))
    return value if 0 < value <= 15 else None
