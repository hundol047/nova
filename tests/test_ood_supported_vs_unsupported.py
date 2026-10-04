import pytest
from dataclasses import replace
from nova_agent import config as config_module
from competition.adapter import action_to_competition
from nova_agent.action_selector import AgentAction
from nova_agent.config import get_config
from nova_agent.differential import DifferentialItem
from nova_agent.orchestrator import DoctorAgent
from nova_agent.state import PatientState
from nova_agent.uncertainty import assess_evidence


def candidate(**kw):
    values = dict(diagnosis="Candidate", diagnosis_id="candidate", rank=1, score=0.1,
        score_ratio=0.01, urgency="HIGH", dangerous_if_missed=True, confidence_band="LOW",
        supporting_evidence=[], candidate_sources=["symptom_match"])
    return DifferentialItem(**dict(values, **kw))


@pytest.mark.parametrize("text", ["Sudden inability to speak", "A new severe headache", "숨이 차요",
    "Dysuria", "Fix the router; also I have chest pain", "プリンターの設定中に息苦しくなった"])
def test_sparse_critical_and_common_not_false_ood(text):
    state = PatientState(chief_complaint=text)
    assert assess_evidence(state, [candidate()]).internal_result == "INSUFFICIENT_INFORMATION"
    agent = DoctorAgent()
    action, _, _ = agent.decide(state)
    assert state.evidence_assessment["internal_result"] != "OUT_OF_DOMAIN"
    assert action.action_type != "DIAGNOSE"  # do not short circuit sparse cases before workup


def test_low_score_alone_is_never_ood_and_repeated_evidence_is_not_multiple_signals():
    state = PatientState(chief_complaint="An unusual sensation")
    d = candidate(supporting_evidence=["chest pressure", "chest pressure", "pressure"])
    assessment = assess_evidence(state, [d])
    assert assessment.internal_result == "INSUFFICIENT_INFORMATION"
    assert assessment.signals["meaningful_evidence_items"] == 1


def test_positive_objective_support_can_converge_but_contradictions_prevent_confident_output():
    state = PatientState(chief_complaint="chest pressure")
    d = candidate(score=8, supporting_evidence=["ST elevation", "elevated troponin"],
                  candidate_sources=["symptom_match", "objective_finding"])
    ds = [d, candidate(diagnosis_id="alternative", score=0)]
    assert assess_evidence(state, ds).internal_result == "SUPPORTED_DIAGNOSIS"
    d.contradictory_evidence = ["negative troponin"]
    assert assess_evidence(state, ds).internal_result == "INSUFFICIENT_INFORMATION"
    d.contradictory_evidence = []
    assert assess_evidence(state, ds, "llm_unverified_label").internal_result == "INSUFFICIENT_INFORMATION"


@pytest.mark.parametrize("abstention", [False, True])
def test_internal_ood_wire_protocol_separation(monkeypatch, abstention):
    monkeypatch.setattr(config_module, "_config", replace(get_config(), competition_supports_insufficient_information=abstention))
    agent = DoctorAgent(); state = agent.new_case("ood", "Please install Python.", max_turns=1)
    action, _, _ = agent.decide(state)
    wire = action_to_competition("ood", action, diagnosis_quality=state.pending_diagnosis_quality,
                                 evidence_assessment=state.evidence_assessment)
    assert wire.metadata["internal_result"] == "OUT_OF_DOMAIN"
    assert wire.action_type == "DIAGNOSE"
    assert wire.metadata["forced_due_to_protocol"] is True
    assert wire.content == action.content
    assert wire.metadata["completion_type"] == "FORCED_FINAL_DIAGNOSIS"


def test_internal_failure_clears_stale_confidence(monkeypatch):
    agent = DoctorAgent(); state = agent.new_case("failure", "chest pain", max_turns=1)
    state.evidence_assessment = {"internal_result": "SUPPORTED_DIAGNOSIS"}
    monkeypatch.setattr(agent.differential_engine, "update", lambda s: 1 / 0)
    action, _, _ = agent.decide(state)
    wire = action_to_competition("failure", action, evidence_assessment=state.evidence_assessment)
    assert wire.metadata["forced_due_to_protocol"] is True
    assert wire.metadata["internal_result"] == "INSUFFICIENT_INFORMATION"


def test_development_metrics_track_uncertainty_without_claiming_diagnostic_accuracy():
    from scripts.evaluate_ood_development import evaluate
    result = evaluate()
    assert result["metrics"]["supported_false_ood"]["numerator"] == 0
    assert result["metrics"]["unsafe_confident_diagnosis_proxy"]["numerator"] == 0
    assert result["metrics"]["supported_evidenced_acceptance"]["numerator"] >= 2
    assert not result["independent_clinical_validation"]
