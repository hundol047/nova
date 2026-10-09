"""DEVELOPMENT-ONLY Tier-2 depth priorities from already executed traces.

No patient/evaluation data enters runtime. No clinical facts are generated.
Counts are distinct cases, not repeated mentions across turns. --archive must
be a development trace archive (never blind/frozen new validation).
"""
import argparse
from collections import defaultdict
import gzip
import json
from pathlib import Path
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def analyze(paths, limit):
    from nova_agent.missing_info import _resolve_entry
    from nova_agent.knowledge.retrieval import disease_by_id
    from nova_agent.ontology.registry import get_default_catalog
    # Similarity is a transparent overlap of existing profile features, not a
    # newly asserted clinical mimic relationship.
    catalog = get_default_catalog()
    counts = defaultdict(lambda: {k:set() for k in ('retrieved','top150','top25','active')})
    observed = {}
    truth_outcome = {}
    for path in paths:
        if any(x in str(path).lower() for x in ('blind','frozen','new_validation')):
            raise ValueError('Only already-used development traces are permitted')
        with tarfile.open(path) as archive:
            for member in archive.getmembers():
                if not member.isfile() or not member.name.endswith(('.json','.json.gz')):
                    continue
                data = archive.extractfile(member).read()
                if member.name.endswith('.gz'): data = gzip.decompress(data)
                case = json.loads(data);case_id = case.get('summary',{}).get('case_id',member.name)
                summary = case.get('summary',{})
                truth_ids = {c['id'] for t in case.get('turns',[])[-1:] for c in t.get('candidates',[])
                             if c['id'].startswith('onto::tier2:') and c.get('name') and summary.get('truth')
                             and c['name'].strip().lower() == str(summary.get('truth')).strip().lower()}
                if summary.get('scored', True) and truth_ids:
                    truth_outcome[case_id] = (truth_ids, bool(summary.get('correct')))
                for turn in case.get('turns',[]):
                    for candidate in turn.get('candidates',[]):
                        cid = candidate['id']
                        if not cid.startswith('onto::tier2:'): continue
                        observed[cid] = candidate
                        rank = candidate.get('retrieval_rank')
                        if rank is not None:
                            counts[cid]['retrieved'].add(case_id)
                            if rank <= 150: counts[cid]['top150'].add(case_id)
                        if (candidate.get('rerank_rank') or 100000) <= 25: counts[cid]['top25'].add(case_id)
                        if candidate.get('active'): counts[cid]['active'].add(case_id)
    # Development long-tail failures: a Tier-2 concept that was the labelled diagnosis of a case answered wrongly.
    failed_truth = defaultdict(set)
    for case_id, (truth_ids, correct) in truth_outcome.items():
        if not correct:
            for tid in truth_ids:
                failed_truth[tid].add(case_id)
    provenance = {}
    try:
        enrichment = json.loads((ROOT/'nova_agent/knowledge/tier2_enrichment.json').read_text())
        for e in enrichment.get('entries', []):
            provenance[e['id']] = ('FIELD_LEVEL: ' + '; '.join(sorted(e['provenance']))) if isinstance(e.get('provenance'), dict) \
                else 'GENERAL ONLY (unreviewed_general_knowledge, no field-level source)'
    except (OSError, ValueError, KeyError):
        pass
    cores = []
    for concept in catalog.all_concepts():
        if concept.concept_id.startswith('core:'):
            entry = disease_by_id(concept.concept_id[5:]) or {}
            cores.append((entry.get('id'),set(entry.get('typical_features',[]))))
    rows=[]
    dimensions=('specific_features','risk_factors','confirmatory_findings','important_contradictions',
                'discriminating_questions','discriminating_exams','discriminating_tests','minimum_workup')
    for cid,candidate in observed.items():
        entry = _resolve_entry(cid) or {}
        coverage={k:len(entry.get(k,[]) or []) for k in ('typical_features',*dimensions)}
        meaningful=sum(bool(coverage[k]) for k in dimensions)
        features=set(entry.get('typical_features',[]))
        similar=sorted([{'id':key,'shared_features':sorted(features & fs)} for key,fs in cores if features & fs],
                       key=lambda r:(-len(r['shared_features']),r['id']))[:5]
        c={k:len(v) for k,v in counts[cid].items()}
        loss=max(0,c['top150']-c['top25'])
        failures=len(failed_truth.get(cid, ()))
        # Round U follow-up: danger is reported (safety tracking) but is NOT a priority term, so a dangerous
        # concept is not prioritised -- or later ranked -- merely for being dangerous.
        score=round(c['retrieved'] + 2*loss + c['active'] + 4*failures
                    + 2*bool(similar) + max(0,4-meaningful)*3,2)
        rows.append({'concept_id':cid[6:],'display_name':candidate['name'],
                     'retrieval_frequency_development':c['retrieved'],'top150_frequency':c['top150'],
                     'top25_frequency':c['top25'],'active_set_frequency':c['active'],
                     'long_tail_development_failures':sorted(failed_truth.get(cid, ())),
                     'dangerous_safety_tracking_only':candidate.get('dangerous',False),'similar_tier1_by_existing_feature_overlap':similar,
                     'clinical_metadata_completeness':coverage,'discrimination_dimensions_present':meaningful,
                     'enriched_status':'NOT_ADJUDICATED','provenance_status':provenance.get(cid[6+len('tier2:'):], 'UNRESOLVED (no field-level source)'),
                     'priority_score':score})
    rows.sort(key=lambda r:(-r['priority_score'],r['concept_id']))
    return {'scope':'DEVELOPMENT ONLY; source-derived prioritization, not clinical evidence or diagnosis ranking',
            'counted_concepts':len(rows),'selected_count':min(limit,len(rows)),'selected':rows[:limit],
            'all_priorities':rows,'formula':'retrieved + 2*(top150-top25) + active + 4*long_tail_failures + 2*similar + 3*max(0,4-depth_dimensions); dangerous is reported for safety tracking only (no weight)',
            'limitations':'Only concepts observed in supplied traces. Depth counts cannot establish clinical quality/provenance; no concept is declared enriched automatically.'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',action='append',required=True)
    p.add_argument('--limit',type=int,default=50);p.add_argument('--output',required=True)
    a=p.parse_args();assert 30 <= a.limit <= 80
    result=analyze(a.archive,a.limit)
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('counted_concepts','selected_count')}))

if __name__=='__main__':main()
