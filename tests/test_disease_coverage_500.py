"""Disease coverage + search validation (vNext PART I) — dependency-free.

Asserts the 500+ bundled catalog is real and well-formed, all 34 Tier-1 deep profiles are
preserved, categories/curation/codes are valid, required specialties have meaningful coverage, and
representative conditions (including abbreviations and Korean aliases) are searchable.
"""

from __future__ import annotations

import re
import sys
import types
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if "nova_agent" not in sys.modules:
    _pkg = types.ModuleType("nova_agent")
    _pkg.__path__ = [str(_ROOT / "nova_agent")]
    sys.modules["nova_agent"] = _pkg

from nova_agent.ontology.models import Tier  # noqa: E402
from nova_agent.ontology.registry import build_catalog  # noqa: E402

CATALOG = build_catalog()
_VALID_CURATION = {"DEEP", "STRUCTURED", "NOT_CURATED"}
_ICD10_RE = re.compile(r"^[A-Z]\d{2}(\.[0-9A-Z]{1,4})?$")  # loose ICD-10(-CM) category shape


def test_bundled_total_at_least_500():
    bundled = [c for c in CATALOG.all_concepts()
               if c.tier in (Tier.TIER1_DEEP, Tier.TIER2_STRUCTURED)]
    assert len(bundled) >= 500, f"bundled catalog must be >=500, got {len(bundled)}"


def test_all_34_tier1_deep_preserved():
    tier1 = [c for c in CATALOG.all_concepts() if c.tier == Tier.TIER1_DEEP]
    assert len(tier1) == 34


def test_no_duplicate_concept_ids():
    ids = [c.concept_id for c in CATALOG.all_concepts()]
    assert len(ids) == len(set(ids))


def test_every_concept_has_valid_category_and_curation():
    for c in CATALOG.all_concepts():
        assert c.category and isinstance(c.category, str)
        assert c.curation_status in _VALID_CURATION


def test_external_codes_well_formed():
    bad = []
    for c in CATALOG.all_concepts():
        for code in c.external_codes:
            if code.system == "ICD10" and not _ICD10_RE.match(code.code):
                bad.append(f"{c.concept_id}:{code.code}")
    assert not bad, f"malformed ICD-10 codes: {bad[:10]}"


def test_no_duplicate_aliases_within_a_concept():
    for c in CATALOG.all_concepts():
        lowered = [a.strip().lower() for a in c.aliases]
        assert len(lowered) == len(set(lowered)), f"duplicate aliases in {c.concept_id}"


REQUIRED_SPECIALTIES_MIN = {
    "cardiovascular": 10, "pulmonary": 10, "neuro": 10, "abdominal_gi": 10,
    "infectious": 8, "hematology": 5, "oncology": 5, "endocrine_metabolic": 8,
    "toxicology": 5, "obstetric": 5, "pediatric": 5, "ophthalmology": 5,
    "ent": 5, "rheumatology": 5, "nephrology": 5, "dermatology": 5,
}


def test_required_specialties_have_meaningful_coverage():
    counts: dict = {}
    for c in CATALOG.all_concepts():
        counts[c.category] = counts.get(c.category, 0) + 1
    missing = {k: (v, counts.get(k, 0)) for k, v in REQUIRED_SPECIALTIES_MIN.items()
               if counts.get(k, 0) < v}
    assert not missing, f"specialties below coverage threshold: {missing}"


import pytest  # noqa: E402


@pytest.mark.parametrize("query,expect_substr", [
    ("myocarditis", "Myocarditis"),
    ("cholangitis", "Cholangitis"),
    ("GBS", "Guillain"),
    ("ovarian torsion", "Ovarian Torsion"),
    ("TTP", "Thrombotic Thrombocytopenic"),
    ("carbon monoxide poisoning", "Carbon Monoxide"),
    ("Kawasaki disease", "Kawasaki"),
    ("SJS", "Stevens-Johnson"),
])
def test_required_search_examples_resolve(query, expect_substr):
    hits = CATALOG.search_conditions(query, limit=3)
    assert hits, f"no match for {query!r}"
    assert any(expect_substr.lower() in h.concept.canonical_name.lower() for h in hits), \
        f"{query!r} did not resolve to a concept containing {expect_substr!r}"


@pytest.mark.parametrize("query,expect_substr", [
    ("통풍", "Gout"),                    # Korean alias
    ("겸상 적혈구병", "Sickle Cell"),      # Korean alias
    ("대상포진", "Herpes Zoster"),         # Korean alias
])
def test_multilingual_synonym_search(query, expect_substr):
    hits = CATALOG.search_conditions(query, limit=3)
    assert hits and any(expect_substr.lower() in h.concept.canonical_name.lower() for h in hits)
