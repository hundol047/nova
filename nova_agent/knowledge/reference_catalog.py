"""Offline MedlinePlus reference candidates, distinct from scored diagnostic rules.

Public-domain patient education is useful retrieval context, not clinical validation.
This module cannot promote an entry into autonomous diagnosis or the rule scorer.
"""
from collections import Counter, defaultdict
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parent/'reference_candidates'
STOP=set('a an the is are was were be been being of and or to in on for with from by as at it its this that these those you your have has had can could may might will would should not no also more most other some such than then they their them about into through how what which when who where why people disease diseases condition conditions symptoms symptom health medical treatment tests test diagnosis diagnosed doctor doctors provider care cause causes caused include includes including usually common often many'.split())


def clean(text):
    return ' '.join(re.sub(r'[^\w\s]','',text.replace('_',' ').lower()).split())


def tokens(text):
    return [word for word in re.findall(r'[a-z][a-z0-9]+',text.lower()) if word not in STOP and len(word)>2]


def validate_bundle(raw, manifest, selection):
    if hashlib.sha256(raw).hexdigest()!=manifest.get('catalog_sha256'):
        raise ValueError('Reference catalog checksum mismatch')
    if hashlib.sha256(selection).hexdigest()!=manifest.get('selection_sha256'):
        raise ValueError('Reference selection checksum mismatch')
    entries=json.loads(raw)
    names=selection.decode().splitlines()
    if len(entries)!=204 or len(set(names))!=204 or manifest.get('n_reference_candidates')!=204:
        raise ValueError('Expected 204 distinct reference candidates')
    seen=set()
    for e in entries:
        if not isinstance(e,dict) or not all(isinstance(e.get(k),str) and e[k].strip() for k in ('id','name','summary','source_url','attribution','source_topic_id')):
            raise ValueError('Malformed reference candidate')
        if e['id']!='medlineplus_'+e['source_topic_id'] or not e['source_topic_id'].isdigit() or e['id'] in seen:
            raise ValueError('Invalid or duplicate reference ID')
        seen.add(e['id'])
        if e.get('validation_status')!='reference_only' or e.get('autonomous_diagnosis_enabled') is not False or e.get('clinical_review_verified') is not False:
            raise ValueError('Reference material cannot promote itself to a validated diagnosis')
        url=urlsplit(e['source_url'])
        if url.scheme!='https' or url.netloc!='medlineplus.gov' or not re.fullmatch(r'/[a-z0-9]+\.html',url.path) or url.query or url.fragment:
            raise ValueError('Unexpected reference source')
        if not isinstance(e.get('aliases'),list) or not all(isinstance(a,str) and a.strip() for a in e['aliases']):
            raise ValueError('Invalid reference aliases')
    if [e['name'] for e in entries]!=names:
        raise ValueError('Reference selection does not match entries')
    return {e['id']:e for e in entries}


@lru_cache(maxsize=1)
def reference_candidates():
    return validate_bundle((ROOT/'catalog.json').read_bytes(),json.loads((ROOT/'manifest.json').read_text()),(ROOT/'selection.txt').read_bytes())


@lru_cache(maxsize=1)
def _name_index():
    names=defaultdict(set)
    for id,entry in reference_candidates().items():
        for name in [id,entry['name'],*entry['aliases']]:names[clean(name)].add(id)
    # Ambiguous aliases are never silently assigned to the last entry.
    return {name:next(iter(ids)) for name,ids in names.items() if len(ids)==1}


def reference_by_name(name):
    name=name.removeprefix('novel:')
    id=_name_index().get(clean(name))
    return reference_candidates().get(id) if id else None


@lru_cache(maxsize=1)
def _mention_patterns():
    return [(id,re.compile(r'(?<!\w)(?:'+ '|'.join(re.escape(clean(name))
             for name in [id,e['name'],*[a for a in e['aliases'] if len(clean(a))>=4]]) + r')(?!\w)'))
            for id,e in reference_candidates().items()]


def reference_mentions(text):
    """Conservative finalization guard, not a disambiguating diagnosis normalizer."""
    from nova_agent.diagnosis_normalizer import _alias_table, _clean
    if _clean(text) in _alias_table():
        # Exact existing labels outrank nested broader reference names, e.g.
        # "dissecting aortic aneurysm" must remain the existing dissection alias.
        return set()
    exact=reference_by_name(text)
    ids={exact['id']} if exact else set()
    normalized=clean(text)
    ids.update(id for id,pattern in _mention_patterns() if pattern.search(normalized))
    return ids


def catalog_inventory():
    from nova_agent.knowledge.retrieval import all_diseases
    return {'total_entries':len(all_diseases())+len(reference_candidates()),
            'rule_supported_entries':len(all_diseases()),'reference_only_entries':len(reference_candidates()),
            'clinically_validated_entries':0,'reference_autonomous_diagnosis_enabled':False}


@lru_cache(maxsize=1)
def _index():
    documents={id:Counter(tokens(e['name']+' '+ ' '.join(e['aliases'])+' '+e['summary'])) for id,e in reference_candidates().items()}
    df=Counter(word for doc in documents.values() for word in doc)
    average=sum(sum(doc.values()) for doc in documents.values())/len(documents)
    return documents,df,average


def retrieve_reference_candidates(texts, top_k=3):
    """BM25 lexical retrieval, not a diagnostic probability or evidence assertion."""
    from nova_agent.evidence_interpreter import patient_symptom_findings, asserted_clauses, positive_clauses
    from nova_agent.language import normalize_clinical_text
    affirmed=[p for t in patient_symptom_findings(texts) for a in asserted_clauses(normalize_clinical_text(t)) for p in positive_clauses(a)
              if not re.search(r'\b(?:history of|previously|resolved|ruled out)\b',p,re.I)]
    query=set(tokens(' '.join(affirmed)))
    if not query:return []
    documents,df,average=_index()
    ranked=[]
    for id,doc in documents.items():
        entry=reference_candidates()[id]
        names=[entry['name'],*entry['aliases']]
        named=any(len(tokens(name)) and re.search(r'(?<!\w)'+re.escape(clean(name))+r'(?!\w)',clean(' '.join(affirmed))) for name in names if len(clean(name))>3 or clean(name)==clean(' '.join(affirmed)))
        overlap=query.intersection(doc)
        if not named and len(overlap)<3:continue
        size=sum(doc.values())
        score=sum(math.log(1+(len(documents)-df[t]+0.5)/(df[t]+0.5))*doc[t]*2.2/(doc[t]+1.2*(0.25+0.75*size/average)) for t in overlap)
        if named:score+=100
        ranked.append((score,id,overlap))
    ranked.sort(key=lambda row:(-row[0],row[1]))
    out=[]
    for score,id,overlap in ranked[:max(0,min(int(top_k),5))]:
        entry=reference_candidates()[id]
        paragraphs=entry['summary'].splitlines()
        chosen=sorted(range(len(paragraphs)),key=lambda i:-len(set(tokens(paragraphs[i]))&query))[:3]
        snippet=' '.join(paragraphs[i] for i in sorted(chosen))[:1100]
        out.append({'source':entry['source_url'],'reference_id':id,'name':entry['name'],
                    'text':snippet,'attribution':entry['attribution'],
                    'validation_status':'reference_only','autonomous_diagnosis_enabled':False,
                    'retrieval_score':round(score,3),'matched_terms':sorted(overlap)})
    return out

if __name__=='__main__':print(json.dumps(catalog_inventory(),indent=2))
