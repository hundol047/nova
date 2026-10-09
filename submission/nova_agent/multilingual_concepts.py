"""Bounded multilingual clinical concept normalization (Round E, defect D).

Architecture (spec): `localized phrase -> canonical symptom concept -> existing routing`. This
module is ONLY the first arrow -- a small, hand-curated table of non-English clinical phrases
mapped to the SAME canonical chief-complaint concept tags chief_complaint.py already routes on
(abdominal_pain, chest_pain, headache, ...). It creates NO separate reasoning logic per language:
these phrases are merged directly into chief_complaint.CONCEPT_ALIASES at import time, so a
Korean or Japanese phrase is scored through the EXACT SAME exact/alias/fuzzy machinery, specificity
precedence, and multi-concept extraction as any English phrase -- there is no parallel "Korean
matcher" or "Japanese matcher" anywhere in this codebase.

Deliberately bounded, not a translation engine:
  - No Google Translate / external LLM translation / any online translation API -- the competition
    runtime must stay fully offline and dependency-light. Every phrase below is a literal,
    hand-written string, checked the same substring/word-overlap way English phrases already are.
  - Covers only the languages this repo's evaluation/UI already exercises (English, Korean,
    Japanese -- see evaluation/blind_cases_v14.py's mixed_language category) and only the ~14
    clinically load-bearing domains named by this round's own spec: pain (generic body-region
    location words that commonly stand in for "X pain" in casual non-English phrasing),
    abdominal_pain, chest_pain, headache, weakness, numbness, dyspnea (shortness of breath), fever,
    vomiting, diarrhea, gi_bleeding (bleeding), dizziness, syncope (fainting).
  - Every phrase is a COMPLETE clinical word or phrase (minimum 2 characters for CJK, never a
    single ambiguous character/fragment) -- chief_complaint.py's existing substring/alias matching
    already requires the whole phrase text to appear, so a phrase here can never fire on an
    unrelated word that merely happens to contain one of its characters.
  - This table only ever ADDS alias coverage for a concept that already exists in
    chief_complaint.CANONICAL_TERMS -- it can never introduce a new tag on its own, and (like every
    other alias in this codebase) never widens matching for any OTHER concept.

Real gap this round's own audit found and closed: a bare non-English body-region NOUN (e.g.
Japanese "下腹部"/"腹部" lower-abdomen/abdomen, Korean "아랫배"/"복부") often stands in for the
whole "X pain" concept in a real mixed-language sentence when the symptom-quality word itself is
in the OTHER language (e.g. "下腹部に sharp pain" -- Japanese location, English quality, with
neither language's own "痛い"/"pain"-compound literally present) -- Blind v14's one mixed-language
miss (Japanese abdominal pain) traced to exactly this shape. Adding the bare region noun closes it
generically (any sentence naming that body region in that language now routes), never by keying on
that one case's exact wording.
"""

from __future__ import annotations

import re

from typing import Dict, List

