"""Integrity and leakage boundaries, not a validation of synthetic clinical labels."""
from collections import Counter, defaultdict
import gzip
import hashlib
import json

from scripts.build_large_simulation_corpus import DIRECTORY, load_sources, payload_digest


def test_frozen_50000_inputs_are_distinct_with_group_separation_and_inherited_labels():
    manifest = json.loads((DIRECTORY / 'manifest.json').read_text())
    path = DIRECTORY / 'cases.jsonl.gz'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest['corpus_sha256']
    pools, _ = load_sources()
    sources = {family: case for entries in pools.values() for family, case in entries}
    counts, ids, payloads = Counter(), set(), set()
    families, diagnoses = defaultdict(set), defaultdict(set)
    with gzip.open(path, 'rt') as stream:
        for line in stream:
            row = json.loads(line)
            case, original = row['case'], sources[row['source_family']]
            assert row['clinical_validation_status'] == 'NOT_VERIFIED'
            assert row['label_origin'] == 'INHERITED_HISTORICAL_SYNTHETIC_SOURCE_NOT_MODEL_PREDICTION'
            assert case['ground_truth_diagnosis'] == original['ground_truth_diagnosis']
            assert case['demographics'].get('sex') == original['demographics'].get('sex')
            assert row['id'] not in ids
            assert row['input_sha256'] == payload_digest(case)
            assert row['input_sha256'] not in payloads
            assert set(case['test_results']) == set(original['test_results'])
            assert set(case['exam_results']) == set(original['exam_results'])
            ids.add(row['id']); payloads.add(row['input_sha256'])
            counts[row['difficulty'] + ':' + row['split']] += 1
            families[row['source_family']].add(row['split'])
            diagnoses[row['diagnostic_group']].add(row['split'])
    assert counts == manifest['counts']
    assert len(ids) == len(payloads) == 50000
    assert all(len(v) == 1 for v in families.values())
    assert all(len(v) == 1 for v in diagnoses.values())
    assert len(families) == 191
    assert len(diagnoses) == 42
    assert not any('v11' in key for key in manifest['source_files'])


def test_identifiers_and_truth_cannot_make_duplicate_input_look_new():
    pools, _ = load_sources()
    case = dict(pools['low'][0][1])
    digest = payload_digest(case)
    case.update(case_id='different', notes='different', category='different',
                ground_truth_diagnosis='invented', scoring_expected=False)
    assert payload_digest(case) == digest
