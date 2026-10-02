"""Provenance/deduplication/isolation checks, not clinical validation."""
import gzip
import hashlib
import json
import pytest

from scripts.build_mondo_review_candidates import SOURCE, OUTPUT, HUMAN, build, parse_obo, eligible_terms
from scripts.search_review_candidates import load_candidates, search
from nova_agent.ontology.registry import build_catalog
from nova_agent.ontology.normalizer import normalize


@pytest.fixture(scope='module')
def snapshot():
    return json.loads(OUTPUT.read_text()), parse_obo(gzip.decompress(SOURCE.read_bytes()).decode())


def test_source_fidelity_and_human_leaf_filter(snapshot):
    data, terms = snapshot
    eligible = {t['id'] for t in eligible_terms(terms)}
    assert data['source_uncompressed_sha256'] == hashlib.sha256(gzip.decompress(SOURCE.read_bytes())).hexdigest()
    assert data['license'] == 'CC-BY-4.0'
    assert len(data['candidates']) == 15350
    for row in data['candidates']:
        assert row['code'] in eligible
        assert row['canonical_name'] == terms[row['code']]['name']
        assert row['aliases'] == terms[row['code']]['aliases']
        assert row['source_xrefs'] == terms[row['code']]['raw_xrefs']
        assert row['runtime_eligible'] is False
        assert row['clinical_validation_status'] == 'NOT_VERIFIED'


def test_all_names_and_long_exact_aliases_screened_against_prior_terms(snapshot):
    data, _ = snapshot
    seen = {normalize(t) for c in build_catalog().all_concepts() for t in c.all_search_terms()}
    seen.update(normalize(c['canonical_name']) for c in load_candidates('icd'))
    for row in data['candidates']:
        keys = {normalize(row['canonical_name']), *(normalize(a) for a in row['aliases'] if len(a) >= 5)}
        assert not keys & seen
        seen.update(keys)


def test_import_is_reproducible_and_target_shortfall_is_honest(snapshot):
    data, _ = snapshot
    assert build() == data
    assert data['combined_registered_and_review_entries'] == 22939
    assert data['shortfall_entries'] == 9061
    assert not data['requested_target_reached']


def test_unified_search_and_runtime_isolation(snapshot):
    data, _ = snapshot
    assert len(load_candidates()) == 6309 + 15350
    first = data['candidates'][0]
    assert first in search(first['code'], source='mondo')
    assert first in search(first['canonical_name'], source='mondo')
    runtime = build_catalog()
    assert len(runtime) == 1280
    assert all(runtime.get_condition(r['id']) is None for r in data['candidates'])


def test_combined_manifest_counts_actual_records(snapshot):
    data, _ = snapshot
    manifest = json.loads((OUTPUT.parent / 'combined_manifest.json').read_text())
    assert manifest['total_registered_and_review_entries'] == len(build_catalog()) + len(load_candidates())
    assert manifest['mondo_review_entries'] == len(data['candidates'])
    assert manifest['clinical_accuracy_verified'] is False


def test_nonhuman_obsolete_grouping_and_broad_synonyms_are_not_imported():
    text = '''format-version: 1.2

[Term]
id: MONDO:0700096
name: human disease

[Term]
id: MONDO:1
name: human grouping
is_a: MONDO:0700096 ! human disease

[Term]
id: MONDO:2
name: specific human disorder
is_a: MONDO:1 ! grouping
synonym: "specific alias" EXACT []
synonym: "broad alias" BROAD []

[Term]
id: MONDO:3
name: animal disorder

[Term]
id: MONDO:4
name: obsolete disorder
is_a: MONDO:0700096
is_obsolete: true

[Term]
id: MONDO:5
name: nondisease
is_a: MONDO:0700096
subset: not_a_disease
'''
    terms = parse_obo(text)
    assert [t['id'] for t in eligible_terms(terms)] == ['MONDO:2']
    assert terms['MONDO:2']['aliases'] == ['specific alias']
