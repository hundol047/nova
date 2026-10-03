"""Retrieve additional named possibilities, never convert match scores into diagnoses."""
from functools import lru_cache
import json
from nova_agent.ontology.registry import get_default_catalog

@lru_cache(maxsize=1)
def runtime_pipeline():
    from learning.pipeline import FiveKPipeline
    from learning.retrieval.index import DiseaseIndex
    from learning.retrieval.retriever import Retriever
    cat = get_default_catalog()
    return FiveKPipeline(Retriever(DiseaseIndex().build(cat.all_concepts()), catalog=cat), cat)

def retrieve_catalog_context(state):
    from learning.retrieval.patient_encoder import PatientQuery
    query = PatientQuery(chief_complaint=state.chief_complaint,
                         symptoms=list(state.pertinent_positives),
                         negatives=list(state.pertinent_negatives),
                         lab_findings=list(state.laboratory_tests.values()),
                         imaging_findings=list(state.imaging.values()),
                         age_years=state.demographics.age, sex=state.demographics.sex or "")
    result = runtime_pipeline().run(query)
    cat = get_default_catalog()
    payload = result.as_dict()
    for item in payload["llm_candidates"]:
        c = cat.get_condition(item["concept_id"])
        item["clinical_validation"] = c.curation_status if c else "NOT_CURATED"
        item["evidence_warning"] = "Retrieval hypothesis only. Match score is not clinical evidence."
    return {"source": "catalog_retrieval_unverified_hypotheses", "text": json.dumps(payload)}