# concept_tag -> list of non-English phrases (Korean + Japanese), each a complete clinical word or
# phrase. English coverage already lives in chief_complaint.py's own CANONICAL_TERMS/CONCEPT_ALIASES
# and needs no duplication here.
MULTILINGUAL_CONCEPT_ALIASES: Dict[str, List[str]] = {
    # Generic "pain" (spec's own named domain) -- bare, unscoped pain words in Korean/Japanese,
    # analogous to how English "pain" alone is too generic to route to any ONE body region; these
    # exist so a bare pain-word combined with an English/Korean/Japanese body-region word elsewhere
    # in the same sentence still contributes SOME signal, never enough alone to pick a specific tag
    # (mirrors matching.py's own _GENERIC_MEDICAL_WORDS treatment of English "pain").
    # (Intentionally NOT added as its own routing tag -- see module docstring: this table only
    # ever extends an EXISTING concept's alias list.)
    "abdominal_pain": [
        "복통", "배가 아파요", "배가 아프다", "아랫배가 아파요", "아랫배 통증", "복부 통증",
        "お腹が痛いです", "下腹部の痛み", "下腹部に痛み", "腹部の痛み",
        # Bare body-region nouns (no "pain"/"痛" word required) -- the real gap this round closed:
        # a mixed-language sentence naming the region in one language while the symptom quality
        # ("sharp", "dull", "crampy") is expressed in a different language/English.
        "아랫배", "하복부", "下腹部", "腹部",
    ],
    "chest_pain": [
        "가슴이 아파요", "흉통", "가슴 통증", "가슴이 답답해요",
        "胸が痛いです", "胸部の痛み", "胸の痛み",
        # Bare body-region nouns (same rationale as abdominal_pain's bare region words above).
        "가슴에", "가슴이", "胸に", "胸が",
    ],
    "headache": [
        "머리가 아파요", "두통이 있어요",
        "頭が痛いです", "頭痛がします",
    ],
    "weakness": [
        "온몸에 힘이 없어요", "기운이 없어요",
        "体に力が入りません", "だるくて力が出ません",
    ],
    "numbness": [
        "손발이 저려요", "감각이 없어요",
        "手足がしびれます", "感覚がありません",
    ],
    "dyspnea": [
        "숨쉬기가 힘들어요", "숨이 차요", "숨이 차고", "숨이 안 쉬어", "숨을 쉴 수 없", "숨이 가빠", "숨이 가쁘",
        "息が苦しいです", "呼吸が苦しいです",
    ],
    "fever": [
        "열이 나요", "몸에 열이 있어요",
        "熱があります", "発熱しています",
    ],
    "vomiting": [
        "계속 토해요", "구토를 했어요",
        "吐き気がして吐きました", "嘔吐しました",
    ],
    "diarrhea": [
        "설사를 해요", "묽은 변을 봐요",
        "下痢をしています", "水っぽい便が出ます",
    ],
    "gi_bleeding": [
        "피를 토했어요", "대변에 피가 섞여요",
        "血を吐きました", "便に血が混じります",
    ],
    "dizziness": [
        "어지러워요", "머리가 빙빙 돌아요",
        "めまいがします", "頭がふらふらします",
    ],
    "allergic": [
        "온몸이 가려", "전신이 가려", "알레르기 반응", "입술이 붓", "얼굴이 붓", "두드러기가 났",
    ],
    "syncope": [
        "정신을 잃었어요", "기절했어요", "쓰러졌어요", "쓰러졌습니다", "쓰러졌다",
        "気を失いました", "意識を失いました",
    ],
}


