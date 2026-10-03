#!/usr/bin/env python3
"""Complete development-only candidate traces; never imported by the submitted runtime.

Observes raw per-query ranks, exact weighted RRF sums, rerank and active stages. Scores
are heuristics, not probabilities. Lossless tar.xz archives retain *all* candidate/turn records.
Primary error attribution is a deterministic diagnostic heuristic with supporting facts,
not expert clinical adjudication. It cannot prove a medical diagnosis from a scripted label.
"""
import argparse
from collections import Counter
import gzip
import io
import tarfile
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.generalization_dev_cases_round_j import ROUND_J_CASES
from evaluation.simulator import PatientSimulator
from nova_agent.orchestrator import DoctorAgent
from nova_agent.llm_client import MockLLMClient
from nova_agent.diagnosis_normalizer import same_diagnosis
from nova_agent.matching import content_words
from nova_agent.severity_evidence import GENERIC_PHYSIOLOGIC_SEVERITY_WORDS
from nova_agent.resolution import is_resolved
from nova_agent.missing_info import _resolve_entry
from nova_agent.syndrome_relationships import syndrome_role
try:
    from nova_agent.syndrome_relationships import supported_source_syndrome_pairs
except ImportError:  # Historical runtime replay has roles but no pair introspection.
    supported_source_syndrome_pairs = lambda differential: []
import nova_agent.differential as de
import nova_agent.retrieval_pipeline as rp

FAILURE_CLASSES = ('RETRIEVAL_MISS','RERANK_MISS','ACTIVE_SET_MISS',
    'EVIDENCE_EXTRACTION_ERROR','EVIDENCE_WEIGHTING_ERROR','ACTION_SELECTION_ERROR',
    'FINAL_RANKING_ERROR','STOP_POLICY_ERROR','PROTOCOL_OR_OOD_ERROR')


def primary_failure(row):
    """Single, ordered primary attribution; preserve the facts used for audit."""
    if not row['scored'] or row['correct']:
        return None
    f = row['final_stage']
    if row['failed_to_diagnose'] or row['malformed']:
        return 'PROTOCOL_OR_OOD_ERROR'
    if not f['scored']:
        if not f['retrieved']: return 'RETRIEVAL_MISS'
        if not f['reranked']: return 'RERANK_MISS'
        return 'ACTIVE_SET_MISS'
    if f['active_rank'] is None: return 'ACTIVE_SET_MISS'
    if f['active_rank'] == 1: return 'FINAL_RANKING_ERROR'
    if row['unrequested_scripted_objective'] and not f['resolved']:
        return 'ACTION_SELECTION_ERROR'
    if row['unrequested_scripted_objective'] and row['stop_was_unforced']:
        return 'STOP_POLICY_ERROR'
    if not f['supporting'] and row['scripted_objective_observed']:
        return 'EVIDENCE_EXTRACTION_ERROR'
    if f['objective_evidence_score'] and f['objective_evidence_score'] > 0:
        return 'EVIDENCE_WEIGHTING_ERROR'
    return 'FINAL_RANKING_ERROR'


