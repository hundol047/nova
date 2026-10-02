"""Audit plumbing fixtures only; these are not independent clinical validation."""
import copy
import pytest
from evaluation.cases import SyntheticCase
from evaluation.candidate_validation import audit, readiness, wilson


def fixtures():
    cases = [SyntheticCase(case_id=str(i), chief_complaint='fixture', demographics={},
             ground_truth_diagnosis='hypoglycemia' if i < 40 else 'migraine') for i in range(80)]
    metadata = {'sha256': 'a'*64, 'independence_verified': False}
    cfg = {'real_verification_mode': 'every_decision', 'case_manifest': metadata,
           'case_ids': [c.case_id for c in cases], **{k:'b'*64 for k in
           ('source_sha256','catalog_sha256','reference_catalog_sha256','config_sha256')}}
    report = {'provider_is_real': True, 'provider': 'fixture', 'model': 'fixture', 'run_config': cfg,
      'cases': [{'case_id':c.case_id, 'ground_truth':c.ground_truth_diagnosis,
          'final_diagnosis':c.ground_truth_diagnosis, 'all_decisions_real':True, 'real_llm_verified':True,
          'turns':1,'llm_successes':1,'llm_calls':1,'llm_failures':0,'fallback_count':0,'malformed_turns':0,
          'timed_out':False,'failed_to_diagnose':False, 'correct':False} for c in cases]}
    return report, copy.deepcopy(report), cases, metadata


def test_numerical_pass_is_not_clinical_approval_and_recomputes_correctness():
    b,a,c,m = fixtures()
    r = audit(b,a,c,m)
    assert r['numerical_screen_passed_count'] == 2
    assert not r['clinical_approval'] and not r['clinical_accuracy_claim']
    assert all(not x['enable_autonomous_diagnosis'] for x in r['conditions'])
    assert len(r['conditions']) == 680


@pytest.mark.parametrize('mutation', ['mock','partial','duplicate','fallback','missing_counts',
    'timeout','manifest','model','fingerprint','subset_config','label','incomplete'])
def test_invalid_evidence_fails_closed(mutation):
    b,a,c,m=fixtures()
    if mutation=='mock':a['provider_is_real']=False
    if mutation=='partial':a['cases'].pop()
    if mutation=='duplicate':a['cases'][-1]=a['cases'][0]
    if mutation=='fallback':a['cases'][0]['fallback_count']=1
    if mutation=='missing_counts':del a['cases'][0]['llm_calls']
    if mutation=='timeout':a['cases'][0]['timed_out']=True
    if mutation=='manifest':a['run_config']['case_manifest']={}
    if mutation=='model':a['model']='changed'
    if mutation=='fingerprint':a['run_config']['source_sha256']=''
    if mutation=='subset_config':a['run_config']['case_ids'].pop()
    if mutation=='label':a['cases'][0]['ground_truth']='forged label'
    if mutation=='incomplete':a['cases'][0]['all_decisions_real']=False
    with pytest.raises(ValueError):audit(b,a,c,m)


def test_new_paired_error_and_critical_miss_cannot_hide_in_high_average():
    b,a,c,m=fixtures()
    c[0].critical_override=True
    a['cases'][0]['final_diagnosis']='migraine'
    a['cases'][0]['correct']=True  # forged metric must be ignored
    r=audit(b,a,c,m)
    assert r['paired_new_errors']==['0'] and r['critical_misses']==['0']
    assert r['numerical_screen_passed_count']==0


def test_small_perfect_sample_does_not_pass():
    assert wilson(1,1)[0] < .9
    assert wilson(40,40)[0] > .9
    b,a,c,m=fixtures()
    c=c[:2]
    for r in (b,a):
        r['cases']=r['cases'][:2];r['run_config']['case_ids']=['0','1']
    assert audit(b,a,c,m)['numerical_screen_passed_count']==0


def test_empty_readiness_does_not_claim_any_validated_conditions():
    r=readiness()
    assert len(r['conditions'])==680
    assert r['numerical_screen_passed_count']==0 and not r['clinical_approval']
