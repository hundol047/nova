"""Generalized numeric/qualitative objective lab evidence normalization (spec: generalize the
glucose/lactate-only numeric-interpretation pattern to the rest of the labs this knowledge base's
`confirmatory_findings` actually reference -- troponin, D-dimer, potassium, sodium, creatinine,
WBC, hemoglobin, platelet, pH, bicarbonate, ketones, CRP, beta-hCG).

Word-overlap matching (matching.py) treats a bare number as opaque text: "potassium 6.9 mEq/L" and
"potassium 3.9 mEq/L" share every content word, so a knowledge-base phrase like "hyperkalemia" or
"elevated potassium" -- which requires the literal word "elevated"/"hyper-" to be PRESENT in the
finding text -- gets NO credit at all from a raw, unannotated lab number, even though the number
alone is exactly what a real FHIR Observation resource or an unembellished lab report would give a
clinician. `glucose_evidence.py` and `severity_evidence.py`'s lactate handling already solved this
for exactly two labs; this module is the same idea generalized to the rest, kept in ONE place with
ONE canonical-ID naming scheme (`lab.<name>`) instead of N bespoke per-lab functions -- and, unlike
glucose_evidence.py, using a REGISTRY (`LAB_SPECS`) so a new lab is one table entry, not one new
function threaded through differential.py by hand.

Threshold honesty (spec: never a number fitted to a specific benchmark case): every threshold
below is the standard, textbook adult reference range/definition. A few labs (troponin, D-dimer,
CRP) are deliberately handled QUALITATIVELY ONLY (an "elevated"/"positive"/"markedly elevated"
word in the result text, or normal/negative) rather than a fixed numeric ng/mL or mg/L cutoff --
real assays for these vary by roughly an order of magnitude between standard and high-sensitivity
methods, and a single hardcoded cutoff across assay types would be clinically wrong, not just
imprecise, so this module does not pretend to have one. This is a disclosed limitation, not an
oversight: see each LabSpec's own `numeric_pattern=None` and docstring note below.

Deliberately does NOT replace glucose_evidence.py or severity_evidence.py's lactate handling --
both are already independently verified and tuned (differential.py's `_score_glucose`/
`_score_lactate`); this module reads the same two values through their existing extractors for
canonical-ID consistency (`lab.glucose`/`lab.lactate` alongside the labs newly added here), never
re-deriving them with a second, competing implementation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from nova_agent.glucose_evidence import extract_glucose_mg_dl
from nova_agent.severity_evidence import extract_lactate_mmol_l
from nova_agent.state import PatientState

Direction = str  # "high" | "low" -- which side of normal counts as abnormal for a given lab


@dataclass(frozen=True)
class LabSpec:
    canonical_id: str
    display_name: str
    unit: str
    raw_keys: tuple  # PatientState.laboratory_tests keys this lab's value may be reported under
    # Numeric interpretation (omitted -- None -- for assay-variable labs, see module docstring).
    numeric_pattern: Optional[re.Pattern]
    low: Optional[float] = None
    high: Optional[float] = None
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None
    # Qualitative fallback: words in the raw text that mean "abnormal in the `high`/`low`
    # direction" even with no parseable number (e.g. "elevated troponin", "large ketones").
    qualitative_high_words: tuple = ()
    qualitative_low_words: tuple = ()
    qualitative_normal_words: tuple = ()


def _panel_pattern(*names: str) -> re.Pattern:
    """Builds a pattern that finds `<analyte name> <number>` anywhere in a combined panel string
    (e.g. a single "bmp"/"basic_metabolic_panel" result reporting several analytes at once, such
    as "potassium 6.9, creatinine elevated above baseline") -- not just a whole-string number, so
    one analyte's presence/absence doesn't depend on where in the panel string it appears."""
    alternation = "|".join(re.escape(n) for n in names)
    return re.compile(rf"(?:{alternation})[^0-9]{{0,15}}?(\d{{1,3}}(?:\.\d+)?)", re.IGNORECASE)


LAB_SPECS: Dict[str, LabSpec] = {
    "lab.potassium": LabSpec(
        canonical_id="lab.potassium", display_name="potassium", unit="mEq/L",
        raw_keys=("potassium", "bmp", "basic_metabolic_panel"),
        numeric_pattern=_panel_pattern("potassium", r"\bk\b"),
        low=3.5, high=5.0, critical_low=2.5, critical_high=6.5,
        qualitative_high_words=("hyperkalemia", "elevated potassium"),
        qualitative_low_words=("hypokalemia", "low potassium"),
    ),
    "lab.sodium": LabSpec(
        canonical_id="lab.sodium", display_name="sodium", unit="mEq/L",
        raw_keys=("sodium", "bmp", "basic_metabolic_panel"),
        numeric_pattern=_panel_pattern("sodium", r"\bna\b"),
        low=135.0, high=145.0, critical_low=120.0, critical_high=155.0,
        qualitative_high_words=("hypernatremia", "elevated sodium"),
        qualitative_low_words=("hyponatremia", "low sodium"),
    ),
    "lab.creatinine": LabSpec(
        canonical_id="lab.creatinine", display_name="creatinine", unit="mg/dL",
        raw_keys=("creatinine", "bmp", "basic_metabolic_panel"),
        numeric_pattern=_panel_pattern("creatinine"),
        # A single absolute cutoff is a real simplification (true AKI is defined by a RISE from a
        # patient's own baseline, not one absolute number) -- disclosed, not hidden: this flags a
        # plausibly-abnormal single value only, it is not a substitute for trend/baseline
        # comparison (see clinical_presentation.py's temporal-evidence item for that).
        high=1.3, critical_high=4.0,
        qualitative_high_words=("elevated creatinine", "rising creatinine", "acute kidney injury"),
    ),
    "lab.wbc": LabSpec(
        canonical_id="lab.wbc", display_name="white blood cell count", unit="x10^3/uL",
        raw_keys=("wbc", "cbc"),
        numeric_pattern=_panel_pattern("wbc", "white blood cell count", "white blood cells"),
        low=4.0, high=11.0, critical_low=1.0, critical_high=20.0,
        qualitative_high_words=("elevated white blood cell count", "leukocytosis"),
        qualitative_low_words=("low white blood cell count", "leukopenia", "neutropenic", "neutropenia"),
    ),
    "lab.hemoglobin": LabSpec(
        canonical_id="lab.hemoglobin", display_name="hemoglobin", unit="g/dL",
        raw_keys=("hemoglobin", "cbc"),
        numeric_pattern=_panel_pattern("hemoglobin", r"\bhgb\b", r"\bhb\b"),
        # Unisex conservative adult cutoff (true normal range is sex-specific) -- a disclosed
        # simplification, same spirit as the creatinine note above.
        low=12.0, critical_low=7.0,
        qualitative_low_words=("low hemoglobin", "anemia", "hemoglobin drop"),
    ),
    "lab.platelet": LabSpec(
        canonical_id="lab.platelet", display_name="platelet count", unit="x10^3/uL",
        raw_keys=("platelet", "platelets", "cbc"),
        numeric_pattern=_panel_pattern("platelet", "platelets"),
        low=150.0, critical_low=50.0,
        qualitative_low_words=("thrombocytopenia", "low platelet"),
    ),
    "lab.ph": LabSpec(
        canonical_id="lab.ph", display_name="pH", unit="",
        raw_keys=("ph", "abg", "vbg"),
        numeric_pattern=re.compile(r"\bph[^0-9]{0,10}?(\d\.\d{1,2})", re.IGNORECASE),
        low=7.35, high=7.45, critical_low=7.20,
        qualitative_low_words=("acidosis", "metabolic acidosis"),
        qualitative_high_words=("alkalosis",),
    ),
    "lab.bicarbonate": LabSpec(
        canonical_id="lab.bicarbonate", display_name="bicarbonate", unit="mEq/L",
        raw_keys=("bicarbonate", "hco3", "abg", "bmp", "basic_metabolic_panel"),
        numeric_pattern=_panel_pattern("bicarbonate", "hco3"),
        low=22.0, high=26.0, critical_low=15.0,
        qualitative_low_words=("metabolic acidosis",),
    ),
    # Troponin/D-dimer/CRP: no numeric_pattern -- deliberately qualitative-only, see module
    # docstring (assay-dependent cutoffs; a single hardcoded number would be clinically wrong).
    "lab.troponin": LabSpec(
        canonical_id="lab.troponin", display_name="troponin", unit="",
        raw_keys=("troponin",), numeric_pattern=None,
        qualitative_high_words=("elevated troponin", "troponin elevated", "positive troponin",
                                 "markedly elevated"),
        qualitative_normal_words=("not elevated", "within normal limits", "negative", "normal"),
    ),
    "lab.d_dimer": LabSpec(
        canonical_id="lab.d_dimer", display_name="D-dimer", unit="",
        raw_keys=("d_dimer",), numeric_pattern=None,
        qualitative_high_words=("elevated d-dimer", "elevated d dimer", "markedly elevated",
                                 "positive"),
        qualitative_normal_words=("not elevated", "within normal limits", "negative", "normal"),
    ),
    "lab.crp": LabSpec(
        canonical_id="lab.crp", display_name="CRP", unit="",
        raw_keys=("crp",), numeric_pattern=None,
        qualitative_high_words=("elevated crp", "elevated c-reactive protein", "markedly elevated"),
        qualitative_normal_words=("not elevated", "within normal limits", "negative", "normal"),
    ),
    "lab.ketones": LabSpec(
        canonical_id="lab.ketones", display_name="urine/serum ketones", unit="",
        raw_keys=("ketones", "urinalysis"), numeric_pattern=None,
        qualitative_high_words=("large ketones", "moderate ketones", "positive ketones"),
        qualitative_normal_words=("negative", "trace ketones", "no ketones"),
    ),
    "lab.beta_hcg": LabSpec(
        canonical_id="lab.beta_hcg", display_name="beta-hCG", unit="",
        raw_keys=("beta_hcg", "hcg", "pregnancy_test"), numeric_pattern=None,
        qualitative_high_words=("positive beta-hcg", "positive hcg", "positive pregnancy test"),
        qualitative_normal_words=("negative",),
    ),
}


@dataclass
class ObjectiveFinding:
    canonical_id: str
    display_name: str
    raw_text: str
    value: Optional[float]
    unit: str
    # "critical_high" | "high" | "normal" | "low" | "critical_low" | "abnormal" | "unknown"
    interpretation: str
    evidence_label: str  # human-readable, for supporting/contradictory_evidence lists


def _extract_numeric(spec: LabSpec, raw_texts: List[str]) -> Optional[float]:
    if spec.numeric_pattern is None:
        return None
    for text in raw_texts:
        match = spec.numeric_pattern.search(text)
        if match:
            try:
                return float(match.group(1))
            except (ValueError, IndexError):
                continue
    return None


def _interpret_numeric(spec: LabSpec, value: float) -> str:
    if spec.critical_low is not None and value <= spec.critical_low:
        return "critical_low"
    if spec.critical_high is not None and value >= spec.critical_high:
        return "critical_high"
    if spec.low is not None and value < spec.low:
        return "low"
    if spec.high is not None and value > spec.high:
        return "high"
    return "normal"


def _interpret_qualitative(spec: LabSpec, raw_texts: List[str]) -> Optional[str]:
    combined = " ".join(t.lower() for t in raw_texts)
    for word in spec.qualitative_high_words:
        if word in combined:
            return "high"
    for word in spec.qualitative_low_words:
        if word in combined:
            return "low"
    for word in spec.qualitative_normal_words:
        if word in combined:
            return "normal"
    return None


def normalize_one(spec: LabSpec, state: PatientState) -> Optional[ObjectiveFinding]:
    """Normalizes ONE lab spec against whatever raw result text is present in
    `state.laboratory_tests` under any of its `raw_keys`. Returns None if that lab was never
    tested (no evidence either way -- never fabricated as "normal")."""
    raw_texts = [state.laboratory_tests[k] for k in spec.raw_keys if state.laboratory_tests.get(k)]
    if not raw_texts:
        return None
    value = _extract_numeric(spec, raw_texts)
    if value is not None:
        interpretation = _interpret_numeric(spec, value)
        label = f"{spec.display_name} {value:g}{(' ' + spec.unit) if spec.unit else ''} ({interpretation.replace('_', ' ')})"
        return ObjectiveFinding(spec.canonical_id, spec.display_name, "; ".join(raw_texts), value,
                                 spec.unit, interpretation, label)
    qualitative = _interpret_qualitative(spec, raw_texts)
    if qualitative is not None:
        label = f"{spec.display_name} ({qualitative})" if qualitative != "normal" \
            else f"{spec.display_name} not elevated"
        return ObjectiveFinding(spec.canonical_id, spec.display_name, "; ".join(raw_texts), None,
                                 spec.unit, qualitative, label)
    # A result was recorded but neither a number nor a recognized qualitative word could be read
    # from it -- real evidence that a test was DONE, but its direction is unreadable; callers must
    # not treat this as either supporting or contradicting anything.
    return ObjectiveFinding(spec.canonical_id, spec.display_name, "; ".join(raw_texts), None,
                             spec.unit, "unknown", f"{spec.display_name} (result not interpretable)")


def normalize_objective_evidence(state: PatientState) -> Dict[str, ObjectiveFinding]:
    """Every objective lab finding actually available on `state` right now, keyed by canonical ID
    (`lab.potassium`, `lab.troponin`, ...) -- re-derived fresh every call (never cached), the same
    "recompute from current state every turn" discipline as differential.py's ranking and
    clinical_presentation.build_clinical_presentation(). Includes glucose/lactate too (delegating
    to their own already-verified extractors) so callers get ONE complete, canonically-keyed map
    instead of having to separately special-case those two."""
    findings: Dict[str, ObjectiveFinding] = {}
    for spec in LAB_SPECS.values():
        finding = normalize_one(spec, state)
        if finding is not None:
            findings[spec.canonical_id] = finding

    glucose = extract_glucose_mg_dl(state.laboratory_tests.get("glucose_point_of_care"))
    if glucose is not None:
        findings["lab.glucose"] = ObjectiveFinding(
            "lab.glucose", "glucose", state.laboratory_tests.get("glucose_point_of_care", ""),
            glucose, "mg/dL",
            "critical_low" if glucose < 54 else "low" if glucose < 70 else
            "critical_high" if glucose >= 400 else "high" if glucose >= 250 else "normal",
            f"point-of-care glucose {glucose:g} mg/dL",
        )
    lactate = extract_lactate_mmol_l(state.laboratory_tests.get("lactate"))
    if lactate is not None:
        findings["lab.lactate"] = ObjectiveFinding(
            "lab.lactate", "lactate", state.laboratory_tests.get("lactate", ""), lactate, "mmol/L",
            "critical_high" if lactate >= 4.0 else "high" if lactate >= 2.0 else "normal",
            f"lactate {lactate:g} mmol/L",
        )
    return findings


# Confirmatory-finding phrase -> (canonical lab id, direction the phrase asserts) -- used by
# differential.py to give a numeric-aware score to the SPECIFIC knowledge-base phrases that name a
# lab this module understands, while leaving every other confirmatory_finding phrase (ECG/imaging
# text, qualitative-only findings with no lab mapping here) on the existing plain word-overlap
# path untouched. Keys are lower-cased KB phrase text, matched exactly against
# disease["confirmatory_findings"]/["typical_features"] entries.
CONFIRMATORY_PHRASE_TO_LAB: Dict[str, tuple] = {
    "elevated troponin": ("lab.troponin", "high"),
    "troponin elevated": ("lab.troponin", "high"),
    "elevated d-dimer": ("lab.d_dimer", "high"),
    "hyperkalemia": ("lab.potassium", "high"),
    "elevated potassium": ("lab.potassium", "high"),
    "hyponatremia": ("lab.sodium", "low"),
    "low sodium": ("lab.sodium", "low"),
    "elevated white blood cell count": ("lab.wbc", "high"),
    "low hemoglobin": ("lab.hemoglobin", "low"),
    "hemoglobin drop": ("lab.hemoglobin", "low"),
    "large ketones": ("lab.ketones", "high"),
    "positive beta-hcg": ("lab.beta_hcg", "high"),
}
