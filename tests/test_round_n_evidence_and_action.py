"""Round N steps 3-6: evidence interpretation (NOVA_EVIDENCE_V2) and blocking-danger workup priority (NOVA_ACTION_V2).

Fresh wording written for this file (not copied from any evaluation case). Covers: idiom words scattered over a
sentence vs. a genuine paraphrase, linking verbs, routing proximity, negative beta-hCG as evidence against
ectopic pregnancy (and NOT a normal troponin against ACS), lying/standing blood pressure parsing with normal and
abnormal values, syncope/urinary concepts with negation, the history gate on the action bonus, and the switches."""
import pytest

from nova_agent.action_selector import ActionSelector
from nova_agent.chief_complaint import route
from nova_agent.clinical_concepts import canonical_findings_for, orthostatic_drop
from nova_agent.config import get_config
from nova_agent.differential import DifferentialEngine
from nova_agent.matching import feature_present_with_aliases
from nova_agent.state import PatientState


@pytest.fixture
def switch(monkeypatch):
    def _set(name, value):
        monkeypatch.setenv(name, value)
        get_config(reload=True)
    yield _set
    for name in ("NOVA_EVIDENCE_V2", "NOVA_ACTION_V2", "NOVA_CONCEPT_NORMALIZATION"):
        monkeypatch.delenv(name, raising=False)
    get_config(reload=True)


# --- proximity-bounded paraphrase matching -------------------------------------------------------------------

def test_idiom_words_scattered_over_a_sentence_do_not_assert_the_idiom():
    # "burning up" (= fever) must not be read out of a heartburn description.
    assert not feature_present_with_aliases("fever", ["a burning sensation rising up behind my breastbone"])


def test_genuine_paraphrase_with_function_words_between_still_matches():
    assert feature_present_with_aliases("fever", ["I have been burning up all night"])
    assert feature_present_with_aliases("chest tightness", ["my chest is so tight"])


@pytest.mark.parametrize("text", ["my chest got tight", "my chest went tight during the meeting",
                                  "my chest feels tight", "the chest became tight", "my chest is so tight",
                                  "my chest felt really tight"])
def test_linking_verbs_do_not_break_a_body_part_and_its_state(text):
    assert feature_present_with_aliases("chest tightness", [text])


def test_aspectual_verbs_are_not_linking_verbs():
    # an external light that "keeps flashing" is not the visual symptom "flashing lights"
    assert not feature_present_with_aliases("aura", ["the dashboard light keeps flashing at me"])
    assert feature_present_with_aliases("aura", ["I saw flashing lights in my vision"])


def test_routing_rejects_scattered_two_word_idioms_but_keeps_paraphrases():
    assert route("a burning feeling creeps up through my chest after dinner").primary_tag != "fever"
    assert route("burning in my chest after dinner").primary_tag == "chest_pain"
    assert route("before the exam my chest got tight").primary_tag == "chest_pain"
    assert route("my neck is really stiff today").primary_tag == "neck_stiffness"
    # phrasal-verb particles and quantifiers do not separate an action from its object
    assert route("I coughed up some blood overnight").primary_tag == "hemoptysis"


def test_proximity_rule_leaves_non_latin_script_unchanged():
    # Korean attaches particles to nouns ("머리가"), so word positions are not comparable; routing is unchanged.
    assert route("머리가 너무 아파요").primary_tag == "headache"


# --- negative beta-hCG -----------------------------------------------------------------------------------------

def _pelvic_state():
    s = PatientState(case_id="hcg", chief_complaint="cramping low on one side of my belly",
                     demographics={"age": 27, "sex": "female"})
    s.record_ask("associated_symptoms", "q", "my period is late and there is some spotting")
    return s


def _ectopic(state):
    return next(x for x in DifferentialEngine().update(state) if x.diagnosis_id == "ectopic_pregnancy")


def test_negative_pregnancy_test_is_evidence_against_ectopic_pregnancy():
    before = _ectopic(_pelvic_state())
    s = _pelvic_state()
    s.record_test("beta_hcg", "serum beta-hCG negative (<5 mIU/mL)")
    after = _ectopic(s)
    assert "positive beta-hCG" in after.contradictory_evidence
    assert after.score < before.score


def test_positive_pregnancy_test_still_supports_ectopic_pregnancy():
    s = _pelvic_state()
    s.record_test("beta_hcg", "serum beta-hCG positive, 1800 mIU/mL")
    assert "positive beta-hCG" not in _ectopic(s).contradictory_evidence


