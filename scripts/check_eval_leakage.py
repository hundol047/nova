#!/usr/bin/env python3
"""Evaluation-leakage check (spec section 33): `python scripts/check_eval_leakage.py`

A best-effort STATIC scan for the most obvious ways a "blind" evaluation set could stop being
blind -- it cannot verify true semantic independence (that requires human judgment about whether a
phrase is a generic concept vs. a lifted sentence), only the mechanical/obvious forms of leakage:

  1. A blind case's case_id string appearing anywhere in nova_agent/ or competition/ (agent core).
  2. A blind case's exact chief_complaint sentence appearing verbatim in nova_agent/ (would mean
     the agent core hardcodes a specific vignette's wording).
  3. A long, distinctive substring shared between a blind case's chief_complaint and any alias
     phrase in chief_complaint.py or differential.py's FEATURE_ALIASES (a short/generic phrase
     like "chest pain" or "throwing up" will always coincidentally overlap somewhere and is not
     flagged -- only a long enough shared span to plausibly be a copy-paste).
  4. A blind case's ground_truth_diagnosis id appearing alongside its own case_id or chief_complaint
     text in agent core (a crude proxy for "answer hardcoded against this specific case").

Exit code 0 + "NO OBVIOUS LEAKAGE DETECTED" when nothing is flagged. Otherwise exit code 1 with the
specific findings -- a human should then judge whether each is a real problem (a generic phrase
that happens to overlap) or genuine leakage (a lifted sentence) before deciding what to do.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Every "blind" evaluation file this repo has ever authored -- each is meant to stay a one-shot
# honesty check, never a tuning target, so leakage from ANY of them into agent core is a problem,
# not just the most recent one.
BLIND_MODULES = ["evaluation.blind_cases_v3", "evaluation.blind_cases_v4", "evaluation.blind_cases_v5",
                  "evaluation.blind_cases_v6", "evaluation.blind_cases_v8"]

# Agent-core source the blind sets must never leak into. Deliberately excludes evaluation/ itself
# (a blind case file referencing its own sibling files, or scripts, is not leakage) and tests/
# (a routing/severity regression test citing a chief-complaint phrase is expected and reviewed by
# hand -- this scanner is about SILENT leakage into the agent's actual decision logic).
AGENT_CORE_DIRS = [ROOT / "nova_agent", ROOT / "competition", ROOT / "submission" / "nova_agent",
                    ROOT / "submission" / "competition"]

# A shared substring shorter than this is almost always a coincidental generic phrase ("chest
# pain", "throwing up", "no rash") rather than a copy-pasted sentence -- long enough to require a
# real multi-word match, short enough to still catch a lifted clause.
_MIN_LEAK_SUBSTRING_LEN = 24


def _load_blind_cases():
    cases = []
    for module_name in BLIND_MODULES:
        try:
            module = __import__(module_name, fromlist=["*"])
        except ImportError:
            continue
        for attr in dir(module):
            value = getattr(module, attr)
            if isinstance(value, list) and value and hasattr(value[0], "chief_complaint"):
                cases.extend(value)
    return cases


def _agent_core_text() -> List[tuple[Path, str]]:
    files = []
    for d in AGENT_CORE_DIRS:
        if not d.is_dir():
            continue
        for path in d.rglob("*.py"):
            try:
                files.append((path, path.read_text(encoding="utf-8", errors="ignore")))
            except Exception:
                continue
    return files


def _longest_common_substring_len(a: str, b: str) -> int:
    """Simple O(len(a)*len(b)) DP -- these strings are short (one sentence / one alias phrase
    each), so this never runs on anything large."""
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    best = 0
    for i in range(1, len(a) + 1):
        curr = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                curr[j] = prev[j - 1] + 1
                best = max(best, curr[j])
        prev = curr
    return best


def main() -> int:
    findings: List[str] = []

    blind_cases = _load_blind_cases()
    if not blind_cases:
        print("No blind case files found (evaluation/blind_cases_v3.py etc.) -- nothing to check.")
        return 0

    core_files = _agent_core_text()

    for case in blind_cases:
        case_id = case.case_id
        chief_complaint = (case.chief_complaint or "").lower()
        ground_truth = case.ground_truth_diagnosis

        for path, text in core_files:
            rel = path.relative_to(ROOT)
            lowered = text.lower()

            # 1. case_id leakage.
            if case_id.lower() in lowered:
                findings.append(f"{rel}: contains blind case_id {case_id!r} verbatim")

            # 2. Exact chief_complaint sentence leakage.
            if chief_complaint and len(chief_complaint) >= _MIN_LEAK_SUBSTRING_LEN and chief_complaint in lowered:
                findings.append(f"{rel}: contains blind case {case_id!r}'s exact chief_complaint text verbatim")

            # 4. ground_truth diagnosis id co-located with this case's own id/complaint (crude
            #    answer-hardcoding proxy) -- only flagged if BOTH appear near each other in the
            #    same file, not just because the diagnosis id exists (every real diagnosis id
            #    legitimately appears throughout nova_agent/knowledge/).
            if case_id.lower() in lowered and ground_truth.lower() in lowered:
                findings.append(f"{rel}: contains both blind case_id {case_id!r} and its "
                                 f"ground_truth_diagnosis {ground_truth!r} -- verify this isn't "
                                 "answer-specific hardcoding")

        # 3. Long shared substrings against chief_complaint.py's alias phrases and
        #    differential.py's FEATURE_ALIASES -- the two places a lifted sentence would most
        #    plausibly end up as a "generalized" alias.
        try:
            from nova_agent.chief_complaint import CONCEPT_PHRASES
            for tag, phrases in CONCEPT_PHRASES.items():
                for phrase in phrases:
                    shared = _longest_common_substring_len(chief_complaint, phrase.lower())
                    if shared >= _MIN_LEAK_SUBSTRING_LEN:
                        findings.append(
                            f"nova_agent/chief_complaint.py ({tag}): alias {phrase!r} shares a "
                            f"{shared}-character span with blind case {case_id!r}'s chief_complaint"
                        )
        except Exception as exc:
            findings.append(f"could not import nova_agent.chief_complaint for alias comparison: {exc}")

        try:
            from nova_agent.differential import FEATURE_ALIASES
            for canonical, aliases in FEATURE_ALIASES.items():
                for alias in aliases:
                    shared = _longest_common_substring_len(chief_complaint, alias.lower())
                    if shared >= _MIN_LEAK_SUBSTRING_LEN:
                        findings.append(
                            f"nova_agent/differential.py FEATURE_ALIASES[{canonical!r}]: {alias!r} "
                            f"shares a {shared}-character span with blind case {case_id!r}'s "
                            "chief_complaint"
                        )
        except Exception as exc:
            findings.append(f"could not import nova_agent.differential for alias comparison: {exc}")

    findings = sorted(set(findings))

    print(f"Checked {len(blind_cases)} blind case(s) across {len(BLIND_MODULES)} module(s) against "
          f"{len(core_files)} agent-core file(s).\n")
    if not findings:
        print("NO OBVIOUS LEAKAGE DETECTED")
        return 0

    print(f"{len(findings)} POTENTIAL LEAKAGE FINDING(S) -- review each by hand (a short generic "
          "phrase overlapping coincidentally is not leakage; a lifted sentence or hardcoded "
          "case-specific rule is):\n")
    for f in findings:
        print(f"  - {f}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
