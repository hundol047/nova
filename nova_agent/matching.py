"""Shared keyword/phrase overlap matching used by differential.py and safety.py to check whether a
knowledge-base feature phrase (e.g. "exertional chest pain") is supported by, or contradicted by,
the free-text findings gathered in PatientState. Deliberately simple (word-overlap + substring),
not an NLP/embedding similarity model -- keeps matching behavior stable/testable across runs.

Plain single-word overlap is too permissive for this domain: "left arm pain" and "denies
unilateral leg pain" share only the word "pain", which is generic enough to appear in almost every
finding regardless of relevance, and would otherwise register as a match. So:
  - stopwords and domain-generic words (pain, ache, discomfort, ...) never count toward overlap.
  - a short phrase (<=2 remaining content words) requires ALL of them present, not just some.
  - a longer phrase requires most (>=60%) of them present.
  - words are lightly, conservatively stemmed (see `_stem()` below -- deterministic suffix
    stripping for common morphological variants like weak/weakness or spin/spinning; a word with no
    matching suffix rule and no explicit `_IRREGULAR_STEM_OVERRIDES` entry is returned UNCHANGED,
    never truncated to a fixed character count -- Round E removed that fallback, since truncation
    could silently equate two otherwise-unrelated words that merely share a prefix)
    so real variant pairs still match without a full NLP stemmer dependency, while an unrelated
    word that merely shares a short prefix (e.g. "pain" vs "painting") stays distinct.
  - a phrase's low-information RELATIONAL/temporal words (after, worse, with, during, ...) must
    never by themselves satisfy a multi-word feature -- see `_distinguishing_tokens()` and
    `feature_present()`'s own gate below (Round E's feature-match specificity hardening).
"""

from __future__ import annotations

import functools
import re
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Callable, Dict, Iterator, List, Optional, Set
from nova_agent.assertion_status import is_uncertain

# --- turn-scoped memoisation ---------------------------------------------------------------------
# The differential re-derives the same pure string normalisations (stems, content-word sets, negation-
# scrubbed clauses, word-boundary patterns) hundreds of thousands of times per decision. They are memoised
# ONLY inside ``evaluation_scope()``, which the orchestrator opens around one decision and discards
# afterwards. The memo lives in a ContextVar, so it is private to the calling thread/async task: nothing
# patient-derived outlives the decision or crosses to another case. Outside a scope nothing is cached and
# behaviour is byte-identical (the memoised functions are pure).
_SCOPE: ContextVar[Optional[Dict[tuple, object]]] = ContextVar("nova_matching_scope", default=None)


@contextmanager
def evaluation_scope() -> Iterator[None]:
    """Memoise pure matching normalisations for the duration of one decision (re-entrant)."""
    if _SCOPE.get() is not None:
        yield
        return
    token = _SCOPE.set({})
    try:
        yield
    finally:
        _SCOPE.reset(token)


def _scoped(kind: str, key, compute: Callable[[], object]):
    memo = _SCOPE.get()
    if memo is None:
        return compute()
    slot = (kind, key)
    try:
        return memo[slot]
    except KeyError:
        value = memo[slot] = compute()
        return value

_STOPWORDS = {
    "a", "an", "the", "to", "of", "in", "on", "or", "and", "with", "is", "are", "was", "were",
    "at", "by", "for", "my", "it", "this", "that", "i", "have", "has", "no", "not", "also",
}
_GENERIC_MEDICAL_WORDS = {"pain", "ache", "aching", "discomfort", "feeling", "symptom", "symptoms", "sensation"}
_IGNORED = _STOPWORDS | _GENERIC_MEDICAL_WORDS
_OVERLAP_RATIO_THRESHOLD = 0.6

# Round E (feature-match specificity hardening): low-information RELATIONAL/temporal/severity
# connector words -- distinct from _GENERIC_MEDICAL_WORDS above (which are generic SYMPTOM-TYPE
# nouns, already stripped from every content-word set entirely). These words describe a relation
# ("after", "with", "during"), a comparison ("worse", "better"), or an unscoped severity/context
# descriptor ("acute", "severe", "episode", "history") that recurs across countless unrelated KB
# phrases -- a multi-word feature like "worse after meals" or "chest pain after trauma" must never
# be satisfied by unrelated text that only shares words from THIS set (e.g. "worse when I breathe"
# sharing only "worse", or "chest pain after a long work shift" sharing only "after"/"chest") while
# missing the phrase's own real distinguishing concept ("meals", "trauma"). Deliberately NOT merged
# into _IGNORED/_content_words() -- this must never blanket-strip these words from every content-
# word computation in the module (content_word_count()'s specificity weighting, the existing
# overlap-ratio math, aliasing, etc. all keep seeing them); it is used ONLY by
# `_distinguishing_tokens()` below, itself used only by feature_present()'s own extra gate.
_RELATIONAL_WORDS = {
    "after", "before", "with", "without", "during", "when", "worse", "better",
    "episode", "history", "acute", "severe",
}


def _distinguishing_tokens(content_words: Set[str]) -> Set[str]:
    """The subset of a phrase's own content words that actually carries its distinguishing
    clinical meaning -- everything left after also removing _RELATIONAL_WORDS (on top of the
    stopwords/generic-medical-words _content_words() already strips). Returns an empty set when a
    phrase reduces to nothing but relational words (rare for a real KB phrase); callers must treat
    that as "no distinguishing-token gate applies" rather than as a match failure."""
    return content_words - _RELATIONAL_WORDS

# CJK/Hangul text often has no whitespace between a clinical phrase and its surrounding
# inflection/punctuation (e.g. "高熱と頭痛", "黒色便が出る"). ASCII word-boundary matching would
# therefore miss a scoped multilingual alias even when the phrase is plainly present. Keep this
# separate from the English matcher and guard it with nearby multilingual negation markers so a
# phrase such as "高熱はありません" does not become positive evidence.
_NON_LATIN_RE = re.compile(r"[가-힣一-龯々ぁ-んァ-ヶ]")
_NON_LATIN_NEGATION_RE = re.compile(
    r"(?:없|아니|않|안|아닌|ない|ません|ありません|無い|なし|没有|无|否认|否定)"
)


def _non_latin_phrase_present(feature: str, finding: str) -> bool:
    if not _NON_LATIN_RE.search(feature):
        return False
    start = finding.find(feature) if feature else -1
    while start != -1:  # literal, non-overlapping occurrences (same as re.finditer(re.escape(feature)))
        end = start + len(feature)
        # A short local window catches suffix negation ("発熱はありません") and prefix negation
        # ("没有发热") without treating distant unrelated clauses as negations.
        before = finding[max(0, start - 10):start]
        after = finding[end:end + 12]
        if not (_NON_LATIN_NEGATION_RE.search(before) or _NON_LATIN_NEGATION_RE.search(after)):
            return True
        start = finding.find(feature, end)
    return False

# EXAM/TEST result strings routinely embed a negation in the SAME string as a positive finding
# (e.g. "clear breath sounds, no focal consolidation") -- unlike ASK answers, this text is never
# clause-split into PatientState.pertinent_negatives at all (see state.py's _absorb_answer vs.
# record_exam/record_test), so a PLAIN feature phrase like "focal consolidation" that happens to
# appear verbatim right after a "no"/"denies"/"without" in a finding must not be treated as that
# finding affirmatively supporting it -- it's the opposite. Handled by scrubbing each negated span
# (the trigger word plus its immediate local clause) out of a finding BEFORE either the substring
# or word-overlap match is attempted, so neither path can see words that were only ever mentioned
# to be denied. Only removes the local clause, not the rest of a longer finding string, so an
# unrelated earlier/later clause in the same finding is unaffected.


