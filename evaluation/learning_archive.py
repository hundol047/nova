"""Immutable archive of built-in synthetic evaluations, never an inference data source.

No external/patient bundles are accepted. Passing a mock test is not clinical validation
or permission to train on held-out cases. Repeat identical runs are idempotent.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

DEFAULT_ARCHIVE = Path(__file__).resolve().parent / 'learning_archive'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def snapshot(report, case_sets):
    if report.get('provider') != 'mock' or report.get('independent_validation') is not False or report.get('clinical_accuracy_claim') is not False:
        raise ValueError('Archive accepts only explicitly unvalidated built-in mock reports')
    if set(report.get('sets', {})) != set(case_sets):
        raise ValueError('Incomplete or unknown evaluation sets')
    records = []
    for name, cases in case_sets.items():
        group = report['sets'][name]
        if group.get('cases_sha256') != digest([c.model_dump() for c in cases]):
            raise ValueError('Case content differs from evaluated snapshot')
        outcomes = group.get('cases', [])
        ids = [r.get('case_id') for r in outcomes]
        if len(ids) != len(set(ids)) or set(ids) != {c.case_id for c in cases}:
            raise ValueError('Missing, duplicate or extra case outcomes')
        by_id = {r['case_id']: r for r in outcomes}
        for case in cases:
            r = by_id[case.case_id]
            for key in ('correct', 'scoring_expected', 'critical_miss'):
                if type(r.get(key)) is not bool:
                    raise ValueError('Explicit outcome booleans required')
            if r['scoring_expected'] != case.scoring_expected:
                raise ValueError('Scoring eligibility changed')
            for key in ('duplicate_actions', 'malformed_turns'):
                if type(r.get(key)) is not int or r[key] < 0:
                    raise ValueError('Valid error counts required')
            from nova_agent.diagnosis_normalizer import same_diagnosis
            correct = bool(r.get('final_diagnosis')) and any(same_diagnosis(r['final_diagnosis'], label)
                for label in [case.ground_truth_diagnosis, *case.acceptable_diagnoses])
            if correct != r['correct'] or r['critical_miss'] != (case.critical and not correct):
                raise ValueError('Outcome does not match frozen case labels')
            status = ('unscored' if not case.scoring_expected else
                      'passed' if correct and not r['critical_miss'] and not r['duplicate_actions'] and not r['malformed_turns'] else 'failed')
            records.append({'set': name, 'case_id': case.case_id, 'status': status,
                'case': case.model_dump(), 'outcome': r,
                'data_origin': 'repository_synthetic_case', 'clinical_validation': False,
                'training_eligible': False,
                'review_route': 'synthetic_training_candidate_review' if name in {'tuning','expanded'} and status == 'passed' else 'evaluation_only_do_not_train'})
    failed = any(r['status'] == 'failed' or r['outcome']['critical_miss'] or
                 r['outcome']['duplicate_actions'] or r['outcome']['malformed_turns'] for r in records)
    if report.get('passed') is not (not failed):
        raise ValueError('Aggregate pass flag disagrees with outcomes')
    return {'schema_version': 1, 'report_sha256': digest(report), 'report': report,
            'counts': {s:sum(r['status'] == s for r in records) for s in ('passed','failed','unscored')},
            'training_eligible_records': 0, 'clinical_validation': False,
            'retention': 'append_only_content_addressed', 'records': records}


def save_snapshot(report, case_sets, directory=DEFAULT_ARCHIVE):
    payload = (json.dumps(snapshot(report, case_sets), sort_keys=True, indent=2) + '\n').encode()
    sha = hashlib.sha256(payload).hexdigest()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (sha + '.json')
    # Link a complete temporary file atomically; never overwrite a historical snapshot.
    fd, temporary = tempfile.mkstemp(prefix='.archive-', dir=directory)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, target)
        except FileExistsError:
            if target.read_bytes() != payload:
                raise ValueError('Existing archive is corrupt; refusing overwrite')
    finally:
        Path(temporary).unlink(missing_ok=True)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', required=True)
    parser.add_argument('--archive-dir', default=str(DEFAULT_ARCHIVE))
    args = parser.parse_args()
    from evaluation.catalog_regression import SETS
    path = save_snapshot(json.loads(Path(args.report).read_text()), SETS, args.archive_dir)
    print(path)


if __name__ == '__main__': main()
