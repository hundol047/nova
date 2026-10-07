"""Clinical concept normalisation: free-text wording -> the canonical phrase the knowledge base uses.

Why: the knowledge base names each finding once ("neck stiffness", "missed period", "melena"), while patients
and examiners use many forms ("nuchal rigidity", "my neck feels locked up", "period is two weeks late",
"black tarry stool"). Literal per-phrase aliases cannot express "period ... late", so these are bounded
patterns, one CONCEPT each. A match appends the canonical phrase to the evidence bag; the patient's own text is
kept unchanged next to it.

Discipline:
  * One pattern -> one concept. Distinct concepts are never merged (dysarthria "slurred speech" and aphasia
    "words come out jumbled" stay separate; melena and hematochezia stay separate).
  * Clause-level and negation-aware: the clause is first scrubbed with matching._strip_negated_spans, so
    "no neck stiffness" / "denies black stools" never produces the concept.
  * Current findings only: a clause marked as history ("history of", "years ago", "used to", "last year",
    "previously") does not produce a CURRENT-symptom concept.
  * No diagnosis is named here; scoring still decides with every other piece of evidence.
PROVENANCE: authored by the engineering agent from standard clinical vocabulary; NOT clinician-reviewed.
"""
from __future__ import annotations

import re
from typing import List, Tuple

_HISTORY = re.compile(r"\b(?:history of|h/o|years? ago|used to|last year|previously|in the past|as a child|childhood)\b",
                      re.IGNORECASE)
_CLAUSE = re.compile(r"[;\n]|(?<=[a-z])\.(?=\s|$)|\bbut\b|\bhowever\b", re.IGNORECASE)

