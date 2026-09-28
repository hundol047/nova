"""Maps a free-text chief complaint onto one of the fixed chief-complaint tags the knowledge base
is organized by (spec section 17's eight case categories). Deterministic, bilingual, with an
explicit 'other' fallback rather than a guessed tag.

Three-level matching, in priority order (never a global synonym substitution -- every alias below
is scoped to the ONE concept it's keyed under, exactly like the feature-local aliases in
differential.py's FEATURE_ALIASES, for the same reason: a global word-group table let unrelated
findings cross-contaminate each other's matches the one time this repo tried it):

  1. Exact/substring phrase match against CONCEPT_PHRASES -- either the concept's own canonical
     clinical term(s) (match_type="exact") or a scoped lay-language alias (match_type="alias").
  2. Token/phrase similarity fallback (match_type="fuzzy") -- reuses matching.py's stemmed
     word-overlap scorer (the same one differential.py and safety.py already rely on) so a
     phrasing that doesn't exactly match any alias but clearly shares the same content words still
     routes correctly, at a lower confidence than an exact/alias hit.
  3. Explicit 'other' (match_type="none") -- only when neither of the above produces any signal.

Every alias here is a GENERIC lay phrasing of its concept, not a sentence lifted from any
evaluation case file (evaluation/cases.py, held_out_cases.py, generalization_cases_v2.py,
generalization_stress_cases.py, blind_cases_v3.py, blind_cases_v4.py) -- a distinctive phrase that
reads as copied from one specific vignette rather than a phrasing many different patients would
plausibly use is exactly what this module must not contain, since that would make a classifier
look accurate on a blind set for the wrong reason (memorized wording, not real generalization).

route() returns a ChiefComplaintRoutingResult with enough structure (primary tag, its score, the
next-best tags, the score margin between them, how the primary was matched, and an overall
confidence tier) for differential.py to build a candidate pool that matches how sure the routing
actually is, rather than either a single hard-routed tag or an untargeted whole-catalog dump every
time the match is imperfect:

  HIGH   -- a clean exact/alias hit with no other tag close behind: primary tag's pool only.
  MEDIUM -- an exact/alias hit tied with another tag, or a fuzzy hit with a real margin over the
            next-best: merge the top 2 concepts' pools.
  LOW    -- a fuzzy hit with little or no margin over the next-best (a genuine ambiguous tie):
            merge the top 3 concepts' pools, plus the small cross-cutting can't-miss list.
  (primary_tag == "other", match_type == "none") -- no signal at all: differential.py's existing
            whole-catalog fallback is the last resort, which already contains every cross-cutting
            diagnosis, so nothing further is added here.

`classify()` and `top_candidates()` remain as thin wrappers over `route()` for callers (and tests)
that only need the single best tag or a ranked list, without the full structured result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Tuple

from nova_agent.matching import _content_words

MatchType = Literal["exact", "alias", "fuzzy", "none"]
Confidence = Literal["HIGH", "MEDIUM", "LOW"]

# Each concept's own canonical clinical term(s) -- a hit here is match_type "exact". Everything
# else in CONCEPT_PHRASES[tag] is a scoped lay-language ALIAS (match_type "alias"). The split only
# affects the reported match_type, never the score: an alias hit is exactly as strong as a
# canonical-term hit, since a lay patient describing "my chest hurts" is not less informative than
# one who says "chest pain".
CANONICAL_TERMS = {
    "chest_pain": ["chest pain"],
    "abdominal_pain": ["abdominal pain"],
    "headache": ["headache"],
    "fever": ["fever"],
    "dyspnea": ["dyspnea", "shortness of breath", "difficulty breathing", "trouble breathing"],
    "dizziness": ["dizziness", "vertigo"],
    "altered_mental_status": ["altered mental status", "confusion"],
    "urinary_symptoms": ["dysuria", "urinary frequency", "painful urination"],
    "syncope": ["syncope", "fainting", "fainted"],
    "palpitations": ["palpitations"],
    "vomiting": ["vomiting"],
    "weakness": ["weakness", "generalized weakness"],
    "cough": ["cough"],
    "back_pain": ["back pain", "flank pain"],
    "leg_swelling": ["leg swelling", "edema"],
    "focal_weakness": ["focal weakness", "one-sided weakness"],
    "aphasia": ["aphasia", "slurred speech"],
    "gi_bleeding": ["gi bleeding", "gastrointestinal bleeding"],
    "pelvic_gynecologic": ["pelvic pain", "vaginal bleeding"],
    "trauma": ["trauma", "traumatic injury"],
    "allergic": ["allergic reaction", "anaphylaxis"],
    "metabolic": ["metabolic symptoms", "hyperglycemia"],
    # Added by the systematic Tier-1 typical_features audit (Round D): each of these was found by
    # cross-referencing EVERY Tier-1 disease's own typical_features/aliases against the existing
    # CONCEPT_PHRASES tables and flagging phrases that route to NOTHING at all (see
    # scripts/audit_chief_complaint_coverage.py) -- never derived from, or scoped to, any specific
    # blind-set case's wording. Each is justified by at least one real Tier-1 disease's own
    # curated typical_features, not invented.
    "upper_respiratory": ["runny nose", "nasal congestion", "sore throat", "stuffy nose"],
    "diarrhea": ["diarrhea", "loose stools"],
    "numbness": ["numbness", "sensory loss", "tingling"],
    "vision_changes": ["vision loss", "blurry vision", "double vision", "vision changes"],
    "neck_stiffness": ["neck stiffness", "stiff neck"],
    "hemoptysis": ["hemoptysis"],
    "seizure": ["seizure", "convulsion"],
}

# Generic lay-language aliases only -- each phrase describes how an ordinary patient would plausibly
# word the concept, never a sentence reused from a specific evaluation vignette.
CONCEPT_ALIASES = {
    "chest_pain": ["chest tightness", "chest pressure", "chest hurts", "chest discomfort",
                   "pain in my chest",
                   "흉통", "가슴 통증", "가슴이 아프", "가슴이 아파",
                   "胸が痛い", "胸の痛み", "胸が締め付けられる",
                   "胸痛", "胸闷", "胸口疼"],
    "abdominal_pain": ["stomach pain", "belly pain", "stomach hurts", "my stomach", "tummy",
                        "gut pain", "stomach ache", "cramping in my stomach", "pain in my gut",
                        "복통", "배가 아프", "배가 아파",
                        "お腹が痛い", "腹痛", "胃が痛い",
                        "腹痛", "肚子疼", "胃痛"],
    "headache": ["head pain", "head hurts", "head is pounding", "splitting headache",
                 "head is throbbing", "pain in my head",
                 "두통", "머리가 아프", "머리가 아파",
                 "頭が痛い", "頭痛",
                 "头痛", "头疼"],
    "fever": ["chills", "high temperature", "burning up", "running a temperature", "feverish",
              "temperature is high", "hot and shivery",
              "열", "발열", "오한",
              "発熱", "悪寒", "熱がある",
              "发热", "寒战", "发烧"],
    "dyspnea": ["breathless", "can't breathe", "cant breathe", "can't catch my breath",
                "out of breath", "winded", "hard to breathe", "unable to breathe comfortably",
                "not getting enough air", "air hunger", "struggling to breathe", "throat feels tight",
                "throat is tightening", "gasping for air", "harder to breathe",
                "wheezing", "wheeze", "wheezy", "whistling when I breathe",
                "숨이 차", "호흡곤란",
                "息苦しい", "息ができない", "呼吸が苦しい", "息が苦しい",
                "呼吸困难", "喘不过气", "喘不上气"],
    "dizziness": ["dizzy", "lightheaded", "light-headed", "room spinning", "woozy",
                  "어지러", "현훈",
                  "めまいがする", "ふらふらする",
                  "头晕", "眩晕"],
    "altered_mental_status": ["confused", "unresponsive", "disoriented", "not making sense",
                              "out of it", "not himself", "not herself", "not tracking conversation",
                              "mentally foggy", "not acting like himself", "not acting like herself",
                              "seems out of it", "can't focus", "can't think straight", "zoning out",
                              "의식", "혼돈", "의식저하",
                              "意識がぼんやりする", "意識障害", "反応が鈍い",
                              "意识模糊", "神志不清", "反应迟钝"],
    "urinary_symptoms": ["blood in urine", "burning when I pee", "burns when I pee",
                          "burning when I urinate", "pain when urinating", "peeing", "urinate",
                          "bladder",
                          "소변", "배뇨통", "빈뇨",
                          "排尿時の痛み", "頻尿", "血尿",
                          "排尿疼痛", "尿频", "血尿"],
    "syncope": ["passed out", "loss of consciousness", "blacked out", "went unconscious",
                "lost consciousness", "collapsed", "went dark",
                # Deliberately "went dark", not "everything went dark": the 3-word original let
                # "everything"+"went" (both generic, present in almost any sudden-change sentence)
                # carry 2-of-3 overlap on their own, spuriously matching unrelated text like
                # "everything went blurry" (vision_changes, not syncope) without the one truly
                # distinguishing word ("dark") ever being present -- a real false positive this
                # round's own routing benchmark caught (scripts/benchmark_chief_complaint_routing.py).
                # The narrower 2-word phrase forces the "<=2 words requires ALL" tier, same
                # discipline as hemoptysis's "coughing blood"/"spitting blood" aliases.
                "실신", "기절",
                "失神", "気を失った",
                "晕厥", "昏倒", "晕倒"],
    "palpitations": ["heart racing", "irregular heartbeat", "heart pounding", "skipping beats",
                      "racing heart", "heart is fluttering", "heart skipping",
                      "pulse pounding in my throat", "feel my pulse in my throat",
                      "두근거림", "심계항진",
                      "動悸", "心臓がドキドキする",
                      "心悸", "心跳加速"],
    "vomiting": ["throwing up", "nausea and vomiting", "puking",
                 "구토", "토했",
                 "吐き気", "嘔吐",
                 "呕吐", "恶心"],
    "weakness": ["feeling weak", "muscle weakness", "no energy", "can't move", "no strength",
                 "body feels heavy", "drained of energy", "feel completely exhausted",
                 "무기력", "힘이 없",
                 # "力が入らない" deliberately NOT used here -- it's a literal substring of
                 # focal_weakness's own JA alias "片側に力が入らない" below, which would make this
                 # generic tag spuriously co-match (and, on a score tie, sometimes WIN over) every
                 # one-sided-weakness phrasing. "体に力が出ない" is a distinct phrase that doesn't
                 # embed focal_weakness's wording as a substring.
                 "体がだるい", "体に力が出ない",
                 "没有力气", "浑身无力"],
    "cough": ["coughing", "productive cough",
              "기침",
              "咳が出る", "咳",
              "咳嗽"],
    "back_pain": ["lower back pain", "side hurts", "side pain", "my flank",
                  "요통", "옆구리 통증",
                  "腰が痛い", "背中の痛み", "脇腹の痛み",
                  "腰痛", "背痛", "腰部疼痛"],
    "leg_swelling": ["swollen leg", "calf swelling",
                      "다리 부종", "종아리 부종",
                      "脚のむくみ", "ふくらはぎの腫れ",
                      "腿肿", "小腿肿胀"],
    "focal_weakness": ["weakness on one side", "one side feels weak", "arm won't work on one side",
                        "leg won't work on one side", "can't lift my arm", "face is drooping",
                        "drooping on one side", "one side of my face is drooping",
                        "face suddenly dropped", "side of my face dropped", "face dropped on one side",
                        "can't move my arm on one side", "can't move one side",
                        "한쪽 힘이 빠짐", "편측 위약", "얼굴이 한쪽으로 처짐", "한쪽 팔에 힘이 없",
                        "片側に力が入らない", "片方の手足が動かない", "顔が片側に下がる",
                        "一侧无力", "手臂没力气", "一侧肢体无力", "脸部一侧下垂"],
    "aphasia": ["trouble finding words", "can't find my words", "words come out wrong",
                "can't speak clearly", "difficulty speaking", "speech sounds slurred",
                "can't get words out",
                "말이 어눌함", "말이 어눌해", "말이 안 나옴", "단어가 생각나지 않음", "발음이 이상함",
                "言葉が出ない", "ろれつが回らない", "うまく話せない", "うまく話せません",
                "说话困难", "言语不清", "说不出话"],
    "gi_bleeding": ["blood in my stool", "black stools", "tarry stools", "vomiting blood",
                     "blood in my vomit", "rectal bleeding", "blood when I wipe",
                     "혈변", "흑변", "토혈", "피를 토함",
                     "吐血", "黒い便", "血便",
                     "呕血", "黑便", "便血"],
    "pelvic_gynecologic": ["vaginal spotting", "missed period", "cramping in my pelvis",
                            "lower pelvic pain", "pain in my ovary area", "pain in my pelvis",
                            "질 출혈", "골반통", "생리가 없음",
                            "性器出血", "骨盤の痛み", "生理が来ない",
                            "阴道出血", "盆腔疼痛", "月经推迟"],
    "trauma": ["car accident", "fell down", "hit my head", "got into an accident",
               "was in a crash", "injured in a fall", "fell and hurt myself",
               "넘어짐", "낙상", "교통사고", "외상",
               "転倒した", "交通事故に遭った", "頭を打った",
               "摔倒", "车祸", "外伤", "跌倒受伤"],
    "allergic": ["hives", "swelling after a sting", "broke out in a rash after eating",
                 "reaction to a sting", "reaction to a food", "itchy welts", "throat swelling after exposure",
                 "throat tightness", "throat feels tight after eating", "tongue swelling", "lips swelling",
                 "두드러기", "입술 부종", "혀 부종", "목이 붓는 느낌",
                 "じんましん", "唇が腫れる", "喉が腫れる感じ",
                 "荨麻疹", "嘴唇肿胀", "喉咙发紧"],
    "metabolic": ["excessive thirst", "urinating a lot lately", "fruity breath", "rapid weight loss",
                  "extreme thirst and urination", "drinking a lot of water lately",
                  "물을 많이 마심", "소변을 자주 봄", "갈증이 심함",
                  "喉が渇く", "尿の回数が増えた", "急激な体重減少",
                  "口渴", "多尿", "体重迅速下降"],
    # New domains from the systematic Tier-1 coverage audit (see CANONICAL_TERMS comment above).
    "upper_respiratory": ["stuffy nose", "congested", "scratchy throat", "throat is scratchy",
                           "throat hurts", "cold symptoms", "sniffly", "rhinorrhea"],
    "diarrhea": ["loose stool", "watery stool", "the runs"],
    "numbness": ["numb", "pins and needles", "can't feel my", "no feeling in my"],
    "vision_changes": ["can't see right", "seeing double", "vision is blurry", "lost vision",
                        "spots in my vision"],
    "neck_stiffness": ["neck won't bend", "stiff neck", "can't move my neck"],
    # Deliberately kept to exactly 2 content words each ("blood" + one anchor word) -- a 3+ word
    # phrase like "coughing up blood" would let the shared fuzzy-matching pool's >=60%-overlap rule
    # match on "coughing"+"up" alone (2 of 3 words) without "blood" itself ever being present, as
    # in "coughing up some clear mucus" -- a real false positive this round's own regression suite
    # caught. See matching.py's/chief_complaint.py's own fuzzy-threshold docs for why a <=2-word
    # phrase requires ALL its words, closing exactly this gap.
    "hemoptysis": ["coughing blood", "spitting blood", "blood in my cough", "blood in my spit"],
    "seizure": ["convulsing", "shaking uncontrollably", "had a fit"],
}

CONCEPT_PHRASES = {tag: CANONICAL_TERMS[tag] + CONCEPT_ALIASES.get(tag, []) for tag in CANONICAL_TERMS}
_CANONICAL_SET = {tag: {t.lower() for t in terms} for tag, terms in CANONICAL_TERMS.items()}

# Backward-compatible alias for anything still importing the old flat name.
CHIEF_COMPLAINT_KEYWORDS = CONCEPT_PHRASES

# Presentations without their own dedicated disease pool are routed to the closest clinically
# related tag(s) so the candidate pool stays targeted instead of falling through to the entire
# knowledge base.
RELATED_TAGS = {
    "syncope": ["dizziness", "chest_pain"],
    "palpitations": ["chest_pain", "dizziness"],
    "vomiting": ["abdominal_pain"],
    "weakness": ["altered_mental_status", "dizziness"],
    "cough": ["dyspnea", "fever"],
    "back_pain": ["abdominal_pain", "urinary_symptoms"],
    "leg_swelling": ["dyspnea"],
    "focal_weakness": ["weakness", "altered_mental_status"],
    "aphasia": ["altered_mental_status", "focal_weakness"],
    "gi_bleeding": ["abdominal_pain", "vomiting"],
    "pelvic_gynecologic": ["abdominal_pain"],
    "trauma": ["chest_pain"],
    "allergic": ["dyspnea"],
    "metabolic": ["altered_mental_status", "weakness"],
    "upper_respiratory": ["cough", "fever"],
    "diarrhea": ["abdominal_pain", "vomiting"],
    "numbness": ["focal_weakness", "altered_mental_status"],
    "vision_changes": ["headache", "dizziness", "focal_weakness"],
    "neck_stiffness": ["headache", "fever"],
    "hemoptysis": ["cough", "chest_pain"],
    "seizure": ["altered_mental_status"],
}

# Specificity precedence (spec: "specific clinically meaningful concept > generic umbrella
# concept" -- never deletion of the generic tag, which stays fully available for genuinely
# nonspecific presentations; this only ever reorders which concept becomes PRIMARY when a more
# specific alternative also has real signal in the same text). Each generic tag maps to the
# specific tag(s) that should take precedence over it -- deliberately small and hand-curated from
# real clinical reasoning (a focal/localized presentation is more actionable and often more
# dangerous than its generic umbrella; a confirmed loss-of-consciousness event is a more specific
# claim than generic dizziness; a bleeding-pattern abdominal complaint is more specific than a
# bare abdominal-pain complaint), never derived from or scoped to any blind-set case.
SPECIFICITY_PRECEDENCE = {
    "weakness": ("focal_weakness", "aphasia", "numbness"),
    "dizziness": ("syncope",),
    "abdominal_pain": ("gi_bleeding",),
    # A genuine hemoptysis mention (real "blood" signal, via the tightened 2-content-word
    # blood-anchored aliases -- see CONCEPT_ALIASES's own comment) is always more specific and
    # more urgent than the generic "cough" tag it would otherwise be buried under as a mere
    # secondary tag (found by this round's own routing benchmark, which caught "I spit out some
    # blood after coughing" routing to plain "cough" as primary with hemoptysis demoted to
    # secondary -- exactly the shadowing this precedence mechanism exists to prevent).
    "cough": ("hemoptysis",),
}

# Lower bar than _FUZZY_MATCH_THRESHOLD below, used ONLY to detect "does this more specific
# concept have ANY real, meaningful signal in the text too" for the precedence check above -- never
# used to let a specific tag independently qualify as primary on its own merits elsewhere. A real
# but partial word-overlap (e.g. 2 of 4 meaningful content words) is legitimate corroborating
# signal for precedence purposes even where it would be too weak to stand alone.
_PRECEDENCE_FUZZY_THRESHOLD = 0.4

# Cross-cutting can't-miss diagnoses (spec: soft routing must never lose safety coverage just
# because the chief complaint didn't cleanly match one category). Deliberately small and by
# diagnosis id, not duplicated logic -- differential.py already has a general critical-condition
# mechanism (safety.py's critical_condition_ids); this list is only the identifiers, consulted by
# differential.py when building a LOW-confidence candidate pool.
CROSS_CUTTING_DANGEROUS_DIAGNOSES = [
    "sepsis", "acute_coronary_syndrome", "pulmonary_embolism", "ischemic_stroke",
    "aortic_dissection", "diabetic_ketoacidosis", "hypoglycemia", "acute_abdomen",
]

_FUZZY_MATCH_THRESHOLD = 0.6  # same overlap ratio matching.py's feature_present() already uses

# An exact/alias primary tag needs at least this much of an integer-hit-count lead over the
# runner-up to count as unambiguous (scores in that range are always 1.0 + an integer hit count,
# so any real lead is >= 1.0 -- a tie is exactly 0.0). A fuzzy-only primary needs at least this
# much of a ratio lead over the runner-up to count as a real (not coincidental) margin.
_EXACT_HIGH_MARGIN = 1.0
_FUZZY_MEDIUM_MARGIN = 0.15

# `_content_words()` splits on any non-alphanumeric character, so a contraction like "can't" or
# "it's" becomes two tokens ("can"/"t", "it"/"s") -- neither is stopword-filtered by matching.py's
# shared list (that list is tuned for clinical KB-feature text, not casual chief-complaint prose),
# and a leftover single-letter fragment or a bare auxiliary verb is not a meaningful content word
# for THIS fuzzy comparison. Filtered locally here only -- never fed back into matching.py's own
# stopword set, which other, already-verified matching behavior depends on.
_CONTRACTION_NOISE = {"t", "s", "m", "re", "ve", "ll", "d", "can"}


def _meaningful_words(words: set) -> set:
    return words - _CONTRACTION_NOISE


# Cached per-tag content-word sets for the fuzzy fallback -- computed once at import time, not
# per-call, since CONCEPT_PHRASES never changes at runtime. A phrase that degenerates to a single
# (or zero) meaningful word after stopword/contraction filtering (e.g. "out of it" -> just {"out"})
# is dropped entirely from fuzzy eligibility: exact/substring matching still catches it precisely,
# but a single common word scoring a trivial 1.0 overlap ratio against nearly any unrelated text is
# exactly the false-positive mechanism this fuzzy layer must not introduce.
_KEYWORD_CONTENT_WORDS: dict = {
    tag: [words for kw in keywords
          for words in [_meaningful_words(_content_words(kw))] if len(words) >= 2]
    for tag, keywords in CONCEPT_PHRASES.items()
}


def _fuzzy_score(text_words: set, tag: str) -> float:
    """Best word-overlap ratio between `text_words` and any single phrase under `tag` (both sides
    pre-filtered of contraction noise), using the same stemmed-content-word approach matching.py's
    feature_present() already uses elsewhere in this codebase."""
    return _fuzzy_score_and_overlap(text_words, tag)[0]


def _fuzzy_score_and_overlap(text_words: set, tag: str) -> Tuple[float, int]:
    """Same best-phrase search as `_fuzzy_score()`, but also returns that best phrase's raw
    overlapping-word COUNT (not just the ratio) -- needed by `_apply_specificity_precedence()`'s
    sub-threshold promotion path, where a bare ratio is not enough: a short 2-word CANONICAL term
    like focal_weakness's own "focal weakness" (content words {"focal", "weak"} -- "weakness"
    stems to "weak", the SAME root the generic "weakness" tag it's meant to be distinguished from
    also uses) can hit ratio 0.5 from the single coincidental shared-stem word alone, with zero
    genuine focal/lateralizing signal actually present in the text -- a real false positive this
    round's own routing benchmark caught. Requiring at least 2 overlapping words for that
    promotion path (see its own call site) closes this without weakening the ratio threshold used
    for regular top-level fuzzy MATCHING (`_fuzzy_score()`, threshold 0.6, already only ever
    reachable in this same false way if a 2-word phrase's ENTIRE content overlaps, which is a
    complete phrase match, not a coincidence)."""
    best_ratio = 0.0
    best_overlap = 0
    for kw_words in _KEYWORD_CONTENT_WORDS[tag]:
        if not text_words:
            continue
        overlap = kw_words & text_words
        ratio = len(overlap) / len(kw_words)
        if ratio > best_ratio:
            best_ratio = ratio
            best_overlap = len(overlap)
    return best_ratio, best_overlap


@dataclass
class ChiefComplaintRoutingResult:
    primary_tag: str                    # "other" when nothing matched at all
    primary_score: float
    secondary_tags: List[str] = field(default_factory=list)   # ranked, excludes primary
    score_margin: float = 0.0           # primary_score - next-best score (0.0 if no runner-up)
    match_type: MatchType = "none"
    confidence: Confidence = "LOW"


def _scores(chief_complaint_text: str) -> List[Tuple[str, float, MatchType]]:
    """Every tag that scored anything against `chief_complaint_text`, highest first, each tagged
    with HOW it matched. An exact/alias hit always outranks a fuzzy-only match (scored in a
    disjoint, higher range) so fuzzy matching can only ever ADD coverage for phrasing exact/alias
    terms miss, never override a real hit."""
    lowered = (chief_complaint_text or "").lower()
    text_words = _meaningful_words(_content_words(lowered))
    scored: List[Tuple[str, float, MatchType]] = []
    for tag, phrases in CONCEPT_PHRASES.items():
        matched = [p for p in phrases if p.lower() in lowered]
        if matched:
            exact_hits = sum(1 for p in matched if p.lower() in _CANONICAL_SET[tag])
            match_type: MatchType = "exact" if exact_hits > 0 else "alias"
            # A tiny length-proportional tiebreaker (spec: a more SPECIFIC phrase match should
            # count for more than a generic one, same principle differential.py's
            # _specificity_multiplier already applies to typical_feature scoring). Needed because
            # a longer, more specific alias can legitimately CONTAIN a shorter, more generic
            # alias from a DIFFERENT tag as a literal substring (e.g. focal_weakness's "한쪽 팔에
            # 힘이 없" contains weakness's own "힘이 없") -- both tags then match the same
            # match-count and would otherwise tie, with the winner decided only by which tag
            # happens to sort first in CONCEPT_PHRASES (dict insertion order), not by which match
            # is actually more clinically specific. Weighted small enough (<=0.01 per matched
            # phrase's length, so well under 1.0 even for a long phrase) that it can only ever
            # break an EXACT tie in match count -- it can never overturn a tag that matched more
            # distinct phrases, or flip an exact/alias hit's ordering against a fuzzy-only one
            # (those already live in disjoint score ranges).
            specificity_bonus = 0.01 * sum(min(len(p), 30) for p in matched) / max(len(matched), 1)
            scored.append((tag, 1.0 + len(matched) + specificity_bonus, match_type))
            continue
        fuzzy = _fuzzy_score(text_words, tag)
        if fuzzy >= _FUZZY_MATCH_THRESHOLD:
            scored.append((tag, fuzzy, "fuzzy"))
    scored.sort(key=lambda t: t[1], reverse=True)
    # Specificity precedence applied HERE, in the shared primitive both route() (single-best-tag
    # routing) and clinical_presentation.extract_presentation() (multi-concept extraction) build
    # on -- so a more specific concept promoted over a generic one is visible to BOTH consumers
    # identically, not just whichever one happened to re-implement the check.
    return _apply_specificity_precedence(scored, text_words)


def _apply_specificity_precedence(scored: List[Tuple[str, float, MatchType]], text_words: set
                                   ) -> List[Tuple[str, float, MatchType]]:
    """Promotes a more specific concept over a generic umbrella one when both have real signal in
    the same text (see SPECIFICITY_PRECEDENCE's own docstring for the clinical rationale). Only
    ever REORDERS/ADDS -- a generic tag with no eligible specific alternative present is completely
    unaffected and never removed from `scored`, so it remains available (possibly still primary)
    for a genuinely nonspecific presentation. Checked in the specific tags' listed priority order;
    the first one with any real signal (already-thresholded fuzzy/alias/exact, OR a real but
    sub-threshold fuzzy overlap) is promoted -- and, in the sub-threshold case, promoted with AT
    LEAST the generic tag's own score, never less: the specific interpretation is judged at least
    as strong evidence as the generic one it supersedes, so every downstream consumer of this
    shared primitive (route()'s own confidence calc, AND clinical_presentation.py's
    extract_presentation() multi-concept inclusion threshold, which calls _scores() directly) must
    treat the promoted concept with due strength, not as a marginal, easily-dropped add-on."""
    if not scored:
        return scored
    generic_tag, generic_score, generic_mt = scored[0]
    alternatives = SPECIFICITY_PRECEDENCE.get(generic_tag)
    if not alternatives:
        return scored
    present = {t: (t, s, mt) for t, s, mt in scored}
    for specific_tag in alternatives:
        if specific_tag in present:
            # Already independently cleared ITS OWN normal threshold (real alias/exact/fuzzy
            # evidence, not a coincidental stem collision) -- always promoted, regardless of how
            # the generic tag itself matched.
            entry = present[specific_tag]
            rest = [e for e in scored if e[0] != specific_tag]
            return [entry] + rest
        if generic_mt == "exact":
            # A clean EXACT canonical-term hit on the generic tag (e.g. "generalized weakness") is
            # never second-guessed by a sub-threshold fuzzy score alone -- that sub-threshold
            # signal is frequently just the generic tag's OWN word stem ("weak"/"weakness")
            # coincidentally overlapping with the specific tag's alias vocabulary (e.g. "weakness
            # on one side" also contains "weakness"), not genuine focal/lateralizing evidence. Only
            # an ALIAS/fuzzy-matched generic primary (inherently more ambiguous lay phrasing) is
            # eligible for this weaker promotion path.
            continue
        weak_score, weak_overlap_count = _fuzzy_score_and_overlap(text_words, specific_tag)
        # Requiring >= 2 overlapping words (not just a ratio) blocks the single-shared-stem-word
        # false positive a bare 2-word canonical term can produce (see
        # _fuzzy_score_and_overlap()'s own docstring) while still allowing a genuine short phrase
        # match (e.g. "arm won't work on one side" overlapping on "arm"+"side") through.
        if weak_score >= _PRECEDENCE_FUZZY_THRESHOLD and weak_overlap_count >= 2:
            promoted_score = max(weak_score, generic_score)
            return [(specific_tag, promoted_score, "fuzzy")] + scored
    return scored


def route(chief_complaint_text: str) -> ChiefComplaintRoutingResult:
    """The full structured routing decision: which tag(s) are plausible, how sure the match is,
    and (via `confidence`) how differential.py should size the resulting candidate pool."""
    scored = _scores(chief_complaint_text)
    if not scored:
        return ChiefComplaintRoutingResult(primary_tag="other", primary_score=0.0,
                                            secondary_tags=[], score_margin=0.0,
                                            match_type="none", confidence="LOW")

    primary_tag, primary_score, match_type = scored[0]
    secondary_tags = [tag for tag, _score, _mt in scored[1:]]
    runner_up_score = scored[1][1] if len(scored) > 1 else None
    margin = primary_score - runner_up_score if runner_up_score is not None else primary_score

    if match_type in ("exact", "alias"):
        confidence: Confidence = "HIGH" if (runner_up_score is None or margin >= _EXACT_HIGH_MARGIN) \
            else "MEDIUM"
    else:  # fuzzy
        confidence = "MEDIUM" if margin >= _FUZZY_MEDIUM_MARGIN else "LOW"

    return ChiefComplaintRoutingResult(primary_tag=primary_tag, primary_score=primary_score,
                                        secondary_tags=secondary_tags, score_margin=margin,
                                        match_type=match_type, confidence=confidence)


def classify(chief_complaint_text: str) -> str:
    """Returns the best-matching tag, or 'other' if nothing matches (never a guessed tag)."""
    return route(chief_complaint_text).primary_tag


def top_candidates(chief_complaint_text: str, k: int = 3) -> List[str]:
    """Up to `k` plausible tags for this chief complaint (primary first, then ranked secondaries),
    for callers that only need the list, not the full routing result. Empty when nothing scored at
    all (genuinely unclassifiable text)."""
    result = route(chief_complaint_text)
    if result.match_type == "none":
        return []
    return [result.primary_tag] + result.secondary_tags[:max(0, k - 1)]


def related_tags(tag: str) -> list:
    """Additional tags whose disease pool is clinically relevant to `tag`, used by
    differential.diseases_for_tag() to build a targeted (not whole-catalog) candidate pool for
    presentations that don't have their own disease entries tagged directly."""
    return RELATED_TAGS.get(tag, [])
