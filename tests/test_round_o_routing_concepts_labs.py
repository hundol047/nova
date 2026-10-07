"""Round O: connective-free fuzzy routing (NOVA_ROUTING_V2), chest-wall / pleuritic / PE-imaging concepts and
question-context for aggravating/relieving answers (NOVA_CONCEPTS_V2), bare-unit lactate (NOVA_LABS_V2).

Fresh wording written for this file (not copied from any evaluation case). Covers paraphrases, benign
look-alikes, negation and history, units (and the unchanged glucose mmol/L policy), and the switches."""
import pytest

from nova_agent.chief_complaint import route
from nova_agent.clinical_concepts import canonical_findings_for
from nova_agent.config import get_config
from nova_agent.differential import DifferentialEngine
from nova_agent.severity_evidence import extract_lactate_mmol_l
from nova_agent.state import PatientState


@pytest.fixture
def switch(monkeypatch):
    def _set(name, value):
        monkeypatch.setenv(name, value)
        get_config(reload=True)
    yield _set
    for name in ("NOVA_ROUTING_V2", "NOVA_CONCEPTS_V2", "NOVA_LABS_V2", "NOVA_STOP_V2"):
        monkeypatch.delenv(name, raising=False)
    get_config(reload=True)


def _rank(state, did):
    ranked = [x.diagnosis_id for x in DifferentialEngine().update(state)]
    return ranked.index(did) if did in ranked else None


# --- routing -------------------------------------------------------------------------------------

def test_connective_words_do_not_route_retrosternal_burning_to_the_urinary_tract():
    assert route("a burning ache behind the breastbone when I bend over after supper").primary_tag != "urinary_symptoms"


@pytest.mark.parametrize("text", ["pain right on my sternum", "heartburn all evening", "my breastbone aches"])
def test_chest_anatomy_and_heartburn_route_to_chest_pain(text):
    assert route(text).primary_tag == "chest_pain"


@pytest.mark.parametrize("text", ["it stings when I wee", "burning when I pee", "weeing every half hour"])
def test_genuine_urinary_wording_still_routes_to_urinary(text):
    assert route(text).primary_tag == "urinary_symptoms"


def test_routing_switch_off_restores_connective_counting(switch):
    switch("NOVA_ROUTING_V2", "0")
    from nova_agent.chief_complaint import _fuzzy_score, _content_words, _meaningful_words
    words = _meaningful_words(_content_words("a burning ache behind the breastbone when i bend over"))
    assert _fuzzy_score(words, "urinary_symptoms") >= 0.6


# --- chest wall / pleuritic / PE imaging concepts -----------------------------------------------

@pytest.mark.parametrize("text,concept", [
    ("it is sore when I push on my ribs", "reproducible with palpation"),
    ("tender to touch just left of the sternum", "reproducible with palpation"),
    ("I can point to the pain with my finger", "localized tenderness"),
    ("sharper when I reach for the top shelf", "worse with movement"),
    ("rotating my trunk sets it off", "worse with movement"),
    ("a stitch every time I take a deep breath", "pleuritic chest pain"),
    ("breathing in hurts on the left", "pleuritic chest pain"),
    ("CTPA: emboli in both lower lobe pulmonary arteries", "filling defect in the pulmonary artery"),
    ("saddle embolus seen", "filling defect in the pulmonary artery"),
])
def test_new_everyday_and_report_wording(text, concept):
    assert concept in canonical_findings_for(text)


@pytest.mark.parametrize("text,concept", [
    ("no tenderness when the chest wall is pressed", "reproducible with palpation"),
    ("not worse when I move", "worse with movement"),
    ("worse when I move my bowels", "worse with movement"),
    ("CT pulmonary angiogram: no pulmonary embolism", "filling defect in the pulmonary artery"),
    ("pulmonary embolism years ago, on no treatment now", "filling defect in the pulmonary artery"),
    ("chest pressure when I climb stairs", "pleuritic chest pain"),
])
def test_negated_historical_or_exertional_wording_is_not_mapped(text, concept):
    assert concept not in canonical_findings_for(text)


def test_exertional_crushing_pain_is_not_turned_into_chest_wall_pain():
    found = canonical_findings_for("crushing pressure in my chest when I walk uphill, eases with rest")
    assert not {"reproducible with palpation", "worse with movement", "localized tenderness"} & set(found)


# --- question context for modifier answers ------------------------------------------------------

def test_aggravating_answer_gets_its_question_context():
    s = PatientState(case_id="ctx", chief_complaint="ache in my chest since the weekend", demographics={"age": 33, "sex": "male"})
    s.record_ask("aggravating", "What makes it worse?", "twisting round and lifting the kettle")
    assert "worse with twisting round and lifting the kettle" in s.pertinent_positives
    assert "worse with movement" in s.all_findings_text()


def test_explicit_or_negative_modifier_answers_are_not_rewritten():
    s = PatientState(case_id="ctx2", chief_complaint="ache in my chest", demographics={"age": 33, "sex": "male"})
    s.record_ask("aggravating", "q", "worse after big meals")
    s.record_ask("relieving", "q", "nothing helps")
    assert not any(p.startswith("worse with worse") for p in s.pertinent_positives)
    assert not any(p.startswith("relieved by nothing") for p in s.pertinent_positives)


