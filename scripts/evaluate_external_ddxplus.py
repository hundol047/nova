#!/usr/bin/env python3
"""Reproducible DDXPlus v2 cohort; questionnaire replay, never training/runtime data.

2,000 distinct clinical evidence configurations from original train/validate/test
partitions, 1,200/400/400. Exact duplicate evidence profiles are excluded even when
age, sex, label or initial complaint differ. All gold labels stay evaluator-only.
"""
import argparse
import ast
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ['NOVA_COMPETITION_RETRIEVAL']='1'
os.environ['NOVA_PRELIMINARY_RULES']='1'
os.environ['NOVA_LLM_PROVIDER']='mock'
ZIP_SHA='a2b4dbc6a2bc177a54cf7c7f1a4e15f94625bfd335738737b575c6832a1060a7'
PREFIX='nova-benchmarks-2026/DDXPlus/'


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def freeze(archive, directory):
    assert sha(archive)==ZIP_SHA, 'Official public benchmark archive differs'
    out=Path(directory)
    if (out/'manifest.json').exists():raise SystemExit('Already frozen; refusing overwrite')
    out.mkdir(parents=True,exist_ok=True)
    seen=set(); rows=[]
    with zipfile.ZipFile(archive) as z:
        evidence=json.loads(z.read(PREFIX+'release_evidences.json'))
        conditions=json.loads(z.read(PREFIX+'release_conditions.json'))
        (out/'LICENSE.txt').write_bytes(z.read(PREFIX+'LICENSE.txt'))
        (out/'release_evidences.json').write_bytes(z.read(PREFIX+'release_evidences.json'))
        # Quotas sample diseases broadly without selecting on agent performance.
        for source,split,n in [('train','dev',1200),('validate','validation',400),('test','holdout',400)]:
            quota={label:n//len(conditions)+int(i<n%len(conditions)) for i,label in enumerate(sorted(conditions))}
            counts=Counter()
            with zipfile.ZipFile(io.BytesIO(z.read(PREFIX+f'release_{source}_patients.zip'))) as patients:
                reader=csv.DictReader(io.TextIOWrapper(patients.open(patients.namelist()[0]),encoding='utf-8'))
                for index,row in enumerate(reader):
                    label=row['PATHOLOGY']
                    if counts[label]>=quota[label]:continue
                    values=sorted(ast.literal_eval(row['EVIDENCES']))
                    fingerprint=hashlib.sha256(json.dumps(values).encode()).hexdigest()
                    if fingerprint in seen:continue
                    seen.add(fingerprint);counts[label]+=1
                    rows.append({'id':f'ddxplus-{source}-{index}','split':split,'source_row':index,
                                 'age':int(row['AGE']),'sex':row['SEX'],'initial':row['INITIAL_EVIDENCE'],
                                 'evidences':values,'expected':label,'dataset_severity':conditions[label]['severity'],
                                 'clinical_fingerprint':fingerprint})
                    if sum(counts.values())==n:break
            assert sum(counts.values())==n,(source,counts)
    cases=out/'cases.jsonl'
    cases.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    manifest={'schema':'external-ddxplus-v36','dataset':'DDXPlus English v2','source':'https://doi.org/10.6084/m9.figshare.22687585.v2',
              'organizer_archive_url':'https://nova.snubhai.org/downloads/nova-benchmarks-2026.zip',
              'organizer_archive_sha256':ZIP_SHA,'license':'CC BY 4.0','cases':len(rows),'distinct_evidence_profiles':len(seen),
              'split_counts':dict(Counter(r['split'] for r in rows)),'conditions':len(set(r['expected'] for r in rows)),
              'case_sha256':sha(cases),'evidence_metadata_sha256':sha(out/'release_evidences.json'),
              'selection':'First distinct evidence profiles per sorted-condition quota, original partitions preserved',
              'generated_paraphrases':False,'labels_modified':False,'patient_or_official_hidden_cases':False,
              'mode':'Positive/structured questionnaire observations replayed; no physical exams, tests or live model',
              'attribution':'Fansi Tchango, Goel, Wen, Martel, Ghosn. DDXPlus: A New Dataset For Automatic Medical Diagnosis. NeurIPS 2022; arXiv:2205.09148.',
              'limitations':['Synthetic source, not real patients or independent clinician review of this agent',
                             'English questionnaire format differs from Korean NOVA patient interactions',
                             'Initial positive complaint + all supplied evidence is a diagnostic replay, not interview coverage',
                             'Dataset severity is reported as given, not used as a gold triage disposition']}
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ('cases','distinct_evidence_profiles','split_counts','conditions')}))