# Longest/most-specific suffix checked first (a `return`-on-first-match loop, so order matters):
# "-iness" before "-ness" (dizziness -> dizzy, not "dizzi"), "-ies" before generic "-s"/"-es",
# "-es" before bare "-s" (boxes -> box, not "boxe"). (suffix, replacement) -- replacement is "" for
# a plain strip, or a real letter for the y<->i orthographic swap English spelling uses before
# "-ness"/"-ed" endings.
#
# Deliberately NO "-ly" rule, despite being a common, otherwise-safe suffix pattern: a degree/
# intensity ADVERB (mildly, severely, moderately) very often modifies a completely different
# clinical dimension than the same-root ADJECTIVE appearing elsewhere in a knowledge-base phrase
# (e.g. an exam's "mildly coarse breath sounds" describes lung-sound TEXTURE, not overall symptom
# severity) -- stemming both to "mild" let that phrase spuriously satisfy viral_uri's own "mild
# symptoms" typical_feature via a single generic leftover content word, a real false positive this
# round's own generalization regression suite caught (see evaluation.benchmark's
# Cough01_CommonBronchitis case). None of this round's required target pairs need "-ly" stripping,
# so it stays out rather than accept that systemic collision risk.
#
# "-ish" IS included (Round E): a common, narrow adjectival suffix on real clinical descriptor
# words (feverish, bluish, yellowish) whose base noun/adjective IS the clinically meaningful
# concept (fever, blue, yellow) -- unlike "-ly", the base word here is almost always the SAME
# clinical dimension, not a different one, so this doesn't carry the same collision risk. Discovered
# via this round's own word-boundary hardening of feature_present()'s EXACT tier (see
# `_exact_phrase_present`): a plain, unbounded `"fever" in "...feverish..."` substring check used to
# accidentally cover this case; making that check word-boundary-safe (closing the "PE"/"period"
# false-positive class) also closed this legitimate variant unless it is handled explicitly here.
_SUFFIX_RULES: tuple = (
    ("iness", "y"), ("ies", "y"), ("ness", ""), ("ish", ""), ("ing", ""), ("ed", ""), ("es", ""), ("s", ""),
)
_MIN_STEM_LENGTH = 3
# Vowels plus w/x/y are never the second half of an English CVC-doubling pair (e.g. "spinning" =
# spin + doubled-n + ing; "seeing" is NOT see + doubled-e + ing -- "ee" is a vowel digraph, not a
# doubled consonant added for the suffix), so a trailing doubled letter from this set is left alone.
_NEVER_DOUBLED_FOR_SUFFIX = set("aeiouwxy")

# Round E (residual unsafe morphology fallback removal): tightly-scoped, hand-curated overrides for
# the rare irregular clinical derivational pair that shares NO suffix relationship any rule above
# can connect (spec: never fall back to truncating an arbitrary word to its first 6 characters,
# which can silently equate two otherwise-UNRELATED words that merely happen to share a prefix --
# e.g. a truncation fallback would have equated "generic"/"generalized" or "several"/"severe" at 6
# characters, a real safety risk this table closes generically). Each entry is a single, explicit,
# reviewed word pair -- never a broad rule -- and every entry must have its own test (see
# tests/test_morphology_no_truncation_fallback.py). Maps the LESS-common derived form to the
# canonical KB form it must normalize to; the canonical form already stems to itself unchanged.
_IRREGULAR_STEM_OVERRIDES = {
    "exertional": "exertion",
    # "pain when I breathe in" / "pain with breathing" / "shortness of breath": verb, gerund and noun forms of
    # one concept that no plain suffix rule joins (breathe+ing -> "breath", breath -> "breath").
    "breathe": "breath", "breathes": "breath", "breathing": "breath", "breaths": "breath",
    # "irregularly irregular rhythm" (the textbook AF finding) vs a report of "irregular rhythm": adverb/adjective.
    "irregularly": "irregular",
    # Round M anatomical adjective/noun pairs: a patient says "pain in one testicle" while a
    # feature says "testicular pain"; no suffix rule connects the two forms.
    "testicular": "testicle", "testis": "testicle", "testes": "testicle", "scrotal": "scrotum",
    "pelvic": "pelvis", "vaginal": "vagina", "urethral": "urethra",
    "ureteral": "ureter", "thoracic": "thorax", "esophageal": "esophagus",
    # canonical nouns whose plain "-s" ending the suffix rules would otherwise strip
    "pelvis": "pelvis", "esophagus": "esophagus",
    # swelling / swollen / swell are one clinical word that three different suffix paths stem to
    # three different values ("swel", "swollen", "swell"); warmth/warm likewise.
    "swelling": "swell", "swollen": "swell", "swelled": "swell", "swells": "swell", "warmth": "warm",
}


def _reduce_doubled_consonant(stem: str) -> str:
    """After stripping "-ing"/"-ed", undoes the standard English CVC-doubling spelling rule
    ("spinning" -> strip "-ing" -> "spinn" -> reduce -> "spin") so the base verb form matches its
    own gerund/past-tense -- conservative: only ever removes ONE trailing letter, only when the
    last two characters are an identical CONSONANT pair."""
    if len(stem) >= 3 and stem[-1] == stem[-2] and stem[-1] not in _NEVER_DOUBLED_FOR_SUFFIX:
        return stem[:-1]
    return stem


def _stem(word: str) -> str:
    return _scoped("stem", word, lambda: _stem_uncached(word))


def _stem_uncached(word: str) -> str:
    """Conservative, deterministic suffix-stripping morphology normalizer (spec: a common clinical
    morphological variant -- weak/weakness, spin/spinning, bleed/bleeding, vomit/vomiting, dizzy/
    dizziness, faint/fainting, numb/numbness -- must normalize to the same stem; an unrelated word
    that merely shares a short prefix must NOT, e.g. "pain" vs "painting" -- must stay distinct).

    Strips AT MOST ONE recognized suffix (see _SUFFIX_RULES, longest/most-specific first), and only
    when the remaining stem is still >= _MIN_STEM_LENGTH characters -- this length guard is what
    keeps a short, unrelated word from ever being touched at all: "pain" matches none of these
    suffixes to begin with, so it is never conflated with "painting" (paint+ing, itself correctly
    stemmed down to "paint", a different string). A doubled final consonant left behind by
    stripping "-ing"/"-ed" (the standard English CVC-doubling spelling rule) is reduced by one
    letter via `_reduce_doubled_consonant`.

    Round E removed the earlier bounded first-6-characters truncation this function fell back to
    when no suffix rule applied: that fallback could silently equate two otherwise-UNRELATED words
    that merely happen to share their first 6 characters (e.g. "generic"/"generalized" or
    "several"/"severe" would both have truncated to the same 6-character prefix) -- a real,
    generic false-positive risk, not merely a hypothetical one (see
    tests/test_morphology_no_truncation_fallback.py's negative controls, built independently of any
    blind evaluation set). When no suffix rule applies and the word is not one of the small,
    explicitly-reviewed `_IRREGULAR_STEM_OVERRIDES` pairs (e.g. "exertional"/"exertion", a genuine
    irregular derivational pair no plain suffix rule connects), this now simply returns the
    normalized original token UNCHANGED -- never truncated. Any FUTURE irregular pair needing
    normalization must be added to `_IRREGULAR_STEM_OVERRIDES` explicitly, with its own test, never
    handled by reintroducing a blanket truncation fallback."""
    lowered = word
    if lowered in _IRREGULAR_STEM_OVERRIDES:
        return _IRREGULAR_STEM_OVERRIDES[lowered]
    for suffix, replacement in _SUFFIX_RULES:
        if not lowered.endswith(suffix):
            continue
        if len(lowered) - len(suffix) + len(replacement) < _MIN_STEM_LENGTH:
            continue
        if suffix == "ed" and len(lowered) > 2 and lowered[-3] == "e":
            # A handful of common English verbs end in a natural "-eed" (bleed, breed, feed,
            # freed, greed, heed, need, seed, speed, weed) -- their base/present-tense form, not
            # some other root + the "-ed" past-tense suffix. Stripping "-ed" there would wrongly
            # turn "bleed" into "ble". Skipped only for this specific vowel-before-suffix pattern.
            continue
        stem = lowered[: -len(suffix)] + replacement
        if suffix in ("ing", "ed"):
            stem = _reduce_doubled_consonant(stem)
        return stem
    return lowered


