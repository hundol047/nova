"""Compare direct/full-information/interactive reasoning with the fixed model."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.model_comparison import load_inputs, run_direct, run_agent, score_saved_predictions, sha
from nova_agent.config import get_config
from nova_agent.llm_client import CompetitionLLMClient
from scripts.run_large_simulation import runtime_digest


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--split', choices=['development', 'validation', 'holdout'], default='development')
    p.add_argument('--validate-only', action='store_true')
    p.add_argument('--limit', type=int, default=3,
                   help='Start with a bounded live smoke run; increase explicitly for frozen evaluation.')
    args = p.parse_args()
    cases, manifest = load_inputs(args.dataset)
    selected = [c for c in cases if c.split == args.split]
    if args.limit < 1:
        raise ValueError('limit must be positive')
    available = len(selected)
    selected = selected[:args.limit] if not args.validate_only else selected
    if not selected:
        raise ValueError('No cases in requested split')
    args.output.mkdir(parents=True, exist_ok=False)
    cfg = get_config()
    meta = {'dataset_manifest': manifest, 'split': args.split, 'cases': len(selected),
            'available_cases': available, 'limit': args.limit,
            'runtime_sha256': runtime_digest(ROOT),
            'runner_sha256': sha(Path(__file__).read_bytes()),
            'comparison_sha256': sha((ROOT / 'evaluation/model_comparison.py').read_bytes()),
            'model': cfg.competition_model, 'expected_revision': '4d7ae4984b7db7de8f8457170b3f1a419ee76d52',
            'server_revision_verified': False, 'temperature': cfg.llm_temperature,
            'max_tokens': cfg.llm_max_tokens, 'training': False,
            'clinical_validation': False, 'live_executed': False,
            'interactive_ready_cases': sum(c.interactive_reviewed for c in selected)}
    (args.output / 'manifest.json').write_text(json.dumps(meta, indent=2) + '\n')
    if args.validate_only:
        print(json.dumps({'validated_cases': len(selected), 'live_executed': False}))
        return
    if (cfg.llm_provider != 'competition' or cfg.competition_model != 'openai/gpt-oss-20b'
            or not os.environ.get('NOVA_COMPETITION_BASE_URL')):
        (args.output / 'blocked.json').write_text(json.dumps({
            'reason': 'Configure provider=competition, fixed model, and authorized endpoint explicitly; mock cannot measure this comparison.'}, indent=2))
        raise SystemExit('BLOCKED: fixed-model endpoint not configured; no accuracy reported')
    results = []
    with (args.output / 'predictions.jsonl').open('w') as out:
        for case in selected:
            for mode in ('direct', 'nova_full', 'nova_interactive'):
                client = CompetitionLLMClient()
                try:
                    result = run_direct(case, client) if mode == 'direct' else run_agent(case, client, mode == 'nova_interactive')
                except Exception as exc:
                    # Store no exception payload that might contain source text or credentials.
                    result = {'error': type(exc).__name__, 'successes': 0}
                result.update(case_id=case.case_id, mode=mode)
                results.append(result)
                out.write(json.dumps(result, ensure_ascii=False) + '\n'); out.flush()
    if runtime_digest(ROOT) != meta['runtime_sha256']:
        raise RuntimeError('Runtime changed during evaluation')
    summary = score_saved_predictions(args.dataset, results)
    (args.output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    meta['live_executed'] = any(r.get('successes', 0) for r in results)
    (args.output / 'manifest.json').write_text(json.dumps(meta, indent=2) + '\n')
    print(json.dumps({'cases': len(selected), 'live_executed': meta['live_executed']}))


if __name__ == '__main__':
    main()
