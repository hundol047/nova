"""Round P: evidence interpretation v3, converging-evidence ranking, objective-only question filter, escalation
specificity and the preliminary bedside stop (switches NOVA_EVIDENCE_V3 / NOVA_RANKING_V3 / NOVA_ACTION_V3 /
NOVA_STOP_V3).

Fresh wording written for this file (not copied from any evaluation case). Covers paraphrases, benign look-alikes,
negation and stopped drugs, Korean wording, units/directions, and that each switch restores the previous behaviour."""
import pytest

from nova_agent.clinical_concepts import canonical_findings_for, is_objective_only_feature
from nova_agent.config import get_config
from nova_agent.differential import DifferentialEngine
from nova_agent.matching import feature_present
from nova_agent.multilingual_concepts import english_evidence_for
from nova_agent.state import PatientState

SWITCHES = ("NOVA_EVIDENCE_V3", "NOVA_RANKING_V3", "NOVA_ACTION_V3", "NOVA_STOP_V3", "NOVA_DOCUMENTED_DX")


@pytest.fixture
def switch(monkeypatch):
    def _set(name, value):
        monkeypatch.setenv(name, value)
        get_config(reload=True)
    yield _set
    for name in SWITCHES:
        monkeypatch.delenv(name, raising=False)
    get_config(reload=True)


def _ranked(state):
    return [d.diagnosis_id for d in DifferentialEngine().update(state)]


# --- partial matching: direction, head noun, time-pattern qualifier ------------------------------------------

@pytest.mark.parametrize("feature,finding,expected", [
    ("low blood pressure", "takes a tablet for blood pressure", False),      # names an indication, not a reading
    ("low blood pressure", "her blood pressure is low today", True),
    ("low blood pressure", "the blood pressure dropped when she stood", True),
    ("washed out colors", "colors look washed out in that eye", True),
    ("episodic high blood pressure", "has had high blood pressure for years", False),
    ("episodic high blood pressure", "episodes of very high blood pressure with sweating", True),
    ("shortness of breath on exertion", "short of breath climbing stairs", True),
    ("headache worse in the morning", "headache in the morning", True),
])
def test_partial_matches_keep_direction_head_and_pattern(feature, finding, expected):
    assert feature_present(feature, [finding]) is expected


def test_partial_match_rules_are_switchable(switch):
    switch("NOVA_EVIDENCE_V3", "0")
    assert feature_present("low blood pressure", ["takes a tablet for blood pressure"])


# --- concepts --------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("text,concept", [
    ("she takes bendroflumethiazide each morning", "diuretic use"),
    ("on a water pill for her ankles", "diuretic use"),
    ("I just feel weak all over today", "generalized weakness"),
    ("pulse 62 and irregular", "irregular heartbeat"),
    ("heart sounds irregularly irregular", "irregularly irregular rhythm"),
    ("my heart keeps skipping", "irregular heartbeat"),
    ("a fast heartbeat came on at rest", "racing heart"),
    ("I'm wiped out all the time", "fatigue"),
])
def test_new_concepts(text, concept):
    assert concept in canonical_findings_for(text)


@pytest.mark.parametrize("text,concept", [
    ("she stopped her water pill a month ago", "diuretic use"),
    ("no diuretics", "diuretic use"),
    ("weak left hand only", "generalized weakness"),
    ("irregular periods since stopping the pill", "irregular heartbeat"),
    ("regular rhythm, no murmur", "irregular heartbeat"),
    ("heart not racing at all", "racing heart"),
])
def test_negated_stopped_or_unrelated_wording_is_not_mapped(text, concept):
    assert concept not in canonical_findings_for(text)


@pytest.mark.parametrize("text,expected", [
    ("다리에 보라색 점상 출혈이 있어요", "petechial rash rash"),
    ("계속 졸려하고 대답이 늦어요", "altered mental status"),
    ("이뇨제를 먹고 있어요", "diuretic use"),
    ("맥이 불규칙하게 뛰어요", "irregular heartbeat"),
])
def test_korean_wording(text, expected):
    assert expected in english_evidence_for(text)


