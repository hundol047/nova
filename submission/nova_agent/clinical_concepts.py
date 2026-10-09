"""Clinical concept normalisation: free-text wording -> the canonical phrase the knowledge base uses.

Why: the knowledge base names each finding once ("neck stiffness", "missed period", "melena"), while patients
and examiners use many forms ("nuchal rigidity", "my neck feels locked up", "period is two weeks late",
"black tarry stool"). Literal per-phrase aliases cannot express "period ... late", so these are bounded
patterns, one CONCEPT each. A match appends the canonical phrase to the evidence bag; the patient's own text is
kept unchanged next to it.

Discipline:
  * One pattern -> one concept. Distinct concepts are never merged (dysarthria "slurred speech" and aphasia
    "words come out jumbled" stay separate; melena and hematochezia stay separate).
  * Clause-level and negation-aware: the clause is first scrubbed with matching._strip_negated_spans, so
    "no neck stiffness" / "denies black stools" never produces the concept.
  * Current findings only: a clause marked as history ("history of", "years ago", "used to", "last year",
    "previously") does not produce a CURRENT-symptom concept.
  * No diagnosis is named here; scoring still decides with every other piece of evidence.
PROVENANCE: authored by the engineering agent from standard clinical vocabulary; NOT clinician-reviewed.
"""
from __future__ import annotations

import re
from typing import List, Tuple
from nova_agent.matching import POSTURAL_LIGHTHEADEDNESS

_HISTORY = re.compile(r"\b(?:history of|h/o|years? ago|used to|last year|previously|in the past|as a child|childhood)\b",
                      re.IGNORECASE)
_CLAUSE = re.compile(r"[;\n]|(?<=[a-z])\.(?=\s|$)|\bbut\b|\bhowever\b", re.IGNORECASE)

