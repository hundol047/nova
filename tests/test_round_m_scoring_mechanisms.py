"""Round M scoring/matching mechanisms found by tracing fresh development cases (general invariants,
independent of any case set)."""

from __future__ import annotations

import pytest

from nova_agent.differential import (
    _TYPICAL_FEATURE_CONTRIBUTION_CAP, CONFIRMATORY_WEIGHT, _score_disease, _soft_saturate)
from nova_agent.matching import content_words, feature_present, feature_present_with_aliases
from nova_agent.state import PatientState


def test_soft_saturation_is_monotone_bounded_and_identity_below_the_knee():
    xs = [0.0, 0.5, 1.0, 2.0, 2.5, 3.0, 4.5, 6.0, 12.0]
    ys = [_soft_saturate(x) for x in xs]
    assert ys[:4] == xs[:4]
    assert all(b > a for a, b in zip(ys, ys[1:])), "more evidence must always rank at least slightly higher"
    assert max(ys) <= _TYPICAL_FEATURE_CONTRIBUTION_CAP <= CONFIRMATORY_WEIGHT


def _entry(name, features):
    return {"id": name, "name": name, "typical_features": features, "risk_factors": [], "confirmatory_findings": []}


def test_six_matched_features_outrank_two_matched_features_instead_of_tying():
    state = PatientState(case_id="sat", chief_complaint="presenting")
    state.symptoms = ["colicky belly cramps", "repeated vomiting", "swollen belly", "no gas passed", "constipation", "dehydration"]
    many = _entry("many", ["colicky belly cramps", "repeated vomiting", "swollen belly", "no gas passed", "constipation", "dehydration"])
    few = _entry("few", ["repeated vomiting", "swollen belly"])
    assert _score_disease(many, state)[0] > _score_disease(few, state)[0]


@pytest.mark.parametrize("feature,finding", [
    ("testicular pain", "pain in one testicle"),
    ("scrotal swelling", "swelling of the scrotum"),
    ("pelvic pain", "pain deep in the pelvis"),
    ("ureteral stone", "a stone in the ureter"),
])
def test_anatomical_adjective_and_noun_forms_match(feature, finding):
    assert feature_present(feature, [finding])


def test_anatomical_normalization_does_not_merge_unrelated_words():
    assert content_words("thoracic") != content_words("abdominal")
    assert not feature_present("testicular pain", ["pain in one knee"])


def test_alias_is_not_satisfied_by_partial_word_overlap():
    # "elevated blood pressure" (alias of hypertension) must not be credited by "elevated white blood cell count"
    assert not feature_present_with_aliases("hypertension", ["elevated white blood cell count"])
    assert feature_present_with_aliases("hypertension", ["her blood pressure is elevated and high blood pressure runs in the family"])


@pytest.mark.parametrize("feature,finding", [
    ("burning upper abdominal pain", "burning upper belly pain at night"),
    ("diffuse crampy abdominal pain", "crampy tummy pain all over"),
])
def test_everyday_region_words_match_the_clinical_adjective(feature, finding):
    assert feature_present(feature, [finding])


def test_ambiguous_region_word_stomach_is_not_equated_with_abdominal():
    assert content_words("stomach") != content_words("abdominal")


@pytest.mark.parametrize("feature,finding", [
    ("unilateral calf swelling", "one calf is swollen"),
    ("swollen tender joint", "the joint swelling is tender"),
    ("warmth and redness of leg", "the leg is warm and red"),
])
def test_swelling_family_and_warmth_forms_agree(feature, finding):
    assert feature_present(feature, [finding])


@pytest.mark.parametrize("feature,finding", [
    ("low blood pressure", "history of high blood pressure"),
    ("elevated potassium", "potassium is low"),
    ("rapid heart rate", "heart rate is slow"),
])
def test_opposite_direction_finding_never_satisfies_a_directional_feature(feature, finding):
    assert not feature_present(feature, [finding])


@pytest.mark.parametrize("feature,finding", [
    ("low blood pressure", "blood pressure is low"),
    ("elevated potassium", "potassium level elevated"),
    ("rapid heart rate", "heart rate is fast"),
    ("high blood pressure", "her blood pressure runs high"),
])
def test_same_direction_still_matches(feature, finding):
    assert feature_present(feature, [finding])


def test_one_lab_result_is_credited_once_even_when_the_entry_names_it_twice():
    state = PatientState(case_id="dedupe", chief_complaint="presenting")
    state.laboratory_tests["troponin"] = "troponin elevated"
    twice = {"id": "t", "name": "t", "typical_features": [], "risk_factors": [],
             "confirmatory_findings": ["elevated troponin", "troponin elevated"]}
    once = dict(twice, confirmatory_findings=["elevated troponin"])
    assert _score_disease(twice, state)[0] == _score_disease(once, state)[0] == CONFIRMATORY_WEIGHT


def test_nonspecific_inflammatory_lab_is_credited_at_feature_weight_not_confirmatory_weight():
    from nova_agent.differential import FEATURE_WEIGHT
    state = PatientState(case_id="wbc", chief_complaint="presenting")
    state.laboratory_tests["cbc"] = "elevated white blood cell count"
    wbc = {"id": "w", "name": "w", "typical_features": [], "risk_factors": [],
           "confirmatory_findings": ["elevated white blood cell count"]}
    score = _score_disease(wbc, state)[0]
    assert score == FEATURE_WEIGHT < CONFIRMATORY_WEIGHT


def test_specific_lab_keeps_full_confirmatory_weight():
    state = PatientState(case_id="trop", chief_complaint="presenting")
    state.laboratory_tests["troponin"] = "troponin elevated"
    entry = {"id": "t", "name": "t", "typical_features": [], "risk_factors": [], "confirmatory_findings": ["elevated troponin"]}
    assert _score_disease(entry, state)[0] == CONFIRMATORY_WEIGHT


def test_alias_that_names_a_generic_symptom_noun_still_requires_it():
    # "pain after meals" must not be satisfied by an onset note that merely says "after a shared meal"
    assert not feature_present_with_aliases("pain after eating", ["after a shared meal"])
    assert feature_present_with_aliases("pain after eating", ["belly pain starts after meals"])
