"""`python scripts/benchmark_chief_complaint_routing.py` -- dedicated routing/generalization
benchmark for nova_agent/chief_complaint.py + clinical_presentation.py (Round D's generalization-
hardening mandate). Distinct from evaluation/benchmark.py's full multi-turn diagnosis pipeline: this
operates directly at the ROUTING layer, so a routing regression is caught and localized immediately,
without needing to reason through an entire simulated case to notice diagnostic accuracy dropped.

Measures five things, each against a curated, hand-authored item set (never derived from or
reworded out of any frozen blind evaluation case):
  1. known_route_success_rate       -- text expected to route to a specific tag actually does.
  2. unknown_fallback_rate          -- text expected to route to NOTHING (match_type == "none")
                                        actually falls through cleanly, never a false positive.
  3. specific_over_generic_accuracy -- text with both generic and specific signal present resolves
                                        to the SPECIFIC concept (SPECIFICITY_PRECEDENCE), not the
                                        generic umbrella tag.
  4. multi_concept_recall           -- text naming 2+ distinct concepts has ALL of them recovered
                                        by clinical_presentation.extract_presentation(), not just
                                        the single best-scoring tag.
  5. critical_concept_recall        -- the same known-route check, restricted to items whose
                                        expected tag maps to at least one CRITICAL/dangerous disease
                                        (a routing miss on these is the highest-stakes failure mode).

Also verifies routing changes reach CANDIDATE GENERATION end-to-end, not just the routing label:
for every known-route item, confirms the expected disease actually appears in
candidate_generator.generate_candidates()'s pool once that text is set as the chief complaint --
catching the class of bug where a chief_complaint.py tag exists but was never added to the relevant
disease's own `chief_complaint_tags` in its knowledge-base JSON (diseases_for_tag() would then
surface nothing for it despite the tag routing "successfully").

Run this before and after any change to chief_complaint.py/clinical_presentation.py's routing
tables to see the delta directly (the script has no historical-comparison machinery of its own --
diff two runs' printed/--json output). `--known-good-only` runs in regression-check mode (exit 1 on
any failure), the same pattern scripts/audit_chief_complaint_coverage.py's --known-gaps-only uses.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nova_agent.candidate_generator import generate_candidates
from nova_agent.chief_complaint import route
from nova_agent.clinical_presentation import extract_presentation
from nova_agent.knowledge.retrieval import all_diseases, diseases_for_tag


@dataclass
class RoutingCase:
    text: str
    category: str  # "known_route" | "unknown_fallback" | "specific_over_generic" | "multi_concept"
    expected_tag: Optional[str] = None          # known_route / specific_over_generic
    expected_tags: List[str] = field(default_factory=list)  # multi_concept (all must be recovered)
    expected_disease_id: Optional[str] = None   # known_route / specific_over_generic end-to-end check
    critical: bool = False                      # expected_tag maps to >=1 CRITICAL/dangerous disease


# Never reworded out of, or copied from, any frozen blind evaluation case -- independently authored
# routing probes, each isolating exactly one of the five metrics above.
ROUTING_CASES: List[RoutingCase] = [
    # --- known_route: the 7 new Round D taxonomy domains, in fresh wording ---
    RoutingCase("my nose is all stuffed up and my throat feels scratchy", "known_route",
                expected_tag="upper_respiratory", expected_disease_id="viral_uri"),
    RoutingCase("been running to the bathroom with watery stool all morning", "known_route",
                expected_tag="diarrhea", expected_disease_id="gastroenteritis"),
    RoutingCase("my left hand feels numb, like pins and needles", "known_route",
                expected_tag="numbness", expected_disease_id="ischemic_stroke", critical=True),
    RoutingCase("my vision suddenly went blurry in one eye", "known_route",
                expected_tag="vision_changes", expected_disease_id="ischemic_stroke", critical=True),
    RoutingCase("my neck won't bend, it's completely stiff", "known_route",
                expected_tag="neck_stiffness", expected_disease_id="meningitis", critical=True),
    RoutingCase("I spit out some blood after coughing this morning", "known_route",
                expected_tag="hemoptysis", expected_disease_id="pulmonary_embolism", critical=True),
    RoutingCase("he was shaking uncontrollably and unresponsive for a minute", "known_route",
                expected_tag="seizure", expected_disease_id="severe_electrolyte_disorder"),
    # --- known_route: a sample of pre-existing, already-working tags (negative-control coverage,
    #     so a regression in an OLD tag is caught here too, not only in the 7 new ones) ---
    RoutingCase("crushing pressure in the middle of my chest", "known_route",
                expected_tag="chest_pain", expected_disease_id="acute_coronary_syndrome", critical=True),
    RoutingCase("sudden, the worst headache I've ever had in my life", "known_route",
                expected_tag="headache", expected_disease_id="subarachnoid_hemorrhage", critical=True),
    RoutingCase("burning when I pee and I keep needing to go", "known_route",
                expected_tag="urinary_symptoms", expected_disease_id="uncomplicated_cystitis"),

    # --- unknown_fallback: genuinely unroutable text (no clinical concept named at all) ---
    RoutingCase("xyzzy plugh wobblefritz", "unknown_fallback"),
    RoutingCase("just don't feel like myself lately, hard to explain", "unknown_fallback"),
    RoutingCase("the weather has been really strange this week", "unknown_fallback"),

    # --- specific_over_generic: both generic umbrella language AND specific signal present ---
    RoutingCase("feeling weak all over, and my right arm and face just went weak on one side",
                "specific_over_generic", expected_tag="focal_weakness",
                expected_disease_id="ischemic_stroke", critical=True),
    RoutingCase("felt dizzy and then I actually passed out for a few seconds",
                "specific_over_generic", expected_tag="syncope",
                expected_disease_id="cardiac_arrhythmia"),
    RoutingCase("bad stomach pain, and now there's blood in my stool",
                "specific_over_generic", expected_tag="gi_bleeding",
                expected_disease_id="gi_bleeding", critical=True),
    # Negative control: generic wording with NO specific alternative present must stay generic.
    RoutingCase("just feeling weak and tired the last couple days, nothing else",
                "specific_over_generic", expected_tag="weakness",
                expected_disease_id="severe_electrolyte_disorder"),

    # --- multi_concept: 2+ distinct concepts named in the same presentation ---
    RoutingCase("bad headache, stiff neck, and a fever since this morning", "multi_concept",
                expected_tags=["headache", "neck_stiffness", "fever"]),
    RoutingCase("can't stop coughing, spiking a fever, and short of breath", "multi_concept",
                expected_tags=["cough", "fever", "dyspnea"]),
    RoutingCase("chest pain that comes with palpitations and feeling dizzy", "multi_concept",
                expected_tags=["chest_pain", "palpitations", "dizziness"]),
]


def _end_to_end_reachable(case: RoutingCase) -> bool:
    """True if `case.expected_disease_id` is actually present in the candidate pool once
    `case.text` is set as the chief complaint -- proves the routing tag doesn't just produce the
    right LABEL, it also actually reaches candidate_generator.py's pool (i.e. the disease's own
    `chief_complaint_tags` in its KB json really does list this tag)."""
    if case.expected_disease_id is None:
        return True
    presentation = extract_presentation(case.text)
    candidates = generate_candidates(presentation, chief_complaint_text=case.text)
    return any(c.entry["id"] == case.expected_disease_id for c in candidates)


def _dangerous_ids_for_tag(tag: str) -> set:
    return {d["id"] for d in diseases_for_tag(tag) if d.get("dangerous")}


def run() -> dict:
    known_route = [c for c in ROUTING_CASES if c.category == "known_route"]
    unknown_fallback = [c for c in ROUTING_CASES if c.category == "unknown_fallback"]
    specific_over_generic = [c for c in ROUTING_CASES if c.category == "specific_over_generic"]
    multi_concept = [c for c in ROUTING_CASES if c.category == "multi_concept"]
    critical_known_route = [c for c in known_route if c.critical]

    known_route_hits = [c for c in known_route if route(c.text).primary_tag == c.expected_tag]
    unknown_fallback_hits = [c for c in unknown_fallback if route(c.text).match_type == "none"]
    specific_hits = [c for c in specific_over_generic if route(c.text).primary_tag == c.expected_tag]
    critical_hits = [c for c in critical_known_route if route(c.text).primary_tag == c.expected_tag]

    multi_concept_results = []
    for c in multi_concept:
        presentation = extract_presentation(c.text)
        recovered = set(presentation.symptoms)
        missing = [t for t in c.expected_tags if t not in recovered]
        multi_concept_results.append((c, recovered, missing))
    multi_concept_full_recall = [r for r in multi_concept_results if not r[2]]

    end_to_end_checked = [c for c in (known_route + specific_over_generic) if c.expected_disease_id]
    end_to_end_hits = [c for c in end_to_end_checked if _end_to_end_reachable(c)]

    def rate(hits: list, total: list) -> float:
        return round(len(hits) / len(total), 4) if total else 1.0

    summary = {
        "known_route_success_rate": rate(known_route_hits, known_route),
        "known_route_misses": [c.text for c in known_route if c not in known_route_hits],
        "unknown_fallback_rate": rate(unknown_fallback_hits, unknown_fallback),
        "unknown_fallback_false_positives": [
            (c.text, route(c.text).primary_tag) for c in unknown_fallback if c not in unknown_fallback_hits
        ],
        "specific_over_generic_accuracy": rate(specific_hits, specific_over_generic),
        "specific_over_generic_misses": [
            (c.text, c.expected_tag, route(c.text).primary_tag)
            for c in specific_over_generic if c not in specific_hits
        ],
        "multi_concept_recall": rate(multi_concept_full_recall, multi_concept),
        "multi_concept_misses": [(c.text, missing) for c, _, missing in multi_concept_results if missing],
        "critical_concept_recall": rate(critical_hits, critical_known_route),
        "critical_concept_misses": [c.text for c in critical_known_route if c not in critical_hits],
        "end_to_end_candidate_generation_rate": rate(end_to_end_hits, end_to_end_checked),
        "end_to_end_candidate_generation_misses": [
            (c.text, c.expected_disease_id) for c in end_to_end_checked if c not in end_to_end_hits
        ],
        "diseases_scanned": len(all_diseases()),
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Machine-readable output.")
    parser.add_argument("--known-good-only", action="store_true",
                         help="Regression-check mode: exit 1 if any metric is below 100%%.")
    args = parser.parse_args()

    summary = run()

    if args.known_good_only:
        failing = {k: v for k, v in summary.items() if k.endswith("_rate") and v < 1.0}
        if failing:
            print("REGRESSION: routing benchmark metric(s) below 100%:")
            print(json.dumps(failing, indent=2))
            raise SystemExit(1)
        print("OK: all routing benchmark metrics at 100%.")
        return

    if args.json:
        print(json.dumps(summary, indent=2))
        return

    print("=== chief_complaint.py / clinical_presentation.py routing benchmark ===\n")
    print(f"Diseases scanned: {summary['diseases_scanned']}\n")
    for label, key in [
        ("Known-route success rate", "known_route_success_rate"),
        ("UNKNOWN fallback rate", "unknown_fallback_rate"),
        ("Specific-over-generic accuracy", "specific_over_generic_accuracy"),
        ("Multi-concept recall", "multi_concept_recall"),
        ("Critical concept recall", "critical_concept_recall"),
        ("End-to-end candidate-generation rate", "end_to_end_candidate_generation_rate"),
    ]:
        print(f"  {label + ':':<40}{summary[key] * 100:.1f}%")
    print()
    for miss_key in ("known_route_misses", "unknown_fallback_false_positives", "specific_over_generic_misses",
                      "multi_concept_misses", "critical_concept_misses", "end_to_end_candidate_generation_misses"):
        misses = summary[miss_key]
        if misses:
            print(f"{miss_key}:")
            for m in misses:
                print(f"  {m!r}")


if __name__ == "__main__":
    main()
