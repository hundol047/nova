"""Engineering regression for question/answer binding, not clinical accuracy.

Same fixed inputs can run unchanged in a baseline checkout. No model, sample
keys, patient identifiers, gold diagnoses or live API calls are used.
"""
import argparse,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.append(str(ROOT/'tests'))
for key,value in [('NOVA_LLM_PROVIDER','mock'),('NOVA_COMPETITION_RETRIEVAL','1'),('NOVA_PRELIMINARY_RULES','1')]:os.environ[key]=value
from nova_agent.config import get_config
get_config(reload=True)
from test_official_independent_audit import encounter,initialise

CASES=[('손 떨림이 있나요?','tremor'),('더위를 많이 타시나요?','heat intolerance'),
       ('발열이 있나요?','fever'),('토하셨나요?','vomiting'),
       ('소변볼 때 따가운가요?','dysuria'),('심장이 두근거리나요?','palpitations')]
AMBIGUOUS=['어머니 손이 떨리나요?','손이 떨리거나 땀이 나나요?',
           '손이 떨리지 않나요?','과거에 손이 떨렸나요?',
           '체중이 몇 kg 줄었나요?','다른 증상이 있나요?']

def run():
 rows=[]
 for question,feature in CASES:
  for reply,polarity in [('네','positive'),('아닙니다','negative'),('모르겠어요','unknown')]:
   e,_=encounter();initialise(e,'불편해요')
   e._absorb('ASK','associated_symptoms',question,reply)
   positive=feature in e.pstate.pertinent_positives
   negative='no '+feature in e.pstate.pertinent_negatives
   unknown=feature in e.pstate.unknown_findings
   expected={'positive':positive and not negative,'negative':negative and not positive,'unknown':unknown and not positive and not negative}[polarity]
   rows.append({'question':question,'reply':reply,'expected_feature':feature,'expected_polarity':polarity,'passed':expected,'state_positive':positive,'state_negative':negative,'state_unknown':unknown,'recorded_actions':len(e.pstate.performed_actions)})
 guards=[]
 for q in AMBIGUOUS:
  e,_=encounter();initialise(e,'불편해요');e._absorb('ASK','associated_symptoms',q,'네')
  guards.append({'question':q,'passed':not e.pstate.pertinent_positives,'positives':e.pstate.pertinent_positives})
 return {'label':'SCRIPTED QUESTION/ANSWER TRANSFER REGRESSION; NOT DIAGNOSTIC ACCURACY OR OFFICIAL SCORE','binding_passed':sum(r['passed'] for r in rows),'binding_cases':len(rows),'ambiguity_guard_passed':sum(r['passed'] for r in guards),'ambiguity_cases':len(guards),'extra_model_calls':0,'cases':rows,'ambiguity_guards':guards}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();r=run();Path(a.output).write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in {'cases','ambiguity_guards'}}))
