"""Preliminary-round episode driver (LOCAL DEVELOPMENT / PRELIMINARY SIMULATION; never an official score).

Plays a SyntheticCase against ``competition.adapter.NovaCompetitionAgent(preliminary=True)`` -- the same
adapter path the submission will use -- through the wire actions SAY / EXAM / DIAGNOSE only. The
simulated patient answers from the case's scripted answer for the internal key behind the agent's
question; ground truth is never given to the agent. A TEST action, an over-long SAY, a multi-question
SAY, a multi-maneuver EXAM, more than ``MAX_INTERACTIONS`` interactions, or a malformed wire action is
recorded as a rule violation.

Organizer assumptions live in ``ORGANIZER_ASSUMPTIONS`` (uncertain; to be replaced by the real guide).
"""
from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from competition.adapter import NovaCompetitionAgent
from evaluation.cases import SyntheticCase
from evaluation.soap_provenance import check_soap, retention
from nova_agent.diagnosis_normalizer import same_diagnosis
from nova_agent.llm_client import MockLLMClient
from nova_agent.orchestrator import DoctorAgent
from nova_agent.preliminary import SAY_MAX_CHARS
from nova_agent.semantic_dedup import semantic_category_for_text

# Centralised, clearly-marked UNCERTAIN organizer assumptions (briefing of 2026-10-06 as transcribed by the
# team). The final guide may change any of them; only this layer and competition/ should need to follow.
ORGANIZER_ASSUMPTIONS = {
    "MAX_INTERACTIONS": (50, "UNCONFIRMED: briefing slide; public web page may differ"),
    "SAY_MAX_CHARS": (SAY_MAX_CHARS, "UNCONFIRMED: briefing slide"),
    "MAX_MINUTES_PER_CASE": (20, "UNCONFIRMED: briefing slide; not simulated here"),
    "TEST_AVAILABLE": (False, "UNCONFIRMED: briefing slide"),
    "REJECTED_EXAM_CHARGED": (False, "UNCONFIRMED: simulator conservatively counts rejections toward the cap"),
}
MAX_INTERACTIONS = ORGANIZER_ASSUMPTIONS["MAX_INTERACTIONS"][0]
LABEL = "LOCAL DEVELOPMENT / PRELIMINARY SIMULATION -- mock LLM, synthetic cases, NOT AN OFFICIAL SCORE"

_QMARK = re.compile(r"[?？]")
_MULTI_MANEUVER = re.compile(r"\s(?:and|then)\s|[,;]|\s및\s|그리고|하고\s|そして|并且|以及")


@dataclass
class Environment:
    """Simulated examiner. ``unsupported_exams``: exam ids the organizer 'does not support' (rejected with
    request-scoped wording and no finding)."""
    unsupported_exams: frozenset = frozenset()
    rejection_text: str = "Request not supported."
    # Round Q (separate evaluation-tool option, OFF by default -- the frozen results never use it): answer a question
    # the case did not script with "not sure" instead of the case's default "No", so an unscripted feature is not
    # reported as denied. Scripted answers, exam results, labels and scoring are unchanged.
    unscripted_unknown: bool = False


@dataclass
class Episode:
    case: SyntheticCase
    wire: List[dict] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)
    result: Dict[str, object] = field(default_factory=dict)


def _is_correct(name: Optional[str], truth: str) -> bool:
    if not name:
        return False
    parts = [name] + [p.strip(" ()") for p in name.replace("(", "|").split("|")]
    return any(same_diagnosis(p, truth) for p in parts if p)


