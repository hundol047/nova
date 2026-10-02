import pytest
from evaluation.expanded_cases import VIGNETTES
from nova_agent.knowledge.retrieval import all_diseases, disease_by_id
from nova_agent.state import PatientState
from nova_agent.taxonomy import EXAM_CATALOG
from nova_agent.expanded_evidence import observed, evidence_complete, rule_matches
from nova_agent.differential import DifferentialEngine
from nova_agent.diagnosis_normalizer import normalize_diagnosis


def state_for(narrative, results):
    state = PatientState(chief_complaint=narrative, turn_count=12)
    for key, value in results.items():
        if key in EXAM_CATALOG:
            state.record_exam(key, value)
        else:
            state.record_test(key, value)
    return state


def test_catalog_doubled_without_alias_collisions():
    assert len(all_diseases()) == 68
    seen = {}
    from nova_agent.diagnosis_normalizer import _clean
    for entry in all_diseases().values():
        for name in [entry['id'], entry['name'], *entry['aliases']]:
            key = _clean(name)
            assert key not in seen or seen[key] == entry['id'], (key, entry['id'], seen.get(key))
            seen[key] = entry['id']


@pytest.mark.parametrize('diagnosis,narrative,results', VIGNETTES, ids=[v[0] for v in VIGNETTES])
def test_new_vignette_rank_with_recorded_evidence(diagnosis, narrative, results):
    state = state_for(narrative, results)
    assert evidence_complete(disease_by_id(diagnosis), state)
    assert DifferentialEngine().update(state)[0].diagnosis_id == diagnosis


@pytest.mark.parametrize('diagnosis,narrative,results', VIGNETTES, ids=[v[0] for v in VIGNETTES])
def test_pending_and_negated_findings_never_complete_support(diagnosis, narrative, results):
    entry = disease_by_id(diagnosis)
    for prefix in ['Possible ', 'No ', 'Pending assessment for ', 'History of ']:
        state = state_for(narrative, {k: '; '.join(prefix + c.strip() for c in v.strip('.').split(';')) for k,v in results.items()})
        assert not any(rule_matches(entry, state))


@pytest.mark.parametrize('diagnosis,narrative,results', VIGNETTES, ids=[v[0] for v in VIGNETTES])
def test_patient_reports_cannot_substitute_for_tests(diagnosis, narrative, results):
    state = PatientState(chief_complaint=narrative + '; ' + '; '.join(results.values()))
    assert not any(rule_matches(disease_by_id(diagnosis), state))


@pytest.mark.parametrize('text', ['mixture', 'acute', 'pain', 'heart', 'hypothyroidisms'])
def test_partial_words_are_not_diagnoses(text):
    assert not normalize_diagnosis(text).mapped


def test_suffix_negation_and_family_history_not_positive():
    assert not observed('low ferritin', ['Low ferritin was not detected.'])
    assert not observed('low ferritin', ['Mother has low ferritin.'])
    assert observed('low ferritin', ['No fever; low ferritin.'])


def test_missing_support_does_not_allow_early_final_or_normal_ruleout():
    from nova_agent.stop_policy import StopPolicy
    from nova_agent.resolution import is_resolved
    state=PatientState(chief_complaint='cold intolerance; weight gain; constipation', turn_count=20)
    diff=DifferentialEngine().update(state)
    assert diff[0].diagnosis_id=='primary_hypothyroidism'
    assert diff[0].confidence_band=='LOW'
    assert not StopPolicy().evaluate(state,diff,[],best_info_gain=0).should_diagnose
    state.record_test('thyroid_panel','Normal.')
    assert not is_resolved('primary_hypothyroidism',[],state)


@pytest.mark.parametrize('diagnosis,narrative,results', VIGNETTES, ids=[v[0] for v in VIGNETTES])
def test_wrong_procedure_cannot_supply_support(diagnosis, narrative, results):
    state=state_for(narrative, {'ct_aorta': '; '.join(results.values())})
    assert not any(rule_matches(disease_by_id(diagnosis), state))


def test_conflicting_reports_lower_confidence_and_retain_safety():
    from nova_agent.decision_quality import assess_decision
    from nova_agent.safety import SafetyLayer
    from nova_agent.differential import _score_disease
    entry=disease_by_id('primary_hypothyroidism')
    state=state_for('Cold intolerance; weight gain; constipation.',
                    {'thyroid_panel':'Elevated TSH; low free T4; low free T4 was not detected.'})
    assert not evidence_complete(entry,state)
    assert _score_disease(entry,state)[3]
    diff=DifferentialEngine().update(state)
    assert assess_decision(state,diff)['band']=='LOW'
    state=state_for('Headache', {'ct_head':'Acute intraparenchymal hematoma.'})
    assert any(f.diagnosis_id=='intracerebral_hemorrhage' for f in SafetyLayer().assess(state,[]))


def test_evidence_rule_schema_cannot_point_to_undeclared_procedure(tmp_path):
    import json
    from nova_agent.knowledge.extensions import load_extension
    entry=dict(disease_by_id('primary_hypothyroidism'))
    entry['evidence_rules']=[{'source':'invented_test','any_of':['low t4']}]
    path=tmp_path/'extension.json';path.write_text(json.dumps([entry]))
    with pytest.raises(ValueError,match='declared'):
        load_extension(path,set())
