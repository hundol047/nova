"""Conservative interview coverage, separate from diagnostic assertion polarity.

An explicit denial answers a question; an uncertain, family-only or merely
attempted response does not. Original observations remain untouched in state.
No diagnosis, disease score, or patient identifier is used here.
"""
import re

from nova_agent.state import answer_kind, _ANSWER_UNKNOWN
from nova_agent.evidence_scope import patient_evidence_text
from nova_agent.clinical_assertions import normalize_exam_notation

_CLAUSES = re.compile(r'[;\n]|(?<!\d)\.(?!\d)|\bbut\b|하지만|그러나', re.I)
_SEDATIVE_NAME = re.compile(r'zolpidem|zopiclone|eszopiclone|diazepam|lorazepam|alprazolam|clonazepam|temazepam|triazolam|졸피뎀|조피클론|로라제팜|알프라졸람|클로나제팜|디아제팜', re.I)
_SEDATIVE = re.compile(_SEDATIVE_NAME.pattern + r'|sedative|sleeping (?:pill|medication)|수면제|진정제|benzodiazep', re.I)
_UNCERTAIN = re.compile(_ANSWER_UNKNOWN.pattern + r'|unknown|uncertain|미확인|확인되지|알지 못|기억.*않', re.I)
_FAMILY_TOPICS = {'parent_height', 'parent_puberty', 'family_illness'}
_LONGITUDINAL_TOPICS = {'growth_records', 'growth_velocity', 'birth', 'medical_history', 'surgery', 'prior_care'}
_QUANTITATIVE = {'medication_dose', 'medication_frequency', 'medication_duration', 'medication_tablets', 'medication_night_extra', 'growth_records', 'growth_velocity', 'parent_height', 'birth'}


def topic_attempted(state, topic):
    from nova_agent.clinical_interview import topic_for_question
    return any(t.action_type == 'ASK' and topic_for_question(t.content) == topic
               for t in state.performed_actions)


def _pieces(text, topic):
    text = normalize_exam_notation(text or '')
    if topic.startswith('medication_'):
        text = text.replace(',', ';')
    for clause in _CLAUSES.split(text):
        if _UNCERTAIN.search(clause):
            continue
        scoped = clause if topic in _FAMILY_TOPICS else patient_evidence_text(clause, allow_historical=topic in _LONGITUDINAL_TOPICS)
        if scoped.strip():
            yield scoped.strip()


