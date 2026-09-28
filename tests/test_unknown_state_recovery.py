"""The zero-evidence/UNKNOWN_PRESENTATION fallback (see test_zero_evidence_unknown_fallback.py) must
be a genuinely TRANSIENT state, not a trap: once real symptom/risk/objective evidence is elicited
(e.g. the agent's own follow-up ASK gets an informative answer), the differential must snap back to
normal evidence-based scoring on the very next turn, with `fallback_candidate` no longer set and a
real top diagnosis reachable via a genuine `symptom_match`/`risk_match`/`objective_finding` source --
never permanently stuck reporting UNKNOWN_PRESENTATION once the presentation is no longer actually
unknown.
"""

from __future__ import annotations

from nova_agent.differential import DifferentialEngine
from nova_agent.state import PatientState
from nova_agent.stop_policy import StopPolicy


def test_zero_evidence_state_recovers_once_real_evidence_is_elicited():
    state = PatientState(case_id="recovery-test", chief_complaint="zonkulated feeling, hard to describe",
                          demographics={"age": 30, "sex": "female"})

    # Turn 1: genuinely nothing matches anything.
    first_differential = DifferentialEngine().update(state)
    assert first_differential and first_differential[0].fallback_candidate is True
    first_decision = StopPolicy().evaluate(state, first_differential, safety_findings=[], best_info_gain=0.0)
    assert first_decision.should_diagnose is False

    # Turn 2: a genuinely informative answer comes in (unambiguous, specific clinical content).
    state.record_ask("associated_symptoms", "any other symptoms?",
                      "runny nose and a sore throat, started two days ago")

    second_differential = DifferentialEngine().update(state)
    assert second_differential, "must still produce a differential after real evidence arrives"
    top = second_differential[0]
    assert top.fallback_candidate is False, "must no longer be flagged as a zero-evidence fallback"
    assert top.score > 0.0
    assert set(top.candidate_sources) != {"zero_evidence_fallback"}
    assert any(source in top.candidate_sources for source in
               ("symptom_match", "risk_match", "objective_finding", "medication_match", "history_match"))
