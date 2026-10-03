"""Exhaustive coverage checks for the multilingual display layer (spec: DoctorAgent(lang=...)
extended to ko/en/ja/zh) -- every QUESTION_CATALOG/EXAM_CATALOG/TEST_CATALOG entry must have
ja/zh text (not just the pre-existing en/ko), and the diagnosis display table must cover every
diagnosis currently in the knowledge base, so neither can silently drift out of sync as entries
are added later.
"""

from __future__ import annotations

from nova_agent.i18n.diagnosis_display import DIAGNOSIS_DISPLAY, translate_diagnosis
from nova_agent.knowledge.retrieval import all_diseases
from nova_agent.taxonomy import EXAM_CATALOG, QUESTION_CATALOG, TEST_CATALOG


def test_every_question_catalog_entry_has_all_four_locales():
    for key, spec in QUESTION_CATALOG.items():
        for field in ("text_en", "text_ko", "text_ja", "text_zh"):
            assert spec.get(field), f"{key} missing {field}"


def test_every_exam_catalog_entry_has_all_four_locales():
    for key, spec in EXAM_CATALOG.items():
        for field in ("name_en", "name_ko", "name_ja", "name_zh"):
            assert spec.get(field), f"{key} missing {field}"


def test_every_test_catalog_entry_has_all_four_locales():
    for key, spec in TEST_CATALOG.items():
        for field in ("name_en", "name_ko", "name_ja", "name_zh"):
            assert spec.get(field), f"{key} missing {field}"


def test_diagnosis_display_table_covers_every_kb_diagnosis():
    kb_ids = set(all_diseases().keys())
    covered = set(DIAGNOSIS_DISPLAY.keys())
    missing = kb_ids - covered
    assert not missing, f"diagnosis_display.py has no row for: {sorted(missing)}"
    for diagnosis_id, row in DIAGNOSIS_DISPLAY.items():
        for locale in ("ko", "ja", "zh"):
            assert row.get(locale), f"{diagnosis_id} missing {locale} translation"


def test_translate_diagnosis_falls_back_to_english_for_unknown_id():
    assert translate_diagnosis("not_a_real_diagnosis", "ko", "Fallback Name") == "Fallback Name"


def test_translate_diagnosis_falls_back_to_english_for_unknown_locale():
    assert translate_diagnosis("migraine", "fr", "Migraine") == "Migraine"


def test_translate_diagnosis_returns_real_translation_for_known_pair():
    result = translate_diagnosis("migraine", "ko", "Migraine")
    assert result == "편두통"
