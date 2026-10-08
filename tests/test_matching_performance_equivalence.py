"""Backend-load optimisations must not change any decision.

* turn-scoped memoisation (matching.evaluation_scope) vs no memo -> identical transcripts;
* the regex-free word-boundary / literal-phrase checks vs the original regex implementations;
* the sparse retrieval dot product vs the dense cosine;
* the memo never outlives a decision and is private to the calling thread."""
import contextlib
import random
import re
import threading

import pytest

import nova_agent.matching as matching
from evaluation.cases import CASES
from evaluation.preliminary_dev_cases import PRELIM_KO_CASES
from evaluation.simulator import run_case
from nova_agent.llm_client import MockLLMClient
from nova_agent.orchestrator import DoctorAgent


def _transcript(case):
    agent = DoctorAgent(llm_client=MockLLMClient())
    result = run_case(agent, case, capture_trajectory=True)
    return result.final_diagnosis, result.differential_trajectory


@pytest.mark.parametrize("case", list(CASES[:4]) + list(PRELIM_KO_CASES[:3]), ids=lambda c: c.case_id)
def test_memoised_decisions_equal_unmemoised_decisions(case, monkeypatch):
    with_memo = _transcript(case)
    monkeypatch.setattr(matching, "evaluation_scope", contextlib.nullcontext)
    without_memo = _transcript(case)
    assert with_memo == without_memo


def test_word_boundary_check_equals_the_regex_it_replaced():
    rng = random.Random(7)
    alphabet = "ab c-_.é가나1 \n'"
    for _ in range(50_000):
        a = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 3)))
        t = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 12)))
        assert matching._exact_phrase_present(a, t) == (re.search(rf"\b{re.escape(a)}\b", t) is not None), (a, t)


def test_non_latin_literal_scan_equals_the_finditer_it_replaced():
    neg = matching._NON_LATIN_NEGATION_RE

    def old(feature, finding):
        for m in re.finditer(re.escape(feature), finding):
            if neg.search(finding[max(0, m.start() - 10):m.start()]) or neg.search(finding[m.end():m.end() + 12]):
                continue
            return True
        return False
    rng = random.Random(3)
    alphabet = "가나없 열ない발a"
    for _ in range(50_000):
        a = "가" + "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 2)))
        t = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 30)))
        assert matching._non_latin_phrase_present(a, t) == old(a, t)


def test_sparse_retrieval_scores_equal_dense_cosine():
    from learning.retrieval.embedding import cosine, hash_embed
    from learning.retrieval.index import DiseaseIndex
    from nova_agent.ontology.registry import get_default_catalog
    index = DiseaseIndex().build(get_default_catalog().all_concepts())
    rng = random.Random(0)
    vocab = ["fever", "cough", "chest pain", "rash", "headache", "vomiting", "dyspnea", "age:50", "sex:female"]
    for _ in range(20):
        query = hash_embed(rng.sample(vocab, 4))
        dense = sorted(((it, cosine(query, it.vector)) for it in index._items), key=lambda t: -t[1])[:40]
        assert [(it.concept_id, s) for it, s in index.search(query, 40)] == [(it.concept_id, s) for it, s in dense]


def test_memo_is_discarded_after_the_decision_and_private_to_the_thread():
    assert matching._SCOPE.get() is None
    seen = {}
    with matching.evaluation_scope():
        matching._content_words("patient specific text")
        assert matching._SCOPE.get()

        def other_thread():
            seen["other"] = matching._SCOPE.get()
        t = threading.Thread(target=other_thread)
        t.start()
        t.join()
    assert seen["other"] is None and matching._SCOPE.get() is None
