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

BASE = '618aecd68df1f6c94b04d10977347e49e00e37ad'
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
    baseline = types.ModuleType('competition.v49_baseline')
    exec(compile(source, 'v49_baseline.py', 'exec'), baseline.__dict__)
    old_contract = types.ModuleType('competition.v49_contract')
    contract_source = subprocess.check_output(['git','show', BASE+':competition/encounter_contract.py'], cwd=ROOT, text=True)
    exec(compile(contract_source, 'v49_contract.py', 'exec'), old_contract.__dict__)
    baseline.INTERVIEW_SYSTEM = old_contract.INTERVIEW_SYSTEM
    baseline.FINAL_SYSTEM = old_contract.FINAL_SYSTEM
    class Recorded(Scenario):
        input_chars = 0
        def respond(self, system, content):
            self.input_chars += len(system) + len(content)
            return super().respond(system, content)
    rows = []
    for index, opening in enumerate(OPENINGS, 1):
        for version, cls in [('v49',baseline.AdaptiveEncounter), ('v50',AdaptiveEncounter)]:
            p = proposal(); p.update(primary_diagnosis='원인 미상의 증상', short_name='원인 미상', evidence=['I0'])
            s = Recorded(actions=[], opening=opening, final=p)
            e = cls(FakeClient(s), {}, sleep=lambda _:None, log=lambda _:None)
            e.run()
            domains = coverage(e)
            rows.append({'case': 'invented-'+str(index), 'version':version,
                'turns':s.turns, 'doctor_calls':s.chat_calls,
                'collection_actions':sum(t.category not in COMMUNICATION_CATEGORIES for t in e.turns),
                'request_characters_not_tokens':s.input_chars,
                'question_count':sum(t.kind == 'SAY' and t.category not in COMMUNICATION_CATEGORIES for t in e.turns),
                'exams':sum(t.kind == 'EXAM' for t in e.turns),
                'spoken_turns':sum(t.category in COMMUNICATION_CATEGORIES for t in e.turns),
                'unasked_template_domains':[x['domain'] for x in domains if x['status']=='unasked'],
                'unresolved_template_domains':[x['domain'] for x in domains if x['status']=='unresolved'],
                'overlength_actions':sum(len(t.text)>30 for t in e.turns), 'completed':s.closed})
    return {'scope':__doc__, 'baseline_source':BASE,
        'limitations':'The baseline controller and its prompts come from v49; both versions share current clinical helpers. This is not a full archived-v49 comparison. Request characters are not tokens or actual model cost. Empty scripted planners and invented replies test control flow, not medical accuracy. The same fixed final plan is deliberately used across complaints and is not a clinical recommendation. Template counts are not rubric scores.',
        'real_model_executed':False, 'official_score_measured':False, 'results':rows}


if __name__ == '__main__':
    result=compare()
    (ROOT/'artifacts/releases/nova-v50-controller-comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps([{k:r[k] for k in ('case','version','turns','collection_actions','doctor_calls','exams')} for r in result['results']], ensure_ascii=False))
