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
from dataclasses import dataclass, replace
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
_HARD_BOUNDARY = re.compile(r"\s*\b(?:but|however|whereas|although|though|despite)\b|하지만|그러나|반면|지만", re.IGNORECASE)
_SOFT_BOUNDARY = re.compile(r",|\s\band\b\s|\s및\s|이고(?:요)?\s*|이며\s*")
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


_PATIENT_SUBJECT = re.compile(r"\b(?:I|I'm|I've|me|myself|the patient)\b|제가|저는|내가|나는|환자", re.I)
_EXPLICIT_AFFIRM = re.compile(r"\b(?:confirms?|confirmed|diagnosed|present|positive|has|have|had)\b|확진|확정|진단|있다고|이라고|라고", re.I)
_ELLIPSIS = re.compile(r"^\s*(?:it|this diagnosis|that diagnosis|the diagnosis)\b|^\s*(?:이|그|해당)\s*진단", re.I)
_ATTRIBUTION = re.compile(r"\b(?:in|of|for)\s+(?:(?:my|her|his|the)\s+)?", re.I)


def _experiencer(text: str, s_lo: int, part_hi: int, mention_start: int, mention_end: int) -> Experiencer:
    # The last explicit subject wins. A new 'the patient' closes a preceding family scope too.
    before = text[s_lo:mention_start]
    subjects = [(m.start(), 'FAMILY') for m in FAMILY_CUE.finditer(before)]
    subjects += [(m.start(), 'OTHER') for m in OTHER_PERSON_CUE.finditer(before)]
    subjects += [(m.start(), 'PATIENT') for m in _PATIENT_SUBJECT.finditer(before)]
    result = max(subjects, default=(-1, 'UNSPECIFIED'))[1]
    after = text[mention_end:part_hi]
    attributed = _ATTRIBUTION.match(after.lstrip())
    if attributed:
        tail = after.lstrip()[attributed.end():]
        if FAMILY_CUE.match(tail): return 'FAMILY'
        if OTHER_PERSON_CUE.match(tail): return 'OTHER'
        if re.match(r"(?:the )?patient\b", tail, re.I): return 'PATIENT'
    return result


