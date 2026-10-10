#!/usr/bin/env python3
"""Round V: disposition-contract FP/FN and simulator-default dependence, baseline vs final (same-condition runs).

Disposition: every frozen fixture case with a `round_s_expect.urgent` contract; FP = urgent plan where the contract
says not urgent, FN = no urgent plan where it says urgent. Read from the evaluate_round_s per-case rows.

Default-"No" dependence: preliminary cases correct under the default simulator (unscripted questions answered with
the case's default, usually "No.") but NOT correct when unscripted questions are answered "I don't know"
(`--unscripted-unknown`). Read from the prelim and prelim_unscripted_unknown outputs of the same run directory.

    python scripts/summarize_round_v.py --before <dir> --after <dir> [--extra name=before_dir:after_dir] --output x.json
"""
import argparse
import json
from pathlib import Path

DISPOSITION_SETS = ('round_s', 'round_t_development', 't_confirmation', 't_probe', 't_postfreeze', 'u20', 'u12', 'u10',
                    'closing_u8', 'followup_new', 'followup_closing', 'round_v', 'round_v_closing')


def disposition(run_dir: Path):
    return {name: disposition_single(run_dir / name) for name in DISPOSITION_SETS
            if (run_dir / name / 'summary.json').exists()}


_FIXTURES = {}


def _fixture_expect(case_id):
    if not _FIXTURES:
        for p in Path(__file__).resolve().parents[1].glob('evaluation/*.json'):
            try:
                rows = json.loads(p.read_text())
            except ValueError:
                continue
            for r in rows if isinstance(rows, list) else []:
                if isinstance(r, dict) and 'case_id' in r:
                    _FIXTURES[r['case_id']] = r.get('round_s_expect') or {}
    return _FIXTURES.get(case_id, {})


def _prelim_rows(path: Path):
    rows = {}
    for group in json.loads(path.read_text())['cases'].values():
        for r in group:
            rows[r['case_id']] = r
    return rows


def default_no_dependence(run_dir: Path):
    default, unknown = run_dir / 'prelim.json', run_dir / 'prelim_unscripted_unknown.json'
    if not (default.exists() and unknown.exists()):
        return None
    a, b = _prelim_rows(default), _prelim_rows(unknown)
    scored = [c for c, r in a.items() if r['scored']]
    dependent = sorted(c for c in scored if a[c]['top1'] and not b.get(c, {}).get('top1'))
    return dict(scored=len(scored), correct_default=sum(1 for c in scored if a[c]['top1']),
                correct_unscripted_unknown=sum(1 for c in scored if b.get(c, {}).get('top1')),
                default_no_dependent=len(dependent), cases=dependent)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--before', required=True)
    p.add_argument('--after', required=True)
    p.add_argument('--extra', action='append', default=[], help='name=before_dir:after_dir (a single evaluate_round_s output)')
    p.add_argument('--output', required=True)
    a = p.parse_args()
    before, after = Path(a.before), Path(a.after)
    disp_b, disp_a = disposition(before), disposition(after)
    for item in a.extra:
        name, _, dirs = item.partition('=')
        b_dir, _, a_dir = dirs.partition(':')
        for target, d in ((disp_b, Path(b_dir)), (disp_a, Path(a_dir))):
            target.update({name: disposition_single(d)})
    table = {name: dict(before=disp_b.get(name), after=disp_a.get(name)) for name in sorted(set(disp_b) | set(disp_a))}
    totals = {side: dict(contracts=sum(v[side]['contracts'] for v in table.values() if v[side]),
                         fp=sum(len(v[side]['fp']) for v in table.values() if v[side]),
                         fn=sum(len(v[side]['fn']) for v in table.values() if v[side])) for side in ('before', 'after')}
    result = dict(disposition=table, disposition_totals=totals,
                  default_no_dependence=dict(before=default_no_dependence(before), after=default_no_dependence(after)))
    Path(a.output).write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps(dict(disposition_totals=totals,
                          default_no=dict({k: {x: y for x, y in (v or {}).items() if x != 'cases'}
                                           for k, v in result['default_no_dependence'].items()})), indent=1))


def disposition_single(d: Path):
    fp, fn, total = [], [], 0
    for row in json.loads((d / 'summary.json').read_text())['rows']:
        expect = _fixture_expect(row['case_id'])
        if 'urgent' not in expect:
            continue
        total += 1
        urgent = bool(row.get('urgent_plan'))
        if urgent and not expect['urgent']:
            fp.append(row['case_id'])
        if not urgent and expect['urgent']:
            fn.append(row['case_id'])
    return dict(contracts=total, fp=fp, fn=fn)


if __name__ == '__main__':
    main()
