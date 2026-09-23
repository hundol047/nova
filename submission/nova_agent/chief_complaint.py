"""Maps a free-text chief complaint onto one of the fixed chief-complaint tags the knowledge base
is organized by (spec section 17's eight case categories). Deterministic, bilingual, with an
explicit 'other' fallback rather than a guessed tag.

Three-level matching, in priority order (never a global synonym substitution -- every alias below
is scoped to the ONE concept it's keyed under, exactly like the feature-local aliases in
differential.py's FEATURE_ALIASES, for the same reason: a global word-group table let unrelated
findings cross-contaminate each other's matches the one time this repo tried it):

  1. Exact/substring phrase match against CHIEF_COMPLAINT_KEYWORDS -- the original mechanism,
     extended with more real lay-language phrasings per concept (not just the clinical term).
  2. Token/phrase similarity fallback -- reuses matching.py's stemmed word-overlap scorer (the
     same one differential.py and safety.py already rely on) so a phrasing that doesn't exactly
     match any alias but clearly shares the same content words ("struggling for air" vs. the
     "dyspnea" concept's "struggling to breathe") still routes correctly, at a lower confidence
     than an exact/alias hit.
  3. Explicit 'other' -- only when neither of the above produces any signal at all.

`classify()` keeps its original signature/behavior (single best tag, or 'other'). `top_candidates()`
is new: returns a confidence-ranked list, which differential.py uses for soft routing (spec:
prefer 2-3 plausible complaint categories plus cross-cutting can't-miss diagnoses over dumping the
entire knowledge base just because the single best match was ambiguous or weak).
"""

from __future__ import annotations

from typing import List, Tuple

from nova_agent.matching import _content_words

CHIEF_COMPLAINT_KEYWORDS = {
    "chest_pain": ["chest pain", "chest tightness", "chest pressure", "chest hurts", "chest discomfort",
                   "pain in my chest", "흉통", "가슴 통증", "가슴이 아프"],
    "abdominal_pain": ["abdominal pain", "stomach pain", "belly pain", "stomach hurts", "my stomach",
                        "tummy", "gut pain", "stomach is killing me", "cramping in my stomach",
                        "pain in my gut", "stomach ache", "belly is killing me",
                        "복통", "배가 아프"],
    "headache": ["headache", "head pain", "head hurts", "my head is killing me", "head is pounding",
                 "splitting headache", "head is throbbing", "pain in my head",
                 "두통", "머리가 아프"],
    "fever": ["fever", "chills", "high temperature", "burning up", "running a temperature",
              "feverish", "temperature is high", "hot and shivery", "burning up with fever",
              "열", "발열", "오한"],
    "dyspnea": ["shortness of breath", "difficulty breathing", "trouble breathing", "dyspnea", "breathless",
                "can't breathe", "cant breathe", "can't catch my breath", "out of breath", "winded",
                "can't get a full breath", "can't get enough air", "hard to breathe",
                "trouble catching my breath", "feel like i'm suffocating", "air hunger",
                "struggling to breathe", "struggling for air", "throat feels like it's closing",
                "throat closing up", "throat feels tight", "throat is tightening", "gasping for air",
                "harder to breathe", "getting harder to breathe",
                "숨이 차", "호흡곤란"],
    "dizziness": ["dizziness", "dizzy", "vertigo", "lightheaded", "light-headed", "room spinning",
                  "woozy", "어지러", "현훈"],
    "altered_mental_status": ["confusion", "confused", "altered mental status", "unresponsive",
                              "disoriented", "not making sense", "out of it", "can't think straight",
                              "not himself", "not herself", "not myself", "not acting like himself",
                              "not acting like herself", "seems out of it", "can't focus",
                              "mentally foggy", "not tracking conversation", "zoning out",
                              "의식", "혼돈", "의식저하"],
    "urinary_symptoms": ["dysuria", "urinary frequency", "painful urination", "blood in urine",
                          "burning when I pee", "burns when I pee", "burning when I urinate",
                          "pain when urinating", "peeing", "urinate", "bladder", "소변", "배뇨통", "빈뇨"],
    # Additional presentation categories (spec section 8/24H): each is deliberately mapped to
    # disease pools already tagged for it in knowledge/diseases/*.json (see each disease's
    # `chief_complaint_tags`), rather than dumping the untargeted full 29-disease catalog whenever
    # a presentation falls slightly outside the original 8 categories.
    "syncope": ["syncope", "fainted", "fainting", "passed out", "loss of consciousness", "blacked out",
                "went out", "went unconscious", "lost consciousness", "collapsed",
                "dropped to the floor", "everything went black",
                "실신", "기절"],
    "palpitations": ["palpitations", "heart racing", "irregular heartbeat", "heart pounding",
                      "skipping beats", "racing heart", "heart is fluttering", "heart skipping",
                      "heart pounding out of my chest", "feel my heart beating fast",
                      "pulse pounding in my throat", "feel my pulse in my throat",
                      "두근거림", "심계항진"],
    "vomiting": ["vomiting", "throwing up", "nausea and vomiting", "puking", "구토", "토했"],
    "weakness": ["weakness", "generalized weakness", "feeling weak", "muscle weakness", "no energy",
                 "can't move", "feel wiped out", "no strength", "body feels heavy",
                 "can't keep going", "drained of energy", "feel completely exhausted",
                 "무기력", "힘이 없"],
    "cough": ["cough", "coughing", "productive cough", "기침"],
    "back_pain": ["back pain", "flank pain", "lower back pain", "side hurts", "side pain", "my flank",
                  "요통", "옆구리 통증"],
    "leg_swelling": ["leg swelling", "swollen leg", "calf swelling", "edema", "다리 부종", "종아리 부종"],
}

