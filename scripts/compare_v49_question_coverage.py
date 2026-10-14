"""Invented-patient control comparison. No live model, official cases or scoring."""
import json
from pathlib import Path
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.append(str(ROOT / 'tests'))
from test_adaptive_encounter import Scenario, proposal
from test_official_sdk_adapter import FakeClient
from competition.adaptive_encounter import AdaptiveEncounter
from competition.interview_coverage import coverage
from competition.nova_sdk_adapter import COMMUNICATION_CATEGORIES

BASE = '735d185c1510a7b7f76938a65788e22800195176'
OPENINGS = [
    '서른 살 여자입니다. 오늘 소변 볼 때 따가워요.',
    '마흔 살 남자입니다. 사흘째 기침이 나요.',
    '스물다섯 살 여자입니다. 이틀째 배가 아파요.',
    '마흔 살 여자입니다. 한 달간 가끔 두통이 생겨요.',
    '마흔 살 남자입니다. 석 달간 체중이 줄었어요.',
    '서른 살 남자입니다. 한 달간 잠을 못 자요.',
    '일곱 살 남자아이입니다. 키가 또래보다 작아요.',
    '서른 살 남자입니다. 며칠간 귀가 먹먹해요.',
]


def compare():
    source = subprocess.check_output(['git','show', BASE+':competition/adaptive_encounter.py'], cwd=ROOT, text=True)
    baseline = types.ModuleType('competition.v48_baseline')
    exec(compile(source, 'v48_baseline.py', 'exec'), baseline.__dict__)
    rows = []
    for index, opening in enumerate(OPENINGS, 1):
        for version, cls in [('v48',baseline.AdaptiveEncounter), ('v49',AdaptiveEncounter)]:
            p = proposal(); p.update(primary_diagnosis='원인 미상의 증상', short_name='원인 미상', evidence=['I0'])
            s = Scenario(actions=[], opening=opening, final=p)
            e = cls(FakeClient(s), {}, sleep=lambda _:None, log=lambda _:None)
            e.run()
            domains = coverage(e)
            rows.append({'case': 'invented-'+str(index), 'version':version,
                'turns':s.turns, 'doctor_calls':s.chat_calls,
                'question_count':sum(t.kind == 'SAY' and t.category not in COMMUNICATION_CATEGORIES for t in e.turns),
                'exams':sum(t.kind == 'EXAM' for t in e.turns),
                'spoken_turns':sum(t.category in COMMUNICATION_CATEGORIES for t in e.turns),
                'unasked_template_domains':[x['domain'] for x in domains if x['status']=='unasked'],
                'unresolved_template_domains':[x['domain'] for x in domains if x['status']=='unresolved'],
                'overlength_actions':sum(len(t.text)>30 for t in e.turns), 'completed':s.closed})
    return {'scope':__doc__, 'baseline_source':BASE,
        'limitations':'Only the baseline controller comes from v48; both versions share current clinical helpers, including the child surgery filter fix. This is not a full archived-v48 comparison. Empty scripted planners and invented replies test control flow, not medical accuracy. The same fixed final plan is deliberately used across complaints and is not a clinical recommendation. Template counts are not rubric scores.',
        'real_model_executed':False, 'official_score_measured':False, 'results':rows}


if __name__ == '__main__':
    result=compare()
    (ROOT/'artifacts/releases/nova-v49-controller-comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps([{k:r[k] for k in ('case','version','turns','doctor_calls','exams')} for r in result['results']], ensure_ascii=False))
