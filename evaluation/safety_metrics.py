"""Observed warning behavior, separate from exact diagnosis and diagnosis-label proxies."""

def safety_metrics(results):
    matrix = dict(tp=0, fp=0, fn=0, tn=0)
    unknown = 0
    missed_ids = []
    for result in results:
        warning = result.get('final_safety_flag')
        if not isinstance(warning, bool):
            unknown += 1
            continue
        critical = result['critical']
        key = ('tp' if warning else 'fn') if critical else ('fp' if warning else 'tn')
        matrix[key] += 1
        if key == 'fn':
            missed_ids.append(result['case_id'])
    tp, fp, fn, tn = (matrix[k] for k in ('tp', 'fp', 'fn', 'tn'))
    return dict(matrix, observed_cases=tp+fp+fn+tn, uninstrumented_cases=unknown,
                sensitivity=tp/(tp+fn) if tp+fn else None,
                specificity=tn/(tn+fp) if tn+fp else None,
                false_negative_rate=fn/(tp+fn) if tp+fn else None,
                missed_case_ids=missed_ids,
                interpretation='Any final SafetyLayer flag versus synthetic critical label; '
                'not condition-specific recall, triage correctness or clinical validation.')
