"""Round Q: a documented diagnosis counts only when it is a CURRENT, PATIENT, clinician-reported, PRESENT mention.

Inputs reproduce the technical review's contrast table (the first twelve rows) plus new minimal pairs. These are
development regression cases (they were analysed while fixing), not an independent evaluation.
"""
import pytest

from nova_agent.config import get_config
from nova_agent.differential import DifferentialEngine
from nova_agent.documented_diagnosis import _name_index, documented_diagnosis_ids, documented_diagnosis_mentions
from nova_agent.state import PatientState

_IDS = dict(_name_index())
AF, PE, PNA = _IDS["atrial fibrillation"], _IDS["pulmonary embolism"], _IDS["pneumonia"]
SVT = _IDS["supraventricular tachycardia"]

CASES = [
    # --- review table -------------------------------------------------------------------------------------------
    ("The referral letter says atrial fibrillation was excluded", []),
    ("진단서에 atrial fibrillation 아니라고 적혀 있습니다", []),
    ("The referral letter says atrial fibrillation was ruled out", []),
    ("The letter says pulmonary embolism cannot be excluded", []),
    ("The letter confirms atrial fibrillation but excludes pulmonary embolism", [AF]),
    ("The letter confirms atrial fibrillation; the patient has no fever", [AF]),
    ("The letter says atrial fibrillation but pulmonary embolism was excluded", [AF]),
    ("The letter says atrial fibrillation and I have no nausea", [AF]),
    ("My mother was diagnosed with atrial fibrillation yesterday", []),
    ("The specialist letter states atrial fibrillation was present in 2016", []),
    ("진단서에 atrial fibrillation 의심된다고 적혀 있습니다", []),
    ("진단서에 atrial fibrillation 배제할 수 없다고 적혀 있습니다", []),
    # --- new minimal pairs --------------------------------------------------------------------------------------
    ("The clinic note confirms supraventricular tachycardia.", [SVT]),
    ("The clinic note excludes supraventricular tachycardia.", []),
    ("The clinic note says pulmonary embolism is not ruled out.", []),
    ("The clinic note says pulmonary embolism is ruled out.", []),
    ("The note confirms atrial fibrillation and denies nausea.", [AF]),
    ("The note denies pulmonary embolism and confirms atrial fibrillation.", [AF]),
    ("I was diagnosed with pneumonia.", [PNA]),
    ("My father was diagnosed with pneumonia.", []),
    ("The note records atrial fibrillation in 2018.", []),
    ("The note confirms current atrial fibrillation.", [AF]),
    ("진단서에 atrial fibrillation이 없다고 합니다.", []),
    ("진단서에 pulmonary embolism을 배제할 수 없다고 합니다.", []),
    ("진단서에 atrial fibrillation이라고 적혀 있어요.", [AF]),
    ("인터넷을 보고 제가 pneumonia라고 추측합니다.", []),
    ("The letter says atrial fibrillation was excluded but pulmonary embolism is confirmed.", [PE]),
    ("The letter confirms atrial fibrillation and pulmonary embolism.", [AF, PE]),
    ("The letter excludes atrial fibrillation and pulmonary embolism.", []),
    ("The letter says atrial fibrillation. A later letter says atrial fibrillation was excluded.", []),
    ("The letter says atrial fibrillation was excluded. The newer letter confirms atrial fibrillation.", [AF]),
    ("My wife says I was diagnosed with atrial fibrillation.", [AF]),
    ("My mother says the doctor diagnosed my brother with pneumonia.", []),
    ("I think it might be pneumonia.", []),
    ("The doctor said it could be pneumonia.", []),
    ("The discharge summary lists pneumonia.", [PNA]),
    ("The discharge summary lists no pneumonia.", []),
    ("The GP diagnosed pneumonia; I have no cough now.", [PNA]),
    ("My friend was diagnosed with pneumonia.", []),
    ("The letter says possible pulmonary embolism.", []),
    ("As a child I was diagnosed with pneumonia.", []),
    ("The letter says pulmonary embolism is unlikely.", []),
]


@pytest.mark.parametrize("text,expected", CASES)
def test_positive_documented_ids(text, expected):
    assert sorted(documented_diagnosis_ids([text])) == sorted(expected)


def _mention(text, cid):
    found = [m for m in documented_diagnosis_mentions([text]) if m.diagnosis_id == cid]
    assert found, (text, cid)
    return found[-1]


