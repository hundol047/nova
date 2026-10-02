"""Audit a completed large run and summarize errors without hiding hard targets."""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path


def iter_results(directory):
    for path in sorted(directory.glob('part_*.jsonl.gz')):
        expected = json.loads(path.with_suffix('.summary.json').read_text())
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected['output_sha256']:
            raise ValueError('Result shard hash differs: ' + str(path))
        with gzip.open(path, 'rt') as stream:
            rows = [json.loads(line) for line in stream]
        if [r['id'] for r in rows] != expected['case_ids']:
            raise ValueError('Shard case IDs differ')
        yield from rows


def summarize(directory):
    completion = json.loads((directory / 'completion.json').read_text())
    if not completion['completed']:
        raise ValueError('Run incomplete')
    tables = {key: defaultdict(Counter) for key in ['difficulty', 'split', 'diagnostic_group', 'source_family', 'documentation']}
    ids, inputs, failed, total = set(), set(), [], Counter()
    for row in iter_results(directory):
        if row['id'] in ids or row['input_sha256'] in inputs:
            raise ValueError('Duplicate result ID or input')
        ids.add(row['id']); inputs.add(row['input_sha256'])
        result = row['result']
        values = dict(cases=1, correct=int(result['correct']), critical=int(result['critical']),
                      critical_correct=int(result['critical'] and result['correct']),
                      unknown_output=int(result['final_diagnosis'] == 'unknown'),
                      turns=result['turns'], real_llm_calls=result['llm_call_count'])
        total.update(values)
        for key, buckets in tables.items():
            value = row['mutation']['documentation'] if key == 'documentation' else row[key]
            buckets[value].update(values)
        if not result['correct']:
            if row['diagnostic_group'].startswith('tier2:'):
                kind = 'unimplemented_deep_target_requires_review'
            elif not result['final_diagnosis']:
                kind = 'no_final_output'
            elif result['final_diagnosis'] == 'unknown':
                kind = 'abstention_on_named_target'
            else:
                kind = 'incorrect_named_output'
            failed.append(dict(id=row['id'], difficulty=row['difficulty'], split=row['split'],
                source_family=row['source_family'], expected=row['diagnostic_group'],
                predicted=result['final_diagnosis'], critical=result['critical'],
                error_triage=kind, documentation=row['mutation']['documentation']))
    if total['cases'] != completion['run_metadata']['cases'] or dict(total).get('real_llm_calls') != 0:
        raise ValueError('Incomplete or non-mock result set')
    def metrics(values):
        return dict(values, accuracy=values['correct']/values['cases'],
                    critical_recall=values['critical_correct']/values['critical'] if values['critical'] else None)
    summary = dict(scope=completion['run_metadata']['scope'], total=metrics(total),
                   breakdown={k: {name: metrics(v) for name,v in sorted(table.items())} for k,table in tables.items()},
                   source_families=len(tables['source_family']),
                   families_all_variants_correct=sum(v['cases']==v['correct'] for v in tables['source_family'].values()),
                   family_macro_accuracy=sum(v['correct']/v['cases'] for v in tables['source_family'].values())/len(tables['source_family']),
                   failure_types=dict(Counter(r['error_triage'] for r in failed)),
                   independent_clinical_validation=False,
                   limitation='Correlated synthetic variants with inherited unverified labels; not population accuracy or calibrated probabilities.')
    (directory / 'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    with (directory / 'failures.jsonl').open('w') as stream:
        for row in failed:
            stream.write(json.dumps(row)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='breakdown'},indent=2))
    print(json.dumps(summary['breakdown']['difficulty'],indent=2))
    return summary


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    summarize(parser.parse_args().directory)