def test_korean_negation_cancels():
    assert "petechial rash rash" not in english_evidence_for("점상 출혈은 없어요")


# --- labs: both directions of potassium confirm a severe electrolyte disorder --------------------------------

@pytest.mark.parametrize("result,phrase", [("potassium 2.5 mmol/L", "hypokalemia"), ("potassium 7.1 mmol/L", "hyperkalemia"),
                                           ("sodium 116 mmol/L", "hyponatremia")])
def test_either_direction_of_a_bidirectional_lab_supports_once(result, phrase):
    s = PatientState(case_id="lab", chief_complaint="cramps and weakness", demographics={"age": 66, "sex": "male"})
    s.record_test("bmp", result)
    item = next(d for d in DifferentialEngine().update(s) if d.diagnosis_id == "severe_electrolyte_disorder")
    assert phrase in item.supporting_evidence and item.supporting_evidence.count(phrase) == 1
    assert not item.contradictory_evidence


def test_normal_electrolytes_do_not_support():
    s = PatientState(case_id="lab2", chief_complaint="cramps and weakness", demographics={"age": 66, "sex": "male"})
    s.record_test("bmp", "potassium 4.2 mmol/L, sodium 139 mmol/L")
    item = next(d for d in DifferentialEngine().update(s) if d.diagnosis_id == "severe_electrolyte_disorder")
    assert not {"hypokalemia", "hyperkalemia", "hyponatremia"} & set(item.supporting_evidence)


# --- candidate sourcing and ranking -------------------------------------------------------------------------

def test_diuretic_and_vomiting_bring_electrolyte_disorder_into_play():
    s = PatientState(case_id="ed", chief_complaint="unsteady and slow to answer since yesterday", demographics={"age": 79, "sex": "female"})
    s.record_ask("medication", "q", "a water pill and something for her heart")
    s.record_ask("associated_symptoms", "q", "threw up twice and off her food")
    item = next(d for d in DifferentialEngine().update(s) if d.diagnosis_id == "severe_electrolyte_disorder")
    assert {"diuretic use", "vomiting or diarrhea"} <= set(item.supporting_evidence)


def test_converging_vital_and_risk_evidence_ranks_pe_above_thin_generic_matches():
    s = PatientState(case_id="pe", chief_complaint="breathless with a pounding heart since my knee operation",
                     demographics={"age": 58, "sex": "female"})
    s.record_ask("past_medical_history", "q", "knee replacement six days ago, stuck in bed since")
    s.record_initial_vitals("HR 121, RR 27, SpO2 89%")
    ranked = _ranked(s)
    assert ranked[0] == "pulmonary_embolism"


def test_pneumonia_hypoxia_does_not_escalate_to_pe():
    s = PatientState(case_id="pn", chief_complaint="cough with green phlegm and a temperature", demographics={"age": 70, "sex": "male"})
    s.record_ask("associated_symptoms", "q", "shivers, a bit breathless")
    s.record_exam("vital_signs", "BP 126/78, HR 104, RR 24, Temp 38.7, SpO2 91%")
    s.record_exam("lung_auscultation", "crackles at the right base")
    ranked = _ranked(s)
    assert ranked.index("pneumonia") < ranked.index("pulmonary_embolism")


def test_ranking_switch_off(switch):
    switch("NOVA_RANKING_V3", "0")
    assert not get_config().ranking_v3_enabled


# --- question filter ---------------------------------------------------------------------------------------

@pytest.mark.parametrize("feature,objective", [("ejection systolic murmur", True), ("low sodium", True),
                                               ("rebound tenderness", True), ("elevated jvp", True),
                                               ("chest pain on exertion", False), ("leg swelling", False),
                                               ("seizure", False), ("family history of sudden death", False)])
def test_objective_only_features(feature, objective):
    assert is_objective_only_feature(feature) is objective


