"""A small, hand-curated adversarial matching suite (Round E) measuring
matching.py's feature-match specificity as an aggregate true-positive-rate /
false-positive-rate / specificity metric, plus regression coverage for
scripts/audit_feature_match_specificity.py's own KB-wide audit. Deliberately small (not a
fabricated large-scale dataset) -- each pair earns its place by isolating one real matching
decision (a genuine match that must survive, or a generic-word collision that must not).
"""

from __future__ import annotations

from nova_agent.matching import _content_words, _distinguishing_tokens, feature_present
from scripts.audit_feature_match_specificity import KNOWN_REVIEWED_THIN_PHRASES, audit

# (kb_phrase, finding_text, expected) -- expected True means finding_text genuinely supports
# kb_phrase (a real distinguishing concept is present); expected False means it shares only
# generic/relational/anatomical filler words and must NOT count as support.
ADVERSARIAL_PAIRS = [
    ("worse after meals", "stomach burns and gets worse after I eat a big meal", True),
    ("worse after meals", "pain that gets worse when I breathe in deeply", False),
    ("chest pain after trauma", "chest pain that started right after a car accident, real trauma", True),
    ("chest pain after trauma", "chest pain after a long work shift", False),
    ("chest pain after trauma", "chest pain after climbing several flights of stairs", False),
    ("worse with exertion", "chest tightness that gets worse with exertion, like climbing stairs", True),
    ("worse with exertion", "feels worse with a loud noise nearby", False),
    ("thunderclap headache", "sudden explosive headache, worst of her life, like a thunderclap", True),
    ("thunderclap headache", "a dull headache that's been going on all week", False),
    ("irregularly irregular rhythm", "cardiac exam: irregularly irregular rhythm noted", True),
    ("irregularly irregular rhythm", "vital signs otherwise unremarkable, regular rhythm", False),
    ("pleuritic chest pain", "sharp chest pain that's worse when he takes a deep breath, pleuritic", True),
    ("pleuritic chest pain", "dull, constant chest pressure, unaffected by breathing", False),
]


def test_adversarial_feature_matching_suite_meets_specificity_floor():
    true_positive_hits = 0
    true_positive_total = 0
    false_positive_hits = 0
    false_positive_total = 0
    failures = []
    for phrase, text, expected in ADVERSARIAL_PAIRS:
        result = feature_present(phrase, [text])
        if expected:
            true_positive_total += 1
            if result:
                true_positive_hits += 1
            else:
                failures.append(f"FALSE NEGATIVE: {text!r} should support {phrase!r}")
        else:
            false_positive_total += 1
            if not result:
                false_positive_hits += 1
            else:
                failures.append(f"FALSE POSITIVE: {text!r} should NOT support {phrase!r}")

    assert not failures, "\n".join(failures)

    true_positive_rate = true_positive_hits / true_positive_total
    specificity = false_positive_hits / false_positive_total  # true-negative rate
    false_positive_rate = 1.0 - specificity

    assert true_positive_rate == 1.0, f"true-positive rate {true_positive_rate} < 1.0"
    assert false_positive_rate == 0.0, f"false-positive rate {false_positive_rate} > 0.0"
    assert specificity == 1.0, f"specificity {specificity} < 1.0"


def test_distinguishing_tokens_strip_only_relational_words_never_the_whole_phrase_for_real_kb_content():
    # A real, specific KB phrase (multiple genuine clinical concepts, no relational filler) must
    # keep ALL of its content words as distinguishing -- the relational-word set must never
    # over-strip genuinely meaningful clinical vocabulary.
    content = _content_words("irregularly irregular rhythm")
    assert _distinguishing_tokens(content) == content


def test_audit_script_finds_no_new_unreviewed_risk_beyond_the_known_set():
    result = audit()
    flagged = {(d, k, p) for d, k, p in result["no_distinguishing_tokens"]} | \
              {(d, k, p) for d, k, p in result["thin_distinguishing_ratio"]}
    new_risks = flagged - KNOWN_REVIEWED_THIN_PHRASES
    assert not new_risks, f"new unreviewed feature-match specificity risk(s): {new_risks}"
