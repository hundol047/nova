"""Small, auditable concept and procedure-aware evidence interpreter.

These are internally authored language-normalization heuristics, not a trained model,
clinical guideline or benchmark answer lookup. They only turn observed text into KB
features, with explicit polarity and provenance. Missing information stays unknown.
"""
from __future__ import annotations
import re
from nova_agent.language import normalize_clinical_text
from functools import lru_cache

# Generic concept variants, scoped to a single KB feature. No global text replacement.
ALIASES = {
 'tracheal deviation': [r'\btrachea\b.{0,18}\b(?:shift\w*|deviat\w*)\b'],
 'bilateral band-like pressure': [r'\b(?:tight|squeez\w*)\b.{0,20}\bband\b',r'\bband[- ]like\b.{0,15}\b(?:headache|pressure)\b'],
 'known asthma or COPD': [r'\b(?:history of asthma|asthma since|known asthma|known copd|history of copd)\b'],
 'right lower quadrant tenderness': [r'\bmcburney.{0,15}point\b', r'\b(?:right lower|lower right|rlq)\b.{0,25}\btender'],
 'rigid abdomen': [r'\bboard[- ](?:hard|like|rigid)\b', r'\b(?:abdomen|belly|stomach)\b.{0,20}\b(?:rigid|hard)\b'],
 'palpitations': [r'\bheart\b.{0,20}\b(?:pound|rac)\w*'],
 'tingling around the mouth or fingers': [r'\b(?:tingl\w*|paresthesia)\b.{0,25}\b(?:fingers?|mouth|hands?)\b'],
 'altered mental status': [r'\b(?:confused|confusion|disoriented|unresponsive)\b'],
 'fear of dying or losing control': [r'\b(?:impending doom|fear of death|afraid of dying)\b'],
 'chest tightness': [r'\bchest\b.{0,12}\btight\b'],
 'symptoms peak within minutes then improve': [r'\bpeak\w*\b.{0,30}\b(?:ease\w*|improv\w*|subsid\w*)\b'],
 'diarrhea': [r'\b(?:loose|watery) stools?\b'],
 'diffuse crampy abdominal pain': [r'\b(?:stomach|abdominal|belly) cramps?\b', r'\bcramp(?:s|y|ing)\b'],
 'recent similar illness contact': [r'\b(?:others?|contacts?|guests?|family)\b.{0,50}\b(?:ill|sick|stomach|vomit|diarrh)', r'\b(?:food poisoning|shared meal)\b'],
 'neck stiffness': [r'\bstiff(?:ness)?\b.{0,15}\bneck\b',r'\bnuchal rigidity\b'],
 'photophobia': [r'\blight\b.{0,15}\b(?:hurt|bother|sensitiv)',r'\bsensitiv\w*\s+to\s+(?:the\s+)?light'],
 'slurred speech': [r'\b(?:dysarthria|aphasia)\b',r'\b(?:word[- ]finding|speech)\s+(?:difficulty|trouble|problem)',r'\b(?:trouble|difficulty)\b.{0,12}\b(?:speaking|words)\b'],
 'unilateral absent breath sounds': [r'\b(?:absent|no)\s+(?:\w+\s+){0,2}breath sounds?\b.{0,30}\b(?:left|right|one side)\b'],
 'absent breath sounds': [r'\b(?:absent|no)\s+(?:\w+\s+){0,2}breath sounds?\b'],
 'productive cough': [r'\b(?:sputum|phlegm|mucus)\b'],
 'recent viral illness': [r'\b(?:recent|after|following)\b.{0,25}\b(?:cold|viral|uri)\b',r'\bcold\b.{0,25}\b(?:resolved|cleared|subsided)\b'],
 'chest wall soreness from coughing': [r'\b(?:chest|ribs?)\b.{0,20}\b(?:sore|hurt)\b.{0,20}\bcough'],
 'rhinorrhea': [r'\b(?:runny|stuffy|congested) nose\b',r'\bnasal congestion\b'],
 'sudden onset urticaria': [r'\b(?:hives|urticaria)\b'],
 'facial swelling': [r'\b(?:swollen|swelling)\b.{0,18}\b(?:lips?|tongue|face)\b',r'\b(?:lips?|tongue|face)\b.{0,18}\b(?:swollen|swelling)\b'],
 'throat tightness': [r'\bthroat\b.{0,15}\b(?:tight|clos)',r'\bstridor\b'],
 'recent allergen exposure': [r'\b(?:bee|wasp|insect)\s+sting\b',r'\b(?:stung|allergen exposure)\b'],
 'periumbilical pain migrating to right lower quadrant': [r'\b(?:umbilic\w*|navel|belly button)\b.{0,100}\b(?:right lower|lower right|rlq)\b',r'\b(?:pain|ache)\b.{0,40}\b(?:migrat\w*|mov\w*)\b.{0,40}\b(?:right lower|lower right|rlq)\b'],
 'anorexia': [r'\b(?:loss of appetite|no appetite|not hungry|poor appetite)\b', r'\blost\b.{0,10}\bappetite\b'],
 'lower abdominal pain': [r'\b(?:lower belly|lower abdomen|lower abdominal|pelvic)\b'],
 'unilateral pelvic pain': [r'\b(?:one[- ]sided|unilateral)\b.{0,20}\b(?:pelvic|lower abdominal)\b'],
 'missed period': [r'\b(?:late|missed|overdue)\s+(?:menstrual\s+)?period\b',r'\bperiod\b.{0,12}\b(?:late|overdue)\b',r'\bamenorrh'],
 'vaginal bleeding': [r'\b(?:vaginal spotting|spotting)\b'],
 'melena': [r'\b(?:black|tarry|dark)\s+stools?\b'],
 'hematochezia': [r'\b(?:maroon|bloody) stools?\b',r'\bblood in (?:the )?stool\b'],
 'hematemesis': [r'\b(?:vomit\w*|throw\w* up)\s+blood\b',r'\bcoffee[- ]ground'],
 'pallor': [r'\bpale\b'],
 'lightheadedness': [r'\blight[- ]headed\w*\b'],
 'sudden onset intense anxiety or fear': [r'\b(?:panic|panicking|terrified|intense fear|very anxious)\b'],
 'hyperventilation': [r'\b(?:hyperventilat\w*|breathing (?:too )?fast)\b'],
 'resolves with calming down or reassurance': [r'\b(?:improv\w*|settled|eased)\b.{0,35}\b(?:calm|reassur)',r'\bcalm\w*\b.{0,35}\b(?:improv\w*|settled|eased)\b'],
 'triggered by standing or pain or fear': [r'\b(?:prolonged standing|standing (?:still|for)|stood for)\b', r'\bstanding\b.{0,60}\blong\b',r'\b(?:sight of blood|blood draw)\b'],
 'brief loss of consciousness': [r'\b(?:fainted|passed out|blacked out)\b'],
 'rapid spontaneous recovery': [r'\b(?:recovered|awoke|awake|woke up|came around)\b.{0,30}\b(?:quickly|seconds|promptly)\b',r'\b(?:quickly|immediately)\b.{0,20}\b(?:recovered|awake|alert)\b'],
 'brief episodic vertigo': [r'\b(?:spinning|vertigo)\b.{0,30}\bseconds\b',r'\bbrief\b.{0,20}\bspinning\b'],
 'triggered by head position change': [r'\b(?:turn\w*|roll\w*)\b.{0,20}\b(?:head|bed)\b',r'\bpositional vertigo\b'],
 'lightheadedness on standing up': [r'\b(?:dizz\w*|light[- ]headed\w*)\b.{0,50}\b(?:stand\w*|getting up|rising)\b'],
 'improves with sitting or lying down': [r'\b(?:improv\w*|resolv\w*|better)\b.{0,30}\bseated\b', r'\b(?:better|improv\w*|resolv\w*|ease\w*)\b.{0,30}\b(?:sitting|lying|sit|lie)\b'],
 'fruity breath odor': [r'\b(?:fruity|acetone|sweet)\b.{0,15}\bbreath\b'],
 'kussmaul breathing': [r'\b(?:deep|labou?red)\b.{0,15}\b(?:rapid|fast)\b.{0,15}\bbreath',r'\bkussmaul\b'],
 'polydipsia': [r'\b(?:thirsty|excessive thirst|increased thirst)\b'],
 'polyuria': [r'\b(?:frequent urination|urinating a lot|peeing a lot)\b'],
 'suspected infection source': [r'\b(?:purulent|infected|infection)\b'],
}