def topic_answered(state, topic, pattern):
    from nova_agent.clinical_interview import topic_for_question
    from nova_agent.clinical_profiles import growth_velocity
    pieces = list(_pieces(state.chief_complaint, topic))
    for t in state.performed_actions:
        if t.action_type not in {'ASK', 'EXAM'}:
            continue
        result = t.result or ''
        direct = t.action_type == 'ASK' and topic_for_question(t.content) == topic
        usable = list(_pieces(result, topic))
        if direct and usable:
            # Short answers inherit the question's topic, never its suggested
            # finding. Quantities still require actual quantitative content.
            kind = answer_kind(result)
            from nova_agent.clinical_interview import DETAIL_QUESTIONS, needs_history_detail
            if topic in DETAIL_QUESTIONS and needs_history_detail(result):
                continue
            if topic not in _QUANTITATIVE | {'symptom_onset'} and kind in {'yes', 'no'}:
                return True
            # A named, direct history answer need not repeat the question's
            # vocabulary (e.g. '고혈압', '충수절제술', '아버지가 당뇨예요').
            # This is coverage only, never a diagnostic feature assertion.
            if topic in {'medical_history', 'surgery', 'family_illness', 'prior_care', 'function'} and kind is None:
                return True
            if topic == 'medication_name' and kind is None:
                # A direct named medication reply need not be a sedative. Keep
                # vague positive screens unresolved for one clarification.
                vague = re.fullmatch(r'\s*(?:약|약을|약은|수면제|혈압약|당뇨약)(?:만)?(?:\s*(?:먹어요|먹고 있어요|복용해요|복용 중이에요))?[.!\s]*', result)
                if not vague and not re.search(r'이름.*(?:모르|기억.*않)|name.*(?:unknown|remember)', result, re.I):
                    return True
            if topic in _QUANTITATIVE - {'parent_height','growth_velocity','growth_records'} and re.search(pattern, ' '.join(usable), re.I):
                return True
        pieces.extend(usable)
    if topic == 'growth_velocity':
        if growth_velocity('; '.join(pieces)) is not None:
            return True
        # An actual numeric answer to the explicit one-year question inherits
        # that interval, matching profile_observations' existing contract.
        return any(t.action_type == 'ASK' and topic_for_question(t.content) == topic
                   and re.fullmatch(r'\s*\d+(?:\.\d+)?\s*cm(?:\s*(?:자랐어요|컸어요|grew))?[.!\s]*', t.result or '', re.I)
                   for t in state.performed_actions)
    if topic == 'weight_change' and any(weight_trajectory(p) for p in pieces):
        return True
    if topic == 'parent_height':
        raw = '; '.join(pieces)
        return all(re.search(rf'(?:{parent})[^;\n]{{0,20}}\d+(?:\.\d+)?\s*(?:cm|센티)', raw, re.I)
                   for parent in ('father|아버지|아빠', 'mother|어머니|엄마'))
    if topic.startswith('medication_'):
        # Medication quantities are attached to the drug in the same clause.
        # An unrelated antihypertensive dose cannot answer a sleeping-pill dose.
        sleep_context = bool(re.search(r'불면|수면|sleep|insomnia', state.chief_complaint, re.I))
        if topic == 'medication_name':
            named = any(_SEDATIVE_NAME.search(p) for p in pieces)
            denial = any(re.search(r'(?:no|not taking)\s+(?:any\s+)?(?:medic(?:ation|ine)s?\b|drugs|sleeping pills)|(?:먹는|복용(?:하는|중인)?)\s*약.*없|(?:약은|약을|수면제).*(?:안.*먹|복용하지 않)', p, re.I) for p in pieces)
            if named or denial:
                return True
            if sleep_context:
                return False
        elif sleep_context:
            return any(_SEDATIVE.search(p) and re.search(pattern, p, re.I) for p in pieces)
    return any(re.search(pattern, p, re.I) for p in pieces)


def weight_trajectory(text):
    """Explicit same-unit trajectory only; no guessed dates, units or weights."""
    from decimal import Decimal
    from nova_agent.korean_numbers import normalize_spoken_numbers
    current = patient_evidence_text(normalize_spoken_numbers(text), allow_historical=False)
    match = re.search(r'(\d+(?:\.\d+)?)\s*kg\s*(?:에서|to|→)\s*(\d+(?:\.\d+)?)\s*kg', current, re.I)
    if not match:
        return None
    before, after = Decimal(match[1]), Decimal(match[2])
    if before <= 0 or after <= 0:
        return None
    interval = re.search(r'(\d+(?:\.\d+)?)\s*(개월|달|주|일|months?|weeks?|days?)', current, re.I)
    return {'previous_weight_kg':float(before), 'current_weight_kg':float(after),
            'weight_change_kg':float(after-before), 'time_window':interval[0] if interval else None,
            'source':match[0], 'derived_fields':['weight_change_kg']}


def exam_topic(text):
    """Only equivalent, single physical maneuvers; no broad body-system dedup."""
    for key, anatomy, maneuver in (
        ('thyroid_exam', r'갑상[선샘]|thyroid', r'촉진|palpat'),
        ('thyroid_eye', r'안구|눈|eye', r'돌출|proptosis'),
        ('growth_height', r'신장|키|height', r'측정|measur'),
        ('growth_weight', r'체중|weight', r'측정|measur'),
        ('growth_proportions', r'상하체|상절|하절|body proportion', r'측정|measur'),
        ('mental_status_exam', r'지남력|orientation', r'확인|평가|assess'),
        ('thyroid_tremor', r'양손|hands?', r'뻗|outstretch'),
        ('lung_auscultation', r'폐|호흡음|lung|chest', r'청진|auscult'),
        ('cardiac_auscultation', r'심장|심음|heart|cardiac', r'청진|auscult'),
    ):
        if re.search(anatomy, text, re.I) and re.search(maneuver, text, re.I):
            return key
    return None


def exam_attempted(state, text):
    key = exam_topic(text)
    return bool(key and (key in state.rejected_exams or state.exam_done(key) or any(
        exam_topic(t.content) == key for t in state.performed_actions if t.action_type == 'EXAM')))
