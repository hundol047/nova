"""Preliminary-round (예선) wire text: SAY questions, EXAM requests, and the closing explanation.

Rules implemented here (organizer briefing of 2026-10-06, supplied by the team as slide photos):
  * SAY  -- one question or one explanation per turn, at most 30 characters.
  * EXAM -- ONE physical-examination maneuver requested as a sentence; no examination list is
            provided, and a request that is not on the organizer's list is rejected (no turn charged).
  * There is no TEST action in the preliminary round.

Internally the agent still reasons with catalog keys (``onset``, ``associated_symptoms:fever``,
``abdominal_exam`` ...). This module only turns those keys into short, single-purpose sentences, so
nothing here changes a diagnosis. The wording is authored by the engineering team from common
clinical interview phrasing; it is not clinician-reviewed.
"""

from __future__ import annotations

import re
from typing import Optional

SAY_MAX_CHARS = 30


def detect_language(text: str) -> str:
    """'ko' | 'ja' | 'zh' | 'en' from the first patient statement (script based, no model)."""
    if not text:
        return "en"
    if re.search(r"[가-힣]", text):
        return "ko"
    if re.search(r"[぀-ヿ]", text):
        return "ja"
    if re.search(r"[一-鿿]", text):
        return "zh"
    return "en"


_AGE_PATTERNS = (
    re.compile(r"(\d{1,3})\s*(?:세|살)"),
    re.compile(r"(\d{1,3})\s*歳"),
    re.compile(r"(\d{1,3})\s*岁"),
    re.compile(r"(\d{1,3})[\s-]*(?:years?[\s-]*old|y/?o|yrs?\b)", re.IGNORECASE),
    re.compile(r"\bage[d:\s]+(\d{1,3})\b", re.IGNORECASE),
)
_FEMALE = re.compile(r"여자|여성|여\b|女性|女の|女\b|\bfemale\b|\bwoman\b|\bgirl\b", re.IGNORECASE)
_MALE = re.compile(r"남자|남성|남\b|男性|男の|男\b|\bmale\b|\bman\b|\bboy\b", re.IGNORECASE)


def parse_first_statement(text: str) -> dict:
    """Age and sex from the patient's first statement ("김철수, 45세 남자입니다..."). The briefing says
    the first statement carries name, age, sex and the reason for the visit and everything else
    must be earned by examining -- so these are NOT assumed to arrive as separate fields. Only a
    clearly stated value is returned; nothing is guessed."""
    out: dict = {}
    for pattern in _AGE_PATTERNS:
        match = pattern.search(text or "")
        if match and 0 <= int(match.group(1)) <= 120:
            out["age"] = int(match.group(1))
            break
    female, male = bool(_FEMALE.search(text or "")), bool(_MALE.search(text or ""))
    if female != male:  # ambiguous when both words appear
        out["sex"] = "female" if female else "male"
    return out