# (canonical KB phrase, pattern). Patterns are matched on lower-cased, negation-scrubbed clause text.
_CONCEPTS: List[Tuple[str, re.Pattern]] = [(c, re.compile(p)) for c, p in (
    # meningeal irritation
    ("neck stiffness", r"\bnuchal rigidity\b|\bmeningism(?:us)?\b|\bbrudzinski\b|\bkernig\b|"
                       r"\bneck (?:feels? |is |has gone )?(?:locked(?: up)?|rigid|stiff)\b|"
                       r"\b(?:can'?t|cannot|unable to) (?:bend|flex|move|turn) (?:my |his |her )?neck\b"),
    ("photophobia", r"\b(?:can'?t|cannot) (?:stand|tolerate|bear|handle) (?:the |any )?(?:bright )?lights?\b|"
                    r"\blights? (?:\w+ )?(?:hurts?|bothers?|is (?:painful|unbearable))\b|\b(?:avoids?|avoiding) (?:the )?light\b|"
                    r"\bwants? (?:the )?(?:room|lights?) (?:dark|off)\b"),
    ("CSF pleocytosis", r"\b(?:cloudy|turbid|purulent)\s+(?:csf|cerebrospinal fluid|spinal fluid)\b|"
                        r"\b(?:csf|cerebrospinal fluid|spinal fluid)\s+(?:is |was |looks? |appears? )?(?:cloudy|turbid|purulent)\b|"
                        r"\b(?:csf|cerebrospinal fluid|spinal fluid)\b[^.;]{0,40}\b(?:elevated|high|raised|increased|markedly)\b"
                        r"[^.;]{0,20}\b(?:white|wbc|leuko|neutrophil|cell count)|"
                        r"\b(?:csf|cerebrospinal fluid)\b[^.;]{0,30}\bwbc\s*(?:of\s*)?\d{3,}"),
    # early pregnancy / gynaecological bleeding
    ("missed period", r"\bperiod (?:is |was |'s )?(?:\w+ ){0,3}(?:late|overdue)\b|\blate period\b|"
                      r"\bmissed (?:my |a |her )?(?:last )?period\b|\b(?:haven'?t|hasn'?t|have not|has not) had (?:my|a|her) period\b|"
                      r"\bno period (?:for|since)\b|\blast (?:menstrual )?period\b[^.;]{0,20}\b(?:\d+|two|three|four|five|six|seven|eight|several) "
                      r"(?:weeks?|months?) ago\b"),
    ("vaginal bleeding", r"\bspotting\b|\bvaginal(?:ly)? bleed\w*|\bbleeding from (?:the |my |her )?vagina\b|"
                         r"\bbleeding (?:down there|down below)\b"),
    # gastrointestinal bleeding (kept as three separate concepts)
    ("melena", r"\b(?:black|tarry|tar-like)\b[^.;]{0,15}\b(?:stools?|poo|poop|bowel movements?|motions?|faeces|feces)\b|"
               r"\b(?:stools?|poo|poop|bowel movements?)\b[^.;]{0,15}\b(?:black|tarry|like tar)\b"),
    ("hematochezia", r"\bmaroon\b[^.;]{0,15}\b(?:stools?|poo|poop|bowel movements?)\b|"
                     r"\b(?:stools?|poo|poop|bowel movements?)\b[^.;]{0,15}\bmaroon\b|"
                     r"\bblood (?:in|with|on) (?:my |the |his |her )?(?:stools?|poo|poop|bowel movements?|toilet paper)\b|"
                     r"\bbright red blood (?:per rectum|from (?:my |the )?(?:bottom|rectum|back passage))\b|\bbloody (?:stools?|diarrh\w+)\b"),
    ("hematemesis", r"\b(?:vomit\w*|threw up|throwing up|puk\w*)\b[^.;]{0,25}\b(?:blood|coffee[- ]grounds?)\b|"
                    r"\bcoffee[- ]ground\w*\b"),
    # focal neurological deficit (aphasia and dysarthria stay distinct)
    ("aphasia", r"\bwords? (?:come|came|coming) out (?:jumbled|wrong|mixed up|garbled)\b|"
                r"\b(?:can'?t|cannot|unable to|struggl\w+ to|trouble) (?:find|finding|get|getting) (?:the |my |his |her )?words\b|"
                r"\bexpressive aphasia\b|\breceptive aphasia\b|\bword[- ]finding difficult\w*"),
    ("slurred speech", r"\bspeech (?:is |was |sounds? )?(?:slurred|thick|garbled)\b|\bslurring (?:my |his |her )?words\b|"
                       r"\btalking (?:funny|like (?:i'?m|he'?s|she'?s) drunk)\b"),
    ("facial droop", r"\b(?:face|mouth|smile)\b[^.;]{0,25}\b(?:droop\w*|lopsided|crooked|uneven|sagging)\b|"
                     r"\b(?:droop\w*|lopsided|crooked)\b[^.;]{0,10}\b(?:face|mouth|smile)\b|\bfacial (?:droop|weakness|palsy)\b"),
    # breathlessness (everyday wording -> the KB's symptom phrase)
    ("shortness of breath", r"\b(?:can'?t|cannot|couldn'?t) (?:catch|get) (?:my |his |her )?breath\b|\bwinded\b|\bpuffed(?: out)?\b|"
                            r"\b(?:struggling|fighting|gasping) (?:to breathe|for (?:air|breath))\b|\b(?:can|could) (?:hardly|barely) breathe\b|"
                            r"\bhard to breathe\b|\bair hunger\b"),
)]


def _current_positive_clauses(text: str) -> List[str]:
    from nova_agent.matching import _strip_negated_spans
    out = []
    for clause in _CLAUSE.split(text or ""):
        if not clause or not clause.strip() or _HISTORY.search(clause):
            continue
        positive = _strip_negated_spans(clause.lower())
        if positive.strip(" ;"):
            out.append(positive)
    return out


def canonical_findings_for(text: str) -> List[str]:
    """Canonical KB phrases asserted (current, not negated) by ``text``; empty when nothing matches."""
    if not text or len(text) < 4:
        return []
    found: List[str] = []
    for clause in _current_positive_clauses(text):
        for canonical, pattern in _CONCEPTS:
            if canonical not in found and pattern.search(clause):
                found.append(canonical)
    return found
