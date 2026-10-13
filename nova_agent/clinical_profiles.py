"""Bounded supplemental profiles; separate from the historical ontology catalog.

Clinical concepts are explicit engineering heuristics, not official code mappings.
No case identifiers, names or exact opening lookup. Source text stays in state.
"""
from functools import lru_cache
import json
from pathlib import Path
import re


@lru_cache(maxsize=1)
def profiles():
    return {r['id']:r for r in json.loads((Path(__file__).parent/'knowledge/clinical_profiles.json').read_text(encoding='utf-8'))['profiles']}


def profile_by_id(cid):
    return profiles().get(cid) or profiles().get('onto::'+cid)


def profile_named(text):
    key = re.sub(r'[^\w가-힣]+', ' ', str(text).casefold()).strip()
    found = [r for r in profiles().values() if any(
        key == re.sub(r'[^\w가-힣]+',' ',n.casefold()).strip() for n in [r['name'],*r['aliases'],r['id']])]
    return found[0] if len(found)==1 else None


_RELATION=r'father|mother|parent|\bmom\b|\bdad\b|아버지|어머니|부모|아빠|엄마|부친|모친'
_LATE_BLOOMER=(r'delayed puberty|late puberty|late bloomer|사춘기(?:가|는|도)?\s*(?:좀\s*)?늦|늦게\s*(?:컸|자랐|크)|'
               r'(?:고등학교|고교)[^.]{0,25}(?:갑자기|많이|훌쩍)[^.]{0,10}(?:컸|자랐)|수염(?:이|도)?\s*늦|변성기(?:가|도)?\s*늦')


def growth_velocity(text):
    """Explicit cm/year or two supplied, dated heights one year apart. No guessed dates."""
    matches = re.findall(r'(\d+(?:\.\d+)?)\s*cm\s*(?:/\s*(?:year|yr)|per\s+year)',text,re.I)
    matches += re.findall(r'(?:1|일)\s*년(?:에|간|\s*동안)[^.;\n]{0,12}?(\d+(?:\.\d+)?)\s*(?:cm|센티)',text,re.I)
    if matches:
        values={float(v) for v in matches}
        return next(iter(values)) if len(values)==1 else None
    m=re.search(r'(?:(?:1|일)\s*년\s*전|작년|one year ago)[^.;\n]{0,25}?(\d+(?:\.\d+)?)\s*cm[^\n]{0,70}?(?:현재|지금|today|now)[^.;\n]{0,20}?(\d+(?:\.\d+)?)\s*cm',text,re.I)
    return float(m[2])-float(m[1]) if m else None


def profile_observations(state):
    """Context-labeled family pattern and actual longitudinal records, only for these profiles."""
    from nova_agent.matching import _scoped
    key=(id(state),state.demographics.age,state.chief_complaint,tuple(t.result or '' for t in state.performed_actions))
    return list(_scoped('profile_observations',key,lambda: _profile_observations(state)))


