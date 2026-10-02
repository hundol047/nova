#!/usr/bin/env python3
"""Audit every offline candidate without converting source checks to clinical approval."""
from collections import defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def run():
    from scripts.build_review_candidates import build as icd
    from scripts.build_mondo_review_candidates import build as mondo
    from scripts.build_orphanet_review_candidates import build as orphanet
    from scripts.build_injury_review_candidates import build as injury
    from scripts.build_doid_review_candidates import build as doid
    from scripts.build_ncit_review_candidates import build as ncit
    from nova_agent.ontology.registry import build_catalog
    from nova_agent.ontology.normalizer import normalize
    from scripts.build_doid_review_candidates import code_key
    directory = ROOT / 'research/diagnosis_expansion'
    output = directory / 'validation'
    output.mkdir(exist_ok=True)
    catalog = build_catalog()
    generators = [('review_candidates.json', lambda: icd(target_total=32000, allow_source_limit=True)),
                  ('mondo_review_candidates.json', mondo), ('orphanet_review_candidates.json', orphanet),
                  ('injury_review_candidates.json', injury), ('doid_review_candidates.json', doid),
                  ('ncit_review_candidates.json', ncit)]
    checked, errors, sources = [], [], []
    ids, names = defaultdict(list), defaultdict(list)
    references = defaultdict(set)
    for filename, generate in generators:
        saved = json.loads((directory / filename).read_text())
        rebuilt = generate()
        exact_rebuild = saved == rebuilt
        if not exact_rebuild:
            errors.append(filename + ': snapshot differs from source rebuild')
        expected = {r['id']: r for r in rebuilt['candidates']}
        for row in saved['candidates']:
            issues = []
            if expected.get(row['id']) != row:
                issues.append('source_rebuild_mismatch')
            if row.get('runtime_eligible') is not False or catalog.get_condition(row['id']) is not None:
                issues.append('runtime_isolation_failure')
            if row.get('clinical_validation_status') != 'NOT_VERIFIED':
                issues.append('unsupported_clinical_validation_claim')
            ids[row['id']].append(filename)
            names[normalize(row['canonical_name'])].append(row['id'])
            for ref in row.get('source_xrefs', []):
                if isinstance(ref, str) and ':' in ref.split()[0]:
                    key = code_key(*ref.split()[0].split(':', 1))
                elif isinstance(ref, dict) and ref.get('system') and ref.get('code'):
                    key = code_key(ref['system'], ref['code'])
                else:
                    continue
                references[key].add(row['id'])
            checked.append(dict(id=row['id'], source_file=filename,
                automated_status='PASS' if not issues else 'FAIL', issues=issues,
                clinical_status='NOT_VERIFIED',
                next_required=['clinical_semantic_review', 'diagnostic_evidence',
                               'independent_labeled_cases', 'real_provider_evaluation']))
            errors.extend(row['id'] + ': ' + issue for issue in issues)
        sources.append(dict(file=filename, records=len(saved['candidates']), exact_source_rebuild=exact_rebuild))
    repeated_ids = {k: v for k, v in ids.items() if len(v) > 1}
    repeated_names = {k: v for k, v in names.items() if len(v) > 1}
    if repeated_ids or repeated_names:
        errors.append('duplicate candidate IDs or canonical labels require review')
    total = len(catalog) + len(checked)
    shared = {k: sorted(v) for k, v in references.items() if len(v) > 1}
    manifest = json.loads((directory / 'combined_manifest.json').read_text())
    if manifest['total_registered_and_review_entries'] != total:
        errors.append('combined manifest count mismatch')
    runtime_names = defaultdict(list)
    for c in catalog.all_concepts():
        runtime_names[normalize(c.canonical_name)].append(c.concept_id)
    distinct_names = len(set(runtime_names) | set(names))
    runtime_candidate_overlap = sorted(set(runtime_names) & set(names))
    if runtime_candidate_overlap:
        errors.append('candidate canonical labels overlap runtime labels')
    if manifest.get('distinct_normalized_names') != distinct_names:
        errors.append('combined manifest distinct-name count mismatch')
    if manifest.get('shortfall') != max(0, manifest['requested_total'] - distinct_names):
        errors.append('combined manifest shortfall mismatch')
    summary = dict(runtime_registered=len(catalog), candidates_checked=len(checked),
        combined_records=total, distinct_normalized_names=distinct_names,
        runtime_candidate_name_overlap=runtime_candidate_overlap,
        source_checks=sources, errors=errors,
        duplicate_candidate_ids=repeated_ids, duplicate_candidate_names=repeated_names,
        shared_reference_groups_requiring_semantic_review=len(shared),
        existing_runtime_duplicate_names={k: v for k, v in runtime_names.items() if len(v) > 1},
        automated_status='PASS' if not errors else 'FAIL',
        clinically_verified_new_candidates=0, clinical_validation_status='NOT_VERIFIED',
        runtime_activation_allowed=False,
        limitation='Source fidelity and software invariants only; no clinician adjudication or clinical accuracy claim.')
    (output / 'candidate_checks.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in checked))
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (output / 'shared_reference_review.json').write_text(json.dumps(dict(
        status='REVIEW_REQUIRED_NOT_PROVEN_DUPLICATES',
        explanation='A shared reference can be broader, related, or equivalent. Do not merge or delete automatically.',
        groups=shared), indent=2) + '\n')
    print(json.dumps(summary, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(run())
