"""Scoring identity must not depend on runtime fixes or break nested names."""
from evaluation.clinical_label_identity import same_label


def test_nested_canonical_display_keeps_its_identity():
    assert same_label('근골격계 흉통 (Musculoskeletal Chest Pain (Costochondritis))',
                      'musculoskeletal_chest_pain')
    assert same_label('Musculoskeletal Chest Pain (Costochondritis)',
                      'musculoskeletal_chest_pain')


def test_conflicting_bilingual_display_does_not_match():
    assert not same_label('asthma (pneumonia)', 'asthma')
    assert not same_label('asthma (pneumonia)', 'pneumonia')


def test_exact_duplicate_catalog_term_is_one_identity():
    assert same_label('위식도역류병 (Gastroesophageal Reflux Disease)', 'gerd')


def test_unbalanced_display_cannot_supply_partial_identity():
    assert not same_label('unrelated (asthma', 'asthma')
