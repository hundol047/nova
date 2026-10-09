#!/usr/bin/env python3
"""Round U follow-up: run the SAME evaluation commands against a pinned checkout and record each execution.

Every step runs with cwd=<checkout> (that checkout's own evaluators, labels, scorer and simulator) under
NOVA_LLM_PROVIDER=mock, NOVA_COMPETITION_RETRIEVAL=1, PYTHONDONTWRITEBYTECODE=1. Per step it records the
command, branch, HEAD, tracked runtime hashes before/after, environment, UTC start/end, exit code, the log
SHA256 and the SHA256 of each copied result artifact. Nothing here edits a case, label, denominator, scorer or
simulator response. A fixture that is not present in the checkout (a new frozen set) is passed by absolute
path to the checkout's own evaluate_round_s.py.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ENV = {'NOVA_LLM_PROVIDER': 'mock', 'NOVA_COMPETITION_RETRIEVAL': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
FROZEN = [  # (name, fixture, manifest or None, evaluator)
    ('round_r', 'frozen_validation_round_r.json', 'frozen_validation_round_r_manifest.json', 'evaluate_round_r'),
    ('acceptance_regression', 'acceptance_regressions_round_r.json', None, 'evaluate_round_r'),
    ('round_s', 'frozen_validation_round_s.json', 'frozen_validation_round_s_manifest.json', 'evaluate_round_s'),
    ('round_t_development', 'frozen_validation_round_t.json', 'frozen_validation_round_t_manifest.json', 'evaluate_round_s'),
    ('t_confirmation', 'frozen_validation_round_t_confirmation.json', 'frozen_validation_round_t_confirmation_manifest.json', 'evaluate_round_s'),
    ('t_probe', 'frozen_validation_round_t_final_probe.json', 'frozen_validation_round_t_final_probe_manifest.json', 'evaluate_round_s'),
    ('t_postfreeze', 'frozen_validation_round_t_postfreeze.json', 'frozen_validation_round_t_postfreeze_manifest.json', 'evaluate_round_s'),
    ('u20', 'frozen_validation_round_u.json', 'frozen_validation_round_u_manifest.json', 'evaluate_round_s'),
    ('u12', 'frozen_validation_round_u_confirmation.json', 'frozen_validation_round_u_confirmation_manifest.json', 'evaluate_round_s'),
    ('u10', 'frozen_validation_round_u_final.json', 'frozen_validation_round_u_final_manifest.json', 'evaluate_round_s'),
    ('closing_u8', 'frozen_validation_round_u_closing.json', 'frozen_validation_round_u_closing_manifest.json', 'evaluate_round_s'),
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def runtime_hashes(checkout):
    names = subprocess.check_output(['git', 'ls-files', 'nova_agent', 'competition'], cwd=checkout, text=True).split()
    return {n: sha(Path(checkout) / n) for n in sorted(names) if Path(n).suffix in {'.py', '.json', '.md'}}


def steps(checkout, out, extra_fixtures):
    py = sys.executable
    s = [
        ('pytest', [py, '-m', 'pytest', 'tests', '-q', '-p', 'no:cacheprovider', '--junitxml', f'{out}/pytest.xml'], []),
        ('prelim', [py, 'scripts/evaluate_preliminary_benchmark.py', '--workers', '2', '--gate', '--output', f'{out}/prelim.json'], []),
        ('prelim_exam_rejection', [py, 'scripts/evaluate_preliminary_benchmark.py', '--workers', '2', '--exam-rejection',
                                   '--output', f'{out}/prelim_exam_rejection.json'], []),
        ('prelim_unscripted_unknown', [py, 'scripts/evaluate_preliminary_benchmark.py', '--workers', '2', '--unscripted-unknown',
                                       '--output', f'{out}/prelim_unscripted_unknown.json'], []),
        ('round_p', [py, 'evaluation/validation_benchmark_round_p.py', '--output', f'{out}/round_p.json'], []),
        ('round_q', [py, 'evaluation/dev_benchmark_round_q.py', '--output', f'{out}/round_q.json'], []),
        ('regressions', [py, 'scripts/evaluate_pre_guide_regressions.py'], [('artifacts/round_m/final_regressions.json', 'regressions.json')]),
        ('round_m', [py, 'scripts/evaluate_round_m_final.py'], [('artifacts/round_m/final_summary.json', 'round_m_final_summary.json'),
                                                                ('artifacts/round_m/failure_analysis.json', 'round_m_failure_analysis.json'),
                                                                ('artifacts/round_m/final/traces.tar.xz', 'round_m_traces.tar.xz')]),
        ('retrieval_stages', [py, 'scripts/audit_round_u_retrieval.py', '--checkout', checkout, '--output', f'{out}/retrieval_stages.json'], []),
        ('retrieval_benchmark', [py, 'scripts/benchmark_competition_retrieval.py'], []),
        ('routing', [py, 'scripts/benchmark_chief_complaint_routing.py'], []),
        ('specificity', [py, 'scripts/audit_feature_match_specificity.py'], []),
        ('leakage', [py, 'scripts/check_eval_leakage.py'], []),
        ('adversarial', [py, '-m', 'evaluation.adversarial'], []),
        ('failure_analysis', [py, '-m', 'evaluation.failure_analysis'], []),
        ('assertion_contrasts', [py, 'scripts/reproduce_round_t_assertions.py'], []),
    ]
    for name, fixture, manifest, evaluator in FROZEN:
        cmd = [py, f'scripts/{evaluator}.py', '--checkout', checkout, '--cases', f'evaluation/{fixture}', '--output', f'{out}/{name}']
        if manifest:
            cmd += ['--freeze', f'evaluation/{manifest}']
        s.append((name, cmd, []))
    for name, fixture, manifest in extra_fixtures:
        s.append((name, [py, 'scripts/evaluate_round_s.py', '--checkout', checkout, '--cases', fixture, '--freeze', manifest,
                         '--output', f'{out}/{name}'], []))
    return s


def run_step(checkout, out, step, before):
    name, cmd, copies = step
    log = Path(out) / f'{name}.log'
    env = dict(os.environ, **ENV)
    env.pop('NOVA_REGRESSION_OUTPUT', None)
    if name == 'pytest':
        # The unit/regression suite pins its own configuration; exporting the evaluation-mode switch makes 15
        # config-default tests fail on baseline and final alike (measured). Run it under the default environment.
        env.pop('NOVA_COMPETITION_RETRIEVAL', None)
    start = datetime.now(timezone.utc).isoformat()
    with open(log, 'wb') as fh:
        code = subprocess.call(cmd, cwd=checkout, env=env, stdout=fh, stderr=subprocess.STDOUT)
    end = datetime.now(timezone.utc).isoformat()
    artifacts = {}
    for src, dst in copies:
        if (Path(checkout) / src).exists():
            shutil.copyfile(Path(checkout) / src, Path(out) / dst)
    for p in sorted(Path(out).glob(f'{name}*')):
        if p.is_file() and p.suffix in {'.json', '.xml'}:
            artifacts[p.name] = sha(p)
    if (Path(out) / name).is_dir() and (Path(out) / name / 'summary.json').exists():
        artifacts[f'{name}/summary.json'] = sha(Path(out) / name / 'summary.json')
    for _, dst in copies:
        if (Path(out) / dst).exists():
            artifacts[dst] = sha(Path(out) / dst)
    rec = dict(step=name, command=cmd, cwd=checkout, environment={k: env.get(k) for k in ENV}, started_utc=start, finished_utc=end, exit_code=code,
               runtime_unchanged=runtime_hashes(checkout) == before, log_sha256=sha(log), artifacts=artifacts)
    (Path(out) / f'{name}.execution.json').write_text(json.dumps(rec, indent=1) + '\n')
    tail = log.read_text(errors='replace').strip().splitlines()[-1:] or ['']
    print(f'[{end}] {name}: exit={code} {tail[0][:160]}', flush=True)
    return rec


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--checkout', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--only', help='comma-separated step names')
    p.add_argument('--skip', default='', help='comma-separated step names')
    p.add_argument('--extra', action='append', default=[], help='name=fixture.json:manifest.json (absolute paths)')
    p.add_argument('--parallel', type=int, default=2)
    a = p.parse_args()
    checkout = str(Path(a.checkout).resolve())
    out = str(Path(a.output).resolve())
    Path(out).mkdir(parents=True, exist_ok=True)
    extra = []
    for item in a.extra:
        name, rest = item.split('=', 1)
        fixture, manifest = rest.split(':', 1)
        extra.append((name, fixture, manifest))
    todo = steps(checkout, out, extra)
    if a.only:
        todo = [s for s in todo if s[0] in a.only.split(',')]
    todo = [s for s in todo if s[0] not in a.skip.split(',')]
    before = runtime_hashes(checkout)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=checkout, text=True).strip()
    branch = subprocess.run(['git', 'branch', '--show-current'], cwd=checkout, text=True, capture_output=True).stdout.strip()
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.parallel) as pool:
        records = list(pool.map(lambda s: run_step(checkout, out, s, before), todo))
    index_path = Path(out) / 'executions.json'
    index = json.loads(index_path.read_text()) if index_path.exists() else {'steps': {}}
    index.update(head=head, branch=branch or '(detached)', runtime_sha256=before,
                 runtime_aggregate_sha256=hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest())
    index['steps'].update({r['step']: {k: r[k] for k in ('exit_code', 'started_utc', 'finished_utc', 'runtime_unchanged', 'log_sha256')}
                           for r in records})
    index_path.write_text(json.dumps(index, indent=1) + '\n')


if __name__ == '__main__':
    main()
