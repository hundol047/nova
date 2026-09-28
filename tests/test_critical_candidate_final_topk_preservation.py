"""Round-C generalization hardening: differential.py's final top_k trim now has two ANALOGOUS
safety-reinjection stages (mirroring retrieval_pipeline.lightweight_rerank's own Stage 3), gated to
competition-retrieval mode so the byte-identical legacy top_k=5 bound is never disturbed:

  Stage A -- the same small, fixed CROSS_CUTTING_DANGEROUS_DIAGNOSES safety net
             candidate_generator.py's pool already guarantees membership for, unconditionally,
             regardless of evidence (a defense-in-depth visibility guarantee, not a ranking claim).
  Stage B -- any OTHER dangerous diagnosis with REAL supporting evidence of its own that would
             otherwise be silently trimmed out purely by non-dangerous keyword volume.

Both stages only ever evict an already-kept ZERO-evidence, non-dangerous filler entry (never one
with real evidence of its own) -- this is the fix for the "candidate present, then silently
dropped" root-cause category, without making any dangerous diagnosis unconditionally immortal (see
tests/test_severity_evidence.py's negative controls, which this must not regress)."""

from __future__ import annotations

import os

import pytest

from nova_agent.chief_complaint import CROSS_CUTTING_DANGEROUS_DIAGNOSES
from nova_agent.config import get_config
from nova_agent.differential import DifferentialEngine
from nova_agent.state import PatientState


@pytest.fixture(autouse=True)
def _isolated_config():
    saved_env = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(saved_env)
    get_config(reload=True)


def _enable_competition_retrieval():
    os.environ["NOVA_LLM_PROVIDER"] = "competition"
    os.environ["NOVA_COMPETITION_RETRIEVAL"] = "true"
    os.environ["NOVA_RETRIEVAL_TOP_K"] = "200"
    os.environ["NOVA_RERANK_TOP_K"] = "30"
    os.environ["NOVA_REASONING_TOP_K"] = "25"
    get_config(reload=True)


def test_evidenced_dangerous_diagnosis_is_not_crowded_out_by_many_symptom_matches():
    """PE has real matched evidence (sudden dyspnea + pleuritic pain + tachycardia + immobility
    risk) on a presentation that also broadly symptom-matches many other, non-dangerous
    respiratory/cardiac diagnoses via generic words like "breath"/"chest" -- PE must still reach
    the final differential."""
    _enable_competition_retrieval()
    state = PatientState(case_id="crowd_pe", chief_complaint="sudden trouble breathing with a sharp catch in my chest",
                          demographics={"age": 44, "sex": "female"})
    state.symptoms = ["sudden onset dyspnea", "pleuritic chest pain", "tachycardia"]
    state.social_history = ["long car ride last week"]
    items = DifferentialEngine().update(state)
    ids_present = {i.diagnosis_id for i in items}
    assert "pulmonary_embolism" in ids_present


def test_must_not_miss_safety_net_reaches_differential_in_competition_mode():
    _enable_competition_retrieval()
    state = PatientState(case_id="crowd_safetynet", chief_complaint="sudden severe chest pain radiating to the back")
    items = DifferentialEngine().update(state)
    ids_present = {i.diagnosis_id for i in items}
    for must_not_miss_id in CROSS_CUTTING_DANGEROUS_DIAGNOSES:
        assert must_not_miss_id in ids_present


def test_reinjection_never_evicts_a_diagnosis_with_real_evidence_of_its_own():
    """Negative control: on a presentation where cystitis is the ONLY diagnosis with real matched
    evidence, the must-not-miss safety net (all zero-evidence here) must be added AROUND it, never
    by evicting it -- this is the exact failure mode caught during this round's own development
    (a bare safety-net placeholder must never outrank real evidence)."""
    _enable_competition_retrieval()
    state = PatientState(case_id="crowd_cystitis", chief_complaint="burning every time I pass water",
                          demographics={"age": 29, "sex": "female"})
    state.symptoms = ["dysuria", "urinary frequency"]
    state.record_exam("vital_signs", "BP 118/74, HR 78, RR 14, Temp 37.0, SpO2 99%")
    items = DifferentialEngine().update(state)
    assert items[0].diagnosis_id == "uncomplicated_cystitis", (
        f"a well-evidenced diagnosis must never be evicted by the must-not-miss safety net, "
        f"got {items[0].diagnosis_id!r} at rank 1"
    )


def test_legacy_non_competition_mode_size_bound_is_unchanged():
    """Both new reinjection stages are gated on competition_retrieval_enabled -- legacy/mock mode's
    long-verified fixed top_k_differential(5) bound must be completely undisturbed."""
    os.environ["NOVA_LLM_PROVIDER"] = "mock"
    os.environ.pop("NOVA_COMPETITION_RETRIEVAL", None)
    get_config(reload=True)
    state = PatientState(case_id="crowd_legacy", chief_complaint="sudden severe chest pain")
    items = DifferentialEngine().update(state)
    assert len(items) <= get_config().top_k_differential
