"""Round Q regression tests for the technical review's reproduced defects (steps 2 and 3).

Sentences here are new minimal contrasts written for these mechanisms, not Round P vignettes. They are development
tests, not an evaluation.
"""
from types import SimpleNamespace

import pytest

from evaluation.cases import SyntheticCase
from nova_agent.differential import DifferentialEngine
from nova_agent.final_decision import UNDIFFERENTIATED_ID, decide_final, support_problems
from nova_agent.matching import feature_denied, feature_present, or_branches
from nova_agent.preliminary import explanation_text, question_is_faithful, same_scope_names
from nova_agent.state import PatientState, answer_kind


def _state(cc, age=60, sex="male", prelim=True):
    s = PatientState(case_id="q", chief_complaint=cc, demographics={"age": age, "sex": sex})
    s.preliminary_rules = prelim
    return s


def _item(state, did):
    return next((d for d in DifferentialEngine().update(state) if d.diagnosis_id == did), None)


# --- 2A: protected rhythm qualifier --------------------------------------------------------------------------

@pytest.mark.parametrize("finding,expected", [
    ("Pulse has an irregular rhythm with occasional pauses", False),
    ("irregular rhythm noted", False),
    ("pulse is irregularly irregular", True),
    ("irregularly irregular rhythm on auscultation", True),
    ("HR 92, irregularly-irregular", True),
])
def test_specific_rhythm_needs_its_qualifier(finding, expected):
    assert feature_present("irregularly irregular rhythm", [finding], strict=True) is expected


def test_general_irregular_pulse_is_general_support_only():
    s = _state("my heartbeat feels uneven")
    s.record_exam("cardiac_auscultation", "Pulse has an irregular rhythm with occasional pauses")
    item = _item(s, "cardiac_arrhythmia")
    assert "irregularly irregular rhythm" not in item.supporting_evidence
    assert "irregular heartbeat" in item.supporting_evidence


# --- 2A: the measured rate is evidence, separate from regularity ---------------------------------------------

@pytest.mark.parametrize("vitals,finding", [
    ("BP 106/68, HR 37 regular, Temp 36.7", "pulse rate below 50"),
    ("BP 120/80, HR 172 regular, Temp 36.8", "pulse rate of 150 or more"),
    ("BP 120/80, HR 49, Temp 36.6", "pulse rate below 50"),
    ("BP 120/80, HR 150, Temp 36.6", "pulse rate of 150 or more"),
])
def test_slow_or_fast_rate_is_kept_and_reviewed(vitals, finding):
    s = _state("I nearly passed out")
    s.record_initial_vitals(vitals)
    assert s.vital_signs[-1].heart_rate is not None
    assert finding in s.vital_sign_findings
    assert finding in _item(s, "cardiac_arrhythmia").supporting_evidence


@pytest.mark.parametrize("vitals", ["BP 120/80, HR 68 regular, Temp 36.8", "BP 120/80, HR 50, Temp 36.8",
                                    "BP 120/80, HR 149, Temp 36.8"])
def test_rate_inside_the_boundaries_adds_nothing(vitals):
    s = _state("I nearly passed out")
    s.record_initial_vitals(vitals)
    assert not {"pulse rate below 50", "pulse rate of 150 or more"} & set(s.vital_sign_findings)


def test_reported_past_rate_is_not_a_current_measurement():
    s = _state("I nearly passed out")
    s.record_ask("past_medical_history", "Any past illnesses?", "my heart rate was 38 once last year")
    item = _item(s, "cardiac_arrhythmia")
    assert item is None or "pulse rate below 50" not in item.supporting_evidence


def test_fast_rate_never_names_a_rhythm_subtype():
    s = _state("I feel hot and shaky")
    s.record_initial_vitals("BP 118/70, HR 156, RR 22, Temp 39.4, SpO2 97%")
    item = _item(s, "cardiac_arrhythmia")
    assert not {"irregularly irregular rhythm", "narrow complex tachycardia", "atrial fibrillation on ecg"} & set(item.supporting_evidence)


# --- 2B: limited normalisation of observed wording -----------------------------------------------------------

