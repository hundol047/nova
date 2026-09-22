"""Parses a free-text vital-signs EXAM result (e.g. "BP 90/60, HR 130, RR 28, Temp 39.5, SpO2 88%")
into a structured VitalSigns record (spec section 5/24D) so SafetyLayer's vital_sign_red_flags
rules actually have structured data to evaluate, not just the raw string sitting unused in
physical_examinations.

Deliberately regex-based (no NLP dependency): the vital_signs EXAM catalog entry always describes
the same handful of measurements, so a fixed set of patterns covers real inputs (including
mock/competition-generated ones) without needing an LLM call just to extract numbers.
"""

from __future__ import annotations

import re
from typing import List, Optional

from nova_agent.knowledge.retrieval import vital_sign_red_flags
from nova_agent.models import VitalSigns

_OPS = {">=": lambda v, t: v >= t, "<=": lambda v, t: v <= t, ">": lambda v, t: v > t, "<": lambda v, t: v < t}

_BP = re.compile(r"\b(?:bp|blood pressure)\s*[:\s]*?(\d{2,3})\s*/\s*(\d{2,3})", re.IGNORECASE)
_HR = re.compile(r"\b(?:hr|heart rate|pulse)\s*[:\s]*?(\d{2,3})\b", re.IGNORECASE)
_RR = re.compile(r"\b(?:rr|respiratory rate|resp(?:iration)? rate)\s*[:\s]*?(\d{1,2})\b", re.IGNORECASE)
_TEMP = re.compile(r"\b(?:temp(?:erature)?)\s*[:\s]*?(\d{2,3}(?:\.\d)?)\s*(f|fahrenheit)?", re.IGNORECASE)
_SPO2 = re.compile(r"\b(?:spo2|sp02|o2 sat(?:uration)?|oxygen saturation)\s*[:\s]*?(\d{2,3})\s*%?", re.IGNORECASE)


def _fahrenheit_to_celsius(f: float) -> float:
    return round((f - 32) * 5.0 / 9.0, 1)


def parse_vital_signs(text: str) -> Optional[VitalSigns]:
    """Returns None only if the text contains no recognizable vital at all (e.g. an EXAM result
    that never got a scripted/real value) -- callers should not assume a non-None return means
    every field was found, only that at least one was."""
    if not text:
        return None

    sbp = dbp = heart_rate = respiratory_rate = spo2 = None
    temperature_c = None

    bp_match = _BP.search(text)
    if bp_match:
        sbp, dbp = int(bp_match.group(1)), int(bp_match.group(2))

    hr_match = _HR.search(text)
    if hr_match:
        heart_rate = int(hr_match.group(1))

    rr_match = _RR.search(text)
    if rr_match:
        respiratory_rate = int(rr_match.group(1))

    temp_match = _TEMP.search(text)
    if temp_match:
        value = float(temp_match.group(1))
        temperature_c = _fahrenheit_to_celsius(value) if temp_match.group(2) else value

    spo2_match = _SPO2.search(text)
    if spo2_match:
        spo2 = int(spo2_match.group(1))

    if not any([sbp, dbp, heart_rate, respiratory_rate, temperature_c, spo2]):
        return None

    try:
        return VitalSigns(sbp=sbp, dbp=dbp, heart_rate=heart_rate, respiratory_rate=respiratory_rate,
                           temperature_c=temperature_c, spo2=spo2, raw_text=text)
    except Exception:
        # An extracted number fell outside VitalSigns' physiologic validation range (e.g. a typo'd
        # observation) -- keep the raw text available elsewhere (physical_examinations) but don't
        # let a single malformed vital crash the turn (spec section 20).
        return None


def describe_vital_sign_abnormalities(vitals: VitalSigns) -> List[str]:
    """Turns structured vital-sign values into short descriptive clinical findings (e.g. "Marked
    tachycardia", "Hypotension / shock") using the SAME threshold table safety.py's
    vital_sign_red_flags rules use -- a single source of truth for what counts as abnormal.

    Without this, a disease's vital-sign-phrased typical_features (e.g. sepsis's "tachycardia",
    "hypotension", "tachypnea") could never be credited by differential.py's keyword matcher: the
    only thing vital_signs EXAM results ever contributed to the evidence corpus was the raw numeric
    string ("BP 84/52, HR 128..."), which no typical_feature phrase keyword-matches. safety.py's
    vital_sign_red_flags already computed these same abnormalities for safety-flag purposes; this
    just also surfaces them as plain-text findings so ranking (not only safety flagging) benefits."""
    values = vitals.model_dump()
    findings: List[str] = []
    for rule in vital_sign_red_flags():
        value = values.get(rule["field"])
        if value is None:
            continue
        if _OPS[rule["op"]](value, rule["value"]):
            findings.append(rule["reason"])
    return findings
