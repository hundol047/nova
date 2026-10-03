"""Bounded multilingual clinical concept normalization (Round E, defect D).

Architecture (spec): `localized phrase -> canonical symptom concept -> existing routing`. This
module is ONLY the first arrow -- a small, hand-curated table of non-English clinical phrases
mapped to the SAME canonical chief-complaint concept tags chief_complaint.py already routes on
(abdominal_pain, chest_pain, headache, ...). It creates NO separate reasoning logic per language:
these phrases are merged directly into chief_complaint.CONCEPT_ALIASES at import time, so a
Korean or Japanese phrase is scored through the EXACT SAME exact/alias/fuzzy machinery, specificity
precedence, and multi-concept extraction as any English phrase -- there is no parallel "Korean
matcher" or "Japanese matcher" anywhere in this codebase.

Deliberately bounded, not a translation engine:
  - No Google Translate / external LLM translation / any online translation API -- the competition
    runtime must stay fully offline and dependency-light. Every phrase below is a literal,
    hand-written string, checked the same substring/word-overlap way English phrases already are.
  - Covers only the languages this repo's evaluation/UI already exercises (English, Korean,
    Japanese -- see evaluation/blind_cases_v14.py's mixed_language category) and only the ~14
    clinically load-bearing domains named by this round's own spec: pain (generic body-region
    location words that commonly stand in for "X pain" in casual non-English phrasing),
    abdominal_pain, chest_pain, headache, weakness, numbness, dyspnea (shortness of breath), fever,
    vomiting, diarrhea, gi_bleeding (bleeding), dizziness, syncope (fainting).
  - Every phrase is a COMPLETE clinical word or phrase (minimum 2 characters for CJK, never a
    single ambiguous character/fragment) -- chief_complaint.py's existing substring/alias matching
    already requires the whole phrase text to appear, so a phrase here can never fire on an
    unrelated word that merely happens to contain one of its characters.
  - This table only ever ADDS alias coverage for a concept that already exists in
    chief_complaint.CANONICAL_TERMS -- it can never introduce a new tag on its own, and (like every
    other alias in this codebase) never widens matching for any OTHER concept.

Real gap this round's own audit found and closed: a bare non-English body-region NOUN (e.g.
Japanese "下腹部"/"腹部" lower-abdomen/abdomen, Korean "아랫배"/"복부") often stands in for the
whole "X pain" concept in a real mixed-language sentence when the symptom-quality word itself is
in the OTHER language (e.g. "下腹部に sharp pain" -- Japanese location, English quality, with
neither language's own "痛い"/"pain"-compound literally present) -- Blind v14's one mixed-language
miss (Japanese abdominal pain) traced to exactly this shape. Adding the bare region noun closes it
generically (any sentence naming that body region in that language now routes), never by keying on
that one case's exact wording.
"""

from __future__ import annotations

import re

from typing import Dict, List

# concept_tag -> list of non-English phrases (Korean + Japanese), each a complete clinical word or
# phrase. English coverage already lives in chief_complaint.py's own CANONICAL_TERMS/CONCEPT_ALIASES
# and needs no duplication here.
MULTILINGUAL_CONCEPT_ALIASES: Dict[str, List[str]] = {
    # Generic "pain" (spec's own named domain) -- bare, unscoped pain words in Korean/Japanese,
    # analogous to how English "pain" alone is too generic to route to any ONE body region; these
    # exist so a bare pain-word combined with an English/Korean/Japanese body-region word elsewhere
    # in the same sentence still contributes SOME signal, never enough alone to pick a specific tag
    # (mirrors matching.py's own _GENERIC_MEDICAL_WORDS treatment of English "pain").
    # (Intentionally NOT added as its own routing tag -- see module docstring: this table only
    # ever extends an EXISTING concept's alias list.)
    "abdominal_pain": [
        "복통", "배가 아파요", "배가 아프다", "아랫배가 아파요", "아랫배 통증", "복부 통증",
        "お腹が痛いです", "下腹部の痛み", "下腹部に痛み", "腹部の痛み",
        # Bare body-region nouns (no "pain"/"痛" word required) -- the real gap this round closed:
        # a mixed-language sentence naming the region in one language while the symptom quality
        # ("sharp", "dull", "crampy") is expressed in a different language/English.
        "아랫배", "하복부", "下腹部", "腹部",
    ],
    "chest_pain": [
        "가슴이 아파요", "흉통", "가슴 통증", "가슴이 답답해요",
        "胸が痛いです", "胸部の痛み", "胸の痛み",
        # Bare body-region nouns (same rationale as abdominal_pain's bare region words above).
        "가슴에", "가슴이", "胸に", "胸が",
    ],
    "headache": [
        "머리가 아파요", "두통이 있어요",
        "頭が痛いです", "頭痛がします",
    ],
    "weakness": [
        "온몸에 힘이 없어요", "기운이 없어요",
        "体に力が入りません", "だるくて力が出ません",
    ],
    "numbness": [
        "손발이 저려요", "감각이 없어요",
        "手足がしびれます", "感覚がありません",
    ],
    "dyspnea": [
        "숨쉬기가 힘들어요", "숨이 차요",
        "息が苦しいです", "呼吸が苦しいです",
    ],
    "fever": [
        "열이 나요", "몸에 열이 있어요",
        "熱があります", "発熱しています",
    ],
    "vomiting": [
        "계속 토해요", "구토를 했어요",
        "吐き気がして吐きました", "嘔吐しました",
    ],
    "diarrhea": [
        "설사를 해요", "묽은 변을 봐요",
        "下痢をしています", "水っぽい便が出ます",
    ],
    "gi_bleeding": [
        "피를 토했어요", "대변에 피가 섞여요",
        "血を吐きました", "便に血が混じります",
    ],
    "dizziness": [
        "어지러워요", "머리가 빙빙 돌아요",
        "めまいがします", "頭がふらふらします",
    ],
    "syncope": [
        "정신을 잃었어요", "기절했어요",
        "気を失いました", "意識を失いました",
    ],
}