# KB feature labels are case-insensitive (including acronym-bearing labels).
ALIASES = {key.lower(): value for key, value in ALIASES.items()}

@lru_cache(maxsize=4096)
def positive_clauses(text: str) -> list[str]:
    """Scope negation to clauses, including contractions; retain positive contrasts."""
    clauses = re.split(r'[;,]|(?<!\d)\.(?!\d)|\b(?:but|however|although)\b', text.lower())
    output=[]
    for part in clauses:
        # 'not only' is not negation; absent physiological findings are handled separately.
        part=re.sub(r'\bnot only\b', '', part)
        part=re.sub(r"\b(?:denies|denied|no|without|negative for|not present|not elevated|not(?!\s+hungry\b)|don.t have|doesn.t have|do not have|does not have)\b.*", '', part)
        if part.strip(): output.append(part.strip())
    return output


@lru_cache(maxsize=4096)
def asserted_clauses(text: str) -> tuple[str, ...]:
    """Retain stated observations, without upgrading possibilities to findings.

    This is a bounded text assertion filter. Tentative evidence remains in the
    original patient state and model summary but cannot act as confirmed support.
    Negations are retained for the caller to interpret; they are not positives.
    """
    parts = re.split(r'[;,]|(?<!\d)\.(?!\d)|\b(?:but|however|although)\b', text, flags=re.I)
    uncertain = re.compile(r'\b(?:possibl\w*|suspected|unconfirmed|inconclusive|pending|hypothetical|'
                           r'might|cannot exclude|cannot rule out|rule out|contaminat\w*)\b|\?|'
                           r'^\s*if\b|\b(?:may|could)\s+(?:be|have|represent|indicate)\b', re.I)
    return tuple(part.strip() for part in parts if part.strip() and not uncertain.search(part))


