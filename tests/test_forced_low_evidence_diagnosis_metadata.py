"""Round E: a forced/zero-evidence diagnosis must never look like a confidently evidence-supported
NORMAL_DIAGNOSIS. Tests PatientState's three independent quality flags (forced_due_to_turn_limit,
zero_evidence_at_diagnosis, fallback_candidate_selected), how orchestrator.DoctorAgent.decide()
stages them, and how competition/adapter.py surfaces them (always in metadata; only relabels the
wire action_type when explicitly configured to).
"""

from __future__ import annotations

from nova_agent.orchestrator import DoctorAgent
from nova_agent.state import PatientState


def test_normal_diagnosis_has_all_flags_false():
    state = PatientState(case_id="c1", chief_complaint="crushing chest pressure radiating to my left arm, sweating",
                          demographics={"age": 58, "sex": "male"})
    agent = DoctorAgent()
    action = None
    for _ in range(40):
        action, _llm_output, _diff = agent.decide(state)
        if action.action_type == "DIAGNOSE":
            agent.observe(state, action, "")
            break
        agent.observe(state, action, "Denies that symptom, nothing else to add.")
    assert action.action_type == "DIAGNOSE"
    assert state.final_diagnosis_forced_due_to_turn_limit is False
    assert state.final_diagnosis_zero_evidence_at_diagnosis is False
    assert state.final_diagnosis_fallback_candidate_selected is False


def test_forced_zero_evidence_diagnosis_has_all_flags_true():
    state = PatientState(case_id="c2", chief_complaint="xyzzy plugh wobblefritz", demographics={"age": 40, "sex": "female"})
    state.turn_count = 58  # near the turn budget
    agent = DoctorAgent()
    action, _llm_output, _diff = agent.decide(state)
    agent.observe(state, action, "")
    assert action.action_type == "DIAGNOSE"
    assert state.final_diagnosis_forced_due_to_turn_limit is True
    assert state.final_diagnosis_zero_evidence_at_diagnosis is True
    assert state.final_diagnosis_fallback_candidate_selected is True


def test_pending_diagnosis_quality_is_cleared_after_record_diagnose():
    state = PatientState(case_id="c3", chief_complaint="xyzzy plugh wobblefritz", demographics={"age": 40, "sex": "female"})
    state.turn_count = 58
    agent = DoctorAgent()
    action, _llm_output, _diff = agent.decide(state)
    assert state.pending_diagnosis_quality is not None
    agent.observe(state, action, "")
    assert state.pending_diagnosis_quality is None


def test_non_diagnose_action_never_sets_pending_diagnosis_quality():
    state = PatientState(case_id="c4", chief_complaint="chest pain", demographics={"age": 58, "sex": "male"})
    agent = DoctorAgent()
    action, _llm_output, _diff = agent.decide(state)
    assert action.action_type != "DIAGNOSE"
    assert state.pending_diagnosis_quality is None


def test_competition_adapter_always_exposes_diagnosis_quality_metadata():
    from competition.adapter import NovaCompetitionAgent

    agent = NovaCompetitionAgent()
    obs = {"case_id": "c5", "turn": 0, "observation_type": "initial",
           "chief_complaint": "xyzzy plugh wobblefritz", "demographics": {"age": 40, "sex": "female"},
           "max_turns": 3}
    result = agent.act(obs)
    assert result["action_type"] == "DIAGNOSE"
    quality = result["metadata"]["diagnosis_quality"]
    assert quality["forced_due_to_turn_limit"] is True
    assert quality["zero_evidence_at_diagnosis"] is True


def test_competition_adapter_ignores_unofficial_fifth_action_flag(monkeypatch):
    import dataclasses

    from nova_agent import config as config_module
    import competition.adapter as adapter_module

    patched = dataclasses.replace(config_module.get_config(), competition_supports_insufficient_information=True)
    monkeypatch.setattr(config_module, "_config", patched)
    agent = adapter_module.NovaCompetitionAgent()
    obs = {"case_id": "c6", "turn": 0, "observation_type": "initial",
           "chief_complaint": "xyzzy plugh wobblefritz", "demographics": {"age": 40, "sex": "female"},
           "max_turns": 3}
    result = agent.act(obs)
    assert result["action_type"] == "DIAGNOSE"


def test_competition_adapter_does_not_treat_repeated_denials_as_supported_diagnosis(monkeypatch):
    import dataclasses

    from nova_agent import config as config_module
    import competition.adapter as adapter_module

    patched = dataclasses.replace(config_module.get_config(), competition_supports_insufficient_information=True)
    monkeypatch.setattr(config_module, "_config", patched)
    agent = adapter_module.NovaCompetitionAgent()
    obs = {"case_id": "c7", "turn": 0, "observation_type": "initial",
           "chief_complaint": "crushing chest pressure radiating to my left arm, sweating",
           "demographics": {"age": 58, "sex": "male"}, "max_turns": 60}
    result = agent.act(obs)
    turns = 0
    while result["action_type"] not in ("DIAGNOSE", "INSUFFICIENT_INFORMATION") and turns < 40:
        obs = {"case_id": "c7", "turn": turns + 1, "observation_type": "ask_response",
               "content": "Denies that symptom, nothing else to add."}
        result = agent.act(obs)
        turns += 1
    assert result["action_type"] == "DIAGNOSE"
    assert result["metadata"]["internal_result"] == "INSUFFICIENT_INFORMATION"


def test_objectively_supported_diagnosis_retains_diagnose_wire_label(monkeypatch):
    import dataclasses
    from nova_agent import config as config_module
    from competition.adapter import action_to_competition
    monkeypatch.setattr(config_module, "_config", dataclasses.replace(
        config_module.get_config(), competition_supports_insufficient_information=True))
    agent = DoctorAgent()
    state = agent.new_case("supported", "Substernal pressure radiating to jaw with diaphoresis", max_turns=1)
    state.record_test("ecg", "ST elevation")
    state.record_test("troponin", "elevated troponin")
    action, _, _ = agent.decide(state)
    wire = action_to_competition("supported", action, diagnosis_quality=state.pending_diagnosis_quality,
                                evidence_assessment=state.evidence_assessment)
    assert wire.action_type == "DIAGNOSE"
    assert wire.metadata["internal_result"] == "SUPPORTED_DIAGNOSIS"
    assert wire.metadata["forced_due_to_protocol"] is False
