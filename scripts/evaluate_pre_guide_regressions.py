"""All requested development suites on one frozen runtime; never imports blind cases."""
import concurrent.futures,json,importlib,subprocess,sys,os,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from evaluation.benchmark import run_all,compute_summary
SUITES={'held_out':('evaluation.held_out_cases','HELD_OUT_CASES'),'generalization_v2':('evaluation.generalization_cases_v2','GENERALIZATION_CASES_V2'),'stress':('evaluation.generalization_stress_cases','GENERALIZATION_STRESS_CASES')}
for r in ('d','e','g','i','j'):
 SUITES['round_'+r]=('evaluation.generalization_dev_cases_round_'+r, 'GENERALIZATION_DEV_CASES_ROUND_'+r.upper() if r in ('d','e') else 'ROUND_'+r.upper()+'_CASES')
def evaluate(item):
 name,(module,var)=item;cases=getattr(importlib.import_module(module),var)
 results=run_all(cases)
 return name,{'summary':compute_summary(results),'cases':[r.model_dump() for r in results]}
def runtime_hashes():
 from scripts.runtime_identity import tracked_runtime_hashes
 return tracked_runtime_hashes(ROOT)
def main():
 hashes=runtime_hashes()
 result={'runtime_sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'runtime_sha256':hashes,'mode':'competition retrieval / mock LLM','suites':{},'runtime_unchanged_during_execution':False}
 with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
  for name,rows in pool.map(evaluate,SUITES.items()):
   result['suites'][name]=rows; print(name,rows['summary'],flush=True)
   (ROOT/os.environ.get('NOVA_REGRESSION_OUTPUT','artifacts/round_m/final_regressions.json')).write_text(json.dumps(result,indent=2)+'\n')
 assert hashes==runtime_hashes(), 'Runtime changed during regression execution; evidence cannot be released'
 result['runtime_unchanged_during_execution']=True
 (ROOT/os.environ.get('NOVA_REGRESSION_OUTPUT','artifacts/round_m/final_regressions.json')).write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
