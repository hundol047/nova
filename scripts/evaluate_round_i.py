"""Development-only stage trace. Never called by the clinical runtime or blind runner."""
import argparse
import json
import statistics
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.generalization_dev_cases_round_i import ROUND_I_CASES, ROUND_I_OOD
from evaluation.simulator import PatientSimulator
from nova_agent.orchestrator import DoctorAgent
from nova_agent.llm_client import MockLLMClient
from nova_agent.diagnosis_normalizer import same_diagnosis
from nova_agent.matching import content_words
from nova_agent.severity_evidence import GENERIC_PHYSIOLOGIC_SEVERITY_WORDS
from nova_agent.objective_evidence import normalize_objective_evidence
from competition.adapter import action_to_competition
import nova_agent.differential as de
import nova_agent.retrieval_pipeline as rp


def diagnose(case):
    agent = DoctorAgent(llm_client=MockLLMClient()); state = agent.new_case(case.case_id, case.chief_complaint, case.demographics)
    simulator = PatientSimulator(case); trajectory = []
    original_score = de._score_disease; original_retrieve = rp.retrieve_high_recall; original_rerank = rp.lightweight_rerank
    for _ in range(state.max_turns):
        scored = {}; retrieved = []; reranked = []
        def score(entry, *args, **kwargs):
            result = original_score(entry, *args, **kwargs)
            scored[entry['id']] = (entry, result)
            return result
        def retrieve(*args, **kwargs):
            result = original_retrieve(*args, **kwargs); retrieved.extend(result); return result
        def rerank(*args, **kwargs):
            result = original_rerank(*args, **kwargs); reranked.extend(result); return result
        with patch.object(de, '_score_disease', score), patch.object(rp, 'retrieve_high_recall', retrieve), patch.object(rp, 'lightweight_rerank', rerank):
            action, _, differential = agent.decide(state)
        def matching(obj):
            return same_diagnosis(obj, case.ground_truth_diagnosis)
        def hit_rank(hits):
            return next((i+1 for i,h in enumerate(hits) if matching(h.concept.concept_id) or matching(h.concept.canonical_name)), None)
        rank = next((d.rank for d in differential if matching(d.diagnosis_id) or matching(d.diagnosis)), None)
        target = next(((entry, result) for entry, result in scored.values() if matching(entry['id']) or matching(entry['name'])), None)
        trace = {'turn': state.turn_count+1, 'retrieved': hit_rank(retrieved) is not None,
            'retrieval_rank': hit_rank(retrieved), 'rerank_rank': hit_rank(reranked), 'active_differential_rank': rank,
            'candidate_scored': target is not None, 'selected_action': action.action_type,
            'action_key': action.key, 'top10': [d.diagnosis_id for d in differential[:10]],
            'negative_evidence': list(state.pertinent_negatives), 'medication_evidence': list(state.medication_text),
            'objective_evidence': {k:v.evidence_label for k,v in normalize_objective_evidence(state).items()}}
        if target:
            entry, result = target
            # Counterfactual component contributions; cap makes generic/specific contributions
            # non-additive. These are exact scorer deltas, not probabilities or causal claims.
            empty = dict(entry, typical_features=[], risk_factors=[], confirmatory_findings=[], reassuring_if_present=[])
            baseline = original_score(empty, state)[0]
            generic = [f for f in entry.get('typical_features', []) if content_words(f) and content_words(f).issubset(GENERIC_PHYSIOLOGIC_SEVERITY_WORDS)]
            specific = [f for f in entry.get('typical_features', []) if f not in generic]
            score_for = lambda **kw: original_score(dict(empty, **kw), state)[0] - baseline
            trace.update(total_score=result[0], specific_evidence_score=score_for(typical_features=specific),
                generic_evidence_score=score_for(typical_features=generic),
                objective_score=score_for(confirmatory_findings=entry.get('confirmatory_findings', [])) + baseline,
                risk_score=score_for(risk_factors=entry.get('risk_factors', [])),
                supporting_evidence=result[2], contradictions=result[3],
                risk_evidence=[f for f in result[2] if f in entry.get('risk_factors', [])])
        else:
            trace.update(total_score=None, specific_evidence_score=None, generic_evidence_score=None,
                         objective_score=None, risk_score=None, risk_evidence=[], supporting_evidence=[], contradictions=[])
        trajectory.append(trace)
        agent.observe(state, action, simulator.respond(action))
        if action.action_type == 'DIAGNOSE':
            break
    final = trajectory[-1]; correct = same_diagnosis(state.final_diagnosis or '', case.ground_truth_diagnosis)
    failure = None if correct else ('RETRIEVAL_MISS' if not final['retrieved'] and not final['candidate_scored'] else
        'RERANK_DROP' if final['retrieved'] and final['rerank_rank'] is None and not final['candidate_scored'] else
        'ACTIVE_DIFFERENTIAL_DROP' if final['active_differential_rank'] is None else 'RANKING_OR_STOP_ERROR')
    return dict(case_id=case.case_id, ground_truth=case.ground_truth_diagnosis, scored=case.scoring_expected,
        critical=case.critical, correct=correct, final=state.final_diagnosis, final_rank=rank,
        turns=state.turn_count, test_count=sum(t['selected_action']=='TEST' for t in trajectory),
        failure_stage=failure, trajectory=trajectory)


