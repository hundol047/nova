#!/usr/bin/env python3
"""Human Disease Ontology leaf terms, source-backed offline review only."""
from collections import defaultdict, deque, Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DIRECTORY = ROOT / 'research/diagnosis_expansion'
SOURCE = DIRECTORY / 'sources/doid-2026-09-30.obo.gz'
OUTPUT = DIRECTORY / 'doid_review_candidates.json'


def code_key(system, code):
    from scripts.build_orphanet_review_candidates import code_key as base_key
    normalized = re.sub(r'[^A-Z0-9]', '', system.upper())
    normalized = {'NCI': 'NCIT', 'UMLSCUI': 'UMLS', 'MIM': 'OMIM'}.get(normalized, normalized)
    if normalized.startswith('SNOMEDCT'):
        normalized = 'SCTID'
    return base_key(normalized, code)


def build():
    from scripts.build_mondo_review_candidates import parse_obo
    from scripts.search_review_candidates import load_candidates
    from nova_agent.ontology.registry import build_catalog
    from nova_agent.ontology.normalizer import normalize
    raw = gzip.decompress(SOURCE.read_bytes())
    text = raw.decode()
    terms = parse_obo(text, prefix='DOID:')
    if 'DOID:4' not in terms:
        raise ValueError('Missing disease root')
    children = defaultdict(set)
    for t in terms.values():
        if not t['obsolete']:
            for parent in t['parents']:
                children[parent].add(t['id'])
    reachable, pending = set(), deque(['DOID:4'])
    while pending:
        item = pending.popleft()
        if item not in reachable:
            reachable.add(item)
            pending.extend(children[item])
    prior = sum((load_candidates(s) for s in ('icd', 'mondo', 'orphanet', 'injury')), [])
    runtime = build_catalog()
    seen = {normalize(t) for c in runtime.all_concepts() for t in c.all_search_terms()}
    seen.update(normalize(t) for c in prior for t in [c['canonical_name'], *c.get('aliases', [])])
    codes = {code_key(x.system, x.code) for c in runtime.all_concepts() for x in c.external_codes}
    catalog_raw = json.loads((ROOT / 'nova_agent/knowledge/tier2_catalog.json').read_text())
    for c in catalog_raw['conditions']:
        codes.update(code_key(x.get('system', 'ICD10'), x['code']) for x in
                     c.get('external_codes', []) + c.get('quarantined_codes', []) if x.get('code'))
    for row in prior:
        code = row['code'].split(':')[-1] if row['code_system'] in ('ORPHANET', 'MONDO') else row['code']
        codes.add(code_key(row['code_system'], code))
        for x in row.get('source_xrefs', []):
            if isinstance(x, str) and ':' in x.split()[0]:
                codes.add(code_key(*x.split()[0].split(':', 1)))
            elif isinstance(x, dict) and x.get('system') and x.get('code'):
                codes.add(code_key(x['system'], x['code']))
    selected, excluded = [], Counter()
    version = re.search(r'^data-version: (.+)$', text, re.M)[1]
    for identifier in sorted(terms):
        t = terms[identifier]
        if (identifier not in reachable or t['obsolete'] or children[identifier]
                or not t['name'] or re.search(r'susceptibility|predisposition|non-human', t['name'], re.I)):
            excluded['obsolete_nonleaf_or_outside_scope'] += 1
            continue
        names = {normalize(t['name']), *(normalize(a) for a in t['aliases'] if len(a) >= 5)}
        if names & seen:
            excluded['name_or_synonym_overlap'] += 1
            continue
        refs = {code_key('DOID', identifier.split(':')[1])}
        refs.update(code_key(*x.split(':', 1)) for x in t['xrefs'] if ':' in x)
        if codes & refs:
            excluded['possible_cross_reference_overlap'] += 1
            continue
        seen.update(names)
        codes.add(code_key('DOID', identifier.split(':')[1]))
        selected.append(dict(id='review:doid:' + identifier.split(':')[1], code=identifier,
            code_system='DOID', canonical_name=t['name'], aliases=t['aliases'],
            category='human_disease_leaf', parent_source_ids=t['parents'], source_xrefs=t['raw_xrefs'],
            source_version=version, source_url='https://purl.obolibrary.org/obo/' + identifier.replace(':', '_'),
            source_label_status='EXACT_OFFICIAL_LABEL', clinical_validation_status='NOT_VERIFIED',
            runtime_eligible=False, semantic_review_status='PENDING', cross_catalog_equivalence_status='PENDING'))
    total = len(runtime) + len(prior) + len(selected)
    return dict(schema_version=1, purpose='OFFLINE_TERMINOLOGY_REVIEW_ONLY', runtime_eligible=False,
        clinical_accuracy_verified=False, source_name='Human Disease Ontology / Disease Ontology team',
        source_url='https://purl.obolibrary.org/obo/doid.obo', source_version=version,
        source_uncompressed_sha256=hashlib.sha256(raw).hexdigest(), license='CC0-1.0',
        previous_combined_entries=len(runtime) + len(prior), added_review_entries=len(selected),
        combined_registered_and_review_entries=total, requested_total_entries=34991,
        shortfall_entries=max(0, 34991-total), requested_target_reached=total >= 34991,
        exclusion_counts=dict(excluded),
        limitations=['Disease subtypes included; semantic equivalence remains unverified.',
                     'Cross-reference overlap excluded conservatively; no exact equivalence asserted.',
                     'Filtered/reformatted source terms, not clinical diagnostic criteria.'], candidates=selected)


if __name__ == '__main__':
    result = build()
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    from scripts.search_review_candidates import update_manifest
    update_manifest()
    print(json.dumps({k:v for k,v in result.items() if k != 'candidates'}, indent=2))
