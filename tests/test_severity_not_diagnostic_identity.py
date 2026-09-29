"""Round E, defect C: generic physiologic-severity markers (hypotension, tachycardia, tachypnea,
fever, hypoxia, ...) must never by themselves identify WHICH dangerous diagnosis is present --
they mark a PATIENT as sick, shared across dozens of diseases' own typical_features. Tests
differential.py's `_specificity_multiplier()` / severity_evidence.GENERIC_PHYSIOLOGIC_SEVERITY_WORDS
directly, as a general mechanism (never a single hardcoded case).
"""

from __future__ import annotations

import pytest

from nova_agent.differential import _GENERIC_SEVERITY_MULTIPLIER, _specificity_multiplier
from nova_agent.severity_evidence import GENERIC_PHYSIOLOGIC_SEVERITY_WORDS


@pytest.mark.parametrize("word", sorted(GENERIC_PHYSIOLOGIC_SEVERITY_WORDS))
def test_bare_generic_severity_word_gets_the_reduced_multiplier(word):
    assert _specificity_multiplier(word) == _GENERIC_SEVERITY_MULTIPLIER


@pytest.mark.parametrize("phrase", [
    "wheeze", "urticaria", "irregularly irregular rhythm", "widened mediastinum",
    "productive cough", "unilateral pulsating headache", "thunderclap headache",
])
def test_genuinely_disease_specific_phrase_keeps_its_normal_weight(phrase):
    assert _specificity_multiplier(phrase) != _GENERIC_SEVERITY_MULTIPLIER
    assert _specificity_multiplier(phrase) >= 1.0


def test_reduced_multiplier_is_nonzero_but_much_smaller_than_normal():
    # Spec: generic severity may still keep a dangerous alternative active / raise urgency -- it
    # must never contribute ZERO evidence, only much LESS than genuinely specific evidence.
    assert 0.0 < _GENERIC_SEVERITY_MULTIPLIER < 1.0


def test_severity_score_is_never_imported_into_diagnostic_scoring():
    # Structural guard: differential.py must never import (and therefore can never call)
    # severity_evidence.severity_score() -- proving the two axes stay architecturally separate
    # (severity_score is consumed only by stop_policy.py/action_selector.py, never by
    # _score_disease() itself). A plain source-text search would also flag this file's own
    # explanatory comments ABOUT the separation, so this checks the actual import surface instead.
    import nova_agent.differential as differential_module

    assert not hasattr(differential_module, "severity_score"), (
        "differential.py must never import severity_evidence.severity_score() -- "
        "physiologic severity and diagnostic support must stay separate axes"
    )
