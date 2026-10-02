"""Regression tests for audit defects, independent of frozen benchmark cases."""
import json
from pathlib import Path
from types import SimpleNamespace

from nova_agent.diagnosis_normalizer import normalize_diagnosis, same_diagnosis
from nova_agent.ontology.registry import build_catalog
from nova_agent.open_world import OpenWorldRetriever


def test_ambiguous_abbreviations_and_substrings_are_not_guessed():
    for term in ['MS', 'ASD', 'AMS', 'hep', 'no acute myocardial infarction']:
        assert not normalize_diagnosis(term).mapped
        assert not OpenWorldRetriever(build_catalog()).normalize_llm_diagnosis(term).mapped


def test_additional_diagnosis_names_equal_their_ids():
    assert same_diagnosis('Acute Pericarditis', 'tier2:pericarditis')
    assert same_diagnosis('unknown', 'unknown')
    assert not same_diagnosis('unknown', 'Acute Pericarditis')


def test_unverified_mapping_cannot_reenter_through_code_search():
    cat = build_catalog()
    assert not cat.map_external_code('ICD10', 'K72.00')
    assert not cat.map_external_code('ICD10', 'H81.23')
    assert not cat.search_conditions('K72.00', fuzzy=False)
    assert cat.get_condition('tier2:acute_hepatitis').curation_status == 'NOT_CURATED'


def test_synthetic_snapshot_excluded_from_runtime(tmp_path, monkeypatch):
    from nova_agent.ontology.providers.custom import CustomProvider
    (tmp_path/'custom.json').write_text(json.dumps({'synthetic':True, 'system':'NOVASYNTH',
        'concepts':[{'code':'fake', 'display':'Synthetic audit condition'}]}))
    monkeypatch.setattr(CustomProvider, 'snapshot_path', lambda self: tmp_path/'custom.json')
    cat = build_catalog()
    assert not any(c.canonical_name == 'Synthetic audit condition' for c in cat.all_concepts())


def test_tier2_critical_cases_count_even_if_fixture_excluded():
    from evaluation.cases import SyntheticCase
    c = SyntheticCase(case_id='new', chief_complaint='weakness', demographics={},
                      ground_truth_diagnosis='tier2:guillain_barre', scoring_expected=False)
    assert c.critical


def test_summary_does_not_hide_labeled_tier2_or_reward_unknown_misdiagnosis():
    from evaluation.simulator import CaseResult
    from evaluation.benchmark import compute_summary
    base = dict(turns=1, ask_count=0, exam_count=0, test_count=0, duplicate_actions=0,
                unnecessary_tests=0, malformed_turns=0, failed_to_diagnose=False)
    results = [CaseResult(case_id='extra', ground_truth='tier2:pericarditis',
                         final_diagnosis='wrong', correct=False, critical=True, critical_miss=True,
                         scoring_expected=False, **base),
               CaseResult(case_id='uncertain', ground_truth='unknown', final_diagnosis='wrong',
                          correct=False, critical=False, critical_miss=False, scoring_expected=False, **base)]
    s=compute_summary(results)
    assert s['n_scored_cases']==1
    assert s['scored_diagnostic_accuracy']==0
    assert s['unsupported_case_success_rate']==0
    assert s['critical_miss_rate']==1


def test_runtime_prompt_receives_broad_candidates():
    from nova_agent.orchestrator import DoctorAgent
    from nova_agent.llm_client import MockLLMClient
    class Capture(MockLLMClient):
        def generate_turn_output(self, ctx):
            self.ctx=ctx
            return super().generate_turn_output(ctx)
    client=Capture();agent=DoctorAgent(llm_client=client)
    agent.decide(agent.new_case('fresh','Acute Pericarditis'))
    snippets=[s for s in client.ctx.retrieved_context if s['source']=='catalog_retrieval_unverified_hypotheses']
    assert snippets
    candidates=json.loads(snippets[0]['text'])['llm_candidates']
    assert any(c['concept_id']=='tier2:pericarditis' for c in candidates)
    assert all('evidence_warning' in c for c in candidates)


def test_error_fallback_abstains_at_turn_limit():
    from nova_agent.orchestrator import DoctorAgent
    agent=DoctorAgent();s=agent.new_case('err','vague concern',max_turns=1)
    assert agent._safe_fallback(s).content=='unknown'
