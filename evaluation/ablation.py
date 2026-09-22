"""Ablation test (spec section 18): `python -m evaluation.ablation`

Compares A-F feature configurations by reusing the real nova_agent components with pieces
selectively disabled (never a separate throwaway implementation), so the comparison reflects what
each component actually contributes:

  A. Basic Agent           -- no differential ranking, fixed question checklist, no safety layer
  B. + Patient State       -- adds dedup/accumulation (checklist skips already-answered items)
  C. + Differential Engine -- adds per-turn differential re-ranking (still fixed checklist actions)
  D. + Info-Gain Selection -- adds utility-based ASK/EXAM/TEST selection (safety_weight = 0)
  E. + Safety Layer        -- full utility formula including safety_weight
  F. + Retrieval           -- RAG enabled

Caveat printed with the results: stages A/B run without a differential at all, so their "diagnosis"
is a naive first-match guess, not a real prediction -- they exist to show how much each later stage
improves on doing nothing clever, not to be a competitive baseline. F is measured under the default
mock LLM client, which never reads retrieved text (only the optional real `anthropic` provider's
prompt does) -- so F vs E shows no metric difference here by construction, not because retrieval is
useless; it is a construction visible in Case Summary of that stage, not a hidden change.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from nova_agent.action_selector import ActionSelector, AgentAction
from nova_agent.config import NovaConfig, UtilityWeights, get_config
from nova_agent.differential import DifferentialEngine, DifferentialItem
from nova_agent.knowledge.retrieval import all_diseases, diseases_for_tag
from nova_agent.chief_complaint import classify as classify_chief_complaint
from nova_agent.orchestrator import DoctorAgent
from nova_agent.safety import SafetyLayer
from nova_agent.state import PatientState
from nova_agent.taxonomy import QUESTION_CATALOG

from evaluation.cases import CASES
from evaluation.simulator import CaseResult, PatientSimulator

FIXED_CHECKLIST = ["onset", "character", "associated_symptoms", "past_medical_history",
                    "family_history", "social_history"]
FIXED_CHECKLIST_LENGTH = len(FIXED_CHECKLIST)


@dataclass
class StageFlags:
    name: str
    use_patient_state: bool
    use_differential: bool
    use_action_selection: bool
    use_safety: bool
    use_retrieval: bool


STAGES = [
    StageFlags("A. Basic Agent", False, False, False, False, False),
    StageFlags("B. + Patient State", True, False, False, False, False),
    StageFlags("C. + Differential Engine", True, True, False, False, False),
    StageFlags("D. + Info-Gain Selection", True, True, True, False, False),
    StageFlags("E. + Safety Layer", True, True, True, True, False),
    StageFlags("F. + Retrieval", True, True, True, True, True),
]


def _naive_differential(state: PatientState) -> List[DifferentialItem]:
    tag = classify_chief_complaint(state.chief_complaint)
    candidates = diseases_for_tag(tag) or list(all_diseases().values())
    entry = candidates[0]
    return [DifferentialItem(
        diagnosis=entry["name"], diagnosis_id=entry["id"], rank=1, score=0.0, score_ratio=0.0,
        supporting_evidence=[], contradictory_evidence=[], missing_discriminative_evidence=[],
        urgency=entry.get("urgency", "LOW"), dangerous_if_missed=bool(entry.get("dangerous", False)),
        confidence_band="LOW",
    )]


def _checklist_action(state: PatientState, differential: List[DifferentialItem], use_patient_state: bool,
                       turn_index: int) -> AgentAction:
    if use_patient_state:
        next_q = next((c for c in FIXED_CHECKLIST if not state.question_asked(c)), None)
    else:
        # No accumulation/dedup: blindly cycles the checklist by turn index, so it can and does
        # re-ask the same question -- this is the point of the "no patient state" stage.
        next_q = FIXED_CHECKLIST[turn_index % FIXED_CHECKLIST_LENGTH]
    if next_q is not None and turn_index < FIXED_CHECKLIST_LENGTH:
        spec = QUESTION_CATALOG[next_q]
        return AgentAction(action_type="ASK", key=next_q, content=spec["text_en"],
                            rationale="Fixed checklist (ablation baseline)")
    top = differential[0]
    return AgentAction(action_type="DIAGNOSE", key=top.diagnosis_id, content=top.diagnosis,
                        rationale="Fixed-length checklist exhausted (ablation baseline)")


def run_stage_case(stage: StageFlags, case) -> CaseResult:
    cfg = get_config()
    weights = UtilityWeights(
        info_gain_weight=cfg.weights.info_gain_weight, discrimination_weight=cfg.weights.discrimination_weight,
        safety_weight=(cfg.weights.safety_weight if stage.use_safety else 0.0),
        management_relevance_weight=cfg.weights.management_relevance_weight,
        turn_cost_weight=cfg.weights.turn_cost_weight, redundancy_penalty=cfg.weights.redundancy_penalty,
    )
    import nova_agent.config as config_module
    config_module._config = NovaConfig(rag_enabled=stage.use_retrieval, weights=weights,
                                        stop_policy=cfg.stop_policy, max_turns=cfg.max_turns)

    agent = DoctorAgent()
    state = agent.new_case(case.case_id, case.chief_complaint, case.demographics)
    simulator = PatientSimulator(case)
    duplicate_actions = 0
    seen_keys: List[tuple] = []
    turn_index = 0
    failed_to_diagnose = True

    for turn_index in range(state.max_turns):
        if stage.use_differential:
            differential = DifferentialEngine().update(state)
        else:
            differential = _naive_differential(state)
        safety_findings = SafetyLayer().assess(state, differential) if stage.use_safety else []

        if stage.use_action_selection:
            action, _candidates, _stop = ActionSelector().generate_and_select(state, differential, safety_findings)
        else:
            action = _checklist_action(state, differential, stage.use_patient_state, turn_index)
            if state.remaining_turns <= 1 and action.action_type != "DIAGNOSE":
                action = AgentAction(action_type="DIAGNOSE", key=differential[0].diagnosis_id,
                                      content=differential[0].diagnosis, rationale="Forced by turn limit.")

        key_sig = (action.action_type, action.key)
        if action.action_type != "DIAGNOSE" and key_sig in seen_keys:
            duplicate_actions += 1
        seen_keys.append(key_sig)

        result = simulator.respond(action)
        agent.observe(state, action, result)
        if action.action_type == "DIAGNOSE":
            failed_to_diagnose = False
            break

    from nova_agent.diagnosis_normalizer import same_diagnosis
    correct = bool(state.final_diagnosis) and same_diagnosis(state.final_diagnosis, case.ground_truth_diagnosis)
    return CaseResult(case_id=case.case_id, ground_truth=case.ground_truth_diagnosis,
                       final_diagnosis=state.final_diagnosis, correct=correct, turns=state.turn_count,
                       duplicate_actions=duplicate_actions, unnecessary_tests=0, critical=case.critical,
                       critical_miss=case.critical and not correct, malformed_turns=0,
                       failed_to_diagnose=failed_to_diagnose)


def run_ablation() -> dict:
    original_config = get_config()
    import nova_agent.config as config_module
    results = {}
    try:
        for stage in STAGES:
            stage_results = [run_stage_case(stage, case) for case in CASES]
            n = len(stage_results) or 1
            results[stage.name] = {
                "accuracy": sum(r.correct for r in stage_results) / n,
                "avg_turns": sum(r.turns for r in stage_results) / n,
                "duplicate_rate": sum(r.duplicate_actions for r in stage_results) / n,
                "critical_miss_rate": (sum(r.critical_miss for r in stage_results if r.critical) /
                                        max(1, sum(1 for r in stage_results if r.critical))),
            }
    finally:
        config_module._config = original_config
    return results


def print_ablation_report(results: dict) -> None:
    header = f"{'Stage':<28}{'Accuracy':<12}{'Avg Turns':<12}{'Dup/Case':<12}{'Crit Miss':<12}"
    print(header)
    print("-" * len(header))
    for name, r in results.items():
        print(f"{name:<28}{r['accuracy'] * 100:>7.1f}%   {r['avg_turns']:>7.1f}     "
              f"{r['duplicate_rate']:>7.2f}     {r['critical_miss_rate'] * 100:>7.1f}%")
    print("\nSee evaluation/ablation.py module docstring for what each stage does and does not "
          "isolate (in particular: stages A/B have no real differential, and F vs E only differs "
          "when NOVA_LLM_PROVIDER=anthropic, since the default mock client never reads retrieved text).")


if __name__ == "__main__":
    print_ablation_report(run_ablation())
