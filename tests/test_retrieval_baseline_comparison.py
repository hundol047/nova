"""Guards the honesty contract of the baseline-vs-new retrieval comparison: the recorded baseline
constants in scripts/benchmark_competition_retrieval.py must stay clearly labeled and distinct
from the live-measured numbers -- never silently overwritten to make a comparison look better."""

from __future__ import annotations

from scripts.benchmark_competition_retrieval import BASELINE_LABEL, BASELINE_RECALL, measure


def test_baseline_is_a_fixed_recorded_constant_not_a_recomputation():
    # The baseline for chief_complaint_only must be the pre-round numbers, materially different
    # from (lower than) what this round's code actually measures now.
    live = measure(use_history=False)
    baseline = BASELINE_RECALL["chief_complaint_only"]
    assert live.recall_at[20] != baseline[20], (
        "baseline and live measurement are identical -- baseline may have been accidentally "
        "recomputed instead of using the recorded pre-change reference"
    )


def test_baseline_label_documents_its_provenance():
    assert "commit" in BASELINE_LABEL.lower() or "sha" in BASELINE_LABEL.lower()


def test_both_conditions_have_recorded_baselines():
    assert set(BASELINE_RECALL) == {"chief_complaint_only", "chief_complaint_plus_history"}
    for condition, recall_by_k in BASELINE_RECALL.items():
        assert set(recall_by_k) == {20, 50, 100}
