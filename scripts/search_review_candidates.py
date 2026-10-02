#!/usr/bin/env python3
"""Search the offline review queue. Results are NOT clinical diagnoses."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_candidates(source='all'):
    directory = ROOT / 'research/diagnosis_expansion'
    files = {'icd': 'review_candidates.json', 'mondo': 'mondo_review_candidates.json',
             'orphanet': 'orphanet_review_candidates.json'}
    rows = []
    for key, filename in files.items():
        if source in ('all', key):
            data = json.loads((directory / filename).read_text())
            if data.get('purpose') != 'OFFLINE_TERMINOLOGY_REVIEW_ONLY':
                raise ValueError('Unexpected review dataset purpose')
            rows.extend(data['candidates'])
    return rows


def update_manifest():
    from nova_agent.ontology.registry import build_catalog
    directory = ROOT / 'research/diagnosis_expansion'
    counts = {source + '_review_entries': len(load_candidates(source))
              for source in ('icd', 'mondo', 'orphanet')}
    runtime = len(build_catalog())
    total = runtime + sum(counts.values())
    manifest = dict(schema_version=1, purpose='OFFLINE_TERMINOLOGY_REVIEW_ONLY',
                    runtime_registered=runtime, **counts,
                    total_registered_and_review_entries=total,
                    requested_total=32000, shortfall=max(0, 32000 - total),
                    clinical_accuracy_verified=False,
                    files=['review_candidates.json', 'mondo_review_candidates.json',
                           'orphanet_review_candidates.json'])
    (directory / 'combined_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


def search(query, source='all', category=None):
    query = query.strip().casefold()
    return [c for c in load_candidates(source)
            if (any(query in t.casefold() for t in [c['canonical_name'], *c.get('aliases', [])])
                or query.replace('.', '') == c['code'].casefold())
            and (not category or c['category'] == category)]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('query', help='English name/alias fragment or ICD-10-CM/MONDO code')
    p.add_argument('--source', choices=['all', 'icd', 'mondo', 'orphanet'], default='all')
    p.add_argument('--category')
    p.add_argument('--limit', type=int, default=20)
    args = p.parse_args()
    rows = search(args.query, args.source, args.category)
    print(json.dumps(dict(status='UNVERIFIED_OFFLINE_REVIEW_ONLY', total_matches=len(rows),
                          results=rows[:max(0, min(args.limit, 100))]), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
