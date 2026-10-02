"""Source audit and isolation; not a clinical accuracy evaluation."""
import json
from scripts.build_orphanet_review_candidates import OUTPUT, read_source, build, eligible, code_key
from scripts.search_review_candidates import load_candidates, search
from nova_agent.ontology.registry import build_catalog


def test_source_fidelity_including_mapping_relations():
    date, digest, rows = read_source()
    raw = {r['code']: r for r in rows}
    data = json.loads(OUTPUT.read_text())
    assert data['source_uncompressed_sha256'] == digest
    assert data['source_version'] == date
    assert len(data['candidates']) == 388
    for row in data['candidates']:
        original = raw[row['code'].split(':')[1]]
        assert eligible(original)
        assert row['canonical_name'] == original['name']
        assert row['source_xrefs'] == original['xrefs']
        assert row['aliases'] == original['aliases']
        assert row['runtime_eligible'] is False
        assert row['clinical_validation_status'] == 'NOT_VERIFIED'


def test_reproducible_and_honest_shortfall():
    data = json.loads(OUTPUT.read_text())
    assert build() == data
    assert data['combined_registered_and_review_entries'] == 23327
    assert data['shortfall_entries'] == 8673
    assert not data['requested_target_reached']


def test_inactive_group_and_non_disease_exclusion():
    row = dict(code='1', name='example', type='Disease', group='Disorder', flags=[])
    assert eligible(row)
    assert not eligible(dict(row, flags=['Inactive']))
    assert not eligible(dict(row, flags=['Historical entity']))
    assert not eligible(dict(row, group='Group of disorders'))
    assert not eligible(dict(row, type='Biological anomaly'))


def test_cross_reference_namespace_normalization():
    assert code_key('ICD-10', 'Q77.3') == code_key('ICD10CM', 'Q773')
    assert code_key('Orphanet', '125') == code_key('ORPHA', '125')
    assert code_key('SNOMED CT', '123') == code_key('SCTID', '123')


def test_search_manifest_and_runtime_isolation():
    data = json.loads(OUTPUT.read_text())
    first = data['candidates'][0]
    assert first in search(first['code'], source='orphanet')
    manifest = json.loads((OUTPUT.parent / 'combined_manifest.json').read_text())
    assert manifest['orphanet_review_entries'] == len(data['candidates'])
    runtime = build_catalog()
    assert len(runtime) == 1280
    assert len(runtime) + len(load_candidates()) == 23327
    assert manifest['total_registered_and_review_entries'] == 23327
    assert all(runtime.get_condition(r['id']) is None for r in data['candidates'])
