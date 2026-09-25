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
from nova_agent.knowledge.retrieval import all_diseases
from nova_agent.missing_info import CandidateInfo, MissingInformationAnalyzer
from nova_agent.safety import SafetyFinding
from nova_agent.state import PatientState
from nova_agent.stop_policy import StopDecision, StopPolicy

AgentActionType = Literal["ASK", "EXAM", "TEST", "DIAGNOSE"]


def _time_critical_ids() -> set:
    """The "time is tissue/brain/myocardium" diagnosis cluster (stroke/ACS/sepsis/anaphylaxis-
    class) -- derived generically from the knowledge base's own `urgency`/`dangerous` fields
    (CRITICAL urgency + dangerous:true already means, by this KB's own schema, an immediate
    time-sensitive intervention need) rather than a second, hand-maintained ID list that could
    drift from it. Recomputed from the live KB each call (cheap, ~30 entries) rather than cached
    at import time, consistent with this module's "never hardcode benchmark-specific IDs" spirit
    -- this reads only the KB's own pre-existing, already-verified urgency/dangerous metadata."""
    return {entry["id"] for entry in all_diseases().values()
            if entry.get("urgency") == "CRITICAL" and entry.get("dangerous")}


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

    def _management_relevance(self, cand: CandidateInfo, dangerous_involved: bool,
                               differential: List[DifferentialItem]) -> float:
        """Spec section 11: not a constant keyed only on the dangerous flag -- reflects how likely
        this action's result is to actually change the clinical plan. Ruling a dangerous diagnosis
        in/out always changes management (urgent workup vs. not), so that case is a hard 1.0.
        Otherwise, relevance scales with how undecided the leading diagnosis still is (a highly
        confident top pick means most further non-dangerous discrimination has little left to
        change) and with how discriminative this specific candidate is."""
        if dangerous_involved:
            return 1.0
        top_confidence = differential[0].confidence_band if differential else "LOW"
        band_factor = {"LOW": 1.0, "MEDIUM": 0.6, "HIGH": 0.25}[top_confidence]
        return round(0.15 + 0.85 * band_factor * cand.diagnostic_discrimination, 3)

    def _utility(self, cand: CandidateInfo, dangerous_involved: bool, time_critical_involved: bool,
                 differential: List[DifferentialItem]) -> tuple[float, dict]:
        w = get_config().weights
        management_relevance = self._management_relevance(cand, dangerous_involved, differential)
        time_critical_bonus = 1.0 if time_critical_involved else 0.0
        utility = (
            w.info_gain_weight * cand.information_gain
            + w.discrimination_weight * cand.diagnostic_discrimination
            + w.safety_weight * cand.safety_relevance
            + w.management_relevance_weight * management_relevance
            + w.time_critical_weight * time_critical_bonus
            - w.turn_cost_weight * cand.turn_cost
            - w.redundancy_penalty * cand.redundancy
        )
        components = {
            "information_gain": cand.information_gain, "diagnostic_discrimination": cand.diagnostic_discrimination,
            "safety_relevance": cand.safety_relevance, "management_relevance": management_relevance,
            "time_critical_bonus": time_critical_bonus, "turn_cost": cand.turn_cost, "redundancy": cand.redundancy,
        }
        return utility, components

    def generate_and_select(self, state: PatientState, differential: List[DifferentialItem],
                             safety_findings: List[SafetyFinding], lang: str = "en"
                             ) -> tuple[AgentAction, List[ScoredCandidate], StopDecision]:
        dangerous_ids = {d.diagnosis_id for d in differential if d.dangerous_if_missed}
        time_critical_ids = _time_critical_ids()
        raw_candidates = self.missing_info.analyze(state, differential, safety_findings)

        scored: List[ScoredCandidate] = []
        for cand in raw_candidates:
            dangerous_involved = bool(set(cand.disease_ids_discriminated) & dangerous_ids)
            time_critical_involved = bool(set(cand.disease_ids_discriminated) & time_critical_ids)
            utility, components = self._utility(cand, dangerous_involved, time_critical_involved, differential)
            content = {"ko": cand.content_ko, "ja": cand.content_ja, "zh": cand.content_zh}.get(lang) \
                or cand.content_en
            scored.append(ScoredCandidate(action_type=cand.action_type, key=cand.key, content=content,
                                           utility=round(utility, 3), components=components))
        scored.sort(key=lambda c: c.utility, reverse=True)

        # The REAL expected information gain of the best remaining action (missing_info.py's
        # entropy-based estimate), not the post-weighting utility score -- utility already bakes
        # in safety/turn-cost/management terms that are irrelevant to "is there anything left to
        # meaningfully learn" (spec section 11/24F: this was previously passing `.utility` here).
        best_info_gain = max((c.information_gain for c in raw_candidates), default=0.0)

        pool_size = get_config().candidate_pool_size
        scored = scored[:pool_size]

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