# (canonical KB phrase, pattern). Patterns are matched on lower-cased, negation-scrubbed clause text.
_CONCEPTS: List[Tuple[str, re.Pattern]] = [(c, re.compile(p)) for c, p in (
    # meningeal irritation
    ("neck stiffness", r"\bnuchal rigidity\b|\bmeningism(?:us)?\b|\bbrudzinski\b|\bkernig\b|"
                       r"\bneck (?:feels? |is |has gone )?(?:locked(?: up)?|rigid|stiff)\b|"
                       r"\b(?:can'?t|cannot|unable to) (?:bend|flex|move|turn) (?:my |his |her )?neck\b"),
    ("photophobia", r"\b(?:can'?t|cannot) (?:stand|tolerate|bear|handle) (?:the |any )?(?:bright )?lights?\b|"
                    r"\blights? (?:\w+ )?(?:hurts?|bothers?|is (?:painful|unbearable))\b|\b(?:avoids?|avoiding) (?:the )?light\b|"
                    r"\bwants? (?:the )?(?:room|lights?) (?:dark|off)\b"),
    ("CSF pleocytosis", r"\b(?:cloudy|turbid|purulent)\s+(?:csf|cerebrospinal fluid|spinal fluid)\b|"
                        r"\b(?:csf|cerebrospinal fluid|spinal fluid)\s+(?:is |was |looks? |appears? )?(?:cloudy|turbid|purulent)\b|"
                        r"\b(?:csf|cerebrospinal fluid|spinal fluid)\b[^.;]{0,40}\b(?:elevated|high|raised|increased|markedly)\b"
                        r"[^.;]{0,20}\b(?:white|wbc|leuko|neutrophil|cell count)|"
                        r"\b(?:csf|cerebrospinal fluid)\b[^.;]{0,30}\bwbc\s*(?:of\s*)?\d{3,}"),
    # early pregnancy / gynaecological bleeding
    ("missed period", r"\bperiod (?:is |was |'s )?(?:\w+ ){0,3}(?:late|overdue)\b|\blate period\b|"
                      r"\bmissed (?:my |a |her )?(?:last )?period\b|\b(?:haven'?t|hasn'?t|have not|has not) had (?:my|a|her) period\b|"
                      r"\bno period (?:for|since)\b|\blast (?:menstrual )?period\b[^.;]{0,20}\b(?:\d+|two|three|four|five|six|seven|eight|several) "
                      r"(?:weeks?|months?) ago\b"),
    ("vaginal bleeding", r"\bspotting\b|\bvaginal(?:ly)? bleed\w*|\bbleeding from (?:the |my |her )?vagina\b|"
                         r"\bbleeding (?:down there|down below)\b"),
    # gastrointestinal bleeding (kept as three separate concepts)
    ("melena", r"\b(?:black|tarry|tar-like)\b[^.;]{0,15}\b(?:stools?|poo|poop|bowel movements?|motions?|faeces|feces)\b|"
               r"\b(?:stools?|poo|poop|bowel movements?)\b[^.;]{0,15}\b(?:black|tarry|like tar)\b"),
    ("hematochezia", r"\bmaroon\b[^.;]{0,15}\b(?:stools?|poo|poop|bowel movements?)\b|"
                     r"\b(?:stools?|poo|poop|bowel movements?)\b[^.;]{0,15}\bmaroon\b|"
                     r"\bblood (?:in|with|on) (?:my |the |his |her )?(?:stools?|poo|poop|bowel movements?|toilet paper)\b|"
                     r"\bbright red blood (?:per rectum|from (?:my |the )?(?:bottom|rectum|back passage))\b|\bbloody (?:stools?|diarrh\w+)\b"),
    ("hematemesis", r"\b(?:vomit\w*|threw up|throwing up|puk\w*)\b[^.;]{0,25}\b(?:blood|coffee[- ]grounds?)\b|"
                    r"\bcoffee[- ]ground\w*\b"),
    # focal neurological deficit (aphasia and dysarthria stay distinct)
    ("aphasia", r"\bwords? (?:come|came|coming) out (?:jumbled|wrong|mixed up|garbled)\b|"
                r"\b(?:can'?t|cannot|unable to|struggl\w+ to|trouble) (?:find|finding|get|getting) (?:the |my |his |her )?words\b|"
                r"\bexpressive aphasia\b|\breceptive aphasia\b|\bword[- ]finding difficult\w*"),
    ("slurred speech", r"\bspeech (?:is |was |sounds? )?(?:slurred|thick|garbled)\b|\bslurring (?:my |his |her )?words\b|"
                       r"\btalking (?:funny|like (?:i'?m|he'?s|she'?s) drunk)\b"),
    ("facial droop", r"\b(?:face|mouth|smile)\b[^.;]{0,25}\b(?:droop\w*|lopsided|crooked|uneven|sagging)\b|"
                     r"\b(?:droop\w*|lopsided|crooked)\b[^.;]{0,10}\b(?:face|mouth|smile)\b|\bfacial (?:droop|weakness|palsy)\b"),
    # syncope / orthostasis wording
    ("lightheadedness on standing up", POSTURAL_LIGHTHEADEDNESS.pattern),
    ("prodrome of lightheadedness", r"\b(?:everything|vision|eyes?|world)\b[^.;]{0,15}\b(?:went|going|turned|goes) "
                                    r"(?:gr[ae]y|dark|black|white|fuzzy|dim)\b|\btunnel vision\b|\bgr[ae]ying out\b|"
                                    r"\bfelt (?:faint|lightheaded|light-headed|woozy|clammy)\b[^.;]{0,25}\b(?:before|first|then)\b"),
    ("rapid spontaneous recovery", r"\b(?:came|come|coming) (?:a)?round\b[^.;]{0,25}\b(?:seconds?|straight away|right away|"
                                   r"immediately|quickly)\b|\b(?:woke|wake|waking) up\b[^.;]{0,15}\b(?:right away|immediately|"
                                   r"straight away|within seconds|quickly)\b|\brecovered (?:quickly|fully within)\b"),
    # urinary wording
    ("dysuria", r"\b(?:pee|peeing|urinat\w*|wee|weeing|bathroom|toilet)\b[^.;]{0,25}\b(?:stings?|stinging|burns?|burning|hurts?)\b|"
                r"\b(?:stings?|stinging|burns?|burning|hurts?)\b[^.;]{0,15}\b(?:to|when (?:i|you)|while (?:i|you)) "
                r"(?:pee|wee|urinate)\b"),
    ("urinary frequency", r"\b(?:going to the (?:bathroom|toilet|loo)|peeing|urinating|weeing|need(?:ing)? to (?:pee|go))\b"
                          r"[^.;]{0,15}\b(?:constantly|all the time|every \w+ minutes|frequently|nonstop|a lot|so often)\b"),
    # breathlessness (everyday wording -> the KB's symptom phrase)
    ("shortness of breath", r"\b(?:can'?t|cannot|couldn'?t) (?:catch|get) (?:my |his |her )?breath\b|\bwinded\b|\bpuffed(?: out)?\b|"
                            r"\b(?:struggling|fighting|gasping) (?:to breathe|for (?:air|breath))\b|\b(?:can|could) (?:hardly|barely) breathe\b|"
                            r"\bhard to breathe\b|\bair hunger\b"),
)]


