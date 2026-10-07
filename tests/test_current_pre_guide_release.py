"""Current evidence checks independent of immutable historical verification artifacts."""
import hashlib,json,subprocess,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(path):return json.loads((ROOT/path).read_text())
def current():
 p=load('artifacts/verification/CURRENT_RELEASE.json');d=load(p['current_verification_artifact'])
 assert p['current_verification_schema']==d['schema']
 assert d['schema'] in {'nova-verification-v12','nova-verification-v13','nova-verification-v14','nova-verification-v15','nova-verification-v16','nova-verification-v17','nova-verification-v18','nova-verification-v19'}
 assert p['verified_runtime_sha']==d['verified_runtime_sha']
 return d

def test_current_runtime_exact_archive_and_commit():
 d=current()
 with zipfile.ZipFile(ROOT/d['submission']['zip']) as z:
  for name,h in d['runtime_sha256'].items():
   data=(ROOT/name).read_bytes()
   assert hashlib.sha256(data).hexdigest()==h
   assert data==subprocess.check_output(['git','show',d['verified_runtime_sha']+':'+name],cwd=ROOT)
   assert data==z.read(name.removeprefix('submission/'))
 assert d['submission']['bytes']<50_000_000
 assert hashlib.sha256((ROOT/d['submission']['zip']).read_bytes()).hexdigest()==d['submission']['sha256']

def test_current_blind_and_readiness_are_honest():
 from evaluation.current_blind import CURRENT_BLIND_STATUS,reference_only_versions
 d=current()
 assert CURRENT_BLIND_STATUS=='REFERENCE-ONLY' and 'v19' in reference_only_versions()
 assert d['new_blind_runs']==0 and d['fresh_final_blind']=='NOT YET AUTHORED'
 for n in ('blind_v19_attempt.json','blind_v19_results.json'):
  assert not (ROOT/'artifacts/blind_runs'/n).exists()
 assert not (ROOT/'evaluation/blind_v19_manifest.json').exists()
 assert not (ROOT/'evaluation/blind_cases_v20.py').exists()
 assert d['official_api_status']==d['real_model_status']=='NOT VERIFIED'
 assert d['schema_status']=='PLACEHOLDER' and d['status']=='NOT READY'

def test_complete_round_m_denominators_and_failure_coverage():
 from evaluation.generalization_dev_cases_round_m import ROUND_M_CASES
 d=current();s=load(d['round_m_artifact']);rows=s['cases'];f=load(d.get('failure_analysis_artifact','artifacts/round_m/failure_analysis.json'))
 assert len(rows)==len(ROUND_M_CASES)==128
 assert sum(r['scored'] for r in rows)==sum(c.scoring_expected for c in ROUND_M_CASES)==123
 assert {r['case_id'] for r in rows}=={c.case_id for c in ROUND_M_CASES}
 assert {r['case_id'] for r in rows if r['scored'] and not r['correct']}=={x['case_id'] for x in f['failures']}
 assert d['tests']['failed']==0
 assert d['round_m']==s['metrics']
