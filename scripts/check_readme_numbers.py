#!/usr/bin/env python3
"""Check each current results-table row, including turn counts, against saved metrics."""
import json
import re
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ROWS = {'tuning': 'Tuning (8 cases)', 'held_out': 'Held-out (18 cases, 15 scored, 13 critical)',
        'generalization_v2': 'Development generalization (18 cases, all scored, 5 critical)',
        'stress': 'Targeted stress (8 cases, all scored, 5 critical)'}
METRICS = ['scored_diagnostic_accuracy', 'all_case_diagnostic_accuracy',
           'critical_diagnosis_recall', 'critical_miss_rate', 'average_turns']

def main():
    data = json.loads((ROOT/'evaluation/latest_results.json').read_text())
    readme = (ROOT/'README.md').read_text()
    errors = []
    for key, label in ROWS.items():
        match = re.search(r'^\| ' + re.escape(label) + r' \|(.+)$', readme, re.M)
        actual = [value.strip() for value in match.group(1).split('|') if value.strip()] if match else []
        expected = [f'{data[key][m]*100:.1f}%' if m != 'average_turns' else f'{data[key][m]:.1f}' for m in METRICS]
        if actual != expected:
            errors.append(f'{label}: expected {expected}; found {actual}')
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print('README current result rows match evaluation/latest_results.json.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
