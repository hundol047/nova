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
from nova_agent.severity_evidence import severity_score
from nova_agent.state import PatientState

# How physiologically deranged the patient must look (severity_evidence.severity_score, a 0..1
# fraction of matched signal categories) before a dangerous diagnosis with otherwise-LOW diagnostic
# confidence still counts as an actively unresolved alternative. ~2 of 7 signal categories.
_SEVERITY_KEEPS_ALTERNATIVE_ACTIVE_THRESHOLD = 0.3


# Decisive-lead stop (Round M). readiness_score above is built from score_ratio = score /
# max_possible, and max_possible grows with every feature a knowledge-base entry lists, so a
# diagnosis that is clearly ahead on ABSOLUTE evidence could still sit at a LOW band and keep the
# encounter running until the action catalog was exhausted (Round M tracing: top-1 correct for
# ~20 turns before the stop). The absolute lead below is the same quantity mature_low_value already
# uses (raw score gap), generalized from "objective confirmation + 2.5 gap" to "converging evidence
# + one typical-feature's worth of gap". It never bypasses an unresolved dangerous alternative.
_DECISIVE_LEAD_MIN_SCORE = 2.0
_DECISIVE_LEAD_MIN_GAP = 1.0
_DECISIVE_LEAD_MIN_SUPPORT = 2
_DECISIVE_LEAD_MIN_TURNS = 6


def _substantively_supported(item: DifferentialItem, severity_ok: bool = True) -> bool:
    """Whether a candidate's supporting evidence is enough to keep a dangerous alternative pending.

    * An ontology (Tier-2/3) item needs at least two matched features: a single generic match (e.g.
      "fever" on a long-tail dangerous concept) is retrieval-level noise, and Tier-2 concepts have no
      workup that could resolve it, so counting it let one stray feature hold every febrile
      encounter open.
    * Support made ONLY of generic physiologic-severity words (fever, tachycardia, confusion...)
      keeps an alternative pending when the patient looks physiologically sick (`severity_ok`) or the
      support converges (>= 3 such features); otherwise one lay-worded "confused" or "fever" kept
      every dangerous metabolic/infectious alternative alive and drove 50-turn encounters.
    * Any other supported Tier-1 item is pending, as before."""
    support = list(item.supporting_evidence)
    if not support:
        return False
    if item.diagnosis_id.startswith("onto::") and len(support) < 2:
        return False
    from nova_agent.matching import content_words
    from nova_agent.severity_evidence import GENERIC_PHYSIOLOGIC_SEVERITY_WORDS
    generic_only = all(content_words(p) and content_words(p).issubset(GENERIC_PHYSIOLOGIC_SEVERITY_WORDS)
                       for p in support)
    return not generic_only or severity_ok or len(support) >= 3


class StopDecision(BaseModel):
    should_diagnose: bool
    forced: bool
    reason: str
    readiness_score: float
    # Development trace only (never read by the decision): which conditions held the encounter open.
    blockers: List[str] = []


