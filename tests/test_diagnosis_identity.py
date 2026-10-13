"""Duplicate catalog rows are one exact identity; conflicting aliases stay ambiguous."""
import pytest
from nova_agent.diagnosis_normalizer import normalize_diagnosis, same_diagnosis


def test_existing_gerd_alias_is_not_rejected_by_duplicate_catalog_entry():
    assert normalize_diagnosis('GERD').canonical_id == 'gerd'
    assert same_diagnosis('GERD','Gastroesophageal Reflux Disease')
    assert same_diagnosis('tier2:gi_gerd_gi','gerd')


def test_every_exact_duplicate_core_name_resolves_to_the_same_identity():
    from collections import defaultdict
    from nova_agent.ontology.registry import get_default_catalog
    from nova_agent.ontology.normalizer import normalize
    groups=defaultdict(list)
    for c in get_default_catalog().all_concepts():groups[normalize(c.canonical_name)].append(c)
    checked=0
    for rows in groups.values():
        core={c.kb_id for c in rows if c.kb_id}
        if len(rows)>1 and len(core)==1:
            checked+=1
            expected=next(iter(core))
            assert normalize_diagnosis(rows[0].canonical_name).canonical_id == expected
            for row in rows:assert normalize_diagnosis(row.concept_id).canonical_id == expected
    assert checked > 0


def test_shared_alias_for_different_names_is_still_ambiguous(monkeypatch):
    from nova_agent.ontology.models import ClinicalConcept
    import nova_agent.ontology.registry as registry
    rows=[ClinicalConcept('one','Distinct disease one',aliases=('ambiguous-test',)),
          ClinicalConcept('two','Distinct disease two',aliases=('ambiguous-test',))]
    class Catalog:
        def all_concepts(self):return rows
        def get_condition(self,key):return next((c for c in rows if c.concept_id==key),None)
    monkeypatch.setattr(registry,'get_default_catalog',lambda:Catalog())
    assert not normalize_diagnosis('ambiguous-test').mapped
