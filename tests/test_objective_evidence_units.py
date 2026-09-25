"""Unit-safety regression tests for numeric objective-evidence interpretation (spec section 19 /
clinical safety: an ambiguous or unexpected unit must never receive an arbitrary numeric clinical
interpretation).

These assert a generic safety invariant, NOT any blind-evaluation case: a lab NUMBER stated in a
non-mg/dL unit must not be silently read as mg/dL, and a result that cannot be parsed must yield
"no evidence either way" (None / "unknown"), never a fabricated value.
"""
import pytest


# glucose_evidence has no pydantic dependency, but importing it via the nova_agent package would
# trigger nova_agent/__init__ (which imports the pydantic-based orchestrator). Import the module by
# file path so this test runs even in a minimal environment.
def _load_glucose_module():
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "nova_agent" / "glucose_evidence.py"
    spec = importlib.util.spec_from_file_location("glucose_evidence_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ge = _load_glucose_module()


class TestGlucoseUnitSafety:
    def test_mg_dl_values_are_interpreted(self):
        assert ge.extract_glucose_mg_dl("blood glucose 42 mg/dL") == 42.0
        assert ge.extract_glucose_mg_dl("blood glucose 400 mg/dL") == 400.0

    def test_mmol_l_values_are_not_misread_as_mg_dl(self):
        # A value explicitly in mmol/L must NOT be interpreted as a mg/dL number. 90 mmol/L is a
        # physiologically impossible mg/dL reading -- the digit must not be grabbed.
        assert ge.extract_glucose_mg_dl("glucose 90 mmol/L") is None
        # Sub-threshold hypoglycemic-range mmol/L values were already correctly rejected (1-digit),
        # but assert them so the guard is covered end to end.
        assert ge.extract_glucose_mg_dl("glucose 5.5 mmol/L") is None
        assert ge.extract_glucose_mg_dl("glucose 3.9 mmol/L") is None

    def test_mixed_unit_text_with_explicit_mg_dl_is_still_interpreted(self):
        # If an explicit mg/dL value is present, a parenthetical mmol/L conversion must not block it.
        assert ge.extract_glucose_mg_dl("glucose 65 mg/dL (3.6 mmol/L)") == 65.0

    def test_unreadable_high_meter_code_is_treated_as_very_high(self):
        assert ge.extract_glucose_mg_dl("unreadable on meter, critical high") == ge.UNREADABLE_HIGH_SENTINEL_MG_DL
        assert ge.extract_glucose_mg_dl("HI") == ge.UNREADABLE_HIGH_SENTINEL_MG_DL

    def test_unparseable_or_missing_result_is_none_not_zero(self):
        for text in ("glucose pending", "", None, "sample hemolyzed"):
            assert ge.extract_glucose_mg_dl(text) is None


# The full objective_evidence registry (potassium/sodium/creatinine/... numeric; troponin/D-dimer/
# CRP/ketone/beta-hCG qualitative-only) imports pydantic-based state, so it is exercised by the
# CI nova-agent job's normal pytest import path. This module keeps the pydantic-free glucose guard
# runnable everywhere; the objective_evidence "unknown-interpretation" guard is asserted below only
# when the environment can import the package (skipped cleanly otherwise, never a false PASS).
try:
    from nova_agent.objective_evidence import normalize_objective_evidence  # noqa: F401
    _HAVE_OBJECTIVE_EVIDENCE = True
except Exception:
    _HAVE_OBJECTIVE_EVIDENCE = False


@pytest.mark.skipif(not _HAVE_OBJECTIVE_EVIDENCE, reason="nova_agent package (pydantic) not importable")
class TestObjectiveEvidenceUnknownGuard:
    def test_unrecognized_result_is_not_forced_into_a_direction(self):
        from nova_agent.state import PatientState
        state = PatientState(case_id="ue-1", chief_complaint="weakness")
        # A potassium result that is neither a parseable number nor a recognized qualitative word
        # must be marked "unknown" (a test was done, but its direction is unreadable) -- never a
        # fabricated high/low/normal. normalize_objective_evidence returns a dict keyed by
        # canonical id (e.g. "lab.potassium").
        state.laboratory_tests["potassium"] = "sample clotted, please redraw"
        findings = normalize_objective_evidence(state)
        pot = findings.get("lab.potassium")
        assert pot is not None, "a recorded (if unreadable) result should still surface as evidence"
        assert pot.interpretation == "unknown"
        assert pot.value is None  # never fabricated as 0 or a guessed number

    def test_numeric_potassium_is_interpreted_with_its_own_unit(self):
        from nova_agent.state import PatientState
        state = PatientState(case_id="ue-2", chief_complaint="weakness")
        # The panel pattern locates "<analyte> <number>", so the value text names the analyte
        # (as a real EMR/panel result string does).
        state.laboratory_tests["potassium"] = "potassium 6.8 mEq/L"
        findings = normalize_objective_evidence(state)
        pot = findings.get("lab.potassium")
        assert pot is not None and pot.value == 6.8
        assert pot.interpretation in ("high", "critical_high")  # 6.8 is hyperkalemic (crit_high 6.5)



# --- Area 1: build_clinical_presentation must not re-inject denied findings as positives ---------
try:
    from nova_agent.clinical_presentation import build_clinical_presentation  # noqa: F401
    _HAVE_PRESENTATION = True
except Exception:
    _HAVE_PRESENTATION = False


@pytest.mark.skipif(not _HAVE_PRESENTATION, reason="nova_agent package (pydantic) not importable")
class TestNegationNotReinjected:
    def test_denied_finding_is_not_reinjected_as_a_positive_concept(self):
        """A finding the patient explicitly DENIES (recorded into pertinent_negatives) must not be
        rebuilt into the positive presentation on a later turn. Complements test_negation_scope
        (which asserts the state.py classification) by asserting the presentation-rebuild step
        itself does not scan pertinent_negatives."""
        from nova_agent.state import PatientState
        from nova_agent.clinical_presentation import build_clinical_presentation

        state = PatientState(case_id="neg-1", chief_complaint="headache")
        # Patient denies chest pain -> classified into pertinent_negatives by _absorb_answer.
        state.record_ask("associated_symptoms", "Any chest pain?", "Patient denies chest pain.")
        assert any("chest" in n.lower() for n in state.pertinent_negatives), \
            "precondition: the denial should be in pertinent_negatives"
        presentation = build_clinical_presentation(state)
        # The rebuilt presentation's positive concept tags (ClinicalPresentation.symptoms /
        # associated_features) must not contain the denied 'chest_pain' concept.
        positive_tags = set(getattr(presentation, "symptoms", []) or []) \
            | set(getattr(presentation, "associated_features", []) or [])
        assert "chest_pain" not in positive_tags
