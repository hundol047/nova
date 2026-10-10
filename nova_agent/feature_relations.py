"""Bounded grammar for existing features; mentions alone do not assert relations.

These patterns normalize observations, not diagnoses. Negation, experiencer and
time projection are applied by matching.py before these predicates are tested.
The same predicate guards canonical and alias paths.
"""
import re

_MEAL = r"(?:meals?|eating|food|dinner|pizza|snacks?|breakfast|lunch)"
_AFTER_MEAL = r"(?:after|following)\s+(?:(?:i\s+)?eat(?:ing)?\b|(?:(?:a|the|big|large|fatty|greasy|heavy)\s+)*" + _MEAL + r")"
_WORSE = r"(?:wors(?:e|ens?|ening)|aggravat(?:ed|es?)|flares?(?: up)?|intensif(?:y|ies))"
_SYMPTOM = r"(?:heartburn|pain|burning|reflux|regurgitation|symptoms?|discomfort|ache|nausea)"
_LYING = r"(?:ly(?:ing|e)(?: down| flat)?|li(?:e|es|ed)(?: down| flat)?|supine)"
_SITTING = r"sit(?:ting|s)?(?: back)?(?: down)?"
_RELIEF = r"(?:improv(?:e|es|ed|ing)|better|eas(?:e|es|ed)|reliev(?:e|ed)|settles?|passes?|goes away)"

def _compile(*patterns):
    return re.compile("|".join("(?:" + p + ")" for p in patterns), re.I)

RELATION_PATTERNS = {
    # These catalog descriptors cannot be supplied by partial word overlap.
    # Require the reported intensity/location, without guessing it from a cause.
    "severe diffuse abdominal pain": _compile(
        r"(?=.*\b(?:severe|intense|unbearable|excruciating)\b)(?=.*\b(?:diffuse|generalized|generalised|all over|whole)\b)(?=.*\b(?:abdominal|abdomen|belly|tummy)\b)"),
    "crampy lower abdominal pain": _compile(
        r"\blower\s+(?:abdominal|abdomen|belly|tummy)\b"),
    "worse after meals": _compile(
        rf"\b{_WORSE}\s+(?:with\s+)?{_AFTER_MEAL}\b",
        rf"\b{_SYMPTOM}\s+(?:(?:starts?|happens?|occurs?|returns?|gets worse|is worse)\s+)?{_AFTER_MEAL}\b",
        rf"\b{_AFTER_MEAL}\s*,?\s*(?:my\s+)?{_SYMPTOM}\s+{_WORSE}\b",
        r"식(?:사|후)[^.;,]{0,12}(?:더\s*아프|심해|악화|속쓰|통증)"),
    "worse lying down": _compile(
        rf"\b{_WORSE}\s+(?:with\s+)?(?:(?:when|on|after|while)\s+)?(?:i\s+)?(?:{_AFTER_MEAL} and\s+)?{_LYING}\b",
        rf"\b{_SYMPTOM}\s+(?:(?:starts?|occurs?|returns?)\s+)?(?:when|on|after|while)\s+(?:i\s+)?{_LYING}\b",
        rf"\b{_LYING}\s+(?:makes? (?:it|the pain|my symptoms) worse|worsens? (?:it|the pain|my symptoms))\b",
        r"누우면[^.;,]{0,12}(?:심해|악화|더\s*아프|속쓰)"),
    "improves with sitting or lying down": _compile(
        rf"\b{_RELIEF}\s+(?:(?:with|by)\s+)?(?:(?:when|on|after|while)\s+)?(?:i\s+)?(?:{_SITTING}|{_LYING})\b",
        rf"\b(?:{_SITTING}|{_LYING})\s+(?:helps?|relieves? (?:it|the dizziness|the symptoms?))\b",
        r"(?:앉|누우)면[^.;,]{0,12}(?:나아|호전|괜찮|좋아)"),
}
# Explicit disjunction branches must not drop the shared relief predicate.
RELATION_PATTERNS["improves with sitting"] = RELATION_PATTERNS["improves with sitting or lying down"]

ROOM_ROTATION = _compile(r"\b(?:room|surroundings|everything)\s+(?:(?:was|is|were|seemed to be)\s+)?(?:spins?|spun|spinning|whirls?|whirled|rotat\w*)\b",
                         r"(?:방|주변|천장)(?:이|가)?\s*(?:빙빙\s*)?(?:돌|도는)",
                         # Japanese: "ぐるぐる回る(めまい)" / "回転性めまい" / "目が回る" describe rotation, not mere unsteadiness.
                         r"ぐるぐる(?:回|まわ)|回転性(?:の)?めまい|目が回")
