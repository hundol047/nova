"""Full-loop behavior of the existing five unscored Round M controls."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from evaluation.generalization_dev_cases_round_m import ROUND_M_CASES
from evaluation.simulator import PatientSimulator
from nova_agent.orchestrator import DoctorAgent
from nova_agent.llm_client import MockLLMClient
from competition.adapter import action_to_competition
rows=[]
for c in ROUND_M_CASES:
 if c.scoring_expected:continue
 agent=DoctorAgent(MockLLMClient());s=agent.new_case(c.case_id,c.chief_complaint,c.demographics);sim=PatientSimulator(c)
 for _ in range(s.max_turns):
  a,_,_=agent.decide(s)
  if a.action_type=='DIAGNOSE':
   wire=action_to_competition(c.case_id,a,evidence_assessment=s.evidence_assessment)
  agent.observe(s,a,sim.respond(a))
  if a.action_type=='DIAGNOSE':break
 rows.append({'case_id':c.case_id,'scored':False,'turns':s.turn_count,'internal':s.evidence_assessment,'wire':wire.model_dump()})
(ROOT/'artifacts/round_m/round_m_ood.json').write_text(json.dumps({'cases':rows,'interpretation':'Forced four-action completion is not a supported diagnosis; no accuracy credit.'},indent=2)+'\n')