def _profile_observations(state):
    from nova_agent.clinical_assertions import normalize_exam_notation
    from nova_agent.evidence_scope import patient_evidence_text
    from nova_agent.matching import _strip_negated_spans
    raw=[state.chief_complaint,*[t.result or '' for t in state.performed_actions]]
    original='; '.join(raw)
    findings=[]
    age=state.demographics.age
    # A single annual velocity is not a diagnosis and cannot identify pubertal status.
    velocity=growth_velocity(original)
    if velocity is None:
        # A quantitative answer inherits the explicitly asked ONE-YEAR interval,
        # not an interval guessed from an undated height or an unrelated question.
        for turn in state.performed_actions:
            if turn.action_type!='ASK' or not re.search(r'(?:1|일)\s*년\s*(?:동안|간)|past year|over (?:one|1) year',turn.content,re.I):continue
            projected=patient_evidence_text(turn.result or '',allow_historical=False)
            m=re.fullmatch(r'\s*(\d+(?:\.\d+)?)\s*cm(?:\s*(?:자랐어요|컸어요|grew))?[.!\s]*',projected,re.I)
            if m:velocity=float(m[1]);break
    if age is not None and 3<=age<12 and velocity is not None:
        if 4<=velocity<=7:findings.append('preserved prepubertal growth velocity')
        elif 0<=velocity<4:findings.append('reduced linear growth velocity')
    parts=re.split(r'[;\n]|(?<=[.!?])\s+',normalize_exam_notation(original))
    # A reply to a question about the parents' puberty is about the parents even
    # when it does not repeat the relation ("중학교 때까지 작았고 고등학교 때 컸대요").
    parental_replies={(t.result or '').casefold() for t in state.performed_actions
                      if t.action_type=='ASK' and re.search(_RELATION,t.content or '',re.I)
                      and re.search(r'사춘기|puberty|성장|컸|자랐',t.content or '',re.I)}
    for part in parts:
        lowered=part.casefold()
        negated=re.search(r'\bnot\b|\bno\b|않|없',lowered)
        if re.search(_RELATION,lowered) or lowered in parental_replies or any(lowered and lowered in r for r in parental_replies):
            if re.search(_LATE_BLOOMER,lowered) and not negated:
                findings.append('family delayed puberty')
            # Short only as a child, then a late spurt, is the late-bloomer pattern, not a short adult parent.
            childhood=re.search(r'어릴\s*때|어렸을\s*때|초등학교|중학교|as a child|in childhood|growing up',lowered)
            if (re.search(r'(?:parents?|mother|father|mom|dad)[^.]{0,20}(?:are|is|were|was)?\s*short\b|(?:부모|어머니|아버지|엄마|아빠)[^.]{0,15}키[^.]{0,6}작',lowered)
                    and not negated and not childhood):
                findings.append('short parental stature')
        # A clearly supplied previous bone-age report is evidence of that report,
        # not a performed test in this encounter or a hormone confirmation.
        if re.search(r'(?:report|document|supplied|기록|제공|보고)',lowered) and re.search(r'delayed bone age|bone age[^.]{0,20}delay|골연령\s*지연',lowered) and not re.search(r'not|no\b|않|없',lowered):
            findings.append('documented delayed bone age')
    return list(dict.fromkeys(findings))


def profile_problems(entry, state, support=None):
    from nova_agent.matching import feature_present_with_aliases
    current=state.all_findings_text(include_context=False,include_family=False)
    if entry['category']=='sedative':
        from nova_agent.evidence_scope import patient_evidence_text
        from nova_agent.clinical_concepts import canonical_findings_for
        for text in state.medication_text:
            projected=patient_evidence_text(text,allow_historical=False)
            if projected:current += [projected,*canonical_findings_for(projected)]
    context=state.all_findings_text(include_context=True,include_family=False)
    observations=profile_observations(state)
    features=[f for f in entry['typical_features'] if f in observations or feature_present_with_aliases(f,current+observations,scrub_negated_spans=True)]
    if entry['category']=='sedative':
        if not feature_present_with_aliases('sedative use',context,scrub_negated_spans=True):return ['sedative_exposure_missing']
        if 'sedative use' not in features:features.append('sedative use')
    requirement=entry['support_requirements'];problems=[]
    biochemical=entry['id']=='onto::tier2:hyperthyroidism' and thyroid_function_supported(state)
    if not biochemical and len(set(features))<requirement['minimum_positive_features']:problems.append('insufficient_independent_current_features')
    if not biochemical and not set(features).intersection(requirement['anchor_any']):problems.append('discriminating_context_missing')
    if entry['category']=='growth':
        if 'short stature' not in features:problems.append('patient_growth_concern_missing')
        if entry['id'].endswith(('constitutional_growth_delay','familial_short_stature')) and 'preserved prepubertal growth velocity' not in features:problems.append('longitudinal_growth_not_supported')
        if state.demographics.age is None or state.demographics.age>=18:problems.append('pediatric_context_missing')
    if entry['category']=='thyroid':
        # Only explicit supplied opposing functional results; no reference cutoff
        # or normal test result is inferred from missing observations.
        objective='; '.join(state.objective_findings_text())
        if re.search(r'(?:tsh[^;]{0,20}(?:high|elevated|상승)|(?:high|elevated)\s+tsh)',objective,re.I) and re.search(r'(?:free\s*t4|ft4)[^;]{0,15}(?:low|낮|감소)',objective,re.I):
            problems.append('opposing_supplied_thyroid_function')
    return problems


def thyroid_function_supported(state):
    """Preserve the existing explicit biochemical finding, not a planned/guessed test.

    This identifies the broader hormone-excess syndrome, not its Graves cause.
    Both current supplied directions must be explicit; no reference range is guessed.
    """
    from nova_agent.matching import feature_present_with_aliases
    current=state.objective_findings_text()
    def present(phrase):return feature_present_with_aliases(phrase,current,scrub_negated_spans=True,strict=True)
    return present('suppressed TSH') and present('raised free T4') and not (
        present('elevated TSH') or present('low free T4'))
