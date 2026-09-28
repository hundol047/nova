"""Competition-mode broad retrieval integration (NOVA_COMPETITION_RETRIEVAL).

Closes the gap where a broad, ontology-scale retrieval capability existed in the codebase
(nova_agent/open_world.py's OpenWorldRetriever, already dependency-free and already part of the
competition submission since it lives under nova_agent/) but was never actually invoked by the
DoctorAgent turn loop. candidate_generator._broaden_with_open_world wires it in as an OPT-IN,
provenance-tagged, safety-preserving EXPANSION step -- never a replacement for the deterministic
KB pool -- and differential.py's DifferentialEngine.update() rebuilds the query from the FULL
current PatientState every turn (via build_clinical_presentation) and passes it through.

These tests exercise the real integration path (generate_candidates / DifferentialEngine.update),
not a mocked stand-in, against the actual bundled DiseaseCatalog (1,280 real curated concepts:
34 Tier-1 deep + 1,246 Tier-2 structured -- no synthetic test-scale concepts are loaded here)."""

from __future__ import annotations

import os

import pytest

from nova_agent.candidate_generator import (
    TARGET_POOL_SIZE,
    CandidateDiagnosis,
    generate_candidates,
)
from nova_agent.chief_complaint import CROSS_CUTTING_DANGEROUS_DIAGNOSES
from nova_agent.clinical_presentation import extract_presentation
from nova_agent.config import get_config


def _presentation(text: str):
    return extract_presentation(text)


@pytest.fixture(autouse=True)
def _isolated_process_wide_config():
    """get_config() is a process-wide singleton -- reloading it while NOVA_LLM_PROVIDER/
    NOVA_COMPETITION_RETRIEVAL are still monkeypatched (which is what happens if this fixture were
    to depend on `monkeypatch` and reload in its own teardown: fixture teardown is LIFO, so a
    dependent fixture's teardown runs BEFORE monkeypatch's own env-var revert) would bake the
    test's temporary override into the shared singleton for every test that runs afterward in the
    same session. This fixture deliberately does NOT depend on monkeypatch: it snapshots/restores
    os.environ directly and reloads the singleton only after that restore, guaranteeing later
    tests never observe this file's temporary provider/env overrides."""
    saved_env = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(saved_env)
    get_config(reload=True)


def test_disabled_by_default_pool_is_byte_identical_to_legacy_behavior():
    presentation = _presentation("sudden severe chest pain radiating to the back")
    without_flag = generate_candidates(presentation, chief_complaint_text=presentation and
                                        "sudden severe chest pain radiating to the back")
    explicit_false = generate_candidates(
        presentation, competition_retrieval=False,
        chief_complaint_text="sudden severe chest pain radiating to the back",
    )
    assert {c.id for c in without_flag} == {c.id for c in explicit_false}


def test_competition_retrieval_adds_provenance_tagged_ontology_retrieval_candidates():
    """Exercises _broaden_with_open_world directly (rather than through the full trimmed pool) so
    the assertion isn't entangled with TARGET_POOL_SIZE's pre-existing trim-budget trade-offs
    (see test_full_catalog_is_never_dumped_into_the_pool / test_competition_retrieval_never_makes_
    the_must_not_miss_trim_worse below for the end-to-end, trimmed-pool behavior)."""
    from nova_agent.candidate_generator import _broaden_with_open_world

    presentation = _presentation("progressive hearing loss and ringing in the ears with vertigo")
    pool: dict = {}
    _broaden_with_open_world(pool, presentation, [],
                              "progressive hearing loss and ringing in the ears with vertigo", 10)
    assert pool, "competition_retrieval must be able to add ontology_retrieval-sourced candidates"
    for candidate in pool.values():
        assert candidate.id.startswith("onto::"), "ontology-sourced candidates must use the onto:: namespace"
        assert candidate.sources == ["ontology_retrieval"]


def test_full_catalog_is_never_dumped_into_the_pool():
    """Even with an aggressively large retrieval budget, the final pool stays bounded at
    TARGET_POOL_SIZE -- broad retrieval expands RECALL upstream, it never forces the whole catalog
    (1,280+ real concepts) through to scoring/LLM context. Uses a presentation with SOME symptom-
    match evidence (so the pool isn't empty -- an empty pool takes the pre-existing, unrelated
    untargeted-whole-catalog LAST-RESORT fallback path, which is a distinct, deliberate safety
    behavior this test isn't about)."""
    presentation = _presentation("chronic dry cough for several weeks")
    records = generate_candidates(
        presentation, competition_retrieval=True, competition_retrieval_max=500,
        chief_complaint_text="chronic dry cough for several weeks",
    )
    assert len(records) <= TARGET_POOL_SIZE