def observation(code, metadata):
    key,sep,value=code.partition('_@_')
    item=metadata[key]
    answer=(item.get('value_meaning',{}).get(value,{}).get('en',value) if sep else 'Yes')
    question=item['question_en']
    # Preserve compound statements/questions rather than inventing individual
    # positives from "A or B". The reported answer is attached to the exact item.
    return ('past_medical_history' if item['is_antecedent'] else 'associated_symptoms',question,answer)


def worker(args):
    row,metadata=args
    from nova_agent.state import PatientState,Demographics
    from nova_agent.differential import DifferentialEngine
    from nova_agent.final_decision import decide_final
    from nova_agent.matching import evaluation_scope
    from evaluation.clinical_label_identity import same_label
    from nova_agent.knowledge.retrieval import disease_by_id
    _,question,answer=observation(row['initial'],metadata)
    opening=f'Patient reports: {question.rstrip("?")} — {answer}.'
    state=PatientState(chief_complaint=opening,demographics=Demographics(age=row['age'],sex='male' if row['sex']=='M' else 'female'))
    for code in row['evidences']:
        category,question,answer=observation(code,metadata)
        # The original question is kept verbatim. A binary yes is linked to its
        # own question via the existing bare-answer resolver; no gold diagnosis.
        feature=re.sub(r'^(?:Do you (?:have|feel|experience|suffer from)|Are you|Have you (?:had|experienced))\s+', '',question, flags=re.I).rstrip('?')
        state.record_ask(category+':'+feature, question, answer)
    with evaluation_scope():differential=DifferentialEngine().update(state)
    final=decide_final(state,differential,'information_exhausted')
    def matches(name):return same_label(name,row['expected'])
    return {'id':row['id'],'split':row['split'],'expected':row['expected'],'primary':final.label(),
            'top1':matches(final.label()),'top3':any(matches(d.diagnosis) for d in differential[:3]),
            'top5':any(matches(d.diagnosis) for d in differential[:5]),'undifferentiated':final.undifferentiated,
            'differential_names':[d.diagnosis for d in differential[:5]],
            'evidence_count':len(row['evidences']),'dataset_severity':row['dataset_severity']}


def main():
    p=argparse.ArgumentParser();p.add_argument('--freeze-archive');p.add_argument('--cohort',required=True)
    p.add_argument('--output');p.add_argument('--split',default='dev',choices=['dev','validation','holdout','all']);p.add_argument('--workers',type=int,default=2)
    a=p.parse_args()
    if a.freeze_archive:freeze(a.freeze_archive,a.cohort);return
    folder=Path(a.cohort);manifest=json.loads((folder/'manifest.json').read_text())
    assert sha(folder/'cases.jsonl')==manifest['case_sha256']
    assert sha(folder/'release_evidences.json')==manifest['evidence_metadata_sha256']
    metadata=json.loads((folder/'release_evidences.json').read_text())
    from scripts.runtime_identity import tracked_runtime_hashes
    runtime=tracked_runtime_hashes(ROOT)
    selected=[json.loads(line) for line in (folder/'cases.jsonl').read_text().splitlines()]
    selected=[r for r in selected if a.split=='all' or r['split']==a.split]
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        rows=list(pool.map(worker,[(r,metadata) for r in selected],chunksize=10))
    def metrics(rs):return {'cases':len(rs),**{k:sum(r[k] for r in rs)/len(rs) for k in ('top1','top3','top5','undifferentiated')}}
    result={'label':'EXTERNAL SYNTHETIC QUESTIONNAIRE REPLAY — NOT OFFICIAL SCORE','manifest_sha256':sha(folder/'manifest.json'),
            'runtime_sha256':runtime,'runtime_unchanged_during_execution':runtime==tracked_runtime_hashes(ROOT),
            'metrics':metrics(rows),'by_split':{s:metrics([r for r in rows if r['split']==s]) for s in ('dev','validation','holdout') if any(r['split']==s for r in rows)},
            'model':'NO MODEL CALLS; deterministic diagnostic evidence replay','source_attribution':manifest['attribution'],
            'limitations':manifest['limitations'],'cases':rows}
    assert result['runtime_unchanged_during_execution'], 'Runtime changed during evaluation'
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result['metrics']))


if __name__=='__main__':main()
