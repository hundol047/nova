"""Action Candidate Generator + utility scoring (spec section 7).

Generates ASK / EXAM / TEST / DIAGNOSE candidates for the current turn and picks the highest-
utility one. Weights come entirely from nova_agent/config.py (never hardcoded here) so local
benchmark / leaderboard feedback can retune behavior without touching this logic.
"""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel

from nova_agent.config import get_config
from nova_agent.differential import DifferentialItem
from nova_agent.missing_info import CandidateInfo, MissingInformationAnalyzer
from nova_agent.safety import SafetyFinding
from nova_agent.state import PatientState
from nova_agent.stop_policy import StopDecision, StopPolicy

AgentActionType = Literal["ASK", "EXAM", "TEST", "DIAGNOSE"]


class ScoredCandidate(BaseModel):
    action_type: AgentActionType
    key: str
    content: str
    utility: float
    components: dict


class AgentAction(BaseModel):
    action_type: AgentActionType
    key: str
    content: str
    rationale: str


class ActionSelector:
    def __init__(self) -> None:
        self.missing_info = MissingInformationAnalyzer()
        self.stop_policy = StopPolicy()

    def _utility(self, cand: CandidateInfo, dangerous_involved: bool) -> tuple[float, dict]:
        w = get_config().weights
        management_relevance = 1.0 if dangerous_involved else 0.3
        utility = (
            w.info_gain_weight * cand.information_gain
            + w.discrimination_weight * cand.diagnostic_discrimination
            + w.safety_weight * cand.safety_relevance
            + w.management_relevance_weight * management_relevance
            - w.turn_cost_weight * cand.turn_cost
            - w.redundancy_penalty * cand.redundancy
        )
        components = {
            "information_gain": cand.information_gain, "diagnostic_discrimination": cand.diagnostic_discrimination,
            "safety_relevance": cand.safety_relevance, "management_relevance": management_relevance,
            "turn_cost": cand.turn_cost, "redundancy": cand.redundancy,
        }
        return utility, components

    def generate_and_select(self, state: PatientState, differential: List[DifferentialItem],
                             safety_findings: List[SafetyFinding], lang: str = "en"
                             ) -> tuple[AgentAction, List[ScoredCandidate], StopDecision]:
        dangerous_ids = {d.diagnosis_id for d in differential if d.dangerous_if_missed}
        raw_candidates = self.missing_info.analyze(state, differential, safety_findings)

        scored: List[ScoredCandidate] = []
        for cand in raw_candidates:
            dangerous_involved = bool(set(cand.disease_ids_discriminated) & dangerous_ids)
            utility, components = self._utility(cand, dangerous_involved)
            content = cand.content_ko if lang == "ko" else cand.content_en
            scored.append(ScoredCandidate(action_type=cand.action_type, key=cand.key, content=content,
                                           utility=round(utility, 3), components=components))
        scored.sort(key=lambda c: c.utility, reverse=True)

        pool_size = get_config().candidate_pool_size
        scored = scored[:pool_size]
        best_info_gain = scored[0].utility if scored else 0.0

        stop_decision = self.stop_policy.evaluate(state, differential, safety_findings, best_info_gain)

        top_diagnosis_name = differential[0].diagnosis if differential else "Undifferentiated presentation"
        diagnose_candidate = ScoredCandidate(
            action_type="DIAGNOSE", key=differential[0].diagnosis_id if differential else "unknown",
            content=top_diagnosis_name, utility=round(stop_decision.readiness_score * 10, 3),
            components={"readiness_score": stop_decision.readiness_score},
        )
        all_candidates = scored + [diagnose_candidate]

        if stop_decision.should_diagnose or not scored:
            action = AgentAction(action_type="DIAGNOSE", key=diagnose_candidate.key,
                                  content=top_diagnosis_name, rationale=stop_decision.reason)
            return action, all_candidates, stop_decision

        chosen = scored[0]
        action = AgentAction(action_type=chosen.action_type, key=chosen.key, content=chosen.content,
                              rationale=f"Highest utility ({chosen.utility}) among {len(scored)} candidate actions; "
                                        f"components={chosen.components}")
        return action, all_candidates, stop_decision
