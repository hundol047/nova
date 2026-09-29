"""Round E, defect D: nova_agent/multilingual_concepts.py's bounded Korean/Japanese clinical
concept table, tested directly at the mapping/merge layer (never asserting a translation model --
this module has none). Fresh phrasing, independently authored, distinct from Blind v14's own
mixed-language cases.
"""

from __future__ import annotations

import pytest

from nova_agent.chief_complaint import CONCEPT_ALIASES, route
from nova_agent.multilingual_concepts import MULTILINGUAL_CONCEPT_ALIASES, apply_multilingual_aliases


def test_multilingual_table_is_merged_into_chief_complaint_concept_aliases():
    for tag, phrases in MULTILINGUAL_CONCEPT_ALIASES.items():
        for phrase in phrases:
            assert phrase in CONCEPT_ALIASES.get(tag, []), (
                f"{phrase!r} (concept {tag!r}) was not merged into chief_complaint.CONCEPT_ALIASES"
            )


def test_apply_multilingual_aliases_never_mutates_the_original_table():
    original = {"headache": ["throbbing headache"]}
    merged = apply_multilingual_aliases(original)
    assert original == {"headache": ["throbbing headache"]}
    assert merged is not original
    assert len(merged["headache"]) > len(original["headache"])


def test_apply_multilingual_aliases_never_introduces_a_brand_new_concept_tag():
    # This table only ever EXTENDS an existing concept's alias list -- it can never introduce a
    # tag that chief_complaint.CANONICAL_TERMS doesn't already define.
    from nova_agent.chief_complaint import CANONICAL_TERMS

    for tag in MULTILINGUAL_CONCEPT_ALIASES:
        assert tag in CANONICAL_TERMS, f"{tag!r} is not an existing chief_complaint.py concept tag"


def test_no_phrase_is_a_single_ambiguous_character_fragment():
    # "Complete clinical phrase/token matches" (spec) -- every phrase must be at least 2 characters,
    # never a lone character that could fire on an unrelated word merely containing it.
    for tag, phrases in MULTILINGUAL_CONCEPT_ALIASES.items():
        for phrase in phrases:
            assert len(phrase.strip()) >= 2, f"{phrase!r} under {tag!r} is too short/ambiguous"


KOREAN_ROUTING_CASES = [
    ("숨쉬기가 힘들어요, 가슴도 답답해요", "dyspnea"),
    ("어지러워요, 눕고 싶어요", "dizziness"),
    ("계속 토해요, 배도 아파요", "vomiting"),
    ("정신을 잃었어요, 잠깐 쓰러졌어요", "syncope"),
]

JAPANESE_ROUTING_CASES = [
    ("息が苦しいです、横になりたいです", "dyspnea"),
    ("めまいがします、立っていられません", "dizziness"),
    ("嘔吐しました、お腹も痛いです", "vomiting"),
    ("意識を失いました、少し倒れました", "syncope"),
]


@pytest.mark.parametrize("text,expected_tag", KOREAN_ROUTING_CASES)
def test_korean_only_phrase_routes_to_its_canonical_concept(text, expected_tag):
    result = route(text)
    assert result.primary_tag == expected_tag


@pytest.mark.parametrize("text,expected_tag", JAPANESE_ROUTING_CASES)
def test_japanese_only_phrase_routes_to_its_canonical_concept(text, expected_tag):
    result = route(text)
    assert result.primary_tag == expected_tag
