import json
import pytest
from scripts.build_ncit_review_candidates import OUTPUT, build, parse_source, descendants, SEMANTIC_TYPES
from scripts.search_review_candidates import load_candidates, search
from nova_agent.ontology.registry import build_catalog
from nova_agent.ontology.normalizer import normalize


@pytest.fixture(scope='module')
def data():
    return json.loads(OUTPUT.read_text())


def test_all_rows_match_official_disease_terms_and_remain_isolated(data):
    terms,children=parse_source()
    scope=descendants('C2991',children)-descendants('C22187',children)
    runtime=build_catalog()
    for r in data['candidates']:
        original=terms[r['code']]
        assert r['code'] in scope
        assert not original['status']
        assert set(original['types']) & SEMANTIC_TYPES
        assert r['canonical_name']==original['names'][0]
        assert r['parent_source_ids']==original['parents']
        assert r['source_leaf']==(not bool(children[r['code']]))
        assert r['clinical_validation_status']=='NOT_VERIFIED'
        assert r['runtime_eligible'] is False
        assert runtime.get_condition(r['id']) is None


def test_rebuild_and_unique_name_target(data):
    assert build()==data
    runtime=build_catalog()
    rows=load_candidates()
    names={normalize(c.canonical_name) for c in runtime.all_concepts()}
    names.update(normalize(r['canonical_name']) for r in rows)
    assert len(names)==35000
    assert len(runtime)+len(rows)==35004
    assert len({r['id'] for r in rows})==len(rows)
    assert len({normalize(r['canonical_name']) for r in rows})==len(rows)
    assert data['leaf_records']+data['nonleaf_records']==len(data['candidates'])
    row=data['candidates'][0]
    assert row in search(row['code'],source='ncit')


def test_header_nodes_link_hierarchy_but_are_never_selected(data):
    terms,children=parse_source()
    assert any('Header_Concept' in t['status'] and children[c] for c,t in terms.items())
    assert all(not terms[r['code']]['status'] for r in data['candidates'])
