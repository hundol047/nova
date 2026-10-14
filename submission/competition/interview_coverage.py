"""Question-level coverage, without patient scripts, answer labels or diagnoses.

These original question templates are a fallback for an empty Doctor plan.
The model remains responsible for complaint-specific differential assessment.
A screen and its details are different questions; unknown is not normal.
"""
import re
from nova_agent.clinical_interview import TOPICS, topic_for_question, topic_known
from nova_agent.state import answer_kind


# key, question, record category. Each entry requests exactly one attribute.
EXTRA = [
    ('character', '증상이 어떤 느낌인지 설명해 주세요', 'character'),
    ('severity', '증상이 얼마나 심한가요?', 'severity'),
    ('location', '불편한 부위가 어디인가요?', 'location'),
    ('radiation', '통증이 다른 곳으로 퍼지나요?', 'location'),
    ('sudden_onset', '증상이 갑자기 시작됐나요?', 'onset'),
    ('daily_timing', '하루 중 언제 증상이 심한가요?', 'duration'),
    ('self_care', '증상을 줄이려고 해본 방법이 있나요?', 'relieving'),
    ('response_to_care', '그 방법으로 증상이 나아졌나요?', 'relieving'),
    ('other_symptoms', '함께 나타난 다른 증상이 있나요?', 'associated_symptoms'),
    ('urine_blood', '소변에 피가 섞여 나오나요?', 'associated_symptoms'),
    ('urine_frequency', '소변을 평소보다 자주 보나요?', 'associated_symptoms'),
    ('urine_urgency', '소변을 참기 어려운가요?', 'associated_symptoms'),
    ('flank_pain', '옆구리가 아픈가요?', 'associated_symptoms'),
    ('fever', '열이 났나요?', 'associated_symptoms'),
    ('chill', '오한이 있나요?', 'associated_symptoms'),
    ('pregnancy', '임신 가능성이 있나요?', 'associated_symptoms'),
    ('vaginal_discharge', '질 분비물이 평소와 달라졌나요?', 'associated_symptoms'),
    ('sputum', '가래가 나오나요?', 'associated_symptoms'),
    ('hemoptysis', '기침할 때 피가 나오나요?', 'associated_symptoms'),
    ('contact', '주변에 비슷하게 아픈 사람이 있나요?', 'social_history'),
    ('chest_exertion', '움직이면 가슴 통증이 심해지나요?', 'aggravating'),
    ('leg_swelling', '한쪽 다리가 부었나요?', 'associated_symptoms'),
    ('vomiting', '구토를 했나요?', 'associated_symptoms'),
    ('stool_blood', '대변에 피가 섞여 나오나요?', 'associated_symptoms'),
    ('head_sudden_peak', '두통이 시작하자마자 가장 심했나요?', 'onset'),
    ('focal_weakness', '한쪽 팔다리에 힘이 빠지나요?', 'associated_symptoms'),
    ('photophobia', '밝은 빛에 두통이 심해지나요?', 'associated_symptoms'),
    ('injury', '최근 다친 적이 있나요?', 'past_medical_history'),
    ('thirst', '갈증이 평소보다 심해졌나요?', 'associated_symptoms'),
    ('polyuria', '소변 양이 평소보다 늘었나요?', 'associated_symptoms'),
    ('father_height', '아버지 키는 얼마인가요?', 'family_history'),
    ('mother_height', '어머니 키는 얼마인가요?', 'family_history'),
    ('allergy_cause', '알레르기를 일으킨 약 이름은 뭔가요?', 'allergy'),
    ('allergy_reaction_detail', '알레르기 때 어떤 반응이 생겼나요?', 'allergy'),
    ('new_drug', '증상 전 새로 시작한 약이 있나요?', 'medication'),
    ('supplements', '건강보조제를 드시나요?', 'medication'),
    ('med_adherence', '약은 처방대로 복용하고 계신가요?', 'medication'),
    ('exposure', '최근 생활환경이 바뀌었나요?', 'social_history'),
    ('support', '집에서 도움을 줄 사람이 있나요?', 'social_history'),
]
_EXACT = {text: key for key, text, _ in EXTRA}


