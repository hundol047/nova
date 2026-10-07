"""SOAP provenance / evidence-integrity checker (development + test tooling, never shipped).

Every factual statement in a SOAP note's Subjective and Objective blocks must be traceable to the
encounter log: the first patient statement, the initial vitals, an actual ASK answer, or an actual
successful EXAM result. The checker re-derives nothing from the diagnosis; it compares the rendered
note with ``PatientState.performed_actions`` and reports every line it cannot trace.

Violations are plain dicts ``{"block", "line", "rule", "detail"}``; an empty list means the note is
fully traceable. ``retention`` measures the opposite failure (patient information lost in the note).
"""
from __future__ import annotations

import re
from typing import Dict, List

from nova_agent.soap import _labels, classify_answer
from nova_agent.state import PatientState
from nova_agent.taxonomy import EXAM_CATALOG

_TOKEN = re.compile(r"[0-9]+(?:[./][0-9]+)?|[A-Za-z]{2,}|[가-힣]+|[぀-ヿ一-鿿]+")
_DOSE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|µg|ug|g|ml|mL|units?|iu|mEq|mmol)\b", re.IGNORECASE)
_RESULT_WORDS = re.compile(r"\b(?:normal|negative|unremarkable|within normal|positive|elevated|abnormal)\b|정상|음성|양성|이상 없", re.IGNORECASE)


def _tokens(text: str) -> set:
    return {t.lower() for t in _TOKEN.findall(text or "")}


def _violation(block: str, line: str, rule: str, detail: str = "") -> Dict[str, str]:
    return {"block": block, "line": line, "rule": rule, "detail": detail}


def _source_tokens(state: PatientState, L: Dict[str, str]) -> set:
    pool = _tokens(state.chief_complaint or "") | _tokens(state.initial_vitals_text or "")
    for turn in state.performed_actions:
        if turn.action_type == "ASK":
            pool |= _tokens(turn.result) | _tokens(turn.key.replace("_", " "))
    for value in L.values():
        pool |= _tokens(value)
    return pool


def check_subjective(state: PatientState, soap: Dict[str, str], lang: str) -> List[Dict[str, str]]:
    L = _labels(lang)
    out: List[Dict[str, str]] = []
    pool = _source_tokens(state, L)
    lines = soap["S"].splitlines()
    if not lines or lines[0] != f"{L['cc']}: {state.chief_complaint or L['none']}":
        out.append(_violation("S", lines[0] if lines else "", "chief_complaint_mismatch"))
    denied_budget = sum(1 for t in state.performed_actions
                        if t.action_type == "ASK" and classify_answer(t.result) == "denied")
    denied_shown = sum(line.count(L["denied"]) for line in lines[1:])
    for line in lines[1:]:
        for token in _tokens(line):
            if token not in pool:
                out.append(_violation("S", line, "untraceable_token", token))
    if denied_shown > denied_budget:
        out.append(_violation("S", "", "denial_without_source", f"{denied_shown} shown vs {denied_budget} sourced"))
    return out


def check_objective(state: PatientState, soap: Dict[str, str], lang: str) -> List[Dict[str, str]]:
    L = _labels(lang)
    out: List[Dict[str, str]] = []
    exam_turns = {t.turn: t for t in state.performed_actions if t.action_type == "EXAM"}
    seen_exam_results = 0
    for line in soap["O"].splitlines():
        if line in (L["no_exam"], L["tests_none"]):
            continue
        m = re.match(r"^\[T0 [^\]]*\] (.+?): (.*)$", line)
        if m:
            if m.group(1) != L["vitals"] or m.group(2) != (state.initial_vitals_text or ""):
                out.append(_violation("O", line, "initial_vitals_mismatch"))
            continue
        m = re.match(r"^\[T(\d+)\] (.+?): (.*)$", line)
        if m:
            turn = exam_turns.get(int(m.group(1)))
            spec = EXAM_CATALOG.get(turn.key) if turn else None
            name = ((spec["name_ko"] if lang == "ko" else spec["name_en"]) if spec else (turn.key if turn else None))
            if turn is None or m.group(2) != name or m.group(3) != ((turn.result or "").strip() or L["none"]):
                out.append(_violation("O", line, "exam_line_not_in_log"))
            seen_exam_results += 1
            continue
        m = re.match(r"^\[-\] (.+?): (.*)$", line)
        if m and m.group(2) == L["rejected"] and state.rejected_exams:
            if _RESULT_WORDS.search(m.group(2)):
                out.append(_violation("O", line, "rejected_exam_given_finding"))
            continue
        out.append(_violation("O", line, "untraceable_objective_line"))
    if seen_exam_results != len(exam_turns):
        out.append(_violation("O", "", "exam_result_omitted", f"{len(exam_turns) - seen_exam_results} missing"))
    if any(t.action_type == "TEST" for t in state.performed_actions):
        out.append(_violation("O", "", "test_performed_in_preliminary"))
    return out


def check_assessment_plan(soap: Dict[str, str], lang: str) -> List[Dict[str, str]]:
    L = _labels(lang)
    out: List[Dict[str, str]] = []
    primaries = [ln for ln in soap["A"].splitlines() if ln.startswith(f"{L['dx']}:")]
    if len(primaries) != 1:
        out.append(_violation("A", "", "not_exactly_one_primary_diagnosis", str(len(primaries))))
    for key in ("basis", "contra", "missing", "ddx"):
        if not any(ln.startswith(f"{L[key]}:") for ln in soap["A"].splitlines()):
            out.append(_violation("A", "", "assessment_section_missing", key))
    for key in ("tests", "tx", "fu", "edu"):
        if not any(ln.startswith(f"{L[key]}:") for ln in soap["P"].splitlines()):
            out.append(_violation("P", "", "plan_section_missing", key))
    if _DOSE.search(soap["P"]) or _DOSE.search(soap["A"]):
        out.append(_violation("P", "", "unsupported_dose"))
    return out


def check_soap(state: PatientState, soap: Dict[str, str], lang: str = "en") -> List[Dict[str, str]]:
    return check_subjective(state, soap, lang) + check_objective(state, soap, lang) + check_assessment_plan(soap, lang)


def retention(state: PatientState, soap: Dict[str, str]) -> Dict[str, float]:
    """Share of non-denial ASK answers whose full text survives in S (information retention)."""
    kept = total = 0
    for turn in state.performed_actions:
        if turn.action_type != "ASK" or not (turn.result or "").strip():
            continue
        if classify_answer(turn.result) == "denied":
            continue
        total += 1
        kept += (turn.result or "").strip() in soap["S"]
    return {"answers": total, "retained": kept, "retention": (kept / total) if total else 1.0}
