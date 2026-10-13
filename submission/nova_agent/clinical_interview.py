"""General concise question selection for chronic presentations, not case lookup.

Uses the available interview budget. Templates ask one thing and
require explicit answered content before skipping a topic. No diagnosis is chosen.
"""
import re
from nova_agent.clinical_assertions import normalize_exam_notation
from nova_agent.clinical_profiles import growth_velocity


def interview_family(state):
    from nova_agent.evidence_scope import patient_evidence_text
    from nova_agent.matching import _strip_negated_spans
    text=patient_evidence_text(state.chief_complaint,allow_historical=False)
    text=_strip_negated_spans(normalize_exam_notation(text)).casefold()
    from nova_agent.matching import feature_present_with_aliases
    current=state.all_findings_text(include_context=False,include_family=False)
    # A chronic complaint never diverts newly observed acute cardiorespiratory
    # or neurological concerns into a routine sleep/growth interview.
    if any(feature_present_with_aliases(f,current,scrub_negated_spans=True) for f in (
        'chest pain','shortness of breath','syncope','hemoptysis','focal weakness',
        'altered mental status','severe headache','fever')):
        return None
    family=_family_from_text(state,text,allow_condition_names=True)
    if family:return family
    # Openings are often narrated by a guardian and describe the course over
    # the past year ("엄마는 ... 일 년 전부터 ..."). The current-evidence filter
    # keeps only the first sentence of such a narrative, which hid the actual
    # complaint. Retry on the whole negation-stripped opening, but a bare
    # disease name there (e.g. a past thyroid operation) is not a complaint.
    full=_strip_negated_spans(normalize_exam_notation(state.chief_complaint or '')).casefold()
    return _family_from_text(state,full,allow_condition_names=False)


def _family_from_text(state,text,allow_condition_names):
    if re.search(r'sleep|insomnia|sedative|졸피뎀|수면제|잠이|불면|낮에.*졸',text):return 'sleep'
    if state.demographics.age is not None and state.demographics.age<18 and re.search(r'short stature|growth|height|키|성장',text):return 'growth'
    if re.search(r'weight loss|lost weight|weight.*los|체중.*(?:감소|빠|줄)|살이.*(?:빠|줄)|먹는데.*빠|더위',text):return 'thyroid'
    if allow_condition_names and re.search(r'갑상',text):return 'thyroid'
    return None