@pytest.mark.parametrize("text,cid,assertion,temporality,experiencer,source", [
    ("The referral letter says atrial fibrillation was excluded", AF, "NEGATED", "UNSPECIFIED", "UNSPECIFIED", "REPORTED_CLINICIAN"),
    ("The letter says pulmonary embolism cannot be excluded", PE, "UNCERTAIN", "UNSPECIFIED", "UNSPECIFIED", "REPORTED_CLINICIAN"),
    ("진단서에 atrial fibrillation 배제할 수 없다고 적혀 있습니다", AF, "UNCERTAIN", "UNSPECIFIED", "UNSPECIFIED", "REPORTED_CLINICIAN"),
    ("진단서에 atrial fibrillation 아니라고 적혀 있습니다", AF, "NEGATED", "UNSPECIFIED", "UNSPECIFIED", "REPORTED_CLINICIAN"),
    ("My mother was diagnosed with atrial fibrillation yesterday", AF, "PRESENT", "UNSPECIFIED", "FAMILY", "REPORTED_CLINICIAN"),
    ("The specialist letter states atrial fibrillation was present in 2016", AF, "PRESENT", "HISTORICAL", "UNSPECIFIED", "REPORTED_CLINICIAN"),
    ("The letter confirms atrial fibrillation but excludes pulmonary embolism", PE, "NEGATED", "UNSPECIFIED", "UNSPECIFIED", "REPORTED_CLINICIAN"),
    ("The letter confirms atrial fibrillation but excludes pulmonary embolism", AF, "PRESENT", "UNSPECIFIED", "UNSPECIFIED", "REPORTED_CLINICIAN"),
    ("My wife says I was diagnosed with atrial fibrillation.", AF, "PRESENT", "UNSPECIFIED", "PATIENT", "REPORTED_CLINICIAN"),
    ("인터넷을 보고 제가 pneumonia라고 추측합니다.", PNA, "UNCERTAIN", "UNSPECIFIED", "PATIENT", "PATIENT_SPECULATION"),
    ("The note confirms current atrial fibrillation.", AF, "PRESENT", "CURRENT", "UNSPECIFIED", "REPORTED_CLINICIAN"),
])
def test_mention_scope(text, cid, assertion, temporality, experiencer, source):
    m = _mention(text, cid)
    assert (m.assertion, m.temporality, m.experiencer, m.source) == (assertion, temporality, experiencer, source)


def test_spans_are_original_text_offsets():
    text = "The letter confirms atrial fibrillation but excludes pulmonary embolism"
    for m in documented_diagnosis_mentions([text]):
        name = text[m.mention_span[0]:m.mention_span[1]].lower()
        assert name in ("atrial fibrillation", "pulmonary embolism")
        assert m.evidence_span[0] <= m.mention_span[0] < m.mention_span[1] <= m.evidence_span[1]
    pe = _mention(text, PE)
    assert "excludes" in text[pe.evidence_span[0]:pe.evidence_span[1]]
    assert "confirms" not in text[pe.evidence_span[0]:pe.evidence_span[1]]


def test_conflicting_statements_are_both_kept():
    text = "The letter says atrial fibrillation. A later letter says atrial fibrillation was excluded."
    assertions = [m.assertion for m in documented_diagnosis_mentions([text]) if m.diagnosis_id == AF]
    assert assertions == ["PRESENT", "NEGATED"]


# --- DifferentialEngine integration ---------------------------------------------------------------------------

def _arrhythmia(chief_complaint):
    s = PatientState(case_id="dd", chief_complaint=chief_complaint, demographics={"age": 64, "sex": "male"})
    return s, next((d for d in DifferentialEngine().update(s) if d.diagnosis_id == AF), None)


@pytest.mark.parametrize("cc", [
    "The referral letter says atrial fibrillation was excluded",
    "진단서에 atrial fibrillation 아니라고 적혀 있습니다",
    "The letter says atrial fibrillation cannot be excluded",
    "My mother was diagnosed with atrial fibrillation yesterday",
    "The specialist letter states atrial fibrillation was present in 2016",
])
def test_non_positive_mentions_add_no_support_or_source(cc):
    _, item = _arrhythmia(cc)
    if item is not None:
        assert "documented diagnosis" not in item.supporting_evidence
        assert "documented_diagnosis" not in item.candidate_sources
        assert "documented diagnosis" not in item.contradictory_evidence  # not turned into a negative result either


def test_positive_mention_survives_a_denied_symptom_in_another_clause():
    _, item = _arrhythmia("The letter says atrial fibrillation and I have no nausea")
    assert item is not None and "documented diagnosis" in item.supporting_evidence
    assert "documented_diagnosis" in item.candidate_sources


def test_answer_text_is_read_whole_not_as_negation_split_fragments():
    s = PatientState(case_id="dd2", chief_complaint="I keep feeling my heart flutter", demographics={"age": 64, "sex": "male"})
    s.record_ask("past_medical_history", "Any past illnesses?", "The letter confirms atrial fibrillation but excludes pulmonary embolism")
    ranked = {d.diagnosis_id: d for d in DifferentialEngine().update(s)}
    assert "documented diagnosis" in ranked[AF].supporting_evidence
    assert PE not in ranked or "documented diagnosis" not in ranked[PE].supporting_evidence


def test_clinician_report_is_not_promoted_to_an_objective_result():
    s, item = _arrhythmia("The letter confirms atrial fibrillation")
    assert item is not None and "irregularly irregular rhythm" not in item.supporting_evidence
    assert not s.physical_examinations and not s.laboratory_tests


def test_switch_off_disables_documented_support(monkeypatch):
    monkeypatch.setenv("NOVA_DOCUMENTED_DX", "0")
    get_config(reload=True)
    try:
        assert documented_diagnosis_ids(["The letter confirms atrial fibrillation"]) == []
    finally:
        monkeypatch.delenv("NOVA_DOCUMENTED_DX")
        get_config(reload=True)
