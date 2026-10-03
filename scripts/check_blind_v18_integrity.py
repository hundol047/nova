"""Pre-execution label/schema and lexical overlap check; never run a diagnostic agent."""
import hashlib
import importlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.blind_cases_v18 import BLIND_CASES_V18
from nova_agent.knowledge.retrieval import all_diseases
from nova_agent.ontology.registry import get_default_catalog
from nova_agent.taxonomy import EXAM_CATALOG, TEST_CATALOG


def validate():
    cases = BLIND_CASES_V18
    assert 60 <= len(cases) <= 80
    assert len({c.case_id for c in cases}) == len(cases)
    catalog = get_default_catalog()
    valid_labels = set(all_diseases()) | {c.canonical_name for c in catalog.all_concepts()}
    for c in cases:
        assert c.ground_truth_diagnosis in valid_labels or (not c.scoring_expected and c.ground_truth_diagnosis == 'UNKNOWN'), c.case_id
        assert set(c.exam_results) <= set(EXAM_CATALOG), c.case_id
        assert set(c.test_results) <= set(TEST_CATALOG), c.case_id
    prior = {}
    for path in (ROOT/'evaluation').glob('*cases*.py'):
        if path.stem == 'blind_cases_v18':
            continue
        mod = importlib.import_module('evaluation.'+path.stem)
        for value in vars(mod).values():
            if isinstance(value, (list, tuple)):
                for c in value:
                    if hasattr(c, 'chief_complaint') and hasattr(c, 'case_id'):
                        prior[(c.case_id, c.chief_complaint)] = c
    tokenize = lambda s: set(re.findall(r'\w+', s.lower()))
    matches = []
    highest = (0, None, None)
    for c in cases:
        for old in list(prior.values()) + [x for x in cases if x.case_id < c.case_id]:
            x, y = tokenize(c.chief_complaint), tokenize(old.chief_complaint)
            score = len(x & y) / max(1, len(x | y))
            if score > highest[0]:
                highest = (score, c.case_id, old.case_id)
            if c.chief_complaint.strip().lower() == old.chief_complaint.strip().lower() or score >= .82:
                matches.append([c.case_id, old.case_id, score])
    assert not matches, matches
    return dict(case_count=len(cases),scored_count=sum(c.scoring_expected for c in cases),
        critical_count=sum(c.critical for c in cases),catalog_labels='PASS',schema='PASS',
        prior_unique_cases=len(prior),exact_or_high_lexical_overlap=matches,
        maximum_chief_complaint_jaccard=highest,
        case_sha256=hashlib.sha256((ROOT/'evaluation/blind_cases_v18.py').read_bytes()).hexdigest(),
        independent_clinical_validation=False,expert_reviewed=False,
        limitation='Lexical check cannot prove semantic independence; same author shares development context. Labels are synthetic author hypotheses.')


if __name__ == '__main__':
    print(json.dumps(validate(), ensure_ascii=False, indent=2))
