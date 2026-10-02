"""Paired external-case audit. Numerical screening is not clinical approval.

Compare two real_llm_benchmark reports on the SAME frozen cases. Never imports labels
at inference or enables reference diagnoses. Missing evidence fails closed.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from nova_agent.knowledge.retrieval import all_diseases
from nova_agent.knowledge.reference_catalog import reference_candidates, clean
from evaluation.sealed_cases import load_frozen_cases

POLICY = {'minimum_positive_cases': 40, 'minimum_negative_cases': 40,
          'minimum_wilson_lower_95': 0.90, 'maximum_new_paired_errors': 0,
          'maximum_critical_misses': 0,
          'status': 'engineering_screen_not_clinically_approved'}


def inventory():
    return {**all_diseases(), **reference_candidates()}


def identities():
    names = {}
    for key, entry in inventory().items():
        for name in [key, entry['name'], *entry['aliases']]:
            names.setdefault(clean(name), set()).add(key)
    return {name: next(iter(keys)) for name, keys in names.items() if len(keys) == 1}


def wilson(correct, total):
    if not total:
        return None
    p = correct / total
    z = 1.959963984540054
    d = 1 + z*z/total
    center = (p + z*z/(2*total))/d
    half = z*math.sqrt(p*(1-p)/total + z*z/(4*total*total))/d
    return [max(0, center-half), min(1, center+half)]


def validate_report(report, cases, metadata):
    cfg = report.get('run_config', {})
    if report.get('provider_is_real') is not True or report.get('provider') == 'mock':
        raise ValueError('Mock or missing real-provider evidence cannot pass')
    if not all(isinstance(report.get(k), str) and report[k].strip() for k in ('provider', 'model')):
        raise ValueError('Provider and model identities are required')
    if cfg.get('real_verification_mode') != 'every_decision':
        raise ValueError('Reports must use --require-real')
    if cfg.get('case_manifest') != metadata:
        raise ValueError('Report does not match the frozen case provenance')
    expected = {c.case_id for c in cases}
    records = report.get('cases', [])
    ids = [r.get('case_id') for r in records]
    configured = cfg.get('case_ids', [])
    if len(ids) != len(set(ids)) or set(ids) != expected or len(configured) != len(set(configured)) or set(configured) != expected:
        raise ValueError('Missing, duplicate or extra cases; partial runs cannot pass')
    for key in ('source_sha256', 'catalog_sha256', 'reference_catalog_sha256', 'config_sha256'):
        value = cfg.get(key)
        if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('Missing or malformed run fingerprint: ' + key)
    for r in records:
        if r.get('all_decisions_real') is not True or r.get('real_llm_verified') is not True:
            raise ValueError('Every decision must be verified real')
        for key in ('turns', 'llm_successes', 'llm_calls', 'llm_failures', 'fallback_count', 'malformed_turns'):
            if type(r.get(key)) is not int or r[key] < 0:
                raise ValueError('Missing or invalid call counts')
        if (r['turns'] < 1 or r['llm_successes'] < r['turns'] or r['llm_calls'] < r['llm_successes']
                or r['llm_failures'] or r['fallback_count'] or r['malformed_turns']):
            raise ValueError('Failed, malformed or fallback decisions cannot pass')
        if r.get('timed_out') is not False or r.get('failed_to_diagnose') is not False:
            raise ValueError('Incomplete decisions cannot pass')
    return {r['case_id']: r for r in records}


def audit(baseline, candidate, cases, metadata):
    before = validate_report(baseline, cases, metadata)
    after = validate_report(candidate, cases, metadata)
    for key in ('provider', 'model'):
        if baseline.get(key) != candidate.get(key):
            raise ValueError('Paired runs require the same ' + key)
    names = identities()
    observations = []
    for case in cases:
        if not case.scoring_expected:
            continue
        labels = {names.get(clean(n)) for n in [case.ground_truth_diagnosis, *case.acceptable_diagnoses]}
        if None in labels:
            raise ValueError('Unresolved/ambiguous gold label: ' + case.case_id)
        for record in (before[case.case_id], after[case.case_id]):
            if record.get('ground_truth') != case.ground_truth_diagnosis:
                raise ValueError('Reported ground truth differs from frozen case')
        b = names.get(clean(before[case.case_id].get('final_diagnosis') or ''))
        a = names.get(clean(after[case.case_id].get('final_diagnosis') or ''))
        observations.append((case.case_id, labels, b, a, case.critical))
    regressions = [id for id, labels, b, a, critical in observations if b in labels and a not in labels]
    misses = [id for id, labels, b, a, critical in observations if critical and a not in labels]
    rows = []
    for key, entry in inventory().items():
        positive = [o for o in observations if key in o[1]]
        negative = [o for o in observations if key not in o[1]]
        tp = sum(o[3] == key for o in positive)
        tn = sum(o[3] != key for o in negative)
        sensitivity = wilson(tp, len(positive))
        specificity = wilson(tn, len(negative))
        reasons = []
        if len(positive) < POLICY['minimum_positive_cases']: reasons.append('insufficient_positive_cases')
        if len(negative) < POLICY['minimum_negative_cases']: reasons.append('insufficient_negative_cases')
        if sensitivity is None or sensitivity[0] < POLICY['minimum_wilson_lower_95']: reasons.append('sensitivity_lower_bound_below_target')
        if specificity is None or specificity[0] < POLICY['minimum_wilson_lower_95']: reasons.append('specificity_lower_bound_below_target')
        if regressions: reasons.append('paired_regression_detected')
        if misses: reasons.append('critical_miss_detected')
        rows.append({'id': key, 'name': entry['name'], 'positive_cases': len(positive),
            'negative_cases': len(negative), 'true_positive': tp, 'true_negative': tn,
            'sensitivity_wilson_95': sensitivity, 'specificity_wilson_95': specificity,
            'numerical_screen_passed': not reasons, 'blockers': reasons,
            'clinical_approval': False, 'enable_autonomous_diagnosis': False})
    return {'status': 'review_required', 'policy': POLICY, 'case_manifest': metadata,
        'baseline_run_config': baseline['run_config'], 'candidate_run_config': candidate['run_config'],
        'scored_cases': len(observations), 'paired_new_errors': regressions, 'critical_misses': misses,
        'numerical_screen_passed_count': sum(r['numerical_screen_passed'] for r in rows),
        'clinical_approval': False, 'clinical_accuracy_claim': False,
        'limitations': ['Intervals are descriptive, not adjusted for multiple testing or case clustering.',
            'Representativeness, independence, near-neighbor coverage and clinical adjudication require external review.',
            'No automatic promotion; numerical success alone is insufficient.'], 'conditions': rows}


def readiness():
    return {'status': 'blocked_missing_external_validation', 'policy': POLICY,
        'clinical_approval': False, 'clinical_accuracy_claim': False,
        'numerical_screen_passed_count': 0,
        'blockers': ['No paired real-model reports on independently adjudicated cases supplied.'],
        'conditions': [{'id': key, 'name': entry['name'], 'external_positive_cases': 0,
                        'clinical_approval': False, 'enable_autonomous_diagnosis': False}
                       for key, entry in inventory().items()]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'candidate', 'cases-json', 'case-manifest'):
        parser.add_argument('--' + name)
    parser.add_argument('--save-json', required=True)
    args = parser.parse_args()
    inputs = (args.baseline, args.candidate, args.cases_json, args.case_manifest)
    if any(inputs) and not all(inputs): parser.error('Supply all four comparison inputs')
    if all(inputs):
        cases, metadata = load_frozen_cases(args.cases_json, args.case_manifest)
        report = audit(json.loads(Path(args.baseline).read_text()), json.loads(Path(args.candidate).read_text()), cases, metadata)
        report['report_sha256'] = {name: hashlib.sha256(Path(path).read_bytes()).hexdigest()
                                   for name, path in [('baseline', args.baseline), ('candidate', args.candidate)]}
    else:
        report = readiness()
    Path(args.save_json).write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'], 'numerical screens passed:', report['numerical_screen_passed_count'])
    # This command reports screening only, never grants clinical approval.
    if not all(inputs) or not report['numerical_screen_passed_count']:
        raise SystemExit(1)


if __name__ == '__main__': main()
