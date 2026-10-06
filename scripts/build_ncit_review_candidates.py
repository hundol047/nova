#!/usr/bin/env python3
"""Source-preserving NCIt disease terms for offline review, never runtime diagnoses."""
from collections import Counter, defaultdict, deque
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DIRECTORY = ROOT / 'research/diagnosis_expansion'
SOURCE = DIRECTORY / 'sources/Thesaurus_26.09d.FLAT.zip'
OUTPUT = DIRECTORY / 'ncit_review_candidates.json'
SOURCE_URL = 'https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/Thesaurus_26.09d.FLAT.zip'
PRIOR_SOURCES = ('icd','mondo','orphanet','injury','doid')
SEMANTIC_TYPES = {'Disease or Syndrome','Neoplastic Process','Congenital Abnormality',
                  'Mental or Behavioral Dysfunction'}
EXCLUDED_LABEL = re.compile(r'^(?:no |normal |negative |absence of |history of |risk of )|'
                            r'\b(?:susceptibility|predisposition)\b', re.I)


def parse_source():
    with zipfile.ZipFile(SOURCE) as archive:
        raw = archive.read('Thesaurus.txt')
    terms, children = {}, defaultdict(set)
    for line in raw.decode('utf-8-sig').splitlines():
        r = line.split('\t')
        if len(r) != 9 or not re.fullmatch(r'C\d+', r[0]):
            raise ValueError('Unexpected NCIt flat-file schema')
        terms[r[0]] = dict(code=r[0], parents=r[2].split('|') if r[2] else [],
                          names=r[3].split('|'), status=r[6], types=r[7].split('|'))
        # Header nodes are essential hierarchy links, but are never selected as diagnoses.
        if not any(x in r[6] for x in ('Retired','Obsolete')):
            for parent in terms[r[0]]['parents']:
                children[parent].add(r[0])
    return terms, children


def descendants(root, children):
    seen, pending = set(), [root]
    while pending:
        node = pending.pop()
        if node not in seen:
            seen.add(node)
            pending.extend(children.get(node, ()))
    return seen


def build(target_total=35000):
    from scripts.search_review_candidates import load_candidates
    from scripts.build_doid_review_candidates import code_key
    from nova_agent.ontology.registry import build_catalog
    from nova_agent.ontology.normalizer import normalize
    terms, children = parse_source()
    if terms.get('C2991', {}).get('names', [None])[0] != 'Disease or Disorder':
        raise ValueError('Disease hierarchy root changed')
    scope = descendants('C2991',children) - descendants('C22187',children)
    prior = [row for source in PRIOR_SOURCES for row in load_candidates(source)]
    catalog = build_catalog()
    seen = {normalize(t) for c in catalog.all_concepts() for t in c.all_search_terms()}
    seen.update(normalize(t) for c in prior for t in [c['canonical_name'],*c.get('aliases',[])])
    known_codes = {code_key(x.system,x.code) for c in catalog.all_concepts() for x in c.external_codes}
    for row in prior:
        known_codes.add(code_key(row['code_system'],row['code'].split(':')[-1]))
        for x in row.get('source_xrefs',[]):
            if isinstance(x,str) and ':' in x.split()[0]:
                known_codes.add(code_key(*x.split()[0].split(':',1)))
            elif isinstance(x,dict) and x.get('system') and x.get('code'):
                known_codes.add(code_key(x['system'],x['code']))
    excluded, groups = Counter(), defaultdict(list)
    # Specific childless terms first; active named parent subtypes can also be legitimate
    # diagnostic records. Retain hierarchy explicitly, never claim clinical independence.
    for code in sorted(terms, key=lambda k:(bool(children[k]),int(k[1:]))):
        t = terms[code]
        if code not in scope or t['status'] or not SEMANTIC_TYPES.intersection(t['types']):
            excluded['outside_disease_scope_or_inactive'] += 1
            continue
        label = t['names'][0]
        if EXCLUDED_LABEL.search(label):
            excluded['non_diagnostic_label'] += 1
            continue
        names = {normalize(n) for n in t['names']}
        if names & seen or code_key('NCIT',code) in known_codes:
            excluded['name_alias_or_known_code_overlap'] += 1
            continue
        seen.update(names)
        category = 'neoplasm' if 'Neoplastic Process' in t['types'] else 'non_neoplastic_disease'
        groups[(bool(children[code]),category)].append(t)
    available = sum(map(len,groups.values()))
    baseline_names = {normalize(c.canonical_name) for c in catalog.all_concepts()}
    baseline_names.update(normalize(r['canonical_name']) for r in prior)
    # Existing runtime has four repeated canonical labels. Count names rather than
    # silently treating those duplicate labels as four new diagnoses.
    needed = target_total - len(baseline_names)
    if needed <= 0 or available < needed:
        raise ValueError(f'Need {needed} eligible terms, source supplies {available}; do not fabricate')
    selected = []
    for is_parent in (False,True):
        queues = [deque(groups[k]) for k in sorted(groups) if k[0] == is_parent]
        while any(queues) and len(selected)<needed:
            for queue in queues:
                if queue and len(selected)<needed:
                    t = queue.popleft(); code=t['code']
                    selected.append(dict(id='review:ncit:26.09d:'+code,code=code,code_system='NCIT',
                        canonical_name=t['names'][0],aliases=list(dict.fromkeys(t['names'][1:])),
                        category='neoplasm' if 'Neoplastic Process' in t['types'] else 'non_neoplastic_disease',
                        source_semantic_types=t['types'], parent_source_ids=t['parents'],
                        source_leaf=not bool(children[code]), source_version='26.09d',
                        source_url=SOURCE_URL, source_member='Thesaurus.txt',
                        source_label_status='EXACT_OFFICIAL_LABEL',clinical_validation_status='NOT_VERIFIED',
                        runtime_eligible=False,semantic_review_status='PENDING',cross_catalog_equivalence_status='PENDING'))
    return dict(schema_version=1,purpose='OFFLINE_TERMINOLOGY_REVIEW_ONLY',runtime_eligible=False,
        clinical_accuracy_verified=False,source_name='Derived NCIt disease review subset (NCI EVS source)',
        source_url=SOURCE_URL,source_version='26.09d',source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        license='CC-BY-4.0',attribution='NCI Enterprise Vocabulary Services, CBIIT, National Cancer Institute',
        changes='Disease hierarchy/type filtering, overlap exclusion and target selection; source labels preserved.',
        previous_combined_entries=len(catalog)+len(prior),added_review_entries=len(selected),
        combined_registered_and_review_entries=len(catalog)+len(prior)+len(selected),
        requested_distinct_names=target_total,
        combined_distinct_normalized_names=len(baseline_names)+len(selected),
        requested_target_reached=True,shortfall_entries=0,
        eligible_source_entries=available,category_counts=dict(Counter(r['category'] for r in selected)),
        leaf_records=sum(r['source_leaf'] for r in selected),
        nonleaf_records=sum(not r['source_leaf'] for r in selected),exclusion_counts=dict(excluded),
        limitations=['Hierarchy includes disease subtypes and named parent categories, not independent diseases.',
                    'Known names/aliases/NCIt references screened; semantic duplicates may remain.',
                    'No diagnostic criteria, translations, treatment advice or clinical verification inferred.'],
        candidates=selected)


if __name__ == '__main__':
    data=build()
    OUTPUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    from scripts.search_review_candidates import update_manifest
    update_manifest()
    print(json.dumps({k:v for k,v in data.items() if k!='candidates'},indent=2))