def _parse_mentions(texts: List[str], documentation_only: bool) -> List[DiagnosisMention]:
    mentions: List[DiagnosisMention] = []
    for index, text in enumerate(texts):
        text = text or ''
        low = ''.join(ch.lower() if len(ch.lower()) == 1 else ch for ch in text)
        for s_lo, s_hi in _sentences(text):
            sentence = text[s_lo:s_hi]
            framed = bool(_FRAMING.search(sentence))
            if documentation_only and not (framed or SPECULATION_CUE.search(sentence)):
                continue
            names = _find_names(low, s_lo, s_hi)
            if not names: continue
            sentence_mentions = []
            for h_lo, h_hi in _split(text, s_lo, s_hi, _HARD_BOUNDARY, names):
                parts = _split(text, h_lo, h_hi, _SOFT_BOUNDARY, names)
                part_names = [[n for n in names if a <= n[0] < b] for a,b in parts]
                cues = []
                for (a,b), ns in zip(parts,part_names):
                    masked = _masked(text,a,b,names)
                    cue = UNCERTAIN_CUE.search(masked) or NEGATION_CUE.search(masked) or _EXPLICIT_AFFIRM.search(masked)
                    status = ('UNCERTAIN' if UNCERTAIN_CUE.search(masked) else
                              'NEGATED' if NEGATION_CUE.search(masked) else 'PRESENT' if cue else None)
                    # Only predicates following a list's diagnosis can propagate backwards.
                    postposed = bool(cue and ns and cue.start()+a >= ns[-1][1])
                    cues.append((status,postposed))
                for p,(a,b) in enumerate(parts):
                    ns = part_names[p]
                    clause = _masked(text,a,b,names)
                    if not ns:
                        # Bounded anaphora: exactly one prior diagnosis in this sentence, explicit correction only.
                        prior = {m.diagnosis_id:m for m in sentence_mentions}
                        if len(prior)==1 and _ELLIPSIS.search(text[a:b]) and cues[p][0]:
                            prev=next(iter(prior.values()))
                            m=replace(prev,assertion=cues[p][0],evidence_span=(prev.mention_span[0],b))
                            mentions.append(m);sentence_mentions.append(m)
                        continue
                    assertion,_ = cues[p]
                    bare = not (SPECULATION_CUE.search(clause) or _PATIENT_SUBJECT.search(clause)
                                or FAMILY_CUE.search(clause) or OTHER_PERSON_CUE.search(clause))
                    if assertion is None and bare:
                        following=next((cues[q] for q in range(p+1,len(parts)) if part_names[q] and cues[q][0]),(None,False))
                        preceding=next((cues[q] for q in range(p-1,-1,-1) if part_names[q] and cues[q][0]),(None,False))
                        assertion=following[0] if following[1] else preceding[0]
                    speculative=bool(SPECULATION_CUE.search(clause))
                    # A bare list continuation shares source/time, an independent predicate does not.
                    inherit = bool(p and bare and not cues[p][0] and not _FRAMING.search(clause))
                    previous = sentence_mentions[-1] if sentence_mentions else None
                    source = ('PATIENT_SPECULATION' if speculative else
                              previous.source if inherit and previous else
                              'REPORTED_CLINICIAN' if framed else 'OTHER')
                    temporal = ('HISTORICAL' if HISTORICAL_CUE.search(clause) else
                                'CURRENT' if CURRENT_CUE.search(clause) else
                                previous.temporality if inherit and previous else 'UNSPECIFIED')
                    for lo,hi,cid in ns:
                        m=DiagnosisMention(cid,index,(lo,hi),(a,b),
                            'UNCERTAIN' if source=='PATIENT_SPECULATION' and assertion!='NEGATED' else assertion or 'PRESENT',
                            temporal,_experiencer(text,s_lo,b,lo,hi),source)
                        mentions.append(m);sentence_mentions.append(m)
    return mentions


def documented_diagnosis_mentions(texts: List[str]) -> List[DiagnosisMention]:
    """All occurrences, local predicate/source/subject/time, with original offsets."""
    from nova_agent.matching import _scoped
    return list(_scoped('diagnosis_mentions',tuple(texts),lambda:tuple(_parse_mentions(texts,True))))


def diagnosis_evidence_text(text: str, allow_historical: bool = True) -> str:
    """A scoring view, never a mutation of the patient's words. Nonpositive/other-person diagnosis spans
    cannot become another disease's risk/feature. Patient history is retained as HISTORY when allowed.
    No result (including a negative test) is invented from a reported exclusion.
    """
    if not text or not (NEGATION_CUE.search(text) or UNCERTAIN_CUE.search(text) or FAMILY_CUE.search(text)
                        or OTHER_PERSON_CUE.search(text) or HISTORICAL_CUE.search(text) or SPECULATION_CUE.search(text)):
        return text
    from nova_agent.matching import _scoped
    def compute():
        mentions=_parse_mentions([text],False)
        latest={m.diagnosis_id:m for m in mentions if m.experiencer not in ('FAMILY','OTHER')}
        chars=list(text)
        for m in mentions:
            current=latest.get(m.diagnosis_id,m)
            blocked=(m.experiencer in ('FAMILY','OTHER') or m.assertion!='PRESENT'
                     or m.source=='PATIENT_SPECULATION' or current.assertion!='PRESENT'
                     or (not allow_historical and m.temporality=='HISTORICAL'))
            if blocked:
                lo,hi=m.mention_span
                chars[lo:hi]=' '* (hi-lo)
        return ''.join(chars)
    return _scoped('diagnosis_evidence',(text,allow_historical),compute)


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