def test_competition_retrieval_never_makes_the_must_not_miss_trim_worse():
    """The fixed 8-entry must-not-miss safety net can already, PRE-EXISTING this change, lose an
    entry to TARGET_POOL_SIZE trimming when enough Tier-1 evidence-based candidates alone fill the
    budget (a pre-existing trade-off, not something this change may alter). What THIS change must
    guarantee is narrower and directly testable: adding ontology_retrieval candidates on top must
    never trim away a must-not-miss diagnosis that would otherwise have survived -- i.e. enabling
    broad retrieval can only ever make the surviving must-not-miss set >= the no-retrieval set,
    never smaller."""
    presentation = _presentation("progressive hearing loss and ringing in the ears with vertigo")
    kwargs = dict(chief_complaint_text="progressive hearing loss and ringing in the ears with vertigo")
    without = generate_candidates(presentation, competition_retrieval=False, **kwargs)
    with_retrieval = generate_candidates(
        presentation, competition_retrieval=True, competition_retrieval_max=500, **kwargs)

    ids_without = {c.id for c in without}
    ids_with = {c.id for c in with_retrieval}
    must_not_miss_without = {d for d in CROSS_CUTTING_DANGEROUS_DIAGNOSES if d in ids_without}
    must_not_miss_with = {d for d in CROSS_CUTTING_DANGEROUS_DIAGNOSES if d in ids_with}
    assert must_not_miss_without.issubset(must_not_miss_with), (
        "enabling competition_retrieval must never trim away a must-not-miss diagnosis that "
        "survived without it"
    )


def test_competition_retrieval_never_displaces_an_evidenced_kb_candidate():
    """A directly, strongly symptom-matched Tier-1 KB diagnosis must survive even when broad
    retrieval is on and aggressively sized -- evidenced candidates are always protected from
    trimming; only zero-evidence supplements (safety net / broadening / retrieval) are trimmable."""
    presentation = _presentation("sudden severe chest pain radiating to the back")
    records = generate_candidates(
        presentation, competition_retrieval=True, competition_retrieval_max=500,
        chief_complaint_text="sudden severe chest pain radiating to the back",
    )
    ids_present = {c.id for c in records}
    assert "aortic_dissection" in ids_present
    assert "acute_coronary_syndrome" in ids_present


def test_retrieval_failure_falls_back_to_deterministic_pool_safely(monkeypatch):
    """If the ontology catalog/retriever fails to load or raises mid-retrieval, DoctorAgent must
    continue safely on the existing deterministic path -- no crash, no case interruption."""
    import nova_agent.ontology.registry as registry_module

    def _boom():
        raise RuntimeError("simulated catalog load failure")

    monkeypatch.setattr(registry_module, "get_default_catalog", _boom)

    presentation = _presentation("sudden severe chest pain radiating to the back")
    records = generate_candidates(
        presentation, competition_retrieval=True, competition_retrieval_max=10,
        chief_complaint_text="sudden severe chest pain radiating to the back",
    )
    # Deterministic KB candidates still present; nothing crashed.
    ids_present = {c.id for c in records}
    assert "acute_coronary_syndrome" in ids_present
    assert not any("ontology_retrieval" in c.sources for c in records)


def test_config_flag_defaults_on_for_competition_provider(monkeypatch):
    monkeypatch.delenv("NOVA_COMPETITION_RETRIEVAL", raising=False)
    monkeypatch.setenv("NOVA_LLM_PROVIDER", "competition")
    cfg = get_config(reload=True)
    assert cfg.competition_retrieval_enabled is True


def test_config_flag_defaults_off_for_mock_provider(monkeypatch):
    monkeypatch.delenv("NOVA_COMPETITION_RETRIEVAL", raising=False)
    monkeypatch.setenv("NOVA_LLM_PROVIDER", "mock")
    cfg = get_config(reload=True)
    assert cfg.competition_retrieval_enabled is False


def test_config_flag_can_be_forced_regardless_of_provider(monkeypatch):
    monkeypatch.setenv("NOVA_LLM_PROVIDER", "mock")
    monkeypatch.setenv("NOVA_COMPETITION_RETRIEVAL", "true")
    cfg = get_config(reload=True)
    assert cfg.competition_retrieval_enabled is True

    monkeypatch.setenv("NOVA_LLM_PROVIDER", "competition")
    monkeypatch.setenv("NOVA_COMPETITION_RETRIEVAL", "false")
    cfg = get_config(reload=True)
    assert cfg.competition_retrieval_enabled is False


def test_real_llm_gate_is_untouched_by_broad_retrieval(monkeypatch):
    """Regression proving the real_llm_ever_succeeded competition DIAGNOSE gate
    (competition/adapter.py, state.py) cannot be satisfied by enabling broad retrieval: it starts
    None (no real LLM call attempted yet) and a differential update -- which now exercises the
    ontology retrieval path (a pure catalog lookup, never an LLM call) -- must leave it None, not
    flip it toward a truthy 'success' value. Only an actual successful real LLM call may."""
    monkeypatch.setenv("NOVA_LLM_PROVIDER", "competition")
    monkeypatch.setenv("NOVA_COMPETITION_RETRIEVAL", "true")
    get_config(reload=True)

    from nova_agent.differential import DifferentialEngine
    from nova_agent.state import PatientState

    state = PatientState(case_id="gate-check", chief_complaint="sudden severe chest pain radiating to the back")
    assert state.real_llm_ever_succeeded is None

    DifferentialEngine().update(state)
    assert state.real_llm_ever_succeeded is None, (
        "broad retrieval must never itself satisfy or otherwise touch the real-LLM-success gate"
    )
    assert state.llm_call_count == 0