TOPICS = {
 'surgery':('past_medical_history','수술받은 적이 있나요?',r'수술력|surgical history|previous surgery'),
 'smoking':('social_history','담배를 피우시나요?',r'smok|tobacco|흡연|담배'),
 'alcohol':('social_history','술은 얼마나 자주 드시나요?',r'alcohol|음주|술.*(?:마시|먹|잔|회)'),
 'course':('course','증상이 점점 심해지고 있나요?',r'worsen|progress|심해|악화|호전|나아'),
 'function':('associated_symptoms','일상생활에 어떤 지장이 있나요?',r'일상.*지장|(?:낮|일|활동).*(?:지장|제한)|daily.*(?:life|activit)|daytime impairment'),
 'prior_care':('past_medical_history','이 증상으로 진료받은 적이 있나요?',r'이 증상.*진료|previous.*(?:evaluat|consult)'),
 'medical_history':('past_medical_history','진단받거나 치료 중인 병이 있나요?',r'(?:과거력|기저질환|chronic disease|medical history).*(?:없|없음|none|no)|진단받.*병'),
 'family_illness':('family_history','가족 중 질환이 있는 분이 있나요?',r'가족력.*(?:없|없음)|family history.*(?:none|negative)'),
 'sleep_pattern':('associated_symptoms','잠들기와 잠 유지 중 무엇이 어렵나요?',r'잠들기.*어렵|자주.*깨|sleep (?:onset|maintenance)'),
 'sleep_hours':('associated_symptoms','하루에 실제로 몇 시간 주무시나요?',r'(?:\d+|한|두|세|네|다섯|여섯)\s*시간.*(?:자|잠|수면)|sleep.*\d+.*hours?'),
 'snoring':('associated_symptoms','잘 때 코골이가 있나요?',r'snor|코골'),
 'caffeine':('social_history','커피나 카페인은 얼마나 드시나요?',r'caffeine|카페인|커피'),
 'symptom_onset':('onset','언제부터 이런 증상이 있었나요?',r'(?:\d+|한|두|세|석|몇)\s*(?:개월|달|주|일|시간)\s*(?:간|전부터|동안|째)|어제부터|오늘.*시작|since (?:yesterday|last|this)|(?:for|over) (?:the )?(?:past )?\d+\s*(?:day|week|month|year)'),
 'weight_change':('associated_symptoms','체중이 몇 kg 줄었나요?',r'\d+(?:\.\d+)?\s*(?:kg|킬로)[^;\n]{0,12}(?:감소|빠|줄)|(?:lost|loss of)\s*\d+(?:\.\d+)?\s*kg'),
 'medication_name':('medication','복용 중인 약 이름이 뭔가요?',r'zolpidem|benzodiazep|diazepam|lorazepam|졸피뎀|수면제|아무.*약.*없|약.*안.*먹'),
 'medication_dose':('medication','수면제 한 번 용량은 몇 mg인가요?',r'\d+(?:\.\d+)?\s*(?:mg|밀리그램|알|정)'),
 'medication_frequency':('medication','수면제를 하루 몇 번 드시나요?',r'every night|daily|nightly|times.*day|매일|하루.*(?:회|번)|매일.*밤'),
 'medication_duration':('medication','수면제를 얼마나 오래 드셨나요?',r'(?:take|taken|복용|먹)[^;\n]{0,30}(?:years?|months?|년|개월)|(?:years?|months?|년|개월)[^;\n]{0,10}(?:복용|먹)'),
 'tolerance':('medication','같은 효과에 더 많은 약이 필요한가요?',r'toleran|increasing doses|dose.*escal|내성|용량.*늘|더.*많.*약'),
 'withdrawal':('medication','수면제를 줄이면 어떤 증상이 생기나요?',r'withdraw|stopp|끊으면|줄이면|중단.*(?:증상|불면)'),
 'daytime_impairment':('associated_symptoms','낮 활동에 어떤 지장이 있나요?',r'daytime impairment|낮.*(?:활동|지장)|운전.*졸'),
 'combined_sedatives':('medication','다른 진정제를 함께 드시나요?',r'combined|other sedative|추가.*수면제|다른.*진정제|병용'),
 'growth_records':('associated_symptoms','이전 키를 잰 날짜와 키를 알려주세요',r'\d+(?:\.\d+)?\s*cm[^\n]{0,60}\d+(?:\.\d+)?\s*cm'),
 'growth_velocity':('associated_symptoms','1년 동안 키가 얼마나 컸나요?',r'growth velocity|성장속도'),
 'parent_height':('family_history','부모님 키는 각각 얼마인가요?',r'parent.*height|부모.*키|father.*short|parents.*short'),
 'parent_puberty':('family_history','부모님도 사춘기가 늦었나요?',r'(?:father|mother|parent|아버지|어머니|부모)[^;\n]{0,30}(?:puberty|사춘기)'),
 'birth':('past_medical_history','태어날 때 체중은 얼마였나요?',r'birth.*weight|출생.*체중|태어.*체중'),
 'nutrition':('associated_symptoms','식사는 규칙적으로 하나요?',r'nutrition|diet|식사|영양'),
 'chronic_gi':('associated_symptoms','설사가 오래 지속되나요?',r'chronic.*diarr|만성.*설사|설사.*지속'),
 'puberty':('associated_symptoms','사춘기 변화가 시작됐나요?',r'(?:my|child|아이|본인)[^;\n]{0,20}(?:pubert|사춘기)'),
 'appetite':('associated_symptoms','식욕은 어떻게 변했나요?',r'appetite|eating more|식욕|잘 먹'),
 'heat':('associated_symptoms','더위를 견디기 어려우신가요?',r'heat intolerance|overheated|더위|더워'),
 'sweat':('associated_symptoms','땀이 평소보다 많아졌나요?',r'sweat|땀|발한'),
 'tremor':('associated_symptoms','손이 떨리나요?',r'tremor|hands?.*shak|손.*떨'),
 'palpitations':('associated_symptoms','가슴이 두근거리나요?',r'palpitat|heart.*pound|두근|심장.*빨리'),
 'bowel':('associated_symptoms','배변 횟수가 늘었나요?',r'bowel|diarr|loose stool|묽은 변|배변|설사'),
 'menstrual':('associated_symptoms','생리 주기가 달라졌나요?',r'menstru|period.*change|생리|월경'),
 'allergy':('allergy','약물 알레르기가 있나요?',r'allerg|알레르기'),
 # Growth: a child's history is the developmental and perinatal record, not adult pain descriptors.
 'birth_course':('past_medical_history','임신·출산 때 문제는 없었나요?',r'(?:임신|출산|분만|만삭|조산|미숙아|prematur|term birth)'),
 'development':('past_medical_history','말하기·걷기 발달은 또래와 비슷한가요?',r'발달|develop|milestone'),
 'fatigue':('associated_symptoms','평소 쉽게 피곤해하나요?',r'피곤|피로|fatigue|tired'),
 'constipation':('associated_symptoms','변비가 있나요?',r'변비|constipat'),
 'headache':('associated_symptoms','두통이나 구토가 자주 있나요?',r'두통|headache|구토|vomit'),
 'sleep_child':('social_history','밤에 몇 시간 자나요?',r'(?:\d+|열|아홉|여덟)\s*시(?:간)?|잠|수면|sleep'),
 'daily_life':('social_history','어린이집 생활은 잘 지내나요?',r'어린이집|유치원|학교|school|daycare|스트레스'),
}


