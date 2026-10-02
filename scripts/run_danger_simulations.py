"""Run unchanged hard reference or frozen new synthetic dialogues against a checkout."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, default=ROOT)
    p.add_argument('--suite', choices=['reference','validation'], required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    sys.path.insert(0, str(args.repo.resolve()))
    os.environ['NOVA_LLM_PROVIDER'] = 'mock'
    from evaluation.cases import SyntheticCase
    from evaluation.simulator import run_case
    from evaluation.benchmark import compute_summary
    from nova_agent.orchestrator import DoctorAgent
    if args.suite == 'reference':
        from evaluation.blind_cases_v11 import BLIND_CASES_V11
        from evaluation.blind_benchmark_v11 import _verify_frozen_hash
        _verify_frozen_hash()
        cases = BLIND_CASES_V11
    else:
        folder = ROOT / 'evaluation/danger_simulation_v2'
        raw = (folder / 'validation.json').read_bytes()
        manifest = json.loads((folder / 'manifest.json').read_text())
        if hashlib.sha256(raw).hexdigest() != manifest['sha256']:
            raise ValueError('Frozen fixture changed')
        cases = [SyntheticCase(**c) for c in json.loads(raw)]
    results = [run_case(DoctorAgent(), c, capture_trajectory=True) for c in cases]
    output = dict(scope='synthetic_mock_only', suite=args.suite,
                  summary=compute_summary(results), cases=[r.model_dump() for r in results])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2)+'\n')
    print(json.dumps(output['summary']))
