#!/usr/bin/env python3
"""Orphanet/INSERM CC-BY-4.0 source terms, isolated from clinical runtime."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DIRECTORY = ROOT / 'research/diagnosis_expansion'
SOURCE = DIRECTORY / 'sources/orphanet-product1-2026-06-23.xml.gz'
OUTPUT = DIRECTORY / 'orphanet_review_candidates.json'
ALLOWED_TYPES = {'Disease', 'Malformation syndrome', 'Clinical syndrome',
                 'Clinical subtype', 'Etiological subtype', 'Histopathological subtype'}
EXCLUDED_FLAGS = {'Inactive', 'Historical entity', 'Head of classification'}


def code_key(system, code):
    system = re.sub(r'[^A-Z0-9]', '', system.upper())
    system = {'ICD10CM': 'ICD10', 'ORPHA': 'ORPHANET',
              'SNOMEDCT': 'SCTID', 'SNOMED': 'SCTID'}.get(system, system)
    return system + ':' + code.replace('.', '').strip().upper()


def read_source():
    data = gzip.decompress(SOURCE.read_bytes())
    root = ET.fromstring(data)
    if root.findtext('Availability/Licence/ShortIdentifier') != 'CC-BY-4.0':
        raise ValueError('Unexpected source license')
    records = []
    for d in root.findall('DisorderList/Disorder'):
        xrefs = []
        for x in d.findall('ExternalReferenceList/ExternalReference'):
            xrefs.append(dict(system=x.findtext('Source'), code=x.findtext('Reference'),
                relation=x.findtext('DisorderMappingRelation/Name'),
                source_mapping_status=x.findtext('DisorderMappingValidationStatus/Name')))
        records.append(dict(code=d.findtext('OrphaCode'), name=d.findtext('Name'),
            aliases=[x.text for x in d.findall('SynonymList/Synonym') if x.text],
            group=d.findtext('DisorderGroup/Name'), type=d.findtext('DisorderType/Name'),
            flags=[x.text for x in d.findall('DisorderFlagList/DisorderFlag/Label') if x.text],
            xrefs=xrefs, url=d.findtext('ExpertLink')))
    return root.attrib['date'], hashlib.sha256(data).hexdigest(), records


def eligible(row):
    return (row['type'] in ALLOWED_TYPES
            and row['group'] in {'Disorder', 'Subtype of disorder'}
            and not EXCLUDED_FLAGS.intersection(row['flags'])
            and bool(row['code'] and row['name']))


def build():
    from scripts.search_review_candidates import load_candidates
    from nova_agent.ontology.registry import build_catalog
    from nova_agent.ontology.normalizer import normalize
    prior = load_candidates('icd') + load_candidates('mondo')
    runtime = build_catalog()
    seen = {normalize(t) for c in runtime.all_concepts() for t in c.all_search_terms()}
    seen.update(normalize(t) for r in prior for t in [r['canonical_name'], *r.get('aliases', [])])
    codes = {code_key(r['code_system'], r['code']) for r in prior}
    for row in prior:
        for value in row.get('source_xrefs', []):
            token = value.split()[0]
            if ':' in token:
                codes.add(code_key(*token.split(':', 1)))
    for c in runtime.all_concepts():
        codes.update(code_key(x.system, x.code) for x in c.external_codes)
    raw = json.loads((ROOT / 'nova_agent/knowledge/tier2_catalog.json').read_text())
    for c in raw['conditions']:
        for x in c.get('external_codes', []) + c.get('quarantined_codes', []):
            if x.get('code'):
                codes.add(code_key(x.get('system', 'ICD10'), x['code']))
    date, digest, source = read_source()
    excluded, selected = Counter(), []
    for row in sorted(source, key=lambda r: int(r['code'])):
        if not eligible(row):
            excluded['inactive_grouping_or_non_disease_context'] += 1
            continue
        names = {normalize(row['name']), *(normalize(a) for a in row['aliases'] if len(a) >= 5)}
        if names & seen:
            excluded['name_or_synonym_overlap'] += 1
            continue
        refs = {code_key('ORPHANET', row['code'])}
        refs.update(code_key(x['system'], x['code']) for x in row['xrefs'] if x['system'] and x['code'])
        if codes & refs:
            excluded['possible_code_or_cross_reference_overlap'] += 1
            continue
        seen.update(names)
        # Block same source ID and explicitly equivalent xrefs between new rows.
        # Broad mappings are not shared identity: keep their original relation.
        codes.add(code_key('ORPHANET', row['code']))
        codes.update(code_key(x['system'], x['code']) for x in row['xrefs']
                     if x['system'] and x['code'] and (x['relation'] or '').startswith('E ('))
        selected.append(dict(id='review:orphanet:' + row['code'],
            code='ORPHA:' + row['code'], code_system='ORPHANET', canonical_name=row['name'],
            aliases=row['aliases'], category='rare_disease_or_subtype',
            source_entity_type=row['type'], source_entity_group=row['group'],
            source_flags=row['flags'], source_xrefs=row['xrefs'],
            source_url=row['url'], source_version=date,
            source_label_status='EXACT_OFFICIAL_LABEL',
            clinical_validation_status='NOT_VERIFIED', runtime_eligible=False,
            semantic_review_status='PENDING', cross_catalog_equivalence_status='PENDING'))
    before = len(runtime) + len(prior)
    return dict(schema_version=1, purpose='OFFLINE_TERMINOLOGY_REVIEW_ONLY',
        runtime_eligible=False, clinical_accuracy_verified=False,
        source_name='Orphanet / INSERM — Orphadata product 1',
        source_url='https://www.orphadata.com/data/xml/en_product1.xml', source_version=date,
        source_uncompressed_sha256=digest, license='CC-BY-4.0',
        license_url='https://creativecommons.org/licenses/by/4.0/',
        input_sha256={f: hashlib.sha256((DIRECTORY / f).read_bytes()).hexdigest()
                      for f in ('review_candidates.json', 'mondo_review_candidates.json')},
        previous_combined_entries=before, added_review_entries=len(selected),
        combined_registered_and_review_entries=before + len(selected),
        requested_total_entries=32000, shortfall_entries=max(0, 32000 - before - len(selected)),
        requested_target_reached=before + len(selected) >= 32000,
        exclusion_counts=dict(excluded),
        limitations=['Counts include disease subtypes; semantic equivalence still requires review.',
                     'Cross-reference overlap is conservatively excluded, not asserted to be equivalence.',
                     'Filtered/reformatted derivative; original labels and mapping relations preserved.',
                     'No symptoms, diagnostic criteria, treatment or clinical validation were generated.'],
        candidates=selected)


if __name__ == '__main__':
    result = build()
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    from scripts.search_review_candidates import update_manifest
    update_manifest()
    print(json.dumps({k: v for k, v in result.items() if k != 'candidates'}, indent=2))
