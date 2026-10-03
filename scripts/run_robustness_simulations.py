#!/usr/bin/env python3
"""Replay frozen formatting variants with autonomous ASK/EXAM/TEST decisions."""
import argparse
from collections import defaultdict
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
    args = p.parse_args()
    folder = ROOT / 'evaluation/robustness_v1'
    fixture = folder / (args.split + '.json')
    metadata = json.loads((folder / 'manifest.json').read_text())['files'][fixture.name]
    if hashlib.sha256(fixture.read_bytes()).hexdigest() != metadata['sha256']:
        raise ValueError('Frozen fixture changed')
    sys.path.insert(0, str(args.repo.resolve()))
    os.environ['NOVA_LLM_PROVIDER'] = 'mock'
    from evaluation.cases import SyntheticCase
    from evaluation.simulator import run_case
    from nova_agent.orchestrator import DoctorAgent
    rows = []
    for entry in json.loads(fixture.read_text()):
        result = run_case(DoctorAgent(), SyntheticCase(**entry['case']))
        row = {k: getattr(result, k) for k in ('case_id', 'ground_truth', 'final_diagnosis',
               'correct', 'critical', 'critical_miss', 'turns')}
        row.update(family=entry['family'], variant=entry['variant'])
        rows.append(row)
    critical = [r for r in rows if r['critical']]
    families = defaultdict(list)
    for r in rows:
        families[r['family']].append(r)
    output = dict(scope='synthetic_mock_dialogue_robustness', split=args.split,
        fixture_sha256=metadata['sha256'], scenarios=len(rows), correct=sum(r['correct'] for r in rows),
        critical_total=len(critical), critical_correct=sum(r['correct'] for r in critical),
        source_families=len(families), families_all_variants_correct=sum(all(r['correct'] for r in v) for v in families.values()),
        rows=rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2)+'\n')
    print(json.dumps({k:v for k,v in output.items() if k != 'rows'}))


if __name__ == '__main__':
    main()