def trace_case(case):
    agent=DoctorAgent(llm_client=MockLLMClient())
    state=agent.new_case(case.case_id,case.chief_complaint,case.demographics)
    sim=PatientSimulator(case); turns=[]; first_safe=None; seen=set(); duplicate=malformed=0
    orig_score=de._score_disease; orig_gen=de.generate_candidates
    orig_retrieve=rp.retrieve_high_recall; orig_rerank=rp.lightweight_rerank; orig_rrf=rp._rrf_fuse
    original_phrase=de._score_phrase; original_lab=de._score_lab_aware_phrase
    original_glucose=de._score_glucose; original_lactate=de._score_lactate
    eligible=retained=0
    while state.remaining_turns:
        scores={}; pool=[]; retrieved=[]; reranked=[]; raw={}
        def rrf(lists,top_k):
            for query_index,(signal,hits) in enumerate(lists):
                for rank,h in enumerate(hits,1):
                    r=raw.setdefault(h.concept.concept_id,dict(concept=h.concept,queries=[],rrf=0))
                    r['queries'].append(dict(query_index=query_index,signal=signal,rank=rank))
                    r['rrf']+=rp.SIGNAL_WEIGHTS.get(signal,1)/(rp._RRF_K+rank)
            return orig_rrf(lists,top_k)
        def gen(*a,**kw):
            result=orig_gen(*a,**kw);pool.extend(result);return result
        def retrieve(*a,**kw):
            result=orig_retrieve(*a,**kw);retrieved.extend(result);return result
        def rerank(*a,**kw):
            result=orig_rerank(*a,**kw);reranked.extend(result);return result
        def score(entry,*a,**kw):
            # Observe actual score operations, not a separate substitute scoring implementation.
            calls=[]; numeric=[]
            def phrase(p,w,*args,**kwargs):
                value=original_phrase(p,w,*args,**kwargs);calls.append((p,w,value));return value
            def lab(p,w,*args,**kwargs):
                value=original_lab(p,w,*args,**kwargs)
                if value is not None:calls.append((p,w,value))
                return value
            def glucose(*args,**kwargs):
                value=original_glucose(*args,**kwargs);numeric.append(value);return value
            def lactate(*args,**kwargs):
                value=original_lactate(*args,**kwargs);numeric.append(value);return value
            with patch.object(de,'_score_phrase',phrase),patch.object(de,'_score_lab_aware_phrase',lab),patch.object(de,'_score_glucose',glucose),patch.object(de,'_score_lactate',lactate):
                result=orig_score(entry,*a,**kw)
            typical=list(entry.get('typical_features',[]));tc=calls[:len(typical)];oc=calls[len(typical):]
            generic=lambda p:bool(content_words(p)) and content_words(p).issubset(GENERIC_PHYSIOLOGIC_SEVERITY_WORDS)
            risk=sum(de.RISK_FACTOR_WEIGHT for p in entry.get('risk_factors',[]) if de._present_with_aliases(p,state.all_findings_text()))
            meds=sum(de.RISK_FACTOR_WEIGHT for p in entry.get('risk_factors',[]) if de._present_with_aliases(p,state.medication_text))
            components=dict(specific_evidence_score=sum(v for p,w,v in tc if not generic(p)),
                generic_evidence_score=sum(v for p,w,v in tc if generic(p)),
                objective_evidence_score=sum(v for p,w,v in oc)+sum(numeric),risk_score=risk,medication_score=meds)
            # Component raw sums may overlap aliases and precede saturation. The residual is
            # explicit: capped adjustment + reassuring penalties. Numeric labs are objective.
            components['score_residual']=result[0]-sum(components[k] for k in ('specific_evidence_score','generic_evidence_score','objective_evidence_score','risk_score'))
            scores[entry['id']]=(entry,result,components)
            return result
        with patch.object(de,'generate_candidates',gen),patch.object(de,'_score_disease',score),patch.object(rp,'_rrf_fuse',rrf),patch.object(rp,'retrieve_high_recall',retrieve),patch.object(rp,'lightweight_rerank',rerank):
            action,llm,differential=agent.decide(state)
        safety=agent.safety_layer.assess(state,differential)
        _,actions,stop=agent.action_selector.generate_and_select(state,differential,safety)
        rawactions=agent.action_selector.missing_info.analyze(state,differential,safety)
        if stop.should_diagnose and not stop.forced and first_safe is None:first_safe=state.turn_count+1
        rr={h.concept.concept_id:i+1 for i,h in enumerate(retrieved)}
        rk={h.concept.concept_id:i+1 for i,h in enumerate(reranked)}
        active={d.diagnosis_id:d for d in differential};poolmap={c.id:c for c in pool}
        # Core concepts use core:<id> in catalog and bare <id> in differential.
        def runtime_id(cid):
            return cid.removeprefix('core:') if cid.startswith('core:') else 'onto::'+cid
        for h in retrieved:
            raw.setdefault(h.concept.concept_id,dict(concept=h.concept,queries=[],rrf=None))
        ids=list(dict.fromkeys([*poolmap, *scores]))
        for cid in raw:
            if runtime_id(cid) not in ids:ids.append(runtime_id(cid))
        candidates=[]
        for did in ids:
            cid=('core:'+did) if not did.startswith('onto::') else did[6:]
            entry,result,components=scores.get(did,({},(None,None,[],[],[]),{}))
            rawhit=raw.get(cid,{}); name=entry.get('name') or getattr(rawhit.get('concept'),'canonical_name',did)
            d=active.get(did);support=result[2];contra=result[3]
            resolved=is_resolved(did,contra,state)
            danger=bool(entry.get('dangerous',getattr(rawhit.get('concept'),'dangerous',False)))
            sources=poolmap[did].sources if did in poolmap else ['raw_retrieval_only']
            plausible=danger and bool(support) and not contra and not resolved
            eligible+=plausible;retained+=bool(plausible and d)
            candidate=dict(id=did,name=name,raw_retrieval_ranks=rawhit.get('queries',[]),
                rrf_score=rawhit.get('rrf'),retrieval_rank=rr.get(cid),rerank_rank=rk.get(cid),
                active_differential_rank=d.rank if d else None,diagnostic_score=result[0],
                **{k:components.get(k) for k in ('specific_evidence_score','generic_evidence_score','objective_evidence_score','risk_score','medication_score','score_residual')},
                supporting=support,negative_evidence=list(state.pertinent_negatives),contradictions=contra,
                missing=result[4],safety_only_support=danger and not support,provenance=sources,
                active=bool(d),resolved=resolved,dangerous=danger,syndrome_role=syndrome_role(did),
                scoring_status='SCORED' if did in scores else 'NOT_SCORED',
                evidence_status=getattr(d,'evidence_status',{}) if d else {})
            candidates.append(candidate)
        target=next((x for x in candidates if same_diagnosis(x['id'],case.ground_truth_diagnosis) or same_diagnosis(x['name'],case.ground_truth_diagnosis)),None)
        stage=dict(retrieved=bool(target and target['retrieval_rank']),reranked=bool(target and target['rerank_rank']),
            rerank_top25=bool(target and target['rerank_rank'] and target['rerank_rank']<=25),
            scored=bool(target and target['scoring_status']=='SCORED'),active_rank=target['active_differential_rank'] if target else None,
            resolved=target['resolved'] if target else False,supporting=target['supporting'] if target else [],
            objective_evidence_score=target['objective_evidence_score'] if target else None)
        key=(action.action_type,action.key);duplicate+=int(key in seen and action.action_type!='DIAGNOSE');seen.add(key);malformed+=int(llm is None)
        turns.append(dict(turn=state.turn_count+1,action=action.model_dump(),stop=stop.model_dump(),
            candidates=candidates,source_syndrome_pairs=supported_source_syndrome_pairs(differential),actions=[a.model_dump() for a in actions],
            action_discriminators=[dict(key=a.key,action_type=a.action_type,diagnoses=a.disease_ids_discriminated) for a in rawactions],truth_stage=stage))
        agent.observe(state,action,sim.respond(action))
        if action.action_type=='DIAGNOSE':break
    unrequested=[f'TEST:{k}' for k in case.test_results if k not in state.completed_tests]+[f'EXAM:{k}' for k in case.exam_results if k not in state.completed_examinations]
    summary=dict(case_id=case.case_id,category=case.category,scored=case.scoring_expected,critical=case.critical,
        truth=case.ground_truth_diagnosis,final=state.final_diagnosis,correct=same_diagnosis(state.final_diagnosis or '',case.ground_truth_diagnosis),
        final_stage=stage,final_rank=stage['active_rank'],turns=state.turn_count,
        tests=sum(t['action']['action_type']=='TEST' for t in turns),first_safe_diagnose_turn=first_safe,
        actual_diagnose_turn=state.turn_count if state.final_diagnosis else None,
        diagnostic_delay=state.turn_count-first_safe if first_safe else None,
        stop_was_unforced=stop.should_diagnose and not stop.forced,
        unrequested_scripted_objective=unrequested,scripted_objective_observed=len(case.test_results)+len(case.exam_results)-len(unrequested),
        eligible_critical_candidate_turns=eligible,retained_critical_candidate_turns=retained,
        duplicate=duplicate,malformed=malformed,failed_to_diagnose=not bool(state.final_diagnosis))
    summary['primary_failure']=primary_failure(summary)
    return summary,turns


