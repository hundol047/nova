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
from nova_agent.knowledge.retrieval import all_diseases, disease_by_id
from nova_agent.missing_info import CandidateInfo, MissingInformationAnalyzer
from nova_agent.safety import SafetyFinding
from nova_agent.state import PatientState
from nova_agent.stop_policy import StopDecision, StopPolicy

AgentActionType = Literal["ASK", "EXAM", "TEST", "DIAGNOSE", "SAY"]


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


# Small tie-break (utility points; typical utilities are ~3) -- see generate_and_select().
LEADER_CONFIRMATORY_BONUS = 0.05
# Round N: priority for the outstanding minimum workup of a dangerous diagnosis that is currently BLOCKING the
# stop (an active safety flag, or a substantively supported unresolved dangerous alternative). Same order of
# magnitude as the measured gap between the chosen action and the best resolving action (median 0.19, p75 0.45
# utility on the development suites). Only after core history is taken, so history is never skipped for tests.
BLOCKING_WORKUP_BONUS = 0.5
_CORE_HISTORY = ("onset", "associated_symptoms", "past_medical_history")


class ActionSelector:
    def __init__(self) -> None:
        self.missing_info = MissingInformationAnalyzer()
        self.stop_policy = StopPolicy()

    @staticmethod
    def _faithful_asks(state, scored):
        """Round Q: a detailed question that can only be SENT as the generic follow-up IS the generic question --
        it is emitted under the generic key (so its answer is recorded as what was really asked), and it is dropped
        when that generic question was already asked. Keeps the best-utility instance of each resulting key."""
        from nova_agent.preliminary import question_is_faithful
        lang = state.locale or "en"
        out, seen = [], set()
        for cand in scored:
            if cand.action_type == "ASK" and ":" in cand.key and not question_is_faithful(cand.key, lang):
                category = cand.key.split(":", 1)[0]
                if state.question_attempted(category):
                    continue
                cand = cand.model_copy(update={"key": category})
            if (cand.action_type, cand.key) in seen:
                continue
            seen.add((cand.action_type, cand.key))
            out.append(cand)
        return out

    @staticmethod
    def _pending_dangerous_bedside_exam(state, differential, scored):
        from nova_agent.differential import _entry_for_candidate_id, _strip_negative_prefix
        from nova_agent.taxonomy import EXAM_CATALOG
        for item in differential[:5]:
            if not (item.dangerous_if_missed and item.score > 0):
                continue
            entry = _entry_for_candidate_id(item.diagnosis_id) or {}
            risk = {str(r).lower() for r in entry.get("risk_factors", [])}
            if not any(e.lower() not in risk and _strip_negative_prefix(e) is None for e in item.supporting_evidence):
                continue
            for exam_id in list(entry.get("minimum_workup") or []) + list(entry.get("discriminating_exams", [])):
                if exam_id in EXAM_CATALOG and not state.exam_done(exam_id):
                    spec = EXAM_CATALOG[exam_id]
                    return ScoredCandidate(action_type="EXAM", key=exam_id, content=spec["name_en"], utility=0.0,
                                           components={"dangerous_alternative_bedside_exam": 1.0})
        return None

    def _decisively_supported_dangerous_ids(self, differential: List[DifferentialItem]) -> dict:
        """Dangerous diagnoses that are ALREADY the clear, well-separated leading diagnosis with no
        competing unresolved dangerous alternative -- i.e. the case is essentially ready to
        DIAGNOSE already (mirrors stop_policy.StopPolicy's own HIGH-confidence + rank1/2-gap +
        no-unresolved-alternative gate, deliberately at least as conservative: ANY other dangerous
        entry anywhere in the differential without contradictory evidence blocks this, not just a
        MEDIUM+ confidence one). Maps diagnosis_id -> that diagnosis's own `minimum_workup` set (or
        empty), used by `_management_relevance` below to stop treating every remaining
        discriminator for an already-decided dangerous diagnosis as automatically management-
        changing (spec: avoid continued unnecessary testing once the leading diagnosis is strongly
        supported and dangerous alternatives are addressed) while still giving full priority to
        whatever that diagnosis's own real confirmatory workup still needs."""
        if not differential:
            return {}
        top = differential[0]
        if not top.dangerous_if_missed or top.confidence_band != "HIGH":
            return {}
        if any(d.dangerous_if_missed and not d.contradictory_evidence for d in differential[1:]):
            return {}
        cfg = get_config().stop_policy
        second = differential[1] if len(differential) > 1 else None
        if second is not None and (top.score_ratio - second.score_ratio) < cfg.min_gap_rank1_rank2:
            return {}
        entry = disease_by_id(top.diagnosis_id)
        return {top.diagnosis_id: set((entry or {}).get("minimum_workup") or ())}

    def _management_relevance(self, cand: CandidateInfo, dangerous_discriminated: set,
                               differential: List[DifferentialItem],
                               decisively_supported: dict) -> float:
        """Spec section 11: not a constant keyed only on the dangerous flag -- reflects how likely
        this action's result is to actually change the clinical plan. Ruling a still-genuinely-
        uncertain dangerous diagnosis in/out always changes management (urgent workup vs. not), so
        that case is a hard 1.0. A dangerous diagnosis this candidate touches that is ALREADY
        decisively supported (see `_decisively_supported_dangerous_ids`) keeps that hard 1.0 ONLY
        for an item still in ITS OWN minimum_workup (the real confirmatory gate) -- once that gate
        is satisfied, an extra item no longer changes the plan and falls through to the same
        discrimination-scaled relevance a non-dangerous candidate gets. Otherwise, relevance scales
        with how undecided the leading diagnosis still is (a highly confident top pick means most
        further non-dangerous discrimination has little left to change) and with how discriminative
        this specific candidate is."""
        if dangerous_discriminated:
            still_relevant = any(
                did not in decisively_supported or cand.key in decisively_supported[did]
                for did in dangerous_discriminated
            )
            if still_relevant:
                return 1.0
        top_confidence = differential[0].confidence_band if differential else "LOW"
        band_factor = {"LOW": 1.0, "MEDIUM": 0.6, "HIGH": 0.25}[top_confidence]
        return round(0.15 + 0.85 * band_factor * cand.diagnostic_discrimination, 3)

    def _utility(self, cand: CandidateInfo, dangerous_discriminated: set, time_critical_involved: bool,
                 differential: List[DifferentialItem], decisively_supported: dict) -> tuple[float, dict]:
        w = get_config().weights
        management_relevance = self._management_relevance(cand, dangerous_discriminated, differential, decisively_supported)
        time_critical_bonus = 1.0 if time_critical_involved else 0.0
        utility = (
            w.info_gain_weight * cand.information_gain
            + w.discrimination_weight * cand.diagnostic_discrimination
            + w.safety_weight * cand.safety_relevance
            + w.management_relevance_weight * management_relevance
            + w.time_critical_weight * time_critical_bonus
            + w.top_competitor_weight * cand.top_competitor_separation
            + w.critical_resolution_weight * cand.critical_resolution_gain
            + w.specificity_gain_weight * cand.specificity_gain
            - w.turn_cost_weight * cand.turn_cost
            - w.redundancy_penalty * cand.redundancy
        )
        components = {
            "top_competitor_separation": cand.top_competitor_separation,
            "critical_resolution_gain": cand.critical_resolution_gain,
            "specificity_gain": cand.specificity_gain,
            "decision_changing_value": cand.decision_changing_value,
            "information_gain": cand.information_gain, "diagnostic_discrimination": cand.diagnostic_discrimination,
            "safety_relevance": cand.safety_relevance, "management_relevance": management_relevance,
            "time_critical_bonus": time_critical_bonus, "turn_cost": cand.turn_cost, "redundancy": cand.redundancy,
        }
        return utility, components

    @staticmethod
    def _blocking_workup(state: PatientState, differential: List[DifferentialItem],
                         safety_findings: List[SafetyFinding]) -> set:
        """Outstanding minimum-workup actions of dangerous diagnoses that currently keep the encounter open."""
        if not get_config().action_v2_enabled or not differential:
            return set()
        if not all(state.question_asked(k) for k in _CORE_HISTORY):
            return set()
        from nova_agent.missing_info import _resolve_entry
        from nova_agent.resolution import is_resolved
        from nova_agent.stop_policy import _substantively_supported
        leader = differential[0].diagnosis_id
        by_id = {d.diagnosis_id: d for d in differential}
        blocking = {f.diagnosis_id for f in safety_findings if f.diagnosis_id != leader}
        blocking |= {d.diagnosis_id for d in differential[1:5] if d.dangerous_if_missed and _substantively_supported(d)}
        done = set(state.completed_tests) | set(state.completed_examinations)
        out = set()
        for did in blocking:
            item = by_id.get(did)
            if is_resolved(did, list(item.contradictory_evidence) if item else [], state):
                continue
            entry = _resolve_entry(did) or {}
            workup = entry.get("minimum_workup") or (list(entry.get("discriminating_exams", []))
                                                      + list(entry.get("discriminating_tests", [])))
            out |= set(workup) - done
        return out

    def generate_and_select(self, state: PatientState, differential: List[DifferentialItem],
                             safety_findings: List[SafetyFinding], lang: str = "en"
                             ) -> tuple[AgentAction, List[ScoredCandidate], StopDecision]:
        # SafetyLayer can actively flag a dangerous diagnosis that is below the display top-K.
        # Treat that finding as dangerous for action utility too; otherwise the stop policy would
        # correctly keep the case open while the selector still preferred unrelated low-safety
        # actions because the flagged diagnosis was not present in the truncated differential.
        dangerous_ids = ({d.diagnosis_id for d in differential if d.dangerous_if_missed}
                         | {f.diagnosis_id for f in safety_findings})
        time_critical_ids = _time_critical_ids()
        safety_only_ids = {f.diagnosis_id for f in safety_findings} - {d.diagnosis_id for d in differential}
        leader = differential[0] if differential else None
        leader_workup = set()
        if leader is not None and leader.dangerous_if_missed:
            from nova_agent.missing_info import _resolve_entry
            leader_workup = set((_resolve_entry(leader.diagnosis_id) or {}).get("minimum_workup") or ())
        decisively_supported = self._decisively_supported_dangerous_ids(differential)
        blocking_workup = self._blocking_workup(state, differential, safety_findings)
        raw_candidates = self.missing_info.analyze(state, differential, safety_findings)
        if state.preliminary_rules:
            # Preliminary round: there is no TEST action. Tests the diagnosis would need are
            # carried into the SOAP plan instead (nova_agent/soap.py), never requested.
            raw_candidates = [c for c in raw_candidates if c.action_type != "TEST"]

        scored: List[ScoredCandidate] = []
        for cand in raw_candidates:
            dangerous_discriminated = set(cand.disease_ids_discriminated) & dangerous_ids
            time_critical_involved = bool(set(cand.disease_ids_discriminated) & time_critical_ids)
            utility, components = self._utility(cand, dangerous_discriminated, time_critical_involved,
                                                  differential, decisively_supported)
            # Legacy (non-competition) retrieval: the minimum-workup confirmatory test of the LEADING
            # dangerous diagnosis (troponin for ACS) must not lose a near-tie to a generic question merely
            # because a weakly supported must-not-miss alternative (kept in the pool by PR #15's safety-net
            # protection) also touches that question. Competition retrieval has its own critical-resolution
            # and specificity terms for this and is left exactly as measured.
            if (leader_workup and not get_config().competition_retrieval_enabled
                    and cand.action_type in {"TEST", "EXAM"} and cand.key in leader_workup):
                utility += LEADER_CONFIRMATORY_BONUS
                components["leading_dangerous_confirmatory"] = LEADER_CONFIRMATORY_BONUS
            # PR #15's "mandatory structured vitals" gate, scoped to its stated purpose: a red flag whose
            # diagnosis is NOT in the displayed differential (SafetyLayer raised it from below the top-K)
            # would otherwise have no action investigating it, so structured vitals -- which feed
            # SafetyLayer's numeric thresholds -- come first. When the flagged diagnosis IS already in the
            # differential (e.g. ACS in a crushing-chest-pain presentation) its own confirmatory test must
            # keep outranking generic early actions (tests/test_discriminator_priority.py). In the
            # preliminary round vitals arrive with the first patient statement, so this is already satisfied.
            if cand.action_type in {"TEST", "EXAM"} and cand.key in blocking_workup:
                utility += BLOCKING_WORKUP_BONUS
                components["blocking_danger_workup"] = BLOCKING_WORKUP_BONUS
            if (safety_only_ids and cand.action_type == "EXAM" and cand.key == "vital_signs"
                    and not state.exam_done("vital_signs")):
                gate_bonus = get_config().weights.safety_weight + get_config().weights.time_critical_weight
                utility += gate_bonus
                components["mandatory_safety_vitals"] = round(gate_bonus, 3)
            content = {"ko": cand.content_ko, "ja": cand.content_ja, "zh": cand.content_zh}.get(lang) \
                or cand.content_en
            scored.append(ScoredCandidate(action_type=cand.action_type, key=cand.key, content=content,
                                           utility=round(utility, 3), components=components))
        scored.sort(key=lambda c: c.utility, reverse=True)
        if state.preliminary_rules:
            scored = self._faithful_asks(state, scored)

        # UNKNOWN_PRESENTATION (spec: zero-evidence file-order bug fix, see differential.py's
        # `is_zero_evidence_presentation`/stop_policy.py's matching gate): with literally nothing
        # matched yet, a TEST result is not meaningfully better-targeted than any other -- it is
        # effectively a random blind test, exactly what the spec forbids here. A plain ASK/EXAM
        # clarifying question is always preferred while any remain, so the very next action is
        # information-gathering rather than an arbitrary test order; only once ASK/EXAM candidates
        # are genuinely exhausted does TEST become reachable again (never a hard block, so the
        # agent can still make progress in the rare case nothing else is left to ask/examine).
        if differential and differential[0].fallback_candidate:
            info_gathering = [c for c in scored if c.action_type in ("ASK", "EXAM")]
            if info_gathering:
                scored = info_gathering + [c for c in scored if c.action_type == "TEST"]

        # The REAL expected information gain of the best remaining action (missing_info.py's
        # entropy-based estimate), not the post-weighting utility score -- utility already bakes
        # in safety/turn-cost/management terms that are irrelevant to "is there anything left to
        # meaningfully learn" (spec section 11/24F: this was previously passing `.utility` here).
        best_info_gain = max((c.information_gain for c in raw_candidates), default=0.0)

        pool_size = get_config().candidate_pool_size
        scored = scored[:pool_size]

        stop_decision = self.stop_policy.evaluate(state, differential, safety_findings, best_info_gain,
            best_decision_value=max((c.decision_changing_value for c in raw_candidates), default=0.0)
                if (get_config().competition_retrieval_enabled or get_config().stop_v2_enabled) else None)

        top_diagnosis_name = differential[0].diagnosis if differential else "Undifferentiated presentation"
        diagnose_candidate = ScoredCandidate(
            action_type="DIAGNOSE", key=differential[0].diagnosis_id if differential else "unknown",
            content=top_diagnosis_name, utility=round(stop_decision.readiness_score * 10, 3),
            components={"readiness_score": stop_decision.readiness_score},
        )
        all_candidates = scored + [diagnose_candidate]

        if (stop_decision.should_diagnose and not stop_decision.forced and state.preliminary_rules
                and get_config().final_decision_enabled):
            pending = self._pending_dangerous_bedside_exam(state, differential, scored)
            if pending is not None:
                # Round Q: before closing, one remaining bedside EXAM of a dangerous candidate that has real positive
                # support (the neuro exam for a stroke with aphasia) is done first -- an executable, discriminating
                # action is preferred to closing on what is still unexamined. Rejected/done exams are never retried.
                return (AgentAction(action_type="EXAM", key=pending.key, content=pending.content,
                                    rationale="Examine a still-unexamined dangerous alternative before closing."),
                        scored + [diagnose_candidate], stop_decision)

        if stop_decision.should_diagnose or not scored:
            # Round Q: record WHY the encounter ends. Exhausting the actions permits completion only; whether a
            # specific diagnosis may be named is decided separately (nova_agent/final_decision.py).
            state.completion_reason = ("budget" if stop_decision.forced else
                                       "supported" if stop_decision.should_diagnose else "information_exhausted")
            action = AgentAction(action_type="DIAGNOSE", key=diagnose_candidate.key,
                                  content=top_diagnosis_name, rationale=stop_decision.reason)
            return action, all_candidates, stop_decision

        chosen = scored[0]
        action = AgentAction(action_type=chosen.action_type, key=chosen.key, content=chosen.content,
                              rationale=f"Highest utility ({chosen.utility}) among {len(scored)} candidate actions; "
                                        f"components={chosen.components}")
        return action, all_candidates, stop_decision
