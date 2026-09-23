"""Regression tests for the generalizable systemic-severity evidence layer (differential.py's
`_score_disease` + severity_evidence.py). Two things must both hold, always together:

  1. When real, objective physiologic derangement (shock, hypoxemia, marked tachycardia/tachypnea,
     high lactate, altered mental status) is actually present, a systemic dangerous syndrome must
     be able to outrank a localized diagnosis whose own specific findings would otherwise win
     (spec section 6/8: e.g. infection source + hypotension + confusion + high lactate -> sepsis
     must be able to beat plain pyelonephritis).
  2. The same mechanism must NOT fire on a stable patient -- a localized diagnosis with normal
     vitals, or a benign diagnosis with a reassuring exam, must keep winning cleanly (spec section
     9: no over-triggering of sepsis/stroke/PE/etc. across every patient just because the boost
     exists). These are the explicit negative controls the spec requires.

No case-specific "pyelonephritis -> sepsis" rule exists anywhere in the code under test -- the
severity layer only reads structured vitals/labs/exam text (nova_agent/severity_evidence.py) and
applies identically to every diagnosis the knowledge base flags `dangerous: true`.
"""

from __future__ import annotations

from nova_agent.differential import DifferentialEngine
from nova_agent.state import PatientState


def _make_state(case_id: str, chief_complaint: str, symptoms, vitals: str = None,
                 lactate: str = None, mental_status: str = None, age: int = 50, sex: str = "female"):
    state = PatientState(case_id=case_id, chief_complaint=chief_complaint,
                          demographics={"age": age, "sex": sex})
    state.symptoms = list(symptoms)
    if vitals:
        state.record_exam("vital_signs", vitals)
    if lactate:
        state.laboratory_tests["lactate"] = lactate
    if mental_status:
        state.physical_examinations["mental_status_exam"] = mental_status
    return state


def test_severe_derangement_lets_systemic_syndrome_outrank_localized_diagnosis():
    """Infection source + shock + confusion + high lactate: the systemic syndrome must win even
    though the localized diagnosis has its own strong, specific matches."""
    state = _make_state(
        "sev_pos", "flank pain and fever",
        ["flank pain", "fever", "chills", "costovertebral angle tenderness"],
        vitals="BP 76/48, HR 136, RR 30, Temp 39.3, SpO2 88%",
        lactate="Lactate 5.6 mmol/L",
        mental_status="confused, disoriented to time and place",
    )
    items = DifferentialEngine().update(state)
    assert items, "differential must never be empty"
    assert items[0].diagnosis_id == "sepsis", \
        f"expected sepsis to win with severe derangement present, got {items[0].diagnosis_id!r}"


def test_localized_infection_with_stable_vitals_does_not_trigger_sepsis():
    state = _make_state(
        "neg_localized", "flank pain and fever",
        ["flank pain", "fever", "costovertebral angle tenderness", "dysuria"],
        vitals="BP 122/78, HR 92, RR 16, Temp 38.4, SpO2 98%",
    )
    items = DifferentialEngine().update(state)
    assert items[0].diagnosis_id == "pyelonephritis", \
        f"stable vitals must not let sepsis win, got {items[0].diagnosis_id!r}"


def test_migraine_with_normal_neuro_exam_does_not_trigger_stroke_or_sah():
    state = _make_state(
        "neg_migraine", "throbbing one-sided headache",
        ["unilateral pulsating headache", "photophobia", "nausea"],
        vitals="BP 118/76, HR 78, RR 14, Temp 36.8, SpO2 99%",
    )
    state.physical_examinations["neuro_exam"] = "normal neuro exam, no focal deficits"
    items = DifferentialEngine().update(state)
    assert items[0].diagnosis_id == "migraine", \
        f"a reassuring exam must not let a dangerous mimic win, got {items[0].diagnosis_id!r}"


def test_mild_asthma_with_normal_oxygenation_does_not_trigger_anaphylaxis():
    state = _make_state(
        "neg_asthma", "wheezing and shortness of breath",
        ["wheeze", "mild dyspnea", "known asthma"],
        vitals="BP 120/80, HR 88, RR 18, Temp 37.0, SpO2 97%",
    )
    items = DifferentialEngine().update(state)
    assert items[0].diagnosis_id == "asthma_copd_exacerbation", \
        f"normal oxygenation must not let anaphylaxis win, got {items[0].diagnosis_id!r}"
    # The invariant this file actually exists to check: with fully normal vitals, the severity
    # layer must contribute nothing at all -- it never has an opinion of its own to inject here.
    from nova_agent.severity_evidence import systemic_severity_signals
    assert systemic_severity_signals(state) == []


def test_simple_gastroenteritis_with_stable_circulation_does_not_trigger_severe_diagnosis():
    state = _make_state(
        "neg_gastro", "vomiting and diarrhea",
        ["vomiting", "watery diarrhea", "abdominal cramping"],
        vitals="BP 110/70, HR 90, RR 16, Temp 37.5, SpO2 99%",
    )
    items = DifferentialEngine().update(state)
    assert items[0].diagnosis_id == "gastroenteritis", \
        f"stable circulation must not let a severe diagnosis win, got {items[0].diagnosis_id!r}"
