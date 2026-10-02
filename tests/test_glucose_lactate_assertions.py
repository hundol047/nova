"""Current-result semantics, independent of corpus wording or diagnosis labels."""
import pytest
from nova_agent.glucose_evidence import extract_glucose_mg_dl, UNREADABLE_HIGH_SENTINEL_MG_DL
from nova_agent.severity_evidence import extract_lactate_mmol_l


@pytest.mark.parametrize('text, expected', [
    ('Previously glucose 44 mg/dL; glucose 310 mg/dL', 310),
    ('Historical report: no glucose 41 mg/dL; Current glucose 420 mg/dL', 420),
    ('Possible glucose 48 mg/dL; current glucose 96 mg/dL', 96),
    ('No glucose 52 mg/dL', None),
    ('Suspected glucose 46 mg/dL', None),
    ('glucose 49 mg/dL; glucose 180 mg/dL', None),
    ('glucose 180 mg/dL; glucose 49 mg/dL', None),
    ('glucose 88 mg/dL; glucose 88 mg/dL', 88),
    ('Historical report: HI; glucose 91 mg/dL', 91),
    ('meter unreadable', None),
    ('HI', UNREADABLE_HIGH_SENTINEL_MG_DL),
    ('glucose 4.9 mmol/L', None),
    ('glucose 65 mg/dL (3.6 mmol/L)', 65),
])
def test_glucose_current_assertions_and_conflicts(text, expected):
    assert extract_glucose_mg_dl(text) == expected


@pytest.mark.parametrize('text, expected', [
    ('Prior report: lactate 7.1 mmol/L; current lactate 1.3 mmol/L', 1.3),
    ('Possible lactate 6.4 mmol/L; current lactate 1.6 mmol/L', 1.6),
    ('No elevated lactate', None),
    ('historical lactate elevated', None),
    ('lactate 1.1 mmol/L; lactate 6.2 mmol/L', None),
    ('lactate 6.2 mmol/L; lactate 1.1 mmol/L', None),
    ('lactate 2.3 mmol/L; lactate 2.3 mmol/L', 2.3),
    ('lactate 19 mg/dL', None),
    ('lactate elevated', 2.0),
    ('lactate elevated; lactate 1.1 mmol/L', None),
])
def test_lactate_current_assertions_and_conflicts(text, expected):
    assert extract_lactate_mmol_l(text) == expected
