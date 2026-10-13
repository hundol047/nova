"""Conservative validation of Doctor text against observed encounter facts.

This is an engineering guard, not a clinical adjudicator. Numeric facts, polarity
and laterality must agree; ordinary wording may vary. Nothing is learned between cases.
"""
import re
import unicodedata
from decimal import Decimal

_UNIT = r"mg\s*/\s*dl|mg\s*/\s*l|g\s*/\s*dl|g\s*/\s*l|ng\s*/\s*ml|mmol\s*/\s*l|밀리그램|마이크로그램|tablets?|pills?|months?|years?|days?|weeks?|hours?|times?|mg|mcg|µg|kg|cm|mmhg|g|ml|회|번|알|정|개월|달|년|주|일|시간|세|살|%|°c"
_NUMBER = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)\s*(" + _UNIT + r")?", re.I)
_UNITS = {"밀리그램": "mg", "마이크로그램": "mcg", "µg": "mcg", "살": "세", "달": "개월", "번": "회",
          "month": "개월", "months": "개월", "year": "년", "years": "년", "day": "일", "days": "일",
          "week": "주", "weeks": "주", "hour": "시간", "hours": "시간", "time": "회", "times": "회",
          "tablet": "tablet", "tablets": "tablet", "pill": "tablet", "pills": "tablet", "알": "tablet", "정": "tablet"}
_CARDINALS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
              "한": "1", "두": "2", "세": "3", "네": "4", "다섯": "5", "여섯": "6"}
_WORD_NUMBER = re.compile(r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\b\s*(" + _UNIT + r")?|"
                          r"(?<![가-힣])(한|두|세|네|다섯|여섯)\s*(알|정|회|번|년|개월|달|주|일|시간|살)", re.I)
_NEG = re.compile(r"\b(?:no|not|without|denies|denied|absent|negative|never)\b|없|아니|않|음성", re.I)
_UNCERTAIN = re.compile(r"cannot|can't|not ruled out|unknown|not sure|don't know|do not know|배제할\s*수\s*없|의심|가능성|모르|미확인|확인되지", re.I)
_YES_NO = re.compile(r"^(?:yes|no|yeah|nope|네|예|맞아요|그렇습니다|아니요|아닙니다|없어요|없습니다)[.!\s]*$", re.I)
_SIDE = {"left": re.compile(r"\bleft\b|왼쪽|좌측", re.I), "right": re.compile(r"\bright\b|오른쪽|우측", re.I),
         "both": re.compile(r"\bbilateral\b|\bboth\b|양쪽|양측", re.I)}
_CLAUSES = re.compile(r"\n|;|(?<!\d)\.(?!\d)|\bbut\b|하지만|그러나", re.I)
_RATE = re.compile(r"\b(once|twice|three times|four times)\s+(daily|a day|per day|weekly|a week)\b|"
                   r"(하루|매일|일주일에)\s*(한|두|세|네|\d+)\s*(?:번|회)", re.I)
_RELATIONS={'mother':r'\bmother\b|\bmom\b|어머니|엄마','father':r'\bfather\b|\bdad\b|아버지|아빠',
            'sibling':r'\bsibling|\bbrother\b|\bsister\b|형제|자매|동생'}


def _assertions(text):
    for clause in _CLAUSES.split(text):
        context,arrow,answer=clause.partition('→')
        if arrow:
            for piece in _assertions(answer):yield context+'→'+piece
            continue
        negative_list=False
        for piece in re.split(r'\band\b|그리고|\s및\s',clause,flags=re.I):
            if negative_list and not _NEG.search(piece) and not re.search(r'\b(?:has|reports|present|is|are)\b|있|보임',piece,re.I):
                piece='no '+piece.strip()
            if piece.strip():yield piece.strip()
            negative_list=bool(re.match(r'^\s*(?:no\b|denies\b|without\b)',piece,re.I))


def _clean(text):
    from nova_agent.clinical_assertions import normalize_exam_notation
    return unicodedata.normalize("NFC", normalize_exam_notation(text)).lower().strip()


def _facts(text):
    """Numbers bind to their unit and, for doses, the preceding drug word."""
    text = _clean(text)
    result = []
    for m in _NUMBER.finditer(text):
        raw_unit = re.sub(r'\s+','',(m[2] or '').lower())
        unit = _UNITS.get(raw_unit,raw_unit)
        anchor = _dose_anchor(text, m.start(), unit)
        value = format(Decimal(m[1]), "f")  # no context rounding of long values
        if "." in value:
            value = value.rstrip("0").rstrip(".")
        result.append((value, unit, anchor))
    for m in _WORD_NUMBER.finditer(text):
        value, raw_unit = (m[1], m[2]) if m[1] else (m[3], m[4])
        unit = _UNITS.get(raw_unit or "", raw_unit or "")
        result.append((_CARDINALS[value], unit, _dose_anchor(text, m.start(), unit)))
    amounts = {"once": "1", "twice": "2", "three times": "3", "four times": "4", "한": "1", "두": "2", "세": "3", "네": "4"}
    for m in _RATE.finditer(text):
        value, period = (m[1], m[2]) if m[1] else (m[4], m[3])
        result.append((amounts.get(value, value), "frequency/week" if period in {"weekly", "a week", "일주일에"} else "frequency/day", ""))
    return result


def _dose_anchor(text, start, unit):
    if unit not in {"mg", "mcg", "g", "ml", "tablet"}:
        return ""
    generic = {"takes", "taking", "taken", "take", "is", "was", "dose", "of", "a", "the", "medicine", "medication",
               "복용량", "복용", "용량", "약", "약물", "하루", "매일"}
    for word in reversed(re.findall(r"[a-z가-힣][a-z가-힣-]*", text[max(0, start - 50):start])):
        word = re.sub(r"(?:을|를|은|는)$", "", word)
        if word not in generic:
            return word
    return ""


