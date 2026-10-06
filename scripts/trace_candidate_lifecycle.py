#!/usr/bin/env python3
"""Development-only turn traces. No patient logging or competition output changes."""
import argparse, json, sys, statistics
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from evaluation.generalization_dev_cases_round_g import ROUND_G_CASES
from evaluation.simulator import PatientSimulator
from nova_agent.orchestrator import DoctorAgent
from nova_agent.llm_client import MockLLMClient
from nova_agent.resolution import is_resolved
from nova_agent.diagnosis_normalizer import same_diagnosis
import nova_agent.differential as de
import nova_agent.retrieval_pipeline as rp


def trace_case(case):
    agent=DoctorAgent(llm_client=MockLLMClient()); state=agent.new_case(case.case_id,case.chief_complaint,case.demographics)
    sim=PatientSimulator(case); rows=[]; prior_ranks=None; seen=set(); previous_active=set(); dropped=set(); reentered=set()
    first_safe=None; first_rank1=None; counted_critical=retained_critical=0
    original_generate=de.generate_candidates; original_score=de._score_disease
    original_retrieve=rp.retrieve_high_recall; original_rerank=rp.lightweight_rerank
    while state.remaining_turns:
        pool=[]; scores={}; retrieved=[]; reranked=[]
        def gen(*a,**kw):
            value=original_generate(*a,**kw);pool.extend(value);return value
        def score(entry,*a,**kw):
            value=original_score(entry,*a,**kw);scores[entry['id']]=value;return value
        def retrieve(*a,**kw):
            value=original_retrieve(*a,**kw);retrieved.extend(value);return value
        def rerank(*a,**kw):
            value=original_rerank(*a,**kw);reranked.extend(value);return value
        with patch.object(de,'generate_candidates',gen),patch.object(de,'_score_disease',score),patch.object(rp,'retrieve_high_recall',retrieve),patch.object(rp,'lightweight_rerank',rerank):
            action,llm,differential=agent.decide(state)
        safety=agent.safety_layer.assess(state,differential)
        _,actions,stop=agent.action_selector.generate_and_select(state,differential,safety)
        raw=agent.action_selector.missing_info.analyze(state,differential,safety)
        rawchosen=next((x for x in raw if (x.action_type,x.key)==(action.action_type,action.key)),None)
        chosen=next((x for x in actions if (x.action_type,x.key)==(action.action_type,action.key)),None)
        active={d.diagnosis_id:d for d in differential};ranked=[d.diagnosis_id for d in differential]
        reentered.update(set(active)&dropped);dropped.update(previous_active-set(active));previous_active=set(active)
        if ranked and same_diagnosis(ranked[0],case.ground_truth_diagnosis) and first_rank1 is None:first_rank1=state.turn_count+1
        if stop.should_diagnose and not stop.forced and first_safe is None:first_safe=state.turn_count+1
        def ranks(hits):return {h.concept.concept_id:i+1 for i,h in enumerate(hits)}
        rr=ranks(retrieved);rk=ranks(reranked)
        candidates=[]
        for c in pool:
            sc,_,support,contra,missing=scores.get(c.id,(None,None,[],[],[]))
            resolved=is_resolved(c.id,contra,state); dangerous=bool(c.entry.get('dangerous'))
            eligible=dangerous and not resolved and (support or 'contextual_safety' in c.sources)
            counted_critical+=bool(eligible);retained_critical+=bool(eligible and c.id in active)
            cid=c.id.removeprefix('onto::')
            candidates.append(dict(id=c.id,source=c.sources,retrieval_rank=rr.get(cid),rerank_rank=rk.get(cid),score=sc,
                supporting=support,contradictions=contra,dangerous=dangerous,resolution_state='resolved' if resolved else 'unresolved',
                status='active' if c.id in active else 'dropped',drop_reason=None if c.id in active else 'DIFFERENTIAL_DROP'))
        gains=sorted((c.information_gain for c in raw),reverse=True)
        key=(action.action_type,action.key)
        rows.append(dict(turn=state.turn_count+1,action=action.model_dump(),candidates=candidates,
            active_count=len(active),unresolved_dangerous=sum(d.dangerous_if_missed and not is_resolved(d.diagnosis_id,d.contradictory_evidence,state) for d in differential),
            best_information_gain=gains[0] if gains else 0,second_information_gain=gains[1] if len(gains)>1 else 0,
            utility_components=chosen.components if chosen else {},affected_diagnoses=len(rawchosen.disease_ids_discriminated) if rawchosen else 0,
            ranking_changed_since_previous=prior_ranks is not None and prior_ranks!=ranked,duplicate=key in seen,
            malformed=llm is None, safe_stop_available=stop.should_diagnose and not stop.forced,stop_reason=stop.reason,ground_truth_present=case.ground_truth_diagnosis in active))
        seen.add(key);prior_ranks=ranked;agent.observe(state,action,sim.respond(action))
        if action.action_type=='DIAGNOSE':break
    actual=state.turn_count
    return dict(case_id=case.case_id,critical=case.critical,correct=same_diagnosis(state.final_diagnosis or '',case.ground_truth_diagnosis),final=state.final_diagnosis,
        turns=actual,first_rank1_turn=first_rank1,first_safe_diagnose_turn=first_safe,
        diagnostic_delay_turns=actual-first_safe if first_safe is not None else None,
        delay_note='Null means no non-forced safe-stop point existed; not a zero delay.',
        eligible_critical_candidate_turns=counted_critical,retained_critical_candidate_turns=retained_critical,
        candidate_dropouts=sorted(dropped),candidate_reentries=sorted(reentered),trajectory=rows)


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    result={'data_type':'SYNTHETIC DEVELOPMENT / MOCK-LLM','cases':[trace_case(c) for c in ROUND_G_CASES]}
    Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'cases':len(result['cases']),'correct':sum(c['correct'] for c in result['cases']),'avg_turns':statistics.mean(c['turns'] for c in result['cases'])}))
if __name__=='__main__':main()
