import gzip
import json
from scripts.build_doid_review_candidates import SOURCE, OUTPUT, build, code_key
from scripts.build_mondo_review_candidates import parse_obo
from scripts.search_review_candidates import load_candidates, search
from nova_agent.ontology.registry import build_catalog


def test_original_labels_leaf_scope_and_isolation():
    raw = parse_obo(gzip.decompress(SOURCE.read_bytes()).decode(), prefix='DOID:')
    parents = {p for t in raw.values() if not t['obsolete'] for p in t['parents']}
    data = json.loads(OUTPUT.read_text())
    runtime = build_catalog()
    for row in data['candidates']:
        assert row['canonical_name'] == raw[row['code']]['name']
        assert row['source_xrefs'] == raw[row['code']]['raw_xrefs']
        assert not raw[row['code']]['obsolete']
        assert row['code'] not in parents
        assert row['clinical_validation_status'] == 'NOT_VERIFIED'
        assert not row['runtime_eligible']
        assert runtime.get_condition(row['id']) is None


def test_rebuild_counts_and_search():
    data = json.loads(OUTPUT.read_text())
    assert build() == data
    assert data['added_review_entries'] == len(data['candidates']) > 0
    rows = load_candidates()
    assert len({r['id'] for r in rows}) == len(rows)
    assert len(build_catalog()) + len(rows) == data['combined_registered_and_review_entries']
    row = data['candidates'][0]
    assert row in search(row['code'], source='doid')


def test_equivalent_namespace_spellings_are_screened_together():
    assert code_key('NCI', 'C123') == code_key('NCIT', 'C123')
    assert code_key('UMLS_CUI', 'C123') == code_key('UMLS', 'C123')
    assert code_key('SNOMEDCT_US_2025_09_01', '123') == code_key('SCTID', '123')
    assert code_key('MIM', '123') == code_key('OMIM', '123')
