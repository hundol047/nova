#!/usr/bin/env python3
"""Full public-corpus audit. Only metadata-derived numeric summaries are saved."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import resource
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nova_agent.organizer_guidelines import build_index, retrieve
from scripts.official_result_tools import distribution, file_sha
EXPECTED_ZIP_SHA256='ef58c2f4369750af382f2706dcc1c9c7a85e3a93c261d880f7470d695eaf30d5'


def evaluate(root, suite):
    start=time.perf_counter();index=build_index(str(root));build=time.perf_counter()-start
    timings=[];rows=[]
    for probe in suite['queries']:
        for language,query in [('en',probe['en']),('ko',probe['ko']),('mixed',probe['ko']+' '+probe['en'])]:
            begin=time.perf_counter();hits=index.search(query,k=5);timings.append(time.perf_counter()-begin)
            relevant=[any(key.lower().replace(' ','') in (d.title+' '+d.path).lower().replace(' ','') for key in probe['keywords']) for d in hits]
            rank=next((i+1 for i,yes in enumerate(relevant) if yes),None)
            rows.append({'domain':probe['domain'],'language':language,'hit3':any(relevant[:3]),'hit5':any(relevant),
                         'first_topical_rank':rank,'returned':len(hits)})
    excerpts_start=time.perf_counter();refs=retrieve(index,'hyperthyroidism 갑상선기능항진',k=3,max_chars=700)
    excerpt_seconds=time.perf_counter()-excerpts_start
    def metrics(rs):
        n=len(rs)
        return {'queries':n,'Recall@3_topical_proxy':sum(r['hit3'] for r in rs)/n,'Recall@5_topical_proxy':sum(r['hit5'] for r in rs)/n,
                'MRR_first_topical_proxy':sum(1/r['first_topical_rank'] if r['first_topical_rank'] else 0 for r in rs)/n}
    return {'label':'PUBLIC ORGANIZER CORPUS / GENERIC TOPICAL METADATA PROXY / NOT CLINICAL ADJUDICATION',
            'definition':suite['definition'],'stats':index.stats(),'build_seconds':build,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'postings_count':sum(len(v) for v in index.postings.values()),'language_counts':dict(Counter(d.language for d in index.docs)),
            'source_url_retained':sum(bool(d.source_url) for d in index.docs),'license_retained':sum(bool(d.license) for d in index.docs),
            'query_latency_seconds':distribution(timings),'bounded_excerpt_query_seconds':excerpt_seconds,
            'excerpt_metadata_retained':all(r.get('source_url') and r.get('license') for r in refs),'metrics':metrics(rows),
            'by_language':{lang:metrics([r for r in rows if r['language']==lang]) for lang in ['en','ko','mixed']},'queries':rows,
            'corpus_text_persisted':False,'heavy_embeddings':False}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--corpus-root',required=True);p.add_argument('--source-zip',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();path=Path(a.source_zip)
    h=file_sha(path)
    if h!=EXPECTED_ZIP_SHA256:raise SystemExit('Official public ZIP checksum mismatch; no corpus was read.')
    result=evaluate(Path(a.corpus_root),json.loads((ROOT/'evaluation/official_rag_queries.json').read_text()))
    result['verified_source_zip_sha256']=h
    output=Path(a.output);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['stats','build_seconds','peak_rss_kib','query_latency_seconds','metrics']},indent=2))
    if result['stats']['documents']!=15904:raise SystemExit('Full corpus count differs from official guide; inspect omissions.')


if __name__=='__main__':main()
