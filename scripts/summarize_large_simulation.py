"""Audit a completed large run and summarize errors without hiding hard targets."""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import sys
from functools import lru_cache

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nova_agent.diagnosis_normalizer import normalize_diagnosis, same_diagnosis
from nova_agent.knowledge.retrieval import critical_condition_ids, disease_by_id


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
    topk = Counter()
    label_confusions = defaultdict(Counter)
    advanced_by = {key: defaultdict(Counter) for key in ('split', 'difficulty')}
    critical_matrix = Counter()
    ood_matrix = Counter()
    followup = Counter()
    failure_signals = Counter()
    critical_ids = set(critical_condition_ids())

    @lru_cache(maxsize=20000)
    def cached_normalize(text):
        return normalize_diagnosis(text)

    @lru_cache(maxsize=100000)
    def cached_same(a, b):
        return same_diagnosis(a, b)

    def canonical_label(text, *, expected=False):
        if not text:
            return '__NONE__'
        normalized = cached_normalize(text)
        if normalized.mapped and normalized.canonical_id:
            return normalized.canonical_id
        clean = ''.join(ch.lower() if ch.isalnum() else '_' for ch in str(text)).strip('_')
        return ('raw_expected:' if expected else 'raw_predicted:') + clean

    def is_ood_expected(row, result):
        group = str(row.get('diagnostic_group', '')).lower()
        gt = str(result.get('ground_truth', '')).lower()
        return 'unknown' in group or gt in {'unknown', 'unknown_presentation', 'ood'}

    def is_ood_predicted(result):
        value = str(result.get('final_diagnosis') or '').strip().lower()
        return not value or value in {'unknown', 'insufficient information', 'unknown presentation'}

    def predicted_is_critical(result):
        value = result.get('final_diagnosis')
        if not value:
            return False
        normalized = cached_normalize(value)
        if normalized.mapped and normalized.canonical_id:
            entry = disease_by_id(normalized.canonical_id)
            return normalized.canonical_id in critical_ids or bool(entry and entry.get('dangerous'))
        return False

    def top5_hit(result, expected, limit):
        trajectory = result.get('differential_trajectory') or []
        if not trajectory:
            return False
        candidates = trajectory[-1].get('top5_differential') or []
        return any(cached_same(str(candidate), str(expected)) for candidate in candidates[:limit])

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
        expected = result.get('ground_truth')
        predicted = result.get('final_diagnosis')
        hit3 = top5_hit(result, expected, 3)
        hit5 = top5_hit(result, expected, 5)
        topk.update(top3=int(hit3), top5=int(hit5))
        expected_label = canonical_label(expected, expected=True)
        predicted_label = canonical_label(predicted)
        for label in {expected_label, predicted_label}:
            label_confusions[label].update(
                tp=int(expected_label == label and predicted_label == label),
                fp=int(expected_label != label and predicted_label == label),
                fn=int(expected_label == label and predicted_label != label),
            )
        expected_critical = bool(result.get('critical'))
        predicted_critical = predicted_is_critical(result)
        critical_matrix.update(
            expected_positive=int(expected_critical), predicted_positive=int(predicted_critical),
            tp=int(expected_critical and predicted_critical),
            fn=int(expected_critical and not predicted_critical),
            fp=int(not expected_critical and predicted_critical),
            tn=int(not expected_critical and not predicted_critical),
        )
        expected_ood = is_ood_expected(row, result)
        predicted_ood = is_ood_predicted(result)
        ood_matrix.update(tp=int(expected_ood and predicted_ood), fn=int(expected_ood and not predicted_ood),
                          fp=int(not expected_ood and predicted_ood), tn=int(not expected_ood and not predicted_ood))
        trajectory = result.get('differential_trajectory') or []
        for dimension in advanced_by:
            bucket = advanced_by[dimension][row[dimension]]
            bucket.update(
                cases=1, correct=int(result.get('correct', False)),
                critical=int(result.get('critical', False)),
                critical_correct=int(result.get('critical', False) and result.get('correct', False)),
                top3=int(hit3), top5=int(hit5), unknown_output=int(is_ood_predicted(result)),
                critical_false_negative=int(result.get('critical', False) and not result.get('correct', False)),
                ood_tp=int(expected_ood and predicted_ood), ood_fp=int(not expected_ood and predicted_ood),
                ood_fn=int(expected_ood and not predicted_ood), ood_tn=int(not expected_ood and not predicted_ood),
            )
        if trajectory:
            first = (trajectory[0].get('top5_differential') or [None])[0]
            last = (trajectory[-1].get('top5_differential') or [None])[0]
            followup.update(cases_with_trajectory=1, first_final_top1_changed=int(first != last),
                            first_top3_hit=int(any(cached_same(str(x), str(expected)) for x in (trajectory[0].get('top5_differential') or [])[:3])),
                            final_top3_hit=int(hit3))
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
            signals = dict(expected_in_final_top3=hit3, expected_in_final_top5=hit5,
                           returned_unknown=is_ood_predicted(result),
                           critical_false_negative=bool(result.get('critical_miss')),
                           reached_turn_limit=bool(result.get('turns') == 60),
                           documentation_mode=row['mutation']['documentation'])
            for signal, enabled in signals.items():
                if isinstance(enabled, bool):
                    failure_signals[signal] += int(enabled)
            failed.append(dict(id=row['id'], difficulty=row['difficulty'], split=row['split'],
                source_family=row['source_family'], expected=row['diagnostic_group'],
                predicted=result['final_diagnosis'], critical=result['critical'],
                error_triage=kind, documentation=row['mutation']['documentation'],
                failure_signals=signals,
                root_cause_status='TRIAGE_ONLY_REVIEW_REQUIRED'))
    if total['cases'] != completion['run_metadata']['cases'] or dict(total).get('real_llm_calls') != 0:
        raise ValueError('Incomplete or non-mock result set')
    def metrics(values):
        return dict(values, accuracy=values['correct']/values['cases'],
                    critical_recall=values['critical_correct']/values['critical'] if values['critical'] else None)
    def binary_metrics(matrix):
        tp, fp, fn, tn = (matrix[k] for k in ('tp', 'fp', 'fn', 'tn'))
        return dict(tp=tp, fp=fp, fn=fn, tn=tn,
                    precision=tp/(tp+fp) if tp+fp else None,
                    recall=tp/(tp+fn) if tp+fn else None,
                    specificity=tn/(tn+fp) if tn+fp else None,
                    false_negative_rate=fn/(tp+fn) if tp+fn else None)

    # With exactly one expected and one predicted label per case, micro precision/recall/F1
    # equals top-1 accuracy. Macro values are still reported because they expose label imbalance.
    per_label = []
    for label, matrix in sorted(label_confusions.items()):
        tp, fp, fn = matrix['tp'], matrix['fp'], matrix['fn']
        precision = tp/(tp+fp) if tp+fp else 0.0
        recall = tp/(tp+fn) if tp+fn else 0.0
        f1 = 2*precision*recall/(precision+recall) if precision+recall else 0.0
        per_label.append(dict(label=label, support=tp+fn, predicted=tp+fp,
                              precision=precision, recall=recall, f1=f1))
    macro_precision = sum(x['precision'] for x in per_label)/len(per_label) if per_label else None
    macro_recall = sum(x['recall'] for x in per_label)/len(per_label) if per_label else None
    macro_f1 = sum(x['f1'] for x in per_label)/len(per_label) if per_label else None
    top1_accuracy = total['correct'] / total['cases'] if total['cases'] else None
    critical_target = dict(cases=total['critical'], correct=total['critical_correct'],
                           false_negatives=total['critical'] - total['critical_correct'],
                           sensitivity=total['critical_correct']/total['critical'] if total['critical'] else None,
                           false_negative_rate=(total['critical'] - total['critical_correct'])/total['critical']
                           if total['critical'] else None)

    def advanced_metrics(values):
        cases = values['cases']
        critical = values['critical']
        ood_den = values['ood_tp'] + values['ood_fn']
        return dict(cases=cases, accuracy=values['correct']/cases if cases else None,
                    top3_recall=values['top3']/cases if cases else None,
                    top5_recall=values['top5']/cases if cases else None,
                    critical_cases=critical,
                    critical_sensitivity=values['critical_correct']/critical if critical else None,
                    critical_false_negatives=values['critical_false_negative'],
                    critical_false_negative_rate=values['critical_false_negative']/critical if critical else None,
                    ood=dict(tp=values['ood_tp'], fp=values['ood_fp'], fn=values['ood_fn'], tn=values['ood_tn'],
                             recall=values['ood_tp']/ood_den if ood_den else None))
    summary = dict(scope=completion['run_metadata']['scope'], total=metrics(total),
                   dataset_provenance=dict(dataset_type='synthetic_mock', train_cases=0,
                                            development_cases=advanced_by['split'].get('development', {}).get('cases', 0),
                                            validation_cases=advanced_by['split'].get('validation', {}).get('cases', 0),
                                            independent_cases=0, clinical_adjudication=False,
                                            real_llm_calls=total['real_llm_calls']),
                   metrics_v2=dict(top1_accuracy=top1_accuracy,
                                   top3_recall=topk['top3']/total['cases'] if total['cases'] else None,
                                   top5_recall=topk['top5']/total['cases'] if total['cases'] else None,
                                   classification_micro=dict(precision=top1_accuracy, recall=top1_accuracy, f1=top1_accuracy),
                                   classification_macro=dict(precision=macro_precision, recall=macro_recall, f1=macro_f1,
                                                             labels=len(per_label)),
                                   critical_target=critical_target,
                                   critical=binary_metrics(critical_matrix),
                                   ood=binary_metrics(ood_matrix),
                                   calibration='NOT_AVAILABLE_NO_CALIBRATOR',
                                   followup_effect=dict(followup, interpretation='descriptive trajectory change; not causal gain')),
                   metrics_v2_by_split={name: advanced_metrics(values) for name, values in sorted(advanced_by['split'].items())},
                   metrics_v2_by_difficulty={name: advanced_metrics(values) for name, values in sorted(advanced_by['difficulty'].items())},
                   breakdown={k: {name: metrics(v) for name,v in sorted(table.items())} for k,table in tables.items()},
                   source_families=len(tables['source_family']),
                   families_all_variants_correct=sum(v['cases']==v['correct'] for v in tables['source_family'].values()),
                   family_macro_accuracy=sum(v['correct']/v['cases'] for v in tables['source_family'].values())/len(tables['source_family']),
                   failure_types=dict(Counter(r['error_triage'] for r in failed)),
                   failure_signals=dict(failure_signals),
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