def test_negative_hcg_rule_out_is_switchable(switch):
    switch("NOVA_EVIDENCE_V2", "0")
    s = _pelvic_state()
    s.record_test("beta_hcg", "serum beta-hCG negative (<5 mIU/mL)")
    assert "positive beta-hCG" not in _ectopic(s).contradictory_evidence


def test_a_single_normal_troponin_does_not_contradict_acs():
    s = PatientState(case_id="trop", chief_complaint="pressure in my chest going down my left arm",
                     demographics={"age": 64, "sex": "male"})
    s.record_test("troponin", "high-sensitivity troponin within normal limits")
    acs = next((x for x in DifferentialEngine().update(s) if x.diagnosis_id == "acute_coronary_syndrome"), None)
    assert acs is not None
    assert not any("troponin" in c.lower() for c in acs.contradictory_evidence)


# --- lying / standing blood pressure ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("lying 132/84, standing 104/70", True),               # systolic fall 28
    ("BP supine 118/78; standing 112/64", True),           # diastolic fall 14
    ("lying down BP 128/80, standing BP 122/76", False),   # small physiological change
    ("128/80 lying, 126/82 standing", False),
    ("standing 120/80", False),                            # one posture only
    ("BP 140/90", False),
])
def test_orthostatic_drop_uses_the_consensus_thresholds(text, expected):
    assert orthostatic_drop(text) is expected


def test_orthostatic_drop_is_a_canonical_finding_only_when_present():
    assert "orthostatic drop in blood pressure" in canonical_findings_for("lying 130/80, standing 100/66 with dizziness")
    assert "orthostatic drop in blood pressure" not in canonical_findings_for("lying 130/80, standing 128/82")


# --- syncope / urinary concepts with negation ------------------------------------------------------------------

@pytest.mark.parametrize("text,concept", [
    ("I get woozy every time I stand up quickly", "lightheadedness on standing up"),
    ("everything went grey before I dropped", "prodrome of lightheadedness"),
    ("I came round within seconds", "rapid spontaneous recovery"),
    ("it stings when I pee", "dysuria"),
    ("going to the toilet constantly", "urinary frequency"),
])
def test_everyday_syncope_and_urinary_wording(text, concept):
    assert concept in canonical_findings_for(text)


@pytest.mark.parametrize("text,concept", [
    ("no burning when I pee", "dysuria"),
    ("not dizzy when I stand up", "lightheadedness on standing up"),
])
def test_negated_syncope_and_urinary_wording_is_ignored(text, concept):
    assert concept not in canonical_findings_for(text)


# --- action: blocking-danger workup ----------------------------------------------------------------------------

def _chest_state(with_history: bool):
    s = PatientState(case_id="act", chief_complaint="sudden pressure in my chest and short of breath",
                     demographics={"age": 58, "sex": "male"})
    if with_history:
        s.record_ask("onset", "q", "started an hour ago at rest")
        s.record_ask("associated_symptoms", "q", "sweaty and sick to my stomach")
        s.record_ask("past_medical_history", "q", "high blood pressure and I smoke")
    return s


def test_blocking_workup_is_withheld_until_core_history_is_taken():
    s = _chest_state(with_history=False)
    d = DifferentialEngine().update(s)
    assert ActionSelector._blocking_workup(s, d, []) == set()


def test_blocking_workup_lists_only_outstanding_actions_of_dangerous_alternatives():
    s = _chest_state(with_history=True)
    d = DifferentialEngine().update(s)
    blocking = ActionSelector._blocking_workup(s, d, [])
    done = set(s.completed_tests) | set(s.completed_examinations)
    assert not blocking & done
    from nova_agent.missing_info import _resolve_entry
    allowed = set()
    for item in d[1:5]:
        if item.dangerous_if_missed:
            entry = _resolve_entry(item.diagnosis_id) or {}
            allowed |= set(entry.get("minimum_workup") or (list(entry.get("discriminating_exams", []))
                                                           + list(entry.get("discriminating_tests", []))))
    assert blocking <= allowed


def test_action_switch_off_disables_the_bonus(switch):
    switch("NOVA_ACTION_V2", "0")
    s = _chest_state(with_history=True)
    d = DifferentialEngine().update(s)
    assert ActionSelector._blocking_workup(s, d, []) == set()
