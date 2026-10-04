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

import re
from typing import List, Set

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
_NEGATED_SPAN_PATTERN = re.compile(
    r"\b(?:no|not|denies|denied|without|absent|negative for)\s+(?:[a-z]+\s*){1,4}", re.IGNORECASE,
)


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


def _content_words(text: str) -> Set[str]:
    # A patient's hyphenation must not split one clinical word into two fragments
    # ("light-headed" == "lightheaded").
    words = re.split(r"[^a-z0-9가-힣]+", _JOINABLE_HYPHEN.sub(r"\1\2", text.lower()))
    return {_stem(w) for w in words if w and w not in _IGNORED}


def content_word_count(text: str) -> int:
    """Public wrapper around `_content_words()` -- differential.py uses this to weight a matched
    knowledge-base phrase by its own specificity (see `_specificity_multiplier()` there)."""
    return len(_content_words(text))


def content_words(text: str) -> Set[str]:
    """Public wrapper around `_content_words()` -- differential.py uses the actual word SET (not
    just the count) to check whether a phrase reduces to nothing but generic physiologic-severity
    markers (see `_specificity_multiplier()` there, Round E's defect C)."""
    return _content_words(text)


def _strip_negated_spans(text: str) -> str:
    return _NEGATED_SPAN_PATTERN.sub(" ", text)


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
    return re.search(rf"\b{re.escape(feature_lower)}\b", finding_lower) is not None


def feature_present(feature: str, findings_text: List[str], scrub_negated_spans: bool = False) -> bool:
    """`scrub_negated_spans=True` is for checking against a general finding bag (e.g.
    state.all_findings_text()) that can contain an EXAM/TEST result embedding an unrelated
    negation in the same string. Leave it False (the default) when checking against
    PatientState.pertinent_negatives -- those entries ARE the negative statement itself (e.g.
    "denies chest pain"), so scrubbing them would erase the very text being matched against."""
    feature_content = _content_words(feature)
    feature_lower = feature.lower()
    distinguishing = _distinguishing_tokens(feature_content)
    for finding in findings_text:
        finding_lower = _strip_negated_spans(finding.lower()) if scrub_negated_spans else finding.lower()
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
        if _exact_phrase_present(feature_lower, finding_lower):
            return True
        if not feature_content:
            continue
        finding_content = _content_words(finding_lower)
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
        if len(feature_content) <= 2:
            if overlap == feature_content:
                return True
        elif len(overlap) / len(feature_content) >= _OVERLAP_RATIO_THRESHOLD:
            return True
    return False


def feature_denied(feature: str, negatives: List[str]) -> bool:
    return feature_present(feature, negatives)


def explicitly_denied_in_findings(feature: str, findings: List[str]) -> bool:
    """Match only locally negated spans, never infer a denial from shared content words.

    General findings contain positive AND negative statements; unlike pertinent_negatives,
    they cannot be passed wholesale to feature_denied(). Clause boundaries remain bounded by
    the existing negation parser. This is an English-text helper, not a full language model.
    """
    spans = [m.group(0) for finding in findings for m in _NEGATED_SPAN_PATTERN.finditer(finding)]
    return feature_present(feature, spans)


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
    """Lay-language variants are matched STRICTLY: the literal phrase on a word boundary, or EVERY
    one of its content words present in one finding -- never the 60% partial overlap feature_present()
    allows for a curated knowledge-base phrase (a 3-word variant must not be satisfied by 2 words)."""
    alias_lower = alias.lower()
    alias_words = _content_words(alias_lower)
    for finding in findings:
        finding_lower = _strip_negated_spans(finding.lower()) if scrub_negated_spans else finding.lower()
        if _exact_phrase_present(alias_lower, finding_lower):
            return True
        if alias_words and alias_words <= _content_words(finding_lower):
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


_merge_lay_aliases()


def feature_present_with_aliases(phrase: str, findings: List[str], scrub_negated_spans: bool = True) -> bool:
    """feature_present() on `phrase` itself, OR on any of its feature-local aliases (see
    FEATURE_ALIASES above) -- the alias never widens matching for any OTHER knowledge-base phrase.
    The single shared entry point for alias-aware matching; both differential.py's scoring and
    candidate_generator.py's pool-membership checks call this rather than plain feature_present()
    directly, so a diagnosis reachable only through an aliased phrase behaves identically at both
    stages."""
    if feature_present(phrase, findings, scrub_negated_spans=scrub_negated_spans):
        return True
    for alias in FEATURE_ALIASES.get(phrase.lower(), ()):
        if (phrase.lower(), alias) in _LAY_VARIANTS:
            if _strict_alias_present(alias, findings, scrub_negated_spans):
                return True
        elif feature_present(alias, findings, scrub_negated_spans=scrub_negated_spans):
            return True
    return False
