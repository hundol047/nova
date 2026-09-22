"""Local patient simulator + single-case runner (spec section 17).

Plays a SyntheticCase against a DoctorAgent exactly the way a real turn-based competition
environment would: DoctorAgent.decide() proposes an action, the simulator supplies the
corresponding scripted (or default) response, DoctorAgent.observe() records it, repeat until
DIAGNOSE or the turn limit.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from nova_agent.action_selector import AgentAction
from nova_agent.diagnosis_normalizer import same_diagnosis
from nova_agent.knowledge.retrieval import critical_condition_ids, disease_by_id
from nova_agent.logging_store import NovaCaseLogger
from nova_agent.orchestrator import DoctorAgent
from nova_agent.state import PatientState

from evaluation.cases import SyntheticCase


class PatientSimulator:
    """Answers the agent's actions from a SyntheticCase's scripted responses, falling back to a
    generic negative/normal response for anything not scripted -- so the agent can ask more than
    the scripted minimum and still get a sensible (if uninformative) answer."""

    def __init__(self, case: SyntheticCase) -> None:
        self.case = case

    def respond(self, action: AgentAction) -> str:
        if action.action_type == "ASK":
            return self.case.answers.get(action.key, self.case.default_answer)
        if action.action_type == "EXAM":
            return self.case.exam_results.get(action.key, self.case.default_exam_result)
        if action.action_type == "TEST":
            return self.case.test_results.get(action.key, self.case.default_test_result)
        return ""


class CaseResult(BaseModel):
    case_id: str
    category: str = "standard"
    scoring_expected: bool = True
    ground_truth: str
    final_diagnosis: Optional[str]
    correct: bool
    turns: int
    ask_count: int = 0
    exam_count: int = 0
    test_count: int = 0
    duplicate_actions: int
    unnecessary_tests: int
    critical: bool
    critical_miss: bool
    malformed_turns: int
    failed_to_diagnose: bool
    llm_call_count: int = 0
    llm_success_count: int = 0
    llm_failure_count: int = 0
    llm_fallback_count: int = 0
    # Populated only when run_case(..., capture_trajectory=True) -- structured evidence summary
    # (never private chain-of-thought) for evaluation/failure_analysis.py's root-cause classifier.
    differential_trajectory: List[dict] = []


def _relevant_test_ids(case: SyntheticCase, seen_diagnosis_ids: Optional[set] = None) -> set:
    """Tests considered 'necessary' for scoring purposes: those tied to the ground-truth disease,
    to any critical condition relevant to this case's chief complaint (since ruling a dangerous
    diagnosis out is legitimate, not wasteful, testing), or to any diagnosis the agent's OWN
    differential engine actually surfaced in its top-K ranking at some point during the case
    (`seen_diagnosis_ids`, spec section 12). That last set matters because the first two only ever
    look at CRITICAL/dangerous diseases -- a plausible, evidence-driven alternative that happens to
    be non-dangerous (e.g. investigating a urinary source in an elderly patient with weakness or
    dyspnea, the way the existing Fever03_DiabeticUrosepsis tuning case expects) was previously
    always counted as 'unnecessary' purely because of that KB metadata flag, not because the test
    was actually unjustified by the evidence gathered so far."""
    relevant = set()
    gt = disease_by_id(case.ground_truth_diagnosis)
    if gt:
        relevant.update(gt.get("discriminating_tests", []))
        relevant.update(gt.get("discriminating_exams", []))
    for cid in critical_condition_ids():
        entry = disease_by_id(cid)
        if entry and set(entry.get("chief_complaint_tags", [])) & set(
                disease_by_id(case.ground_truth_diagnosis).get("chief_complaint_tags", []) if gt else []):
            relevant.update(entry.get("discriminating_tests", []))
    for diagnosis_id in (seen_diagnosis_ids or ()):
        entry = disease_by_id(diagnosis_id)
        if entry:
            relevant.update(entry.get("discriminating_tests", []))
    return relevant


def run_case(agent: DoctorAgent, case: SyntheticCase, logger: Optional[NovaCaseLogger] = None,
             capture_trajectory: bool = False) -> CaseResult:
    state: PatientState = agent.new_case(case.case_id, case.chief_complaint, case.demographics)
    simulator = PatientSimulator(case)

    seen_keys: List[tuple] = []
    duplicate_actions = 0
    malformed_turns = 0
    tests_performed: List[str] = []
    ask_count = exam_count = test_count = 0
    failed_to_diagnose = True
    trajectory: List[dict] = []
    seen_diagnosis_ids: set = set()

    for _ in range(state.max_turns):
        action, llm_output, differential = agent.decide(state)
        # rank<=2 only (not the whole top-5): with sparse early evidence almost every candidate in
        # a disease pool cycles through SOME top-5 slot at some point, which would make this set --
        # and therefore what counts as a justified test -- nearly everything. Reaching rank 1/2 is
        # a much stronger signal that the agent's own reasoning seriously considered the diagnosis,
        # not just that it was present in a large candidate pool.
        seen_diagnosis_ids.update(d.diagnosis_id for d in differential if d.rank <= 2)
        if llm_output is None:
            malformed_turns += 1
        if capture_trajectory:
            trajectory.append({
                "turn": state.turn_count + 1,
                "action": f"{action.action_type}:{action.key}",
                "top5_differential": [d.diagnosis for d in differential[:5]],
            })

        key_sig = (action.action_type, action.key)
        if action.action_type != "DIAGNOSE" and key_sig in seen_keys:
            duplicate_actions += 1
        seen_keys.append(key_sig)
        if action.action_type == "TEST":
            tests_performed.append(action.key)
            test_count += 1
        elif action.action_type == "ASK":
            ask_count += 1
        elif action.action_type == "EXAM":
            exam_count += 1

        if logger is not None:
            logger.log_turn(state, action, differential, [f.condition for f in getattr(state, "red_flags", [])])

        result = simulator.respond(action)
        agent.observe(state, action, result)

        if action.action_type == "DIAGNOSE":
            failed_to_diagnose = False
            break

    relevant_tests = _relevant_test_ids(case, seen_diagnosis_ids)
    unnecessary_tests = sum(1 for t in tests_performed if t not in relevant_tests)

    correct = bool(state.final_diagnosis) and same_diagnosis(state.final_diagnosis, case.ground_truth_diagnosis)
    result_obj = CaseResult(
        case_id=case.case_id, category=case.category, scoring_expected=case.scoring_expected,
        ground_truth=case.ground_truth_diagnosis, final_diagnosis=state.final_diagnosis,
        correct=correct, turns=state.turn_count, ask_count=ask_count, exam_count=exam_count,
        test_count=test_count, duplicate_actions=duplicate_actions,
        unnecessary_tests=unnecessary_tests, critical=case.critical,
        critical_miss=case.critical and not correct, malformed_turns=malformed_turns,
        failed_to_diagnose=failed_to_diagnose,
        llm_call_count=state.llm_call_count, llm_success_count=state.llm_success_count,
        llm_failure_count=state.llm_failure_count, llm_fallback_count=state.llm_fallback_count,
        differential_trajectory=trajectory,
    )
    if logger is not None:
        logger.log_final(state, "correct" if correct else "incorrect")
    return result_obj
