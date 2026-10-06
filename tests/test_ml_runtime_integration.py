"""Tests for the governed ML ranker runtime integration (vNext PART D) — dependency-free.

Verifies the governance control logic WITHOUT torch/a real model (the model-loading path degrades
to fallback here, which is itself a governed outcome we assert). Confirms:
  - disabled by default,
  - enabled-but-no-model -> fallback to deterministic ordering, clinical output unchanged,
  - shadow mode never changes clinical output,
  - the merge-preserving helper never drops a deterministic candidate,
  - Safety Guard > ML priority is documented and enforced by preservation + post-safety application.
"""

from __future__ import annotations

import os

import pytest

from learning.runtime import GovernedMLRuntime, MLRuntimeConfig, _merge_preserving
from learning.schemas import CandidateFeature


def _cands(*ids):
    return [CandidateFeature(i) for i in ids]


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("NOVA_ML_RANKER_ENABLED", raising=False)
    rt = GovernedMLRuntime(MLRuntimeConfig.from_env())
    dec = rt.consult("c1", [0.0] * 72, _cands("a", "b"), ["a", "b"])
    assert dec.mode == "disabled"
    assert dec.changed_clinical_output is False


def test_enabled_without_model_falls_back_and_never_changes_output():
    rt = GovernedMLRuntime(MLRuntimeConfig(enabled=True, shadow_mode=False, model_path=""))
    dec = rt.consult("c1", [0.0] * 72, _cands("a", "b", "c"), ["a", "b", "c"])
    assert dec.mode == "fallback"
    assert dec.changed_clinical_output is False
    assert dec.ordered_concept_ids == ["a", "b", "c"]


def test_shadow_mode_never_changes_output_even_with_model_absent():
    rt = GovernedMLRuntime(MLRuntimeConfig(enabled=True, shadow_mode=True, model_path="/nonexistent.pt"))
    dec = rt.consult("c1", [0.0] * 72, _cands("a", "b"), ["a", "b"])
    # No model -> fallback (still never changes output). If a model existed it would be 'shadow'.
    assert dec.changed_clinical_output is False


def test_merge_preserving_reorders_but_never_drops():
    # ML reorders b before a and omits c entirely -> c must still be preserved (appended).
    merged = _merge_preserving(["b", "a"], ["a", "b", "c"])
    assert merged == ["b", "a", "c"]
    assert set(merged) == {"a", "b", "c"}  # nothing dropped


def test_merge_preserving_ignores_ml_hallucinated_ids():
    # ML proposes an id not in the deterministic set -> ignored (ML cannot inject candidates here).
    merged = _merge_preserving(["zzz", "a"], ["a", "b"])
    assert merged == ["a", "b"]


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("NOVA_ML_RANKER_ENABLED", "true")
    monkeypatch.setenv("NOVA_ML_SHADOW_MODE", "false")
    monkeypatch.setenv("NOVA_ML_MODEL_PATH", "/models/x.pt")
    cfg = MLRuntimeConfig.from_env()
    assert cfg.enabled and not cfg.shadow_mode and cfg.model_path == "/models/x.pt"