# One short, single-question sentence per core history category (all <= SAY_MAX_CHARS).
_SHORT_QUESTIONS = {
    "onset": {"ko": "증상은 언제 시작됐나요?", "en": "When did it start?", "ja": "いつから始まりましたか？", "zh": "什么时候开始的？"},
    "location": {"ko": "정확히 어디가 불편하세요?", "en": "Where exactly is it?", "ja": "正確にどこが辛いですか？", "zh": "具体是哪个部位？"},
    "duration": {"ko": "얼마나 오래 지속되나요?", "en": "How long does it last?", "ja": "どのくらい続きますか？", "zh": "每次持续多久？"},
    "character": {"ko": "어떤 느낌으로 아픈가요?", "en": "What does it feel like?", "ja": "どんな痛みですか？", "zh": "是什么样的感觉？"},
    "severity": {"ko": "0~10점이면 몇 점인가요?", "en": "Pain from 0 to 10?", "ja": "0〜10で何点ですか？", "zh": "0到10分是几分？"},
    "aggravating": {"ko": "무엇을 하면 더 심해지나요?", "en": "What makes it worse?", "ja": "何で悪化しますか？", "zh": "什么会让它加重？"},
    "relieving": {"ko": "무엇을 하면 나아지나요?", "en": "What makes it better?", "ja": "何で楽になりますか？", "zh": "什么会让它缓解？"},
    "associated_symptoms": {"ko": "동반되는 다른 증상이 있나요?", "en": "Any other symptoms?", "ja": "他に症状はありますか？", "zh": "还有其他症状吗？"},
    "past_medical_history": {"ko": "앓고 있는 병이 있으신가요?", "en": "Any past illnesses?", "ja": "持病はありますか？", "zh": "有既往疾病吗？"},
    "medication": {"ko": "복용 중인 약이 있나요?", "en": "Are you taking any medicine?", "ja": "服用中の薬はありますか？", "zh": "目前在服用药物吗？"},
    "allergy": {"ko": "알레르기가 있으신가요?", "en": "Do you have any allergies?", "ja": "アレルギーはありますか？", "zh": "有过敏吗？"},
    "family_history": {"ko": "가족 중 비슷한 병이 있나요?", "en": "Any family history?", "ja": "家族に同じ病気は？", "zh": "家人有类似疾病吗？"},
    "social_history": {"ko": "흡연이나 음주를 하시나요?", "en": "Do you smoke or drink?", "ja": "喫煙や飲酒はしますか？", "zh": "吸烟或饮酒吗？"},
}

# A feature question wraps an English knowledge-base feature phrase ("fever", "neck stiffness").
# Those phrases are kept as-is (the patient model is multilingual); only the frame is localized.
_FEATURE_FRAME = {"ko": "{f} 있으세요?", "en": "Any {f}?", "ja": "{f}はありますか？", "zh": "有{f}吗？"}
# Fallback frame when the feature is too long for the frame within the limit.
_FEATURE_FRAME_TIGHT = {"ko": "{f}?", "en": "{f}?", "ja": "{f}？", "zh": "{f}？"}

_EXPLAIN = {
    "ko": ("{d} 가능성이 있어요.", "{d} 의심됩니다.", "병명은 {d}일 수 있어요.", "원인을 더 확인할게요."),
    "en": ("This may be {d}.", "I suspect {d}.", "Possibly {d}.", "I will explain next."),
    "ja": ("{d}の可能性があります。", "{d}を疑います。", "原因を説明します。"),
    "zh": ("可能是{d}。", "怀疑是{d}。", "我来说明原因。"),
}

_EXAM_REQUEST = {
    "vital_signs": {"ko": "혈압을 재 주세요.", "en": "Please measure the blood pressure.", "ja": "血圧を測ってください。", "zh": "请测量血压。"},
    "general_appearance": {"ko": "전반적인 모습을 관찰해 주세요.", "en": "Please observe the general appearance.", "ja": "全身の様子を観察してください。", "zh": "请观察整体状态。"},
    "cardiac_auscultation": {"ko": "심장 소리를 청진해 주세요.", "en": "Please listen to the heart sounds.", "ja": "心音を聴診してください。", "zh": "请听诊心脏。"},
    "lung_auscultation": {"ko": "폐 소리를 청진해 주세요.", "en": "Please listen to the lung sounds.", "ja": "肺音を聴診してください。", "zh": "请听诊肺部。"},
    "abdominal_exam": {"ko": "배를 눌러 압통을 확인해 주세요.", "en": "Please palpate the abdomen for tenderness.", "ja": "腹部を触診して圧痛を確認してください。", "zh": "请触诊腹部检查压痛。"},
    "neuro_exam": {"ko": "양팔을 들어 근력을 확인해 주세요.", "en": "Please check the arm strength.", "ja": "腕の筋力を確認してください。", "zh": "请检查双臂肌力。"},
    "meningeal_signs": {"ko": "목을 앞으로 굽혀 강직을 확인해 주세요.", "en": "Please flex the neck to check for stiffness.", "ja": "首を前屈させて項部硬直を確認してください。", "zh": "请屈颈检查颈强直。"},
    "skin_exam": {"ko": "피부를 관찰해 주세요.", "en": "Please inspect the skin.", "ja": "皮膚を観察してください。", "zh": "请检查皮肤。"},
    "extremity_exam": {"ko": "종아리를 만져 압통을 확인해 주세요.", "en": "Please palpate the calf for tenderness.", "ja": "ふくらはぎを触診して圧痛を確認してください。", "zh": "请触诊小腿检查压痛。"},
    "costovertebral_tenderness": {"ko": "옆구리 뒤쪽을 두드려 통증을 확인해 주세요.", "en": "Please percuss the flank for tenderness.", "ja": "背部の肋骨脊柱角を叩打してください。", "zh": "请叩击肋脊角检查压痛。"},
    "pelvic_exam": {"ko": "골반 진찰을 해 주세요.", "en": "Please perform a pelvic examination.", "ja": "骨盤の診察をしてください。", "zh": "请做盆腔检查。"},
    "mental_status_exam": {"ko": "의식 수준을 확인해 주세요.", "en": "Please assess the level of consciousness.", "ja": "意識レベルを確認してください。", "zh": "请评估意识水平。"},
}

