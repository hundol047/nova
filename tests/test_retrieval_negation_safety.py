"""Explicit negative evidence ("denies fever", "no focal deficit") must never behave as a positive
retrieval signal. The retrieval pipeline itself does no negation parsing -- it reuses
clinical_presentation.build_clinical_presentation(), which already scans ONLY positive-evidence
PatientState fields (chief_complaint/symptoms/associated_symptoms/pertinent_positives) and
deliberately excludes pertinent_negatives/raw unsegmented history text (see that function's own
docstring). These tests prove the guarantee holds end-to-end through the actual retrieval call
site, not just at the ClinicalPresentation layer."""

from __future__ import annotations

from nova_agent.clinical_presentation import build_clinical_presentation
from nova_agent.retrieval_pipeline import build_signal_queries
from nova_agent.state import PatientState


def test_pertinent_negatives_never_enter_the_retrieval_signals():
    state = PatientState(case_id="negation-test", chief_complaint="chest pain")
    state.pertinent_negatives.extend(["fever", "focal neurologic deficit", "dyspnea"])
    state.pertinent_positives.extend(["chest pain radiating to the arm"])

    presentation = build_clinical_presentation(state)
    queries = build_signal_queries(
        chief_complaint=state.chief_complaint, symptoms=presentation.symptoms,
        history_risk=presentation.risk_factors,
    )
    all_query_text = " ".join(text for _signal, text in queries).lower()

    for negated_term in ("fever", "focal neurologic deficit"):
        assert negated_term not in all_query_text, (
            f"a pertinent-negative term {negated_term!r} leaked into a positive retrieval query"
        )


def test_a_denied_symptom_absorbed_from_a_free_text_answer_does_not_become_a_positive_signal():
    """Mirrors how a real turn works: the patient's answer is absorbed through
    PatientState.record_ask() -> _absorb_answer()'s existing negation-aware clause classification,
    not typed directly into pertinent_negatives/positives."""
    state = PatientState(case_id="negation-test-2", chief_complaint="abdominal pain")
    state.record_ask("associated_symptoms", "Any other symptoms?",
                      "denies fever, denies vomiting; has nausea")

    assert "fever" not in " ".join(state.pertinent_positives).lower()
    assert any("nausea" in p.lower() for p in state.pertinent_positives)

    presentation = build_clinical_presentation(state)
    queries = build_signal_queries(
        chief_complaint=state.chief_complaint, symptoms=presentation.symptoms,
        history_risk=presentation.risk_factors,
    )
    all_query_text = " ".join(text for _signal, text in queries).lower()
    assert "fever" not in all_query_text
    assert "vomiting" not in all_query_text


def test_objective_finding_phrases_are_caller_supplied_not_derived_from_raw_negated_text():
    """The objective_finding_phrases signal is built by candidate_generator.py from
    ObjectiveFinding.evidence_label for ABNORMAL findings only (see its own call site) -- this
    test locks in that build_signal_queries() itself performs no interpretation of raw text, so a
    caller who (correctly) filters out normal/unknown findings before calling it can never have a
    negative finding smuggled in through this signal either."""
    queries = build_signal_queries(
        chief_complaint="", objective_finding_phrases=["elevated troponin", "critical_high potassium"],
    )
    assert queries == [("objective_finding", "elevated troponin critical_high potassium")]