_JOINABLE_HYPHEN = re.compile(r"\b(light|head|dizzy|nose|numb)-(headed|bleed|ness|sighted)\b")


# Everyday words for an anatomical region that the knowledge base names with its clinical adjective
# ("belly pain" vs "abdominal pain"). Mapped to the clinical adjective's own stem before matching so
# both directions agree; only unambiguous region words ("stomach" is NOT here: it names the organ
# as often as the region).
_LAY_ANATOMY = {"belly": "abdominal", "tummy": "abdominal"}


def _content_words(text: str) -> Set[str]:
    return set(_scoped("content", text, lambda: frozenset(_content_words_uncached(text))))


def _content_words_uncached(text: str) -> Set[str]:
    # A patient's hyphenation must not split one clinical word into two fragments
    # ("light-headed" == "lightheaded").
    words = re.split(r"[^a-z0-9가-힣]+", _JOINABLE_HYPHEN.sub(r"\1\2", text.lower()))
    return {_stem(_LAY_ANATOMY.get(w, w)) for w in words if w and w not in _IGNORED}


def content_word_count(text: str) -> int:
    """Public wrapper around `_content_words()` -- differential.py uses this to weight a matched
    knowledge-base phrase by its own specificity (see `_specificity_multiplier()` there)."""
    return len(_content_words(text))


def content_words(text: str) -> Set[str]:
    """Public wrapper around `_content_words()` -- differential.py uses the actual word SET (not
    just the count) to check whether a phrase reduces to nothing but generic physiologic-severity
    markers (see `_specificity_multiplier()` there, Round E's defect C)."""
    return _content_words(text)


# "absent breath sounds", "absent pulses", "absent bowel sounds": here "absent" DESCRIBES the examination
# finding (the sign is absent) -- it does not negate a symptom mentioned earlier or later in the report.
_ABSENT_SIGN = (r"(?:breath|bowel|heart|lung|air entry|tendon|deep tendon|corneal|gag|femoral|radial|pedal|"
                r"distal|peripheral|carotid|pulses?|reflexes?|bruits?)\b")


def _strip_negated_spans(text: str) -> str:
    return _scoped("strip", text, lambda: _strip_negated_spans_uncached(text))


def _strip_negated_spans_uncached(text: str) -> str:
    # Negation ends at a clause boundary, not an arbitrary four-word window.
    # Keep affirmative clauses after "but"/"however" rather than erasing the entire report.
    # Sentence periods are boundaries too; decimal points are not.
    # A comma is not an assertion boundary: in "no A, B, or C" the denial
    # governs all three. Only a new explicit predicate escapes the list.
    clauses = re.split(r"[;\n]|(?<=[a-z])\.(?=\s|$)|\b(?:but|however)\b|"
                       r",\s*(?=(?:(?:and\s+)?(?:i|he|she|the patient)\s+(?:have|has|feel|feels|report|reports|am|is)\b|"
                       r"(?:has|have|reports?)\b|[^,;\n]{1,70}\b(?:is|are|was|were)\b))", text, flags=re.I)
    positive = []
    for clause in clauses:
        if is_uncertain(clause):
            continue
        # Reports often place the negation after the finding. Scrubbing only
        # from "not" onward would leave the denied finding looking positive.
        if re.search(r"(?:\b(?:is|are|was|were)\s+|:\s*)(?:absent|negative|not (?:present|seen|detected|found))\b"
                     r"|\b(?:absent|not present|not seen|not detected|not found)\s*[.!]?\s*$", clause, re.I):
            continue
        positive.append(re.sub(r"\b(?:no|not|denies|denied|without|negative for|absent(?!\s+" + _ABSENT_SIGN + r"))\b.*$",
                               " ", clause, flags=re.I))
    return " ; ".join(positive)


def _exact_phrase_present(feature_lower: str, finding_lower: str) -> bool:
    """Word-boundary-safe version of a plain substring check. A naive `feature_lower in
    finding_lower` check is unsafe for a SHORT feature/alias (e.g. the disease-name alias "PE" for
    pulmonary_embolism, or "MI" for acute_coronary_syndrome): as a raw substring, "pe" silently
    matches inside completely unrelated words like "period" or "experience", and "mi" matches
    inside "family" or "time" -- a real, general false-positive risk for every short clinical
    abbreviation in the knowledge base (see tests/test_feature_match_generic_word_collision.py),
    not a hypothetical one (this is exactly how "PE" matched a social-history mention of a late
    "period" and hijacked a reproductive-age-emergency case's candidate pool during Round E
    development). `\\b` is Unicode-aware by default for `str` patterns in Python 3, so this stays
    correct for Korean/Japanese multi-character phrases too. A multi-word phrase like "one-sided
    headache" is unaffected -- the boundary only anchors the two ends of the whole phrase, any
    internal punctuation/spacing is matched literally exactly as before."""
    if not feature_lower:
        return re.search(r"\b\b", finding_lower) is not None
    # Equivalent to re.search(rf"\b{re.escape(feature_lower)}\b", finding_lower) -- Python's Unicode \w is
    # exactly str.isalnum() or "_" -- without compiling a new pattern per phrase (a measured hot spot).
    start = finding_lower.find(feature_lower)
    while start != -1:
        if _word_boundary(finding_lower, start) and _word_boundary(finding_lower, start + len(feature_lower)):
            return True
        start = finding_lower.find(feature_lower, start + 1)
    return False