def test_agent_never_asks_patient_about_exam_or_lab_only_findings():
    from nova_agent.action_selector import ActionSelector
    s = PatientState(case_id="q", chief_complaint="breathless and my heart flutters when I climb stairs",
                     demographics={"age": 45, "sex": "male"})
    s.record_ask("onset", "q", "a few weeks")
    d = DifferentialEngine().update(s)
    from nova_agent.safety import SafetyLayer
    _, candidates, _ = ActionSelector().generate_and_select(s, d, SafetyLayer().assess(s, d))
    asks = [c.key for c in candidates if c.action_type == "ASK" and ":" in c.key]
    assert not any(is_objective_only_feature(k.split(":", 1)[1]) for k in asks)


# --- preliminary bedside stop -------------------------------------------------------------------------------

def _item(did, score, support, dangerous, rank):
    from nova_agent.differential import DifferentialItem
    return DifferentialItem(diagnosis=did, diagnosis_id=did, rank=rank, score=score, score_ratio=0.2,
                            supporting_evidence=support, urgency="HIGH" if dangerous else "LOW",
                            dangerous_if_missed=dangerous, confidence_band="LOW")


def _prelim_state(exams):
    s = PatientState(case_id="ps", chief_complaint="fever and a stiff neck", demographics={"age": 20, "sex": "male"})
    s.preliminary_rules = True
    for q in ("associated_symptoms", "onset", "past_medical_history"):
        s.record_ask(q, "q", "yes")
    for key, result in exams.items():
        s.record_exam(key, result)
    for i in range(4):
        s.record_ask(f"x{i}", "q", "no")
    return s


def test_dangerous_leader_stops_in_preliminary_once_bedside_workup_is_complete():
    from nova_agent.stop_policy import StopPolicy
    diff = [_item("meningitis", 4.0, ["fever", "neck stiffness", "photophobia"], True, 1),
            _item("migraine", 1.0, ["photophobia"], False, 2)]
    full = {"meningeal_signs": "neck stiffness present", "skin_exam": "no rash", "vital_signs": "Temp 39.1, HR 112",
            "mental_status_exam": "alert"}
    assert StopPolicy().evaluate(_prelim_state(full), diff, [], 0.5, best_decision_value=0.5).should_diagnose
    partial = {"vital_signs": "Temp 39.1, HR 112"}
    assert not StopPolicy().evaluate(_prelim_state(partial), diff, [], 0.5, best_decision_value=0.5).should_diagnose


def test_bedside_stop_needs_an_objective_supporting_finding():
    from nova_agent.stop_policy import StopPolicy
    diff = [_item("meningitis", 4.0, ["photophobia", "headache"], True, 1), _item("migraine", 1.0, ["photophobia"], False, 2)]
    exams = {"meningeal_signs": "no neck stiffness", "skin_exam": "normal", "vital_signs": "normal", "mental_status_exam": "alert"}
    assert not StopPolicy().evaluate(_prelim_state(exams), diff, [], 0.5, best_decision_value=0.5).should_diagnose


def test_bedside_stop_never_applies_outside_preliminary_rules():
    from nova_agent.stop_policy import StopPolicy
    diff = [_item("meningitis", 4.0, ["fever", "neck stiffness", "photophobia"], True, 1),
            _item("migraine", 1.0, ["photophobia"], False, 2)]
    s = _prelim_state({"meningeal_signs": "neck stiffness present", "skin_exam": "no rash", "vital_signs": "Temp 39.1",
                       "mental_status_exam": "alert"})
    s.preliminary_rules = False
    assert not StopPolicy().evaluate(s, diff, [], 0.5, best_decision_value=0.5).should_diagnose


# --- documented diagnosis (NOVA_DOCUMENTED_DX) ----------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("The cardiology letter states atrial fibrillation and asks for follow-up", "cardiac_arrhythmia"),
    ("I was diagnosed with pulmonary embolism last week and the breathlessness is back", "pulmonary_embolism"),
])
def test_documented_diagnosis_is_recognised(text, expected):
    from nova_agent.documented_diagnosis import documented_diagnosis_ids
    assert expected in documented_diagnosis_ids([text])


