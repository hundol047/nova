import json
from scripts.build_injury_review_candidates import OUTPUT, build, eligible
from scripts.build_review_candidates import DEFAULT_SOURCE, source_rows
from scripts.search_review_candidates import load_candidates, search
from nova_agent.ontology.registry import build_catalog


def test_exact_source_labels_and_isolation():
    data = json.loads(OUTPUT.read_text())
    source = {c: (n, terminal) for c, n, terminal in source_rows(DEFAULT_SOURCE)}
    runtime = build_catalog()
    assert len(runtime) == 1280
    for row in data['candidates']:
        assert source[row['code']] == (row['canonical_name'], True)
        assert eligible(row['code'], row['canonical_name'], True)
        assert row['clinical_validation_status'] == 'NOT_VERIFIED'
        assert row['runtime_eligible'] is False
        assert runtime.get_condition(row['id']) is None


def test_reproducible_and_target_not_claimed():
    data = json.loads(OUTPUT.read_text())
    assert build() == data
    assert data['requested_total_entries'] == 34991
    assert not data['requested_target_reached']
    assert data['combined_registered_and_review_entries'] + data['shortfall_entries'] == 34991
    assert len(data['candidates']) > 0


def test_encounter_and_intent_variants_excluded():
    assert eligible('S0001XA', 'Abrasion of scalp, initial encounter', True)
    assert not eligible('S0001XD', 'Abrasion of scalp, subsequent encounter', True)
    assert not eligible('T00000A', 'Poisoning, intentional self-harm', True)
    assert not eligible('T00000A', 'Poisoning, assault', True)


def test_search_and_aggregate_counts():
    data = json.loads(OUTPUT.read_text())
    row = data['candidates'][0]
    assert row in search(row['code'], source='injury')
    manifest = json.loads((OUTPUT.parent / 'combined_manifest.json').read_text())
    all_rows = load_candidates()
    assert len({r['id'] for r in all_rows}) == len(all_rows)
    assert manifest['total_registered_and_review_entries'] == len(build_catalog()) + len(all_rows)
    assert manifest['injury_review_entries'] == len(data['candidates'])
