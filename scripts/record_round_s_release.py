"""Bind real executed Round S evidence to the committed runtime and ZIP.

No metrics are carried forward from an earlier runtime. Detailed XML and traces
are local review evidence; aggregate records do not imply publication approval.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.evaluate_round_r import hashes

def read(p):return json.loads((ROOT/p).read_text())
def digest(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def write(p,d):
    target=ROOT/p;target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);a=p.parse_args()
    base='artifacts/round_s/final/'
    runtime=hashes(ROOT)
    runtime.update({n:digest(n) for n in ('submission/run.py','submission/requirements.txt')})
    for n,h in runtime.items():
        assert (ROOT/n).read_bytes()==subprocess.check_output(['git','show',a.runtime+':'+n],cwd=ROOT),n
    expected={n:h for n,h in runtime.items() if not n.startswith('submission/')}
    reg=read(base+'regressions.json');assert reg['runtime_unchanged_during_execution']
    assert reg['runtime_sha256']==expected
    new=read(base+'new_validation/summary.json');assert new['runtime_unchanged']
    assert new['runtime_sha256']==expected
    assert new['fixture_sha256']==read('evaluation/frozen_validation_round_s_manifest.json')['sha256']
    m=read(base+'round_m/final_summary.json');assert m['runtime_sha256']==expected
    files=[base+'pytest_runtime.xml',base+'pytest_research.xml']
    if (ROOT/base/'pytest_release.xml').exists():files.append(base+'pytest_release.xml')
    cases=[c for n in files for c in ET.parse(ROOT/n).getroot().iter('testcase')]
    assert len({(c.get('classname'),c.get('name')) for c in cases})==len(cases)
    failed=[c for c in cases if c.find('failure') is not None or c.find('error') is not None]
    assert not failed
    skipped=[{'test':c.get('classname')+'.'+c.get('name'),'reason':c.find('skipped').get('message')}
             for c in cases if c.find('skipped') is not None]
    tests={'passed':len(cases)-len(skipped),'failed':0,'skipped':len(skipped),'skip_reasons':skipped,
           'deselected':0 if len(files)==3 else 3,'not_executed':[] if len(files)==3 else ['3 release-binding tests pending'],
           'scope':'Complete tests/ in disjoint runtime, NCIt research and release-binding processes.',
           'local_detailed_junit_fingerprints':{n:digest(n) for n in files},'detailed_xml_public':False}
    audit=read(base+'package_audit.json');validation=read(base+'zip_validation.json')
    assert audit['source_submission_byte_equivalence'] and validation['all_pass']
    assert audit['secret_scan']['status']=='PASS'
    package='artifacts/verification/nova-pre-guide-v24.zip'
    assert digest(package)==audit['zip_sha256']==validation['sha256']
    import zipfile
    with zipfile.ZipFile(ROOT/package) as z:
        for n,h in runtime.items():assert hashlib.sha256(z.read(n.removeprefix('submission/'))).hexdigest()==h
    artifact='artifacts/verification/local-release-'+a.runtime[:7]+'-v24.json'
    data={'schema':'nova-verification-v24','status':'NOT READY','verified_runtime_sha':a.runtime,
          'executed_local_runtime_sha':a.runtime,'runtime_sha256':runtime,
          'generated_utc':datetime.now(timezone.utc).isoformat(),'runtime_changed_after_freeze':False,
          'reasoning_freeze_artifact':base+'reasoning_freeze.json',
          'new_validation_attempt_disclosure':{
              'baseline_incomplete_unread_attempts':1,'baseline_trace_files_before_interrupt':22,
              'final_runtime_attempts_before_final_freeze':0,
              'reason':'Existing Round J unit-test regression; no new-case outputs inspected; fixture/scorer unchanged.',
              'record':'artifacts/round_s/development/candidate_5b15a56/reasoning_freeze.json'},
          'official_api_status':'NOT VERIFIED','real_model_status':'NOT VERIFIED','schema_status':'PLACEHOLDER',
          'official_submission_allowed':False,'new_blind_runs':0,'fresh_final_blind':'NOT YET AUTHORED',
          'tests':tests,'source_submission_sync':True,
          'submission':{'zip':package,'bytes':(ROOT/package).stat().st_size,'sha256':digest(package)},
          'round_m':m['metrics'],'round_m_artifact':base+'round_m/final_summary.json',
          'failure_analysis_artifact':base+'round_m/failure_analysis.json',
          'preliminary':read(base+'prelim.json')['summaries'],
          'regressions':{n:r['summary'] for n,r in reg['suites'].items()},
          'new_validation':{'artifact':base+'new_validation/summary.json','summary':new['summary'],
                            'behavior':new['behavior'],'limitation':new['limitation']},
          'report':'docs/competition/ROUND_S_REPAIR_REPORT_KO.md',
          'acceptance':'See report: numerical/regression/behavior/clinical limitations are separate; not a perfect-score claim.',
          'publication':'Local complete evidence; public source review is separately identified. Do not infer publication of detailed traces.'}
    write(artifact,data);write(base+'test_summary.json',tests)
    pointer=read('artifacts/verification/CURRENT_RELEASE.json')
    old=pointer['current_verification_artifact']
    pointer.update(current_verification_artifact=artifact,current_verification_schema='nova-verification-v24',
                   verified_runtime_sha=a.runtime,reason='Round S offline structural repairs; remaining clinical/performance gaps and official/real-model verification documented in report.')
    if old!=artifact:pointer['previous_verification_artifacts']=list(dict.fromkeys([old]+pointer['previous_verification_artifacts']))
    write('artifacts/verification/CURRENT_RELEASE.json',pointer)
    print(json.dumps({'artifact':artifact,'tests':tests,'zip_sha256':digest(package)},indent=2))

if __name__=='__main__':main()