def check_wire(action: dict, interactions: int) -> List[str]:
    kind, content = action.get("action_type"), action.get("content")
    bad: List[str] = []
    if kind not in {"SAY", "EXAM", "DIAGNOSE"}:
        return [f"forbidden_action_type:{kind}"]
    if not isinstance(content, str) or not content.strip():
        bad.append("empty_content")
        return bad
    if kind == "SAY":
        if len(content) > SAY_MAX_CHARS:
            bad.append("say_over_limit")
        if len(_QMARK.findall(content)) > 1 or "\n" in content:
            bad.append("say_multi_question")
    if kind == "EXAM" and (_MULTI_MANEUVER.search(content) or "\n" in content):
        bad.append("exam_multi_maneuver")
    if kind == "DIAGNOSE":
        soap = action.get("soap") or {}
        if not action.get("primary_diagnosis") or not all(str(soap.get(k, "")).strip() for k in "SOAP"):
            bad.append("diagnose_missing_soap_or_primary")
    if kind != "DIAGNOSE" and interactions >= MAX_INTERACTIONS:
        bad.append("over_interaction_cap")
    return bad


class _DecideSpy:
    """Captures, per case id, the last differential and state the engine produced (evaluation-side only)."""

    def __init__(self, inner: DoctorAgent) -> None:
        self.inner, self.original, self.captured = inner, inner.decide, {}
        inner.decide = self._spy  # instance-level wrapper, removed by close()

    def _spy(self, state):
        out = self.original(state)
        self.captured[state.case_id] = {"differential": out[2], "state": state}
        return out

    def close(self) -> None:
        self.inner.decide = self.original


def _episode(case: SyntheticCase, agent: NovaCompetitionAgent, env: Environment, spy: _DecideSpy,
             observation_hook: Optional[Callable[[dict], dict]] = None):
    """Generator: yields after every wire action; its return value is the finished Episode."""
    ep = Episode(case)
    obs = {"case_id": case.case_id, "observation_type": "initial", "chief_complaint": case.chief_complaint,
           "demographics": case.demographics, "vital_signs": case.exam_results.get("vital_signs")}
    interactions = rejected = say_n = exam_n = 0
    say_cats: List[str] = []
    seen, dup, sem_dup = set(), 0, 0
    while True:
        action = agent.act(obs if observation_hook is None else observation_hook(obs))
        ep.wire.append(action)
        kind = action.get("action_type")
        ep.violations += check_wire(action, interactions)
        yield ep
        if kind == "DIAGNOSE":
            break
        interactions += 1
        pending = agent._pending_actions[case.case_id]
        signature = (kind, pending.key)
        dup += signature in seen
        seen.add(signature)
        if kind == "SAY":
            say_n += 1
            if pending.key in {"explanation", "plan_explanation"}:
                reply = "네, 알겠습니다."
            else:
                cat = semantic_category_for_text("ASK", action["content"])
                base = pending.key.split(":")[0]
                sem_dup += bool(cat and cat == base and base in say_cats)
                say_cats.append(base)
                default = case.default_answer
                if env.unscripted_unknown:
                    default = "잘 모르겠어요." if re.search(r"[가-힣]", case.default_answer or "") else "I'm not sure."
                reply = case.answers.get(pending.key, default)
            obs = {"case_id": case.case_id, "observation_type": "say_response", "content": reply}
        else:
            exam_n += 1
            if pending.key in env.unsupported_exams:
                rejected += 1
                obs = {"case_id": case.case_id, "observation_type": "exam_result", "content": env.rejection_text,
                       "raw": {"rejected": True}}
            else:
                obs = {"case_id": case.case_id, "observation_type": "exam_result",
                       "content": case.exam_results.get(pending.key, case.default_exam_result)}
        if interactions > MAX_INTERACTIONS + 5:  # runaway guard; flagged as a violation
            ep.violations.append("runaway_episode")
            break
    ep.result = _score(case, ep, spy.captured.get(case.case_id, {"differential": [], "state": None}),
                       interactions, say_n, exam_n, rejected, dup, sem_dup)
    return ep


def run_episode(case: SyntheticCase, agent: Optional[NovaCompetitionAgent] = None, env: Optional[Environment] = None,
                observation_hook: Optional[Callable[[dict], dict]] = None) -> Episode:
    """One full encounter. ``agent`` may be reused across cases (that is exactly what the isolation tests do)."""
    own = agent is None
    agent = agent or NovaCompetitionAgent(agent=DoctorAgent(llm_client=MockLLMClient()), preliminary=True)
    spy = _DecideSpy(agent.agent)
    try:
        gen = _episode(case, agent, env or Environment(), spy, observation_hook)
        while True:
            try:
                next(gen)
            except StopIteration as done:
                return done.value
    finally:
        spy.close()
        if own:
            agent.close_case(case.case_id)


