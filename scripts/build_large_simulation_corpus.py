"""Build 50,000 labeled synthetic robustness dialogues, not independent patients.

Preserve source diagnoses and current findings; vary presentation and explicitly
noncurrent/nonasserted report clauses. Never use NOVA predictions as labels.
Historical reference cases are disclosed; v11 and later frozen checks are excluded.
"""
from collections import Counter
import gzip
import hashlib
import importlib
import json
from pathlib import Path
import random
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DIRECTORY = ROOT / 'research/simulation_50000_v1'
SOURCES = [
    ('evaluation.cases', 'CASES'),
    ('evaluation.held_out_cases', 'HELD_OUT_CASES'),
    ('evaluation.generalization_cases_v2', 'GENERALIZATION_CASES_V2'),
    ('evaluation.generalization_stress_cases', 'GENERALIZATION_STRESS_CASES'),
    ('evaluation.blind_cases_v8', 'BLIND_CASES_V8'),
    ('evaluation.blind_cases_v9', 'BLIND_CASES_V9'),
    ('evaluation.blind_cases_v10', 'BLIND_CASES_V10'),
]
REPORT_DISTRACTORS = {
    'ecg': 'ST elevation', 'ct_head': 'subarachnoid blood',
    'cxr': 'focal consolidation', 'chest_xray': 'focal consolidation',
    'troponin': 'elevated troponin', 'urinalysis': 'nitrites positive',
    'glucose_point_of_care': 'glucose 39 mg/dL',
    'lactate': 'lactate 5.8 mmol/L', 'cbc': 'hemoglobin 6.1 g/dL',
    'electrolytes': 'potassium 6.7 mmol/L',
}


def payload_digest(case):
    # IDs, notes, labels and reporting metadata cannot create an apparently new input.
    body = {k: v for k, v in case.items() if k not in
            {'case_id', 'notes', 'ground_truth_diagnosis', 'category', 'scoring_expected'}}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def group_split(diagnosis):
    # All cases for the same target, including old rewordings, stay in one split.
    number = int(hashlib.sha256(('nova-50k-v1:' + diagnosis).encode()).hexdigest()[:8], 16)
    return 'validation' if number % 5 == 0 else 'development'