# Presentations without their own dedicated disease pool are routed to the closest clinically
# related tag(s) so the candidate pool stays targeted instead of falling through to the entire
# knowledge base. Order matters only for tie-breaking (chief_complaint.classify picks the single
# best keyword match above this step -- this table only affects diseases_for_tag's fallback via
# differential.py, not the classifier itself).
RELATED_TAGS = {
    "syncope": ["dizziness", "chest_pain"],
    "palpitations": ["chest_pain", "dizziness"],
    "vomiting": ["abdominal_pain"],
    "weakness": ["altered_mental_status", "dizziness"],
    "cough": ["dyspnea", "fever"],
    "back_pain": ["abdominal_pain", "urinary_symptoms"],
    "leg_swelling": ["dyspnea"],
}

# Cross-cutting can't-miss diagnoses (spec: soft routing must never lose safety coverage just
# because the chief complaint didn't cleanly match one category). Deliberately small and by
# diagnosis id, not duplicated logic -- differential.py already has a general critical-condition
# mechanism (safety.py's critical_condition_ids); this list is only the identifiers, consulted by
# differential.py when building a low-confidence candidate pool.
CROSS_CUTTING_DANGEROUS_DIAGNOSES = [
    "sepsis", "acute_coronary_syndrome", "pulmonary_embolism", "ischemic_stroke",
    "aortic_dissection", "diabetic_ketoacidosis", "hypoglycemia", "acute_abdomen",
]

_FUZZY_MATCH_THRESHOLD = 0.6  # same overlap ratio matching.py's feature_present() already uses

# `_content_words()` splits on any non-alphanumeric character, so a contraction like "can't" or
# "it's" becomes two tokens ("can"/"t", "it"/"s") -- neither is stopword-filtered by matching.py's
# shared list (that list is tuned for clinical KB-feature text, not casual chief-complaint prose),
# and a leftover single-letter fragment or a bare auxiliary verb is not a meaningful content word
# for THIS fuzzy comparison. Filtered locally here only -- never fed back into matching.py's own
# stopword set, which other, already-verified matching behavior depends on.
_CONTRACTION_NOISE = {"t", "s", "m", "re", "ve", "ll", "d", "can"}


