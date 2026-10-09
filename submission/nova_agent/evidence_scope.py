"""Small deterministic observation views; original words and offsets are never rewritten.

Scope applies to bare symptoms as well as diagnosis names. Polarity is retained for
the existing feature-local negation parser; this module does not turn an uncertain
or excluded diagnosis into a normal examination. Engineering linguistic rules.
"""
from dataclasses import dataclass
import re

from nova_agent.assertion_status import (
    CURRENT_CUE, FAMILY_CUE, HISTORICAL_CUE, OTHER_PERSON_CUE,
    NEGATION_CUE, UNCERTAIN_CUE,
)

_PATIENT = re.compile(r"\b(?:I|I'm|I've|me|myself|the patient)\b|제가|저는|저도|내가|나는|환자(?:는|가)?", re.I)
_POSSESSIVE = re.compile(r"\bmy\s+(?!family\s+history\b)|제\s+", re.I)
_PRONOUN = re.compile(r"^\s*(?:he|she|his|her|they|their)\b|^\s*(?:그분|그녀)", re.I)
_BOUNDARY = re.compile(r"[;!?\n]|(?<=\w)\.(?=\s|$)|\b(?:but|however|whereas)\b|하지만|그러나|반면", re.I)
_TEMPORAL_SWITCH = re.compile(r"(?:,|\band\b)\s*(?=(?:now|today|currently)\b)|(?=지금은|현재는)", re.I)


@dataclass(frozen=True)
class EvidenceClause:
    source: str
    span: tuple[int, int]
    text: str
    experiencer: str
    temporality: str
    assertion: str


def evidence_clauses(text: str, source: str = "narrative", default_subject: str = "PATIENT") -> tuple[EvidenceClause, ...]:
    """Bounded explicit scope. A new subject closes the previous subject's scope.

    Third-person clinical wording inherits the caller's source subject. It is
    not enough to override an explicit family antecedent. Standalone callers
    can pass UNSPECIFIED when no patient-observation context exists.
    Within a relative's narrative, a bare continuation stays with that relative.
    'My father' is one FAMILY subject, not an intervening PATIENT 'my'.
    """
    if not text:
        return ()
    subjects = [(m.start(), m.end(), 'FAMILY') for m in FAMILY_CUE.finditer(text)]
    subjects += [(m.start(), m.end(), 'OTHER') for m in OTHER_PERSON_CUE.finditer(text)]
    persons = sorted(subjects)
    subjects += [(m.start(), m.end(), 'PATIENT') for m in _PATIENT.finditer(text)]
    for m in _POSSESSIVE.finditer(text):
        if not any(m.end() <= a <= m.end() + 1 for a, _, _ in persons):
            subjects.append((m.start(), m.end(), 'PATIENT'))
    subjects.sort()
    cuts = {0, len(text)}
    for m in _BOUNDARY.finditer(text):
        cuts.update((m.start(), m.end()))
    for m in _TEMPORAL_SWITCH.finditer(text):
        cuts.add(m.start())
    # Subject transitions can occur without a semicolon ("dad coughs and I itch").
    previous = default_subject
    for a, b, subject in subjects:
        if previous is not None and subject != previous:
            # A leading determiner/negator belongs to its first subject:
            # "No family history ..." must not become positive family content.
            prefix = text[:a].strip().lower()
            if prefix not in {'my', 'no', 'no known', 'denies', 'without', '제', '우리'}:
                cuts.add(a)
        previous = subject
    points = sorted(cuts)
    out = []
    subject = default_subject
    temporal = 'UNSPECIFIED'
    for lo, hi in zip(points, points[1:]):
        raw = text[lo:hi]
        if not raw.strip() or _BOUNDARY.fullmatch(raw):
            continue
        own = [(a, s) for a, b, s in subjects if lo <= a < hi]
        if own:
            subject = own[-1][1]
            temporal = 'UNSPECIFIED'
        elif _PRONOUN.search(raw):
            subject = subject if subject in {'FAMILY', 'OTHER'} else default_subject
        past = list(HISTORICAL_CUE.finditer(raw))
        current = list(CURRENT_CUE.finditer(raw))
        if past or current:
            temporal = max([(m.start(), 'HISTORICAL') for m in past] +
                           [(m.start(), 'CURRENT') for m in current])[1]
        assertion = ('UNCERTAIN' if UNCERTAIN_CUE.search(raw) else
                     'NEGATED' if NEGATION_CUE.search(raw) else 'PRESENT')
        out.append(EvidenceClause(source, (lo, hi), raw, subject, temporal, assertion))
    return tuple(out)


def patient_evidence_text(text: str, *, allow_historical: bool = True, source: str = "narrative",
                          allow_unattributed_pronoun: bool = False) -> str:
    from nova_agent.matching import _scoped
    return _scoped('patient_scope', (text, allow_historical, source, allow_unattributed_pronoun),
                   lambda: _patient_evidence_text(text, allow_historical=allow_historical, source=source,
                                                  allow_unattributed_pronoun=allow_unattributed_pronoun))


def _patient_evidence_text(text: str, *, allow_historical: bool, source: str,
                           allow_unattributed_pronoun: bool) -> str:
    """Mask only nonpatient/historical ranges, preserving positions and polarity.

    Disease-name assertion filtering remains in documented_diagnosis. Current
    symptom consumers use allow_historical=False; risk/history consumers opt in.
    """
    # Most objective results contain no subject or time cue. Fast path matters
    # because all candidates use the same observation view every turn.
    if not (FAMILY_CUE.search(text) or OTHER_PERSON_CUE.search(text)
            or (_PRONOUN.search(text) and not allow_unattributed_pronoun)
            or (not allow_historical and HISTORICAL_CUE.search(text))):
        return text
    chars = list(text)
    for clause in evidence_clauses(text, source):
        if clause.experiencer != 'PATIENT' or (not allow_historical and clause.temporality == 'HISTORICAL'):
            a, b = clause.span
            chars[a:b] = ' ' * (b - a)
    return ''.join(chars)
