"""5,000-diagnosis retrieval->rerank->LLM pipeline assembly (PHASE 1 PART H+I).

Ties the stages together into the architecture:

    PatientQuery
      -> retrieval (Top-100~200 from 5,000+)          [learning.retrieval]
      -> multi-specialty router boost (additive)       [learning.routing]
      -> deterministic SAFETY-RECALL expansion         [learning.safety_recall]  (Safety > ML > LLM)
      -> deep reranker Top-20~30 (mandatory retained)  [learning.rerank]
      -> LLM candidate bundle (ONLY Top-20~30 + evidence/contradictions/missing/must-not-miss)
      -> open-world outcome + OOD flag                 [KNOWN/POSSIBLE_UNMAPPED/INSUFFICIENT/UNKNOWN]

The LLM is NEVER handed the full 5,000 catalog — only the narrowed bundle. A novel LLM diagnosis
(free text outside the bundle) is normalized to a canonical concept or preserved as
UNMAPPED_LLM_DIAGNOSIS. UNKNOWN/OOD remain first-class outcomes even with 5,000 concepts.

Dependency-free (uses the deterministic retrieval/rerank paths). Never in the submission.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Sequence

from learning.rerank.reranker import Reranker, RerankInput
from learning.retrieval.patient_encoder import PatientQuery
from learning.retrieval.retriever import Retriever
from learning.routing.router import SpecialtyRouter
from learning.safety_recall import apply_safety_recall


class PipelineOutcome(str, Enum):
    KNOWN_CONDITION = "KNOWN_CONDITION"
    POSSIBLE_UNMAPPED_CONDITION = "POSSIBLE_UNMAPPED_CONDITION"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    UNKNOWN_PRESENTATION = "UNKNOWN_PRESENTATION"


# Confidence thresholds (retrieval/rerank scores are match confidences, NOT calibrated probabilities).
KNOWN_SCORE = 0.6
POSSIBLE_SCORE = 0.3
MIN_SIGNAL_TOKENS = 2


@dataclass
class LLMCandidate:
    concept_id: str
    name: str
    rank: int
    score: float
    is_critical: bool
    safety_mandatory: bool

    def as_dict(self) -> dict:
        return {"concept_id": self.concept_id, "name": self.name, "rank": self.rank,
                "score": round(self.score, 4), "is_critical": self.is_critical,
                "safety_mandatory": self.safety_mandatory}


@dataclass
class PipelineResult:
    outcome: PipelineOutcome
    llm_candidates: List[LLMCandidate]       # the ONLY candidates the LLM sees (Top-20~30)
    must_not_miss: List[str]                 # names the LLM is told never to dismiss
    is_ood: bool
    retrieval_pool_size: int
    latencies_ms: Dict[str, float] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "outcome": self.outcome.value,
            "is_ood": self.is_ood,
            "retrieval_pool_size": self.retrieval_pool_size,
            "must_not_miss": list(self.must_not_miss),
            "llm_candidates": [c.as_dict() for c in self.llm_candidates],
            "latencies_ms": {k: round(v, 2) for k, v in self.latencies_ms.items()},
            "notes": list(self.notes),
        }


@dataclass
class NormalizedLLMDiagnosis:
    raw_text: str
    mapped: bool
    concept_id: Optional[str]
    concept_name: Optional[str]
    status: str  # 'MAPPED' | 'UNMAPPED_LLM_DIAGNOSIS'


class FiveKPipeline:
    def __init__(self, retriever: Retriever, catalog, reranker: Optional[Reranker] = None,
                 router: Optional[SpecialtyRouter] = None, ood_detector=None) -> None:
        self._retriever = retriever
        self._catalog = catalog
        self._reranker = reranker or Reranker(keep=25)
        self._router = router or SpecialtyRouter()
        self._ood = ood_detector  # optional learning.ood.OODDetector (fitted); None => no OOD flag

    def run(self, query: PatientQuery, *, retrieval_k: int = 200) -> PipelineResult:
        notes: List[str] = []
        # 1) retrieval
        res = self._retriever.retrieve(query, top_k=retrieval_k)
        pool = res.items
        lat = dict(res.latencies_ms)

        # 2) router (additive boost only; global fallback keeps broad pool)
        route = self._router.route(query.chief_complaint + " " + " ".join(query.symptoms),
                                   candidate_categories=[it.category for it in pool[:50]])
        self._router.boost(pool, route)
        notes.extend(route.notes)

        # 3) safety-recall expansion (Safety > ML > LLM): add must-not-miss, flag mandatory
        text = " ".join([query.chief_complaint, *query.symptoms, *query.history,
                         *query.lab_findings, *query.imaging_findings, *query.ecg_findings])
        audit = apply_safety_recall(pool, self._catalog, text,
                                    extra_signals=list(query.medications))
        notes.extend(audit.get("notes", []))
        must_not_miss = [getattr(it, "name", "") for it in pool if getattr(it, "safety_mandatory", False)]

        # 4) deep rerank Top-20~30 (mandatory retained regardless of score)
        rerank_inputs = [
            RerankInput(
                concept_id=it.concept_id, name=it.name, tier=getattr(it, "tier", ""),
                category=getattr(it, "category", ""), retrieval_score=float(getattr(it, "score", 0.0)),
                embedding_cosine=float(getattr(it, "score", 0.0)),
                is_critical=getattr(it, "safety_mandatory", False),
                safety_mandatory=getattr(it, "safety_mandatory", False),
            )
            for it in pool
        ]
        rr = self._reranker.rerank(rerank_inputs)
        notes.extend(rr.notes)

        llm_candidates = [
            LLMCandidate(concept_id=r.concept_id, name=r.name, rank=r.rank, score=r.score,
                         is_critical=r.is_critical, safety_mandatory=r.safety_mandatory)
            for r in rr.ranked
        ]

        # 5) OOD flag (optional): if the patient embedding is far from the fitted distribution.
        is_ood = False
        if self._ood is not None and getattr(self._ood, "fitted", False):
            try:
                from learning.retrieval.patient_encoder import encode_patient
                is_ood = bool(self._ood.is_ood(encode_patient(query)))
            except Exception:
                is_ood = False
        if is_ood:
            notes.append("Presentation flagged OUT-OF-DISTRIBUTION; ML/rerank confidence reduced, "
                         "deterministic + safety layers emphasized.")

        # 6) open-world outcome. Lexical grounding: did ANY retrieved candidate match the query by
        # lexical/code provenance (not embedding-only, not safety-rule-added)? If not, a high
        # embedding cosine is likely a hash collision on gibberish -> UNKNOWN.
        lexically_grounded = any(
            any(src in ("lexical", "code") for src in (getattr(it, "sources", []) or []))
            for it in pool
        )
        outcome = self._classify(query, llm_candidates, is_ood, lexically_grounded=lexically_grounded)
        lat["total_pipeline"] = sum(v for k, v in lat.items() if k != "total")
        return PipelineResult(outcome=outcome, llm_candidates=llm_candidates,
                              must_not_miss=must_not_miss, is_ood=is_ood,
                              retrieval_pool_size=len(pool), latencies_ms=lat, notes=notes)

    def _classify(self, query: PatientQuery, cands: Sequence[LLMCandidate], is_ood: bool,
                  lexically_grounded: bool = True) -> PipelineOutcome:
        signal = len((query.chief_complaint or "").split()) + len(query.symptoms)
        if signal < MIN_SIGNAL_TOKENS:
            return PipelineOutcome.INSUFFICIENT_INFORMATION
        if not cands:
            return PipelineOutcome.UNKNOWN_PRESENTATION
        # Lexical grounding guard: hash-embedding similarity can be spuriously high on out-of-
        # vocabulary / gibberish tokens (hash collisions). If NOTHING in the pool matched the query
        # lexically or by code (embedding-only), a high cosine is untrustworthy -> UNKNOWN, so
        # gibberish is never promoted to KNOWN/POSSIBLE. (Safety candidates are added by rule, not by
        # query match, so they don't count as lexical grounding.)
        if not lexically_grounded:
            return PipelineOutcome.UNKNOWN_PRESENTATION
        top = cands[0]
        if top.score >= KNOWN_SCORE and not is_ood:
            return PipelineOutcome.KNOWN_CONDITION
        if top.score >= POSSIBLE_SCORE:
            return PipelineOutcome.POSSIBLE_UNMAPPED_CONDITION
        return PipelineOutcome.UNKNOWN_PRESENTATION

    # --- novel LLM diagnosis normalization (H1/H2) -------------------------------------------
    def normalize_llm_diagnosis(self, raw_text: str) -> NormalizedLLMDiagnosis:
        raw = (raw_text or "").strip()
        if len(raw) < 3:
            return NormalizedLLMDiagnosis(raw, False, None, None, "UNMAPPED_LLM_DIAGNOSIS")
        hits = self._catalog.search_conditions(raw, limit=1)
        if hits and hits[0].score >= 0.9:
            c = hits[0].concept
            return NormalizedLLMDiagnosis(raw, True, c.concept_id, c.canonical_name, "MAPPED")
        return NormalizedLLMDiagnosis(raw, False, None, None, "UNMAPPED_LLM_DIAGNOSIS")
