"""Bounded evaluation-only memoization for repeated synthetic lexical inputs.

No diagnosis, differential, action, or case result is cached. Every dialogue runs
DoctorAgent.decide/observe normally. Catalog/model/config stay fixed per process.
Validate against uncached execution before interpreting a large-run result.
"""
from functools import lru_cache
import sys
from types import SimpleNamespace


def install():
    import nova_agent.matching as matching
    if getattr(matching, '_bulk_cache_installed', False):
        raise RuntimeError('Install once in a fresh evaluation worker')
    matching._bulk_cache_installed = True
    caches = {}
    for name in ('_content_words', '_strip_negated_spans'):
        cached = lru_cache(maxsize=16384)(getattr(matching, name))
        setattr(matching, name, cached)
        caches[name] = cached

    original_feature = matching.feature_present

    @lru_cache(maxsize=131072)
    def pair(feature, finding, scrub, strict):
        return original_feature(feature, [finding], scrub, strict)

    def feature_present(feature, findings_text, scrub_negated_spans=False, strict=False):
        # The original matcher checks each finding independently in a loop.
        return any(pair(feature, finding, scrub_negated_spans, strict) for finding in findings_text)

    for name, module in list(sys.modules.items()):
        if name.startswith('nova_agent.') and getattr(module, 'feature_present', None) is original_feature:
            module.feature_present = feature_present
    matching.feature_present = feature_present
    caches['feature_finding_pair'] = pair

    import nova_agent.catalog_context as context
    original_context = context.retrieve_catalog_context

    @lru_cache(maxsize=2048)
    def catalog_context(cc, positives, negatives, labs, imaging, age, sex):
        return original_context(SimpleNamespace(chief_complaint=cc,
            pertinent_positives=positives, pertinent_negatives=negatives,
            laboratory_tests=dict(labs), imaging=dict(imaging),
            demographics=SimpleNamespace(age=age, sex=sex)))

    def retrieve(state):
        return dict(catalog_context(state.chief_complaint, tuple(state.pertinent_positives),
            tuple(state.pertinent_negatives), tuple(state.laboratory_tests.items()),
            tuple(state.imaging.items()), state.demographics.age, state.demographics.sex))

    context.retrieve_catalog_context = retrieve
    caches['catalog_context'] = catalog_context

    # Exact query/embedding keys, not approximate normalization or score rounding.
    from nova_agent.ontology.search import ConceptSearchIndex
    original_search = ConceptSearchIndex.search
    cached_search = lru_cache(maxsize=8192)(original_search)

    def search(self, query, limit=20, fuzzy=True):
        return list(cached_search(self, query, limit, fuzzy))

    ConceptSearchIndex.search = search
    caches['catalog_search'] = cached_search

    from learning.retrieval.index import DiseaseIndex
    original_embedding_search = DiseaseIndex.search
    index_caches = {}

    def embedding_search(self, query_vec, top_k=200):
        if id(self) not in index_caches:
            index_caches[id(self)] = lru_cache(maxsize=2048)(
                lambda vector, limit: tuple(original_embedding_search(self, vector, limit)))
        return list(index_caches[id(self)](tuple(query_vec), top_k))

    DiseaseIndex.search = embedding_search
    return lambda: {name: function.cache_info()._asdict() for name, function in caches.items()}