@lru_cache(maxsize=256)
def _patterns(feature: str):
    return [re.compile(pattern, re.I) for pattern in ALIASES.get(feature.lower(), [])]


def concept_present(feature: str, texts: list[str]) -> bool:
    feature = feature.lower()
    texts = [" ; ".join(asserted_clauses(text)) for text in texts]
    if feature == "periumbilical pain migrating to right lower quadrant":
        # Bind locations to an explicit temporal/migration description within one observation.
        for text in texts:
            positive = " ; ".join(positive_clauses(text))
            if (re.search(r"\b(?:start\w*|began|initially|migrat\w*|mov\w*)\b", positive)
                and re.search(r"\b(?:umbilic\w*|navel|belly button)\b.{0,180}\b(?:right lower|lower right|rlq)\b", positive)):
                return True
        return False
    if feature == "epigastric pain radiating to back":
        combined = " ; ".join(clause for text in texts for clause in positive_clauses(text))
        if re.search(r"\bepigastric\b", combined) and re.search(r"\b(?:radiat\w*|boring)\b.{0,40}\bback\b", combined):
            return True
    patterns=_patterns(feature)
    if not patterns:
        return False
    # 'absent breath sounds' is a positive pathological observation, not absence of disease.
    use_raw=feature in {'absent breath sounds','unilateral absent breath sounds'}
    for text in texts:
        for clause in ([text] if use_raw else positive_clauses(text)):
            if use_raw and re.search(r"\b(?:no|not|without|denies)\s+(?:any\s+)?(?:absent|absence)\b", clause, re.I):
                continue
            if any(p.search(clause) for p in patterns): return True
    return False