def run_interleaved(cases: List[SyntheticCase], agent: NovaCompetitionAgent, env: Optional[Environment] = None) -> List[Episode]:
    """Round-robin ONE wire action per case on the SAME agent, so patient states coexist in the adapter."""
    spy = _DecideSpy(agent.agent)
    try:
        gens = [_episode(c, agent, env or Environment(), spy) for c in cases]
        done: List[Optional[Episode]] = [None] * len(cases)
        while any(d is None for d in done):
            for i, gen in enumerate(gens):
                if done[i] is None:
                    try:
                        next(gen)
                    except StopIteration as fin:
                        done[i] = fin.value
        return done  # type: ignore[return-value]
    finally:
        spy.close()


def _unresolved_critical(differential: list, state) -> int:
    from nova_agent.resolution import is_resolved
    n = 0
    for item in differential[1:5]:
        if item.dangerous_if_missed and not is_resolved(item.diagnosis_id, list(item.contradictory_evidence), state):
            n += 1
    return n


def _unnecessary_exams(case, ep, differential) -> int:
    """EXAM requests that no diagnosis the agent actually weighed (truth + final top-5) lists as discriminating,
    apart from the always-useful vital signs / general appearance. A development proxy, not clinical advice."""
    from nova_agent.knowledge.retrieval import disease_by_id
    useful = {"vital_signs", "general_appearance"}
    for diagnosis_id in [case.ground_truth_diagnosis] + [d.diagnosis_id for d in (differential or [])[:5]]:
        entry = disease_by_id(diagnosis_id)
        if entry:
            useful.update(entry.get("discriminating_exams", []))
    asked = [w["metadata"].get("key") for w in ep.wire if w["action_type"] == "EXAM"]
    return sum(1 for k in asked if k not in useful)


def _score(case, ep, captured, interactions, say_n, exam_n, rejected, dup, sem_dup) -> Dict[str, object]:
    final = ep.wire[-1]
    differential = captured["differential"] or []
    state = captured["state"]
    primary = final.get("primary_diagnosis")
    key = (final.get("metadata") or {}).get("key", "")
    top1 = _is_correct(primary, case.ground_truth_diagnosis) or same_diagnosis(key, case.ground_truth_diagnosis)
    names = [d.diagnosis for d in differential]
    top3 = top1 or any(_is_correct(n, case.ground_truth_diagnosis) for n in names[:3])
    top5 = top1 or any(_is_correct(n, case.ground_truth_diagnosis) for n in names[:5])
    truth_rank = next((i + 1 for i, n in enumerate(names) if _is_correct(n, case.ground_truth_diagnosis)), None)
    truth_item = differential[truth_rank - 1] if truth_rank else None
    soap = final.get("soap") or {}
    lang = (state.locale if state is not None else None) or "en"
    prov = check_soap(state, soap, lang) if (state is not None and soap) else [{"rule": "no_soap"}]
    ret = retention(state, soap) if (state is not None and soap) else {"answers": 0, "retained": 0, "retention": 0.0}
    unresolved = _unresolved_critical(differential, state) if state is not None else 0
    gathered = say_n + exam_n
    return dict(
        case_id=case.case_id, category=case.category, scored=case.scoring_expected, critical=case.critical,
        truth=case.ground_truth_diagnosis, primary=primary, top1=top1, top3=top3, top5=top5,
        critical_miss=bool(case.critical and not top1),
        interactions=interactions, says=say_n, exams=exam_n, rejected_exams=rejected,
        duplicate_actions=dup, semantic_duplicate_questions=sem_dup,
        unnecessary_exams=_unnecessary_exams(case, ep, differential),
        premature=bool(gathered < 3 or (not top1 and unresolved)),
        unresolved_critical_at_diagnosis=unresolved, soap_complete=not any(
            v["rule"] in {"assessment_section_missing", "plan_section_missing", "no_soap", "not_exactly_one_primary_diagnosis"}
            for v in prov),
        soap_unsupported=len([v for v in prov if v["rule"] not in {"assessment_section_missing", "plan_section_missing"}]),
        soap_retention=ret["retention"], soap_answers=ret["answers"],
        rule_violations=len(ep.violations), violation_kinds=sorted(set(ep.violations)),
        malformed=any(v.startswith(("empty_content", "diagnose_missing")) for v in ep.violations),
        llm_calls=getattr(state, "llm_call_count", None), llm_fallbacks=getattr(state, "llm_fallback_count", None),
        truth_rank=truth_rank, differential_size=len(names),
        truth_supporting=list(truth_item.supporting_evidence) if truth_item else [],
        truth_contradictory=list(truth_item.contradictory_evidence) if truth_item else [],
        top_supporting=list(differential[0].supporting_evidence) if differential else [],
        language=("ko" if re.search(r"[가-힣]", case.chief_complaint) else "ja/zh" if re.search(r"[぀-ヿ一-鿿]", case.chief_complaint) else "en"),
        explained_before_diagnose=any(w["action_type"] == "SAY" and (w.get("metadata") or {}).get("key") == "explanation"
                                      for w in ep.wire),
    )