def _meaningful_words(words: set) -> set:
    return words - _CONTRACTION_NOISE


# Cached per-tag content-word sets for the fuzzy fallback -- computed once at import time, not
# per-call, since CHIEF_COMPLAINT_KEYWORDS never changes at runtime. Aliases that degenerate to a
# single (or zero) meaningful word after stopword/contraction filtering (e.g. "out of it" -> just
# {"out"}) are dropped entirely from fuzzy eligibility: exact/substring matching still catches them
# precisely, but a single common word scoring a trivial 1.0 overlap ratio against nearly any
# unrelated text is exactly the false-positive mechanism this fuzzy layer must not introduce.
_KEYWORD_CONTENT_WORDS: dict = {
    tag: [words for kw in keywords
          for words in [_meaningful_words(_content_words(kw))] if len(words) >= 2]
    for tag, keywords in CHIEF_COMPLAINT_KEYWORDS.items()
}


def _fuzzy_score(text_words: set, tag: str) -> float:
    """Best word-overlap ratio between `text_words` and any single keyword phrase under `tag`
    (both sides pre-filtered of contraction noise), using the same stemmed-content-word approach
    matching.py's feature_present() already uses elsewhere in this codebase -- deliberately not a
    separate NLP mechanism, just the existing one reused for a different comparison direction
    (chief-complaint text vs. a concept's keywords, rather than a KB feature phrase vs. gathered
    findings)."""
    best = 0.0
    for kw_words in _KEYWORD_CONTENT_WORDS[tag]:
        if not text_words:
            continue
        overlap = kw_words & text_words
        ratio = len(overlap) / len(kw_words)
        if ratio > best:
            best = ratio
    return best


def _scores(chief_complaint_text: str) -> List[Tuple[str, float]]:
    """Every tag's score against `chief_complaint_text`, highest first. An exact/substring alias
    hit always outranks a fuzzy-only match (scored in a disjoint, higher range) so fuzzy matching
    can only ever ADD coverage for phrasing exact aliases miss, never override a real alias hit."""
    lowered = (chief_complaint_text or "").lower()
    text_words = _meaningful_words(_content_words(lowered))
    scored: List[Tuple[str, float]] = []
    for tag, keywords in CHIEF_COMPLAINT_KEYWORDS.items():
        exact_hits = sum(1 for kw in keywords if kw.lower() in lowered)
        if exact_hits > 0:
            scored.append((tag, 1.0 + exact_hits))  # >=2.0, always beats any fuzzy-only score
            continue
        fuzzy = _fuzzy_score(text_words, tag)
        if fuzzy >= _FUZZY_MATCH_THRESHOLD:
            scored.append((tag, fuzzy))  # in (0, 1.0), never confused with an exact hit
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored


def classify(chief_complaint_text: str) -> str:
    """Returns the best-matching tag, or 'other' if nothing matches (never a guessed tag)."""
    scored = _scores(chief_complaint_text)
    return scored[0][0] if scored else "other"


def top_candidates(chief_complaint_text: str, k: int = 3) -> List[str]:
    """Up to `k` plausible tags for this chief complaint, ranked by confidence -- for soft routing
    when the single best match is weak/ambiguous rather than a confident exact hit. Empty when
    nothing scored at all (genuinely unclassifiable text; differential.py's existing whole-catalog
    fallback remains the last resort for that case -- soft routing has nothing to be soft about
    when there is no signal whatsoever)."""
    return [tag for tag, _score in _scores(chief_complaint_text)[:k]]


def related_tags(tag: str) -> list:
    """Additional tags whose disease pool is clinically relevant to `tag`, used by
    differential.diseases_for_tag() to build a targeted (not whole-catalog) candidate pool for
    presentations that don't have their own disease entries tagged directly."""
    return RELATED_TAGS.get(tag, [])