def objective_findings(entry: dict, state) -> list[str]:
    """Keep source compartments: CSF leukocytes are not blood or urine leukocytes."""
    results={**state.physical_examinations, **state.laboratory_tests, **state.imaging}
    results = {key: ' ; '.join(asserted_clauses(normalize_clinical_text(value))) for key,value in results.items()}
    allowed=set(entry.get('discriminating_exams',[])+entry.get('discriminating_tests',[]))
    out=[value for key,value in results.items() if key in allowed]
    # An explicit positive in a named test has semantics even if the value omits its name.
    labels={'beta_hcg':'positive beta-hCG', 'fecal_occult_blood':'positive fecal occult blood',
            'ketones':'large ketones'}
    for key,label in labels.items():
        value=results.get(key,'')
        positive_pattern = r'\blarge\b' if key == 'ketones' else r'\b(?:positive|strongly positive)\b'
        if key in allowed and re.search(positive_pattern,value,re.I) and not re.search(r'\b(?:not|negative|pending|trace)\b',value,re.I):
            out.append(label)
    # Preserve the named procedure when a result only describes its value.
    lipase=results.get('lipase','') if 'lipase' in allowed else ''
    if re.search(r'\b(?:elevated|raised|high|increased)\b',lipase,re.I) and not re.search(r'\b(?:not|no|normal|pending)\b',lipase,re.I):
        out.append('elevated lipase')
    csf=results.get('lumbar_puncture','') if 'lumbar_puncture' in allowed else ''
    if any(re.search(r'\b(?:elevated|increased|high)\b.{0,20}\b(?:white|wbc|leukocyte|cell)',clause,re.I) for clause in positive_clauses(csf)):
        out.append('CSF pleocytosis')
    return out


def current_symptom_findings(feature: str, texts: list[str]) -> list[str]:
    """Exclude explicitly resolved nasal symptoms from current-symptom evidence.

    The original observations stay in state and LLM history. Historical viral illness
    can still be a risk/trigger; this filter only applies to the current nasal feature.
    """
    if feature.lower() != "rhinorrhea":
        return texts
    return [clause for text in texts for clause in positive_clauses(text)
            if not re.search(r"\b(?:resolved|cleared(?: up)?|subsided|gone|used to)\b", clause)]


def infection_with_circulatory_and_mental_change(state) -> list[str]:
    """Conservative source-bound support, not SOFA or confirmed sepsis criteria.

    Requires infection-compatible objective evidence, actual recorded hypotension,
    and mental-status change together. None of these alone receives this support.
    Unknowns, pending cultures, and unrelated shock do not count as infection.
    """
    urine = state.laboratory_tests.get('urinalysis', '')
    culture = state.laboratory_tests.get('blood_culture', '')
    # Tentative, pending and contaminated interpretations are not objective support.
    if re.search(r'\b(?:pending|possible|contaminat\w*|hypothetical)\b', urine, re.I):
        urine = ''
    if re.search(r'\b(?:pending|possible|contaminat\w*|hypothetical)\b', culture, re.I):
        culture = ''
    infection = (any(re.search(r"\bpositive\s+" + marker + r"\b", clause)
                     for clause in positive_clauses(urine)
                     for marker in ['nitrites?', 'leukocyte esterase'])
                 or any(re.search(r"\b(?:positive|growth of|grew)\b", clause)
                        for clause in positive_clauses(culture)))
    low_pressure = bool(state.vital_signs and state.vital_signs[-1].sbp is not None
                        and state.vital_signs[-1].sbp < 90)
    mental = state.physical_examinations.get('mental_status_exam', '')
    changed = concept_present('altered mental status', [mental])
    if infection and low_pressure and changed:
        return ['infection-compatible specimen result with recorded hypotension and mental-status change']
    return []


def patient_symptom_findings(texts: list[str]) -> list[str]:
    """Family-member observations may be risk factors, not current patient symptoms."""
    return [" ; ".join(clause for clause in asserted_clauses(text)
            if not re.search(r"\b(?:mother|father|sister|brother|family history)\b|어머니|아버지|가족력",clause,re.I)) for text in texts]
