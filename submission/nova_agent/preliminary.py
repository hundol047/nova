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
    "vital_signs": {"ko": "혈압, 맥박, 체온을 재 주세요.", "en": "Please check the vital signs.", "ja": "バイタルを測ってください。", "zh": "请测量生命体征。"},
    "general_appearance": {"ko": "전반적인 상태를 관찰해 주세요.", "en": "Please observe the general appearance.", "ja": "全身の様子を観察してください。", "zh": "请观察整体状态。"},
    "cardiac_auscultation": {"ko": "심장 소리를 청진해 주세요.", "en": "Please listen to the heart sounds.", "ja": "心音を聴診してください。", "zh": "请听诊心脏。"},
    "lung_auscultation": {"ko": "폐 소리를 청진해 주세요.", "en": "Please listen to the lung sounds.", "ja": "肺音を聴診してください。", "zh": "请听诊肺部。"},
    "abdominal_exam": {"ko": "배를 눌러 압통을 확인해 주세요.", "en": "Please palpate the abdomen for tenderness.", "ja": "腹部を触診して圧痛を確認してください。", "zh": "请触诊腹部检查压痛。"},
    "neuro_exam": {"ko": "팔다리 근력과 감각을 확인해 주세요.", "en": "Please check limb strength and sensation.", "ja": "四肢の筋力と感覚を確認してください。", "zh": "请检查四肢肌力和感觉。"},
    "meningeal_signs": {"ko": "목 굽힘 시 뻣뻣한지 확인해 주세요.", "en": "Please check for neck stiffness on flexion.", "ja": "項部硬直を確認してください。", "zh": "请检查颈部强直。"},
    "skin_exam": {"ko": "피부를 관찰해 주세요.", "en": "Please inspect the skin.", "ja": "皮膚を観察してください。", "zh": "请检查皮肤。"},
    "extremity_exam": {"ko": "다리의 부종과 압통을 확인해 주세요.", "en": "Please check the legs for swelling and tenderness.", "ja": "下肢の浮腫と圧痛を確認してください。", "zh": "请检查下肢水肿和压痛。"},
    "costovertebral_tenderness": {"ko": "옆구리 뒤쪽을 두드려 통증을 확인해 주세요.", "en": "Please percuss the flank for tenderness.", "ja": "背部の肋骨脊柱角を叩打してください。", "zh": "请叩击肋脊角检查压痛。"},
    "pelvic_exam": {"ko": "골반 진찰을 해 주세요.", "en": "Please perform a pelvic examination.", "ja": "骨盤の診察をしてください。", "zh": "请做盆腔检查。"},
    "mental_status_exam": {"ko": "의식과 지남력을 확인해 주세요.", "en": "Please assess alertness and orientation.", "ja": "意識と見当識を確認してください。", "zh": "请评估意识和定向力。"},
}


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


def say_text(key: str, lang: str = "en", fallback: str = "") -> str:
    """The SAY sentence (<= 30 characters, ONE question) for an internal ASK key."""
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


def explanation_text(diagnosis_label: str, lang: str = "en") -> str:
    """A closing SAY (<= 30 characters) that tells the patient the working diagnosis; the longest
    template that fits is used so a long disease name degrades to a name-free sentence."""
    templates = _EXPLAIN.get(lang, _EXPLAIN["en"])
    label = diagnosis_label.strip()
    for template in templates:
        text = template.format(d=label)
        if len(text) <= SAY_MAX_CHARS:
            return text
    return fit_say(templates[-1].format(d=""))