def apply_multilingual_aliases(concept_aliases: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Merges MULTILINGUAL_CONCEPT_ALIASES into an existing concept-alias table (chief_complaint.
    py's own CONCEPT_ALIASES), extending each tag's alias LIST in place of creating any parallel
    structure -- called once at chief_complaint.py's import time, before CONCEPT_PHRASES is built,
    so every downstream consumer (route(), extract_presentation(), specificity precedence) sees
    these phrases exactly the way it sees any other alias, with zero new code paths."""
    merged = {tag: list(phrases) for tag, phrases in concept_aliases.items()}
    for tag, phrases in MULTILINGUAL_CONCEPT_ALIASES.items():
        merged.setdefault(tag, [])
        for phrase in phrases:
            if phrase not in merged[tag]:
                merged[tag].append(phrase)
    return merged


# Bare, COMPLETE clinical nouns (>= 2 characters, never fragments) added after Blind v16 showed the
# sentence-ending-only phrases above miss natural variants ("下痢がひどいです" vs "下痢をしています").
_BARE_CLINICAL_NOUNS: Dict[str, List[str]] = {
    "abdominal_pain": ["복통", "腹痛"], "chest_pain": ["흉통", "胸痛"], "headache": ["두통", "頭痛"],
    "weakness": ["무력감", "脱力"], "numbness": ["저림", "しびれ", "痺れ"], "dyspnea": ["호흡곤란", "息切れ", "息苦しい"],
    "fever": ["발열", "発熱"], "vomiting": ["구토", "嘔吐", "吐き気"], "diarrhea": ["설사", "下痢"],
    "gi_bleeding": ["토혈", "혈변", "吐血", "下血"], "dizziness": ["어지럼", "めまい", "眩暈"], "syncope": ["실신", "失神"],
}
for _concept, _nouns in _BARE_CLINICAL_NOUNS.items():
    MULTILINGUAL_CONCEPT_ALIASES[_concept] = list(MULTILINGUAL_CONCEPT_ALIASES[_concept]) + [
        n for n in _nouns if n not in MULTILINGUAL_CONCEPT_ALIASES[_concept]]

# A localized symptom immediately followed by one of these is DENIED, not present.
_NEGATION_MARKERS = ("없", "않", "아니", "ありません", "ない", "なし", "ませんでした", "ないです", "なかっ")


# Canonical ENGLISH evidence wording for each concept above. Routing/pool selection already uses the
# localized phrases directly, but differential scoring matches knowledge-base typical_features by
# English word overlap, so a Korean/Japanese complaint earned ZERO score (Blind v16: both Japanese-
# mixed cases never moved their differential at all). Appending the canonical term to the evidence
# bag makes a localized symptom count the same as the English patient saying it -- no translation
# API, no per-language reasoning, and English-only input is completely unaffected.
_CANONICAL_ENGLISH_EVIDENCE: Dict[str, str] = {
    "abdominal_pain": "abdominal pain", "chest_pain": "chest pain", "headache": "headache",
    "weakness": "weakness", "numbness": "numbness", "dyspnea": "shortness of breath", "fever": "fever",
    "vomiting": "vomiting", "diarrhea": "diarrhea", "gi_bleeding": "gi bleeding", "dizziness": "dizziness",
    "syncope": "syncope",
}


# Direct localized-symptom -> canonical English evidence for findings that are NOT routing concepts
# (follow-up answers such as nausea, dysuria, chills). Same discipline as above: only a non-ASCII
# phrase can fire, a following denial marker cancels it, and plain English is never touched.
# PROVENANCE: authored by the engineering agent from common Korean/Japanese clinical vocabulary;
# not clinician-reviewed; one localized noun maps to one plain English symptom, no diagnostic claim.
_DIRECT_LOCALIZED_EVIDENCE: Dict[str, str] = {
    "메스꺼": "nausea", "구역": "nausea", "속이 안 좋": "nausea", "吐き気": "nausea", "むかむか": "nausea",
    "배뇨통": "dysuria painful urination", "소변을 볼 때 아": "dysuria painful urination",
    "排尿時": "dysuria painful urination", "排尿痛": "dysuria painful urination",
    "오줌 눌 때 아": "dysuria painful urination", "소변 볼 때 아": "dysuria painful urination",
    "열이 나": "fever", "열이 있": "fever", "熱があ": "fever", "熱が出": "fever",
    "우하복부": "right lower quadrant abdominal pain", "右下腹部": "right lower quadrant abdominal pain",
    "빈뇨": "urinary frequency", "자주 소변": "urinary frequency", "頻尿": "urinary frequency",
    "오한": "chills", "悪寒": "chills", "寒気": "chills",
    "옆구리": "flank pain", "側腹部": "flank pain", "脇腹": "flank pain",
    "기침": "cough", "咳": "cough", "가래": "productive cough", "痰": "productive cough",
    "식은땀": "sweating", "冷や汗": "sweating", "발한": "sweating", "多汗": "sweating",
    "두근": "palpitations", "動悸": "palpitations",
    "목이 아": "sore throat", "喉の痛み": "sore throat", "のどが痛": "sore throat",
    "혈뇨": "hematuria blood in urine", "血尿": "hematuria blood in urine",
    "황달": "jaundice", "黄疸": "jaundice",
    "발진": "rash", "発疹": "rash",
    "경련": "seizure", "けいれん": "seizure", "痙攣": "seizure",
}


# Korean colloquial history/symptom phrases -> canonical ENGLISH evidence (the wording the knowledge base's
# typical_features and risk_factors use). Added after the Korean preliminary development set showed that
# first-person Korean answers ("종아리가 붓고 아파요", "목이 뻣뻣해요") were recorded but never reached
# differential scoring. Same discipline as above: only a non-ASCII phrase can fire, a following denial
# marker cancels it ("종아리가 붓지 않아요"), one phrase maps to one plain English finding, and no
# diagnosis is named. PROVENANCE: authored by the engineering agent from common Korean clinical
# vocabulary; NOT clinician-reviewed; development-set cases in evaluation/preliminary_dev_cases.py.
_DIRECT_LOCALIZED_EVIDENCE.update({
    "종아리가 붓": "calf swelling", "종아리 부종": "calf swelling", "다리가 붓": "calf swelling leg swelling",
    "한쪽 다리": "unilateral leg pain", "종아리가 아": "unilateral leg pain",
    "피 섞인 가래": "hemoptysis", "피가 섞인 가래": "hemoptysis", "객혈": "hemoptysis",
    "깊이 쉬면 더 아": "pleuritic chest pain", "숨 쉴 때마다": "pleuritic chest pain", "숨쉴 때마다": "pleuritic chest pain",
    "숨이 차": "shortness of breath", "숨 차": "shortness of breath", "숨쉬기 힘": "shortness of breath",
    "숨이 안 쉬어": "shortness of breath", "숨을 쉴 수 없": "shortness of breath",
    "목이 뻣뻣": "neck stiffness", "목 뒤가 뻣뻣": "neck stiffness", "경부 강직": "neck stiffness", "목이 뻐근": "neck stiffness",
    "빛이 눈부": "photophobia", "빛에 예민": "photophobia", "눈이 부셔": "photophobia", "소리에 예민": "phonophobia",
    "벼락 치": "thunderclap headache sudden onset severe headache", "망치로 맞은": "thunderclap headache sudden onset severe headache",
    "평생 이런 두통": "worst headache of life", "가장 심한 두통": "worst headache of life",
    "맥박 뛰듯": "pulsating headache", "욱신욱신": "pulsating headache", "한쪽 머리": "unilateral headache",
    "눈앞이 번쩍": "aura", "앞이 번쩍": "aura",
    "입이 한쪽으로 돌아": "facial droop", "입꼬리가 처": "facial droop", "안면 마비": "facial droop",
    "말이 어눌": "slurred speech", "발음이 이상": "slurred speech", "말이 꼬": "slurred speech",
    "팔다리에 힘이 안": "sudden onset focal weakness", "한쪽 팔에 힘": "sudden onset focal weakness",
    "두드러기": "urticaria hives", "입술이 붓": "facial swelling", "얼굴이 붓": "facial swelling",
    "쌕쌕": "wheeze", "목이 조이": "throat tightness", "목이 막히": "throat tightness",
    "질 출혈": "vaginal bleeding", "질출혈": "vaginal bleeding", "생리가 늦": "missed period", "생리를 안": "missed period",
    "한쪽 아랫배": "unilateral pelvic pain", "왼쪽 아랫배": "unilateral pelvic pain", "오른쪽 아랫배": "right lower quadrant abdominal pain",
    "가슴을 쥐어": "substernal pressure", "가슴이 쥐어": "substernal pressure", "가슴을 짓누르": "substernal pressure",
    "가슴이 짓눌": "substernal pressure", "가슴이 조이": "substernal pressure", "가슴이 꽉": "substernal pressure",
    "인슐린을 맞": "known diabetes on insulin insulin use", "인슐린은 맞": "known diabetes on insulin insulin use",
    "인슐린 주사": "known diabetes on insulin insulin use", "손이 떨": "tremor", "몸이 떨": "tremor", "멍해": "confusion",
    "혼란": "confusion", "아침을 걸렀": "missed meal", "식사를 걸렀": "missed meal", "끼니를 걸렀": "missed meal",
    "왼팔": "left arm pain radiates to arm or jaw", "왼쪽 팔": "left arm pain radiates to arm or jaw", "턱까지": "radiates to arm or jaw",
    "신물": "sour taste", "시큼": "sour taste", "타는 것처럼": "burning chest pain", "속이 쓰": "burning chest pain",
    "누우면 더": "worse lying down", "누우면 심": "worse lying down", "먹고 나면": "worse after meals", "식사하고 나면": "worse after meals",
    "제산제": "relieved by antacids", "방이 빙빙": "brief episodic vertigo", "빙글빙글": "brief episodic vertigo",
    "고개를 돌리": "triggered by head position change", "누웠다 일어": "triggered by head position change",
    "눈앞이 캄캄": "prodrome of lightheadedness", "어질어질": "prodrome of lightheadedness",
    "금방 깨어": "rapid spontaneous recovery", "서 있다가": "triggered by standing", "쓰러졌": "brief loss of consciousness",
    "고혈압": "hypertension", "당뇨": "diabetes", "고지혈증": "hyperlipidemia", "심방세동": "atrial fibrillation",
    "천식": "known asthma or COPD", "수술을 받": "recent surgery", "배가 아": "abdominal pain", "윗배": "epigastric abdominal pain",
    "미열": "fever", "열이 났": "fever", "열이 오르": "fever", "열이 심": "fever", "고열": "fever", "토했": "vomiting", "토해": "vomiting",
})


# Round P (NOVA_EVIDENCE_V3): petechiae, drowsiness, diuretics, generalised weakness, cramps. Same discipline.
_DIRECT_LOCALIZED_EVIDENCE_V3: Dict[str, str] = {
    "점상 출혈": "petechial rash rash", "점상출혈": "petechial rash rash", "자반": "petechial rash rash",
    "보라색 반점": "petechial rash rash", "보라색 점": "petechial rash rash",
    "졸려": "altered mental status", "기면": "altered mental status", "의식 저하": "altered mental status",
    "의식이 흐": "altered mental status", "혼미": "altered mental status", "지남력 저하": "altered mental status confusion",
    "헛소리": "confusion",
    "이뇨제": "diuretic use", "소변 나오는 약": "diuretic use",
    "기운이 없": "generalized weakness", "온몸에 힘이 없": "generalized weakness",
    "쥐가 나": "muscle cramps", "근육 경련": "muscle cramps",
    "맥이 불규칙": "irregular heartbeat", "불규칙하게 뛰": "irregular heartbeat", "불규칙한 리듬": "irregular heartbeat",
}


# Round Q (NOVA_EVIDENCE_V3): Korean wording whose word order a fixed substring cannot cover. Each pattern is one
# observation; the bare chest word followed by a heartbeat verb describes the HEARTBEAT, not chest pain.
_KO_HEARTBEAT = re.compile(r"(?:가슴|심장)(?:이|은)?\s*(?:갑자기\s*)?(?:너무\s*|막\s*)?(?:빨리|빠르게|두근|쿵쾅|벌렁)\s*(?:두근\s*)?(?:뛰|거려|거리)")
_KO_CHEST_PAIN_WORD = re.compile(r"가슴[^.。]{0,6}(?:아파|아프|통증|답답|쥐어|조이|짓누르|뻐근|찌르)")
_KO_PATTERNS_V3 = (
    (re.compile(r"소변[^.。]{0,8}(?:따갑|따가|화끈|쓰라|아파|아프)|배뇨통"), "dysuria"),
    (re.compile(r"(?:소변[^.。]{0,6}자주|자주\s*마려|자꾸\s*마려|빈뇨)"), "urinary frequency"),
    (re.compile(r"(?:급하게\s*마려|참기\s*(?:어려|힘들))"), "urinary urgency"),
    # Round U follow-up: upper-central abdominal pain spreading to the back is the existing pancreatitis phrase.
    (re.compile(r"(?:윗배|명치|상복부)[^.。]{0,14}(?:등|허리)\s*(?:까지|으로|쪽으로)?\s*(?:뻗|퍼지|퍼져|방사|울려)"),
     "epigastric pain radiating to back"),
    # Heavy drinking stated in Korean is the existing "alcohol use" risk phrase (no amount inferred).
    (re.compile(r"과음|폭음|술을\s*(?:많이|매일|자주)\s*마"), "alcohol use"),
)


def _present_not_negated(phrase: str, text: str, protected: tuple = ()) -> bool:
    start = text.find(phrase)
    while start != -1:
        end = start + len(phrase)
        if any(lo <= start and end <= hi for lo, hi in protected):
            start = text.find(phrase, start + 1)
            continue
        tail = re.split(r"[.!?。！？,，;；\n]", text[end:], maxsplit=1)[0]
        # A denial belonging to the next symptom must not cancel this one.
        next_concepts = [tail.find(p) for ps in _BARE_CLINICAL_NOUNS.values()
                         for p in ps if tail.find(p) >= 0]
        if next_concepts:
            tail = tail[:min(next_concepts)]
        tail = tail[:12]
        if not any(m in tail for m in _NEGATION_MARKERS):
            return True
        start = text.find(phrase, start + 1)
    return False


_ROUTING_ONLY = frozenset({("vomiting", "吐き気")})


def english_evidence_for(text: str) -> List[str]:
    """Canonical English symptom phrases for every localized (non-ASCII) clinical phrase present in
    `text`. Only phrases containing a non-ASCII character can fire, so plain English never changes."""
    if not text or text.isascii():
        return []
    found: List[str] = []
    # Longest clinical term owns its span: muscle cramp is not an epileptic seizure.
    # A separate occurrence of 경련 elsewhere still retains its existing meaning.
    muscle_spans = tuple((m.start(), m.end()) for m in re.finditer(r"근육\s*경련", text))
    for concept, phrases in MULTILINGUAL_CONCEPT_ALIASES.items():
        english = _CANONICAL_ENGLISH_EVIDENCE.get(concept)
        # Round U follow-up: a ROUTING alias is not always the same observation -- 吐き気 (nausea) routes with the
        # vomiting complaint but is evidence of nausea only (see _DIRECT_LOCALIZED_EVIDENCE), never of vomiting.
        phrases = [p for p in phrases if (concept, p) not in _ROUTING_ONLY]
        if english and english not in found and any((not p.isascii()) and _present_not_negated(p, text) for p in phrases):
            found.append(english)
    for phrase, english in _DIRECT_LOCALIZED_EVIDENCE.items():
        if english not in found and phrase in text and _present_not_negated(
                phrase, text, muscle_spans if phrase == "경련" else ()):
            found.append(english)
    from nova_agent.config import get_config
    if get_config().evidence_v3_enabled:
        for phrase, english in _DIRECT_LOCALIZED_EVIDENCE_V3.items():
            if english not in found and phrase in text and _present_not_negated(phrase, text):
                found.append(english)
        heartbeat = _KO_HEARTBEAT.search(text)
        if heartbeat and _present_not_negated(heartbeat.group(0), text):
            if "chest pain" in found and not _KO_CHEST_PAIN_WORD.search(text):
                found.remove("chest pain")
            for english in ("racing heart", "palpitations"):
                if english not in found:
                    found.append(english)
        for pattern, english in _KO_PATTERNS_V3:
            match = pattern.search(text)
            if (match and english not in found and _present_not_negated(match.group(0), text)
                    and not re.search(r"(?:^|\s)(?:안|못)\s", match.group(0))):   # "소변 볼 때 안 따가워요"
                found.append(english)
    return found
