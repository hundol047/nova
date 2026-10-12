"""Fixed synthetic observation replay; LOCAL RUBRIC PROXY — NOT OFFICIAL SCORE.

No network, credentials, private-case imports or medical adjudication. Supplied
observations are replayed directly; this does not measure real interview coverage.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / 'submission'))


class ReplayClient:
    timeout = 240

    def __init__(self):
        self.said = []

    def say(self, text, request_id=None):
        self.said.append(text)
        return {'content': '알겠습니다.', 'turn': len(self.said), 'turns_remaining': 50-len(self.said)}


FAMILIES = {
    'graves': ('graves', '그레이브스'),
    'sedative': ('sedative-hypnotic use disorder', '수면제 사용장애', '수면제 의존'),
    'growth': ('constitutional', '체질성 성장'),
    'familial_growth': ('familial short', '가족성 저신장'),
    'growth_hormone': ('growth hormone deficiency', '성장호르몬 결핍'),
    'medication_sleep': ('medication-related', '약물 관련', '약물 유발'),
    'meningitis': ('meningitis', '수막염'),
    'pneumonia': ('pneumonia', '폐렴'),
}


def run():
    from competition.nova_sdk_adapter import OfficialEncounter, Turn
    from competition.adapter import NovaCompetitionAgent
    from nova_agent.orchestrator import DoctorAgent
    from nova_agent.llm_client import MockLLMClient
    path = ROOT/'evaluation/rubric_proxy_cases.json'
    rows = []
    for case in json.loads(path.read_text(encoding='utf-8'))['cases']:
        started = time.monotonic()
        client = ReplayClient()
        e = OfficialEncounter(client, {}, sleep=lambda _: None, log=lambda _: None)
        e.opening, e.vitals = case['opening'], 'BP 118/72, HR 82, RR 16, Temp 36.7, SpO2 98%'
        e.engine = NovaCompetitionAgent(DoctorAgent(llm_client=MockLLMClient()), preliminary=True)
        e.engine.act({'case_id': case['id'], 'observation_type': 'initial', 'chief_complaint': e.opening,
                      'demographics': {'age':case['age']}, 'vital_signs':e.vitals})
        e.pstate = e.engine.state(case['id'])
        # Source facts supplied by the fixture; no diagnosis label is given to the engine.
        e.pstate.record_ask('associated_symptoms', '어떤 증상이 있나요?', case['history'])
        e.pstate.record_exam('replayed_exam', case['exam'])
        e.turns = [Turn('SAY', '어떤 증상이 있나요?', case['history'], 'associated_symptoms', 1),
                   Turn('EXAM', '관련 진찰을 하겠습니다', case['exam'], 'replayed_exam', 2)]
        advisory = {'primary_diagnosis':case['doctor_primary'], 'evidence':[case['opening'],case['history'],case['exam']]}
        e.followup_plan = {'differential':[{'name':case['doctor_primary']}], 'evidence':[case['history']]}
        if hasattr(e, 'remember_advisory'):
            e.remember_advisory(advisory, 'followup')
        e.final_consult = {} if case['fail_final'] else advisory
        ddx, final = e._engine_final()
        e._accepted_primary = e._validated_primary(ddx, final)
        e._diagnosis_checked = True
        e._explain(ddx, final)
        note, diagnosis = e.official_record(ddx, final)
        expected = case['expected_family']
        topic_patterns={'graves':r'TSH|갑상선|갑상샘','sedative':r'복약|용량|복용|진정','growth':r'성장|골연령',
                        'familial_growth':r'성장|부모','growth_hormone':r'IGF|내분비|성장','medication_sleep':r'복약|용량|복용|진정',
                        'meningitis':r'요추천자|뇌척수|CSF|혈액','pneumonia':r'흉부|X-ray|폐'}
        topic_pattern=topic_patterns.get(expected)
        match = any(w in diagnosis.lower() for w in FAMILIES.get(expected, ()))
        if expected == 'unknown':
            match = not e._accepted_primary and not any(w in diagnosis.lower() for family in ('graves','meningitis','pneumonia','growth_hormone') for w in FAMILIES[family])
        urgent = e._urgent(ddx, final)
        plan = note['P']
        rows.append({'id':case['id'],'diagnosis':diagnosis,'reference_compatible':match,
                     'doctor_accepted':bool(e._accepted_primary),'urgency_matches':urgent==case['urgent'],
                     'test_plan_present':bool(plan['tests']), 'plan_topic_compatible_proxy':bool(__import__('re').search(topic_pattern,plan['tests'],__import__('re').I)) if topic_pattern else None, 'followup_has_interval':bool(__import__('re').search(r'\d+\s*(?:일|주|개월|day|week|month)',plan['follow_up'])),
                     'precautions_present':any(w in ' '.join(plan.values()) for w in ('즉시','응급','악화','재평가')),
                     'communication_turns':len(client.said),'explanation_present':bool(client.said),
                     'communication':client.said, 'plan':plan,
                     'objective_tests_empty':note['O']['tests']=='', 'seconds':time.monotonic()-started})
    n=len(rows)
    metrics={'cases':n,'reference_compatible':sum(r['reference_compatible'] for r in rows),
             'urgency_matches':sum(r['urgency_matches'] for r in rows),
             'test_plan_present':sum(r['test_plan_present'] for r in rows),
             'plan_topic_compatible_proxy':sum(r['plan_topic_compatible_proxy'] is True for r in rows),
             'plan_topic_scored_cases':sum(r['plan_topic_compatible_proxy'] is not None for r in rows),
             'followup_has_interval':sum(r['followup_has_interval'] for r in rows),
             'precautions_present':sum(r['precautions_present'] for r in rows),
             'explanation_present':sum(r['explanation_present'] for r in rows),
             'mean_closing_turns':sum(r['communication_turns'] for r in rows)/n,
             'unperformed_test_results':sum(not r['objective_tests_empty'] for r in rows)}
    return {'label':'LOCAL RUBRIC PROXY — NOT OFFICIAL SCORE','fixture_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'information_gathering':'Provided observations replayed; interview coverage measured in separate fake-SDK regressions.',
            'diagnostic_reasoning':'Reference-family agreement; no clinician adjudication.',
            'tests_followup':'Presence/interval/precaution lexical checks, not medical quality scores.',
            'safety':'Expected urgency engineering assertions.', 'communication':'Actual fixture SAYs and submitted plan.',
            'efficiency':'Closing turns only; no real-model token or latency claims.', 'metrics':metrics,'cases':rows}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    result=run();Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result['metrics']))
