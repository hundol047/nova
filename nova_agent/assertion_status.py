"""Lexical uncertainty markers: hypotheses are not affirmative observations.

This intentionally does not infer probabilities or interpret negative tests.
"""
import re

_UNCERTAIN = re.compile(
    r"\b(?:possible|possibly|suspected|suspicious for|question of|uncertain|"
    r"cannot (?:exclude|rule out)|can't (?:exclude|rule out)|"
    r"(?:cannot|can't) be (?:excluded|ruled out)|not (?:excluded|ruled out)|"
    r"(?:cannot|can't|could not) (?:yet )?(?:confirm|verify|establish)|"
    r"(?:cannot|can't|could not) (?:yet )?be (?:confirmed|verified|established)|"
    r"not (?:yet )?(?:confirmed|verified|established)|"
    r"rule out|may (?:be|represent|indicate)|might (?:be|represent|indicate))\b",
    re.I,
)


def is_uncertain(clause: str) -> bool:
    return bool(_UNCERTAIN.search(clause))


# --- Round Q: shared clause-level cues for diagnosis-mention scope (nova_agent/documented_diagnosis.py) ---------
# Applied to ONE clause with the diagnosis names blanked out. Uncertainty compounds are always consulted before
# plain negation, so "cannot be excluded" / "배제할 수 없다" are never read as "excluded" / "없다".
UNCERTAIN_CUE = re.compile(
    _UNCERTAIN.pattern + r"|\b(?:probable|probably|likely|unlikely|query|suspect\w*|suspicion|maybe|could be|"
    r"not yet (?:excluded|ruled out)|not been (?:excluded|ruled out)|r/o)\b|\?|"
    r"\b(?:cannot|can\'t)(?: yet| entirely| completely)? be (?:excluded|ruled out)\b|\b(?:remains? a possibility|considered)\b|"
    r"의심|배제할 ?수 ?없|배제(?:하지)? ?못|가능성|일 ?수도|아닐까|추정|것 ?같",
    re.I,
)
NEGATION_CUE = re.compile(
    r"\b(?:excluded|excludes?|exclusion|rejected|ruled out|rules out|absent|negative for|no evidence of|no|not|without|"
    r"free of|denies|denied|isn't|wasn't|aren't|weren't|never)\b|"
    r"아니(?:라|다|에요|래|었|였|고|며)|아닌|없(?:다|어|음|었|는|고)|배제(?:됐|되었|됨|했|되어|라고)|음성",
    re.I,
)
AFFIRM_CUE = re.compile(
    r"\b(?:confirms?|confirmed|diagnosed|diagnosis|says?|said|states?|stated|mentions?|mentioned|shows?|showed|"
    r"records?|recorded|documents?|documented|lists?|listed|notes?|noted|has|have|had|is|was|are|were)\b|"
    r"진단|확인|이라고|라고",
    re.I,
)
HISTORICAL_CUE = re.compile(
    r"\b(?:in (?:19|20)\d\d|(?:19|20)\d\d|years? ago|months? ago|previously|in the past|used to|history of|"
    r"past history|as a (?:child|kid|teenager)|grew out of|resolved|prior)\b|"
    r"과거|예전|전에|\d+\s*년\s*전|어릴 ?때|완치",
    re.I,
)
CURRENT_CUE = re.compile(r"\b(?:current|currently|now|today|ongoing|active|new|recent|recently)\b|지금|현재|요즘|최근", re.I)
FAMILY_CUE = re.compile(
    r"\b(?:mother|father|mum|mom|dad|brother|sister|son|daughter|aunt|uncle|grand(?:mother|father|ma|pa)|cousin|"
    r"wife|husband|parents?|siblings?|family)\b|어머니|아버지|엄마|아빠|누나|언니|오빠|동생|가족|할머니|할아버지|부모님|남편|아내",
    re.I,
)
OTHER_PERSON_CUE = re.compile(r"\b(?:friend|colleague|neighbou?r|co-?worker|roommate)\b|친구|동료|이웃", re.I)
FIRST_PERSON_CUE = re.compile(r"\b(?:I|I'm|I've|me|my|myself)\b|제가|저는|저도|저를|내가|나는|제\s", re.I)
SPECULATION_CUE = re.compile(
    r"\b(?:I think|I guess|I wonder|I suspect|I'm worried|I am worried|I'm afraid|I read|internet|online|google\w*)\b|"
    r"추측|인터넷|검색|걱정",
    re.I,
)
