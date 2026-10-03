"""Freeze development/validation/holdout by lexical clusters, preserving source labels.

Needs pyarrow. No inference, no synthetic questions, no authoring new diagnoses.
This is a public research split, not independent clinical validation.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.model_comparison import CaseInput, full_packet, normalized, sha


def main():
    import pyarrow.parquet as pq
    source = ROOT / 'research/external_evidence/diagnosisarena'
    output = ROOT / 'research/external_evidence/comparison_v1'
    output.mkdir(exist_ok=False)
    manifest = json.loads((source / 'manifest.json').read_text())
    file_info = next(f for f in manifest['files'] if f['path'] == 'test.parquet')
    raw = (source / 'source/test.parquet').read_bytes()
    if sha(raw) != file_info['sha256']:
        raise ValueError('Source changed')
    records = pq.read_table(source / 'source/test.parquet').to_pylist()
    exposed = {str(json.loads(l)['original_record']['id']) for l in
               (ROOT / 'research/external_evidence/target_cases_9.jsonl').read_text().splitlines()}
    cases = [CaseInput(case_id=str(r['id']), family_id=str(r['id']), split='development',
                       initial=r['Case Information'], exams={'source_report': r['Physical Examination']},
                       tests={'source_report': r['Diagnostic Tests']},
                       data_type='PUBLIC_CASE_REPORT_DERIVED_AUTHOR_REVIEWED',
                       previously_inspected=str(r['id']) in exposed) for r in records]
    tokens = [set(normalized(full_packet(c)).split()) for c in cases]
    parent = list(range(len(cases)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    pairs = 0
    for i in range(len(cases)):
        for j in range(i):
            if tokens[i] and tokens[j] and len(tokens[i] & tokens[j]) / len(tokens[i] | tokens[j]) >= .9:
                parent[root(i)] = root(j); pairs += 1
    groups = {}
    for i, case in enumerate(cases):
        groups.setdefault(root(i), []).append(i)
    assigned = {}
    quarantine = []
    pool = []
    for indexes in groups.values():
        group_id = 'lexical:' + min(cases[i].case_id for i in indexes)
        for i in indexes:
            cases[i].family_id = group_id
        if any(cases[i].previously_inspected for i in indexes):
            for i in indexes:
                cases[i].previously_inspected = True
                assigned[i] = 'development'
            continue
        # Flag source text already naming the complete answer; never silently redact it.
        if any(normalized(records[i]['Final Diagnosis']) in normalized(full_packet(cases[i])) for i in indexes):
            quarantine.extend(cases[i].case_id for i in indexes)
            continue
        pool.append(indexes)
    pool.sort(key=lambda indexes: hashlib.sha256(('nova-comparison-v1:' + cases[indexes[0]].family_id).encode()).hexdigest())
    counts = {'development': 0, 'validation': 0, 'holdout': 0}
    quotas = {'development': 50, 'validation': 50, 'holdout': 100}
    for indexes in pool:
        split = next((s for s in quotas if counts[s] < quotas[s]), None)
        if split is None:
            break
        for i in indexes:
            assigned[i] = split
        counts[split] += len(indexes)
    if any(counts[s] < quotas[s] for s in quotas):
        raise ValueError('Insufficient eligible cases for frozen quotas')
    inputs, labels = [], []
    for i in sorted(assigned):
        c = cases[i]; c.split = assigned[i]
        inputs.append(c.model_dump_json())
        labels.append(json.dumps({'case_id': c.case_id,
                                  'accepted_diagnoses': [records[i]['Final Diagnosis']],
                                  'review': 'source-author reported review; NOVA mapping pending'}, ensure_ascii=False))
    ib = ('\n'.join(inputs) + '\n').encode(); lb = ('\n'.join(labels) + '\n').encode()
    (output / 'inputs.jsonl').write_bytes(ib); (output / 'labels.jsonl').write_bytes(lb)
    result = {'schema_version': 1, 'source': manifest['dataset'], 'source_revision': manifest['revision'],
              'source_sha256': sha(raw), 'input_sha256': sha(ib), 'label_sha256': sha(lb),
              'seed': 'nova-comparison-v1', 'new_case_quotas': quotas,
              'actual_counts': {s: list(assigned.values()).count(s) for s in quotas},
              'preparation_sha256': sha(Path(__file__).read_bytes()),
              'near_duplicate_pairs_grouped': pairs, 'exact_answer_mentions_quarantined': quarantine,
              'family_basis': 'lexical clusters only; patient/article family identifiers unavailable',
              'semantic_leakage_review': 'PENDING', 'triage_labels': 'UNAVAILABLE',
              'interactive_mapping_review': 'PENDING', 'clinical_validation': False,
              'model_pretraining_contamination': 'UNKNOWN',
              'terms': 'RESEARCH_AND_MODEL_EVALUATION_ONLY; no clinical use',
              'expert_review_scope': 'authors report source review; no new NOVA clinician adjudication'}
    (output / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'counts': result['actual_counts'], 'near_duplicate_pairs': pairs,
                      'answer_mentions_quarantined': len(quarantine)}))


if __name__ == '__main__':
    main()
