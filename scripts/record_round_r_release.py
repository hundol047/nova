"""Bind Round R executed evidence to committed runtime; no inherited stale runtime metrics."""
import argparse,hashlib,json,shutil,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
def read(p):return json.loads((ROOT/p).read_text())
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def write(p,v):(ROOT/p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--runtime',required=True)
 p.add_argument('--executed-runtime',help='Actual local execution commit when GitHub API recreated identical trees')
 a=p.parse_args();executed=a.executed_runtime or a.runtime
 trees={s:subprocess.check_output(['git','rev-parse',s+'^{tree}'],cwd=ROOT,text=True).strip() for s in {a.runtime,executed}}
 assert trees[a.runtime]==trees[executed], 'Published and executed runtime trees differ'
 base='artifacts/round_r/final/'
 from scripts.evaluate_round_r import hashes
 runtime=hashes(ROOT)
 runtime.update({n:sha(n) for n in ('submission/run.py','submission/requirements.txt')})
 for n,h in runtime.items():
  assert (ROOT/n).read_bytes()==subprocess.check_output(['git','show',a.runtime+':'+n],cwd=ROOT),n
 reg=read(base+'regressions.json');assert reg['runtime_unchanged_during_execution']
 assert reg['runtime_sha256']=={n:h for n,h in runtime.items() if not n.startswith('submission/')}
 new=read(base+'new_validation/summary.json')
 assert new['runtime_sha256']==reg['runtime_sha256'] and new['runtime_unchanged']
 assert new['fixture_sha256']==read('evaluation/frozen_validation_round_r_manifest.json')['sha256']
 junit=[base+'pytest_runtime.xml',base+'pytest_research.xml']
 if (ROOT/base/'pytest_release.xml').exists():junit.append(base+'pytest_release.xml')
 cases=[c for n in junit for c in ET.parse(ROOT/n).getroot().iter('testcase')]
 assert len({(c.get('classname'),c.get('name')) for c in cases})==len(cases)
 assert not any(c.find('failure') is not None or c.find('error') is not None for c in cases)
 skipped=[{'test':c.get('classname')+'.'+c.get('name'),'reason':c.find('skipped').get('message')} for c in cases if c.find('skipped') is not None]
 audit=read(base+'package_audit.json')
 package_validation=read(base+'zip_validation.json')
 assert package_validation['all_pass'] and package_validation['sha256']==audit['zip_sha256']
 assert audit['source_submission_byte_equivalence'] and audit['secret_scan']['status']=='PASS'
 assert not any(audit[k] for k in ('sync_mismatches','forbidden_files','training_operations','utf8_failures'))
 package='artifacts/verification/nova-pre-guide-v23.zip'
 shutil.copyfile(ROOT/'submission/submission.zip',ROOT/package);assert sha(package)==audit['zip_sha256']
 m=read(base+'round_m_verified/final_summary.json')
 assert m['runtime_sha256']==reg['runtime_sha256']
 tests={'passed':len(cases)-len(skipped),'failed':0,'skipped':len(skipped),'skip_reasons':skipped,
        'deselected':0 if len(junit)==3 else 3,'not_executed':[] if len(junit)==3 else ['release consistency: 3 tests pending'],
        'scope':'Complete tests/ in disjoint processes (runtime, 3 NCIt research tests, 3 release binding tests).',
        'junit_files':{n:sha(n) for n in junit}}
 artifact='artifacts/verification/local-release-'+a.runtime[:7]+'-v23.json'
 data=dict(schema='nova-verification-v23',status='NOT READY',local_validation_status='ENGINEERING_REGRESSION_VERIFIED; NEW_CASE_SAFETY_INCOMPLETE',
   external_status='EXTERNAL_OFFICIAL_INTERFACE_BLOCKED',official_api_status='NOT VERIFIED',real_model_status='NOT VERIFIED',
   schema_status='PLACEHOLDER',official_submission_allowed=False,new_blind_runs=0,fresh_final_blind='NOT YET AUTHORED',
   generated_utc=datetime.now(timezone.utc).isoformat(),audited_remote_head='02e56eb8e97ba0b6ce09061091d64222fee1c37a',
   verified_runtime_sha=a.runtime,executed_local_runtime_sha=executed,runtime_sha256=runtime,runtime_changed_after_freeze=False,
   publication_equivalence={'identical_git_tree':trees[a.runtime],'executed_local_commit':executed,'published_commit':a.runtime,
   'note':'GitHub API changes commit metadata; complete Git trees and every runtime/archive byte were verified identical. Execution records retain their original commit IDs.'},
   tests=tests,source_submission_sync=True,submission={'zip':package,'bytes':(ROOT/package).stat().st_size,'sha256':sha(package)},
   round_m=m['metrics'],round_m_artifact=base+'round_m_verified/final_summary.json',failure_analysis_artifact=base+'round_m_verified/failure_analysis.json',
   regressions={n:r['summary'] for n,r in reg['suites'].items()},
   preliminary=read(base+'prelim.json')['summaries'],new_validation={'summary':new['summary'],'behavior':new['behavior'],
   'artifact':base+'new_validation/summary.json','limitation':'24 engineer-authored synthetic cases; author saw implementation and development failures. Not independent clinical validation.'},
   report='docs/competition/ROUND_R_REPAIR_REPORT_KO.md',
   acceptance={'implemented_regressions':'PASS','offline_implementation':'FAIL: full work order incomplete; residual unknown-answer, semantic evidence and final-decision defects',
   'new_case_clinical_safety':'FAIL: NewR_18 unsupported orthostatic label and routine disposition','package':'PASS','real_llm_and_official_interface':'NOT VERIFIED'},
   provenance='Legacy clinical/licence gaps remain UNRESOLVED; docs/compliance/LLM_GENERATION_LOG.md records new guard sources.')
 write(artifact,data)
 pointer=read('artifacts/verification/CURRENT_RELEASE.json');previous=pointer['current_verification_artifact']
 history=pointer['previous_verification_artifacts']
 if previous!=artifact:history=list(dict.fromkeys([previous]+history))
 pointer.update(current_verification_artifact=artifact,current_verification_schema='nova-verification-v23',verified_runtime_sha=a.runtime,previous_verification_artifacts=history)
 pointer['reason']='Local regression/package checks passed; NewR_18 clinical safety and other documented defects remain. Official interface, real model and rights clearance unverified.'
 write('artifacts/verification/CURRENT_RELEASE.json',pointer)
 print(json.dumps({'artifact':artifact,'tests':tests,'zip_sha256':sha(package)},indent=2))
if __name__=='__main__':main()
