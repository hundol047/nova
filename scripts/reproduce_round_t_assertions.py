"""Offline diagnosis-assertion contrasts through extraction and candidate scoring.

No label is supplied to the engine. Expectations are checked only on the output.
Full encounter behavior is evaluated separately by evaluate_round_s.py.
"""
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ['NOVA_LLM_PROVIDER']='mock';os.environ['NOVA_COMPETITION_RETRIEVAL']='1'
from nova_agent.config import get_config
from nova_agent.documented_diagnosis import documented_diagnosis_ids
from nova_agent.differential import DifferentialEngine
from nova_agent.state import PatientState
get_config(reload=True)
CASES=[
 ('The referral letter says atrial fibrillation was excluded',[]),
 ('진단서에 atrial fibrillation 아니라고 적혀 있습니다',[]),
 ('The letter confirms atrial fibrillation but excludes pulmonary embolism',['cardiac_arrhythmia']),
 ('The letter confirms atrial fibrillation; the patient has no fever',['cardiac_arrhythmia']),
 ('The letter says pulmonary embolism cannot be excluded',[]),
 ('The letter says pulmonary embolism was not ruled out',[]),
 ('의사 기록에는 atrial fibrillation 의심된다고 적혀 있습니다',[]),
 ('The referral confirms that my father has atrial fibrillation',[]),
 ('The letter records a past history of atrial fibrillation',[]),
 ('The cardiology report confirms current atrial fibrillation',['cardiac_arrhythmia']),
]
rows=[]
for text,expected in CASES:
 ids=documented_diagnosis_ids([text])
 diff=DifferentialEngine().update(PatientState(chief_complaint=text,preliminary_rules=True))
 supported=[d.diagnosis_id for d in diff if 'documented diagnosis' in d.supporting_evidence]
 rows.append({'input':text,'expected':expected,'extracted':ids,'documented_support_ids':supported,
              'pass':set(ids)==set(expected) and set(supported)==set(expected)})
print(json.dumps({'passed':sum(r['pass'] for r in rows),'total':len(rows),'rows':rows},ensure_ascii=False,indent=2))