def aggregate(rows):
    s=[r for r in rows if r['scored']];c=[r for r in s if r['critical']]
    top=lambda rs,k:sum(r['final_rank'] is not None and r['final_rank']<=k for r in rs)/len(rs) if rs else None
    rate=lambda rs,key:sum(bool(r['final_stage'][key]) for r in rs)/len(rs) if rs else None
    m={f'Top{k}':top(s,k) for k in (1,3,5,10)}
    m.update({f'critical_Top{k}':top(c,k) for k in (1,3,5)})
    ranks=[r['final_rank'] for r in s if r['final_rank']];delays=[r['diagnostic_delay'] for r in rows if r['diagnostic_delay'] is not None]
    m.update(scored_cases=len(s),critical_count=len(c),accuracy=sum(r['correct'] for r in s)/len(s),
        critical_recall=sum(r['correct'] for r in c)/len(c),critical_miss=sum(not r['correct'] for r in c)/len(c),
        MRR=sum(1/r['final_rank'] if r['final_rank'] else 0 for r in s)/len(s),median_true_rank=statistics.median(ranks) if ranks else None,
        missing_rank_count=len(s)-len(ranks),median_definition='active ranks only; missing rank count reported separately',
        retrieval_truth_retention=rate(s,'retrieved'),rerank_truth_retention=rate(s,'reranked'),active_truth_retention=len(ranks)/len(s),
        average_turns=statistics.mean(r['turns'] for r in rows),average_tests=statistics.mean(r['tests'] for r in rows),
        average_diagnostic_delay=statistics.mean(delays) if delays else None,diagnostic_delay_observed_count=len(delays),
        diagnostic_delay_definition='policy-eligible non-forced stop, not clinical safety certification; null != zero',
        critical_candidate_retention=sum(r['retained_critical_candidate_turns'] for r in rows)/max(1,sum(r['eligible_critical_candidate_turns'] for r in rows)),
        failure_counts=dict(Counter(r['primary_failure'] for r in s if not r['correct'])),
        action_selection_error_rate=sum(r['primary_failure']=='ACTION_SELECTION_ERROR' for r in s)/len(s),
        final_ranking_error_rate=sum(r['primary_failure']=='FINAL_RANKING_ERROR' for r in s)/len(s))
    lt=[r for r in s if 'long_tail' in r['category']]
    m['long_tail']={'count':len(lt),'retrieved':rate(lt,'retrieved'),'rerank_top25':rate(lt,'rerank_top25'),
        'active':sum(r['final_rank'] is not None for r in lt)/len(lt) if lt else None,'Top5':top(lt,5),'Top1':top(lt,1),
        'interpretation':'name-bearing coverage probes, not symptom-only diagnosis validation'}
    return m


