"""Regression tests proving diagnostic_score and severity_score stay on separate axes
(differential.py's `_score_disease` for the former, severity_evidence.py's `severity_score` for
the latter, consumed only by stop_policy.py -- see both modules' docstrings for the full
rationale). Two things must both hold, always together:

  1. When a diagnosis has real DISEASE-SPECIFIC evidence (its own typical_features/confirmatory_
     findings actually present, e.g. sepsis's own "fever"/"tachycardia"/"hypotension"/"altered
     mental status" typical_features plus a numeric elevated-lactate confirmatory finding), it can
     still outrank a localized diagnosis whose own specific findings would otherwise win -- but
     through ITS OWN evidence, never a generic severity bonus applied identically to every
     dangerous diagnosis regardless of whether that diagnosis's own findings are present.
  2. A diagnosis must NOT win, or be treated as an active unresolved alternative, just because the
     patient looks generically sick (marked vitals derangement alone, with no disease-specific
     evidence for that diagnosis at all) -- a localized diagnosis with normal vitals, or a benign
     diagnosis with a reassuring exam, must keep winning cleanly. No over-triggering of sepsis/
     stroke/PE/anaphylaxis/etc. across every patient just because SOME severity signal exists
     somewhere. These are the explicit negative controls the spec requires.

No case-specific "pyelonephritis -> sepsis" rule exists anywhere in the code under test -- sepsis
wins the positive case below through its own KB-declared evidence (typical_features + a numeric
lactate confirmatory finding), not a disease-name check.
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


def test_simple_cystitis_with_normal_vitals_does_not_trigger_sepsis():
    state = _make_state(
        "neg_cystitis", "burning when I pee",
        ["dysuria", "urinary frequency"],
        vitals="BP 118/74, HR 78, RR 14, Temp 37.0, SpO2 99%",
    )
    items = DifferentialEngine().update(state)
    assert items[0].diagnosis_id == "uncomplicated_cystitis", \
        f"normal vitals must not let sepsis win, got {items[0].diagnosis_id!r}"


def test_mild_pneumonia_with_stable_vitals_does_not_trigger_sepsis():
    state = _make_state(
        "neg_pneumonia", "cough and fever",
        ["productive cough", "fever", "pleuritic chest pain"],
        vitals="BP 118/76, HR 92, RR 20, Temp 38.2, SpO2 96%",
    )
    items = DifferentialEngine().update(state)
    assert items[0].diagnosis_id == "pneumonia", \
        f"stable vitals must not let sepsis win over a mild pneumonia, got {items[0].diagnosis_id!r}"


def test_severity_score_never_appears_in_diagnostic_ranking_directly():
    """A diagnosis with strong, specific evidence of its own (ACS: crushing chest pain radiating
    to the arm, diaphoresis, ST changes, elevated troponin) must keep winning even when the
    patient's vitals ALSO happen to satisfy some of sepsis's own (vitals-phrased) typical_features
    incidentally -- no fever here at all, so sepsis has only weak, partial, non-infection evidence
    of its own. Severity_score is high (shock physiology), but that must never be enough on its own
    to override a diagnosis with genuinely stronger, disease-specific support."""
    state = _make_state(
        "neg_severity_alone", "crushing chest pain radiating to my left arm",
        ["crushing chest pain", "diaphoresis", "pain radiates to my left arm", "nausea"],
        vitals="BP 78/50, HR 138, RR 30, Temp 37.0, SpO2 88%",
    )
    state.laboratory_tests["ecg"] = "ST elevation in the anterior leads"
    state.laboratory_tests["troponin"] = "markedly elevated troponin"
    items = DifferentialEngine().update(state)
    assert items, "differential must never be empty"
    assert items[0].diagnosis_id == "acute_coronary_syndrome", \
        (f"ACS's own strong specific evidence must win over sepsis's incidental vitals-only "
         f"overlap (no fever, no infection source), got {items[0].diagnosis_id!r}")