@pytest.mark.parametrize("text", [
    "I am worried it might be pulmonary embolism",              # the patient's own speculation
    "the doctor said it was not pulmonary embolism",            # denial
    "I was diagnosed with asthma as a child",                   # history only
    "sudden breathlessness since this morning",                 # no documentation at all
])
def test_speculation_denial_or_history_is_not_a_documented_diagnosis(text):
    from nova_agent.documented_diagnosis import documented_diagnosis_ids
    assert documented_diagnosis_ids([text]) == []


def test_documented_diagnosis_adds_one_feature_of_support_only():
    s = PatientState(case_id="dd", chief_complaint="The discharge letter mentions atrial fibrillation; my pulse feels uneven",
                     demographics={"age": 70, "sex": "male"})
    item = next(d for d in DifferentialEngine().update(s) if d.diagnosis_id == "cardiac_arrhythmia")
    assert item.supporting_evidence.count("documented diagnosis") == 1


def test_documented_diagnosis_switch_off(switch):
    monkey = switch
    monkey("NOVA_DOCUMENTED_DX", "0")
    from nova_agent.documented_diagnosis import documented_diagnosis_ids
    assert documented_diagnosis_ids(["The discharge letter mentions atrial fibrillation"]) == []


# --- one observation, one piece of evidence; escalation needs converging support -----------------------------

def test_irregularly_irregular_is_counted_once():
    found = canonical_findings_for("rhythm irregularly irregular on auscultation")
    assert "irregularly irregular rhythm" in found and "irregular heartbeat" not in found


def test_af_found_at_examination_does_not_displace_a_confirmed_stroke():
    s = PatientState(case_id="st", chief_complaint="sudden weakness of my left arm and a headache", demographics={"age": 76, "sex": "male"})
    s.record_exam("cardiac_auscultation", "irregularly irregular")
    s.record_exam("neuro_exam", "left arm drift and left facial droop")
    s.record_test("ct_head", "acute infarct in the right middle cerebral artery territory")
    assert _ranked(s)[0] == "ischemic_stroke"


def test_well_supported_pneumonia_is_not_displaced_by_a_thinner_pe():
    s = PatientState(case_id="pn2", chief_complaint="fever, cough and a sharp pain on breathing in", demographics={"age": 81, "sex": "female"})
    s.record_ask("past_medical_history", "q", "COPD")
    s.record_exam("vital_signs", "BP 124/70, HR 112, RR 26, Temp 38.9, SpO2 89%")
    s.record_exam("lung_auscultation", "crackles at the left base")
    s.record_test("cxr", "left lower lobe consolidation")
    ranked = _ranked(s)
    assert ranked.index("pneumonia") < ranked.index("pulmonary_embolism")


def _arrhythmia(state):
    return next(d for d in DifferentialEngine().update(state) if d.diagnosis_id == "cardiac_arrhythmia")


def _palpitations_with_af_on_exam():
    s = PatientState(case_id="af", chief_complaint="my heartbeat feels irregular", demographics={"age": 70, "sex": "male"})
    s.record_exam("cardiac_auscultation", "irregularly irregular rhythm")
    return s


def test_general_rhythm_symptom_is_not_credited_again_beside_the_specific_rhythm_finding():
    d = _arrhythmia(_palpitations_with_af_on_exam())
    assert "irregularly irregular rhythm" in d.supporting_evidence
    assert "irregular heartbeat" not in d.supporting_evidence
    assert "irregular heartbeat" not in d.missing_discriminative_evidence


def test_rhythm_subsumption_switch_off_restores_previous_scoring(switch):
    switch("NOVA_RANKING_V3", "0")
    d = _arrhythmia(_palpitations_with_af_on_exam())
    assert {"irregularly irregular rhythm", "irregular heartbeat"} <= set(d.supporting_evidence)


def test_rhythm_symptom_still_counts_without_an_objective_rhythm_finding():
    s = PatientState(case_id="af2", chief_complaint="my heartbeat feels irregular", demographics={"age": 70, "sex": "male"})
    assert "irregular heartbeat" in _arrhythmia(s).supporting_evidence