def uncertainty():
    agent = DoctorAgent(llm_client=MockLLMClient()); rows=[]
    for i,(group,text) in enumerate(ROUND_I_OOD):
        state=agent.new_case(f'I_ood_{i}',text,max_turns=1); action,_,_=agent.decide(state)
        wire=action_to_competition(state.case_id,action,evidence_assessment=state.evidence_assessment)
        rows.append(dict(id=i,group=group,result=state.evidence_assessment['internal_result'],
            forced=wire.metadata['forced_due_to_protocol'],assessment=state.evidence_assessment))
    def rate(items,predicate):
        return dict(numerator=sum(predicate(r) for r in items),denominator=len(items),
                    rate=sum(predicate(r) for r in items)/len(items) if items else None)
    ood=[r for r in rows if r['group'] in {'nonmedical','administrative','medication_question'}]
    supported=[r for r in rows if r['group'] in {'supported_sparse','hard_supported','mixed_medical'}]
    unsupported=[r for r in rows if r not in supported]
    return {'data_type':'FRESH SYNTHETIC DEVELOPMENT', 'cases':len(rows),'metrics':{
        'true_ood_detection':rate(ood,lambda r:r['result']=='OUT_OF_DOMAIN'),
        'supported_false_ood':rate(supported,lambda r:r['result']=='OUT_OF_DOMAIN'),
        'insufficient_information':rate(rows,lambda r:r['result']=='INSUFFICIENT_INFORMATION'),
        'insufficient_information_detection':rate([r for r in rows if r['group'] in {'unsupported_medical','contradictory','nonsense'}],lambda r:r['result']=='INSUFFICIENT_INFORMATION'),
        'unsafe_confident_unsupported':rate(unsupported,lambda r:r['result']=='SUPPORTED_DIAGNOSIS'),
        'protocol_forced_diagnosis':rate(rows,lambda r:r['forced']),
        'hard_supported_retained':rate([r for r in supported if r['group']=='hard_supported'],lambda r:r['result']!='OUT_OF_DOMAIN')},'rows':rows}


def evaluate():
    rows=[diagnose(c) for c in ROUND_I_CASES];scored=[r for r in rows if r['scored']];critical=[r for r in scored if r['critical']]
    ranks=[r['final_rank'] for r in scored if r['final_rank'] is not None]
    top=lambda rs,k:sum(r['final_rank'] is not None and r['final_rank']<=k for r in rs)/len(rs) if rs else None
    metrics={f'Top{k}':top(scored,k) for k in [1,3,5,10]}
    metrics.update(MRR=sum(1/r['final_rank'] if r['final_rank'] else 0 for r in scored)/len(scored),
        median_true_rank=statistics.median(ranks) if ranks else None, missing_rank_count=len(scored)-len(ranks),
        median_definition='retrieved active ranks only; missing ranks separately reported',
        critical_Top1=top(critical,1),critical_Top5=top(critical,5),critical_count=len(critical),
        diagnosis_accuracy=sum(r['correct'] for r in scored)/len(scored),
        critical_recall=sum(r['correct'] for r in critical)/len(critical),scored_cases=len(scored))
    return dict(data_type='SYNTHETIC DEVELOPMENT / COMPETITION-STRUCTURE MOCK-LLM', independent_clinical_validation=False,
        expert_reviewed=False,ranking=metrics,cases=rows,ood=uncertainty())


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();result=evaluate()
    for row in result['cases']:
        if row['correct']:
            row['trajectory'] = [row['trajectory'][-1]]
            row['trace_retention'] = 'final turn only for correct case; full trajectory retained for every error'
    Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'ranking':result['ranking'],'ood':result['ood']['metrics'],'errors':[(r['case_id'],r['final'],r['failure_stage']) for r in result['cases'] if r['scored'] and not r['correct']]},indent=2))