def summarize(rows: List[Dict[str, object]]) -> Dict[str, object]:
    if not rows:
        return {"cases": 0}
    scored = [r for r in rows if r["scored"]]
    crit = [r for r in scored if r["critical"]]
    n = len(rows)
    turns = [r["interactions"] for r in rows]
    asked = sum(r["says"] for r in rows) or 1
    unsupported_total = sum(r["soap_unsupported"] for r in rows)
    answers = sum(r["soap_answers"] for r in rows)
    return {
        "label": LABEL, "cases": n, "scored": len(scored),
        "top1": sum(r["top1"] for r in scored) / max(1, len(scored)),
        "top3": sum(r["top3"] for r in scored) / max(1, len(scored)),
        "top5": sum(r["top5"] for r in scored) / max(1, len(scored)),
        "critical_cases": len(crit),
        "critical_recall": (sum(r["top1"] for r in crit) / len(crit)) if crit else None,
        "critical_miss_rate": (sum(r["critical_miss"] for r in crit) / len(crit)) if crit else None,
        "avg_interactions": statistics.mean(turns), "median_interactions": statistics.median(turns), "max_interactions": max(turns),
        "say_count": sum(r["says"] for r in rows), "exam_count": sum(r["exams"] for r in rows),
        "rejected_exam_count": sum(r["rejected_exams"] for r in rows),
        "unnecessary_exam_share": sum(r["unnecessary_exams"] for r in rows) / max(1, sum(r["exams"] for r in rows)),
        "duplicate_action_rate": sum(r["duplicate_actions"] for r in rows) / max(1, sum(turns)),
        "semantic_duplicate_question_rate": sum(r["semantic_duplicate_questions"] for r in rows) / asked,
        "premature_diagnosis_rate": sum(r["premature"] for r in rows) / n,
        "unresolved_critical_alternative_rate": sum(1 for r in rows if r["unresolved_critical_at_diagnosis"]) / n,
        "soap_completeness": sum(r["soap_complete"] for r in rows) / n,
        "soap_information_retention": (sum(r["soap_retention"] * r["soap_answers"] for r in rows) / answers) if answers else 1.0,
        "soap_unsupported_info_rate": sum(1 for r in rows if r["soap_unsupported"]) / n,
        "soap_unsupported_lines": unsupported_total,
        "explained_before_diagnose_rate": sum(r["explained_before_diagnose"] for r in rows) / n,
        "rule_violations": sum(r["rule_violations"] for r in rows),
        "malformed_output_rate": sum(r["malformed"] for r in rows) / n,
        "llm_fallback_turns": sum((r["llm_fallbacks"] or 0) for r in rows),
        "cases_over_cap": sum(r["interactions"] > MAX_INTERACTIONS for r in rows),
    }