SHORT_DURATION = _compile(r"\b(?:a few|\d+)\s+seconds?\b", r"\b(?:half a|under a|less than a)\s+minute\b", r"\bbrief(?:ly)?\b", r"(?:몇\s*초|수초|30초|일\s*분\s*미만)",
                          r"(?:数秒|何秒|\d+\s*秒)")
HEAD_POSITION = _compile(r"\b(?:when|whenever|after|as)\s+(?:i\s+)?(?:roll(?:ed|ing)? over|turn(?:ed|ing)? over|turn(?:ed|ing)? my head|tilt(?:ed|ing)? my head)\b",
                         r"(?:고개를\s*(?:돌리|돌렸)|돌아누우|돌아누웠)",
                         # Japanese: turning over in bed (寝返り), moving/turning the head, sitting up.
                         r"寝返り|頭を(?:動か|回|向け)|起き上が")


def observed_rotation_features(clause: str) -> list[str]:
    """Do not invent brevity or a posture trigger from 'dizzy' or 'turn' alone."""
    if not ROOM_ROTATION.search(clause):
        return []
    found = ["vertigo"]
    if SHORT_DURATION.search(clause):
        found.append("brief episodic vertigo")
    if HEAD_POSITION.search(clause):
        found.append("triggered by head position change")
    return found


STERNAL_PRESSURE = _compile(
    r"\b(?:pressure|squeezing|tightness|heaviness|crushing(?: pain)?)\s+(?:behind|under|beneath|below)\s+(?:(?:my|the)\s+)?(?:breastbone|sternum)\b",
    # The existing KB feature already groups pressure/squeezing/weight on the
    # chest (lay_language.py). Preserve that vocabulary family without inferring
    # a cause, exertion trigger, ECG finding or confirmed anatomical lesion.
    r"\bchest\s+(?:pressure|squeezing|tightness|heaviness)\b",
    r"\b(?:crushing|squeezing|constricting)\s+chest\s+(?:pain|discomfort)\b",
    r"\b(?:pressure|squeezing|tightness|heaviness|(?:a\s+)?heavy weight)\s+(?:(?:began|started|developed)\s+)?(?:deep\s+)?(?:on|across|in)\s+(?:(?:my|the)\s+)?(?:upper\s+)?chest\b",
    # Round V: the same sensation-on-chest wording in Japanese and Korean (締め付け/圧迫/重苦しい, 조이/짓누르/누르는).
    r"胸(?:が|を|の)?[^。、,]{0,4}(?:締め付け|締めつけ|圧迫|重苦し|押さえつけ)",
    r"가슴(?:이|을|에)?\s*(?:꽉\s*)?(?:조이|조여|짓누르|짓눌|누르는|눌리|압박)")
PAIN_SPREAD = _compile(
    r"\b(?:pressure|pain|ache)\s+(?:that\s+)?(?:spreads?|spreading|travels?|traveling|radiates?|radiating)\s+(?:to|into)\s+(?:(?:my|the)\s+)?(?:(?:left|right)\s+)?(?:arms?|shoulders?|jaw)\b",
    r"\bpain\s+(?:to|into)\s+(?:(?:my|the)\s+)?(?:(?:left|right|both)\s+)?(?:arms?|shoulders?|jaw)\b",
    # Round V: spread of the chest pain to the arm/shoulder/jaw in Japanese and Korean.
    r"(?:左|右|両)?(?:腕|肩|顎|あご)(?:に|へ|まで)(?:も)?(?:広が|放散|響|走)",
    r"(?:왼|오른|양)?(?:쪽\s*)?(?:팔|어깨|턱)(?:으로|로|까지|에)\s*(?:도\s*)?(?:퍼지|퍼져|뻗치|뻗쳐|뻗|번지|번져|방사|울려)")


def observed_pressure_features(clause: str) -> list[str]:
    """Existing features require both the sensation and its observed anatomy.

    Called only after the shared assertion/subject/time projection. No diagnosis
    is generated, and spreading rash or an anatomical mention alone is ignored.
    """
    return (["substernal pressure"] if STERNAL_PRESSURE.search(clause) else []) + (
        ["radiates to arm or jaw"] if PAIN_SPREAD.search(clause) else [])
