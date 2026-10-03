"""Frozen synthetic unit-equivalence dialogues; never a clinical accuracy estimate."""
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
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    folder = ROOT / 'evaluation/hard_units_v1'
    raw = (folder / 'cases.json').read_bytes()
    manifest = json.loads((folder / 'manifest.json').read_text())
    assert hashlib.sha256(raw).hexdigest() == manifest['sha256'], 'Frozen cases changed'
    sys.path.insert(0, str(args.repo.resolve()))
    os.environ['NOVA_LLM_PROVIDER'] = 'mock'
    from evaluation.cases import SyntheticCase
    from evaluation.simulator import run_case
    from evaluation.benchmark import compute_summary
    from nova_agent.orchestrator import DoctorAgent
    results = [run_case(DoctorAgent(), SyntheticCase(**c), capture_trajectory=True)
               for c in json.loads(raw)]
    output = dict(manifest=manifest, summary=compute_summary(results),
                  cases=[r.model_dump() for r in results])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2)+'\n')
    print(json.dumps(output['summary']))
