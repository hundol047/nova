"""N.O.V.A. 5,000-diagnosis retrieval subsystem (PHASE 1 PART C/D).

High-recall candidate retrieval over the full disease universe (Tier-1 deep + Tier-2 structured +
Tier-3 ontology). The design is a RETRIEVAL problem, not a 5,000-way classifier: a patient is
embedded once and scored against a prebuilt disease-embedding INDEX by similarity, so adding a new
disease is a new index row — never a change to a fixed output layer.

All of this is dependency-free by default: the encoders produce deterministic feature-hashed vectors
that run without numpy/torch, so retrieval + Recall@K are measurable in any environment. A richer
torch encoder is optional (loaded lazily) and never required.

This package is OPTIONAL and hospital-side: it is never imported by the competition submission.
"""

from learning.retrieval.disease_encoder import DiseaseEncoder, encode_disease
from learning.retrieval.patient_encoder import PatientQuery, PatientEncoder, encode_patient
from learning.retrieval.index import DiseaseIndex
from learning.retrieval.retriever import Retriever, RetrievedItem

__all__ = [
    "DiseaseEncoder", "encode_disease",
    "PatientQuery", "PatientEncoder", "encode_patient",
    "DiseaseIndex",
    "Retriever", "RetrievedItem",
]
