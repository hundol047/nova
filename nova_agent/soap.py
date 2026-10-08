"""SOAP initial-visit note for the preliminary-round DIAGNOSE action.

Organizer rule (2026-10-06 briefing): "what was asked or examined AND recorded counts; what was
written without being asked does not" -- so every Subjective/Objective line here is rebuilt from the
turn log (``PatientState.performed_actions``), never from the diagnosis the agent settled on.

    S  chief complaint, history of present illness, past history, medications, allergies, family
       and social history, review of systems -- including the negatives ("denies X" is recorded)
    O  physical-examination findings WITH the turn number in which each result arrived (the
       vital signs handed over with the first statement are turn 0); no test results in the
       preliminary round
    A  ONE primary diagnosis, its supporting findings, and a short differential
    P  tests/treatment/disposition/follow-up/education. Tests are listed as plan items because
       they cannot be ordered in the preliminary round. No drug doses are ever generated.

The plan is deliberately generic and safety-first (urgent diagnoses -> same-day emergency
evaluation); it is rule-derived from the knowledge base's own urgency/workup/red-flag fields, not
clinician-authored. Pure formatting: this module never changes which diagnosis is chosen.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from nova_agent.assertion_status import is_uncertain
from nova_agent.state import PatientState
from nova_agent.taxonomy import EXAM_CATALOG, TEST_CATALOG

_LABELS = {
    "ko": {
        "S": "S (주관적 정보)", "O": "O (객관적 정보)", "A": "A (평가)", "P": "P (계획)",
        "cc": "주호소", "hpi": "현병력", "pmh": "과거력", "meds": "복용 약물", "allergy": "알레르기",
        "fhx": "가족력", "shx": "사회력", "ros": "계통 문진", "not_asked": "문진하지 않음",
        "denied": "없음", "unclear": "불명확(확인 필요)", "initial": "초진 시", "vitals": "활력징후", "no_exam": "시행한 진찰 없음",
        "rejected": "요청 거절됨(결과 없음)", "tests_none": "검사 결과 없음(예선에서 검사 불가)",
        "dx": "주진단", "basis": "근거", "ddx": "감별진단", "no_basis": "특이 근거 부족",
        "against": "반대/부족 소견", "contra": "상충 소견", "missing": "확인되지 않은 감별 소견", "tests": "추가 검사", "tx": "치료·처치 결정", "fu": "추적",
        "edu": "환자 교육", "none": "없음",
        "tx_urgent": "응급 상황 가능성: 즉시 응급실 평가와 모니터링, 필요 시 즉각적인 처치",
        "tx_routine": "원인 질환 평가 후 증상 완화 중심의 보존적 관리, 위험 징후 시 상향 조정",
        "fu_urgent": "응급 평가 후 입원 여부 결정, 결과에 따라 즉시 재평가",
        "fu_routine": "증상 변화를 보며 필요 시 외래 재진, 악화·지속 시 조기 재평가",
        "edu_done": "진료 중 환자에게 설명함", "edu_diag": "진단 의심 사항 설명", "edu_plan": "다음 단계·경고 증상 설명", "edu_none": "진료 중 시행하지 않음(계획: 진단과 필요한 검사를 설명하고 경고 증상을 안내)",
        "red_flags": "경고 증상",
    },
    "en": {
        "S": "S (Subjective)", "O": "O (Objective)", "A": "A (Assessment)", "P": "P (Plan)",
        "cc": "Chief complaint", "hpi": "History of present illness", "pmh": "Past medical history",
        "meds": "Medications", "allergy": "Allergies", "fhx": "Family history", "shx": "Social history",
        "ros": "Review of systems", "not_asked": "not asked", "denied": "denied", "unclear": "unclear (needs confirmation)", "initial": "at presentation",
        "vitals": "Vital signs", "no_exam": "no examination performed", "rejected": "request rejected (no result)",
        "tests_none": "no test results (tests are unavailable in the preliminary round)",
        "dx": "Primary diagnosis", "basis": "Supporting findings", "ddx": "Differential diagnosis",
        "no_basis": "no specific supporting finding", "against": "against/lacking", "contra": "Contradictory findings", "missing": "Missing discriminating evidence", "tests": "Further tests",
        "tx": "Treatment / disposition decision", "fu": "Follow-up", "edu": "Patient education", "none": "none",
        "tx_urgent": "Possible emergency: immediate emergency-department evaluation and monitoring; urgent treatment as indicated",
        "tx_routine": "Evaluate the cause, then conservative symptom-directed care; escalate if warning signs appear",
        "fu_urgent": "Emergency evaluation, then decide on admission; reassess promptly with results",
        "fu_routine": "Outpatient re-evaluation as symptoms evolve; reassess early if worse or persistent",
        "edu_done": "delivered to the patient during the visit", "edu_diag": "working diagnosis explained", "edu_plan": "next step and warning signs explained", "edu_none": "not performed during the visit (plan: explain the diagnosis and needed tests, advise on the warning signs)",
        "red_flags": "Warning signs",
    },
}


def _labels(lang: str) -> Dict[str, str]:
    return _LABELS["ko" if lang == "ko" else "en"]


def localized_name(entry: Optional[dict], fallback: str, lang: str) -> str:
    """Display name: for Korean, the first Hangul alias of the entry when it has one."""
    if entry and lang == "ko":
        for alias in entry.get("aliases", []):
            if re.search(r"[가-힣]", alias):
                return alias
    return fallback


_PATIENT_UNSURE = re.compile(
    r"\b(?:not sure|unsure|don'?t know|do not know|dunno|maybe|perhaps|i think|i guess|not certain|"
    r"can'?t remember|cannot remember|don'?t remember|not really sure)\b"
    r"|모르겠|잘 모르|기억이 안|기억 안|아마|확실하지|わかりません|分かりません|たぶん|多分|覚えていません|不确定|不知道|不清楚|可能吧|不记得",
    re.IGNORECASE,
)


def _is_unclear(answer: str) -> bool:
    """A patient answer that does not settle the question (hedged, unsure, cannot remember)."""
    return is_uncertain(answer) or bool(_PATIENT_UNSURE.search(answer or ""))


# --- answer classification -------------------------------------------------------------------------
# An answer is rewritten to "denied" ONLY when every clause of it is an unambiguous denial. A leading
# "No"/"아니요" never turns the whole answer negative when a later clause states a positive fact
# ("No insulin. I take metformin." / "아니요, 아스피린 알레르기가 있어요."): anything mixed, positive,
# uncertain or unparseable is kept verbatim, because lossy normalisation here deletes real patient
# information from the SOAP note.
_CLAUSE_SPLIT = re.compile(
    r"[.;,!?:/\n。、，；！？]+"
    r"|\s+(?:but|however|except|although|though|yet|and|or|also|while|whereas)\s+"
    r"|(?<=[가-힣])\s*(?:하지만|그러나|그런데|근데|그리고|다만|이지만|지만)\s*"
    r"|(?<=[가-힣])(?:고|는데|으나|며|면서)\s+"
    r"|(?:けど|けれど|でも|しかし|が、)"
    r"|(?:但是|但|而且|不过|可是|除了)",
    re.IGNORECASE,
)
_NEGATION = re.compile(
    r"^\s*(?:no|none|nope|nah|nothing|never|not|neither|denies|denied|n/a|negative)\b"
    r"|\b(?:don'?t|do not|doesn'?t|does not|didn'?t|did not|haven'?t|have not|hasn'?t|has not|"
    r"never (?:take|took|use|used|had|have|been)|not (?:taking|on|using|allergic|aware)|no known)\b"
    r"|아니|없|않|못\s|안\s|부인|아닙니다"
    r"|ありません|いません|ない|ません|なし"
    r"|没有|没|无|不(?:吃|服|用|曾|是|会|对|痛|疼|发)",
    re.IGNORECASE,
)
_UNCERTAIN = re.compile(
    r"\b(?:not sure|unsure|don'?t know|do not know|dunno|maybe|perhaps|i guess|not certain|can'?t remember|"
    r"cannot remember|don'?t remember)\b|모르|기억.{0,3}(?:안|않|못)|잘 모|확실하지|아마|わかりません|分かりません|不知道|不确定|不清楚",
    re.IGNORECASE,
)
# A clause that names something the patient DOES (or "only"/"just"/"except") is positive content even
# when it contains a negation word ("only aspirin, no other drugs").
_AFFIRM_GUARD = re.compile(r"\b(?:only|just|except|besides|other than|aside from)\b|만\s|말고|빼고|제외|だけ|のみ|只|仅|除", re.IGNORECASE)


def _clauses(answer: str) -> List[str]:
    return [c.strip() for c in _CLAUSE_SPLIT.split(answer or "") if c and c.strip()]


def classify_answer(answer: str) -> str:
    """'empty' | 'denied' | 'uncertain' | 'affirmed' | 'mixed'.

    'denied' means the ENTIRE answer is a clear denial. 'mixed' means at least one denial clause and
    at least one non-denial clause. The SOAP writer shows the patient's own words for everything
    except 'denied'."""
    text = (answer or "").strip()
    if not text or not re.search(r"\w", text):
        return "empty"
    if _UNCERTAIN.search(text):
        return "uncertain"
    clauses = _clauses(text)
    if not clauses:
        return "empty"
    negative = [bool(_NEGATION.search(c)) and not _AFFIRM_GUARD.search(c) for c in clauses]
    if all(negative):
        return "denied"
    return "mixed" if any(negative) else "affirmed"


def label_alternatives(entry: Optional[dict], lang: str) -> List[str]:
    """Other names of a knowledge-base entry (aliases/abbreviations), same script as ``lang`` first, so a
    spoken explanation can use a short name when the formal one is too long for a 30-character SAY."""
    if not entry:
        return []
    aliases = [a for a in entry.get("aliases", []) if isinstance(a, str)]
    hangul = [a for a in aliases if re.search(r"[가-힣]", a)]
    other = [a for a in aliases if not re.search(r"[가-힣]", a)]
    return (hangul + other) if lang == "ko" else other


def _is_denial(answer: str) -> bool:
    return classify_answer(answer) == "denied"


_CATEGORY_SECTION = {
    "past_medical_history": "pmh", "medication": "meds", "allergy": "allergy",
    "family_history": "fhx", "social_history": "shx",
}


def _subjective(state: PatientState, L: Dict[str, str]) -> List[str]:
    sections: Dict[str, List[str]] = {k: [] for k in ("hpi", "pmh", "meds", "allergy", "fhx", "shx", "ros")}
    for turn in state.performed_actions:
        if turn.action_type != "ASK":
            continue
        category, _, detail = turn.key.partition(":")
        answer = (turn.result or "").strip()
        if not answer:
            continue
        if _is_denial(answer):
            shown = L["denied"]
        elif _is_unclear(answer):
            shown = f"{L['unclear']}: {answer}"
        else:
            shown = answer
        if category in _CATEGORY_SECTION:
            sections[_CATEGORY_SECTION[category]].append(shown)
        elif detail:
            sections["ros"].append(f"{detail.replace('_', ' ')}: {shown}")
        else:
            sections["hpi"].append(f"{category.replace('_', ' ')}: {shown}")
    lines = [f"{L['cc']}: {state.chief_complaint or L['none']}"]
    for name in ("hpi", "pmh", "meds", "allergy", "fhx", "shx", "ros"):
        values = sections[name]
        lines.append(f"{L[name]}: " + ("; ".join(values) if values else L["not_asked"]))
    return lines


def _objective(state: PatientState, L: Dict[str, str], lang: str) -> List[str]:
    lines: List[str] = []
    if state.initial_vitals_text:
        lines.append(f"[T0 {L['initial']}] {L['vitals']}: {state.initial_vitals_text}")
    for turn in state.performed_actions:
        if turn.action_type != "EXAM":
            continue
        spec = EXAM_CATALOG.get(turn.key)
        name = (spec["name_ko"] if lang == "ko" else spec["name_en"]) if spec else turn.key
        lines.append(f"[T{turn.turn}] {name}: {(turn.result or '').strip() or L['none']}")
    for exam_id in state.rejected_exams:
        spec = EXAM_CATALOG.get(exam_id)
        name = (spec["name_ko"] if lang == "ko" else spec["name_en"]) if spec else exam_id
        lines.append(f"[-] {name}: {L['rejected']}")
    if not lines:
        lines.append(L["no_exam"])
    lines.append(L["tests_none"])
    return lines


def _entry_for(diagnosis_id: str) -> Optional[dict]:
    try:
        from nova_agent.missing_info import _resolve_entry
        return _resolve_entry(diagnosis_id)
    except Exception:  # noqa: BLE001 - presentation only, never fatal
        return None


def _plan_tests(top_entry: Optional[dict], dangerous_entries: List[dict], lang: str) -> List[str]:
    wanted: List[str] = []
    for entry in [top_entry] + dangerous_entries:
        if not entry:
            continue
        for test_id in list(entry.get("minimum_workup") or []) + list(entry.get("discriminating_tests") or []):
            if test_id in TEST_CATALOG and test_id not in wanted:
                wanted.append(test_id)
        if len(wanted) >= 6:
            break
    names = []
    for test_id in wanted[:6]:
        spec = TEST_CATALOG[test_id]
        names.append(spec["name_ko"] if lang == "ko" else spec["name_en"])
    return names


def _education_line(state: PatientState, L: Dict[str, str], flags: List[str]) -> str:
    """Patient education is recorded ONLY if it was actually said during the visit (SAY turns with their
    turn numbers); the note never claims an explanation that the turn log does not contain."""
    said = [(t.turn, t.key) for t in state.performed_actions if t.action_type == "SAY" and t.key in ("explanation", "plan_explanation")]
    if not said:
        return f"{L['edu']}: {L['edu_none']}"
    parts = []
    for turn, key in said:
        parts.append(f"[T{turn}] {L['edu_diag'] if key == 'explanation' else L['edu_plan']}")
    tail = f" ({L['red_flags']}: {', '.join(flags)})" if flags and any(k == "plan_explanation" for _, k in said) else ""
    return f"{L['edu']}: {L['edu_done']} -- " + "; ".join(parts) + tail


_UNDIFF_NOTE = {
    "en": "Status: no specific diagnosis is supported by the information obtained; the candidates below are not "
          "excluded and need further evaluation.",
    "ko": "상태: 얻은 정보로는 특정 진단을 뒷받침할 수 없음. 아래 감별진단은 배제되지 않았으며 추가 평가가 필요함.",
}


def build_soap(state: PatientState, differential: list, lang: str = "en", final=None) -> Dict[str, object]:
    """Returns {'S','O','A','P' (text blocks), 'primary_diagnosis', 'text'} for the final DIAGNOSE.

    ``differential`` is the validated differential the agent just decided on (DifferentialItem
    objects, rank order). Round Q: ``final`` (nova_agent/final_decision.FinalDecision) decides the primary; without
    it the first element is used (legacy callers). An undifferentiated decision states so in A and keeps every
    candidate as an alternative that is not excluded."""
    L = _labels(lang)
    undifferentiated = final is not None and final.item is None
    if final is not None:
        top = final.item
        others = [d for d in differential if top is None or d.diagnosis_id != top.diagnosis_id]
    else:
        top = differential[0] if differential else None
        others = list(differential[1:])
    top_entry = _entry_for(top.diagnosis_id) if top else None
    if undifferentiated:
        primary = final.label(lang)
    else:
        primary = localized_name(top_entry, top.diagnosis if top else (state.chief_complaint or L["none"]), lang)
        if top is not None and primary != top.diagnosis and lang == "ko":
            primary = f"{primary} ({top.diagnosis})"

    basis = list(top.supporting_evidence) if top else []
    a_lines = [f"{L['dx']}: {primary}",
               f"{L['basis']}: " + ("; ".join(basis[:8]) if basis else L["no_basis"])]
    if undifferentiated:
        a_lines.append(_UNDIFF_NOTE["ko" if lang == "ko" else "en"])
    ddx_lines = []
    dangerous_entries: List[dict] = []
    for item in others[:5 if undifferentiated else 4]:
        entry = _entry_for(item.diagnosis_id)
        name = localized_name(entry, item.diagnosis, lang)
        reason = "; ".join(item.supporting_evidence[:3]) or L["no_basis"]
        against = "; ".join(item.contradictory_evidence[:2])
        ddx_lines.append(f"- {name}: {reason}" + (f" ({L['against']}: {against})" if against else ""))
        if item.dangerous_if_missed and entry and item.supporting_evidence and len(dangerous_entries) < 1:
            dangerous_entries.append(entry)
    contra = list(top.contradictory_evidence) if top else []
    missing = list(top.missing_discriminative_evidence) if top else []
    a_lines.append(f"{L['contra']}: " + ("; ".join(contra[:4]) if contra else L["none"]))
    a_lines.append(f"{L['missing']}: " + ("; ".join(missing[:4]) if missing else L["none"]))
    a_lines.append(f"{L['ddx']}:")
    a_lines.extend(ddx_lines or [f"- {L['none']}"])

    urgent = bool(top and (top.dangerous_if_missed or top.urgency in ("CRITICAL", "HIGH"))) or (
        undifferentiated and any(d.dangerous_if_missed and d.supporting_evidence and d.score > 0 for d in differential[:3]))
    if undifferentiated and differential:
        top_entry = _entry_for(differential[0].diagnosis_id)  # tests that would evaluate the leading possibility
    tests = _plan_tests(top_entry, dangerous_entries, lang)
    flags = list((top_entry or {}).get("red_flag_keywords") or [])[:6]
    p_lines = [f"{L['tests']}: " + (", ".join(tests) if tests else L["none"]),
               f"{L['tx']}: " + (L["tx_urgent"] if urgent else L["tx_routine"]),
               f"{L['fu']}: " + (L["fu_urgent"] if urgent else L["fu_routine"]),
               _education_line(state, L, flags)]

    blocks = {"S": "\n".join(_subjective(state, L)), "O": "\n".join(_objective(state, L, lang)),
              "A": "\n".join(a_lines), "P": "\n".join(p_lines)}
    text = "\n\n".join(f"{L[k]}\n{blocks[k]}" for k in ("S", "O", "A", "P"))
    return {**blocks, "primary_diagnosis": primary, "text": text}