# A positive screening reply does not identify the disease, drug or reaction.
# One clarification per topic and three per encounter; unknown/refused replies
# are left unresolved rather than repeatedly solicited.
DETAIL_QUESTIONS = {
    'allergy': '어떤 약에 어떤 알레르기 반응이 있었나요?',
    'medication_name': '복용 약 이름을 구체적으로 알려주세요',
    'medical_history': '진단받은 병 이름이 무엇인가요?',
    'symptom_onset': '증상이 시작된 때를 구체적으로 알려주세요',
    'prior_care': '이 증상으로 진료받은 결과는 어땠나요?',
    'family_illness': '가족 중 누가 어떤 병을 앓고 있나요?',
    'surgery': '어떤 수술을 받으셨나요?',
    'function': '일상에서 가장 어려운 활동은 무엇인가요?',
}


def needs_history_detail(answer):
    from nova_agent.state import answer_kind
    kind = answer_kind(answer)
    if kind in {'no', 'unknown'}:return False
    if kind == 'yes':return True
    # Only nonspecific affirmative screens, not arbitrary short named answers.
    return bool(re.fullmatch(
        r'\s*(?:네[, ]*)?(?:약(?:을|은)? (?:먹고|복용하고) 있어요|'
        r'병이 있어요|알레르기가 있어요|수술(?:을)? (?:했어요|받았어요)|'
        r'진료(?:를)? 받았어요|검사(?:를)? 받았어요|불편해요)[.!\s]*', answer or ''))


def next_history_clarification(state):
    attempts = [a for a in state.performed_actions if a.action_type == 'ASK']
    if sum(a.content in DETAIL_QUESTIONS.values() for a in attempts) >= 3:return None
    for topic, question in DETAIL_QUESTIONS.items():
        replies = [a for a in attempts if topic_for_question(a.content) == topic]
        if not replies or any(a.content == question for a in attempts):continue
        if needs_history_detail(replies[-1].result):
            category = TOPICS[topic][0]
            return ('SAY', category+':'+topic, question, category)
    return None


def unresolved_history(state):
    """Observed gaps only; no conversion of unasked items to negative facts."""
    from nova_agent.state import answer_kind
    latest = {}
    for a in state.performed_actions:
        if a.action_type != 'ASK':continue
        topic = topic_for_question(a.content)
        if topic:latest[topic] = a
    return [f'{a.content} → {a.result} (미확인 또는 세부 정보 부족)'
            for topic, a in latest.items()
            if answer_kind(a.result) == 'unknown' or
            (topic == 'symptom_onset' and answer_kind(a.result) == 'no') or
            (topic in DETAIL_QUESTIONS and needs_history_detail(a.result))]


