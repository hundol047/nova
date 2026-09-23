"""Tests for multi-concept clinical presentation extraction (nova_agent/clinical_presentation.py).
Every phrasing is written fresh for this test file, not copied from any evaluation case file."""

from __future__ import annotations

from nova_agent.clinical_presentation import extract_presentation


def test_extracts_multiple_concurrent_concepts_stroke_presentation():
    p = extract_presentation("suddenly couldn't find her words and her right arm won't work")
    assert "aphasia" in p.symptoms
    assert "focal_weakness" in p.symptoms
    assert p.onset == "sudden"
    assert "head/neuro" in p.body_regions and "extremity" in p.body_regions


def test_extracts_multiple_concurrent_concepts_cardiopulmonary():
    p = extract_presentation("severe chest pain and shortness of breath for the past 2 hours")
    assert "chest_pain" in p.symptoms
    assert "dyspnea" in p.symptoms
    assert "severe" in p.severity_features
    assert p.duration_hint == "2 hours"


def test_single_concept_text_still_extracts_one_symptom():
    p = extract_presentation("I have a headache that won't go away")
    assert p.symptoms == ["headache"]


def test_unrelated_text_extracts_no_symptoms():
    p = extract_presentation("I have a splinter stuck in my finger")
    assert p.symptoms == []


def test_risk_factors_and_medications_passed_through():
    p = extract_presentation(
        "burning when I pee", past_medical_history=["diabetes"], medications=["metformin"],
        demographics={"age": 55, "sex": "female"},
    )
    assert p.risk_factors == ["diabetes"]
    assert p.medication_context == ["metformin"]
    assert p.demographic_context == {"age": 55, "sex": "female"}


def test_gradual_onset_detected():
    p = extract_presentation("this headache has come on gradually over the past few days")
    assert p.onset == "gradual"


def test_confidence_scores_present_for_matched_concepts():
    p = extract_presentation("I have abdominal pain and vomiting")
    assert "abdominal_pain" in p.confidence
    assert "vomiting" in p.confidence
    assert p.confidence["abdominal_pain"] > 0
