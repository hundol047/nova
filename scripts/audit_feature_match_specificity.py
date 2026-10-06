"""`python scripts/audit_feature_match_specificity.py` -- systematic audit of every Tier-1 disease's
own `typical_features`, `risk_factors`, and `confirmatory_findings` phrases for GENERIC-WORD
FUZZY-MATCH FALSE-POSITIVE RISK (Round E's feature-match specificity hardening).

A multi-word KB phrase like "worse after meals" or "chest pain after trauma" is dominated by
low-information RELATIONAL/temporal/severity connector words ("after", "worse", "with", "during",
...) plus generic symptom-type nouns ("pain", "symptom", ...) -- matching.py's `_distinguishing_
tokens()` strips both, leaving only the phrase's real clinically-distinguishing concept(s) (e.g.
"meals", "trauma"). `feature_present()` now requires those distinguishing tokens to independently
clear the same presence rule the full phrase does (see matching.py's own docstring) -- this script
is the audit tool that FINDS which KB phrases were at risk before/without that gate, so a future
addition to the knowledge base can be checked the same way.

Flags two risk classes:
  - NO_DISTINGUISHING_TOKENS: every content word is relational/generic -- the gate cannot apply at
    all (falls back to legacy ratio-only behavior), so this phrase is genuinely at risk of a
    generic-word collision and should be reworded (add a real distinguishing word) or reviewed by
    hand.
  - THIN_DISTINGUISHING_RATIO: the phrase has some distinguishing content, but it's a small
    minority of the phrase's total words (e.g. 1 of 3+) -- exactly the shape that let generic words
    alone clear the 60% overlap-ratio threshold before this round's gate existed. Not necessarily
    unsafe NOW (the gate covers it), but worth a human's attention if the KB grows.

This is a permanent, reusable regression tool -- re-run after adding any new Tier-1 disease or
editing typical_features/risk_factors/confirmatory_findings text.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nova_agent.matching import _content_words, _distinguishing_tokens  # noqa: E402
from nova_agent.knowledge.retrieval import all_diseases  # noqa: E402

# Phrases this round's audit already reviewed and judged genuinely thin/no-distinguishing-token,
# each closed by matching.py's new distinguishing-token gate (not reworded, since the phrase text
# itself is legitimate clinical language -- the FIX lives in the matching architecture, not the KB).
# Kept here so a NEW phrase added later with the same risk shape is flagged as new, not silently
# lumped in with an already-reviewed one.
KNOWN_REVIEWED_THIN_PHRASES = {
    ("gerd", "typical_features", "worse after meals"),
    # Surfaced only after Round E removed matching.py's truncation fallback (previously "episode"
    # incorrectly stemmed to "episod", a mismatch against the relational-word set's exact "episode"
    # entry, so the distinguishing-token gate never saw this phrase as thin at all) -- reviewed and
    # confirmed correctly protected: requires "palpitations" itself to be present, correctly
    # rejecting text that only shares "before"/"the episode" without palpitations ever mentioned.
    ("orthostatic_hypotension", "typical_features", "no palpitations before the episode"),
    ("vasovagal_syncope", "typical_features", "no palpitations before the episode"),
}


def audit() -> dict:
    no_distinguishing = []
    thin_ratio = []
    for disease_id, entry in sorted(all_diseases().items()):
        for key in ("typical_features", "risk_factors", "confirmatory_findings"):
            for phrase in entry.get(key, []):
                content = _content_words(phrase)
                distinguishing = _distinguishing_tokens(content)
                if not content:
                    continue
                if not distinguishing:
                    no_distinguishing.append((disease_id, key, phrase))
                elif len(distinguishing) == 1 and len(content) >= 3:
                    thin_ratio.append((disease_id, key, phrase))
    return {"no_distinguishing_tokens": no_distinguishing, "thin_distinguishing_ratio": thin_ratio}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--known-reviewed-only", action="store_true",
                         help="Regression-check mode: fail if a NEW (not previously reviewed) risky "
                              "phrase appears -- e.g. after a KB edit.")
    parser.add_argument("--json", action="store_true", help="Machine-readable output.")
    args = parser.parse_args()

    result = audit()
    all_flagged = {(d, k, p) for d, k, p in result["no_distinguishing_tokens"]} | \
                  {(d, k, p) for d, k, p in result["thin_distinguishing_ratio"]}

    if args.known_reviewed_only:
        new_risks = all_flagged - KNOWN_REVIEWED_THIN_PHRASES
        if args.json:
            print(json.dumps({"new_risks": sorted(new_risks)}))
        elif new_risks:
            print("NEW feature-match specificity risk(s) found (not previously reviewed):")
            for d, k, p in sorted(new_risks):
                print(f"  {d:30s} {k:22s} {p!r}")
            raise SystemExit(1)
        else:
            print(f"OK: no new feature-match specificity risks beyond the "
                  f"{len(KNOWN_REVIEWED_THIN_PHRASES)} already-reviewed phrase(s).")
        return

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print(f"=== Feature-match specificity audit: {len(all_diseases())} Tier-1 diseases ===\n")
    print(f"{len(result['no_distinguishing_tokens'])} phrase(s) with NO distinguishing tokens "
          "(gate cannot apply -- legacy ratio-only behavior, review by hand):")
    for d, k, p in result["no_distinguishing_tokens"]:
        reviewed = " [reviewed]" if (d, k, p) in KNOWN_REVIEWED_THIN_PHRASES else " [NEW]"
        print(f"  {d:30s} {k:22s} {p!r}{reviewed}")
    print(f"\n{len(result['thin_distinguishing_ratio'])} phrase(s) with a THIN distinguishing "
          "ratio (covered by the new gate, worth periodic review):")
    for d, k, p in result["thin_distinguishing_ratio"]:
        reviewed = " [reviewed]" if (d, k, p) in KNOWN_REVIEWED_THIN_PHRASES else " [NEW]"
        print(f"  {d:30s} {k:22s} {p!r}{reviewed}")


if __name__ == "__main__":
    main()
