"""Maps a free-text chief complaint onto one of the fixed chief-complaint tags the knowledge base
is organized by (spec section 17's eight case categories). Deterministic keyword match, bilingual,
with an explicit 'other' fallback rather than a guessed tag."""

from __future__ import annotations

CHIEF_COMPLAINT_KEYWORDS = {
    "chest_pain": ["chest pain", "chest tightness", "chest pressure", "chest hurts", "chest discomfort",
                   "pain in my chest", "흉통", "가슴 통증", "가슴이 아프"],
    "abdominal_pain": ["abdominal pain", "stomach pain", "belly pain", "stomach hurts", "my stomach",
                        "tummy", "복통", "배가 아프"],
    "headache": ["headache", "head pain", "head hurts", "my head is killing me", "두통", "머리가 아프"],
    "fever": ["fever", "chills", "high temperature", "burning up", "running a temperature",
              "열", "발열", "오한"],
    "dyspnea": ["shortness of breath", "difficulty breathing", "dyspnea", "breathless",
                "can't breathe", "cant breathe", "can't catch my breath", "out of breath", "winded",
                "숨이 차", "호흡곤란"],
    "dizziness": ["dizziness", "dizzy", "vertigo", "lightheaded", "light-headed", "room spinning",
                  "woozy", "어지러", "현훈"],
    "altered_mental_status": ["confusion", "confused", "altered mental status", "unresponsive",
                              "disoriented", "not making sense", "out of it", "can't think straight",
                              "not himself", "not herself", "not myself", "의식", "혼돈", "의식저하"],
    "urinary_symptoms": ["dysuria", "urinary frequency", "painful urination", "blood in urine",
                          "burning when I pee", "burns when I pee", "burning when I urinate",
                          "pain when urinating", "peeing", "urinate", "bladder", "소변", "배뇨통", "빈뇨"],
    # Additional presentation categories (spec section 8/24H): each is deliberately mapped to
    # disease pools already tagged for it in knowledge/diseases/*.json (see each disease's
    # `chief_complaint_tags`), rather than dumping the untargeted full 29-disease catalog whenever
    # a presentation falls slightly outside the original 8 categories.
    "syncope": ["syncope", "fainted", "fainting", "passed out", "loss of consciousness", "blacked out",
                "went out", "실신", "기절"],
    "palpitations": ["palpitations", "heart racing", "irregular heartbeat", "heart pounding",
                      "skipping beats", "racing heart", "두근거림", "심계항진"],
    "vomiting": ["vomiting", "throwing up", "nausea and vomiting", "puking", "구토", "토했"],
    "weakness": ["weakness", "generalized weakness", "feeling weak", "muscle weakness", "no energy",
                 "can't move", "무기력", "힘이 없"],
    "cough": ["cough", "coughing", "productive cough", "기침"],
    "back_pain": ["back pain", "flank pain", "lower back pain", "side hurts", "side pain", "my flank",
                  "요통", "옆구리 통증"],
    "leg_swelling": ["leg swelling", "swollen leg", "calf swelling", "edema", "다리 부종", "종아리 부종"],
}

# Presentations without their own dedicated disease pool are routed to the closest clinically
# related tag(s) so the candidate pool stays targeted instead of falling through to the entire
# knowledge base. Order matters only for tie-breaking (chief_complaint.classify picks the single
# best keyword match above this step -- this table only affects diseases_for_tag's fallback via
# differential.py, not the classifier itself).
RELATED_TAGS = {
    "syncope": ["dizziness", "chest_pain"],
    "palpitations": ["chest_pain", "dizziness"],
    "vomiting": ["abdominal_pain"],
    "weakness": ["altered_mental_status", "dizziness"],
    "cough": ["dyspnea", "fever"],
    "back_pain": ["abdominal_pain", "urinary_symptoms"],
    "leg_swelling": ["dyspnea"],
}


def classify(chief_complaint_text: str) -> str:
    """Returns the best-matching tag, or 'other' if nothing matches (never a guessed tag)."""
    lowered = (chief_complaint_text or "").lower()
    best_tag, best_score = "other", 0
    for tag, keywords in CHIEF_COMPLAINT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in lowered)
        if score > best_score:
            best_tag, best_score = tag, score
    return best_tag


def related_tags(tag: str) -> list:
    """Additional tags whose disease pool is clinically relevant to `tag`, used by
    differential.diseases_for_tag() to build a targeted (not whole-catalog) candidate pool for
    presentations that don't have their own disease entries tagged directly."""
    return RELATED_TAGS.get(tag, [])
