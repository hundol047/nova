"""Round M: evidence-extraction mechanisms found by tracing fresh development cases.

Each test asserts a GENERAL wording/normalization invariant (independent of every case set): magnitude
phrasing for qualitative-only labs, hyphenation, feature-scoped lay-language variants, and the
localized-symptom -> English evidence bridge for follow-up findings."""

from __future__ import annotations

import pytest

from nova_agent.lay_language import LAY_FEATURE_ALIASES
from nova_agent.matching import FEATURE_ALIASES, content_words, feature_present_with_aliases
from nova_agent.multilingual_concepts import english_evidence_for
from nova_agent.objective_evidence import normalize_objective_evidence
from nova_agent.state import PatientState


def _lab(key: str, text: str):
    state = PatientState(case_id=f"rm_{key}", chief_complaint="generic presentation")
    state.laboratory_tests[key] = text
    return normalize_objective_evidence(state)


@pytest.mark.parametrize("text", [
    "lipase more than three times normal", "lipase 4x the upper limit", "lipase is markedly raised",
    "lipase increased",
])
def test_magnitude_wording_for_a_high_only_lab_reads_as_high(text):
    assert _lab("lipase", text)["lab.lipase"].interpretation == "high"


@pytest.mark.parametrize("text", [
    "lipase not raised", "lipase was normal", "lipase is not increased", "no increase, lipase within normal",
])
def test_negated_or_normal_magnitude_wording_is_never_high(text):
    assert _lab("lipase", text)["lab.lipase"].interpretation != "high"


def test_pregnancy_test_positive_wording_reads_as_high_hcg():
    assert _lab("beta_hcg", "the pregnancy test is positive")["lab.beta_hcg"].interpretation == "high"


def test_hyphenated_and_joined_forms_are_the_same_words():
    assert content_words("light-headed") == content_words("lightheaded")


def test_lay_aliases_are_merged_and_stay_scoped_to_their_own_phrase():
    assert LAY_FEATURE_ALIASES
    for phrase, variants in LAY_FEATURE_ALIASES.items():
        for variant in variants:
            assert variant in FEATURE_ALIASES[phrase.lower()]
    # an alias for one phrase must not be an alias of a different, unrelated phrase
    owners = {}
    for phrase, variants in LAY_FEATURE_ALIASES.items():
        for variant in variants:
            owners.setdefault(variant, set()).add(phrase)
    # variants may be shared deliberately (e.g. fever lists) but never by dozens of phrases
    assert max(len(v) for v in owners.values()) <= 6


def test_lay_variant_matches_only_through_its_feature():
    phrase = next(iter(LAY_FEATURE_ALIASES))
    variant = LAY_FEATURE_ALIASES[phrase][0]
    assert feature_present_with_aliases(phrase, [f"patient says {variant}"])
    assert not feature_present_with_aliases("zzz unrelated clinical phrase", [f"patient says {variant}"])


def test_negated_lay_variant_is_not_evidence():
    phrase = next(iter(LAY_FEATURE_ALIASES))
    variant = LAY_FEATURE_ALIASES[phrase][0]
    assert not feature_present_with_aliases(phrase, [f"no {variant}"])


@pytest.mark.parametrize("text,expected", [
    ("소변을 볼 때 아프고 메스꺼워요", {"nausea", "dysuria painful urination"}),
    ("排尿時に痛みがあり悪寒もあります", {"dysuria painful urination", "chills"}),
    ("옆구리가 아프고 혈뇨가 있어요", {"flank pain", "hematuria blood in urine"}),
])
def test_localized_followup_findings_become_english_evidence(text, expected):
    assert expected <= set(english_evidence_for(text))


@pytest.mark.parametrize("text", ["吐き気はありません", "오한은 없어요", "血尿はなかったです"])
def test_negated_localized_followup_finding_is_not_evidence(text):
    assert english_evidence_for(text) == []
