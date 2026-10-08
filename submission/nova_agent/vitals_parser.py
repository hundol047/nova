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
# ANY blood-pressure-shaped number pair, not just ones with a leading "BP"/"blood pressure" label
# -- used only to detect a SECOND bilateral reading in the same text (e.g. "BP 180/60 right arm,
# 130/50 left arm"), where the second pair often has no repeated label. Gated below on the text
# also naming both sides explicitly, so an unrelated pair of numbers is never misread as a limb.
_BP_PAIR = re.compile(r"\b(\d{2,3})\s*/\s*(\d{2,3})\b")
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
    sbp_arm_differential = None

    bp_match = _BP.search(text)
    if bp_match:
        sbp, dbp = int(bp_match.group(1)), int(bp_match.group(2))

    # Bilateral BP reading (spec: an objective inter-arm differential -- a classic aortic
    # dissection sign, but generic to any vascular presentation -- must actually affect the
    # differential, not be silently discarded by the single-BP-only parse above). Gated on the
    # text explicitly naming BOTH sides so an unrelated pair of numbers (e.g. a same-arm trend
    # note like "BP 150/95 improved to 120/80") is never misread as two different limbs.
    lowered = text.lower()
    if "left" in lowered and "right" in lowered and lowered.count("arm") >= 2:
        pairs = _BP_PAIR.findall(text)
        if len(pairs) >= 2:
            sbp1, sbp2 = int(pairs[0][0]), int(pairs[1][0])
            sbp_arm_differential = abs(sbp1 - sbp2)

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

    if all(v is None for v in
           (sbp, dbp, heart_rate, respiratory_rate, temperature_c, spo2, sbp_arm_differential)):
        return None

    try:
        return VitalSigns(sbp=sbp, dbp=dbp, heart_rate=heart_rate, respiratory_rate=respiratory_rate,
                           temperature_c=temperature_c, spo2=spo2,
                           sbp_arm_differential=sbp_arm_differential, raw_text=text)
    except Exception:
        # An extracted number fell outside VitalSigns' physiologic validation range (e.g. a typo'd
        # observation) -- keep the raw text available elsewhere (physical_examinations) but don't
        # let a single malformed vital crash the turn (spec section 20).
        return None


SLOW_PULSE_FINDING = "pulse rate below 50"
FAST_PULSE_FINDING = "pulse rate of 150 or more"


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
    # Standard adult descriptive definitions (not red flags): the red-flag table above only fires on MARKED
    # derangement (HR >= 120, T >= 39.0), so an ordinary tachycardia (HR 118) or fever (T 38.4) previously
    # never reached the evidence corpus at all. Each is added only when the stricter red flag did not fire.
    hr, temp = values.get("heart_rate"), values.get("temperature_c")
    if hr is not None and 100 < hr < 120:
        findings.append("Tachycardia")
    # Round Q: the heart rate itself, kept separate from any rhythm statement ("HR 37 regular" is still a slow rate).
    # Thresholds are the ones the AHA adult bradycardia / tachycardia algorithms use to suggest a RHYTHM cause
    # ("typically <50/min if bradyarrhythmia", "typically >=150/min if tachyarrhythmia"; Panchal AR et al., 2020
    # AHA Guidelines for CPR and ECC, Part 3, Circulation 2020;142:S366). They prompt review of rhythm causes; they
    # never name a subtype (AF, VT, AV block) and do not remove fever/pain/volume/drug explanations.
    if hr is not None and hr < 50:
        findings.append(SLOW_PULSE_FINDING)
    if hr is not None and hr >= 150:
        findings.append(FAST_PULSE_FINDING)
    if temp is not None and 38.0 <= temp < 39.0:
        findings.append("Fever")
    return findings