# Round O (NOVA_CONCEPTS_V2): chest-wall / musculoskeletal wording. Kept separate so the switch can turn it off.
_ACTION = r"(?:twist\w*|turn\w*|mov(?:e|es|ed|ing|ement)\b(?! (?:my|his|her|the) bowels?)|bend\w*|lift\w*|reach\w*|stretch\w*|rotat\w*|rais\w* my arms?)"
_CONCEPTS_V2: List[Tuple[str, re.Pattern]] = [(c, re.compile(p)) for c, p in (
    ("reproducible with palpation",
     r"\b(?:hurts?|sore|tender|aches?|pain\w*|worse)\b[^.;]{0,25}\b(?:press(?:ed|es|ing)?|push(?:ed|es|ing)?|touch(?:ed|es|ing)?|"
     r"prod\w*|palpat\w*)\b|\bpress(?:ing)? on (?:it|the (?:spot|area)|my (?:chest|ribs?|breastbone|sternum))\b|"
     r"\btender to (?:the )?touch\b|\breproduc\w+ (?:on|with|by) (?:palpation|pressure|pressing)\b"),
    ("localized tenderness",
     r"\b(?:one|a|single) (?:sore |tender |painful )?spot\b|\bpoint to (?:it|the pain|where it hurts)\b|"
     r"\btender (?:spot|point|area)\b|\bpoint tenderness\b|\blocali[sz]ed tenderness\b|\btender (?:at|over) the (?:rib|costochondral)"),
    ("pleuritic chest pain",
     r"\b(?:pain\w*|hurts?|stab\w*|sharp|catch(?:es)?|stitch|twinge)\b[^.;]{0,40}\b(?:when|whenever|every time|each time|as) "
     r"(?:i |you |he |she )?(?:breathe|take a (?:deep |big )?breath|inhale|cough)|"
     r"\b(?:breathing in|deep breaths?|inhaling)\b[^.;]{0,15}\b(?:hurts?|is painful|makes it worse|stabs?)\b"),
    ("filling defect in the pulmonary artery",
     r"\bpulmonary (?:arter(?:y|ies) )?(?:embol\w*|thromb\w*|clots?)\b|\bsaddle embol\w*|"
     r"\bembol\w*\b[^.;]{0,30}\bpulmonary arter(?:y|ies)\b|\bfilling defects?\b[^.;]{0,40}\bpulmonary arter(?:y|ies)\b"),
    ("worse with movement",
     r"\b(?:worse|hurts?|sore|sharper|aggravated|pain\w*)\b[^.;]{0,20}\b(?:with|when(?: i| you)?|on|if i) " + _ACTION + r"|"
     r"\b" + _ACTION + r"\b[^.;]{0,20}\b(?:makes? it worse|brings? it on|hurts?|sets? it off)\b|"
     r"\bworse with (?:movement|moving|activity)\b"),
)]