# Closing SAY that tells the patient the next step (<= 30 characters; urgent vs routine).
_PLAN_SAY = {
    "ko": ("지금 바로 응급 검사가 필요해요.", "검사 후 악화되면 바로 오세요."),
    "en": ("You need urgent tests now.", "Return at once if it worsens."),
    "ja": ("今すぐ緊急の検査が必要です。", "悪化したらすぐ来てください。"),
    "zh": ("需要马上做紧急检查。", "加重请立即就诊。"),
}

# A short empathic opener attached to the very first question (only when the total still fits).
_EMPATHY = {"ko": "힘드시겠어요. ", "en": "I'm sorry. ", "ja": "お辛いですね。", "zh": "辛苦了。"}

# How an environment is likely to refuse an examination that is not on its list. The real wording is
# unpublished, so this is a documented heuristic, not a contract. Three signals, strongest first:
#   1. structured fields on the observation (rejected / error / status / ok=false ...), which a real
#      protocol is far more likely to carry than a particular sentence;
#   2. an empty reply (nothing was found, nothing can be recorded);
#   3. request-scoped refusal wording in ko/en/ja/zh. The wording must be about the REQUEST itself so
#      that a clinical finding ("breath sounds not available on the left") is never mistaken for one,
#      and long replies are treated as findings, not refusals.
_REJECTION = re.compile(
    "|".join((
        r"거절|지원하지 않|지원되지 않|수행할 수 없|할 수 없는 요청|목록에 없|허용되지 않|제공되지 않는 (?:진찰|검사|요청)|유효하지 않은 (?:진찰|요청)",
        r"対応していません|サポートされていません|実行できません|許可されていません|拒否されました|リストにありません",
        r"不支持|无法执行|不允许|已拒绝|无效(?:的)?(?:请求|检查)|不在(?:列表|清单)",
        r"\b(?:invalid|unsupported|unknown|unrecognized|unrecognised)\s+(?:request|exam(?:ination)?|maneuver|action)\b",
        r"\b(?:request|exam(?:ination)?|maneuver|action)\b[^.\n]{0,40}\b(?:rejected|refused|denied|not (?:supported|allowed|permitted|available|recognized|recognised)|cannot be (?:performed|done))",
        r"\b(?:cannot|can't|unable to) (?:perform|carry out)\b",
        r"\bnot (?:in|on) the (?:allowed |available |supported )?(?:list|set)\b",
        r"\bno such (?:exam|examination|maneuver|action)\b",
    )),
    re.IGNORECASE,
)
_MAX_REFUSAL_CHARS = 160
_REJECTION_STATUS = {"rejected", "reject", "refused", "denied", "unsupported", "invalid", "error", "failed",
                     "failure", "not_allowed", "not_supported", "not_available", "unavailable", "unknown_action"}