def topic_for_question(text):
    for topic, question in DETAIL_QUESTIONS.items():
        if text == question:return topic
    for topic, (_, question, _) in TOPICS.items():
        if text == question:return topic
    # Question-language match is intentionally separate from answer evidence.
    for topic,pattern in (
        ('birth',r'태어|출생'),
        ('surgery',r'수술|입원한|surg|hospitali'),
        ('smoking',r'담배|흡연|smok|tobacco'),
        ('alcohol',r'술은|음주|alcohol'),
        ('course',r'점점.*심|경과|worsen|progress'),
        ('function',r'일상.*지장|daily.*activit'),
        ('prior_care',r'이 증상.*진료|previous.*evaluat'),
        ('medical_history',r'진단받.*병|치료 중인 병|기저.*질환|과거.*병|과거력|병력|앓.*병|medical history|chronic disease'),
        ('family_illness',r'가족.*(?:질환|병)|family.*(?:history|illness)'),
        ('sleep_pattern',r'잠들기|잠 유지|sleep.*pattern'),
        ('sleep_hours',r'몇 시간.*(?:주무|자|수면)|hours.*sleep'),
        ('snoring',r'코골|snor'),('caffeine',r'커피|카페인|caffeine'),
        ('symptom_onset',r'언제부터|when.*start'),('weight_change',r'체중.*(?:몇|얼마)|몇\s*kg.*(?:빠|줄)|weight.*(?:lost|loss)'),
        ('medication_dose',r'몇\s*mg|용량|몇\s*알|dose'),('medication_frequency',r'(?:약|수면제|복용|드시|먹|medicin|take).*(?:몇\s*번|몇\s*회|frequency)|(?:몇\s*번|몇\s*회).*(?:복용|드시|먹|take)'),
        ('medication_duration',r'얼마나.*(?:드|복용)|복용.*기간|how long.*tak'),
        ('tolerance',r'같은 효과|내성|증량|toleran'),('withdrawal',r'줄이면|끊으면|금단|withdraw'),
        ('medication_name',r'약.*이름|무슨.*약|복용.*약|먹는.*약|medicin'),
        ('growth_records',r'이전.*키|키.*날짜'),('growth_velocity',r'1년.*키|성장.*속도|growth velocity'),
        ('parent_height',r'부모.*키'),('parent_puberty',r'부모.*사춘기'),('birth',r'태어|출생'),
        ('nutrition',r'식사|영양'),('chronic_gi',r'설사.*오래|만성.*설사'),('puberty',r'사춘기'),
        ('heat',r'더위|heat'),('sweat',r'땀|sweat'),('tremor',r'떨|tremor'),('palpitations',r'두근|palpitat'),
        ('appetite',r'식욕|appetite'),('bowel',r'배변|bowel'),('menstrual',r'생리|월경'),
        ('allergy',r'알레르기|allerg'),('daytime_impairment',r'낮.*(?:활동|졸)|daytime'),
        ('combined_sedatives',r'다른.*진정제|병용')):
        if re.search(pattern,text,re.I):return topic
    return None


def relevant_substance_question(state, text):
    if state.demographics.age is None or state.demographics.age>=12:return True
    if not re.search(r'smok|alcohol|흡연|음주|담배|술',text,re.I):return True
    if re.search(r'second.hand|passive smok|간접흡연|담배\s*연기|흡연.*노출',text,re.I):return True
    raw=' '.join([state.chief_complaint,*state.medication_text,*state.social_history])
    return bool(re.search(r'poison|ingest|expos|중독|노출|마셨|삼켰',raw,re.I))


def topic_known(state, topic):
    from nova_agent.interview_evidence import topic_answered
    return topic_answered(state, topic, TOPICS[topic][2])


