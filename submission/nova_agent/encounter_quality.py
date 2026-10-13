"""General interview and plan contracts; no public-case or evaluator lookup.

Engineering checks distinguish a question attempt from observed information.
Only wording and coverage change here, never a diagnostic or safety score.
"""
import re


def single_question(text):
    """Reject requests for multiple independent answers rather than truncate.

    Alternatives for one attribute (sleep onset vs maintenance) remain valid.
    Multi-field allergy screens are split by the clinical interview instead.
    """
    if len(re.findall(r'[?？]', text)) > 1:
        return False
    if re.search(r'그리고|\s및\s|한꺼번에|모두.*(?:알려|말씀)|전체.*(?:병력|증상)', text):
        return False
    if re.search(r'(?:타고|있고|나고|아프고|하거나|하나요.*또|인가요.*또)', text):
        return False
    return True


def pending_interview(state):
    """Missing/attempted HPI domains are suggestions, not an obligatory quota."""
    from nova_agent.clinical_interview import TOPICS, topic_known
    from nova_agent.interview_evidence import topic_attempted
    domains=['symptom_onset','course','function','prior_care','medical_history',
             'medication_name','allergy','episode_duration','episode_frequency',
             'trigger','relief','previous_episodes','occupation']
    return {t: ('answered' if topic_known(state,t) else 'attempted_unknown' if topic_attempted(state,t) else 'unasked')
            for t in domains if t in TOPICS}


def needs_adaptive_review(turns, pending=False):
    from nova_agent.state import answer_kind
    observed=[t for t in turns if t.ok and t.reply]
    if not observed:return False
    if pending:return True
    return any(t.kind=='EXAM' or answer_kind(t.reply) not in {'no','unknown'} for t in observed)


def specific_test_plan(plan, entry, urgent=False):
    """Explain existing KB planned tests; no invented results or blanket panel.

    Uses the existing catalog and workup. Conditional PE pathways replace the
    old flat D-dimer+CT list; an early normal troponin never rules out ACS.
    """
    from nova_agent.taxonomy import TEST_CATALOG
    ids=list(dict.fromkeys((entry or {}).get('minimum_workup',[]) +
                          (entry or {}).get('discriminating_tests',[])))
    ids=[k for k in ids if k in TEST_CATALOG][:4]
    purpose={
        'ecg':'심장 리듬·허혈 소견 확인', 'troponin':'심근 손상 평가',
        'cxr':'폐렴·기흉·울혈 등 흉부 원인 구분',
        'glucose_point_of_care':'저혈당·고혈당 확인', 'ketones':'케톤증 확인',
        'abg':'산염기·호흡 상태 확인', 'bmp':'전해질·신기능 확인',
        'cbc':'빈혈·염증 소견 평가', 'urinalysis':'요로 감염·혈뇨 확인',
        'urine_culture':'원인균과 항생제 감수성 확인', 'blood_culture':'균혈증 평가',
        'lactate':'저관류 평가', 'lipase':'췌장염 감별',
        'beta_hcg':'임신 관련 원인·검사 안전성 평가',
        'pelvic_ultrasound':'임신 위치·골반 원인 확인',
        'ct_head':'급성 두개내 원인 평가', 'ct_aorta':'대동맥 질환 확인',
        'ct_abdomen':'복부 구조적 원인 구분',
    }
    additions=[f"- {TEST_CATALOG[k]['name_ko']}: {purpose[k]} (계획; 미시행)" for k in ids if k in purpose]
    cid=(entry or {}).get('id','')
    if cid=='pulmonary_embolism':
        additions=['폐색전증 사전확률 평가 후 저위험이면 D-dimer 고려; 양성이거나 사전확률이 높으면 CT 폐혈관조영을 고려 (계획; 미시행)']
    if cid=='acute_coronary_syndrome':
        additions.append('초기 정상 심전도·트로포닌만으로 배제하지 않음; 증상 시작 시점에 따른 반복 평가를 응급 진료에서 결정')
    if additions:
        # Keep tests justified by supported dangerous alternatives and actual
        # measured concerns. A leading benign candidate cannot erase them.
        previous=plan.get('tests','')
        if cid=='pulmonary_embolism':
            previous='; '.join(x.strip() for x in previous.split(',')
                               if not any(TEST_CATALOG[k]['name_ko'] in x for k in ('d_dimer','ct_chest_angio')))
        plan['tests']='\n'.join(filter(None,[previous,*additions]))
        plan['tests']+='\n이상 결과에 따라 원인별 치료·의뢰를 결정; 정상이어도 증상이 지속되면 대체 원인과 검사 시점·한계를 재평가'
    if urgent:
        plan['follow_up']='지금 응급 진료에서 증상·활력징후·필요 검사 결과를 즉시 재평가하고 관찰·입원 여부 결정; 일반 외래 예약까지 기다리지 않음'
    elif cid in {'pneumonia','pyelonephritis','gastroenteritis','acute_bronchitis','uncomplicated_cystitis'}:
        plan['follow_up']='48~72시간 내 담당 진료에서 증상·수분 섭취·치료 반응과 검사 결과를 재평가; 악화하거나 호흡곤란·의식 변화·섭취 불가 시 즉시 진료'
        plan['spoken_follow_up']='2~3일 내 증상과 결과를 다시 확인해요'
        plan['spoken_precautions']='숨참·의식 변화·섭취 불가면 즉시 진료해요'
    if ids:
        first=ids[0]
        name=TEST_CATALOG[first]['name_ko']
        why=purpose.get(first,'의심 원인 확인')
        message=f'{name}로 {why}해요'
        if len(message)<=30:plan['spoken_test_purpose']=message
    return plan


