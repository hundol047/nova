#!/usr/bin/env python3
"""Development-only stage audit. Scripted history is an upper bound, not autonomous recall.

Runs on a pinned checkout without editing it. Truth labels are used only after
retrieval/reranking. Never imports blind fixtures or changes a scorer/denominator.
"""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
from unittest.mock import patch


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkout',default=str(Path(__file__).resolve().parents[1]))
    p.add_argument('--output',required=True)
    a=p.parse_args();root=Path(a.checkout).resolve();sys.path.insert(0,str(root))
    from scripts.benchmark_competition_retrieval import _ALL_CASES
    from evaluation.generalization_dev_cases_round_m import ROUND_M_CASES
    from nova_agent.diagnosis_normalizer import same_diagnosis
    from nova_agent.ontology.registry import get_default_catalog
    from nova_agent.open_world import OpenWorldRetriever
    from nova_agent.candidate_generator import _concept_to_kb_entry
    from nova_agent.matching import feature_present_with_aliases, evaluation_scope
    from nova_agent.clinical_concepts import is_objective_only_feature
    from nova_agent import retrieval_pipeline as rp
    catalog=get_default_catalog();concepts=catalog.all_concepts();retriever=OpenWorldRetriever(catalog)
    rows=[];unmapped=[]
    cases={c.case_id:c for c in [*_ALL_CASES,*ROUND_M_CASES] if c.scoring_expected}
    for case in cases.values():
        concept=next((c for c in concepts if same_diagnosis(c.kb_id or c.canonical_name,case.ground_truth_diagnosis)),None)
        if concept is None:unmapped.append(case.case_id);continue
        for mode in ('chief_only','all_scripted_history_upper_bound'):
            history=list(case.answers.values()) if mode!='chief_only' else []
            observed=[case.chief_complaint,*history];fused={};original=rp._rrf_fuse
            def fusion(lists,top_k):
                for signal,hits in lists:
                    for rank,h in enumerate(hits,1):
                        cid=h.concept.concept_id
                        fused[cid]=fused.get(cid,0)+rp.SIGNAL_WEIGHTS.get(signal,1)/(rp._RRF_K+rank)
                return original(lists,top_k)
            with evaluation_scope(),patch.object(rp,'_rrf_fuse',fusion):
                retrieved=rp.retrieve_high_recall(retriever,chief_complaint=case.chief_complaint,history=history,retrieval_top_k=150)
                reranked=rp.lightweight_rerank(retrieved,rerank_top_k=25)
                ranks={c.concept.concept_id:i for i,c in enumerate(retrieved,1)}
                hit=next((c for c in retrieved if c.concept.concept_id==concept.concept_id),None)
                rranks={c.concept.concept_id:i for i,c in enumerate(reranked,1)}
                evidence_only=sorted(enumerate(retrieved,1),key=lambda x:-rp._rerank_score(x[1],x[0]))[:25]
                entry=_concept_to_kb_entry(concept)
                def matched(field):return [s for s in entry.get(field,[]) if feature_present_with_aliases(s,observed,scrub_negated_spans=True)]
                features=matched('typical_features');specific=matched('specific_features');confirm=matched('confirmatory_findings')
                row=dict(case_id=case.case_id,mode=mode,truth=concept.concept_id,display_name=concept.canonical_name,
                    retrieval_rank=ranks.get(concept.concept_id),retrieval_score=fused.get(concept.concept_id),
                    retrieval_match_score=hit.match_score if hit else None,
                    rerank_score=rp._rerank_score(hit,ranks[concept.concept_id]) if hit else None,
                    rerank_rank=rranks.get(concept.concept_id),retrieved=hit is not None,
                    retained25=concept.concept_id in {c.concept.concept_id for c in reranked[:25]},
                    retained_safety_overflow=concept.concept_id in rranks,
                    before_safety25=concept.concept_id in {c.concept.concept_id for _,c in evidence_only},
                    matched_evidence=features,specific_evidence=specific+confirm,
                    objective_evidence=[s for s in features+confirm if is_objective_only_feature(s)],risk_evidence=matched('risk_factors'),
                    competing_concepts=[dict(id=c.concept.concept_id,score=c.rerank_score,reasons=c.reasons) for c in reranked[:25]])
                rows.append(row)
    aggregate={}
    for mode in ('chief_only','all_scripted_history_upper_bound'):
        subset=[r for r in rows if r['mode']==mode]
        aggregate[mode]={'n':len(subset),**{k:sum(r[k] for r in subset) for k in ('retrieved','retained25','before_safety25','retained_safety_overflow')}}
    result={'runtime_sha':subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip(),
        'runtime_sha256':{str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for d in ('nova_agent','competition') for f in sorted((root/d).rglob('*')) if f.is_file() and f.suffix in {'.py','.json','.md'}},
        'limitation':'Development lexical proxy. Scripted history is privileged upper-bound input, never an autonomous encounter metric. No independent clinical adjudication.',
        'aggregate':aggregate,'unmapped_truths':unmapped,'losses':[r for r in rows if r['retrieved'] and not r['retained25']],'rows':rows}
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,ensure_ascii=False,indent=1)+'\n')
    print(json.dumps(aggregate,indent=2))

if __name__=='__main__':main()
