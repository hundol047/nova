"""Software invariants of offline drafts; never evidence of clinical performance."""
import json

import pytest

from scripts.review_diagnostic_evidence import DIRECTORY, assess, load_profiles, run_probes


def test_structured_positive_negative_temporal_and_mimic_probes(tmp_path):
    report = run_probes(tmp_path / 'probes.json')
    assert report['probes'] == 54
    assert report['failed'] == 0
    for case in report['results']:
        result = case['result']
        assert result['final_diagnosis'] is None
        assert result['probability'] is None
        assert result['disease_excluded'] is False
        assert result['runtime_eligible'] is False


def test_review_drafts_address_remaining_gaps_without_runtime_activation():
    from nova_agent.knowledge.retrieval import disease_by_id
    from nova_agent.ontology.registry import build_catalog
    profiles = load_profiles()
    gaps = json.loads((DIRECTORY.parents[2] / 'docs/evaluation/diagnostic_context_v1/remaining_coverage.json').read_text())
    assert set(profiles) == {r['expected'] for r in gaps}
    catalog = build_catalog()
    for key, profile in profiles.items():
        assert catalog.get_condition(key) is not None
        assert disease_by_id(key) is None
        assert profile['independent_review_status'] == 'PENDING'
        assert profile['runtime_eligible'] is False
        assert profile['sources'] and profile['confirmation_needed'] and profile['mimics_for_review']


@pytest.mark.parametrize('row', [
    {'feature': 'barking_cough', 'status': 'present'},
    {'feature': 'barking_cough', 'status': 'positive', 'temporality': 'current'},
    {'feature': 'barking_cough', 'status': 'present', 'temporality': 'future'},
    {'feature': 'croup', 'status': 'present', 'temporality': 'current'},
])
def test_diagnosis_labels_or_ambiguous_input_cannot_be_evidence(row):
    with pytest.raises(ValueError):
        assess(load_profiles()['tier2:croup'], [row])


def test_conflict_handling_is_order_independent():
    profile = load_profiles()['tier2:croup']
    observations = [
        dict(feature='barking_cough', status='present', temporality='current'),
        dict(feature='inspiratory_stridor', status='present', temporality='current'),
        dict(feature='barking_cough', status='absent', temporality='current'),
    ]
    assert assess(profile, observations) == assess(profile, observations[::-1])
    assert assess(profile, observations)['status'] == 'INSUFFICIENT_PATTERN_EVIDENCE'