def question_key(text):
    if text in _EXACT:
        return _EXACT[text]
    # Specific details take precedence over the broad allergy/family screens.
    if re.search(r'알레르기|allerg', text, re.I):
        if re.search(r'반응|증상|어떻게|reaction', text, re.I):return 'allergy_reaction_detail'
        if re.search(r'이름|어떤 약|무슨 약|무엇', text):return 'allergy_cause'
    if re.search(r'가족|아버지|어머니|부모|family|father|mother', text, re.I):
        if re.search(r'키|height', text, re.I):
            if re.search(r'아버지|아빠|father', text, re.I):return 'father_height'
            if re.search(r'어머니|엄마|mother', text, re.I):return 'mother_height'
        for token, pattern in [('diabetes', r'당뇨|diabet'), ('thyroid', r'갑상|thyroid'),
                               ('cardiac', r'심장|돌연사|cardiac'), ('cancer', r'암|cancer')]:
            if re.search(pattern, text, re.I):return 'family_detail:' + token
        if (topic_for_question(text) == 'family_illness'
                and not re.search(r'가족.*(?:질환이|병이|병력).*있|family history', text, re.I)
                and text != TOPICS['family_illness'][1]):
            return 'family_detail:' + re.sub(r'\s+', '', text)
    if re.search(r'약|medicin', text, re.I) and re.search(r'새로|새롭게|새 약|new', text, re.I):
        return 'new_drug'
    if re.search(r'약|복용|수면제|medicin', text, re.I) and re.search(r'얼마나 자주|how often', text, re.I):
        return 'medication_frequency'
    for key, pattern in [
        ('severity', r'얼마나 심|몇 점|심한 정도'),
        ('location', r'어느 부위|부위.*어디|어디.*아프'),
        ('radiation', r'퍼지|뻗치|radiat'),
        ('character', r'어떤 느낌|통증.*양상'),
        ('urine_frequency', r'소변.*자주|빈뇨'),
        ('flank_pain', r'옆구리.*(?:아프|통증)'),
        ('fever', r'열이.*(?:났|나|있)|발열'),
        ('pregnancy', r'임신.*가능'),
    ]:
        if re.search(pattern, text, re.I):return key
    return topic_for_question(text)


def complaint_groups(state):
    # Never use a proposed diagnosis, patient identifier or sample selector.
    from nova_agent.evidence_scope import patient_evidence_text
    from nova_agent.matching import _strip_negated_spans
    text = _strip_negated_spans(patient_evidence_text(state.chief_complaint, allow_historical=False))
    groups = []
    for name, pattern in [
        ('urinary', r'소변|배뇨|urina|dysuria'), ('respiratory', r'기침|가래|숨.*차|cough|dyspnea'),
        ('chest', r'가슴.*(?:아프|아파|아픈|통증)|흉통|chest pain'),
        ('abdominal', r'복통|배가.*(?:아프|아파|아픈)|배.*통증|abdominal|stomach'),
        ('headache', r'두통|머리.*(?:아프|아파|아픈)|headache'), ('sleep', r'불면|잠.*(?:안|못)|수면제|insomnia'),
        ('weight', r'체중.*(?:빠|감소|줄)|살.*빠|weight loss'),
    ]:
        if re.search(pattern, text, re.I):groups.append(name)
    # Guardian narratives may place the child's complaint after demographics.
    if state.demographics.age is not None and state.demographics.age < 18 and re.search(r'키|성장|height|growth', state.chief_complaint, re.I):
        groups.append('growth')
    return groups


