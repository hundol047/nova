"""Multilingual clinical concept routing (spec: Korean/English/Japanese/Chinese input must
normalize to the SAME language-neutral clinical concept tags). Covers the minimum category set the
spec names for each language -- chest pain, dyspnea, stroke symptoms, GI bleed, syncope, fever,
allergy/anaphylaxis, abdominal pain -- plus a cross-language equivalence check confirming the same
clinical meaning in all four languages routes to the same concept tag. Phrasings here are fresh,
generic lay language, never copied from any evaluation/blind case file.
"""

from __future__ import annotations

import pytest

from nova_agent.chief_complaint import classify

# {category -> {locale -> phrase}}. Not every category needs a phrase in every locale (JA/ZH still
# cover the full category set given the concept-alias tables just added; KO covers every category
# too since the previously-thin concepts were filled in).
CASES = {
    "chest_pain": {
        "ko": "가슴이 아파요", "en": "my chest hurts", "ja": "胸が痛いです", "zh": "我胸口疼",
    },
    "dyspnea": {
        "ko": "숨이 차요", "en": "I can't catch my breath", "ja": "息が苦しいです", "zh": "我呼吸困难",
    },
    "focal_weakness": {
        "ko": "한쪽 팔에 힘이 없어요", "en": "my arm won't work on one side",
        "ja": "片側に力が入らないです", "zh": "我一侧手臂没力气",
    },
    "aphasia": {
        "ko": "말이 어눌해요", "en": "I can't get my words out",
        "ja": "うまく話せません", "zh": "我说话困难",
    },
    "gi_bleeding": {
        "ko": "혈변이 나와요", "en": "I have blood in my stool",
        "ja": "血便が出ます", "zh": "我有便血",
    },
    "syncope": {
        "ko": "기절했어요", "en": "I passed out", "ja": "失神しました", "zh": "我晕厥了",
    },
    "fever": {
        "ko": "열이 나요", "en": "I have a fever", "ja": "発熱があります", "zh": "我发热",
    },
    "allergic": {
        "ko": "두드러기가 났어요", "en": "I broke out in hives",
        "ja": "じんましんが出ました", "zh": "我起荨麻疹了",
    },
    "abdominal_pain": {
        "ko": "배가 아파요", "en": "my stomach hurts", "ja": "お腹が痛いです", "zh": "我肚子疼",
    },
}


@pytest.mark.parametrize("category,locale", [
    (category, locale) for category, by_locale in CASES.items() for locale in by_locale
])
def test_multilingual_phrase_routes_to_expected_concept(category, locale):
    phrase = CASES[category][locale]
    assert classify(phrase) == category, f"[{locale}] {phrase!r} should route to {category}"


@pytest.mark.parametrize("category", list(CASES))
def test_cross_language_equivalence_same_meaning_same_tag(category):
    """The SAME clinical meaning in all four languages must produce the SAME concept tag -- only
    the surface language differs, never the internal routing (spec: internal canonical IDs must
    never vary per locale)."""
    tags = {locale: classify(phrase) for locale, phrase in CASES[category].items()}
    assert len(set(tags.values())) == 1, f"{category}: inconsistent routing across locales: {tags}"
    assert list(set(tags.values()))[0] == category


def test_mixed_korean_english_input_still_routes_correctly():
    """A real mixed-language presentation (spec: e.g. Korean carrier text with an embedded English
    clinical term) must still route on whichever language's phrase is present."""
    assert classify("환자가 dyspnea 있고 숨쉬기 힘들어해요") == "dyspnea"
    assert classify("SpO2 88%인데 가슴이 아파요") == "chest_pain"


def test_mixed_japanese_english_input_still_routes_correctly():
    assert classify("患者は chest pain を訴えています") == "chest_pain"


def test_mixed_chinese_english_input_still_routes_correctly():
    assert classify("患者主诉 dyspnea 和呼吸困难") == "dyspnea"
