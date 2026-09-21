"""Maps a free-text chief complaint onto one of the fixed chief-complaint tags the knowledge base
is organized by (spec section 17's eight case categories). Deterministic keyword match, bilingual,
with an explicit 'other' fallback rather than a guessed tag."""

from __future__ import annotations

CHIEF_COMPLAINT_KEYWORDS = {
    "chest_pain": ["chest pain", "chest tightness", "chest pressure", "흉통", "가슴 통증", "가슴이 아프"],
    "abdominal_pain": ["abdominal pain", "stomach pain", "belly pain", "복통", "배가 아프"],
    "headache": ["headache", "head pain", "두통", "머리가 아프"],
    "fever": ["fever", "chills", "high temperature", "열", "발열", "오한"],
    "dyspnea": ["shortness of breath", "difficulty breathing", "dyspnea", "breathless", "숨이 차", "호흡곤란"],
    "dizziness": ["dizziness", "dizzy", "vertigo", "lightheaded", "어지러", "현훈"],
    "altered_mental_status": ["confusion", "confused", "altered mental status", "unresponsive", "disoriented", "의식", "혼돈", "의식저하"],
    "urinary_symptoms": ["dysuria", "urinary frequency", "painful urination", "blood in urine", "소변", "배뇨통", "빈뇨"],
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
