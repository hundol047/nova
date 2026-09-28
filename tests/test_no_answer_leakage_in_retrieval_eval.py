"""Guards against the exact forbidden pattern the retrieval evaluation utility must never fall
into: `query = expected_diagnosis` (or any equivalent leakage of the ground-truth answer into the
retrieval query used to measure recall)."""

from __future__ import annotations

from evaluation.generalization_cases_v2 import GENERALIZATION_CASES_V2
from evaluation.generalization_stress_cases import GENERALIZATION_STRESS_CASES
from evaluation.held_out_cases import HELD_OUT_CASES
from nova_agent.knowledge.retrieval import disease_by_id

_ALL_CASES = list(HELD_OUT_CASES) + list(GENERALIZATION_CASES_V2) + list(GENERALIZATION_STRESS_CASES)


def test_benchmark_script_never_uses_the_ground_truth_diagnosis_as_the_query():
    """Static check on the actual evaluation utility's source: it must query only
    case.chief_complaint / case.answers.values(), never case.ground_truth_diagnosis."""
    import inspect

    from scripts.benchmark_competition_retrieval import measure

    source = inspect.getsource(measure)
    assert "ground_truth_diagnosis" in source, "the function must at least reference it (to look up the target concept)"
    # The only correct uses of ground_truth_diagnosis are as a lookup key / leakage assertion --
    # never passed as `chief_complaint=` or `history=` (the actual query arguments).
    assert "chief_complaint=gt" not in source
    assert "chief_complaint=case.ground_truth_diagnosis" not in source
    assert "history=[gt]" not in source


def test_no_case_chief_complaint_literally_contains_its_own_ground_truth_diagnosis_name():
    """Direct data check: for every real synthetic case, the disease's own canonical name/aliases
    must not appear verbatim in the chief complaint text -- otherwise a recall measurement against
    that case would be trivially inflated regardless of retrieval quality."""
    leaks = []
    for case in _ALL_CASES:
        gt = getattr(case, "ground_truth_diagnosis", None)
        if not gt:
            continue
        entry = disease_by_id(gt)
        if entry is None:
            continue
        names_to_check = [entry["name"]] + list(entry.get("aliases", []))
        complaint_lower = case.chief_complaint.lower()
        for name in names_to_check:
            if len(name) >= 4 and name.lower() in complaint_lower:
                leaks.append((case.case_id, name))
    assert not leaks, f"chief_complaint text leaks the ground-truth diagnosis name/alias: {leaks}"