def merged_model_tests(plan, proposal, corpus, allowed_names, grounded_in):
    """Accept an indicated planned test, never an arbitrary free-form result.

    The final supported primary owns this proposal. Clinical indications must
    quote one real patient observation. Tests remain within its KB workup.
    """
    rows=proposal.get('test_plan')
    if not isinstance(rows,list):return plan
    additions=[]
    canonical=lambda value: re.sub(r'[\s_·()/-]+', '', value).casefold()
    names={canonical(name):name for name in allowed_names}
    for row in rows[:5]:
        if not isinstance(row,dict):continue
        name=row.get('test');indication=row.get('indication');evidence=row.get('evidence')
        if not all(isinstance(v,str) and 0<len(v)<=250 for v in (name,indication,evidence)):continue
        if canonical(name) not in names or not grounded_in(evidence,corpus):continue
        name=names[canonical(name)]
        # The indication is a clinical inference, separate from its quote.
        line=f'- {name}: 계획 목적 — {indication} (관찰 근거: {evidence}; 계획·미시행)'
        for key,label in (('if_abnormal','이상 결과 시'),('if_normal','정상이나 증상 지속 시')):
            action=row.get(key)
            if isinstance(action,str) and 0<len(action)<=250:
                # Free-form result branches cannot add medication doses,
                # cancel necessary follow-up or downgrade urgent disposition.
                if not re.search(r'\d+\s*(?:mg|mcg|정|알)|약.*(?:끊|중단|증량)|검사.*불필요|배제.*확정|완전.*배제|응급.*(?:불필요|없)|안.*와도',action,re.I):
                    line+=f'; {label}: {action}'
        additions.append(line)
    if additions:plan['tests']+='\n'+'\n'.join(dict.fromkeys(additions))
    return plan


def grounded_reasoning(proposal, corpus, grounded_in):
    """Preserve concise clinical interpretation next to its verified quotation.

    Interpretations are explicitly judgments, never newly observed S/O facts.
    The caller only passes the proposal belonging to the accepted diagnosis.
    """
    rows = proposal.get('clinical_reasoning', [])
    if not isinstance(rows, list):
        return []
    out = []
    for row in rows[:4]:
        if not isinstance(row, dict):
            continue
        fact, meaning = row.get('observation'), row.get('interpretation')
        if (isinstance(fact, str) and isinstance(meaning, str)
                and 0 < len(fact) <= 300 and 0 < len(meaning) <= 400
                and grounded_in(fact, corpus)):
            out.append(f'- 관찰: {fact} / 임상적 해석: {meaning}')
    return list(dict.fromkeys(out))


def complete_care_plan(plan, state, decision, urgent):
    """One plan for spoken and written advice; keep clinical safety policy intact.

    Return precautions are conditional future events, not new patient findings.
    Sources and limits are documented in the v46 engineering report.
    """
    if urgent:
        plan['disposition'] = '지금 응급실 평가 및 모니터링; 추가 문진이나 외래 예약 때문에 이송을 지연하지 않음'
        plan['spoken_next_step'] = '지금 응급실에서 평가받으세요'
        plan['spoken_precautions'] = '직접 운전하지 말고 119 도움을 받으세요'
        plan['education'] += '\n응급 평가가 필요한 현재 상황을 설명하고 안전한 이송 방법 안내; 직접 운전하지 않도록 설명'
        plan['follow_up'] = '응급 진료에서 즉시 증상·활력징후와 필요한 검사 결과를 재평가; 결과에 따라 관찰·입원 결정'
        plan['spoken_follow_up'] = '응급실에서 바로 상태를 다시 확인해야 해요'
        return plan
    # Existing profile precautions are already specific; supplement only the
    # generic fallback that previously said merely "if worse".
    generic = plan.get('spoken_precautions') == '1~2주 내 재진, 악화 시 즉시 진료받으세요'
    if generic:
        from nova_agent.matching import feature_present_with_aliases
        facts = state.all_findings_text(include_context=False, include_family=False)
        has = lambda f: feature_present_with_aliases(f, facts, scrub_negated_spans=True)
        if any(has(f) for f in ('chest pain', 'palpitations', 'shortness of breath', 'syncope')):
            warning = '흉통·숨참·실신 시 즉시 응급실로 가세요'
        elif any(has(f) for f in ('headache', 'dizziness', 'weakness')):
            warning = '갑작스런 마비·말 어눌함은 즉시 응급실로'
        elif any(has(f) for f in ('abdominal pain', 'vomiting', 'diarrhea')):
            warning = '심한 복통·피 토함·실신 시 즉시 진료해요'
        else:
            warning = '숨참·의식 변화·실신 시 즉시 진료받으세요'
        plan['spoken_precautions'] = warning
        plan['follow_up'] += '\n예정일을 기다리지 않을 상황: ' + warning
    plan['education'] += '\n현재 진단은 수집 정보에 근거한 추정이며 추가 확인이 필요함. ' + plan.get('spoken_precautions', '')
    return plan