@pytest.mark.parametrize("text,did,feature,present", [
    ("there is reduced power in both legs", "severe_electrolyte_disorder", "muscle weakness", True),
    ("I had a brief convulsive fit", "severe_electrolyte_disorder", "seizure", True),
    ("I am fit and well otherwise", "severe_electrolyte_disorder", "seizure", False),
    ("my heart suddenly took off", "cardiac_arrhythmia", "sudden onset palpitations", True),
    ("I felt lightheaded with it", "cardiac_arrhythmia", "associated lightheadedness", True),
])
def test_observed_wording_reaches_the_kb_feature(text, did, feature, present):
    s = _state("I don't feel right")
    s.record_ask("associated_symptoms", "Any other symptoms?", text)
    item = _item(s, did)
    assert (item is not None and feature in item.supporting_evidence) is present


def test_dialysis_is_kidney_disease_context_but_a_kidney_problem_is_not_assumed_chronic():
    on_dialysis = _state("I feel weak")
    on_dialysis.record_ask("past_medical_history", "Any past illnesses?", "kidney failure, I am on dialysis three times a week")
    vague = _state("I feel weak")
    vague.record_ask("past_medical_history", "Any past illnesses?", "I had a kidney problem")
    assert "chronic kidney disease" in _item(on_dialysis, "severe_electrolyte_disorder").supporting_evidence
    item = _item(vague, "severe_electrolyte_disorder")
    assert item is None or "chronic kidney disease" not in item.supporting_evidence


def test_a_single_drug_or_symptom_does_not_make_electrolyte_disorder_the_named_diagnosis():
    s = _state("I take a water tablet every morning")
    differential = DifferentialEngine().update(s)
    assert decide_final(s, differential).primary_id != "severe_electrolyte_disorder"


def test_or_feature_branches_are_presence_only():
    assert or_branches("history of heart attack or cardiomyopathy") == ("history of heart attack", "history of cardiomyopathy")
    assert or_branches("calf pain or tenderness") == ()
    # denying ONE branch never denies the disjunction
    assert not feature_denied("history of heart attack or cardiomyopathy", ["no heart attack"])


# --- 2C: answers grounded to the question actually asked ------------------------------------------------------

@pytest.mark.parametrize("answer,positive,negative,unknown", [
    ("Yes.", True, False, False),
    ("No.", False, True, False),
    ("I don't know.", False, False, True),
    ("아니요, 없어요.", False, True, False),
    ("네, 있어요.", True, False, False),
])
def test_bare_answer_attaches_to_the_single_asked_feature(answer, positive, negative, unknown):
    s = _state("I feel dizzy")
    s.record_ask("associated_symptoms:palpitations", "Any palpitations?", answer)
    assert ("palpitations" in s.pertinent_positives) is positive
    assert ("no palpitations" in s.pertinent_negatives) is negative
    assert ("palpitations" in s.unknown_findings) is unknown
    assert "Yes" not in s.pertinent_positives and "No" not in s.pertinent_positives


def test_explicit_answer_is_unchanged():
    s = _state("I feel dizzy")
    s.record_ask("associated_symptoms:palpitations", "Any palpitations?", "No palpitations.")
    assert s.pertinent_negatives == ["No palpitations"]


def test_generic_fallback_question_says_nothing_about_the_detailed_feature():
    key = "associated_symptoms:history of heart attack or cardiomyopathy"
    assert not question_is_faithful(key, "en")
    s = _state("I blacked out")
    s.record_ask("past_medical_history", "Any past illnesses?", "I had a heart attack two years ago")
    s.record_ask(key, "Any other symptoms?", "No.", faithful=False)
    assert not any("heart attack" in n for n in s.pertinent_negatives)
    assert not s.question_asked(key)            # the detailed discriminator was never really asked
    assert s.question_asked("associated_symptoms")  # the generic one was
    assert s.is_duplicate("ASK", key)           # and the fallback is not sent again


def test_earlier_positive_survives_a_later_generic_no():
    s = _state("my heart keeps racing")
    s.record_ask("associated_symptoms", "Any other symptoms?", "No.")
    assert not s.pertinent_negatives
    assert "racing heart" in _item(s, "cardiac_arrhythmia").supporting_evidence