class StopPolicy:
    def evaluate(self, state: PatientState, differential: List[DifferentialItem],
                 safety_findings: List[SafetyFinding], best_info_gain: Optional[float] = None,
                 best_decision_value: Optional[float] = None) -> StopDecision:
        cfg = get_config().stop_policy

        # Preliminary round: a case ends at 50 turns OR 20 minutes, and a case that never submits
        # scores 0, so the wall clock forces the diagnosis too (with headroom for the closing
        # explanation and the final submission), and three turns are kept in reserve for the closing dialogue (history top-up, diagnosis and next-step SAY).
        time_up = state.time_nearly_up()
        reserve = cfg.forced_diagnose_remaining_turns + (3 if state.preliminary_rules else 0)
        if state.remaining_turns <= reserve or time_up:
            return StopDecision(should_diagnose=True, forced=True,
                                 reason=(f"Only {state.remaining_turns} turn(s) remaining" if not time_up
                                         else "Case time budget nearly spent")
                                        + "; forcing final diagnosis to guarantee submission within the limit.",
                                 readiness_score=1.0)

        if not differential:
            return StopDecision(should_diagnose=False, forced=False,
                                 reason="No differential has been generated yet.", readiness_score=0.0)

        top = differential[0]

        # UNKNOWN_PRESENTATION / zero-evidence gate (spec: the file-order fallback-ranking bug's
        # real fix). `top.fallback_candidate` is only ever True when literally nothing -- no
        # symptom, risk, medication, history, imaging, or objective evidence -- matched anything
        # this turn (see differential.py's own `is_zero_evidence_presentation` computation); every
        # entry in `differential` is then just the untargeted whole catalog, tied at score 0.0, and
        # "rank 1" is an artifact of dict/file insertion order, not clinical signal. Diagnosing
        # confidently off that tie is exactly the bug this gate closes: never let `no_more_value`
        # (there is genuinely nothing left to usefully ask when nothing has been elicited yet, which
        # is trivially true turn one) or a coincidentally-passing readiness/gap check bypass this.
        # The hard forced-diagnose-at-low-remaining-turns branch above this still applies regardless
        # -- the agent must still submit SOME final diagnosis before the turn budget runs out even
        # if the presentation is never clarified -- so this can never cause an infinite stall.
        if top.fallback_candidate:
            return StopDecision(
                should_diagnose=False, forced=False,
                reason="UNKNOWN_PRESENTATION: no symptom, risk, medication, history, imaging, or "
                       "objective evidence has matched anything yet -- the current top-ranked entry "
                       "is an artifact of candidate order, not real clinical support. Further "
                       "clarifying information is required before any diagnosis can be made.",
                readiness_score=0.0,
            )
        second = differential[1] if len(differential) > 1 else None

        band_score = {"HIGH": 1.0, "MEDIUM": 0.5, "LOW": 0.0}[top.confidence_band]
        gap_ratio = 1.0 if second is None else max(0.0, top.score_ratio - second.score_ratio)

        # A dangerous alternative is "unresolved" if it is not the top pick, still plausible (no
        # contradictory evidence against it), and hasn't had its discriminating tests completed.
        # Normally that also requires at least MEDIUM diagnostic confidence -- but a genuinely
        # sick-looking patient (severity_evidence.severity_score, a SEPARATE axis from diagnostic
        # confidence -- see differential.py's module docs for why the two are never mixed into one
        # score) can rationally justify keeping a dangerous diagnosis actively pursued even while
        # its own diagnostic evidence is still thin, as long as it already has SOME real supporting
        # evidence of its own (never zero-evidence noise): this is the "safety_priority" the spec
        # describes -- danger_if_missed + diagnostic plausibility (some real support) + severity
        # context + not yet ruled out -- and it only ever affects which alternative stays actively
        # tracked here (and therefore which questions/tests action_selector.py's existing
        # dangerous-diagnosis-discrimination weighting prioritizes next), never the differential
        # ranking/score itself.
        severity = severity_score(state)
        severity_keeps_alternative_active = severity >= _SEVERITY_KEEPS_ALTERNATIVE_ACTIVE_THRESHOLD
        unresolved_dangerous = [
            d for d in differential[1:]
            if d.dangerous_if_missed and not d.contradictory_evidence
            and (d.confidence_band != "LOW" or (severity_keeps_alternative_active and _substantively_supported(d, True)))
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

        # `not dangerous_alternative_exists` is an UNCONDITIONAL requirement (spec: DIAGNOSE
        # allowed only when strong evidence + top margin + critical alternatives resolved + low
        # remaining info gain all hold SIMULTANEOUSLY) -- `no_more_value` alone must never bypass
        # it. Previously it did: once the agent ran out of further USEFUL questions/tests to ask
        # (best_info_gain <= 0.0), it could diagnose a well-matched benign top pick (e.g. a
        # patient's own known-migraine history) while a newly-flagged, still-uninvestigated
        # dangerous alternative (e.g. a new focal deficit suggesting stroke) sat completely
        # unresolved -- exactly the anchoring/premature-closure failure mode this fix targets, in
        # its generic form. `no_more_value` still legitimately substitutes for the
        # readiness/gap-margin check (there's nothing more to learn that would change the
        # ranking), it just can never substitute for having actually resolved a real danger. The
        # separate forced-diagnose-at-low-remaining-turns branch above this still guarantees the
        # agent never stalls forever even if a flagged danger is never resolved.
        should_diagnose = enough_turns_gathered and not dangerous_alternative_exists and (
            (readiness_score >= cfg.diagnose_threshold and gap_ratio >= cfg.min_gap_rank1_rank2)
            or no_more_value
        )

        if best_decision_value is not None:
            # An evidenced critical Top-5 alternative with workup remaining must not be
            # forgotten simply because its heuristic band is LOW or one soft negative exists.
            pending_critical = any(d.dangerous_if_missed and _substantively_supported(d, severity_keeps_alternative_active)
                and not is_resolved(d.diagnosis_id, d.contradictory_evidence, state)
                for d in differential[:5])
            from nova_agent.knowledge.retrieval import disease_by_id
            entry = disease_by_id(top.diagnosis_id) or {}
            objective_confirmed = bool(set(entry.get("confirmatory_findings", [])) & set(top.supporting_evidence))
            raw_gap = top.score - second.score if second else top.score
            mature_low_value = (objective_confirmed and raw_gap >= 2.5
                                and best_decision_value <= 0.15 and enough_turns_gathered)
            pending_critical_alternative = any(
                d.dangerous_if_missed and _substantively_supported(d, severity_keeps_alternative_active)
                and not is_resolved(d.diagnosis_id, d.contradictory_evidence, state)
                for d in differential[1:5])
            decisive_lead = (state.turn_count >= _DECISIVE_LEAD_MIN_TURNS and second is not None
                             and top.score >= _DECISIVE_LEAD_MIN_SCORE
                             and len(top.supporting_evidence) >= _DECISIVE_LEAD_MIN_SUPPORT
                             and raw_gap >= _DECISIVE_LEAD_MIN_GAP
                             and not top.contradictory_evidence)
            should_diagnose = ((should_diagnose or mature_low_value) and not (
                dangerous_alternative_exists or pending_critical)) or (
                decisive_lead and not (dangerous_alternative_exists or pending_critical_alternative))

        blockers: List[str] = []
        if not should_diagnose:
            blockers += [f"unresolved_dangerous:{d.diagnosis_id}" for d in unresolved_dangerous]
            blockers += [f"safety_flag:{f.diagnosis_id}" for f in active_safety_flags]
            if not enough_turns_gathered:
                blockers.append("min_turns")
            if readiness_score < cfg.diagnose_threshold:
                blockers.append("readiness")
            if gap_ratio < cfg.min_gap_rank1_rank2:
                blockers.append("gap")
            if best_decision_value is not None and pending_critical:
                blockers.append("pending_critical")

        if should_diagnose:
            reason = ("Top diagnosis is well-supported, clearly separated from the next candidate, "
                       "and no unresolved dangerous alternative remains." if not no_more_value else
                       "No further question/exam/test would meaningfully change the current ranking.")
        else:
            reason = "Insufficient confidence, unresolved dangerous alternative, or differential too close to call."

        return StopDecision(should_diagnose=should_diagnose, forced=False, reason=reason,
                             readiness_score=round(readiness_score, 3), blockers=blockers)
