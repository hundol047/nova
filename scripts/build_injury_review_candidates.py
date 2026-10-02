#!/usr/bin/env python3
"""Source-backed injury/toxic-effect terms in an offline review queue only."""
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DIRECTORY = ROOT / 'research/diagnosis_expansion'
OUTPUT = DIRECTORY / 'injury_review_candidates.json'
TARGET = 34991  # ceil(23327 * 1.5), user's next target


def eligible(code, name, terminal):
    from scripts.build_review_candidates import EXCLUDED
    return bool(terminal and (code[0] == 'S' or 'T00' <= code[:3] <= 'T79')
                and code.endswith('A') and not EXCLUDED.search(name)
                and not re.search(r'intentional self-harm|assault|undetermined', name, re.I))


def build():
    from scripts.build_review_candidates import source_rows, DEFAULT_SOURCE, SOURCE_URL, MEMBER
    from scripts.build_orphanet_review_candidates import code_key
    from scripts.search_review_candidates import load_candidates
    from nova_agent.ontology.registry import build_catalog
    from nova_agent.ontology.normalizer import normalize
    prior = sum((load_candidates(s) for s in ('icd', 'mondo', 'orphanet')), [])
    runtime = build_catalog()
    seen = {normalize(t) for c in runtime.all_concepts() for t in c.all_search_terms()}
    seen.update(normalize(t) for c in prior for t in [c['canonical_name'], *c.get('aliases', [])])
    codes = {code_key(x.system, x.code) for c in runtime.all_concepts() for x in c.external_codes}
    raw = json.loads((ROOT / 'nova_agent/knowledge/tier2_catalog.json').read_text())
    for c in raw['conditions']:
        codes.update(code_key(x.get('system', 'ICD10'), x['code'])
                     for x in c.get('external_codes', []) + c.get('quarantined_codes', []) if x.get('code'))
    for row in prior:
        codes.add(code_key(row['code_system'], row['code']))
        for x in row.get('source_xrefs', []):
            if isinstance(x, str):
                token = x.split()[0]
                if ':' in token:
                    codes.add(code_key(*token.split(':', 1)))
            elif x.get('system') and x.get('code'):
                codes.add(code_key(x['system'], x['code']))
    rows = []
    for code, name, terminal in source_rows(DEFAULT_SOURCE):
        if not eligible(code, name, terminal):
            continue
        if normalize(name) in seen or code_key('ICD10', code) in codes:
            continue
        seen.add(normalize(name))
        rows.append(dict(id='review:icd10cm:2027:' + code, code=code, code_system='ICD-10-CM',
            canonical_name=name, category='injury_or_toxic_effect', source_version='FY2027',
            source_member=MEMBER, source_label_status='EXACT_OFFICIAL_LABEL',
            clinical_validation_status='NOT_VERIFIED', runtime_eligible=False,
            semantic_review_status='PENDING', cross_catalog_equivalence_status='PENDING'))
    before = len(runtime) + len(prior)
    return dict(schema_version=1, purpose='OFFLINE_TERMINOLOGY_REVIEW_ONLY',
        runtime_eligible=False, clinical_accuracy_verified=False,
        source_url=SOURCE_URL, source_sha256=hashlib.sha256(DEFAULT_SOURCE.read_bytes()).hexdigest(),
        input_sha256={f: hashlib.sha256((DIRECTORY / f).read_bytes()).hexdigest()
                      for f in ('review_candidates.json', 'mondo_review_candidates.json', 'orphanet_review_candidates.json')},
        previous_combined_entries=before, requested_total_entries=TARGET,
        added_review_entries=len(rows), combined_registered_and_review_entries=before + len(rows),
        requested_target_reached=before + len(rows) >= TARGET,
        shortfall_entries=max(0, TARGET - before - len(rows)),
        limitations=['Diagnosis terminology includes injuries, poisoning and adverse effects; not distinct validated diseases.',
                     'Initial-encounter codes only; laterality, unspecified/other, and intent-only variants excluded.',
                     'Original labels preserved; source cross-reference conflicts excluded conservatively.',
                     'No diagnostic criteria, treatment, Korean translation or clinical validation generated.'],
        candidates=rows)


if __name__ == '__main__':
    result = build()
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    from scripts.search_review_candidates import update_manifest
    update_manifest()
    print(json.dumps({k: v for k, v in result.items() if k != 'candidates'}, indent=2))