def next_clinical_action(state):
    from nova_agent.interview_evidence import topic_attempted
    family=interview_family(state)
    if not family:return None
    if family=='sleep':
        order=['medication_name','medication_dose','medication_frequency','medication_duration','tolerance','withdrawal','daytime_impairment','combined_sedatives','allergy']
        from nova_agent.matching import feature_present_with_aliases
        exposure=feature_present_with_aliases('sedative use',state.all_findings_text(include_context=True,include_family=False),scrub_negated_spans=True)
        if not exposure:order=['medication_name','daytime_impairment','allergy']
        order += ['symptom_onset','sleep_pattern','sleep_hours','snoring','caffeine']
    elif family=='growth':
        order=['growth_records','growth_velocity','parent_height','parent_puberty','birth','birth_course','development',
               'nutrition','chronic_gi','fatigue','constipation','headache','puberty','sleep_child','daily_life']
    else:
        order=['symptom_onset','weight_change','appetite','heat','palpitations','tremor','sweat','bowel','allergy']
        if state.demographics.sex=='female' and (state.demographics.age is None or 12<=state.demographics.age<=55):order.append('menstrual')
        # Once a characteristic symptom cluster is established, examination has
        # more candidate-separating value than finishing every possible ROS item.
        from nova_agent.matching import feature_present_with_aliases
        current=state.all_findings_text(include_context=False,include_family=False)
        cluster=sum(feature_present_with_aliases(f,current,scrub_negated_spans=True)
                    for f in ('weight loss','increased appetite','heat intolerance','palpitations','tremor'))
        if cluster>=3:
            if not state.exam_done('thyroid_exam'):return ('EXAM','thyroid_exam','갑상선을 촉진하겠습니다','thyroid_exam')
            if feature_present_with_aliases('diffuse goiter',state.objective_findings_text(),scrub_negated_spans=True):
                if not state.exam_done('thyroid_eye'):return ('EXAM','thyroid_eye','안구 돌출을 살펴보겠습니다','thyroid_eye')
                # A characteristic exam does not answer the time course,
                # quantitative change or medication/allergy safety history.
                if 'medication_name' not in order:order.append('medication_name')
    # Fewer, higher-value turns, then only relevant physical maneuvers.
    for topic in order:
        if not topic_known(state,topic) and not topic_attempted(state,topic):
            category,text,_=TOPICS[topic]
            feature={'heat':'heat intolerance','sweat':'sweating','tremor':'tremor','palpitations':'palpitations',
                     'withdrawal':'withdrawal symptoms','tolerance':'dose escalation','daytime_impairment':'daytime sleepiness',
                     'chronic_gi':'chronic diarrhea'}.get(topic,topic.replace('_',' '))
            return ('SAY',category+':'+feature,text,category)
    exams={'growth':[('growth_height','신장을 측정하겠습니다'),('growth_weight','체중을 측정하겠습니다'),
                     ('growth_proportion','상하체 비율을 측정하겠습니다'),('growth_dysmorphism','얼굴 기형이 있는지 보겠습니다'),
                     ('thyroid_exam','갑상선을 촉진하겠습니다'),('growth_tanner','사춘기 발달 단계를 보겠습니다'),
                     ('growth_abdomen','간과 비장을 촉진하겠습니다')],
           'thyroid':[('thyroid_exam','갑상선을 촉진하겠습니다'),('thyroid_eye','안구 돌출을 살펴보겠습니다'),('thyroid_tremor','양손을 뻗어 떨림을 보겠습니다')],
           'sleep':[]}[family]
    for key,text in exams:
        if not state.exam_done(key):return ('EXAM',key,text,key)
    return None


def missing_foundation_topics(state):
    """Unattempted essentials, not a minimum turn quota or a diagnosis gate.

    A birth-weight question does not replace medical history; parental heights
    do not replace family illness. Unknown replies remain unknown but are not
    repeatedly requested. Already observed facts need no extra question.
    """
    from nova_agent.interview_evidence import topic_attempted
    order = ['symptom_onset','course','medical_history','medication_name',
             'allergy','family_illness','function','prior_care']
    if interview_family(state)=='growth':
        # Slow growth has no "worsening" or "daily-life limitation" in the pain/symptom sense; the opening
        # already dates it. The growth interview covers its course with measured records instead.
        order=[t for t in order if t not in ('course','function','symptom_onset')]
    # Broad prior-care questions do not establish surgical history. Adult
    # substance exposure affects both the differential and safe treatment.
    order.append('surgery')
    if state.demographics.age is not None and state.demographics.age >= 18:
        order += ['smoking','alcohol']
    standard_keys={'symptom_onset':'onset','course':'course','medical_history':'past_medical_history',
                   'medication_name':'medication','allergy':'allergy','family_illness':'family_history'}
    def attempted(topic):
        if topic_attempted(state,topic):return True
        return any(a.action_type=='ASK' and a.key==standard_keys.get(topic)
                   and topic_for_question(a.content) in (None,topic) for a in state.performed_actions)
    return [t for t in order if not topic_known(state,t) and not attempted(t)]


def next_foundation_action(state):
    clarification = next_history_clarification(state)
    if clarification:return clarification
    missing = missing_foundation_topics(state)
    if not missing:return None
    topic = missing[0]
    category,text,_ = TOPICS[topic]
    return ('SAY', category+':'+topic, text, category)
