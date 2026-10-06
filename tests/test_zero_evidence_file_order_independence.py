"""Regression test for the zero-evidence fallback file-order bug (Round D generalization-
hardening mandate): when literally NOTHING (no symptom concept, risk factor, medication, history,
imaging, or objective lab) matches anything, candidate_generator.py's `if not pool:` branch falls
back to the untargeted whole catalog. Before this round's fix, differential.py's stable sort left
every candidate tied at score 0.0, so the ORIGINAL dict/list insertion order -- ultimately
`nova_agent/knowledge/diseases/*.json`'s alphabetical filename load order -- silently decided which
diagnosis "won" (confirmed real: the first 5 diseases in that load order won 3 unrelated blind-set
zero-evidence presentations in the Blind v13 first run).

This test proves the fix generically, without ever asserting which diagnosis "wins": it feeds the
SAME zero-evidence presentation through the differential/stop-policy pipeline twice, with the
underlying disease catalog's iteration order reversed between runs (simulating a different file
load order), and asserts the CLINICAL CONCLUSION is identical either way -- every candidate is
correctly marked `fallback_candidate=True`, and StopPolicy refuses to DIAGNOSE in both orders.
Never asserts a specific "rank 1" diagnosis: with genuinely zero evidence, no such ranking is
clinically meaningful, and asserting one would silently reintroduce exactly the bug this test
guards against.
"""

from __future__ import annotations

import nova_agent.candidate_generator as candidate_generator_module
from nova_agent.differential import DifferentialEngine
from nova_agent.state import PatientState
from nova_agent.stop_policy import StopPolicy


def _zero_evidence_state() -> PatientState:
    # Nonsense chief complaint: routes to no chief-complaint tag, matches no symptom concept, no
    # risk factor, no medication, no history, no imaging, no objective lab -- guaranteed to hit
    # candidate_generator.py's whole-catalog `if not pool:` fallback on turn one.
    return PatientState(case_id="zero-evidence-order-test", chief_complaint="xyzzy plugh wobblefritz",
                         demographics={"age": 40, "sex": "female"})


def _run_with_disease_order(monkeypatch, reversed_order: bool) -> tuple:
    from nova_agent.knowledge.retrieval import all_diseases as real_all_diseases

    real = real_all_diseases()
    ordered_items = list(reversed(real.items())) if reversed_order else list(real.items())
    reordered = dict(ordered_items)
    assert set(reordered) == set(real), "reordering must not add or drop any disease"

    monkeypatch.setattr(candidate_generator_module, "all_diseases", lambda: reordered)

    state = _zero_evidence_state()
    differential = DifferentialEngine().update(state)
    stop_decision = StopPolicy().evaluate(state, differential, safety_findings=[], best_info_gain=0.0)
    return differential, stop_decision


def test_zero_evidence_conclusion_identical_regardless_of_disease_file_load_order(monkeypatch):
    forward_differential, forward_stop = _run_with_disease_order(monkeypatch, reversed_order=False)
    reversed_differential, reversed_stop = _run_with_disease_order(monkeypatch, reversed_order=True)

    # The clinical CONCLUSION -- never diagnose, everything is an explicit zero-evidence fallback
    # candidate -- must hold identically regardless of load order.
    assert forward_differential, "must still produce a differential (never an empty one)"
    assert reversed_differential, "must still produce a differential (never an empty one)"
    assert all(d.fallback_candidate for d in forward_differential)
    assert all(d.fallback_candidate for d in reversed_differential)
    assert all(d.confidence_band == "LOW" for d in forward_differential)
    assert all(d.confidence_band == "LOW" for d in reversed_differential)
    assert all(d.score == 0.0 for d in forward_differential)
    assert all(d.score == 0.0 for d in reversed_differential)

    assert forward_stop.should_diagnose is False
    assert reversed_stop.should_diagnose is False
    assert "UNKNOWN_PRESENTATION" in forward_stop.reason
    assert "UNKNOWN_PRESENTATION" in reversed_stop.reason

    # `differential` is truncated to the fixed legacy top_k (5) -- WHICH 5 tied-at-zero entries
    # survive that truncation legitimately depends on order (there is no principled way to break a
    # genuine 0.0/0.0/.../0.0 tie), so it is not itself an order-invariant set. The real invariant
    # ("file order never changes the clinical CONCLUSION") is proven above: fallback_candidate/LOW/
    # score==0.0/should_diagnose==False hold for EVERY entry regardless of order. What must stay
    # order-independent is the underlying CANDIDATE POOL itself (nothing is silently dropped),
    # checked directly below via generate_candidates() before any top_k truncation.


def test_zero_evidence_candidate_pool_membership_identical_regardless_of_disease_file_load_order(monkeypatch):
    """Below the top_k truncation, the raw candidate pool itself (candidate_generator.py's
    whole-catalog fallback) must contain the exact same set of diagnoses regardless of the
    underlying disease dict's iteration order -- nothing is silently dropped just because of where
    in the (re-)ordered dict a disease happens to fall."""
    from nova_agent.candidate_generator import generate_candidates
    from nova_agent.clinical_presentation import build_clinical_presentation

    from nova_agent.knowledge.retrieval import all_diseases as real_all_diseases
    real = real_all_diseases()

    state = _zero_evidence_state()
    presentation = build_clinical_presentation(state)

    monkeypatch.setattr(candidate_generator_module, "all_diseases", lambda: real)
    forward_pool = generate_candidates(presentation)

    monkeypatch.setattr(candidate_generator_module, "all_diseases", lambda: dict(reversed(real.items())))
    reversed_pool = generate_candidates(presentation)

    assert {c.id for c in forward_pool} == {c.id for c in reversed_pool} == set(real)
    assert all(c.sources == ["zero_evidence_fallback"] for c in forward_pool)
    assert all(c.sources == ["zero_evidence_fallback"] for c in reversed_pool)


def test_zero_evidence_action_selector_never_diagnoses_regardless_of_disease_file_load_order(monkeypatch):
    from nova_agent.action_selector import ActionSelector

    for reversed_order in (False, True):
        differential, _ = _run_with_disease_order(monkeypatch, reversed_order)
        state = _zero_evidence_state()
        action, _, stop_decision = ActionSelector().generate_and_select(state, differential, safety_findings=[])
        assert action.action_type != "DIAGNOSE", (
            f"action_selector must never DIAGNOSE a zero-evidence presentation "
            f"(reversed_order={reversed_order}); got action={action.action_type} key={action.key}"
        )
        assert action.action_type in ("ASK", "EXAM"), (
            "with nothing yet elicited, the very first action must be a clarifying ASK/EXAM, "
            f"never a blind TEST (reversed_order={reversed_order}); got {action.action_type}"
        )