def options(state):
    """Ordered fallback options; ordinary history never asserts an answer."""
    extra = {key: (category, text) for key, text, category in EXTRA}
    groups = complaint_groups(state)
    keys = ['character', 'severity', 'episode_duration', 'episode_frequency',
            'trigger', 'relief', 'previous_episodes', 'daily_timing', 'other_symptoms']
    if any(g in groups for g in ('urinary', 'chest', 'abdominal', 'headache')):
        keys = ['location', 'sudden_onset', *keys]
    if any(g in groups for g in ('chest', 'abdominal', 'headache')):keys.append('radiation')
    family = {
        'urinary': ['fever', 'chill', 'flank_pain', 'urine_frequency', 'urine_urgency', 'urine_blood', 'vomiting'],
        'respiratory': ['safety_breathing', 'safety_chest', 'fever', 'sputum', 'hemoptysis', 'contact'],
        'chest': ['safety_breathing', 'safety_syncope', 'chest_exertion', 'leg_swelling', 'palpitations'],
        'abdominal': ['fever', 'vomiting', 'bowel', 'stool_blood', 'appetite'],
        'headache': ['head_sudden_peak', 'focal_weakness', 'safety_vision', 'fever', 'vomiting', 'photophobia', 'injury'],
        'sleep': ['sleep_pattern', 'sleep_hours', 'snoring', 'caffeine', 'daytime_impairment'],
        'weight': ['safety_chest', 'safety_breathing', 'safety_syncope', 'weight_change', 'intentional_weight_loss', 'appetite', 'nutrition', 'thirst', 'polyuria', 'chronic_gi', 'heat', 'palpitations', 'tremor'],
        'growth': ['headache', 'safety_vomiting', 'safety_vision', 'growth_records', 'growth_velocity', 'father_height', 'mother_height', 'parent_puberty', 'birth', 'birth_course', 'nutrition', 'chronic_gi', 'growth_development', 'fatigue', 'constipation'],
    }
    if 'sleep' in groups:
        from nova_agent.matching import feature_present_with_aliases
        observed = state.all_findings_text(include_context=True, include_family=False)
        if feature_present_with_aliases('sedative use', observed, scrub_negated_spans=True):
            family['sleep'] = ['safety_breathing', 'safety_syncope', 'medication_dose',
                'medication_frequency', 'medication_duration', 'tolerance', 'withdrawal',
                'combined_sedatives', 'medication_control', *family['sleep']]
            if feature_present_with_aliases('dose escalation', observed, scrub_negated_spans=True):
                family['sleep'] = ['medication_tablets', 'medication_night_extra', *family['sleep']]
    # Symptom-specific discrimination before generic extra history.
    keys = [k for g in groups for k in family[g]] + keys
    age, sex = state.demographics.age, state.demographics.sex
    if sex == 'female' and age is not None and 12 <= age <= 55 and any(g in groups for g in ('urinary', 'abdominal')):
        keys = ['pregnancy', *keys, 'menstrual']
        if 'urinary' in groups:keys.append('vaginal_discharge')
    if 'growth' in groups:
        keys = [k for k in keys if k not in {'character','severity','episode_duration','episode_frequency','trigger','relief','daily_timing'}]
    keys += ['self_care', 'new_drug', 'supplements', 'occupation', 'exposure', 'support']
    if age is not None and age < 12:keys = [k for k in keys if k != 'occupation']
    for key in dict.fromkeys(keys):
        if key in extra:
            category, text = extra[key]
        elif key in TOPICS:
            category, text, _ = TOPICS[key]
        else:continue
        yield {'kind':'SAY', 'text':text, 'topic':key, 'category':category}


def exam_options(state):
    exams = {
        'urinary': ['늑골척추각을 타진하겠습니다', '하복부를 촉진하겠습니다'],
        'respiratory': ['폐를 청진하겠습니다', '호흡 양상을 살펴보겠습니다'],
        'chest': ['심장을 청진하겠습니다', '폐를 청진하겠습니다', '다리 부종을 확인하겠습니다'],
        'abdominal': ['복부를 시진하겠습니다', '복부를 청진하겠습니다', '복부를 촉진하겠습니다'],
        'headache': ['동공반사를 확인하겠습니다', '팔다리 근력을 확인하겠습니다'],
        'growth': ['신장을 측정하겠습니다', '체중을 측정하겠습니다', '상하체 비율을 측정하겠습니다'],
        'weight': ['체중을 측정하겠습니다', '갑상선을 촉진하겠습니다'],
        'sleep': [],
    }
    for group in complaint_groups(state):
        for text in exams[group]:
            yield {'kind':'EXAM', 'text':text, 'category':'physical_exam'}


def attempted(encounter, action):
    from nova_agent.interview_evidence import exam_topic, exam_attempted
    text, kind = action['text'], action['kind']
    key = question_key(text) if kind == 'SAY' else exam_topic(text)
    for turn in encounter.turns:
        if turn.kind != kind:continue
        if turn.text == text:return True
        other = question_key(turn.text) if kind == 'SAY' else exam_topic(turn.text)
        if key and key == other:return True
    if kind == 'EXAM':return exam_attempted(encounter.pstate, text)
    return bool(key in TOPICS and topic_known(encounter.pstate, key))


def coverage(encounter):
    """Only actual attempts and their replies, not model claims of coverage."""
    result = []
    for action in options(encounter.pstate):
        key = question_key(action['text'])
        turns = [(i, t) for i, t in enumerate(encounter.turns, 1)
                 if t.kind == 'SAY' and question_key(t.text) == key]
        status = 'unasked'
        if turns:
            t = turns[-1][1]
            status = 'unresolved' if not t.ok or answer_kind(t.reply) == 'unknown' else 'observed_reply'
        elif key in TOPICS and topic_known(encounter.pstate, key):status = 'observed_elsewhere'
        result.append({'domain':key, 'status':status, 'observation_ids':['T'+str(i) for i, _ in turns],
                       'suggested_question':action['text']})
    return result
