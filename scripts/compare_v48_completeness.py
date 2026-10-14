"""Scripted v47/v48 control comparison, NOT a score or clinical accuracy test.

The baseline controller is loaded from the fixed public v47 source commit.
Transport and clinical helpers are shared; this isolates controller behavior.
Unknown answers count as attempted domains, never as resolved findings.
"""
import json
from pathlib import Path
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.append(str(ROOT / 'tests'))
from test_adaptive_encounter import Scenario
from test_official_sdk_adapter import FakeClient
from competition.adaptive_encounter import AdaptiveEncounter
from competition.nova_sdk_adapter import COMMUNICATION_CATEGORIES
from nova_agent.clinical_interview import missing_foundation_topics, unresolved_history

BASE = '476e2e8c3597b7175bf20f403364e565de731a84'


def compare():
    source = subprocess.check_output(['git', 'show', BASE + ':competition/adaptive_encounter.py'], cwd=ROOT, text=True)
    baseline = types.ModuleType('competition.v47_baseline')
    exec(compile(source, 'v47_baseline.py', 'exec'), baseline.__dict__)
    results = []
    for version, cls in [('v47', baseline.AdaptiveEncounter), ('v48', AdaptiveEncounter)]:
        server = Scenario()
        encounter = cls(FakeClient(server), {}, sleep=lambda _: None, log=lambda _: None)
        encounter.run()
        results.append({'version': version, 'turns': server.turns, 'scripted_doctor_calls': server.chat_calls,
            'unattempted_foundation_domains': missing_foundation_topics(encounter.pstate),
            'unknown_or_insufficient_history': unresolved_history(encounter.pstate),
            'spoken_messages': [t.text for t in encounter.turns if t.category in COMMUNICATION_CATEGORIES],
            'exam_attempts': sum(t.kind == 'EXAM' for t in encounter.turns),
            'submitted_primary': server.diagnosis, 'completed': server.closed})
    return {'scope': __doc__, 'baseline_source': BASE, 'real_model_executed': False,
            'official_score_measured': False, 'results': results}


if __name__ == '__main__':
    report = compare()
    (ROOT / 'artifacts/releases/nova-v48-controller-comparison.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))