def test_unknown_medication_names_are_not_drugs():
    s = _state("I feel dizzy")
    s.record_ask("medication", "What medicines do you take?", "I cannot remember their names.")
    assert s.medications == []
    assert any(u.startswith("medication") for u in s.unknown_findings)
    assert s.medication_text == ["I cannot remember their names."]


def test_bare_yes_to_a_compound_question_invents_no_part():
    s = _state("I feel weak")
    s.record_ask("associated_symptoms:vomiting or diarrhea", "Any vomiting or diarrhea?", "Yes.")
    assert s.pertinent_positives == ["vomiting or diarrhea"]


@pytest.mark.parametrize("answer,kind", [("No, I don't have that.", "no"), ("No idea", "unknown"),
                                         ("Yes, after every meal", None), ("No palpitations", None)])
def test_answer_kind(answer, kind):
    assert answer_kind(answer) == kind


# --- 3A: workup outcome -----------------------------------------------------------------------------------------

def test_rejected_or_unknown_exam_is_not_an_observation():
    s = _state("my heart flutters")
    s.record_exam_rejected("cardiac_auscultation")
    s.record_exam("neuro_exam", "Result unknown.")
    s.record_exam("abdominal_exam", "soft, non-tender")
    assert not s.exam_observed("cardiac_auscultation")
    assert not s.exam_observed("neuro_exam")
    assert s.exam_observed("abdominal_exam")
    assert "cardiac_auscultation" not in s.physical_examinations   # rejection never becomes a normal result


def test_unknown_answers_and_rejected_exams_do_not_address_arrhythmia():
    from nova_agent.config import get_config
    import os
    os.environ["NOVA_COMPETITION_RETRIEVAL"] = "1"
    get_config(reload=True)
    try:
        from nova_agent.resolution import is_resolved
        s = _state("my heart flutters")
        for q in ("onset", "duration", "associated_symptoms", "past_medical_history"):
            s.record_ask(q, q, "I don't know.")
        s.record_exam_rejected("cardiac_auscultation")
        assert not is_resolved("cardiac_arrhythmia", [], s)
    finally:
        os.environ.pop("NOVA_COMPETITION_RETRIEVAL", None)
        get_config(reload=True)


# --- 3C: support contract for naming the primary -----------------------------------------------------------------

def _fake(did, support, score=1.0, dangerous=True):
    return SimpleNamespace(diagnosis_id=did, diagnosis=did, supporting_evidence=list(support), score=score,
                           dangerous_if_missed=dangerous, fallback_candidate=False, urgency="HIGH",
                           contradictory_evidence=[], missing_discriminative_evidence=[])


def test_zero_support_leader_is_not_named():
    s = _state("I just feel off")
    d = [_fake("acute_abdomen", [], score=0.0), _fake("migraine", [], score=0.0, dangerous=False)]
    final = decide_final(s, d, "information_exhausted")
    assert final.primary_id == UNDIFFERENTIATED_ID and final.completion_reason == "information_exhausted"


def test_dangerous_diagnosis_on_one_nonspecific_symptom_is_not_named():
    s = _state("I feel dizzy", age=29, sex="female")
    assert "single_nonspecific_support" in support_problems(_fake("ectopic_pregnancy", ["dizziness"]), s, [])


def test_ectopic_needs_a_pregnancy_related_feature():
    s = _state("I feel dizzy", age=29, sex="female")
    item = _fake("ectopic_pregnancy", ["dizziness", "syncope"], score=2.0)
    assert any(p.startswith("required_context_missing") for p in support_problems(item, s, [item]))
    s.record_ask("associated_symptoms", "Any other symptoms?", "my period is two weeks late and I have lower abdominal pain")
    assert not any(p.startswith("required_context_missing") for p in support_problems(item, s, [item]))


def test_hypertensive_emergency_needs_a_hypertensive_reading():
    item = _fake("onto::tier2:hypertensive_emergency", ["chest pain", "shortness of breath"], score=2.2)
    low = _state("chest pain and short of breath")
    low.record_initial_vitals("BP 92/58, HR 176, Temp 36.8")
    high = _state("chest pain and short of breath")
    high.record_initial_vitals("BP 214/126, HR 96, Temp 36.8")
    assert any(p.startswith("required_context_missing") for p in support_problems(item, low, [item]))
    assert not any(p.startswith("required_context_missing") for p in support_problems(item, high, [item]))


