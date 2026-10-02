#!/usr/bin/env python3
"""Build an isolated terminology review queue, never the clinical runtime catalog.

Source labels are copied verbatim. No symptoms, translations, urgency or clinical
validation are inferred from a billing code. This does not open the expansion gate.
"""
import argparse
from collections import Counter, defaultdict, deque
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SOURCE_URL = 'https://ftp.cdc.gov/pub/health_statistics/nchs/publications/ICD10CM/2027/icd10cm-code-descriptions-2027.zip'
MEMBER = 'icd10cm-code-descriptions-2027/icd10cm-order-2027.txt'
DEFAULT_SOURCE = ROOT / 'research/diagnosis_expansion/sources/icd10cm-code-descriptions-2027.zip'
OUTPUT = ROOT / 'research/diagnosis_expansion/review_candidates.json'
EXCLUDED = re.compile(r'\b(right|left|bilateral|unspecified|other|trimester|fetus|in remission)\b', re.I)


def chapter(code):
    if code[0] in 'AB': return 'infectious'
    if code[0] == 'C' or (code[0] == 'D' and code[:3] < 'D50'): return 'neoplasms'
    if code[0] == 'D': return 'blood_immune'
    if code[0] == 'H': return 'eye' if code[:3] < 'H60' else 'ear'
    return dict(E='endocrine_metabolic', F='mental_behavioral', G='neurologic',
                I='circulatory', J='respiratory', K='digestive', L='skin',
                M='musculoskeletal', N='genitourinary', O='pregnancy',
                P='perinatal', Q='congenital', T='care_complications')[code[0]]


def source_rows(archive):
    with zipfile.ZipFile(archive) as z:
        data = z.read(MEMBER)
    for line in data.decode('utf-8-sig').splitlines():
        # CDC order-file layout: code at 7-13, valid-for-submission flag at
        # 15, long description from 78 (one-based positions).
        if len(line) < 78 or line[14] not in '01':
            raise ValueError('Unexpected CDC fixed-width order-file layout')
        yield line[6:13].strip(), line[77:].strip(), line[14] == '1'


def build(archive=DEFAULT_SOURCE, multiplier=5, *, target_total=None, allow_source_limit=False):
    from nova_agent.ontology.registry import build_catalog
    from nova_agent.ontology.normalizer import normalize
    catalog = build_catalog()
    existing = catalog.all_concepts()
    seen = {normalize(t) for c in existing for t in c.all_search_terms()}
    existing_codes = {c.code.replace('.', '').upper() for x in existing
                      for c in x.external_codes if 'ICD10' in c.system.upper().replace('-', '')}
    raw = json.loads((ROOT / 'nova_agent/knowledge/tier2_catalog.json').read_text())
    for c in raw['conditions']:
        for code in c.get('external_codes', []) + c.get('quarantined_codes', []):
            if code.get('code'):
                existing_codes.add(code['code'].replace('.', '').upper())
    groups = defaultdict(list)
    for code, name, terminal in source_rows(archive):
        eligible = code[0] in 'ABCDEFGHIJKLMNOPQ' or ('T80' <= code[:3] <= 'T88' and code.endswith('A'))
        if not terminal or not eligible or EXCLUDED.search(name):
            continue
        key = normalize(name)
        if key in seen or code in existing_codes:
            continue
        seen.add(key)
        groups[chapter(code)].append((code, name))
    # Round-robin chapter selection prevents alphabetic truncation from
    # excluding whole specialties; shorter codes take precedence within each.
    queues = {k: deque(sorted(v, key=lambda x: (len(x[0]), x[0]))) for k, v in sorted(groups.items())}
    requested_total = target_total if target_total is not None else len(existing) * multiplier
    target = requested_total - len(existing)
    available = sum(map(len, queues.values()))
    if target <= 0 or (available < target and not allow_source_limit):
        raise ValueError('Insufficient eligible source entries; do not fabricate rows')
    target = min(target, available)
    selected = []
    while len(selected) < target:
        for group, q in queues.items():
            if q and len(selected) < target:
                code, name = q.popleft()
                selected.append(dict(
                    id='review:icd10cm:2027:' + code, canonical_name=name,
                    code=code, code_system='ICD-10-CM', source_version='FY2027',
                    category=group, source_member=MEMBER,
                    source_label_status='EXACT_OFFICIAL_LABEL',
                    clinical_validation_status='NOT_VERIFIED',
                    semantic_review_status='PENDING',
                    cross_catalog_equivalence_status='PENDING',
                    runtime_eligible=False,
                ))
    return dict(
        schema_version=1, purpose='OFFLINE_TERMINOLOGY_REVIEW_ONLY',
        runtime_eligible=False, clinical_accuracy_verified=False,
        source_url=SOURCE_URL,
        source_sha256=hashlib.sha256(Path(archive).read_bytes()).hexdigest(),
        baseline_registered_entries=len(existing),
        baseline_distinct_normalized_names=len({normalize(c.canonical_name) for c in existing}),
        baseline_ids=sorted(c.concept_id for c in existing),
        requested_total_entries=requested_total,
        eligible_source_entries=available,
        requested_target_reached=len(existing) + len(selected) == requested_total,
        source_limited=len(existing) + len(selected) < requested_total,
        shortfall_entries=max(0, requested_total - len(existing) - len(selected)),
        added_review_entries=len(selected),
        combined_registered_and_review_entries=len(existing) + len(selected),
        category_counts=dict(sorted(Counter(x['category'] for x in selected).items())),
        limitations=[
            'Counts are terminology records including disease subtypes, not distinct clinically validated diseases.',
            'Exact names, aliases and known code duplicates excluded; synonym/concept equivalence still needs expert review.',
            'ICD labels do not establish diagnostic criteria, urgency, treatments or Korean clinical terminology.',
            'Existing runtime catalog and expansion gate are unchanged; new rows are not diagnostic candidates at runtime.',
        ],
        candidates=selected,
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=DEFAULT_SOURCE)
    p.add_argument('--target-total', type=int, default=32000)
    p.add_argument('--allow-source-limit', action='store_true',
                   help='Save all eligible rows if the requested count exceeds the source; report the shortfall')
    args = p.parse_args()
    result = build(args.source, target_total=args.target_total, allow_source_limit=args.allow_source_limit)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('candidates', 'baseline_ids')}, indent=2))


if __name__ == '__main__':
    main()
