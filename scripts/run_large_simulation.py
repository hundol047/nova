"""Run/checkpoint every synthetic dialogue with an actual mock DoctorAgent loop."""
import argparse
from collections import defaultdict, Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import hashlib
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / 'research/simulation_50000_v1'
_agent = _case_class = _run_case = _cache_info = _resolve_response = None


def runtime_digest(repo):
    digest = hashlib.sha256()
    for directory in ('nova_agent', 'learning'):
        for path in sorted((repo / directory).rglob('*')):
            if path.is_file() and path.suffix in {'.py', '.json'} and '__pycache__' not in path.parts:
                digest.update(str(path.relative_to(repo)).encode())
                digest.update(path.read_bytes())
    return digest.hexdigest()


def initialize(repo, memoize, response_policy):
    global _agent, _case_class, _run_case, _cache_info, _resolve_response
    sys.path.insert(0, str(repo))
    os.environ['NOVA_LLM_PROVIDER'] = 'mock'
    if memoize:
        path = ROOT / 'evaluation/large_simulation/cache.py'
        spec = importlib.util.spec_from_file_location('nova_evaluation_cache', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _cache_info = module.install()
    from evaluation.cases import SyntheticCase
    from evaluation.simulator import run_case
    import evaluation.simulator as simulator
    from nova_agent.orchestrator import DoctorAgent
    import nova_agent
    from nova_agent.config import get_config
    if get_config().case_timeout_seconds is not None:
        raise ValueError('Wall-clock budgets would make cached and uncached cases incomparable')
    if not Path(nova_agent.__file__).resolve().is_relative_to(repo):
        raise ValueError('Wrong runtime checkout imported')
    if response_policy == 'mapped_unknown_missing':
        path = ROOT / 'evaluation/large_simulation/responses.py'
        spec = importlib.util.spec_from_file_location('nova_evaluation_responses', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _resolve_response = module.resolve
        simulator.PatientSimulator.respond = lambda self, action: _resolve_response(self.case, action.action_type, action.key)
    _agent, _case_class, _run_case = DoctorAgent(), SyntheticCase, run_case


def execute_job(job):
    index, rows, destination, metadata = job
    output = Path(destination) / f'part_{index:04d}.jsonl.gz'
    summary_path = output.with_suffix('.summary.json')
    if output.exists() and summary_path.exists():
        summary = json.loads(summary_path.read_text())
        if summary['run_metadata'] != metadata or summary['case_ids'] != [r['id'] for r in rows]:
            raise ValueError('Checkpoint provenance differs; use a new run directory')
        if summary['output_sha256'] != hashlib.sha256(output.read_bytes()).hexdigest():
            raise ValueError('Checkpoint hash mismatch')
        return summary
    start = time.monotonic()
    counters = Counter()
    temporary = output.with_suffix('.partial')
    with temporary.open('wb') as raw, gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as stream:
        for i, row in enumerate(rows):
            case = _case_class(**row['case'])
            result = _run_case(_agent, case, capture_trajectory=True).model_dump()
            # Retain exactly the scripted observation returned for each executed action.
            for turn in result['differential_trajectory']:
                action, key = turn['action'].split(':', 1)
                mapping = {'ASK': (case.answers, case.default_answer),
                           'EXAM': (case.exam_results, case.default_exam_result),
                           'TEST': (case.test_results, case.default_test_result)}
                turn['observation'] = (_resolve_response(case, action, key) if _resolve_response
                                       else mapping[action][0].get(key, mapping[action][1]) if action in mapping else '')
            record = dict(id=row['id'], input_sha256=row['input_sha256'], difficulty=row['difficulty'],
                          split=row['split'], source_family=row['source_family'],
                          diagnostic_group=row['diagnostic_group'], mutation=row['mutation'],
                          label_origin=row['label_origin'], clinical_validation_status='NOT_VERIFIED',
                          eligible_for_training=False, result=result)
            stream.write((json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n').encode())
            counters['cases'] += 1
            counters['correct'] += result['correct']
            counters['critical'] += result['critical']
            counters['critical_correct'] += result['critical'] and result['correct']
            counters['real_llm_calls'] += result['llm_call_count']
            if (i + 1) % 20 == 0:
                (Path(destination) / f'progress_{index:04d}.json').write_text(json.dumps(dict(
                    completed=i+1, total=len(rows), elapsed_seconds=time.monotonic()-start)))
    temporary.replace(output)
    summary = dict(part=index, counts=dict(counters), case_ids=[r['id'] for r in rows],
                   elapsed_seconds=time.monotonic()-start, run_metadata=metadata,
                   output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                   cache_stats=_cache_info() if _cache_info else {})
    summary_path.write_text(json.dumps(summary, indent=2) + '\n')
    (Path(destination) / f'progress_{index:04d}.json').unlink(missing_ok=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--split', choices=['development', 'validation', 'all'], default='all')
    parser.add_argument('--limit-per-family', type=int)
    parser.add_argument('--workers', type=int, default=6)
    parser.add_argument('--uncached', action='store_true')
    parser.add_argument('--response-policy', choices=['legacy', 'mapped_unknown_missing'], default='mapped_unknown_missing')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((CORPUS / 'manifest.json').read_text())
    corpus_hash = hashlib.sha256((CORPUS / 'cases.jsonl.gz').read_bytes()).hexdigest()
    if corpus_hash != manifest['corpus_sha256']:
        raise ValueError('Frozen corpus changed')
    groups = defaultdict(list)
    with gzip.open(CORPUS / 'cases.jsonl.gz', 'rt') as stream:
        for line in stream:
            row = json.loads(line)
            if args.split != 'all' and row['split'] != args.split:
                continue
            family = (row['difficulty'], row['source_family'])
            if args.limit_per_family and len(groups[family]) >= args.limit_per_family:
                continue
            groups[family].append(row)
    metadata = dict(scope='SYNTHETIC_MOCK_DIALOGUES_NOT_CLINICAL_ACCURACY',
                    corpus_sha256=corpus_hash, runtime_sha256=runtime_digest(args.repo),
                    runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    cache_sha256=hashlib.sha256((ROOT / 'evaluation/large_simulation/cache.py').read_bytes()).hexdigest(),
                    response_adapter_sha256=hashlib.sha256((ROOT / 'evaluation/large_simulation/responses.py').read_bytes()).hexdigest(),
                    response_policy=args.response_policy,
                    simulator_sha256=hashlib.sha256((args.repo / 'evaluation/simulator.py').read_bytes()).hexdigest(),
                    runtime_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=args.repo, text=True).strip(),
                    split=args.split, limit_per_family=args.limit_per_family, memoized=not args.uncached,
                    cases=sum(map(len, groups.values())), families=len(groups), real_llm_provider=False)
    previous = args.output / 'run_manifest.json'
    if previous.exists() and json.loads(previous.read_text()) != metadata:
        raise ValueError('Run directory already has different provenance')
    previous.write_text(json.dumps(metadata, indent=2) + '\n')
    jobs = [(i, rows, str(args.output), metadata) for i, (_, rows) in enumerate(sorted(groups.items()))]
    start = time.monotonic()
    counters = Counter()
    with ProcessPoolExecutor(max_workers=args.workers, mp_context=multiprocessing.get_context('spawn'),
                             initializer=initialize, initargs=(args.repo.resolve(), not args.uncached, args.response_policy)) as pool:
        futures = [pool.submit(execute_job, job) for job in jobs]
        for future in as_completed(futures):
            summary = future.result()
            counters.update(summary['counts'])
            print(json.dumps(dict(completed=counters['cases'], total=metadata['cases'],
                                  elapsed_seconds=round(time.monotonic()-start, 1))), flush=True)
    if runtime_digest(args.repo) != metadata['runtime_sha256']:
        raise RuntimeError('Runtime changed during execution; do not combine these results')
    report = dict(run_metadata=metadata, counts=dict(counters), elapsed_seconds=time.monotonic()-start,
                  completed=counters['cases'] == metadata['cases'])
    (args.output / 'completion.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
