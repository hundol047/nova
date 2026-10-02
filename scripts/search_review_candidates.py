#!/usr/bin/env python3
"""Search the offline review queue. Results are NOT clinical diagnoses."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('query', help='English name fragment or ICD-10-CM code')
    p.add_argument('--category')
    p.add_argument('--limit', type=int, default=20)
    args = p.parse_args()
    data = json.loads((ROOT / 'research/diagnosis_expansion/review_candidates.json').read_text())
    query = args.query.strip().casefold()
    rows = [c for c in data['candidates']
            if (query in c['canonical_name'].casefold() or query.replace('.', '') == c['code'].casefold())
            and (not args.category or c['category'] == args.category)]
    print(json.dumps(dict(status='UNVERIFIED_OFFLINE_REVIEW_ONLY', total_matches=len(rows),
                          results=rows[:max(0, min(args.limit, 100))]), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
