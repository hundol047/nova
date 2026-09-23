"""Maps a free-text chief complaint onto one of the fixed chief-complaint tags the knowledge base
is organized by (spec section 17's eight case categories). Deterministic, bilingual, with an
explicit 'other' fallback rather than a guessed tag.

Three-level matching, in priority order (never a global synonym substitution -- every alias below
is scoped to the ONE concept it's keyed under, exactly like the feature-local aliases in
differential.py's FEATURE_ALIASES, for the same reason: a global word-group table let unrelated
findings cross-contaminate each other's matches the one time this repo tried it):

  1. Exact/substring phrase match against CONCEPT_PHRASES -- either the concept's own canonical
     clinical term(s) (match_type="exact") or a scoped lay-language alias (match_type="alias").
  2. Token/phrase similarity fallback (match_type="fuzzy") -- reuses matching.py's stemmed
     word-overlap scorer (the same one differential.py and safety.py already rely on) so a
     phrasing that doesn't exactly match any alias but clearly shares the same content words still
     routes correctly, at a lower confidence than an exact/alias hit.
  3. Explicit 'other' (match_type="none") -- only when neither of the above produces any signal.

Every alias here is a GENERIC lay phrasing of its concept, not a sentence lifted from any
evaluation case file (evaluation/cases.py, held_out_cases.py, generalization_cases_v2.py,
generalization_stress_cases.py, blind_cases_v3.py, blind_cases_v4.py) -- a distinctive phrase that
reads as copied from one specific vignette rather than a phrasing many different patients would
plausibly use is exactly what this module must not contain, since that would make a classifier
look accurate on a blind set for the wrong reason (memorized wording, not real generalization).

route() returns a ChiefComplaintRoutingResult with enough structure (primary tag, its score, the
next-best tags, the score margin between them, how the primary was matched, and an overall
confidence tier) for differential.py to build a candidate pool that matches how sure the routing
actually is, rather than either a single hard-routed tag or an untargeted whole-catalog dump every
time the match is imperfect:

  HIGH   -- a clean exact/alias hit with no other tag close behind: primary tag's pool only.
  MEDIUM -- an exact/alias hit tied with another tag, or a fuzzy hit with a real margin over the
            next-best: merge the top 2 concepts' pools.
  LOW    -- a fuzzy hit with little or no margin over the next-best (a genuine ambiguous tie):
            merge the top 3 concepts' pools, plus the small cross-cutting can't-miss list.
  (primary_tag == "other", match_type == "none") -- no signal at all: differential.py's existing
            whole-catalog fallback is the last resort, which already contains every cross-cutting
            diagnosis, so nothing further is added here.

`classify()` and `top_candidates()` remain as thin wrappers over `route()` for callers (and tests)
that only need the single best tag or a ranked list, without the full structured result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Tuple

from nova_agent.matching import _content_words

MatchType = Literal["exact", "alias", "fuzzy", "none"]
Confidence = Literal["HIGH", "MEDIUM", "LOW"]

# Each concept's own canonical clinical term(s) -- a hit here is match_type "exact". Everything
# else in CONCEPT_PHRASES[tag] is a scoped lay-language ALIAS (match_type "alias"). The split only
# affects the reported match_type, never the score: an alias hit is exactly as strong as a
# canonical-term hit, since a lay patient describing "my chest hurts" is not less informative than
# one who says "chest pain".
CANONICAL_TERMS = {
    "chest_pain": ["chest pain"],
    "abdominal_pain": ["abdominal pain"],
    "headache": ["headache"],
    "fever": ["fever"],
    "dyspnea": ["dyspnea", "shortness of breath", "difficulty breathing", "trouble breathing"],
    "dizziness": ["dizziness", "vertigo"],
    "altered_mental_status": ["altered mental status", "confusion"],
    "urinary_symptoms": ["dysuria", "urinary frequency", "painful urination"],
    "syncope": ["syncope", "fainting", "fainted"],
    "palpitations": ["palpitations"],
    "vomiting": ["vomiting"],
    "weakness": ["weakness", "generalized weakness"],
    "cough": ["cough"],
    "back_pain": ["back pain", "flank pain"],
    "leg_swelling": ["leg swelling", "edema"],
    "focal_weakness": ["focal weakness", "one-sided weakness"],
    "aphasia": ["aphasia", "slurred speech"],
    "gi_bleeding": ["gi bleeding", "gastrointestinal bleeding"],
    "pelvic_gynecologic": ["pelvic pain", "vaginal bleeding"],
    "trauma": ["trauma", "traumatic injury"],
    "allergic": ["allergic reaction", "anaphylaxis"],
    "metabolic": ["metabolic symptoms", "hyperglycemia"],
}

# Generic lay-language aliases only -- each phrase describes how an ordinary patient would plausibly
# word the concept, never a sentence reused from a specific evaluation vignette.
CONCEPT_ALIASES = {
    "chest_pain": ["chest tightness", "chest pressure", "chest hurts", "chest discomfort",
                   "pain in my chest",
                   "흉통", "가슴 통증", "가슴이 아프"],
    "abdominal_pain": ["stomach pain", "belly pain", "stomach hurts", "my stomach", "tummy",
                        "gut pain", "stomach ache", "cramping in my stomach", "pain in my gut",
                        "복통", "배가 아프"],
    "headache": ["head pain", "head hurts", "head is pounding", "splitting headache",
                 "head is throbbing", "pain in my head",
                 "두통", "머리가 아프"],
    "fever": ["chills", "high temperature", "burning up", "running a temperature", "feverish",
              "temperature is high", "hot and shivery",
              "열", "발열", "오한"],
    "dyspnea": ["breathless", "can't breathe", "cant breathe", "can't catch my breath",
                "out of breath", "winded", "hard to breathe", "unable to breathe comfortably",
                "not getting enough air", "air hunger", "struggling to breathe", "throat feels tight",
                "throat is tightening", "gasping for air", "harder to breathe",
                "숨이 차", "호흡곤란"],
    "dizziness": ["dizzy", "lightheaded", "light-headed", "room spinning", "woozy",
                  "어지러", "현훈"],
    "altered_mental_status": ["confused", "unresponsive", "disoriented", "not making sense",
                              "out of it", "not himself", "not herself", "not tracking conversation",
                              "mentally foggy", "not acting like himself", "not acting like herself",
                              "seems out of it", "can't focus", "can't think straight", "zoning out",
                              "의식", "혼돈", "의식저하"],
    "urinary_symptoms": ["blood in urine", "burning when I pee", "burns when I pee",
                          "burning when I urinate", "pain when urinating", "peeing", "urinate",
                          "bladder",
                          "소변", "배뇨통", "빈뇨"],
    "syncope": ["passed out", "loss of consciousness", "blacked out", "went unconscious",
                "lost consciousness", "collapsed", "everything went dark",
                "실신", "기절"],
    "palpitations": ["heart racing", "irregular heartbeat", "heart pounding", "skipping beats",
                      "racing heart", "heart is fluttering", "heart skipping",
                      "pulse pounding in my throat", "feel my pulse in my throat",
                      "두근거림", "심계항진"],
    "vomiting": ["throwing up", "nausea and vomiting", "puking",
                 "구토", "토했"],
    "weakness": ["feeling weak", "muscle weakness", "no energy", "can't move", "no strength",
                 "body feels heavy", "drained of energy", "feel completely exhausted",
                 "무기력", "힘이 없"],
    "cough": ["coughing", "productive cough",
              "기침"],
    "back_pain": ["lower back pain", "side hurts", "side pain", "my flank",
                  "요통", "옆구리 통증"],
    "leg_swelling": ["swollen leg", "calf swelling",
                      "다리 부종", "종아리 부종"],
    "focal_weakness": ["weakness on one side", "one side feels weak", "arm won't work on one side",
                        "leg won't work on one side", "can't lift my arm", "face is drooping",
                        "drooping on one side", "one side of my face is drooping"],
    "aphasia": ["trouble finding words", "can't find my words", "words come out wrong",
                "can't speak clearly", "difficulty speaking", "speech sounds slurred",
                "can't get words out"],
    "gi_bleeding": ["blood in my stool", "black stools", "tarry stools", "vomiting blood",
                     "blood in my vomit", "rectal bleeding", "blood when I wipe"],
    "pelvic_gynecologic": ["vaginal spotting", "missed period", "cramping in my pelvis",
                            "lower pelvic pain", "pain in my ovary area", "pain in my pelvis"],
    "trauma": ["car accident", "fell down", "hit my head", "got into an accident",
               "was in a crash", "injured in a fall", "fell and hurt myself"],
    "allergic": ["hives", "swelling after a sting", "broke out in a rash after eating",
                 "reaction to a sting", "reaction to a food", "itchy welts", "throat swelling after exposure"],
    "metabolic": ["excessive thirst", "urinating a lot lately", "fruity breath", "rapid weight loss",
                  "extreme thirst and urination", "drinking a lot of water lately"],
}

CONCEPT_PHRASES = {tag: CANONICAL_TERMS[tag] + CONCEPT_ALIASES.get(tag, []) for tag in CANONICAL_TERMS}
_CANONICAL_SET = {tag: {t.lower() for t in terms} for tag, terms in CANONICAL_TERMS.items()}

# Backward-compatible alias for anything still importing the old flat name.
CHIEF_COMPLAINT_KEYWORDS = CONCEPT_PHRASES

# Presentations without their own dedicated disease pool are routed to the closest clinically
# related tag(s) so the candidate pool stays targeted instead of falling through to the entire
# knowledge base.
RELATED_TAGS = {
    "syncope": ["dizziness", "chest_pain"],
    "palpitations": ["chest_pain", "dizziness"],
    "vomiting": ["abdominal_pain"],
    "weakness": ["altered_mental_status", "dizziness"],
    "cough": ["dyspnea", "fever"],
    "back_pain": ["abdominal_pain", "urinary_symptoms"],
    "leg_swelling": ["dyspnea"],
    "focal_weakness": ["weakness", "altered_mental_status"],
    "aphasia": ["altered_mental_status", "focal_weakness"],
    "gi_bleeding": ["abdominal_pain", "vomiting"],
    "pelvic_gynecologic": ["abdominal_pain"],
    "trauma": ["chest_pain"],
    "allergic": ["dyspnea"],
    "metabolic": ["altered_mental_status", "weakness"],
}

# Cross-cutting can't-miss diagnoses (spec: soft routing must never lose safety coverage just
# because the chief complaint didn't cleanly match one category). Deliberately small and by
# diagnosis id, not duplicated logic -- differential.py already has a general critical-condition
# mechanism (safety.py's critical_condition_ids); this list is only the identifiers, consulted by
# differential.py when building a LOW-confidence candidate pool.
CROSS_CUTTING_DANGEROUS_DIAGNOSES = [
    "sepsis", "acute_coronary_syndrome", "pulmonary_embolism", "ischemic_stroke",
    "aortic_dissection", "diabetic_ketoacidosis", "hypoglycemia", "acute_abdomen",
]

_FUZZY_MATCH_THRESHOLD = 0.6  # same overlap ratio matching.py's feature_present() already uses

# An exact/alias primary tag needs at least this much of an integer-hit-count lead over the
# runner-up to count as unambiguous (scores in that range are always 1.0 + an integer hit count,
# so any real lead is >= 1.0 -- a tie is exactly 0.0). A fuzzy-only primary needs at least this
# much of a ratio lead over the runner-up to count as a real (not coincidental) margin.
_EXACT_HIGH_MARGIN = 1.0
_FUZZY_MEDIUM_MARGIN = 0.15

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
# per-call, since CONCEPT_PHRASES never changes at runtime. A phrase that degenerates to a single
# (or zero) meaningful word after stopword/contraction filtering (e.g. "out of it" -> just {"out"})
# is dropped entirely from fuzzy eligibility: exact/substring matching still catches it precisely,
# but a single common word scoring a trivial 1.0 overlap ratio against nearly any unrelated text is
# exactly the false-positive mechanism this fuzzy layer must not introduce.
_KEYWORD_CONTENT_WORDS: dict = {
    tag: [words for kw in keywords
          for words in [_meaningful_words(_content_words(kw))] if len(words) >= 2]
    for tag, keywords in CONCEPT_PHRASES.items()
}


def _fuzzy_score(text_words: set, tag: str) -> float:
    """Best word-overlap ratio between `text_words` and any single phrase under `tag` (both sides
    pre-filtered of contraction noise), using the same stemmed-content-word approach matching.py's
    feature_present() already uses elsewhere in this codebase."""
    best = 0.0
    for kw_words in _KEYWORD_CONTENT_WORDS[tag]:
        if not text_words:
            continue
        overlap = kw_words & text_words
        ratio = len(overlap) / len(kw_words)
        if ratio > best:
            best = ratio
    return best


@dataclass
class ChiefComplaintRoutingResult:
    primary_tag: str                    # "other" when nothing matched at all
    primary_score: float
    secondary_tags: List[str] = field(default_factory=list)   # ranked, excludes primary
    score_margin: float = 0.0           # primary_score - next-best score (0.0 if no runner-up)
    match_type: MatchType = "none"
    confidence: Confidence = "LOW"


def _scores(chief_complaint_text: str) -> List[Tuple[str, float, MatchType]]:
    """Every tag that scored anything against `chief_complaint_text`, highest first, each tagged
    with HOW it matched. An exact/alias hit always outranks a fuzzy-only match (scored in a
    disjoint, higher range) so fuzzy matching can only ever ADD coverage for phrasing exact/alias
    terms miss, never override a real hit."""
    lowered = (chief_complaint_text or "").lower()
    text_words = _meaningful_words(_content_words(lowered))
    scored: List[Tuple[str, float, MatchType]] = []
    for tag, phrases in CONCEPT_PHRASES.items():
        matched = [p for p in phrases if p.lower() in lowered]
        if matched:
            exact_hits = sum(1 for p in matched if p.lower() in _CANONICAL_SET[tag])
            match_type: MatchType = "exact" if exact_hits > 0 else "alias"
            scored.append((tag, 1.0 + len(matched), match_type))
            continue
        fuzzy = _fuzzy_score(text_words, tag)
        if fuzzy >= _FUZZY_MATCH_THRESHOLD:
            scored.append((tag, fuzzy, "fuzzy"))
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored


def route(chief_complaint_text: str) -> ChiefComplaintRoutingResult:
    """The full structured routing decision: which tag(s) are plausible, how sure the match is,
    and (via `confidence`) how differential.py should size the resulting candidate pool."""
    scored = _scores(chief_complaint_text)
    if not scored:
        return ChiefComplaintRoutingResult(primary_tag="other", primary_score=0.0,
                                            secondary_tags=[], score_margin=0.0,
                                            match_type="none", confidence="LOW")

    primary_tag, primary_score, match_type = scored[0]
    secondary_tags = [tag for tag, _score, _mt in scored[1:]]
    runner_up_score = scored[1][1] if len(scored) > 1 else None
    margin = primary_score - runner_up_score if runner_up_score is not None else primary_score

    if match_type in ("exact", "alias"):
        confidence: Confidence = "HIGH" if (runner_up_score is None or margin >= _EXACT_HIGH_MARGIN) \
            else "MEDIUM"
    else:  # fuzzy
        confidence = "MEDIUM" if margin >= _FUZZY_MEDIUM_MARGIN else "LOW"

    return ChiefComplaintRoutingResult(primary_tag=primary_tag, primary_score=primary_score,
                                        secondary_tags=secondary_tags, score_margin=margin,
                                        match_type=match_type, confidence=confidence)


def classify(chief_complaint_text: str) -> str:
    """Returns the best-matching tag, or 'other' if nothing matches (never a guessed tag)."""
    return route(chief_complaint_text).primary_tag


def top_candidates(chief_complaint_text: str, k: int = 3) -> List[str]:
    """Up to `k` plausible tags for this chief complaint (primary first, then ranked secondaries),
    for callers that only need the list, not the full routing result. Empty when nothing scored at
    all (genuinely unclassifiable text)."""
    result = route(chief_complaint_text)
    if result.match_type == "none":
        return []
    return [result.primary_tag] + result.secondary_tags[:max(0, k - 1)]


def related_tags(tag: str) -> list:
    """Additional tags whose disease pool is clinically relevant to `tag`, used by
    differential.diseases_for_tag() to build a targeted (not whole-catalog) candidate pool for
    presentations that don't have their own disease entries tagged directly."""
    return RELATED_TAGS.get(tag, [])