def test_chest_wall_wording_ranks_musculoskeletal_pain_first_without_naming_it():
    s = PatientState(case_id="msk", chief_complaint="my chest wall is sore since I started climbing",
                     demographics={"age": 27, "sex": "female"})
    s.record_ask("aggravating", "q", "pushing on the spot and stretching")
    s.record_test("ecg", "normal sinus rhythm")
    s.record_test("troponin", "normal")
    assert _rank(s, "musculoskeletal_chest_pain") == 0


def test_concepts_switch_off(switch):
    switch("NOVA_CONCEPTS_V2", "0")
    assert canonical_findings_for("it is sore when I push on my ribs") == []
    s = PatientState(case_id="off", chief_complaint="ache in my chest", demographics={"age": 33, "sex": "male"})
    s.record_ask("aggravating", "q", "twisting")
    assert "worse with twisting" not in s.pertinent_positives


# --- lactate units ------------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("4.6 mmol/L", 4.6), ("1.2 mmol/L", 1.2), ("lactate 3.3 mmol/L", 3.3),
    ("42 mg/dL", None),               # mg/dL never read as mmol/L
    ("no lactate 5 mmol/L", None), ("previously 6.1 mmol/L", None),
])
def test_bare_unit_lactate(text, expected):
    assert extract_lactate_mmol_l(text) == expected


def test_glucose_mmol_policy_is_unchanged():
    from nova_agent.glucose_evidence import extract_glucose_mg_dl
    assert extract_glucose_mg_dl("glucose 3.1 mmol/L") is None


def test_bare_lactate_makes_septic_hypoperfusion_count_for_sepsis():
    s = PatientState(case_id="sep", chief_complaint="feverish and confused, breathing hard", demographics={"age": 81, "sex": "female"})
    s.record_exam("vital_signs", "BP 82/50, HR 126, RR 30, Temp 39.1")
    s.record_test("urinalysis", "nitrite positive")
    s.record_test("lactate", "5.2 mmol/L")
    sepsis = next(x for x in DifferentialEngine().update(s) if x.diagnosis_id == "sepsis")
    assert any(e.startswith("elevated lactate") for e in sepsis.supporting_evidence)
    assert _rank(s, "sepsis") == 0


def test_labs_switch_off(switch):
    switch("NOVA_LABS_V2", "0")
    assert extract_lactate_mmol_l("4.6 mmol/L") is None


# --- stop policy (NOVA_STOP_V2) ------------------------------------------------------------------

def _item(did, name, score, support, dangerous, rank, band="LOW"):
    from nova_agent.differential import DifferentialItem
    return DifferentialItem(diagnosis=name, diagnosis_id=did, rank=rank, score=score, score_ratio=0.2,
                            supporting_evidence=support, urgency="HIGH" if dangerous else "LOW",
                            dangerous_if_missed=dangerous, confidence_band=band)


def _stop_state(turns=8):
    s = PatientState(case_id="stop", chief_complaint="ache in my chest", demographics={"age": 30, "sex": "male"})
    for i in range(turns):
        s.record_ask(f"q{i}", "q", "fine")
    return s


def test_decisive_benign_lead_now_stops_in_legacy_mode():
    from nova_agent.stop_policy import StopPolicy
    diff = [_item("musculoskeletal_chest_pain", "MSK", 2.6, ["reproducible with palpation", "worse with movement"], False, 1),
            _item("gerd", "GERD", 0.5, ["burning chest pain"], False, 2)]
    decision = StopPolicy().evaluate(_stop_state(), diff, [], 0.1, best_decision_value=0.1)
    assert decision.should_diagnose


def test_dangerous_leader_is_not_closed_on_history_alone():
    from nova_agent.stop_policy import StopPolicy
    diff = [_item("aortic_dissection", "Aortic Dissection", 2.4, ["pain radiates to back", "sudden onset severe pain"], True, 1),
            _item("acute_pancreatitis", "Acute Pancreatitis", 1.0, ["vomiting"], False, 2)]
    s = _stop_state()
    assert not StopPolicy().evaluate(s, diff, [], 0.5, best_decision_value=0.5).should_diagnose
    s.record_test("ct_aorta", "no dissection, normal calibre aorta")   # defining test done but NOT confirming
    assert not StopPolicy().evaluate(s, diff, [], 0.5, best_decision_value=0.5).should_diagnose


def test_dangerous_leader_with_objective_confirmation_may_stop():
    from nova_agent.stop_policy import StopPolicy
    diff = [_item("aortic_dissection", "Aortic Dissection", 4.4,
                  ["pain radiates to back", "sudden onset severe pain", "intimal flap"], True, 1),
            _item("acute_pancreatitis", "Acute Pancreatitis", 1.0, ["vomiting"], False, 2)]
    s = _stop_state()
    s.record_test("ct_aorta", "intimal flap in the ascending aorta")
    assert StopPolicy().evaluate(s, diff, [], 0.5, best_decision_value=0.5).should_diagnose


def test_supported_dangerous_alternative_still_blocks_a_benign_decisive_lead():
    from nova_agent.stop_policy import StopPolicy
    diff = [_item("gerd", "GERD", 3.0, ["burning chest pain", "relieved by antacids"], False, 1),
            _item("acute_coronary_syndrome", "ACS", 1.2, ["exertional chest pain", "diaphoresis"], True, 2, band="MEDIUM")]
    assert not StopPolicy().evaluate(_stop_state(), diff, [], 0.2, best_decision_value=0.2).should_diagnose


def test_stop_switch_off_keeps_legacy_selector_behaviour(switch):
    switch("NOVA_STOP_V2", "0")
    assert not get_config().stop_v2_enabled