# Round P (NOVA_EVIDENCE_V3): medication class, generalised weakness and rhythm wording.
_STOPPED_DRUG = re.compile(r"\b(?:stopped|ran out|run out|quit|no longer|discontinued|came off|come off|off (?:my|the|his|her))\b")
_CONCEPTS_V3: List[Tuple[str, re.Pattern]] = [(c, re.compile(p)) for c, p in (
    # NICE CG150 table 1: bilateral + pressing/tightening. Require both
    # descriptors and a head site in one asserted clause; headache alone is not it.
    ("bilateral band-like pressure",
     r"(?=.*\b(?:headache|head|temples?)\b)(?=.*\b(?:bilateral|both (?:sides|temples))\b)"
     r"(?=.*\b(?:pressing|pressure|tight(?:ening)?|band[- ]like)\b).+"),
    ("diuretic use",
     r"\b(?:diuretics?|water (?:tablets?|pills?)|thiazides?|furosemide|frusemide|bumetanide|torsemide|bendroflumethiazide|"
     r"hydrochlorothiazide|indapamide|chlortalidone|chlorthalidone|spironolactone|lasix)\b"),
    ("generalized weakness",
     r"\b(?:generally|all over|whole body|everywhere)\b[^.;]{0,10}\bweak\w*|\bweak(?:ness)? (?:all over|everywhere)\b|"
     r"\b(?:feel|feels|felt|feeling)(?: so| very| really)? weak\b|\bno strength\b"),
    ("irregular heartbeat",
     r"\b(?:hr|pulse|heart rate|rhythm|heartbeat)\b[^.;]{0,15}\birregular(?!ly)\b|\birregular "
     r"(?:rhythm|pulse|heartbeat|heart ?beat|heart rate|beats?)\b|\bdropped beats\b|\bheart\b[^.;]{0,25}\bskipping\b|\bskipped (?:a )?beats?\b"),
    ("racing heart", r"\b(?:racing|pounding|fast(?:er)?|rapid|quick(?:er)?) heart ?beats?\b|"
                     r"\bheart(?:beat)? (?:is |was |keeps )?(?:racing|pounding|beating (?:fast|quickly)|going (?:fast|quickly))\b"),
    ("irregularly irregular rhythm", r"\birregularly irregular\b"),
    ("fatigue", r"\b(?:washed out|wiped out|worn out|exhausted|drained of energy|no energy)\b"),
    # Round Q: an instantaneous onset described in lay words IS the KB phrase "sudden onset severe headache"
    # ("came on in a second", "like being hit with a bat"). The headache word must be in the same clause.
    ("sudden onset severe headache",
     r"\b(?:headache|head pain|head ache)\b[^.;]{0,60}\b(?:in a second|in seconds|within seconds|instantly|all at once|"
     r"like (?:being )?hit|thunderclap)\b|\b(?:in a second|within seconds|instantly|all at once|like (?:being )?hit|"
     r"thunderclap)\b[^.;]{0,60}\b(?:headache|head pain|head ache)\b"),
)]
_DRUG_CONCEPTS = {"diuretic use"}


def _current_positive_clauses(text: str) -> List[str]:
    from nova_agent.matching import _strip_negated_spans
    out = []
    for clause in _CLAUSE.split(text or ""):
        if not clause or not clause.strip() or _HISTORY.search(clause):
            continue
        positive = _strip_negated_spans(clause.lower())
        if positive.strip(" ;"):
            out.append(positive)
    return out


_BP = r"(?:bp\s*)?(\d{2,3})\s*/\s*(\d{2,3})"
_POSTURE = {"lying": r"(?:lying(?: down)?|supine|recumbent)", "standing": r"(?:standing|upright|on standing)"}


def _posture_bp(text: str, posture: str):
    """(systolic, diastolic) labelled with a posture; "<posture> ... 120/80" is preferred over "120/80 <posture>"."""
    word = _POSTURE[posture]
    for pattern in (r"\b" + word + r"\b[^.;,\d]{0,15}" + _BP, _BP + r"[^.;,\d]{0,6}\b" + word + r"\b"):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1)), int(match.group(2))
    return None


def orthostatic_drop(text: str) -> bool:
    """Lying vs standing blood pressure in one report with a systolic fall >= 20 or diastolic fall >= 10 mmHg
    (the standard consensus definition of orthostatic hypotension)."""
    lying, standing = _posture_bp(text or "", "lying"), _posture_bp(text or "", "standing")
    if not lying or not standing or lying == standing:
        return False
    return lying[0] - standing[0] >= 20 or lying[1] - standing[1] >= 10


