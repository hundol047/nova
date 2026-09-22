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

from collections import OrderedDict
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel

from nova_agent.action_canonicalizer import canonicalize_action
from nova_agent.action_selector import AgentAction, ScoredCandidate
from nova_agent.config import get_config
from nova_agent.diagnosis_normalizer import normalize_diagnosis
from nova_agent.differential import DifferentialItem
from nova_agent.knowledge.retrieval import disease_by_id
from nova_agent.llm_schema import AgentTurnOutput
from nova_agent.resolution import is_resolved
from nova_agent.safety import SafetyFinding
from nova_agent.semantic_dedup import is_semantic_duplicate
from nova_agent.state import PatientState, normalize_key
from nova_agent.stop_policy import StopDecision

CandidatePool = Dict[Tuple[str, str], ScoredCandidate]


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
        top_k = get_config().top_k_differential

        if llm_output is not None and llm_output.differential:
            # LLM differential validation hardening (spec section 10): canonicalize each entry,
            # merge (not just skip) duplicates -- two items resolving to the same diagnosis_id
            # pool their evidence instead of the second silently vanishing or double-counting --
            # then rank by the LLM's own stated order (clamped/defaulted for garbage values like
            # rank=0, rank=999, or a missing/duplicate rank) and reassign clean sequential ranks.
            by_id: "OrderedDict[str, DifferentialItem]" = OrderedDict()
            for item in llm_output.differential:
                diagnosis_id = item.diagnosis_id or normalize_diagnosis(item.diagnosis).canonical_id
                entry = disease_by_id(diagnosis_id) if diagnosis_id else None
                # Known-diagnosis metadata (dangerous/urgency) is authoritative from the local KB
                # once matched -- the LLM can only ever ADD a dangerous flag it wasn't given
                # credit for, never suppress one the KB already asserts.
                dangerous = item.dangerous_if_missed or bool(entry and entry.get("dangerous"))
                urgency = entry.get("urgency") if entry else ("CRITICAL" if dangerous else "LOW")
                resolved_id = diagnosis_id or f"novel:{normalize_key(item.diagnosis)}"
                raw_rank = item.rank if 1 <= item.rank <= 1000 else 1000
                det_match = det_by_id.get(resolved_id)
                score = det_match.score if det_match else 0.0
                score_ratio = det_match.score_ratio if det_match else band_proxy[item.confidence]

                if resolved_id in by_id:
                    existing = by_id[resolved_id]
                    existing.supporting_evidence = list(dict.fromkeys(existing.supporting_evidence + item.supporting_evidence))
                    existing.contradictory_evidence = list(dict.fromkeys(existing.contradictory_evidence + item.contradictory_evidence))
                    existing.dangerous_if_missed = existing.dangerous_if_missed or dangerous
                    existing.rank = min(existing.rank, raw_rank)
                    continue

                by_id[resolved_id] = DifferentialItem(
                    diagnosis=item.diagnosis, diagnosis_id=resolved_id, rank=raw_rank, score=score,
                    score_ratio=score_ratio, supporting_evidence=list(item.supporting_evidence),
                    contradictory_evidence=list(item.contradictory_evidence),
                    missing_discriminative_evidence=item.missing_information,
                    urgency=urgency or "LOW", dangerous_if_missed=dangerous, confidence_band=item.confidence,
                )

            ordered = sorted(by_id.values(), key=lambda d: d.rank)[:top_k]
            for new_rank, d in enumerate(ordered, start=1):
                d.rank = new_rank
            merged = ordered
            # Based on the POST-truncation list: a diagnosis cut by the top-K cap is no longer
            # actually present in `merged`, so it must not be treated as "seen" -- otherwise a
            # dangerous diagnosis that got capped out would never get re-injected by the
            # safety-finding pass below.
            seen_ids = {d.diagnosis_id for d in merged}
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
            # DIAGNOSE key/content consistency (spec section 9): a malformed output where `key`
            # and `content` name two DIFFERENT known diagnoses (e.g. key="gerd",
            # content="Acute Myocardial Infarction") must never be trusted at face value -- reject
            # it outright rather than guessing which one the model "really" meant.
            key_norm = normalize_diagnosis(picked.key) if picked.key else None
            content_norm = normalize_diagnosis(picked.content) if picked.content else None
            if (key_norm and key_norm.mapped and content_norm and content_norm.mapped
                    and key_norm.canonical_id != content_norm.canonical_id):
                return ValidationResult(
                    action=deterministic_action, differential=merged_differential, overridden=True,
                    override_reason=f"Blocked inconsistent DIAGNOSE: key {picked.key!r} resolves to "
                                     f"{key_norm.canonical_id!r} but content {picked.content!r} resolves to "
                                     f"{content_norm.canonical_id!r}.",
                )

            llm_diagnosis_id = picked.key or (normalize_diagnosis(picked.content).canonical_id or "")
            unresolved = [
                d for d in merged_differential
                if d.dangerous_if_missed and d.diagnosis_id != llm_diagnosis_id
                and not is_resolved(d.diagnosis_id, d.contradictory_evidence, state)
            ]
            if unresolved:
                return ValidationResult(
                    action=deterministic_action, differential=merged_differential, overridden=True,
                    override_reason=f"Blocked premature DIAGNOSE: {unresolved[0].diagnosis} is dangerous, "
                                     "still plausible, and has not been worked up yet.",
                )

            # Minimum readiness gate (spec section 8): "no unresolved dangerous alternative" alone
            # doesn't rule out a low-confidence, thinly-evidenced DIAGNOSE for a NON-dangerous
            # diagnosis. Require either the deterministic stop policy to independently agree it's
            # time to stop (readiness_score/gap/confidence-band based, computed from the KB prior,
            # not from any LLM/novel-diagnosis proxy score), OR a minimum turn count + evidence
            # bar on the LLM's own chosen diagnosis -- so an under-evidenced DIAGNOSE is blocked
            # regardless of which diagnosis it names, not only ones that happen to leave a
            # dangerous alternative dangling.
            cfg = get_config().stop_policy
            llm_item = next((d for d in merged_differential if d.diagnosis_id == llm_diagnosis_id), None)
            evidence_count = len(llm_item.supporting_evidence) if llm_item else 0
            minimally_ready = stop_decision.should_diagnose or (
                state.turn_count >= cfg.min_turns_before_diagnose and evidence_count >= cfg.min_evidence_items
            )
            if not minimally_ready:
                return ValidationResult(
                    action=deterministic_action, differential=merged_differential, overridden=True,
                    override_reason=f"Blocked low-confidence DIAGNOSE: only {evidence_count} supporting evidence "
                                     f"item(s) for {picked.content!r} after {state.turn_count} turn(s) (need >= "
                                     f"{cfg.min_evidence_items} after >= {cfg.min_turns_before_diagnose} turns, or "
                                     "the deterministic stop policy to independently agree it's ready).",
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
            # Hybrid candidate expansion (spec section 5): the key wasn't in this turn's
            # KB-differential-derived pool -- which is expected whenever the LLM is reasoning
            # about a novel diagnosis outside the local knowledge base -- so try to canonicalize
            # the LLM's proposal onto a REAL taxonomy entry before giving up on it entirely.
            canonicalized = canonicalize_action(picked.type, picked.key, picked.content, state)
            if canonicalized is not None:
                return ValidationResult(action=canonicalized, differential=merged_differential, overridden=False)
            return ValidationResult(action=deterministic_action, differential=merged_differential, overridden=True,
                                     override_reason=f"selected_action key {picked.key!r} is not a known "
                                                      f"{picked.type} in this turn's legal candidate pool, and "
                                                      "could not be canonicalized onto any real taxonomy entry.")
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
