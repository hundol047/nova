"""Stop / Diagnose Policy (spec section 11).

Decides whether the agent should DIAGNOSE now instead of asking/examining/testing further.
Combines top-diagnosis confidence, the rank-1/rank-2 gap, contradictory evidence, whether a
dangerous alternative is still unresolved, and remaining turns. A hard forced-diagnose fallback
guarantees the agent NEVER runs out the clock without submitting a final diagnosis.

Hybrid-architecture note (spec section 8): `evaluate()` is called by action_selector.py with the
DETERMINISTIC differential only (never the LLM-merged one -- see orchestrator.py's turn pipeline).
This is deliberate: it means `should_diagnose`/`readiness_score` can never be skewed by an
arbitrary confidence/proxy score the LLM assigned to a novel diagnosis it introduced -- those
numbers simply never reach this module. safety_validator.py's `validate_action` is the one place
that reasons about the LLM's own chosen diagnosis, and it does so via `is_resolved()` (evidence-
and workup-based, not score-based) plus an explicit minimum-evidence/turn-count gate, never by
trusting a score.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from nova_agent.config import get_config
from nova_agent.differential import DifferentialItem
from nova_agent.resolution import is_resolved
from nova_agent.safety import SafetyFinding
from nova_agent.state import PatientState


class StopDecision(BaseModel):
    should_diagnose: bool
    forced: bool
    reason: str
    readiness_score: float


class StopPolicy:
    def evaluate(self, state: PatientState, differential: List[DifferentialItem],
                 safety_findings: List[SafetyFinding], best_info_gain: Optional[float] = None) -> StopDecision:
        cfg = get_config().stop_policy

        if state.remaining_turns <= cfg.forced_diagnose_remaining_turns:
            return StopDecision(should_diagnose=True, forced=True,
                                 reason=f"Only {state.remaining_turns} turn(s) remaining; forcing final diagnosis "
                                        "to guarantee submission within the turn limit.",
                                 readiness_score=1.0)

        if not differential:
            return StopDecision(should_diagnose=False, forced=False,
                                 reason="No differential has been generated yet.", readiness_score=0.0)

        top = differential[0]
        second = differential[1] if len(differential) > 1 else None

        band_score = {"HIGH": 1.0, "MEDIUM": 0.5, "LOW": 0.0}[top.confidence_band]
        gap_ratio = 1.0 if second is None else max(0.0, top.score_ratio - second.score_ratio)

        # A dangerous alternative is "unresolved" if it is not the top pick, still plausible (no
        # contradictory evidence against it), and hasn't had its discriminating tests completed.
        unresolved_dangerous = [
            d for d in differential[1:]
            if d.dangerous_if_missed and not d.contradictory_evidence and d.confidence_band != "LOW"
        ]
        differential_by_id = {d.diagnosis_id: d for d in differential}
        active_safety_flags = [
            f for f in safety_findings
            if f.diagnosis_id != top.diagnosis_id
            and not is_resolved(f.diagnosis_id, differential_by_id[f.diagnosis_id].contradictory_evidence
                                 if f.diagnosis_id in differential_by_id else [], state)
        ]
        unresolved_dangerous = [d for d in unresolved_dangerous if not is_resolved(d.diagnosis_id, d.contradictory_evidence, state)]

        dangerous_alternative_exists = bool(unresolved_dangerous or active_safety_flags)

        readiness_score = band_score * 0.4 + gap_ratio * 0.3 + (0.0 if dangerous_alternative_exists else 0.3)

        no_more_value = best_info_gain is not None and best_info_gain <= 0.0
        enough_turns_gathered = state.turn_count >= cfg.min_turns_before_diagnose

        should_diagnose = enough_turns_gathered and (
            (readiness_score >= cfg.diagnose_threshold and gap_ratio >= cfg.min_gap_rank1_rank2
             and not dangerous_alternative_exists)
            or no_more_value
        )

        if should_diagnose:
            reason = ("Top diagnosis is well-supported, clearly separated from the next candidate, "
                       "and no unresolved dangerous alternative remains." if not no_more_value else
                       "No further question/exam/test would meaningfully change the current ranking.")
        else:
            reason = "Insufficient confidence, unresolved dangerous alternative, or differential too close to call."

        return StopDecision(should_diagnose=should_diagnose, forced=False, reason=reason,
                             readiness_score=round(readiness_score, 3))
