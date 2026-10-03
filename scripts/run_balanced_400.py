"""Frozen, source-balanced 200 easy + 200 hard synthetic replay; no training."""
import argparse
import gzip
import hashlib
import json
import multiprocessing
from collections import defaultdict, Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_large_simulation import initialize, execute_job, runtime_digest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/evaluation/balanced_400_2026_10_03')
    parser.add_argument('--seed', default='balanced400-v1')
    parser.add_argument('--exclude', type=Path)
    args = parser.parse_args()
    output = args.output
    if (output / 'completion.json').exists():
        raise ValueError('Use a fresh output directory')
    excluded = set()
    if args.exclude:
        excluded = {json.loads(line)['input_sha256'] for line in args.exclude.read_text().splitlines()}
    output.mkdir(parents=True, exist_ok=True)
    corpus = ROOT / 'research/simulation_50000_v1/cases.jsonl.gz'
    manifest = json.loads(corpus.with_name('manifest.json').read_text())
    digest = hashlib.sha256(corpus.read_bytes()).hexdigest()
    assert digest == manifest['corpus_sha256']
    pools = defaultdict(lambda: defaultdict(list))
    with gzip.open(corpus, 'rt') as stream:
        for line in stream:
            row = json.loads(line)
            if row['input_sha256'] not in excluded:
                pools[row['difficulty']][row['source_family']].append(row)
    selected = []
    for difficulty in ('low', 'high'):
        groups = pools[difficulty]
        for rows in groups.values():
            rows.sort(key=lambda r: hashlib.sha256((args.seed + ':' + r['id']).encode()).hexdigest())
        names = sorted(groups, key=lambda n: hashlib.sha256((args.seed + ':' + n).encode()).hexdigest())
        chosen = []
        index = 0
        while len(chosen) < 200:
            for name in names:
                if index < len(groups[name]):
                    chosen.append(groups[name][index])
                    if len(chosen) == 200:
                        break
            index += 1
        selected.extend(chosen)
    assert len({r['id'] for r in selected}) == 400
    assert len({r['input_sha256'] for r in selected}) == 400
    payload = ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in selected)
    metadata = dict(scope='SYNTHETIC_MOCK_DIALOGUES_NOT_CLINICAL_ACCURACY',
                    selection='200 per difficulty; deterministic round-robin source families; no prediction filtering',
                    seed=args.seed, excluded_inputs=len(excluded), corpus_sha256=digest, selected_sha256=hashlib.sha256(payload.encode()).hexdigest(),
                    runtime_sha256=runtime_digest(ROOT),
                    runtime_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                    runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    response_policy='mapped_unknown_missing', memoized=True, cases=400,
                    independent_test=False, clinical_validation=False, training=False,
                    limitation='Previously development-exposed synthetic source families and correlated variants; English scripted dialogues; not ICD-11-wide coverage.')
    (output / 'selected_cases.jsonl').write_text(payload)
    (output / 'run_manifest.json').write_text(json.dumps(metadata, indent=2) + '\n')
    jobs = [(i // 20, selected[i:i+20], str(output), metadata) for i in range(0, 400, 20)]
    start = time.monotonic()
    counters = Counter()
    with ProcessPoolExecutor(max_workers=4, mp_context=multiprocessing.get_context('spawn'),
                             initializer=initialize, initargs=(ROOT, True, 'mapped_unknown_missing')) as pool:
        for future in as_completed([pool.submit(execute_job, job) for job in jobs]):
            counters.update(future.result()['counts'])
            print(json.dumps(dict(completed=counters['cases'], total=400, elapsed=round(time.monotonic()-start, 1))), flush=True)
    assert runtime_digest(ROOT) == metadata['runtime_sha256']
    (output / 'completion.json').write_text(json.dumps(dict(run_metadata=metadata, counts=dict(counters),
        elapsed_seconds=time.monotonic()-start, completed=counters['cases']==400), indent=2) + '\n')
    from scripts.summarize_large_simulation import summarize, iter_results
    from evaluation.safety_metrics import safety_metrics
    summary = summarize(output)
    records = list(iter_results(output))
    extra = {}
    for difficulty in ('low', 'high'):
        rows = [r for r in records if r['difficulty'] == difficulty]
        results = [r['result'] for r in rows]
        scored = [r for r in results if r['scoring_expected']]
        extra[difficulty] = dict(cases=len(rows), source_families=len({r['source_family'] for r in rows}),
            diagnostic_groups=len({r['diagnostic_group'] for r in rows}),
            correct=sum(r['correct'] for r in results),
            scored_cases=len(scored), scored_correct=sum(r['correct'] for r in scored),
            safety=safety_metrics(results))
    (output / 'difficulty_safety.json').write_text(json.dumps(extra, indent=2) + '\n')
    print(json.dumps(extra, indent=2), flush=True)

if __name__ == '__main__':
    main()