def archive_traces(out, rows):
    """Pack losslessly with deterministic member metadata; validate every uncompressed hash."""
    archive = out / 'traces.tar.xz'
    with tarfile.open(archive, 'w:xz', preset=6) as tf:
        for c in rows:
            payload = gzip.decompress((out / c['trace_file']).read_bytes())
            name = c['case_id'] + '.json'
            info = tarfile.TarInfo(name); info.size = len(payload); info.mtime = 0
            tf.addfile(info, io.BytesIO(payload))
            c['trace_file'] = name
            c['trace_archive'] = archive.name
            c['trace_sha256'] = hashlib.sha256(payload).hexdigest()
    with tarfile.open(archive, 'r:xz') as tf:
        for c in rows:
            assert hashlib.sha256(tf.extractfile(c['trace_file']).read()).hexdigest() == c['trace_sha256']
    for c in rows:
        (out / (c['case_id'] + '.json.gz')).unlink()
    return hashlib.sha256(archive.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);p.add_argument('--cases',help='Comma-separated development IDs only')
    args=p.parse_args();out=Path(args.output_dir);out.mkdir(parents=True,exist_ok=True)
    cases=ROUND_J_CASES if not args.cases else [c for c in ROUND_J_CASES if c.case_id in args.cases.split(',')]
    rows=[]
    for case in cases:
        summary,turns=trace_case(case);target=out/(case.case_id+'.json.gz')
        payload=json.dumps({'summary':summary,'turns':turns},ensure_ascii=False,separators=(',',':')).encode()
        target.write_bytes(gzip.compress(payload,mtime=0));summary['trace_file']=target.name;summary['trace_sha256']=hashlib.sha256(target.read_bytes()).hexdigest();rows.append(summary)
        print(case.case_id,summary['correct'],summary['final_rank'],summary['primary_failure'],flush=True)
    archive_hash = archive_traces(out, rows)
    result=dict(trace_archive_sha256=archive_hash, data_type='SYNTHETIC DEVELOPMENT / COMPETITION STRUCTURE / MOCK LLM',expert_reviewed=False,independent_clinical_validation=False,
        runtime_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        runtime_dirty=bool(subprocess.check_output(['git','status','--porcelain','--','nova_agent'],cwd=ROOT,text=True).strip()),
        case_file_sha256=hashlib.sha256((ROOT/'evaluation/generalization_dev_cases_round_j.py').read_bytes()).hexdigest(),
        component_definition='raw signed component sums; objective includes numeric glucose/lactate; score_residual records saturation and reassuring penalties; medication overlaps risk',
        metrics=aggregate(rows),cases=rows)
    (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result['metrics'],indent=2))
if __name__=='__main__':main()
