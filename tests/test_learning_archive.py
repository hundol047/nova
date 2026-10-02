import copy
import json
import pytest
from evaluation.cases import CASES
from evaluation.learning_archive import digest, save_snapshot, snapshot
from evaluation.source_fingerprint import source_sha256


def fixture():
    cases = [CASES[0].model_copy(deep=True), CASES[1].model_copy(deep=True)]
    cases[1].scoring_expected = False
    records = [{'case_id':c.case_id, 'correct':True, 'scoring_expected':c.scoring_expected,
                'critical_miss':False, 'duplicate_actions':0, 'malformed_turns':0,
                'final_diagnosis':c.ground_truth_diagnosis} for c in cases]
    report = {'provider':'mock', 'independent_validation':False, 'clinical_accuracy_claim':False,
              'passed':True, 'sets':{'tuning':{'cases_sha256':digest([c.model_dump() for c in cases]), 'cases':records}}}
    return report, {'tuning':cases}


def test_archive_preserves_complete_case_and_is_idempotent(tmp_path):
    r,c=fixture();p=save_snapshot(r,c,tmp_path)
    assert save_snapshot(r,c,tmp_path)==p
    assert len(list(tmp_path.glob('*.json')))==1
    saved=json.loads(p.read_text())
    assert saved['counts']=={'passed':1,'failed':0,'unscored':1}
    assert saved['records'][0]['case']==c['tuning'][0].model_dump()
    assert saved['records'][0]['review_route']=='synthetic_training_candidate_review'
    assert saved['records'][1]['review_route']=='evaluation_only_do_not_train'
    assert not any(x['training_eligible'] for x in saved['records'])


def test_new_outcomes_append_and_keep_failures_without_overwriting(tmp_path):
    r,c=fixture();first=save_snapshot(r,c,tmp_path)
    r['sets']['tuning']['cases'][0]['duplicate_actions']=1;r['passed']=False
    second=save_snapshot(r,c,tmp_path)
    assert first!=second and first.exists()
    assert json.loads(second.read_text())['counts']['failed']==1


@pytest.mark.parametrize('mutation',['mock','hash','partial','duplicate','forged_correct','aggregate','boolean'])
def test_invalid_archive_input_is_rejected(tmp_path,mutation):
    r,c=fixture()
    if mutation=='mock':r['provider']='real'
    if mutation=='hash':r['sets']['tuning']['cases_sha256']='bad'
    if mutation=='partial':r['sets']['tuning']['cases'].pop()
    if mutation=='duplicate':r['sets']['tuning']['cases'][1]=r['sets']['tuning']['cases'][0]
    if mutation=='forged_correct':r['sets']['tuning']['cases'][0]['correct']=False
    if mutation=='aggregate':r['passed']=False
    if mutation=='boolean':r['sets']['tuning']['cases'][0]['correct']='true'
    with pytest.raises(ValueError):save_snapshot(r,c,tmp_path)
    assert not list(tmp_path.glob('*.json'))


def test_corrupt_existing_snapshot_cannot_be_overwritten(tmp_path):
    r,c=fixture();p=save_snapshot(r,c,tmp_path);p.write_text('corrupt')
    with pytest.raises(ValueError,match='corrupt'):save_snapshot(r,c,tmp_path)
    assert p.read_text()=='corrupt'


def test_reports_and_archives_do_not_change_code_fingerprint(tmp_path):
    (tmp_path/'nova_agent').mkdir();(tmp_path/'evaluation').mkdir()
    code=tmp_path/'nova_agent'/'example.py';code.write_text('a = 1')
    before=source_sha256(tmp_path)
    (tmp_path/'evaluation'/'report.json').write_text('{}')
    archive=tmp_path/'evaluation'/'learning_archive';archive.mkdir()
    (archive/'snapshot.json').write_text('{}')
    assert source_sha256(tmp_path)==before
    code.write_text('a = 2');assert source_sha256(tmp_path)!=before