def test_siadh_is_not_named_from_symptoms_alone():
    s = _state("headache, nausea and confusion")
    item = _fake("onto::tier2:siadh", ["confusion", "headache", "nausea"], score=2.4)
    assert any(p.startswith("required_context_missing") for p in support_problems(item, s, [item]))


def test_hemoptysis_needs_blood_actually_coughed_up():
    s = _state("cough and chest pain")
    item = _fake("onto::tier2:sym_hemoptysis", ["cough", "chest pain"], score=2.0)
    assert any(p.startswith("required_context_missing") for p in support_problems(item, s, [item]))


def test_one_strong_specific_observation_may_be_named():
    s = _state("I feel terrible")
    item = _fake("sepsis", ["elevated lactate (5.1 mmol/L)"], score=2.5)
    assert support_problems(item, s, [item]) == []


def test_dangerous_tie_on_nonspecific_support_is_not_decided_by_order():
    s = _state("I feel dizzy")
    a, b = _fake("ectopic_pregnancy", ["dizziness", "nausea"], 2.0), _fake("bppv", ["dizziness", "nausea"], 2.0, dangerous=False)
    assert "tied_on_nonspecific_support" in support_problems(a, s, [a, b])


def test_closing_names_stay_at_the_same_scope():
    names = same_scope_names("Cardiac Arrhythmia (e.g. Atrial Fibrillation, SVT)")
    assert names == ["Cardiac Arrhythmia (e.g. Atrial Fibrillation, SVT)", "Cardiac Arrhythmia", "Arrhythmia"]
    assert not any("fibrillation" in n.lower() for n in names[1:])
    assert explanation_text("severe electrolyte disorder", "en", ["electrolyte disorder"]) == "Possibly electrolyte disorder."
    text = explanation_text("sepsis", "en", same_scope_names("Sepsis"))
    assert "shock" not in text.lower()


# --- 3C end to end: an exhausted encounter with no supported diagnosis -------------------------------------------

def _sparse_case(cc, lang="en"):
    neg, normal = ("아니요, 없어요.", "특이 소견 없음.") if lang == "ko" else ("No.", "Unremarkable.")
    return SyntheticCase(case_id="RoundQ_sparse", chief_complaint=cc, demographics={"age": 34, "sex": "female"},
                         ground_truth_diagnosis="unknown", answers={}, exam_results={}, default_answer=neg,
                         default_exam_result=normal, category="round_q;sparse", notes="Round Q test", scoring_expected=False)


@pytest.mark.parametrize("cc,lang", [("I have been feeling a little strange since lunch", "en"),
                                     ("오늘 그냥 기분이 좀 이상해요", "ko")])
def test_sparse_encounter_completes_undifferentiated_with_one_consistent_decision(cc, lang, monkeypatch):
    monkeypatch.setenv("NOVA_COMPETITION_RETRIEVAL", "1")
    from nova_agent.config import get_config
    get_config(reload=True)
    try:
        from evaluation.preliminary_driver import run_episode
        ep = run_episode(_sparse_case(cc, lang))
    finally:
        monkeypatch.delenv("NOVA_COMPETITION_RETRIEVAL")
        get_config(reload=True)
    final = ep.wire[-1]
    md = final["metadata"]
    assert final["action_type"] == "DIAGNOSE"
    if md["final_decision"]["support"] == "UNDIFFERENTIATED":
        assert md["key"] == UNDIFFERENTIATED_ID
        assert "미분화" in final["primary_diagnosis"] or "Undifferentiated" in final["primary_diagnosis"]
        assert final["primary_diagnosis"] in final["soap"]["A"]
        explanation = [w["content"] for w in ep.wire if (w.get("metadata") or {}).get("key") == "explanation"]
        assert explanation and explanation[0] in ("The cause is not yet clear.", "아직 진단이 불확실해요.")
    else:
        # a named primary must be the one the SOAP assessment reports
        assert final["primary_diagnosis"].split(" (")[0] in final["soap"]["A"]
    assert len([w for w in ep.wire if w["action_type"] != "DIAGNOSE"]) <= 50
    assert all(len(w["content"]) <= 30 for w in ep.wire if w["action_type"] == "SAY")


