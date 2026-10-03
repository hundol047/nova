"""ActionSelector: a candidate action that helps discriminate a time-critical diagnosis
(stroke/ACS/sepsis/anaphylaxis-class -- derived generically from the knowledge base's own
urgency=="CRITICAL" + dangerous:true fields, never a hand-picked benchmark-specific list) gets a
small additional priority bonus over an otherwise-identical candidate that doesn't. Purely a
question/test PRIORITIZATION weight -- never triggers, implies, or is read as a treatment
directive of any kind.
"""

from __future__ import annotations

from nova_agent.action_selector import ActionSelector, _time_critical_ids
from nova_agent.missing_info import CandidateInfo


def test_time_critical_ids_are_kb_critical_dangerous_diagnoses():
    ids = _time_critical_ids()
    # Textbook "time is tissue/brain/myocardium" categories must be included.
    for expected in ("ischemic_stroke", "acute_coronary_syndrome", "sepsis", "anaphylaxis"):
        assert expected in ids
    # A non-dangerous, non-critical diagnosis must never be included.
    assert "viral_uri" not in ids
    assert "migraine" not in ids


def test_time_critical_candidate_gets_higher_utility_than_otherwise_identical_non_critical_one():
    selector = ActionSelector()
    base_kwargs = dict(
        action_type="TEST", key="ecg", content_en="Order ECG", content_ko="심전도 시행",
        diagnostic_discrimination=0.5, safety_relevance=0.0, information_gain=0.5,
        redundancy=0.0, turn_cost=1,
    )
    time_critical_cand = CandidateInfo(disease_ids_discriminated=["acute_coronary_syndrome"], **base_kwargs)
    non_critical_cand = CandidateInfo(disease_ids_discriminated=["viral_uri"], **base_kwargs)

    tc_utility, tc_components = selector._utility(time_critical_cand, dangerous_involved=True,
                                                    time_critical_involved=True, differential=[])
    nc_utility, nc_components = selector._utility(non_critical_cand, dangerous_involved=False,
                                                    time_critical_involved=False, differential=[])

    assert tc_components["time_critical_bonus"] == 1.0
    assert nc_components["time_critical_bonus"] == 0.0
    assert tc_utility > nc_utility


def test_time_critical_bonus_never_appears_on_a_diagnose_action():
    """The bonus is computed only inside _utility(), which is never called for the DIAGNOSE
    candidate itself (generate_and_select builds that one separately from stop_decision.readiness_score
    alone) -- so it can only ever influence WHICH question/test is asked next, never a diagnosis or
    treatment choice."""
    import inspect

    source = inspect.getsource(ActionSelector.generate_and_select)
    diagnose_line = next(l for l in source.splitlines() if "diagnose_candidate = ScoredCandidate" in l)
    assert "time_critical" not in diagnose_line