def canonical_findings_for(text: str) -> List[str]:
    """Canonical KB phrases asserted (current, not negated) by ``text``; empty when nothing matches."""
    if not text or len(text) < 4:
        return []
    found: List[str] = []
    from nova_agent.config import get_config
    if get_config().evidence_v2_enabled and orthostatic_drop(text):
        found.append("orthostatic drop in blood pressure")
    patterns = (_CONCEPTS + (_CONCEPTS_V2 if get_config().concepts_v2_enabled else [])
                + (_CONCEPTS_V3 if get_config().evidence_v3_enabled else []))
    for clause in _current_positive_clauses(text):
        for canonical, pattern in patterns:
            if canonical == "filling defect in the pulmonary artery" and re.search(
                    r"\b(?:artifact|artefact|mixing|motion|equivocal|indeterminate|limited|poor|aort\w*|vein|venous|bronch\w*)\b", clause):
                continue
            if canonical in _DRUG_CONCEPTS and _STOPPED_DRUG.search(clause):
                continue  # a drug the patient stopped is not current use
            if canonical == "irregular heartbeat" and "irregularly irregular" in clause:
                continue  # one observation, one concept: the specific rhythm finding already represents it
            if canonical not in found and pattern.search(clause):
                found.append(canonical)
    return found


def procedure_context_findings(procedure: str, result: str) -> List[str]:
    """Use an actually observed study's compartment, never a planned study.

    ESC/ERS 2019 PE guideline and 2025 CTA consensus (Round S provenance).
    A definite lobar/segmental filling defect on pulmonary CTA can omit the
    repeated words 'pulmonary artery'. Other compartments and technical or
    uncertain findings must not supply that omitted anatomical context.
    """
    if procedure != "ct_chest_angio":
        return []
    for clause in _current_positive_clauses(result):
        if re.search(r"\b(?:artifact|artefact|mixing|motion|equivocal|indeterminate|limited|poor|aort\w*|vein|venous|bronch\w*)\b", clause):
            continue
        if (re.search(r"\bfilling defects?\b", clause)
                and re.search(r"\b(?:segmental|lobar|main pulmonary|pulmonary arter\w*)\b", clause)):
            return ["filling defect in the pulmonary artery"]
    return []


# Round P (NOVA_RANKING_V3): a specific objective rhythm/finding phrase already represents the general symptom phrase
# for the same physiology. When a disease lists both and the specific one is present in the objective record, the
# general one is the same observation and must not earn a second piece of credit.
SPECIFIC_SUBSUMES = {
    "irregularly irregular rhythm": ("irregular heartbeat",),
}


# Round P (NOVA_ACTION_V3): findings only an examiner or a laboratory can establish. Asking the patient "Any ejection
# systolic murmur?" or "Any low sodium?" wastes a turn and invites a guessed answer; these features are reached by
# EXAM (when the bedside can show them) or not at all in a test-free encounter.
_OBJECTIVE_ONLY_FEATURE = re.compile(
    r"\b(?:murmur|bruit|crackles|rales|rhonchi|nystagmus|papill?oedema|papilledema|reflex\w*|sign|tenderness|rebound|"
    r"guarding|rigidity|sodium|potassium|calcium|magnesium|phosphate|creatinine|h(?:a)?emoglobin|platelets?|troponin|"
    r"d-?dimer|ecg|ekg|ct|mri|x-?ray|ultrasound|imaging|echocardiogram|biopsy|culture|levels?|count|"
    r"hypo(?:natr|kal|calc|magnes)a?emia|hyper(?:natr|kal|calc|magnes)a?emia|leukocytosis|elevated|"
    r"(?:systolic|diastolic) (?:pressure|murmur)|on (?:examination|exam|auscultation|palpation))\b")


def is_objective_only_feature(feature: str) -> bool:
    """True for a finding the patient cannot report from experience (exam signs, lab values, imaging).

    A disjunction is askable when any part is ("calf pain or tenderness": the pain is the patient's to report)."""
    if not feature:
        return False
    parts = [p for p in re.split(r"\s+or\s+", feature.lower()) if p.strip()]
    return bool(parts) and all(_OBJECTIVE_ONLY_FEATURE.search(p) for p in parts)


def bedside_exam_for_feature(feature: str):
    """Only mappings covered by existing EXAM maneuvers; lab/imaging findings stay unavailable.
    Reuses taxonomy's cardiac/lung auscultation scope, not a generated test request."""
    low = feature.lower()
    if re.search(r"\bmurmur\b", low):
        return "cardiac_auscultation"
    if re.search(r"\b(?:crackles|rales|rhonchi)\b", low):
        return "lung_auscultation"
    return None
