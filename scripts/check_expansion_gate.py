#!/usr/bin/env python3
"""Fail closed until ALL additional conditions have independently reviewed evidence.

Structural tests alone cannot open this gate. Do not manufacture verification metadata.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def collect():
    conditions=json.loads((ROOT/'nova_agent/knowledge/tier2_catalog.json').read_text())['conditions']
    missing_review=[]
    missing_mapping=[]
    quarantined=[]
    for c in conditions:
        review=c.get('clinical_review', {})
        if (c.get('clinical_validation_status')!='VERIFIED' or not review.get('references')
                or not review.get('reviewer') or not review.get('reviewed_at')
                or not review.get('independent_evaluation_id')):
            missing_review.append(c['id'])
        if any(code.get('mapping_status')!='VERIFIED' for code in c.get('external_codes', [])):
            missing_mapping.append(c['id'])
        if c.get('quarantined_codes'):
            quarantined.append(c['id'])
    return {'decision':'BLOCKED' if missing_review or missing_mapping or quarantined else 'READY_FOR_CLINICAL_GATE',
            'registered_entries':len(conditions),
            'missing_independent_clinical_review':len(missing_review),
            'unverified_mapping_entries':len(missing_mapping),
            'quarantined_mapping_entries':len(quarantined),
            'clinical_accuracy_verified':False,
            'further_expansion_allowed':False,
            'reason':'Clinical performance and expert review must be independently verified; metadata is insufficient.'}

if __name__=='__main__':
    report=collect()
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report['further_expansion_allowed'] else 1)