def _is_word_char(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def _word_boundary(text: str, index: int) -> bool:
    before = index > 0 and _is_word_char(text[index - 1])
    after = index < len(text) and _is_word_char(text[index])
    return before != after


# Direction-of-change words. A feature that asserts one direction ("low blood pressure") must not be
# satisfied by a finding asserting the OPPOSITE direction ("high blood pressure") merely because the
# remaining words overlap: 2 of 3 content words used to clear the 60% threshold, so a history of
# hypertension credited hypotension-defined diagnoses. Stems, so "elevated"/"increased" etc. are
# covered through _content_words().
_POLARITY_UP = {"high", "elevat", "increas", "rais", "rapid", "fast", "hyper"}
_POLARITY_DOWN = {"low", "decreas", "reduc", "slow", "hypo", "drop"}


def _opposite_polarity(feature_content: Set[str], finding_content: Set[str]) -> bool:
    f_up, f_down = bool(feature_content & _POLARITY_UP), bool(feature_content & _POLARITY_DOWN)
    if f_up == f_down:  # no direction word, or both (ambiguous): do not gate
        return False
    n_up, n_down = bool(finding_content & _POLARITY_UP), bool(finding_content & _POLARITY_DOWN)
    return (f_up and n_down and not n_up) or (f_down and n_up and not n_down)


# Round U follow-up: British and American spellings of the SAME medical word ("diarrhoea"/"diarrhea",
# "oedema"/"edema", "haemoptysis"/"hemoptysis", "hyponatraemia"/"hyponatremia") are one word. Both the KB phrase and
# the finding are normalised to the US form, so this only ever equates identical words; it adds no synonym.
_US_SPELLING = tuple((re.compile(p, re.IGNORECASE), r) for p, r in (
    (r"\boe(?=dem|sophag|strog)", "e"),     # oedema, oesophagus, oestrogen
    (r"(?<=[hn])oea\b", "ea"),              # diarrhoea, amenorrhoea, dyspnoea, orthopnoea, apnoea
    (r"\bhaem", "hem"),                     # haemoptysis, haemorrhage, haematuria
    (r"(?<=[a-z])aem(?=[a-z])", "em"),       # anaemia, ischaemia, hyperkalaemia, septicaemia, hypoxaemia
    (r"\bpaed", "ped"),
    (r"\bfoet", "fet"),
    (r"\b(tum|col|behavi)our", r"\1or"),
))


@functools.lru_cache(maxsize=65536)
def us_spelling(text: str) -> str:
    lowered = text.lower() if text else ""
    if not lowered or not ("oe" in lowered or "ae" in lowered or "our" in lowered):
        return text
    for pattern, repl in _US_SPELLING:
        text = pattern.sub(repl, text)
    return text


def feature_present(feature: str, findings_text: List[str], scrub_negated_spans: bool = False, strict: bool = False,
                    ignore_words: frozenset = frozenset()) -> bool:
    feature = us_spelling(feature)
    findings_text = [us_spelling(t) for t in findings_text]
    return _scoped("feature", (feature, tuple(findings_text), scrub_negated_spans, strict, frozenset(ignore_words)),
                   lambda: _feature_present_uncached(feature, findings_text, scrub_negated_spans, strict, ignore_words))


_PAIN_FEATURE = re.compile(r"\b(?:pain|ache|aching)\b")
_PAIN_ASSERTION = re.compile(
    r"\b(?:pain|painful|ache|aches|aching|discomfort|hurt|hurts|hurting|radiat\w*|tight(?:ness)?|"
    r"crushing|squeez\w*|burning|cramp\w*|stabbing|sharp|throbbing)\b|통증|아프|아파|痛|疼")
_ASSERTION_SPLIT = re.compile(r"[;\n]|(?<=\w)\.(?=\s|$)")


def _assertion_clauses(finding: str) -> tuple:
    return _scoped("clauses", finding, lambda: tuple(_ASSERTION_SPLIT.split(finding.lower())))


# Round Q: a qualifier that IS the clinical meaning of a feature. Stemming folds "irregularly" into "irregular", so
# a plain "irregular rhythm" would otherwise satisfy the specific AF finding "irregularly irregular rhythm". A feature
# carrying a protected qualifier is met only by a clause that states that qualifier explicitly; the general wording
# is handled by the general feature ("irregular heartbeat") instead. Stemming itself is unchanged everywhere else.
_PROTECTED_QUALIFIERS = (
    ("irregularly irregular", re.compile(r"\birregularly[\s-]+irregular\b")),
    # The pain must be linked to urination, not to another body site in the same clause.
    ("pain on urinating", re.compile(r"\b(?:pain|painful|burning|burns|hurts?)\s+(?:(?:when|while|on|with|during)\s+)?(?:i\s+)?(?:urinating|urination|passing urine|pee(?:ing)?)\b")),
    ("pain when urinating", re.compile(r"\b(?:pain|painful|burning|burns|hurts?)\s+(?:(?:when|while|on|with|during)\s+)?(?:i\s+)?(?:urinating|urination|passing urine|pee(?:ing)?)\b")),
)

# Require the symptom-to-posture relation, not a bag containing "standing".
# NICE CG109 1.2.1.2 / CG109 postural-hypotension assessment; vocabulary
# normalization only, never a diagnosis or an inferred lying/standing BP.
POSTURAL_LIGHTHEADEDNESS = re.compile(
    r"\b(?:lightheadedness|lightheaded|light-headed|dizziness|dizzy|woozy|faint(?:ness)?)\s+"
    r"(?:(?:occurs?|happens?|starts?|begins?)\s+)?(?:on|upon|when|after|whenever|every time)\s+"
    r"(?:i\s+)?(?:stand(?:ing)?(?: up)?|get(?:ting)? up|ris(?:e|ing))\b|"
    r"\b(?:on|upon|when|after|whenever|every time)\s+(?:i\s+)?(?:stand(?:ing)?(?: up)?|get(?:ting)? up|ris(?:e|ing))"
    r"\s*[,; ]\s*(?:i\s+)?(?:feel\s+|get\s+|become\s+|am\s+)?(?:dizzy|lightheaded|light-headed|woozy|faint)\b|"
    r"\b(?:standing up|getting up|rising)\s+(?:makes? me|causes?|triggers?)\s+(?:feel\s+)?"
    r"(?:dizzy|lightheaded|light-headed|woozy|faint|dizziness|lightheadedness)\b|"
    r"(?:일어설|일어날|일어나면|기립할)\s*(?:때(?:마다)?|마다)?\s*(?:머리가\s*)?"
    r"어지(?:럽|러|럼)(?![^.;,]{0,10}(?:않|없))", re.I)


def _protected_qualifier(feature_lower: str):
    from nova_agent.feature_relations import RELATION_PATTERNS
    if feature_lower in RELATION_PATTERNS:
        return RELATION_PATTERNS[feature_lower]
    if (re.search(r"\b(?:blood|bloody)\b", feature_lower)
            and re.search(r"\b(?:cough\w*|spit\w*|sputum|expectorat\w*)\b", feature_lower)):
        # Blood must be the expelled material or modify the sputum, not be
        # borrowed from a separate blood test/pressure mention in the clause.
        return re.compile(
            r"\b(?:cough\w*|spit\w*|expectorat\w*)\s+(?:up\s+|out\s+)?"
            r"(?:(?:some|fresh|a little|small amounts? of)\s+)?(?:blood|bloody sputum)\b|"
            r"\b(?:bloody|blood[- ](?:streaked|tinged|stained))\s+(?:sputum|phlegm|mucus)\b|"
            r"\b(?:sputum|phlegm|mucus)\s+(?:contains?|containing|with|mixed with|streaked with)\s+blood\b|"
            r"\bblood\s+in\s+(?:(?:my|the|his|her)\s+)?(?:sputum|phlegm|mucus)\b|"
            r"\b(?:sputum|phlegm|mucus)\s+(?:is|was)\s+(?:bloody|blood[- ](?:streaked|tinged|stained))\b|"
            r"\bblood\s+(?:(?:was|is|has been)\s+)?(?:coughed|spat|expectorated)\b")
    if feature_lower == "lightheadedness on standing up":
        return POSTURAL_LIGHTHEADEDNESS
    if feature_lower == "pain spreading across abdomen":
        return re.compile(r"\bspread(?:s|ing)?\b[^.;]{0,30}\b(?:abdomen|belly)\b|"
                          r"\b(?:abdominal|belly) pain\b[^.;]{0,20}\bspread(?:s|ing)?\b")
    if (re.search(r"\b(?:urinating|urination|urine|pee|peeing|wee)\b", feature_lower)
            and re.search(r"\b(?:pain|painful|burning|burns|hurt|hurts|stings)\b", feature_lower)):
        return re.compile(
            r"\b(?:pain|painful|burning|burns|hurts?|stings)\s+(?:(?:when|while|on|with|during|after)\s+)?"
            r"(?:i\s+)?(?:urinating|urination|passing urine|pee(?:ing)?|wee)\b|"
            r"\b(?:urinating|urination|passing urine|pee(?:ing)?|wee)\s+(?:is\s+)?(?:painful|hurts?|burns|stings)\b")
    return next((pattern for phrase, pattern in _PROTECTED_QUALIFIERS if phrase in feature_lower), None)


_OR_PREFIX = re.compile(r"^(?:family history of|history of|known|prior|previous|recent)\s+")


def or_branches(feature: str) -> tuple:
    """Round Q: the explicit alternatives of ONE "A or B" feature, each a complete phrase, or () when the feature is
    not such a disjunction. A shared leading context ("history of heart attack or cardiomyopathy") is carried to the
    second branch. Branches of one content word are not split off ("calf pain or tenderness" stays whole), so a
    lone generic word never stands in for the feature. Used for PRESENCE only: denying one branch never denies the
    disjunction (callers keep checking the whole phrase for contradiction)."""
    low = feature.lower().strip()
    from nova_agent.feature_relations import RELATION_PATTERNS
    if low in RELATION_PATTERNS:
        return ()  # shared predicate cannot be lost from the second branch
    if low.count(" or ") != 1:
        return ()
    left, right = (part.strip() for part in low.split(" or "))
    prefix = _OR_PREFIX.match(left)
    if prefix and not _OR_PREFIX.match(right):
        right = prefix.group(0) + right
    if len(_content_words(left)) < 2 or len(_content_words(right)) < 2:
        # Round U follow-up: two participles sharing the SAME head and complement ("pain relieved or worsened by
        # eating") are distributed to two complete phrases; anything else stays whole.
        m = re.fullmatch(r"(.+?)\s+(\w+ed)", left)
        n = re.fullmatch(r"(\w+ed)\s+((?:by|with|after|on|when)\b.+)", right)
        if m and n:
            return (f"{m.group(1)} {m.group(2)} {n.group(2)}", f"{m.group(1)} {n.group(1)} {n.group(2)}")
        return ()
    return (left, right)


def and_branches(feature: str) -> tuple:
    """Round U follow-up: the two members of ONE short list feature ("nausea and vomiting", "polyuria and polydipsia",
    "fever and malaise"), or () otherwise. The feature is present only when BOTH members are observed -- possibly
    in different statements ("nausea" in the complaint, "vomiting" in a later answer). Used for PRESENCE only; a
    denial of one member never denies the pair, and a pair still counts as ONE piece of evidence."""
    low = feature.lower().strip()
    from nova_agent.feature_relations import RELATION_PATTERNS
    if low in RELATION_PATTERNS or low.count(" and ") != 1 or " or " in low:
        return ()
    left, right = (part.strip() for part in low.split(" and "))
    if re.search(r"\b(?:with|without|after|before|on|when|while|history|known|prior|previous)\b", low):
        return ()
    if not (1 <= len(left.split()) <= 3 and 1 <= len(right.split()) <= 3):
        return ()
    if not _content_words(left) or not _content_words(right):
        return ()
    return (left, right)


def _feature_present_uncached(feature: str, findings_text: List[str], scrub_negated_spans: bool = False,
                              strict: bool = False, ignore_words: frozenset = frozenset()) -> bool:
    """`scrub_negated_spans=True` is for checking against a general finding bag (e.g.
    state.all_findings_text()) that can contain an EXAM/TEST result embedding an unrelated
    negation in the same string. Leave it False (the default) when checking against
    PatientState.pertinent_negatives -- those entries ARE the negative statement itself (e.g.
    "denies chest pain"), so scrubbing them would erase the very text being matched against."""
    feature_content = _content_words(feature) - ignore_words
    feature_lower = feature.lower()
    distinguishing = _distinguishing_tokens(feature_content)
    # Match within one assertion, not a whole report. Otherwise words from unrelated
    # sentences ("left arm BP ... abdominal pain") invent "left arm pain". Negation
    # scrubbing also inserts semicolons for commas, so split ORIGINAL assertions first.
    # Comma-linked qualifiers ("cannot walk, started yesterday") stay together.
    from nova_agent.evidence_scope import patient_evidence_text
    scoped_findings = [patient_evidence_text(t) for t in findings_text] if (
        scrub_negated_spans and not feature_lower.startswith("family history")) else findings_text
    clauses = (clause for finding in scoped_findings for clause in _assertion_clauses(finding))
    feature_is_pain = _scoped("is_pain", feature_lower, lambda: bool(_PAIN_FEATURE.search(feature_lower)))
    for finding_lower in clauses:
        # A Korean case/topic particle attached to an English clinical phrase
        # is a grammatical boundary, not part of that English word.
        finding_lower = re.sub(r"(?<=[a-z])(?:은|는|이|가|을|를)(?=\s)", " ", finding_lower)
        if scrub_negated_spans:
            finding_lower = _strip_negated_spans(finding_lower)
        capability = re.search(r"\b(?:unable to|inability to|cannot|can't)\s+(.+)", feature_lower)
        if capability:
            predicate = re.split(r"\b(?:came|started|began|suddenly|after|since)\b", capability.group(1))[0]
            target = _content_words(predicate)
            def action_head(value):
                return next((_stem(t) for t in re.findall(r"[a-z]+", value) if t not in _IGNORED), None)
            scopes = re.finditer(r"\b(?:unable to|inability to|cannot|can't)\s+([^,;.]+)", finding_lower)
            if not any(action_head(m.group(1)) == action_head(capability.group(1)) and
                       target <= _content_words(re.split(r"\b(?:and|but)\b", m.group(1))[0]) for m in scopes):
                continue
        protected = _scoped("protected", feature_lower, lambda: _protected_qualifier(feature_lower))
        if protected is not None:
            if protected.search(finding_lower):
                return True
            continue
        # Pain is excluded from specificity scoring, but it remains a required assertion.
        # A BP report mentioning the left arm must not become 'left arm pain'; a description of the sensation
        # itself ("pressure radiating to my left arm", "crushing", "sharp") IS a pain assertion.
        if feature_is_pain and not _scoped("pain_assertion", finding_lower,
                                           lambda: bool(_PAIN_ASSERTION.search(finding_lower))):
            continue
        # A prodrome is an explicitly preceding symptom. Preserve that temporal
        # qualifier instead of requiring patients to use the word "prodrome".
        if feature_lower.startswith("prodrome of "):
            symptom = _content_words(feature_lower[len("prodrome of "):])
            for clause in re.split(r"[;,\n]", finding_lower):
                before = re.search(r"\b(?:before|preceding|prior to)\b", clause)
                if before and not re.search(r"\bafter\b", clause[:before.start()]):
                    preceding_words = _content_words(clause[:before.start()])
                    if symptom and symptom <= preceding_words:
                        return True
        # Only the feature-contained-in-finding direction is a safe substring shortcut (a longer
        # finding sentence happens to contain the whole feature phrase verbatim, e.g. feature
        # "diaphoresis" in finding "diaphoresis, nausea, ..."). The reverse direction (finding
        # contained in feature) is NOT safe: a short, generic finding like the bare chief
        # complaint text "headache" is trivially a substring of almost any longer feature phrase
        # that happens to contain that word (e.g. "worst headache of life"), which would falsely
        # match every such feature regardless of relevance -- so it is deliberately not checked.
        # This EXACT tier is unconditional (never gated below) -- the whole literal phrase text
        # being present, ON A WORD BOUNDARY (see `_exact_phrase_present`), is inherently safe
        # regardless of which of its words are "relational".
        if _exact_phrase_present(feature_lower, finding_lower) or _non_latin_phrase_present(feature_lower, finding_lower):
            return True
        if not feature_content:
            continue
        finding_content = _content_words(finding_lower)
        # A material qualifier cannot disappear in the partial-token fallback:
        # coughing UP sputum is not coughing UP BLOOD. Complete clinical/lay
        # aliases still take their own path, so this asserts no new finding.
        blood = {"blood", "bloody"}
        if feature_content & blood and not finding_content & blood:
            continue
        if _opposite_polarity(feature_content, finding_content):
            continue
        # Round E gate (feature-match specificity hardening): a phrase's distinguishing tokens
        # (its content words minus low-information RELATIONAL connectors like "after"/"worse"/
        # "with") must independently clear the SAME two-tier presence rule the full content-word
        # set does below -- otherwise generic relational words overlapping alone (e.g. "worse
        # after meals" satisfied by "...worse when I breathe...", sharing only "worse"; "chest
        # pain after trauma" satisfied by "chest pain after a long work shift", sharing only
        # "after"/"chest") could clear the overlap-ratio check on relational words alone, with the
        # phrase's real distinguishing concept ("meals", "trauma") never actually present. Purely
        # ADDITIVE -- never loosens matching, only narrows it further; skipped only when a phrase
        # has no distinguishing tokens left at all (rare), since no meaningful gate could apply.
        if distinguishing:
            distinguishing_overlap = distinguishing & finding_content
            if len(distinguishing) <= 2:
                if distinguishing_overlap != distinguishing:
                    continue
            elif len(distinguishing_overlap) / len(distinguishing) < _OVERLAP_RATIO_THRESHOLD:
                continue
        overlap = feature_content & finding_content
        if strict or len(feature_content) <= 2:
            if overlap == feature_content:
                return True
        elif len(overlap) / len(feature_content) >= _OVERLAP_RATIO_THRESHOLD:
            if _direction_missing(feature_content, finding_content):
                # Round P: a feature that asserts a DIRECTION ("low blood pressure") is not met by a finding that
                # shares its other words but states no direction ("a blood pressure tablet").
                continue
            if _head_or_pattern_missing(feature_lower, finding_content):
                # Round P: a partial match must keep the phrase's time-pattern qualifier ("EPISODIC high blood
                # pressure" is not a history of hypertension).
                continue
            return True
    return False


_RELATIONAL_STEMS = {_stem(w) for w in _RELATIONAL_WORDS} | {"wors", "worse", "better", "bett"}
_QUALIFIER_SPLIT = re.compile(r"\s(?:on|with|after|during|when|while|at|in|from|to|across|into|over|before|"
                              r"following|without|for|due)\s")
_PATTERN_QUALIFIERS = {"episod", "intermitt", "paroxysm", "recurr", "sudden", "chronic", "persist", "constant"}


def _head_or_pattern_missing(feature_lower: str, finding_content: Set[str]) -> bool:
    from nova_agent.config import get_config
    if not get_config().evidence_v3_enabled:
        return False
    if feature_lower.startswith("sudden onset "):
        # Shared timing is not a shared symptom: sudden-onset headache must not
        # generate sudden-onset dyspnea or palpitations. Existing complete aliases
        # are matched separately; this guards only the partial-token fallback.
        symptom = _content_words(feature_lower[len("sudden onset "):])
        if not symptom <= finding_content:
            return True
    base = _QUALIFIER_SPLIT.split(feature_lower, maxsplit=1)[0]  # "shortness of breath | on exertion"
    ordered = [_stem(t) for t in re.findall(r"[a-z0-9]+", base) if t not in _IGNORED]
    ordered = [t for t in ordered if t and t not in _RELATIONAL_STEMS]
    if not ordered:
        return False
    # (A head-noun requirement was tried here and reverted: it broke legitimate partial matches such as
    # "periumbilical pain migrating to right lower quadrant", costing correct appendicitis diagnoses.)
    return any(q in t for t in ordered for q in _PATTERN_QUALIFIERS) and not any(
        q in w for w in finding_content for q in _PATTERN_QUALIFIERS if any(q in t for t in ordered))


def _direction_missing(feature_content: Set[str], finding_content: Set[str]) -> bool:
    from nova_agent.config import get_config
    if not get_config().evidence_v3_enabled:
        return False
    up, down = feature_content & _POLARITY_UP, feature_content & _POLARITY_DOWN
    if bool(up) == bool(down):
        return False
    wanted = _POLARITY_UP if up else _POLARITY_DOWN
    return not (finding_content & wanted)


_LEADING_NEGATION = re.compile(r"^\s*(?:denies|denied|no|without|negative for|never had|not experiencing|"
                               r"(?:does not|doesn't|do not|don't|did not|didn't) have)\b[:\s]*", re.IGNORECASE)


def _narrower_than_feature(feature_words: Set[str], negative: str) -> bool:
    """A denial that names MORE than the feature does not refute the feature: "denies productive cough" says
    nothing about a bare "cough" (the patient may have a dry one), whereas "denies cough" does refute
    "dry cough". True when the denied phrase carries a content word the feature lacks."""
    if not _LEADING_NEGATION.match(negative):
        return False
    target = _content_words(_LEADING_NEGATION.sub("", negative, count=1).lower())
    return bool(target) and bool(feature_words) and feature_words <= target and bool(target - feature_words)


def feature_denied(feature: str, negatives: List[str]) -> bool:
    feature = us_spelling(feature)
    negatives = [us_spelling(n) for n in negatives]
    feature_words = _content_words(feature)
    targets = []
    for negative in negatives:
        if _LEADING_NEGATION.match(negative):
            body = _LEADING_NEGATION.sub("", negative, count=1)
            targets.extend("no " + p.strip() for p in re.split(r",|\b(?:and|or|nor)\b", body) if p.strip())
        else:
            targets.append(negative)
    effective = [n for n in targets if not _narrower_than_feature(feature_words, n)]
    # A denial needs the actual finding, not 60% of its qualifiers ("no sudden
    # rapid palpitations" must not contradict sudden dyspnoea).
    return feature_present(feature, effective, strict=True)


# Locally negated span ("denies chest pain"): used ONLY by explicitly_denied_in_findings(); the
# general negation scrubber _strip_negated_spans() is clause-based (see above).
_NEGATED_SPAN_PATTERN = re.compile(
    r"\b(?:no|not|denies|denied|without|absent(?!\s+" + _ABSENT_SIGN + r")|negative for)\s+"
    r"(?:(?!\b(?:but|however)\b|,\s*(?:(?:i|he|she)\s+)?(?:has|have|reports?|feels?)\b)[^;.\n])*",
    re.IGNORECASE,
)


def explicitly_denied_in_findings(feature: str, findings: List[str]) -> bool:
    """Match only locally negated spans, never infer a denial from shared content words.

    General findings contain positive AND negative statements; unlike pertinent_negatives,
    they cannot be passed wholesale to feature_denied(). Clause boundaries remain bounded by
    the existing negation parser. This is an English-text helper, not a full language model.
    """
    spans = [m.group(0) for finding in findings for m in _NEGATED_SPAN_PATTERN.finditer(finding)]
    return feature_denied(feature, spans)


# Feature-local aliases (spec section 6, Option A): alternate phrasings tried ONLY when evaluating
# the ONE exact knowledge-base phrase they are keyed to -- never a global finding-text substitution
# like the earlier clinical_synonyms.py attempt (reverted after it let unrelated findings that
# merely shared a word-group cross-contaminate each other's matches, e.g. "mild fever" spuriously
# supporting "denies high fever"). A lay phrase here can only ever help the ONE named KB phrase.
# Shared here (not duplicated in differential.py and candidate_generator.py separately) so an
# aliased risk_factor/typical_feature/history phrase behaves identically whether it is being
# scored (differential.py's own _score_disease) or being used to decide candidate POOL MEMBERSHIP
# in the first place (candidate_generator.py's risk_match/medication_match/history_match) -- these
# two call sites diverging was a real bug (a diagnosis reachable ONLY through an aliased
# risk/medication phrase, e.g. "aspirin" for the KB's own "antiplatelet use", could score correctly
# once present, but never actually ENTER the pool via that alias in the first place). Two
# categories populate this table: (1) common lay-language variants of a clinical sign
# (throbbing/pulsating, sensitive to light/photophobia) and (2) high-value medication-class/
# condition-name normalization (spec section 4) -- a specific drug name or plain-English condition
# name standing in for the canonical risk factor phrase it belongs to. Deliberately NOT a general
# medication/condition NLP system: only classes/conditions an existing knowledge-base
# risk_factor/typical_feature already names.
FEATURE_ALIASES: dict[str, list[str]] = {
    "unilateral pulsating headache": ["throbbing headache", "pounding headache", "one-sided headache",
                                       "one sided headache", "pounding pain", "throbbing pain",
                                       "pulsating pain"],
    "photophobia": ["sensitive to light", "light sensitivity", "light bothers me"],
    "phonophobia": ["sensitive to sound", "sound sensitivity", "noise bothers me"],
    "aura": ["shimmering lights", "visual aura", "flashing lights", "seeing spots before",
             "zigzag lines", "blind spot in my vision", "jagged lines"],
    "recurrent similar episodes": ["similar to headaches", "happened before", "same as before",
                                    "feels the same as last time", "this feels the same",
                                    "gets these", "a few times a year", "has had these before"],
    "family history of migraine": ["mother gets migraines", "father gets migraines",
                                    "mother has migraines", "parent gets migraines", "runs in my family",
                                    "sister gets migraines", "sister has migraines", "brother gets migraines"],
    "known migraine history": ["diagnosed with migraines", "history of migraines", "has migraines before"],
    "syncope": ["passed out", "fainted"],
    "palpitations": ["racing heartbeat", "heart racing"],
    # Medication-class normalization (spec section 4).
    "sulfonylurea use": ["glipizide", "glyburide", "glimepiride", "sulfonylurea"],
    "insulin use": ["insulin", "lantus", "humalog", "novolog", "glargine"],
    "known diabetes on insulin": ["insulin", "lantus", "humalog", "novolog", "glargine"],
    "anticoagulant use": ["warfarin", "apixaban", "rivaroxaban", "dabigatran", "heparin", "coumadin"],
    "antiplatelet use": ["aspirin", "clopidogrel"],
    "nsaid use": ["ibuprofen", "naproxen", "nsaid"],
    "diuretic use": ["water pill", "furosemide", "hydrochlorothiazide", "lasix"],
    "immunosuppressant use": ["prednisone", "methotrexate", "tacrolimus", "cyclosporine", "azathioprine"],
    "oral contraceptive use": ["birth control", "oral contraceptive", "the pill"],
    "missed meal": ["hasn't eaten", "hasn't eaten much", "poor oral intake", "not eating today",
                     "skipped a meal", "skipped meals"],
    # Common lay/plain-English terms for a risk_factor a KB entry names by its clinical term
    # (spec section 4's medication-class normalization, generalized to a few very common
    # condition-name risk factors) -- scoped to the ONE named risk_factor phrase each, same
    # discipline as every alias above, never a general finding-text substitution.
    "hyperlipidemia": ["high cholesterol", "elevated cholesterol", "high blood cholesterol", "high lipids"],
    "hypertension": ["high blood pressure", "elevated blood pressure"],
    "poorly controlled hypertension": ["poorly controlled high blood pressure", "uncontrolled blood pressure",
                                        "uncontrolled hypertension", "high blood pressure that's not controlled"],
    "atrial fibrillation": ["afib", "a-fib", "irregular heart rhythm", "irregular heartbeat history"],
    "immobilization": ["long flight", "long car ride", "bed rest", "recent long travel", "sitting for hours"],
    "long travel": ["long flight", "long car ride", "recent long trip"],
    "liver disease": ["cirrhosis", "hepatitis", "liver problems"],
    "peptic ulcer disease": ["stomach ulcer", "ulcer history", "history of ulcers"],
}


_LAY_VARIANTS: Set[tuple] = set()


def _strict_alias_present(alias: str, findings: List[str], scrub_negated_spans: bool) -> bool:
    alias = us_spelling(alias)
    findings = [us_spelling(f) for f in findings]
    return _scoped("strict_alias", (alias, tuple(findings), scrub_negated_spans),
                   lambda: _strict_alias_present_uncached(alias, findings, scrub_negated_spans))


def _strict_alias_present_uncached(alias: str, findings: List[str], scrub_negated_spans: bool) -> bool:
    """Lay-language variants are matched STRICTLY: the literal phrase on a word boundary, or EVERY
    one of its content words present in one finding -- never the 60% partial overlap feature_present()
    allows for a curated knowledge-base phrase (a 3-word variant must not be satisfied by 2 words)."""
    alias_lower = alias.lower()
    if _protected_qualifier(alias_lower) is not None:
        return feature_present(alias, findings, scrub_negated_spans=scrub_negated_spans, strict=True)
    if _NON_LATIN_RE.search(alias_lower):
        # A CJK/Hangul (or mixed-script, e.g. "右腕 weakness") alias is matched as a LITERAL phrase only. Its
        # content words would otherwise collapse to the Latin remainder ("weakness"), letting a bare English
        # word satisfy a focal-weakness feature.
        return any(_non_latin_phrase_present(alias_lower, _strip_negated_spans(f.lower()) if scrub_negated_spans else f.lower())
                   for f in findings)
    internal = re.search(r"(?<=\w)\s+(?:without|with no|no)\b", alias_lower)
    if internal and scrub_negated_spans:
        # Round U follow-up: a paraphrase whose meaning CONTAINS a negation ("passed out without any warning") is
        # erased by negation scrubbing. Match it literally on the raw text, and require that the event before the
        # negation word ("passed out") itself survives scrubbing -- "I never passed out without warning" does not match.
        head = alias_lower[:internal.start()].strip()
        for finding in findings:
            raw = finding.lower()
            at = raw.find(alias_lower)
            if at >= 0 and _exact_phrase_present(alias_lower, raw) and _exact_phrase_present(head, _strip_negated_spans(raw)) \
                    and not re.search(r"\b(?:never|not|n't|no)\b\W*(?:\w+\W+){0,2}$", raw[:at]):
                return True
        return False
    alias_words = _content_words(alias_lower)
    # Generic symptom nouns (pain, ache...) are stripped from content words, so "pain after meals" would
    # otherwise reduce to {after, meal} and match any "after a meal" text. They must still be present.
    alias_generic = [w for w in re.findall(r"[a-z]+", alias_lower) if w in _GENERIC_MEDICAL_WORDS]
    for finding in findings:
        finding_lower = _strip_negated_spans(finding.lower()) if scrub_negated_spans else finding.lower()
        if _exact_phrase_present(alias_lower, finding_lower) or _non_latin_phrase_present(alias_lower, finding_lower):
            return True
        if alias_words and alias_words <= _content_words(finding_lower) and all(
                re.search(rf"\b{re.escape(w)}", finding_lower) for w in alias_generic):
            if not _evidence_v2() or _alias_words_close_together(alias_lower, alias_words, finding_lower):
                return True
    return False


def _evidence_v2() -> bool:
    from nova_agent.config import get_config
    return get_config().evidence_v2_enabled


_TOKEN = re.compile(r"[a-z0-9]+")
# Words that never break the adjacency of a paraphrase's words (unless they ARE one of its words):
#  - linking verbs joining a body part to its state ("chest GOT tight", "fingers WENT tingly", "head FEELS heavy");
#  - degree adverbs modifying that state ("neck is SO stiff", "chest felt REALLY tight");
#  - phrasal-verb particles and quantifiers ("coughed UP blood", "spit out SOME blood").
# Aspectual verbs ("keeps", "stays") are deliberately NOT included: "a warning light keeps flashing" describes an
# ongoing external event, not the symptom "flashing lights".
_ADJACENCY_TRANSPARENT = frozenset({
    "got", "get", "gets", "getting", "gotten", "went", "go", "goes", "going", "feel", "feels", "felt",
    "feeling", "became", "become", "becomes", "turned", "turn", "turns", "seem", "seems", "seemed",
    "is", "was", "are", "were", "be", "been", "being",
    "so", "very", "really", "too", "quite", "pretty", "extremely", "super", "rather", "bit", "little", "kind", "sort",
    "up", "out", "down", "off", "some", "any", "much", "lot", "lots", "bunch",
})


def _alias_words_close_together(alias_lower: str, alias_words: Set[str], finding_lower: str) -> bool:
    """A paraphrase is matched by its words only when they occur TOGETHER: inside one clause, with no unrelated
    CONTENT word between them (function words such as "in my" may intervene; for paraphrases of three or more
    content words, one extra content word is tolerated). Otherwise an idiom's words scattered over a sentence
    assert something else ("burning up" = fever was matched by "a burning feeling climbs up my chest"), while
    "burning in my chest" still matches "chest burning".

    Word positions are only meaningful for space-separated Latin-script text: an alias written in another script
    (Korean attaches particles to the noun, "머리가") keeps the previous subset-only behaviour."""
    if not alias_lower.isascii():
        return True
    limit = len(alias_words) + (0 if len(alias_words) <= 2 else 1)
    for clause in re.split(r"[;,.\n]", finding_lower):
        stems = []
        for t in _TOKEN.findall(clause):
            if t in _IGNORED:
                continue
            st = _stem(_LAY_ANATOMY.get(t, t))
            if t in _ADJACENCY_TRANSPARENT and st not in alias_words:
                continue
            stems.append(st)
        positions = {w: [i for i, st in enumerate(stems) if st == w] for w in alias_words}
        if any(not p for p in positions.values()):
            continue
        for start in sorted({i for p in positions.values() for i in p}):
            ends = [min((i for i in p if i >= start), default=None) for p in positions.values()]
            if None not in ends and max(ends) - start + 1 <= limit:
                return True
    return False


def _merge_lay_aliases() -> None:
    """Merge nova_agent.lay_language.LAY_FEATURE_ALIASES into FEATURE_ALIASES (each variant stays
    scoped to its one knowledge-base phrase)."""
    from .lay_language import LAY_FEATURE_ALIASES

    for phrase, variants in LAY_FEATURE_ALIASES.items():
        bucket = FEATURE_ALIASES.setdefault(phrase.lower(), [])
        for variant in variants:
            if variant not in bucket:
                bucket.append(variant)
                _LAY_VARIANTS.add((phrase.lower(), variant))


def _merge_pr15_aliases() -> None:
    """Merge the filtered PR #15 feature-local aliases (see nova_agent/pr15_feature_aliases.py)."""
    from .pr15_feature_aliases import PR15_FEATURE_ALIASES

    for phrase, variants in PR15_FEATURE_ALIASES.items():
        bucket = FEATURE_ALIASES.setdefault(phrase.lower(), [])
        for variant in variants:
            if variant not in bucket:
                bucket.append(variant)


_merge_lay_aliases()
_merge_pr15_aliases()


# A drug the patient stopped, ran out of, skipped or is no longer taking is not CURRENT use: "ran out of insulin
# three days ago" must not satisfy "insulin use" / "known diabetes on insulin" (it is the opposite -- an omission).
# Applied only to medication-USE features, so omission features ("missed insulin doses", "missed meal") and every
# symptom/exam feature are untouched.
_USE_FEATURE = re.compile(r"\b(?:use|user|on|takes?|taking)\b")
_DISCONTINUED_SPAN = re.compile(
    r"\b(?:ran|run|running) out of\b[^;,.\n]*"
    r"|\b(?:stopped(?: taking)?|quit(?: taking)?|discontinued|no longer (?:takes?|taking|on|uses?|using)|not taking|"
    r"(?:have|has)n'?t (?:been )?taking|missed|skipped|forgot(?: to take)?)\s+(?:all |any |my |the |his |her |their )?"
    r"(?:doses? of |shots? of )?[a-z][\w\-]*(?:\s+(?!for\b|since\b|in\b|and\b|but\b)[a-z][\w\-]*)?",
    re.IGNORECASE)


def _without_discontinued(findings: List[str]) -> List[str]:
    return [_DISCONTINUED_SPAN.sub(" ", f) for f in findings]


def feature_present_with_aliases(phrase: str, findings: List[str], scrub_negated_spans: bool = True,
                                 strict: bool = False, ignore_words: frozenset = frozenset()) -> bool:
    if scrub_negated_spans and not phrase.lower().startswith("family history"):
        from nova_agent.evidence_scope import patient_evidence_text
        findings = [patient_evidence_text(t) for t in findings]
    if re.search(r"\bsyncope\b|loss of consciousness", phrase.lower()):
        # The event did not happen in presyncope. Remove only the near-event span;
        # an actual faint described elsewhere in the same finding still counts.
        findings = [re.sub(r"\b(?:nearly|almost)\s+(?:fainted|passed out|lost consciousness)|\bnear[ -](?:fainting|syncope)\b",
                           "lightheadedness", f, flags=re.I) for f in findings]
    if _USE_FEATURE.search(phrase.lower()) and any(_DISCONTINUED_SPAN.search(f) for f in findings):
        findings = _without_discontinued(findings)
    return _scoped("with_aliases", (phrase, tuple(findings), scrub_negated_spans, strict, frozenset(ignore_words)),
                   lambda: _feature_present_with_aliases(phrase, findings, scrub_negated_spans, strict, ignore_words))


def _feature_present_with_aliases(phrase: str, findings: List[str], scrub_negated_spans: bool,
                                  strict: bool, ignore_words: frozenset) -> bool:
    """feature_present() on `phrase` itself, OR on any of its feature-local aliases (see
    FEATURE_ALIASES above) -- the alias never widens matching for any OTHER knowledge-base phrase.
    The single shared entry point for alias-aware matching; both differential.py's scoring and
    candidate_generator.py's pool-membership checks call this rather than plain feature_present()
    directly, so a diagnosis reachable only through an aliased phrase behaves identically at both
    stages."""
    from nova_agent.feature_relations import RELATION_PATTERNS
    if phrase.lower() in RELATION_PATTERNS:
        return feature_present(phrase, findings, scrub_negated_spans=scrub_negated_spans, strict=strict, ignore_words=ignore_words)
    if feature_present(phrase, findings, scrub_negated_spans=scrub_negated_spans, strict=strict, ignore_words=ignore_words):
        return True
    for alias in FEATURE_ALIASES.get(phrase.lower(), ()):
        # Every alias is a PARAPHRASE of its phrase, so it is matched strictly (never by the 60%
        # partial overlap used for curated phrases): "elevated blood pressure" used to be satisfied
        # by "elevated white blood cell count" (2 of 3 words), crediting hypertension from a CBC.
        if _strict_alias_present(alias, findings, scrub_negated_spans):
            return True
    return False
