"""Round N: clinical concept normalisation (nova_agent/clinical_concepts.py) and the peritoneal-sign data fix.

Fresh wording written for this file (not copied from any evaluation case). Covers: different wordings of the
same finding, negation, past history, concepts that must stay distinct, numeric/unit-free safety, and the effect
on ranking and on the final-label abstention guard."""
import pytest

from nova_agent.clinical_concepts import canonical_findings_for
from nova_agent.differential import DifferentialEngine, has_required_diagnostic_context
from nova_agent.state import PatientState


@pytest.mark.parametrize("text,concept", [
    ("examiner notes meningismus", "neck stiffness"), ("Kernig sign positive", "neck stiffness"),
    ("he can't bend his neck forward", "neck stiffness"), ("my neck has gone rigid", "neck stiffness"),
    ("lights hurt so I keep the room dark", "photophobia"), ("she cannot tolerate light", "photophobia"),
    ("spinal fluid turbid", "CSF pleocytosis"), ("CSF shows raised white cell count", "CSF pleocytosis"),
    ("my period is overdue", "missed period"), ("last period was seven weeks ago", "missed period"),
    ("I haven't had my period this month", "missed period"), ("a little spotting today", "vaginal bleeding"),
    ("poo is black like tar", "melena"), ("tarry bowel movements since Monday", "melena"),
    ("blood on the toilet paper and in my stool", "hematochezia"), ("vomiting blood this morning", "hematemesis"),
    ("I keep struggling to find the words", "aphasia"), ("his speech is slurred", "slurred speech"),
    ("her smile looks crooked", "facial droop"), ("I get winded on the stairs", "shortness of breath"),
    ("I could barely breathe last night", "shortness of breath"),
])
def test_different_wordings_reach_the_same_canonical_finding(text, concept):
    assert concept in canonical_findings_for(text)


@pytest.mark.parametrize("text,concept", [
    ("no neck stiffness", "neck stiffness"), ("denies photophobia or light sensitivity", "photophobia"),
    ("denies black or tarry stools", "melena"), ("no blood in the stool", "hematochezia"),
    ("not vomiting blood", "hematemesis"), ("no spotting", "vaginal bleeding"),
    ("history of black stools years ago from an ulcer", "melena"), ("had a stiff neck as a child", "neck stiffness"),
    ("I am not short of breath and can breathe fine", "shortness of breath"),
])
def test_negated_or_historical_statements_never_create_a_current_finding(text, concept):
    assert concept not in canonical_findings_for(text)


def test_distinct_concepts_are_not_merged():
    assert canonical_findings_for("words come out jumbled") == ["aphasia"]
    assert canonical_findings_for("speech is slurred") == ["slurred speech"]
    assert canonical_findings_for("black tarry stools") == ["melena"]
    assert canonical_findings_for("maroon stools") == ["hematochezia"]


def test_mixed_clause_keeps_only_the_positive_concept():
    found = canonical_findings_for("no neck stiffness, but light really hurts my eyes")
    assert "photophobia" in found and "neck stiffness" not in found


def test_numbers_and_unrelated_text_produce_nothing():
    for text in ("BP 120/80, HR 72", "glucose 5.4 mmol/L", "period of observation was 2 hours", "stool softener taken"):
        assert canonical_findings_for(text) == []


def _top(state):
    return DifferentialEngine().update(state)


def test_meningeal_exam_wording_supports_meningitis_and_its_final_label_guard():
    s = PatientState(case_id="t1", chief_complaint="fever and a bad headache", demographics={"age": 22, "sex": "male"})
    s.record_exam("meningeal_signs", "nuchal rigidity with a positive Brudzinski sign")
    d = _top(s)
    men = next(x for x in d if x.diagnosis_id == "meningitis")
    assert "neck stiffness" in men.supporting_evidence
    assert has_required_diagnostic_context(men, s)


def test_late_period_with_spotting_keeps_ectopic_pregnancy_ranked_above_orthostasis():
    s = PatientState(case_id="t2", chief_complaint="my period is overdue and I have spotting",
                     demographics={"age": 29, "sex": "female"})
    s.record_ask("associated_symptoms", "q", "lightheaded when I stand up")
    ranked = [x.diagnosis_id for x in _top(s)]
    assert "ectopic_pregnancy" in ranked
    assert ranked.index("ectopic_pregnancy") < ranked.index("orthostatic_hypotension") if "orthostatic_hypotension" in ranked else True


def test_negated_bleeding_wording_does_not_create_gi_bleeding_evidence():
    s = PatientState(case_id="t3", chief_complaint="tired all week", demographics={"age": 60, "sex": "male"})
    s.record_ask("associated_symptoms", "q", "denies black stools, no blood in stool")
    gi = next((x for x in _top(s) if x.diagnosis_id == "gi_bleeding"), None)
    assert gi is None or not {"melena", "hematochezia"} & set(gi.supporting_evidence)


def test_diffuse_peritonitis_is_not_appendicitis_confirmatory_but_rlq_rebound_still_is():
    diffuse = PatientState(case_id="t4", chief_complaint="sudden severe abdominal pain", demographics={"age": 75, "sex": "female"})
    diffuse.record_exam("abdominal_exam", "board-like rigidity with diffuse rebound tenderness")
    order = [x.diagnosis_id for x in _top(diffuse)]
    assert "acute_abdomen" in order
    assert "appendicitis" not in order or order.index("acute_abdomen") < order.index("appendicitis")
    local = PatientState(case_id="t5", chief_complaint="pain moved to the right lower belly", demographics={"age": 20, "sex": "male"})
    local.record_exam("abdominal_exam", "rebound tenderness in the right lower quadrant")
    app = next(x for x in _top(local) if x.diagnosis_id == "appendicitis")
    assert "right lower quadrant rebound tenderness" in app.supporting_evidence


def test_switch_off_reproduces_the_previous_behaviour(monkeypatch):
    from nova_agent.config import get_config
    monkeypatch.setenv("NOVA_CONCEPT_NORMALIZATION", "0")
    get_config(reload=True)
    try:
        s = PatientState(case_id="t6", chief_complaint="poo is black like tar")
        assert "melena" not in s.all_findings_text()
    finally:
        monkeypatch.delenv("NOVA_CONCEPT_NORMALIZATION")
        get_config(reload=True)
