"""Deterministic Safety Guard + Structured Action Validation (spec sections 2/24A).

This is the ONLY place an LLM-proposed turn output gets overridden. It does not try to force the
LLM toward a single "correct" deterministic answer -- it blocks a small, explicit list of hard
violations:

  - a diagnosis submitted while a dangerous, unresolved, not-yet-worked-up alternative exists
  - a duplicate ASK/EXAM/TEST
  - an ASK/EXAM/TEST key that isn't in the legal candidate pool (hallucinated / unknown / invalid)
  - an unrecognized action type, or no usable LLM output at all (malformed/timeout/exception)
  - the turn limit (a hard override that beats every other consideration)

Any other LLM choice -- including introducing a new differential diagnosis outside the local
knowledge base, re-ranking existing ones, or picking a legal action that is NOT the deterministic
utility-argmax -- is accepted as-is. This is what makes the LLM a real clinical reasoner instead of
a phrasing layer over a fixed deterministic pick.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel

from nova_agent.action_selector import AgentAction, ScoredCandidate
from nova_agent.diagnosis_normalizer import normalize_diagnosis
from nova_agent.differential import DifferentialItem
from nova_agent.knowledge.retrieval import disease_by_id
from nova_agent.llm_schema import AgentTurnOutput
from nova_agent.safety import SafetyFinding
from nova_agent.semantic_dedup import is_semantic_duplicate
from nova_agent.state import PatientState, normalize_key
from nova_agent.stop_policy import StopDecision

CandidatePool = Dict[Tuple[str, str], ScoredCandidate]


def _fully_worked_up(diagnosis_id: str, state: PatientState) -> bool:
    """True once every discriminating exam/test the knowledge base lists for this diagnosis has
    already been performed (so a dangerous alternative that WAS actively investigated and still
    shows nothing stops blocking further action -- see stop_policy.py's identical helper, which
    this mirrors for the same reason)."""
    entry = disease_by_id(diagnosis_id)
    if not entry:
        return True
    required = set(entry.get("discriminating_exams", [])) | set(entry.get("discriminating_tests", []))
    if not required:
        return True
    done = set(state.completed_examinations) | set(state.completed_tests)
    return required.issubset(done)


def build_candidate_pool(candidates: List[ScoredCandidate]) -> CandidatePool:
    return {(c.action_type, c.key): c for c in candidates if c.action_type != "DIAGNOSE"}


class ValidationResult(BaseModel):
    action: AgentAction
    differential: List[DifferentialItem]
    overridden: bool
    override_reason: str = ""

    model_config = {"arbitrary_types_allowed": True}


class SafetyValidator:
    def merge_differential(self, llm_output: Optional[AgentTurnOutput],
                            deterministic_differential: List[DifferentialItem],
                            safety_findings: List[SafetyFinding]) -> List[DifferentialItem]:
        """LLM's differential (when present and non-empty) is authoritative for ranking and
        evidence -- including introducing diagnoses outside the local knowledge base. The
        deterministic knowledge-based ranking is only the fallback when there's no usable LLM
        output. Either way, every currently-active SafetyFinding's diagnosis is guaranteed to be
        present somewhere in the result: it can never silently disappear just because the LLM (or
        a malformed/absent response) left it out."""
        # score/score_ratio are internal ranking numbers, deliberately not part of the LLM-facing
        # schema (spec section 4: never hand the model something that looks like a calibrated
        # probability). When the LLM's diagnosis matches one the deterministic engine already
        # scored, that real score is reused here (so stop_policy's gap/readiness math keeps
        # working on real numbers); a genuinely novel LLM-introduced diagnosis gets a coarse
        # bandderived proxy instead of a fabricated-looking precise number.
        det_by_id = {d.diagnosis_id: d for d in deterministic_differential}
        band_proxy = {"HIGH": 0.75, "MEDIUM": 0.45, "LOW": 0.15}

        if llm_output is not None and llm_output.differential:
            merged: List[DifferentialItem] = []
            seen_ids = set()
            for item in llm_output.differential:
                diagnosis_id = item.diagnosis_id or normalize_diagnosis(item.diagnosis).canonical_id
                entry = disease_by_id(diagnosis_id) if diagnosis_id else None
                dangerous = item.dangerous_if_missed or bool(entry and entry.get("dangerous"))
                urgency = entry.get("urgency") if entry else ("CRITICAL" if dangerous else "LOW")
                resolved_id = diagnosis_id or f"novel:{normalize_key(item.diagnosis)}"
                det_match = det_by_id.get(resolved_id)
                score = det_match.score if det_match else 0.0
                score_ratio = det_match.score_ratio if det_match else band_proxy[item.confidence]
                merged.append(DifferentialItem(
                    diagnosis=item.diagnosis, diagnosis_id=resolved_id, rank=item.rank, score=score,
                    score_ratio=score_ratio, supporting_evidence=item.supporting_evidence,
                    contradictory_evidence=item.contradictory_evidence,
                    missing_discriminative_evidence=item.missing_information,
                    urgency=urgency or "LOW", dangerous_if_missed=dangerous, confidence_band=item.confidence,
                ))
                seen_ids.add(resolved_id)
        else:
            merged = list(deterministic_differential)
            seen_ids = {d.diagnosis_id for d in merged}

        next_rank = len(merged) + 1
        for finding in safety_findings:
            if finding.diagnosis_id in seen_ids:
                continue
            entry = disease_by_id(finding.diagnosis_id)
            if not entry:
                continue
            merged.append(DifferentialItem(
                diagnosis=entry["name"], diagnosis_id=finding.diagnosis_id, rank=next_rank, score=0.0,
                score_ratio=0.0, supporting_evidence=finding.evidence, contradictory_evidence=[],
                missing_discriminative_evidence=[], urgency=finding.urgency,
                dangerous_if_missed=True, confidence_band="LOW",
            ))
            seen_ids.add(finding.diagnosis_id)
            next_rank += 1
        return merged

    def validate_action(self, state: PatientState, llm_output: Optional[AgentTurnOutput],
                         candidate_pool: CandidatePool, deterministic_action: AgentAction,
                         merged_differential: List[DifferentialItem], stop_decision: StopDecision) -> ValidationResult:
        # Hard override #1: the turn limit beats everything else, LLM included.
        if stop_decision.forced:
            content = deterministic_action.content
            if llm_output is not None and llm_output.selected_action.type == "DIAGNOSE" and llm_output.selected_action.content:
                content = llm_output.selected_action.content  # keep the LLM's phrasing/diagnosis if it agrees
            action = AgentAction(action_type="DIAGNOSE", key=deterministic_action.key, content=content,
                                  rationale=stop_decision.reason)
            return ValidationResult(action=action, differential=merged_differential, overridden=False)

        if llm_output is None:
            return ValidationResult(action=deterministic_action, differential=merged_differential, overridden=True,
                                     override_reason="No usable LLM output (malformed/timeout/exception); "
                                                      "used deterministic fallback action.")

        picked = llm_output.selected_action

        if picked.type == "DIAGNOSE":
            llm_diagnosis_id = picked.key or (normalize_diagnosis(picked.content).canonical_id or "")
            unresolved = [
                d for d in merged_differential
                if d.dangerous_if_missed and d.diagnosis_id != llm_diagnosis_id
                and not d.contradictory_evidence and not _fully_worked_up(d.diagnosis_id, state)
            ]
            if unresolved:
                return ValidationResult(
                    action=deterministic_action, differential=merged_differential, overridden=True,
                    override_reason=f"Blocked premature DIAGNOSE: {unresolved[0].diagnosis} is dangerous, "
                                     "still plausible, and has not been worked up yet.",
                )
            content = picked.content or (merged_differential[0].diagnosis if merged_differential else deterministic_action.content)
            key = picked.key or (merged_differential[0].diagnosis_id if merged_differential else "unknown")
            action = AgentAction(action_type="DIAGNOSE", key=key, content=content,
                                  rationale="LLM-selected diagnosis; passed deterministic safety validation "
                                            "(no unresolved dangerous alternative).")
            return ValidationResult(action=action, differential=merged_differential, overridden=False)

        if picked.type not in {"ASK", "EXAM", "TEST"}:
            return ValidationResult(action=deterministic_action, differential=merged_differential, overridden=True,
                                     override_reason=f"Unrecognized action type {picked.type!r}.")

        pool_entry = candidate_pool.get((picked.type, picked.key))
        if pool_entry is None:
            return ValidationResult(action=deterministic_action, differential=merged_differential, overridden=True,
                                     override_reason=f"selected_action key {picked.key!r} is not a known "
                                                      f"{picked.type} in this turn's legal candidate pool.")
        if state.is_duplicate(picked.type, picked.key):
            return ValidationResult(action=deterministic_action, differential=merged_differential, overridden=True,
                                     override_reason=f"selected_action {picked.type}:{picked.key!r} is a duplicate.")

        content = picked.content or pool_entry.content
        # Layer 3 defensive check (spec section 12): the LLM's own phrasing of `content` might
        # semantically match a DIFFERENT category than the `key` it claimed (e.g. a paraphrase
        # that keyword-maps onto an already-completed item) -- catch that even though the exact
        # key itself passed the layer-1 duplicate check above.
        if content != pool_entry.content and is_semantic_duplicate(picked.type, content, state):
            return ValidationResult(action=deterministic_action, differential=merged_differential, overridden=True,
                                     override_reason=f"selected_action content {content!r} semantically duplicates "
                                                      "an already-covered item.")
        action = AgentAction(action_type=picked.type, key=picked.key, content=content,
                              rationale="LLM-selected action; passed deterministic safety validation "
                                        "(legal, non-duplicate candidate).")
        return ValidationResult(action=action, differential=merged_differential, overridden=False)
