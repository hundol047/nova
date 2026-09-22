# Knowledge base provenance

Honest statement of where `nova_agent/knowledge/`'s content comes from (spec section 11), written
because the alternative -- inventing citations that were never actually checked -- would be worse
than no citation at all.

## What this is

Every entry in `diseases/*.json`, `red_flags/*.json`, `diagnostic_tests/notes.json`, and
`guidelines/chief_complaint_guidelines.json` is an **internally authored clinical heuristic**,
written by the implementer from general medical knowledge (standard differential-diagnosis
teaching: typical presenting features, common risk factors, first-line discriminating workup for
each condition). None of it was copied or algorithmically derived from a specific named guideline
document, textbook, or clinical decision-support database, and none of it has been reviewed by a
licensed clinician as part of this implementation.

**This is explicitly the same status SynexAgent (the vendored medical decision-support backend
this repo also contains) already gives its own rule tables** -- see
`backend/app/services/rule_engine.py`'s `EVIDENCE_LEVEL = 'PROTOTYPE RULE — NOT CLINICALLY
VALIDATED'` and its accompanying comment that its interaction rules are "SynexAgent internal
prototype policy... not an official drug database, formulary, or clinical guideline." The Doctor
Agent's knowledge base carries the identical caveat for the identical reason: it is a working
prototype's clinical judgment encoded as data, not a certified source.

## What this is not

- Not sourced from UpToDate, DynaMed, a specific national/society clinical practice guideline, a
  peer-reviewed diagnostic-accuracy study, or any other citable external reference. No such
  citation is claimed anywhere in the JSON files, deliberately -- adding a fabricated "source" URL
  or document name to make an entry look more authoritative than it is would be actively
  misleading, and none has been added.
- Not clinically validated against real patient outcomes or reviewed by a licensed physician.
- Not exhaustive: 34 diagnoses across 15 chief-complaint categories is a deliberately small,
  can't-miss-condition-weighted set (spec section 12's KB = high-frequency + can't-miss diseases /
  LLM = long-tail differential generation design), not a claim of comprehensive coverage.

## Per-entry fields

Each disease entry's `typical_features`, `risk_factors`, `discriminating_questions/exams/tests`,
`confirmatory_findings`, `minimum_workup`, and `red_flag_keywords` are the implementer's summary of
standard teaching for that condition, structured for keyword-based matching (see
`nova_agent/matching.py`) -- not a verbatim quotation of any single source. `urgency` and
`dangerous` follow conventional triage judgment (e.g. the 14 time-critical "can't-miss" diagnoses
named in the original task spec) rather than a formal acuity scoring system.

## If official guidance becomes available

If the N.O.V.A. 2026 competition rules specify a required knowledge source, an approved reference
set, or a licensing constraint, that takes precedence over everything in this file and in
`knowledge/*.json` -- update the affected entries (and this file) to cite it accurately rather than
leaving this internally-authored-heuristic framing in place once a real source is confirmed.
