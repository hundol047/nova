"""One SCRIPTED control-flow comparison; not a diagnostic accuracy benchmark.

Same synthetic patient and legacy-compatible Doctor answer, two controllers.
The designated model, official scoring, real tokens, latency and money are NOT
measured. Tests separately validate the new interleaved planner contract.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.append(str(ROOT / 'tests'))
from test_adaptive_encounter import Scenario, ACTIONS, proposal
from test_official_sdk_adapter import FakeClient
from competition.nova_sdk_adapter import OfficialEncounter, COMMUNICATION_CATEGORIES
from competition.adaptive_encounter import AdaptiveEncounter


class CompatibleScenario(Scenario):
    def respond(self, system, content):
        if '"actions"' in system or '"questions"' in system:
            asked = {text for _, text, _ in self.events}
            remaining = [a for a in ACTIONS if a['text'] not in asked]
            return json.dumps({'actions': remaining,
                'questions': [a['text'] for a in remaining if a['kind'] == 'SAY'],
                'exams': [a['text'] for a in remaining if a['kind'] == 'EXAM'],
                'ready': not remaining}, ensure_ascii=False)
        p = proposal()
        # Both controllers see the same literal patient quote, not new-only IDs.
        p['evidence'] = ['오늘부터 소변을 볼 때 따갑습니다.']
        p['plan']['tests'][0]['evidence'] = p['evidence']
        p['plan']['disposition']['evidence'] = p['evidence']
        return json.dumps(p, ensure_ascii=False)


def compare():
    rows = []
    for cls in (OfficialEncounter, AdaptiveEncounter):
        server = CompatibleScenario()
        encounter = cls(FakeClient(server), {}, sleep=lambda _: None, log=lambda _: None)
        encounter.run()
        spoken = [t.text for t in encounter.turns if t.category in COMMUNICATION_CATEGORIES]
        rows.append({'controller': cls.__name__, 'turns': server.turns,
            'scripted_doctor_requests': server.chat_calls, 'submitted_primary': server.diagnosis,
            'exam_count': sum(t.kind == 'EXAM' for t in encounter.turns),
            'supplied_followup_retained': '2일 내' in server.record['P']['follow_up'],
            'supplied_followup_spoken': any('2일 내' in t for t in spoken),
            'action_length_violations': sum(len(t.text) > 30 for t in encounter.turns),
            'diagnostic_accuracy': 'NOT MEASURED', 'actual_record': server.record})
    return {'scope': __doc__, 'results': rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    report = compare()
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps([{k: v for k, v in row.items() if k != 'actual_record'} for row in report['results']], ensure_ascii=False))