def _polarity(text):
    if _UNCERTAIN.search(text):
        return "uncertain"
    return "negative" if _NEG.search(text) else "positive"


def _words(text):
    return re.findall(r"[가-힣]{2,}|[a-z]{3,}", _clean(text))


def grounded_in(claim, corpus, threshold=0.6):
    """Match ONE observed assertion, never stitch a dose or a negation across facts.

    In a ``question → answer`` source the question supplies context, not an
    affirmative finding. A negative reply keeps its negative polarity.
    """
    claim = _clean(claim)
    assertions=list(_assertions(claim))
    if len(assertions)>1:
        return all(grounded_in(piece,corpus,threshold) for piece in assertions)
    words = _words(claim)
    if not words:
        return False
    claim_facts = _facts(claim)
    sides = {k for k, pattern in _SIDE.items() if pattern.search(claim)}
    for source in _assertions(_clean(corpus)):
        if not source.strip():
            continue
        context, sep, answer = source.partition("→")
        factual = answer.strip() if sep else source
        comparison = source if sep else factual
        from nova_agent.assertion_status import FAMILY_CUE
        if bool(FAMILY_CUE.search(claim)) != bool(FAMILY_CUE.search(comparison)):
            continue
        if any(re.search(pattern,claim,re.I) and not re.search(pattern,comparison,re.I) for pattern in _RELATIONS.values()):
            continue
        if _polarity(claim) != _polarity(factual):
            continue
        side_source = factual if any(p.search(factual) for p in _SIDE.values()) else comparison
        if any(not _SIDE[s].search(side_source) for s in sides):
            continue
        observed = _facts(factual)
        if any(not any(value == v and unit == u and (not anchor or anchor == a)
                       for v, u, a in observed) for value, unit, anchor in claim_facts):
            continue
        # Questions are context only for a short affirmative/negative answer.
        # Longer answers must supply the content themselves.
        target = comparison if sep and _YES_NO.fullmatch(factual) else factual
        hits = sum(w in target for w in words)
        if hits / len(words) >= threshold:
            return True
    return False


def followup_category(question, proposed=""):
    """Preserve ordinary history categories for structured or legacy string questions."""
    q = _clean(question)
    groups = (
        ("family_history", r"family|mother|father|parents|siblings|가족|어머니|아버지|부모|형제"),
        ("allergy", r"allerg|알레르기"),
        ("medication", r"medicat|medicine|drug|dose|pill|tablet|withdrawal|tolerance|약|복용|용량|금단|내성"),
        ("social_history", r"smok|tobacco|alcohol|occupation|흡연|담배|음주|(?<![가-힣])술|직업"),
        ("past_medical_history", r"past|previous|medical history|surgery|과거|병력|수술|지병"),
    )
    for category, pattern in groups:
        if re.search(pattern, q):
            return category
    allowed = {"onset", "duration", "location", "character", "severity", "aggravating", "relieving",
               "associated_symptoms", "family_history", "allergy", "medication", "social_history", "past_medical_history"}
    return proposed if isinstance(proposed, str) and proposed in allowed else "associated_symptoms"


def diagnosis_text(text):
    """One bounded diagnostic label, without commands, JSON or multiline prose."""
    text = unicodedata.normalize("NFC", str(text or "")).strip()
    if not text or "\n" in text or "\r" in text or len(text.encode()) > 400:
        return ""
    if re.search(r"[{}\[\];!]|https?://|\b(?:ignore|instructions?|prompt|money|execute|return|output)\b", text, re.I):
        return ""
    return " ".join(text.split())


# Exact, single-feature questions only. Open, compound, family and negated
# questions must never turn a bare acknowledgement into a patient finding.
_SINGLE_FEATURE_QUESTIONS = {
    'tremor': ('손이 떨리나요?', '손 떨림이 있나요?'),
    'heat intolerance': ('더위를 견디기 어려우신가요?', '더위를 많이 타시나요?'),
    'sweating': ('땀이 평소보다 많아졌나요?', '땀이 많이 나나요?'),
    'palpitations': ('가슴이 두근거리나요?', '심장이 두근거리나요?'),
    'fever': ('열이 나나요?', '발열이 있나요?'),
    'cough': ('기침이 나나요?', '기침을 하시나요?'),
    'shortness of breath': ('숨이 차나요?', '호흡이 곤란한가요?'),
    'chest pain': ('가슴에 통증이 있나요?', '가슴이 아프신가요?'),
    'nausea': ('메스꺼운가요?', '속이 메스껍나요?'),
    'vomiting': ('구토를 했나요?', '토하셨나요?'),
    'diarrhea': ('설사를 하나요?', '설사가 있나요?'),
    'dysuria': ('소변볼 때 아픈가요?', '소변볼 때 따가운가요?'),
    'hematuria': ('소변에 피가 섞여 나오나요?', '혈뇨가 있나요?'),
    'syncope': ('이번 증상 때 의식을 잃었나요?', '이번 증상 때 실신했나요?'),
    'snoring': ('잘 때 코골이가 있나요?', '코골이가 있나요?'),
    'weight loss': ('체중이 줄었나요?', '살이 빠졌나요?'),
}


def followup_discriminator(question):
    """Recover meaning from verified wording, never a Doctor-supplied key."""
    clean=lambda t: re.sub(r'[\s?.!。？！]+','',unicodedata.normalize('NFC',t)).casefold()
    q=clean(question)
    matches={feature for feature, variants in _SINGLE_FEATURE_QUESTIONS.items()
             if q in {clean(v) for v in variants}}
    return 'associated_symptoms:'+next(iter(matches)) if len(matches)==1 else ''
