#!/usr/bin/env python3
"""Evidence-only synthetic final-turn probes; not clinical diagnostic accuracy."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, default=ROOT)
    p.add_argument('--split', choices=['development', 'validation'], required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    folder = ROOT / 'evaluation/uncertainty_v1'
    file = folder / (a.split + '.json')
    manifest = json.loads((folder / 'manifest.json').read_text())
    digest = hashlib.sha256(file.read_bytes()).hexdigest()
    if digest != manifest['files'][file.name]['sha256']:
        raise ValueError('Frozen fixture changed')
    sys.path.insert(0, str(a.repo.resolve()))
    os.environ['NOVA_LLM_PROVIDER'] = 'mock'
    from nova_agent.orchestrator import DoctorAgent
    rows = []
    for case in json.loads(file.read_text()):
        agent = DoctorAgent()
        state = agent.new_case(case['id'], 'assessment', max_turns=15)
        state.turn_count = 14
        target = state.imaging if case['test_key'] in {'cxr', 'ct_abdomen'} else state.laboratory_tests
        target[case['test_key']] = case['report']
        state.completed_tests = [case['test_key']]
        action, _, _ = agent.decide(state)
        rows.append(dict(**case, actual=action.content,
                         correct=action.action_type == 'DIAGNOSE' and action.content == case['expected']))
    result = dict(scope=manifest['scope'], split=a.split, fixture_sha256=digest,
                  total=len(rows), correct=sum(r['correct'] for r in rows), rows=rows)
    a.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'rows'}))


if __name__ == '__main__':
    main()