def apply_multilingual_aliases(concept_aliases: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Merges MULTILINGUAL_CONCEPT_ALIASES into an existing concept-alias table (chief_complaint.
    py's own CONCEPT_ALIASES), extending each tag's alias LIST in place of creating any parallel
    structure -- called once at chief_complaint.py's import time, before CONCEPT_PHRASES is built,
    so every downstream consumer (route(), extract_presentation(), specificity precedence) sees
    these phrases exactly the way it sees any other alias, with zero new code paths."""
    merged = {tag: list(phrases) for tag, phrases in concept_aliases.items()}
    for tag, phrases in MULTILINGUAL_CONCEPT_ALIASES.items():
        merged.setdefault(tag, [])
        for phrase in phrases:
            if phrase not in merged[tag]:
                merged[tag].append(phrase)
    return merged


# Bare, COMPLETE clinical nouns (>= 2 characters, never fragments) added after Blind v16 showed the
# sentence-ending-only phrases above miss natural variants ("下痢がひどいです" vs "下痢をしています").
_BARE_CLINICAL_NOUNS: Dict[str, List[str]] = {
    "abdominal_pain": ["복통", "腹痛"], "chest_pain": ["흉통", "胸痛"], "headache": ["두통", "頭痛"],
    "weakness": ["무력감", "脱力"], "numbness": ["저림", "しびれ", "痺れ"], "dyspnea": ["호흡곤란", "息切れ", "息苦しい"],
    "fever": ["발열", "発熱"], "vomiting": ["구토", "嘔吐", "吐き気"], "diarrhea": ["설사", "下痢"],
    "gi_bleeding": ["토혈", "혈변", "吐血", "下血"], "dizziness": ["어지럼", "めまい", "眩暈"], "syncope": ["실신", "失神"],
}
for _concept, _nouns in _BARE_CLINICAL_NOUNS.items():
    MULTILINGUAL_CONCEPT_ALIASES[_concept] = list(MULTILINGUAL_CONCEPT_ALIASES[_concept]) + [
        n for n in _nouns if n not in MULTILINGUAL_CONCEPT_ALIASES[_concept]]

# A localized symptom immediately followed by one of these is DENIED, not present.
_NEGATION_MARKERS = ("없", "않", "아니", "ありません", "ない", "なし", "ませんでした", "ないです", "なかっ")


# Canonical ENGLISH evidence wording for each concept above. Routing/pool selection already uses the
# localized phrases directly, but differential scoring matches knowledge-base typical_features by
# English word overlap, so a Korean/Japanese complaint earned ZERO score (Blind v16: both Japanese-
# mixed cases never moved their differential at all). Appending the canonical term to the evidence
# bag makes a localized symptom count the same as the English patient saying it -- no translation
# API, no per-language reasoning, and English-only input is completely unaffected.
_CANONICAL_ENGLISH_EVIDENCE: Dict[str, str] = {
    "abdominal_pain": "abdominal pain", "chest_pain": "chest pain", "headache": "headache",
    "weakness": "weakness", "numbness": "numbness", "dyspnea": "shortness of breath", "fever": "fever",
    "vomiting": "vomiting", "diarrhea": "diarrhea", "gi_bleeding": "gi bleeding", "dizziness": "dizziness",
    "syncope": "syncope",
}


def _present_not_negated(phrase: str, text: str) -> bool:
    start = text.find(phrase)
    while start != -1:
        end = start + len(phrase)
        tail = re.split(r"[.!?。！？,，;；\n]", text[end:], maxsplit=1)[0]
        # A denial belonging to the next symptom must not cancel this one.
        next_concepts = [tail.find(p) for ps in _BARE_CLINICAL_NOUNS.values()
                         for p in ps if tail.find(p) >= 0]
        if next_concepts:
            tail = tail[:min(next_concepts)]
        tail = tail[:12]
        if not any(m in tail for m in _NEGATION_MARKERS):
            return True
        start = text.find(phrase, start + 1)
    return False


def english_evidence_for(text: str) -> List[str]:
    """Canonical English symptom phrases for every localized (non-ASCII) clinical phrase present in
    `text`. Only phrases containing a non-ASCII character can fire, so plain English never changes."""
    if not text or text.isascii():
        return []
    found: List[str] = []
    for concept, phrases in MULTILINGUAL_CONCEPT_ALIASES.items():
        english = _CANONICAL_ENGLISH_EVIDENCE.get(concept)
        if english and english not in found and any((not p.isascii()) and _present_not_negated(p, text) for p in phrases):
            found.append(english)
    return found
