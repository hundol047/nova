"""Offline evidence-pattern review. Never returns a diagnosis, probability or rule-out.

Input feature codes must already be abstracted from evidence by a reviewer. This
module does not parse patient language, numeric labs, sex, age or gestational age.
The profiles and probes are developer-authored and await independent review.
There is deliberately no runtime import or activation option.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'research/clinical_review/hard_seven'


def load_profiles():
    pack = json.loads((DIRECTORY / 'profiles.json').read_text())
    if pack['purpose'] != 'OFFLINE_EVIDENCE_REVIEW_ONLY' or pack['runtime_eligible'] is not False:
        raise ValueError('Only isolated review drafts are accepted')
    profiles = {}
    for p in pack['profiles']:
        if p['id'] in profiles or p['runtime_eligible'] is not False or p['clinical_validation_status'] != 'NOT_VERIFIED':
            raise ValueError('Duplicate or unexpectedly activated review profile')
        if not p['sources'] or not p['feature_groups'] or not all(p['feature_groups']):
            raise ValueError('Missing source or evidence group')
        profiles[p['id']] = p
    return profiles


def assess(profile, observations):
    """Conservative structured evidence check; no match does NOT exclude disease."""
    allowed = {f for group in profile['feature_groups'] for f in group}
    allowed.update(profile['additional_features'])
    current = defaultdict(set)
    ignored = []
    for row in observations:
        if set(row) != {'feature', 'status', 'temporality'}:
            raise ValueError('Observation requires exactly feature, status and temporality')
        if row['feature'] not in allowed:
            raise ValueError('Unrecognized feature code: ' + str(row['feature']))
        if row['status'] not in {'present', 'absent', 'uncertain', 'not_measured'}:
            raise ValueError('Unrecognized observation status')
        if row['temporality'] not in {'current', 'historical', 'unknown'}:
            raise ValueError('Unrecognized observation temporality')
        if row['temporality'] != 'current':
            ignored.append(dict(row))
        else:
            current[row['feature']].add(row['status'])
    # An unresolved positive/negative or positive/uncertain conflict cannot count
    # as affirmative evidence, irrespective of input order or repeated positives.
    positive = {f for f, states in current.items() if states == {'present'}}
    conflicts = sorted(f for f, states in current.items() if len(states) > 1)
    matches = [sorted(set(group) & positive) for group in profile['feature_groups']]
    supported = all(matches)
    return dict(profile=profile['id'],
                status='PATTERN_FOR_REVIEW' if supported else 'INSUFFICIENT_PATTERN_EVIDENCE',
                matched_groups=matches,
                missing_groups=[group for group, match in zip(profile['feature_groups'], matches) if not match],
                conflicting_features=conflicts, ignored_noncurrent_observations=ignored,
                confirmation_needed=profile['confirmation_needed'],
                clinical_validation_status='NOT_VERIFIED', runtime_eligible=False,
                final_diagnosis=None, probability=None, disease_excluded=False)


def run_probes(output):
    profiles = load_profiles()
    raw = (DIRECTORY / 'probes.json').read_bytes()
    probes = json.loads(raw)
    results = []
    for case in probes['cases']:
        result = assess(profiles[case['profile']], case['observations'])
        supported = result['status'] == 'PATTERN_FOR_REVIEW'
        results.append(dict(id=case['id'], kind=case['kind'],
                            expected_pattern_supported=case['expected_pattern_supported'],
                            passed=supported == case['expected_pattern_supported'], result=result))
    report = dict(scope=probes['scope'], profiles_checked=len(profiles), probes=len(results),
                  passed=sum(r['passed'] for r in results),
                  failed=sum(not r['passed'] for r in results),
                  profiles_sha256=hashlib.sha256((DIRECTORY / 'profiles.json').read_bytes()).hexdigest(),
                  probes_sha256=hashlib.sha256(raw).hexdigest(),
                  independent_clinical_validation=False, runtime_activated=False,
                  limitation='Structured feature semantics only; not diagnosis, clinical accuracy, external validation or model training.',
                  results=results)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = run_probes(args.output)
    print(json.dumps({k: v for k, v in report.items() if k != 'results'}))
    raise SystemExit(1 if report['failed'] else 0)
