"""Source fidelity and runtime isolation, not clinical performance tests."""
import hashlib
import json
import pytest

from scripts.build_review_candidates import DEFAULT_SOURCE, OUTPUT, EXCLUDED, build, chapter, source_rows
from nova_agent.ontology.normalizer import normalize
from nova_agent.ontology.registry import build_catalog
from scripts.check_expansion_gate import collect


def test_review_queue_reports_source_limit_without_fabricated_names_or_codes():
    data = json.loads(OUTPUT.read_text())
    source = {code: (name, terminal) for code, name, terminal in source_rows(DEFAULT_SOURCE)}
    rows = data['candidates']
    assert len(rows) == 6309
    assert data['combined_registered_and_review_entries'] == 7589
    assert data['requested_total_entries'] == 32000
    assert data['requested_target_reached'] is False
    assert data['shortfall_entries'] == 24411
    assert data['source_sha256'] == hashlib.sha256(DEFAULT_SOURCE.read_bytes()).hexdigest()
    assert len({c['id'] for c in rows}) == len(rows)
    assert len({normalize(c['canonical_name']) for c in rows}) == len(rows)
    for c in rows:
        assert source[c['code']] == (c['canonical_name'], True)
        assert c['category'] == chapter(c['code'])
        assert not EXCLUDED.search(c['canonical_name'])
        assert c['runtime_eligible'] is False
        assert c['clinical_validation_status'] == 'NOT_VERIFIED'
        assert not any(k in c for k in ('symptoms', 'treatment', 'urgency', 'clinical_review'))


def test_rebuild_is_deterministic():
    assert build(target_total=32000, allow_source_limit=True) == json.loads(OUTPUT.read_text())


def test_unreachable_request_fails_without_explicit_partial_output():
    with pytest.raises(ValueError, match='Insufficient eligible'):
        build(target_total=32000)


def test_all_previous_candidates_preserved():
    previous = {c['id'] for c in build()['candidates']}
    current = {c['id'] for c in json.loads(OUTPUT.read_text())['candidates']}
    assert len(previous) == 5120
    assert previous < current


def test_source_labels_do_not_duplicate_existing_names_or_aliases():
    existing = {normalize(t) for c in build_catalog().all_concepts() for t in c.all_search_terms()}
    rows = json.loads(OUTPUT.read_text())['candidates']
    assert not existing.intersection(normalize(c['canonical_name']) for c in rows)


def test_review_queue_does_not_expand_runtime_or_open_gate():
    data = json.loads(OUTPUT.read_text())
    runtime = build_catalog()
    assert sorted(c.concept_id for c in runtime.all_concepts()) == data['baseline_ids']
    assert len(runtime) == 1280
    assert all(runtime.get_condition(c['id']) is None for c in data['candidates'])
    assert collect()['further_expansion_allowed'] is False


def test_diversity_includes_treatment_complications_without_encounter_multiplication():
    data = json.loads(OUTPUT.read_text())
    assert len(data['category_counts']) == 18
    rows = [c for c in data['candidates'] if c['category'] == 'care_complications']
    assert len(rows) == 205
    assert all('T80' <= c['code'][:3] <= 'T88' and c['code'].endswith('A') for c in rows)


def test_alphanumeric_neoplasm_category():
    assert chapter('D3A00') == 'neoplasms'
    assert chapter('D500') == 'blood_immune'
