"""Audit downloaded research benchmarks; never call NOVA or modify training data.

Requires pyarrow only for DiagnosisArena's original Parquet file.
Keyword coverage is a review queue, NOT clinician-approved label mapping.
"""
import gzip
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'research/external_evidence'
PATTERNS = {
    'pheochromocytoma': r'pheochromocytoma|phaeochromocytoma',
    'croup': r'\bcroup\b|laryngotracheobronchitis',
    'preeclampsia': r'pre[- ]?eclampsia',
    'pancreatic_cancer': r'pancreatic (?:adeno)?carcinoma|pancreatic cancer|adenocarcinoma of the pancreas',
    'acute_kidney_injury': r'acute kidney injury|acute renal (?:failure|injury)',
    'pericarditis': r'pericarditis',
    'stevens_johnson_syndrome': r'Stevens[– -]Johnson|toxic epidermal necrolysis',
    'guillain_barre': r'Guillain[– -]Barr',
    'fabry': r'Fabry',
}


def digest(b):
    return hashlib.sha256(b).hexdigest()


def main():
    import pyarrow.parquet as pq
    report = {'schema_version': 1, 'clinical_accuracy_measured': False,
              'training_performed': False, 'runtime_eligible': False,
              'coverage_method': 'case-insensitive regex; not clinical adjudication',
              'near_duplicate_or_cross_corpus_leakage_checked': False,
              'patterns': PATTERNS, 'datasets': {}, 'review_queue': []}
    for name in ['medxpertqa', 'diagnosisarena']:
        folder = ROOT / name
        manifest = json.loads((folder / 'manifest.json').read_text())
        for f in manifest['files']:
            raw = (folder / 'source' / f['path']).read_bytes()
            if digest(raw) != f['sha256']:
                raise ValueError(f'File integrity failure: {name}/{f["path"]}')
            if 'uncompressed_sha256' in f and digest(gzip.decompress(raw)) != f['uncompressed_sha256']:
                raise ValueError('Uncompressed integrity failure')
        if name == 'medxpertqa':
            rows = []
            for split in ['dev', 'test']:
                with gzip.open(folder / 'source' / f'Text_{split}.jsonl.gz', 'rt') as stream:
                    for line in stream:
                        r = json.loads(line)
                        if r['label'] not in r['options']:
                            raise ValueError('Invalid answer key')
                        rows.append((split, str(r['id']), r['question'],
                                     r['options'][r['label']], r['medical_task'], r['options']))
        else:
            rows = []
            for r in pq.read_table(folder / 'source/test.parquet').to_pylist():
                if r['Right Option'] not in r['Options'] or not r['Final Diagnosis'].strip():
                    raise ValueError('Invalid diagnosis/answer key')
                prompt = '\n'.join(r[k] for k in ['Case Information', 'Physical Examination', 'Diagnostic Tests'])
                rows.append(('test', str(r['id']), prompt, r['Final Diagnosis'], 'Diagnosis', r['Options']))
        ids = [r[1] for r in rows]
        if len(set(ids)) != len(ids):
            raise ValueError('Duplicate IDs')
        norm = [re.sub(r'\W+', '', r[2].casefold()) for r in rows]
        coverage = {}
        for disease, pattern in PATTERNS.items():
            mentions = gold = 0
            for split, rid, prompt, answer, task, options in rows:
                answer_match = bool(re.search(pattern, answer, re.I))
                mention = bool(re.search(pattern, prompt + json.dumps(options) + answer, re.I))
                mentions += mention
                gold += answer_match
                if mention:
                    report['review_queue'].append({
                        'dataset': name, 'split': split, 'id': rid, 'disease': disease,
                        'source_task': task, 'answer_contains_term': answer_match,
                        'source_answer': answer if answer_match else None,
                        'nova_mapping_review': 'PENDING', 'expert_reviewer': None,
                        'clinical_gold_approved_for_nova': False,
                    })
            coverage[disease] = {'any_mention': mentions, 'answer_contains_term': gold}
        report['datasets'][name] = {
            'rows': len(rows), 'splits': dict(Counter(r[0] for r in rows)),
            'duplicate_ids': 0, 'duplicate_normalized_prompts': len(norm) - len(set(norm)),
            'files_hash_verified': len(manifest['files']), 'coverage': coverage,
        }
    (ROOT / 'intake_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report['datasets'], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