def load_sources():
    pools = {'low': [], 'high': []}
    provenance = {}
    for module_name, variable in SOURCES:
        module = importlib.import_module(module_name)
        cases = getattr(module, variable)
        path = Path(module.__file__)
        provenance[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        for index, case in enumerate(cases):
            # Lower difficulty means typical source + clean documentation, not low urgency.
            easy = (module_name == 'evaluation.cases'
                    or (module_name == 'evaluation.generalization_cases_v2' and case.category == 'common_disease')
                    or (module_name == 'evaluation.blind_cases_v8' and index < 34))
            difficulty = 'low' if easy else 'high'
            pools[difficulty].append((module_name + ':' + case.case_id, case.model_dump()))
    return pools, provenance


def _render(text, rng, role):
    # Cosmetic documentation variations retain assertions and numerical values.
    prefix = rng.choice(['', '', 'Patient reports: ']) if role == 'answer' else rng.choice(['', '', 'Result: ', 'Current finding: '])
    text = prefix + text
    casing = rng.randrange(3)
    if casing == 1:
        text = text.lower()
    elif casing == 2:
        text = text.upper()
    spacing = rng.randrange(3)
    if spacing == 1:
        text = text.replace('; ', ';\n')
    elif spacing == 2:
        text = text.replace(' ', '  ')
    return text


def transform(base, difficulty, rng):
    case = json.loads(json.dumps(base))
    age = case['demographics'].get('age')
    if isinstance(age, int) and age >= 18:
        lower, upper = (65, 100) if age >= 65 else (18, 64)
        case['demographics']['age'] = max(lower, min(upper, age + rng.choice([-3, -2, -1, 0, 1, 2, 3])))
    case['chief_complaint'] = rng.choice(['', 'My main concern is: ', 'Presenting symptom: ']) + case['chief_complaint']
    mode = rng.choice(['source_atypical', 'historical_positive', 'uncertain_positive', 'prior_negative']) if difficulty == 'high' else 'clean'
    altered = []
    for field, role in [('answers', 'answer'), ('exam_results', 'result'), ('test_results', 'result')]:
        for key, text in case[field].items():
            if field == 'test_results' and key in REPORT_DISTRACTORS and mode != 'source_atypical' and difficulty == 'high':
                phrase = REPORT_DISTRACTORS[key]
                if mode == 'historical_positive':
                    text = f'Historical report: {phrase}; Current result: {text}'
                elif mode == 'uncertain_positive':
                    text = f'Possible {phrase}; Current result: {text}'
                elif mode == 'prior_negative':
                    text = f'Historical report: no {phrase}; Current result: {text}'
                altered.append(key)
            case[field][key] = _render(text, rng, role)
    return case, dict(documentation=mode, altered_test_fields=altered,
                      source_current_findings_preserved=True, source_sex_preserved=True,
                      age_variation='at_most_3_years_within_original_adult_band')


def build():
    pools, provenance = load_sources()
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    output = DIRECTORY / 'cases.jsonl.gz'
    if output.exists():
        raise SystemExit('Frozen corpus exists; do not overwrite after seeing predictions.')
    seen, counts, families, diagnoses, modes = set(), Counter(), {}, {}, Counter()
    with output.open('wb') as raw, gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as stream:
        for difficulty in ('low', 'high'):
            for split, target in [('development', 20000), ('validation', 5000)]:
                selected = [(f, b) for f, b in pools[difficulty] if group_split(b['ground_truth_diagnosis']) == split]
                if not selected:
                    raise ValueError('Empty source partition')
                rng = random.Random(f'nova-50000-v1:{difficulty}:{split}')
                for i in range(target):
                    family, base = selected[i % len(selected)]
                    for attempt in range(100):
                        case, mutation = transform(base, difficulty, rng)
                        fingerprint = payload_digest(case)
                        if fingerprint not in seen:
                            break
                    else:
                        raise ValueError('Unique input variants exhausted; do not count duplicate IDs as new inputs')
                    seen.add(fingerprint)
                    case['case_id'] = f'SIM50_{difficulty}_{split}_{i:05d}'
                    row = dict(id=case['case_id'], difficulty=difficulty, split=split,
                               source_family=family, source_category=base['category'],
                               diagnostic_group=base['ground_truth_diagnosis'], input_sha256=fingerprint,
                               label_origin='INHERITED_HISTORICAL_SYNTHETIC_SOURCE_NOT_MODEL_PREDICTION',
                               clinical_validation_status='NOT_VERIFIED', mutation=mutation, case=case)
                    stream.write((json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n').encode())
                    counts[difficulty + ':' + split] += 1
                    families[family] = split
                    diagnoses[base['ground_truth_diagnosis']] = split
                    modes[difficulty + ':' + mutation['documentation']] += 1
    manifest = dict(schema_version=1, scope='SYNTHETIC_MOCK_ROBUSTNESS_NOT_CLINICAL_ACCURACY',
                    baseline_commit='1c44c67', cases=50000, low=25000, high=25000,
                    counts=dict(counts), unique_raw_inputs=len(seen), source_families=len(families),
                    distinct_source_diagnoses=len(diagnoses), source_family_splits=families,
                    diagnosis_group_splits=diagnoses, mutations=dict(modes), source_files=provenance,
                    corpus_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                    split_policy='All variants and all sources sharing a diagnosis remain in the same split.',
                    low_definition='Typical source presentations with clean documentation variants; urgency can still be critical.',
                    high_definition='Historical atypical/mimic/rare sources, sometimes with explicit historical/uncertain report distractors.',
                    independent_patients=0, independent_clinical_adjudication=False,
                    limitations=['50,000 variations share a small number of source families; not 50,000 independent clinical cases.',
                                 'Historical source labels and default simulator responses are internally authored and unverified.',
                                 'Difficulty is a construction label, not an empirically calibrated difficulty scale.',
                                 'Repeated mock simulation does not train a model or calibrate clinical probabilities.',
                                 'Validation is reserved during this pass; source vignettes have been seen in earlier work.'])
    (DIRECTORY / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({k: v for k, v in manifest.items() if k not in {'source_family_splits', 'diagnosis_group_splits', 'source_files'}}, indent=2))


if __name__ == '__main__':
    build()
