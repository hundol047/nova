"""Round F: localized (ko/ja) symptoms must reach differential SCORING as canonical English evidence,
not only routing. Fresh wording, independent of every blind/dev set; negation and plain-English guards."""

from __future__ import annotations

import pytest

from nova_agent.multilingual_concepts import english_evidence_for
from nova_agent.state import PatientState


@pytest.mark.parametrize("text,expected", [
    ("下痢がひどいです", {"diarrhea"}),
    ("昨日から嘔吐と発熱があります", {"vomiting", "fever"}),
    ("めまいがして立てません", {"dizziness"}),
    ("복통이 심해요", {"abdominal pain"}),
    ("두통과 구토가 있어요", {"headache", "vomiting"}),
])
def test_localized_symptom_becomes_canonical_english_evidence(text, expected):
    assert set(english_evidence_for(text)) == expected


@pytest.mark.parametrize("text", ["下痢はありません", "발열이 없어요", "嘔吐はなかったです。熱もなし", "ただ頭痛はない"])
def test_negated_localized_symptom_is_not_evidence(text):
    assert english_evidence_for(text) == []


def test_plain_english_and_empty_input_are_untouched():
    assert english_evidence_for("I have a bad headache and fever") == []
    assert english_evidence_for("") == []


def test_findings_bag_gets_the_english_evidence_only_for_localized_text():
    s = PatientState(case_id="c", chief_complaint="下痢がひどいです, since last night", demographics={"age": 30, "sex": "female"})
    assert "diarrhea" in s.all_findings_text()
    e = PatientState(case_id="d", chief_complaint="bad diarrhea since last night", demographics={"age": 30, "sex": "female"})
    assert e.all_findings_text() == ["bad diarrhea since last night"]