# --- found while measuring: bare "No" against what the patient already said; closing before a dangerous exam -------

def test_instant_onset_wording_is_a_sudden_onset_headache():
    from nova_agent.clinical_concepts import canonical_findings_for
    assert "sudden onset severe headache" in canonical_findings_for("the worst headache ever came on in a second")
    assert "sudden onset severe headache" not in canonical_findings_for("my headache built up slowly over the day")


def test_bare_no_contradicting_an_earlier_report_is_a_conflict_not_a_denial():
    s = _state("The worst headache of my life came on in a second")
    s.record_ask("associated_symptoms:sudden severe headache", "Any sudden severe headache?", "No.")
    assert "no sudden severe headache" not in s.pertinent_negatives
    assert "conflicting answer: sudden severe headache" in s.unknown_findings


def test_later_report_withdraws_an_earlier_bare_no():
    s = _state("sharp chest pain")
    s.record_ask("associated_symptoms:pain eased by leaning forward", "Any pain eased by leaning forward?", "No.")
    assert "no pain eased by leaning forward" in s.pertinent_negatives
    s.record_ask("relieving", "What makes it better?", "leaning forward helps a lot")
    assert "no pain eased by leaning forward" not in s.pertinent_negatives
    assert "conflicting answer: pain eased by leaning forward" in s.unknown_findings


def test_explicit_denial_is_never_withdrawn():
    s = _state("my heart flutters")
    s.record_ask("associated_symptoms:palpitations", "Any palpitations?", "No palpitations at all.")
    s.record_ask("associated_symptoms", "Any other symptoms?", "a bit of palpitations last week")
    assert any(n.lower().startswith("no palpitations") for n in s.pertinent_negatives)


def test_unexamined_dangerous_alternative_with_support_is_examined_before_closing():
    from nova_agent.action_selector import ActionSelector
    s = _state("my words are coming out wrong and my heart feels irregular", age=74, sex="female")
    s.record_ask("past_medical_history", "Any past illnesses?", "irregular heartbeat")
    differential = DifferentialEngine().update(s)
    exam = ActionSelector._pending_dangerous_bedside_exam(s, differential, [])
    assert exam is not None and exam.action_type == "EXAM"
    s.record_exam(exam.key, "normal")
    assert ActionSelector._pending_dangerous_bedside_exam(s, DifferentialEngine().update(s), []) is None or \
        ActionSelector._pending_dangerous_bedside_exam(s, DifferentialEngine().update(s), []).key != exam.key


@pytest.mark.parametrize("text,present,absent", [
    ("소변 볼 때 따갑고 자주 마려워요", {"dysuria", "urinary frequency"}, set()),
    ("소변 볼 때 안 따가워요", set(), {"dysuria"}),
    ("가슴이 갑자기 빨리 뛰고 어지러워요", {"racing heart", "palpitations"}, {"chest pain"}),
    ("가슴이 아프고 두근거려요", {"chest pain"}, set()),
    ("가슴이 답답해요", {"chest pain"}, {"racing heart"}),
])
def test_korean_heartbeat_and_urinary_wording(text, present, absent):
    from nova_agent.multilingual_concepts import english_evidence_for
    found = set(english_evidence_for(text))
    assert present <= found and not (absent & found)


def test_unfaithful_detailed_question_is_sent_as_the_generic_question_once():
    from nova_agent.action_selector import ActionSelector, ScoredCandidate
    long_key = "associated_symptoms:history of heart attack or cardiomyopathy"
    s = _state("I blacked out")
    cands = [ScoredCandidate(action_type="ASK", key=long_key, content="x", utility=3.0, components={}),
             ScoredCandidate(action_type="ASK", key="associated_symptoms:blood pressure above 180 over 120", content="x", utility=2.0, components={}),
             ScoredCandidate(action_type="ASK", key="associated_symptoms:palpitations", content="x", utility=1.0, components={})]
    out = ActionSelector._faithful_asks(s, cands)
    assert [c.key for c in out] == ["associated_symptoms", "associated_symptoms:palpitations"]
    s.record_ask("associated_symptoms", "Any other symptoms?", "my calf is swollen")
    out = ActionSelector._faithful_asks(s, cands)
    assert [c.key for c in out] == ["associated_symptoms:palpitations"]
