#!/usr/bin/env python3
"""Import source-backed human disease leaf terms into OFFLINE review only.

Mondo Disease Ontology, Monarch Initiative, CC BY 4.0.
No runtime registration or assertion of clinical validation is performed.
"""
from collections import Counter, defaultdict, deque
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DIRECTORY = ROOT / 'research/diagnosis_expansion'
SOURCE = DIRECTORY / 'sources/mondo-2026-09-01.obo.gz'
OUTPUT = DIRECTORY / 'mondo_review_candidates.json'
HUMAN = 'MONDO:0700096'
EXCLUDED_SUBSETS = {'not_a_disease', 'metaclass', 'disease_grouping', 'rare_grouping',
                    'ordo_group_of_disorders', 'other_hierarchy', 'predisposition',
                    'omim_susceptibility', 'obsoletion_candidate'}


def parse_obo(text, prefix='MONDO:'):
    terms = {}
    for block in text.split('\n[Term]\n')[1:]:
        block = block.split('\n[', 1)[0]
        fields = defaultdict(list)
        for line in block.splitlines():
            if ': ' in line:
                key, value = line.split(': ', 1)
                fields[key].append(value)
        identifier = fields['id'][0]
        if not identifier.startswith(prefix):
            continue
        aliases = []
        for value in fields['synonym']:
            m = re.match(r'"((?:\\.|[^"\\])*)" EXACT(?: |$)', value)
            if m and 'NON_HUMAN' not in value:
                aliases.append(m[1].replace('\\"', '"').replace('\\\\', '\\'))
        terms[identifier] = dict(
            id=identifier, name=fields.get('name', [''])[0],
            obsolete='true' in fields['is_obsolete'],
            parents=[v.split()[0] for v in fields['is_a']],
            subsets=[v.split()[0] for v in fields['subset']],
            aliases=aliases, xrefs=[v.split()[0] for v in fields['xref']],
            raw_xrefs=fields['xref'],
        )
    return terms


def eligible_terms(terms):
    children = defaultdict(set)
    for t in terms.values():
        if not t['obsolete']:
            for p in t['parents']:
                children[p].add(t['id'])
    human = set()
    pending = deque([HUMAN])
    while pending:
        t = pending.popleft()
        if t in human:
            continue
        human.add(t)
        pending.extend(children[t])
    for identifier in sorted(human - {HUMAN}):
        t = terms[identifier]
        if (t['obsolete'] or not t['name'] or children[identifier]
                or EXCLUDED_SUBSETS.intersection(t['subsets'])):
            continue
        if re.search(r'non[- ]human|susceptibility|predisposition', t['name'], re.I):
            continue
        yield t


def build():
    from nova_agent.ontology.registry import build_catalog
    from nova_agent.ontology.normalizer import normalize
    data = gzip.decompress(SOURCE.read_bytes())
    text = data.decode('utf-8')
    version = re.search(r'^data-version: (.+)$', text, re.M)[1]
    terms = parse_obo(text)
    icd = json.loads((DIRECTORY / 'review_candidates.json').read_text())
    catalog = build_catalog()
    seen = {normalize(t) for c in catalog.all_concepts() for t in c.all_search_terms()}
    seen.update(normalize(c['canonical_name']) for c in icd['candidates'])
    codes = {c['code'] for c in icd['candidates']}
    for c in catalog.all_concepts():
        for code in c.external_codes:
            if 'ICD10' in code.system.upper().replace('-', ''):
                codes.add(code.code.replace('.', '').upper())
    raw = json.loads((ROOT / 'nova_agent/knowledge/tier2_catalog.json').read_text())
    for c in raw['conditions']:
        codes.update(x['code'].replace('.', '').upper()
                     for x in c.get('external_codes', []) + c.get('quarantined_codes', []) if x.get('code'))
    candidates, excluded = [], Counter()
    for t in eligible_terms(terms):
        names = {normalize(t['name']), *(normalize(a) for a in t['aliases'] if len(a) >= 5)}
        if names & seen:
            excluded['name_or_exact_synonym_overlap'] += 1
            continue
        icd_xrefs = {x.split(':', 1)[1].replace('.', '').upper() for x in t['xrefs']
                     if x.startswith(('ICD10:', 'ICD10CM:'))}
        if icd_xrefs & codes:
            # Even a broad/related xref triggers conservative exclusion here.
            # It must not be promoted to an equivalence mapping.
            excluded['possible_existing_icd_overlap'] += 1
            continue
        seen.update(names)
        candidates.append(dict(
            id='review:mondo:' + t['id'].split(':')[1], code=t['id'], code_system='MONDO',
            canonical_name=t['name'], aliases=t['aliases'],
            category='human_disease_leaf', parent_source_ids=t['parents'],
            source_subsets=t['subsets'], source_xrefs=t['raw_xrefs'],
            source_version=version, source_label_status='EXACT_OFFICIAL_LABEL',
            source_url='https://purl.obolibrary.org/obo/' + t['id'].replace(':', '_'),
            clinical_validation_status='NOT_VERIFIED', semantic_review_status='PENDING',
            cross_catalog_equivalence_status='PENDING', runtime_eligible=False,
        ))
    total = icd['combined_registered_and_review_entries'] + len(candidates)
    return dict(
        schema_version=1, purpose='OFFLINE_TERMINOLOGY_REVIEW_ONLY',
        runtime_eligible=False, clinical_accuracy_verified=False,
        source_name='Mondo Disease Ontology — Monarch Initiative',
        source_url='https://purl.obolibrary.org/obo/mondo.obo', source_version=version,
        license='CC-BY-4.0', license_url='https://creativecommons.org/licenses/by/4.0/',
        source_uncompressed_sha256=hashlib.sha256(data).hexdigest(),
        icd_queue_sha256=hashlib.sha256((DIRECTORY / 'review_candidates.json').read_bytes()).hexdigest(),
        previous_combined_entries=icd['combined_registered_and_review_entries'],
        added_review_entries=len(candidates), combined_registered_and_review_entries=total,
        requested_total_entries=32000, requested_target_reached=total >= 32000,
        shortfall_entries=max(0, 32000 - total), exclusion_counts=dict(excluded),
        limitations=[
            'Human disease leaf concepts only, excluding obsolete/grouping/non-disease/predisposition subsets.',
            'Terms include disease subtypes; count is not independently validated unique diseases.',
            'Exact names/synonyms and ICD cross-reference conflicts screened; semantic equivalence still pending.',
            'Source xrefs retain their original meaning and are not asserted as exact code mappings.',
            'Filtered and reformatted derivative of Mondo; source labels preserved; clinical use not verified.',
        ], candidates=candidates,
    )


if __name__ == '__main__':
    result = build()
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    icd = json.loads((DIRECTORY / 'review_candidates.json').read_text())
    manifest = dict(
        schema_version=1, purpose='OFFLINE_TERMINOLOGY_REVIEW_ONLY',
        runtime_registered=icd['baseline_registered_entries'],
        icd_review_entries=icd['added_review_entries'],
        mondo_review_entries=result['added_review_entries'],
        total_registered_and_review_entries=result['combined_registered_and_review_entries'],
        requested_total=result['requested_total_entries'], shortfall=result['shortfall_entries'],
        clinical_accuracy_verified=False,
        files=['review_candidates.json', 'mondo_review_candidates.json'],
    )
    (DIRECTORY / 'combined_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    if (DIRECTORY / 'orphanet_review_candidates.json').exists():
        from scripts.search_review_candidates import update_manifest
        update_manifest()
    print(json.dumps({k: v for k, v in result.items() if k != 'candidates'}, indent=2))
