"""Synthetic retrieval eval-set builder + measurement (dependency-free).

Builds labeled retrieval cases by sampling catalog concepts and constructing a PatientQuery from
each concept's OWN describable attributes (name/aliases/tags), optionally with light paraphrase/
noise, then measuring whether the retriever surfaces that concept in Top-K. This measures the
retrieval PLUMBING (does a patient described by a disease's features retrieve that disease?) on
synthetic data — it is NOT a claim of clinical accuracy on real patients (asserted via the marker).

Real clinical Recall@K requires real labeled encounters and is NOT VERIFIED here.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Sequence

from learning.retrieval.metrics import EvalCase, evaluate
from learning.retrieval.patient_encoder import PatientQuery
from learning.retrieval.retriever import Retriever

REAL_CLINICAL_RECALL = "NOT VERIFIED"  # synthetic plumbing eval only; not a clinical claim


def _query_from_concept(concept, rng: random.Random) -> PatientQuery:
    """Construct a plausible patient query from a concept's own attributes (+ light noise)."""
    name = getattr(concept, "canonical_name", "")
    aliases = list(getattr(concept, "aliases", ()) or ())
    tags = list(getattr(concept, "chief_complaint_tags", ()) or ())
    feats = list(getattr(concept, "typical_features", ()) or ())
    # chief complaint: an alias if available (more query-like), else the name
    chief = rng.choice(aliases) if aliases else name
    symptoms = []
    if feats:
        symptoms = rng.sample(feats, k=min(2, len(feats)))
    elif tags:
        symptoms = tags[:2]
    return PatientQuery(chief_complaint=chief, symptoms=symptoms)


def build_eval_cases(catalog, retriever: Retriever, *, n: int = 200, top_k: int = 200,
                     seed: int = 42, critical_categories: Optional[set] = None) -> List[EvalCase]:
    rng = random.Random(seed)
    concepts = list(catalog.all_concepts())
    sample = rng.sample(concepts, k=min(n, len(concepts)))
    critical_categories = critical_categories or set()
    cases: List[EvalCase] = []
    for c in sample:
        q = _query_from_concept(c, rng)
        res = retriever.retrieve(q, top_k=top_k)
        is_crit = bool(getattr(c, "dangerous", False)) or (getattr(c, "category", "") in critical_categories)
        cases.append(EvalCase(case_id=getattr(c, "concept_id", ""),
                              ranked_concept_ids=res.concept_ids(),
                              true_concept_id=getattr(c, "concept_id", ""),
                              is_critical=is_crit))
    return cases


def measure(catalog, retriever: Retriever, *, n: int = 200, top_k: int = 200, seed: int = 42) -> Dict[str, float]:
    cases = build_eval_cases(catalog, retriever, n=n, top_k=top_k, seed=seed)
    return evaluate(cases)
