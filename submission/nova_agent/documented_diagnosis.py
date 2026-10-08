"""Round P (NOVA_DOCUMENTED_DX): a diagnosis the patient reports as DOCUMENTED by a clinician.

"My referral letter mentions Meniere disease", "the GP says it's atrial fibrillation", "I was diagnosed with gout"
are genuine clinical information (a known diagnosis from a prior assessment), not a guess. When such a statement
names a condition in the static catalog EXACTLY (canonical name or listed synonym, whole words), that condition is
brought into the candidate pool and receives one feature's worth of support labelled "documented diagnosis".

Round Q: every diagnosis mention is kept as a ``DiagnosisMention`` with its OWN assertion, time, experiencer and
source, judged on the smallest clause that governs it (original-text offsets, never offsets of a scrubbed copy).
Only a clinician-reported, PRESENT, patient-attributed, not-historical mention counts as positive support. A negated
("was excluded", "아니라고"), uncertain ("cannot be excluded", "의심"), historical ("in 2016"), family ("my mother
was diagnosed") or speculative ("I think it's ...") mention is kept for provenance but never adds support -- and a
negated mention is not turned into a normal test result either: it simply contributes nothing. A denied SYMPTOM in
another clause ("... and I have no nausea") no longer erases a documented diagnosis.
PROVENANCE: engineering-authored wording rules; not clinician-reviewed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Literal, Optional, Tuple

from nova_agent.assertion_status import (
    AFFIRM_CUE, CURRENT_CUE, FAMILY_CUE, FIRST_PERSON_CUE, HISTORICAL_CUE, NEGATION_CUE, OTHER_PERSON_CUE,
    SPECULATION_CUE, UNCERTAIN_CUE,
)

_FRAMING = re.compile(
    r"\b(?:referral|referred|(?:clinic|discharge|specialist|gp|hospital) (?:note|letter|summary)|letter|"
    r"discharge (?:summary|letter)|records?|my notes|the notes|note|report|"
    r"(?:my|the) (?:doctor|gp|specialist|consultant|cardiologist|neurologist|hospital))\b[^.;]{0,40}?"
    r"\b(?:mentions?|mentioned|says?|said|states?|stated|lists?|listed|wrote|noted|notes|told me|diagnosed|"
    r"confirms?|confirmed|records?|recorded|documents?|documented|shows?|showed|excludes?|excluded|denies|"
    r"rules? out|ruled out)\b|"
    r"\bdiagnosed with\b|\bdiagnosis of\b|진단(?:을)? ?받|진단서|소견서|의사(?:가| 선생님이)", re.IGNORECASE)
_SENTENCE = re.compile(r"[.;!?\n]")
# Hard boundaries keep a predicate on its own side ("confirms AF but excludes PE"); soft boundaries separate list
# items that may share one predicate ("excludes AF and PE", "AF and PE were excluded").
_HARD_BOUNDARY = re.compile(r"\s*\b(?:but|however|whereas|although|though|yet)\b|하지만|그러나|반면|지만", re.IGNORECASE)
_SOFT_BOUNDARY = re.compile(r",|\s\band\b\s|\s및\s")
_MIN_NAME_LEN = 5

Assertion = Literal["PRESENT", "NEGATED", "UNCERTAIN", "UNKNOWN"]
Temporality = Literal["CURRENT", "HISTORICAL", "UNSPECIFIED"]
Experiencer = Literal["PATIENT", "FAMILY", "OTHER", "UNSPECIFIED"]
Source = Literal["REPORTED_CLINICIAN", "PATIENT_SPECULATION", "OTHER"]


@dataclass(frozen=True)
class DiagnosisMention:
    diagnosis_id: str
    text_index: int
    mention_span: Tuple[int, int]      # offsets in the ORIGINAL text
    evidence_span: Tuple[int, int]     # the smallest clause whose cues decided assertion/subject/time
    assertion: Assertion
    temporality: Temporality
    experiencer: Experiencer
    source: Source

    @property
    def counts_as_documented(self) -> bool:
        return (self.assertion == "PRESENT" and self.source == "REPORTED_CLINICIAN"
                and self.experiencer in ("PATIENT", "UNSPECIFIED") and self.temporality != "HISTORICAL")


@lru_cache(maxsize=1)
def _name_index() -> Tuple[Tuple[str, str], ...]:
    """(lower-case name, candidate id) for every KB disease name/alias and every catalog concept name/synonym."""
    names: Dict[str, str] = {}
    from nova_agent.knowledge.retrieval import all_diseases
    for entry in all_diseases().values():
        for name in [entry.get("name", "")] + list(entry.get("aliases", [])):
            for variant in {name, re.sub(r"\s*\(.*?\)", "", name)}:
                if len(variant.strip()) >= _MIN_NAME_LEN:
                    names.setdefault(variant.strip().lower(), entry["id"])
    try:
        from nova_agent.ontology.registry import get_default_catalog
        for concept in get_default_catalog().all_concepts():
            for name in [concept.canonical_name] + list(getattr(concept, "aliases", []) or []):
                if name and len(name.strip()) >= _MIN_NAME_LEN:
                    names.setdefault(name.strip().lower(), f"onto::{concept.concept_id}")
    except Exception:
        pass
    # longest first, so "acute pericarditis" wins over "pericarditis"
    return tuple(sorted(names.items(), key=lambda kv: -len(kv[0])))


def _find_names(low: str, lo: int, hi: int) -> List[Tuple[int, int, str]]:
    taken: List[Tuple[int, int, str]] = []
    window = low[lo:hi]
    for name, cid in _name_index():
        start = window.find(name)
        while start != -1:
            end = start + len(name)
            # A Korean particle may follow a Latin-script name directly ("atrial fibrillation이"): still a whole name.
            boundary = ((start == 0 or not window[start - 1].isalnum())
                        and (end == len(window) or not window[end].isalnum()
                             or (window[end - 1].isascii() and "가" <= window[end] <= "힣")))
            if boundary and not any(a < lo + end and lo + start < b for a, b, _ in taken):
                taken.append((lo + start, lo + end, cid))
                break
            start = window.find(name, start + 1)
    return sorted(taken)


def _sentences(text: str) -> List[Tuple[int, int]]:
    out, start = [], 0
    for m in _SENTENCE.finditer(text):
        if m.start() > start:
            out.append((start, m.start()))
        start = m.end()
    if start < len(text):
        out.append((start, len(text)))
    return out


def _split(text: str, lo: int, hi: int, pattern: "re.Pattern[str]", protected: List[Tuple[int, int, str]]) -> List[Tuple[int, int]]:
    cuts = [m for m in pattern.finditer(text, lo, hi)
            if not any(a < m.end() and m.start() < b for a, b, _ in protected)]
    parts, start = [], lo
    for m in cuts:
        parts.append((start, m.start()))
        start = m.end()
    parts.append((start, hi))
    return [(a, b) for a, b in parts if text[a:b].strip()]


def _masked(text: str, lo: int, hi: int, mentions: List[Tuple[int, int, str]]) -> str:
    """The clause with diagnosis names blanked out (a name containing "no"/"not" can never act as a cue)."""
    chars = list(text[lo:hi])
    for a, b, _ in mentions:
        for i in range(max(a, lo), min(b, hi)):
            chars[i - lo] = " "
    return "".join(chars)


def _assertion_cue(clause: str) -> Tuple[Optional[str], bool]:
    """(assertion, postposed?) decided by cues inside ONE clause. Uncertainty compounds are consumed FIRST
    ("cannot be excluded" is never read as a negation)."""
    uncertain = UNCERTAIN_CUE.search(clause)
    if uncertain:
        return "UNCERTAIN", True
    negated = NEGATION_CUE.search(clause)
    if negated:
        return "NEGATED", True
    if AFFIRM_CUE.search(clause):
        return "PRESENT", False
    return None, False


def _experiencer(text: str, s_lo: int, s_hi: int, mention_start: int) -> Experiencer:
    """Whose diagnosis: a family member named before the mention is the experiencer unless a first-person
    subject comes between them ("my mother says I was diagnosed with ..." is the patient's)."""
    before = text[s_lo:mention_start]
    family = None
    for family in FAMILY_CUE.finditer(before):
        pass
    if family is not None and not FIRST_PERSON_CUE.search(before[family.end():]):
        return "FAMILY"
    other = None
    for other in OTHER_PERSON_CUE.finditer(before):
        pass
    if other is not None and not FIRST_PERSON_CUE.search(before[other.end():]):
        return "OTHER"
    if FIRST_PERSON_CUE.search(text[s_lo:s_hi]) or re.search(r"\bthe patient\b|환자", text[s_lo:s_hi], re.I):
        return "PATIENT"
    return "UNSPECIFIED"


def documented_diagnosis_mentions(texts: List[str]) -> List[DiagnosisMention]:
    """Every diagnosis named inside a clinician-documentation or patient-speculation sentence, with its scope."""
    mentions: List[DiagnosisMention] = []
    for index, text in enumerate(texts):
        text = text or ""
        low = text.lower()
        if len(low) != len(text):   # offsets must stay valid on the original text
            low = "".join(ch.lower() if len(ch.lower()) == 1 else ch for ch in text)
        for s_lo, s_hi in _sentences(text):
            sentence = text[s_lo:s_hi]
            framed = bool(_FRAMING.search(sentence))
            speculative = bool(SPECULATION_CUE.search(sentence))
            if not (framed or speculative):
                continue
            names = _find_names(low, s_lo, s_hi)
            if not names:
                continue
            source: Source = "PATIENT_SPECULATION" if speculative else "REPORTED_CLINICIAN"
            for h_lo, h_hi in _split(text, s_lo, s_hi, _HARD_BOUNDARY, names):
                parts = _split(text, h_lo, h_hi, _SOFT_BOUNDARY, names)
                cues = [_assertion_cue(_masked(text, a, b, names)) for a, b in parts]
                for p, (a, b) in enumerate(parts):
                    in_part = [n for n in names if a <= n[0] < b]
                    if not in_part:
                        continue
                    assertion, _ = cues[p]
                    if assertion is None:
                        # A bare list item shares the predicate of its list: a postposed one that follows
                        # ("AF and PE were excluded") or the one that precedes it ("excludes AF and PE").
                        following = next((c for c in cues[p + 1:] if c[0] is not None), (None, False))
                        preceding = next((c for c in reversed(cues[:p]) if c[0] is not None), (None, False))
                        assertion = following[0] if following[0] is not None and following[1] else preceding[0]
                    clause = _masked(text, a, b, names)
                    scope = _masked(text, h_lo, h_hi, names)
                    temporality: Temporality = ("HISTORICAL" if HISTORICAL_CUE.search(clause) or HISTORICAL_CUE.search(scope)
                                                else "CURRENT" if CURRENT_CUE.search(clause) else "UNSPECIFIED")
                    experiencer = _experiencer(text, s_lo, s_hi, in_part[0][0])
                    for n_lo, n_hi, cid in in_part:
                        mentions.append(DiagnosisMention(
                            diagnosis_id=cid, text_index=index, mention_span=(n_lo, n_hi), evidence_span=(a, b),
                            # A patient's own guess is a hypothesis, never an affirmation (an explicit denial stays one).
                            assertion=("UNCERTAIN" if source == "PATIENT_SPECULATION" and assertion != "NEGATED"
                                       else assertion or ("PRESENT" if framed else "UNKNOWN")),
                            temporality=temporality, experiencer=experiencer, source=source))
    return mentions


def documented_diagnosis_ids(texts: List[str]) -> List[str]:
    """Candidate ids named as a CURRENT, PATIENT, clinician-documented, PRESENT diagnosis (order of first mention).

    When the same diagnosis is mentioned more than once, the LAST statement decides (a later correction --
    "... but it was later excluded" -- updates the earlier one); every mention stays available via
    ``documented_diagnosis_mentions`` so a conflict is visible rather than silently merged."""
    from nova_agent.config import get_config
    if not get_config().documented_dx_enabled:
        return []
    latest: Dict[str, DiagnosisMention] = {}
    order: List[str] = []
    for mention in documented_diagnosis_mentions(texts):
        if mention.source != "REPORTED_CLINICIAN" or mention.experiencer not in ("PATIENT", "UNSPECIFIED"):
            continue
        if mention.diagnosis_id not in order:
            order.append(mention.diagnosis_id)
        latest[mention.diagnosis_id] = mention
    return [cid for cid in order if latest[cid].counts_as_documented]
