"""Bounded history follow-ups using the existing KB's risk context, never inferred lab results.
No diagnostic weights are assigned here. Question wording is an engineering contract.
"""
SHORT_FOLLOWUPS = {
    'medication:recent medication changes': {
        'en':'Any recent medicine changes?', 'ko':'최근 약이 바뀌었나요?',
        'ja':'最近、薬の変更はありますか？', 'zh':'最近用药有变化吗？'},
    'associated_symptoms:vomiting': {'en':'Have you been vomiting?', 'ko':'구토를 했나요?', 'ja':'嘔吐しましたか？','zh':'有呕吐吗？'},
    'associated_symptoms:diarrhea': {'en':'Any diarrhea?', 'ko':'설사를 하나요?', 'ja':'下痢はありますか？','zh':'有腹泻吗？'},
    'social_history:fluid intake changes': {'en':'Has your fluid intake changed?','ko':'마시는 물의 양이 바뀌었나요?', 'ja':'水分摂取量は変わりましたか？','zh':'饮水量有变化吗？'},
    'past_medical_history:last dialysis': {'en':'When was your last dialysis?', 'ko':'마지막 투석은 언제였나요?', 'ja':'最後の透析はいつですか？','zh':'最后一次透析是什么时候？'},
    'associated_symptoms:loss of consciousness': {'en':'Did you lose consciousness?', 'ko':'의식을 잃었나요?', 'ja':'意識を失いましたか？','zh':'有失去意识吗？'},
}


def followup_questions(state, item):
    """Only contenders with multiple observed signals get these follow-ups.
    A drug name or weakness alone never activates an electrolyte workup."""
    if not state.preliminary_rules or item is None:
        return []
    from nova_agent.disposition import symptomatic_rate_concern
    observed_rate_cluster = (item.diagnosis_id == 'cardiac_arrhythmia' and bool(symptomatic_rate_concern(state)))
    if not observed_rate_cluster and (item.rank > 3 or len(item.supporting_evidence) < 2):
        return []
    support = set(item.supporting_evidence)
    keys = []
    if item.diagnosis_id == 'severe_electrolyte_disorder' and support.intersection(
            {'muscle weakness','muscle cramps','confusion','seizure'}):
        keys = ['associated_symptoms:vomiting','associated_symptoms:diarrhea',
                'social_history:fluid intake changes']
        if state.medication_text or state.medications:
            keys.append('medication:recent medication changes')
        if 'dialysis' in ' '.join(state.all_findings_text(include_family=False)).lower():
            keys.append('past_medical_history:last dialysis')
    if item.diagnosis_id == 'cardiac_arrhythmia' and support.intersection(
            {'pulse rate below 50','pulse rate of 150 or more'}):
        keys = ['associated_symptoms:loss of consciousness']
        if state.medication_text or state.medications:
            keys.append('medication:recent medication changes')
    from nova_agent.matching import feature_present_with_aliases, feature_denied
    return [k for k in keys if not state.question_attempted(k)
            and not feature_present_with_aliases(k.partition(':')[2],state.all_findings_text(include_family=False),scrub_negated_spans=True)
            and not feature_denied(k.partition(':')[2],state.pertinent_negatives)]