def looks_like_rejection(text: str) -> bool:
    """Request-scoped refusal wording (ko/en/ja/zh) in a SHORT reply."""
    return bool(text) and len(text) <= _MAX_REFUSAL_CHARS and bool(_REJECTION.search(text))


def rejection_signal(raw: Optional[dict], content: Optional[str]) -> bool:
    """True when the environment refused an examination request (see the comment above): a structured
    refusal field, an explicitly false success flag, an empty reply, or request-scoped refusal wording."""
    raw = raw or {}
    if raw.get("rejected") is True or raw.get("error") not in (None, "", False):
        return True
    for key in ("status", "result", "outcome", "state"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip().lower().replace(" ", "_") in _REJECTION_STATUS:
            return True
    if any(raw.get(key) is False for key in ("ok", "success", "accepted", "valid", "allowed")):
        return True
    text = (content or "").strip()
    return not text or looks_like_rejection(text)


def _pick(table: dict, lang: str) -> Optional[str]:
    return table.get(lang) or table.get("en")


def fit_say(text: str, limit: int = SAY_MAX_CHARS) -> str:
    """Guarantee a SAY fits the character limit: collapse whitespace, then trim at a word boundary
    (never mid-word where avoidable) and keep terminal punctuation."""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    cut = text[: limit - 1]
    if " " in cut and not text[limit - 1].isspace():
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,.;:?!") + "?"


def say_text(key: str, lang: str = "en", fallback: str = "", empathy: bool = False) -> str:
    """The SAY sentence (<= 30 characters, ONE question) for an internal ASK key. ``empathy`` adds a
    short opener (first question only) when the whole sentence still fits the limit."""
    text = _say_core(key, lang, fallback)
    if empathy:
        opener = _EMPATHY.get(lang, _EMPATHY["en"])
        if len(opener + text) <= SAY_MAX_CHARS:
            return opener + text
    return text


def plan_say_text(urgent: bool, lang: str = "en") -> str:
    texts = _PLAN_SAY.get(lang, _PLAN_SAY["en"])
    return fit_say(texts[0] if urgent else texts[1])


def _say_core(key: str, lang: str, fallback: str) -> str:
    category, _, detail = key.partition(":")
    if detail:
        feature = detail.replace("_", " ").strip()
        frame = _FEATURE_FRAME.get(lang, _FEATURE_FRAME["en"])
        text = frame.format(f=feature)
        if len(text) > SAY_MAX_CHARS:
            text = _FEATURE_FRAME_TIGHT.get(lang, _FEATURE_FRAME_TIGHT["en"]).format(f=feature)
        return fit_say(text)
    table = _SHORT_QUESTIONS.get(category)
    if table is not None:
        return fit_say(_pick(table, lang))
    return fit_say(fallback or _pick(_SHORT_QUESTIONS["associated_symptoms"], lang))


def exam_request_text(exam_id: str, lang: str = "en", fallback: str = "") -> str:
    """One physical-examination maneuver as a request sentence (no length limit applies to EXAM)."""
    table = _EXAM_REQUEST.get(exam_id)
    if table is not None:
        return _pick(table, lang)
    return fallback or exam_id.replace("_", " ")


def explanation_text(diagnosis_label: str, lang: str = "en", alternatives=()) -> str:
    """A closing SAY (<= 30 characters) that tells the patient the working diagnosis. Every candidate name
    (the full label first, then shorter aliases/abbreviations, e.g. "heart attack") is tried against every
    template, preferring the most informative name; only when NO name fits does it degrade to a name-free
    sentence."""
    templates = _EXPLAIN.get(lang, _EXPLAIN["en"])
    named = [t for t in templates if "{d}" in t]
    candidates = [c.strip() for c in [diagnosis_label, *alternatives] if c and c.strip()]
    for label in sorted(dict.fromkeys(candidates), key=len, reverse=True):
        for template in named:
            text = template.format(d=label)
            if len(text) <= SAY_MAX_CHARS:
                return text
    return fit_say(templates[-1].format(d=""))
