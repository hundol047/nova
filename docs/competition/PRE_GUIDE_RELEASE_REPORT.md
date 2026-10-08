# N.O.V.A. 2026 PRE-GUIDE RELEASE REPORT

> **Historical report** for the runtime it names (v16-era). Its test counts, benchmark values and SHAs describe that commit only. Current status: [`../CURRENT_STATUS.md`](../CURRENT_STATUS.md).

REMOTE HEAD audited: `7c2c59773cdff71a8fde33e61dfa346f3110e076`
CURRENT RUNTIME SHA: `920eb608337fd035746be17cd87f12eb93bbe604`

STATUS: **NOT READY**. LOCAL_PRE_GUIDE_VERIFIED / EXTERNAL_OFFICIAL_INTERFACE_BLOCKED.

## Four requested tasks

1. Field-level provenance triage and reproducible replacement candidates prepared. No legacy rights cleared or clinical replacement promoted without review.
2. Retrieval experiments and every metric delta retained, including rejected variants and remaining losses.
3. Question coverage and action-efficiency experiments evaluated against unchanged cases and safety tests.
4. Professor packet covers all 34 core profiles, 29 with lexical source leads; all approval fields pending.

637 previously integrated licensed references remain. Five test-purpose excerpts are review candidates, not substitutes for diagnostic indications/safety caveats.
Tier-2: 1,246 total; 83 have features; 1,163 do not; 27 have confirmatory fields; no clinician review claimed.

## ROUND M — synthetic development / mock LLM

128 cases; 123 scored; 43 marked critical; five OOD/unscored. Labels and denominators unchanged.
Critical recall uses the existing 43 marked cases; it is not a clinical safety certification.
Retrieval is measured at the final decision turn; core scoring may bypass ontology retrieval.
Pure KO/JA sample sizes are tiny; follow-up text may be English. No broad multilingual claim.

| Metric | Before (v14) | Current | Delta |
|---|---:|---:|---:|
| MRR | 0.9735772357723578 | 0.9735772357723578 | 0.0 |
| Top1 | 0.959349593495935 | 0.959349593495935 | 0.0 |
| Top10 | 0.991869918699187 | 0.991869918699187 | 0.0 |
| Top3 | 0.983739837398374 | 0.983739837398374 | 0.0 |
| Top5 | 0.991869918699187 | 0.991869918699187 | 0.0 |
| accuracy | 0.959349593495935 | 0.959349593495935 | 0.0 |
| action_selection_error_rate | 0.0 | 0.0 | 0.0 |
| active_truth_retention | 0.991869918699187 | 0.991869918699187 | 0.0 |
| average_ask | 9.90625 | 8.65625 | -1.25 |
| average_diagnostic_delay | 0 | 0 | 0 |
| average_exam | 6 | 6 | 0 |
| average_tests | 8.9921875 | 9.0234375 | 0.03125 |
| average_turns | 25.8984375 | 24.6796875 | -1.21875 |
| average_unresolved_critical_alternatives | 11.390625 | 11.359375 | -0.03125 |
| cases | 128 | 128 | 0 |
| critical_Top1 | 1.0 | 1.0 | 0.0 |
| critical_Top3 | 1.0 | 1.0 | 0.0 |
| critical_Top5 | 1.0 | 1.0 | 0.0 |
| critical_candidate_retention | 1.0 | 1.0 | 0.0 |
| critical_count | 43 | 43 | 0 |
| critical_miss | 0.0 | 0.0 | 0.0 |
| critical_recall | 1.0 | 1.0 | 0.0 |
| diagnostic_delay_observed_count | 124 | 125 | 1 |
| final_ranking_error_rate | 0.032520325203252036 | 0.032520325203252036 | 0.0 |
| median_true_rank | 1.0 | 1.0 | 0.0 |
| median_turns | 20.5 | 19.0 | -1.5 |
| missing_rank_count | 1 | 1 | 0 |
| redundant_tests | 0 | 0 | 0 |
| rerank_at25 | 0.7235772357723578 | 0.7235772357723578 | 0.0 |
| rerank_truth_retention | 0.7317073170731707 | 0.7317073170731707 | 0.0 |
| retrieval_at150 | 0.8455284552845529 | 0.8455284552845529 | 0.0 |
| retrieval_truth_retention | 0.8455284552845529 | 0.8455284552845529 | 0.0 |
| scored_cases | 123 | 123 | 0 |

Rates above are fractions, not percentages. Long-tail and language detail:

```json
{
  "long_tail": {
    "count": 26,
    "retrieved": 1.0,
    "rerank_top25": 0.9615384615384616,
    "active": 1.0,
    "Top5": 1.0,
    "Top1": 0.9230769230769231,
    "interpretation": "Round M category-defined symptom-only development probes, no independent medical adjudication",
    "Top10": 1.0,
    "retrieval_at150": 1.0,
    "rerank_at25": 0.9615384615384616
  },
  "languages": {
    "EN": {
      "count": 113,
      "correct": 108,
      "accuracy": 0.9557522123893806
    },
    "KO": {
      "count": 1,
      "correct": 1,
      "accuracy": 1.0
    },
    "JA": {
      "count": 2,
      "correct": 2,
      "accuracy": 1.0
    },
    "Mixed": {
      "count": 7,
      "correct": 7,
      "accuracy": 1.0
    }
  }
}
```

OOD observations (forced DIAGNOSE is not a supported-diagnosis claim):

```json
[
  {
    "case_id": "RoundM_124",
    "final": "Acute Abdomen (Surgical Abdomen)",
    "turns": 44,
    "tests": 19,
    "asks": 12,
    "exams": 12
  },
  {
    "case_id": "RoundM_125",
    "final": "Acute Abdomen (Surgical Abdomen)",
    "turns": 44,
    "tests": 19,
    "asks": 12,
    "exams": 12
  },
  {
    "case_id": "RoundM_126",
    "final": "Gastrointestinal Bleeding",
    "turns": 36,
    "tests": 16,
    "asks": 10,
    "exams": 9
  },
  {
    "case_id": "RoundM_127",
    "final": "Migraine",
    "turns": 40,
    "tests": 18,
    "asks": 10,
    "exams": 11
  },
  {
    "case_id": "RoundM_128",
    "final": "Acute Abdomen (Surgical Abdomen)",
    "turns": 44,
    "tests": 19,
    "asks": 12,
    "exams": 12
  }
]
```

Every wrong scored case has ordered earliest-stage failure attribution in `artifacts/clinical_review_pass/failure_analysis.json`.
This heuristic attribution is not clinician causal adjudication. Diagnostic delay is a policy proxy; missing observations are not zero delay.

## REGRESSION

Tests passed: 1028; failed: 0; skipped: 1. FULL CURRENT SUITE.
Skip reasons: [{"test": "sha256.8cb56e51e8fc3aa67968326c96381d9851697704c949c89e1468d550ebd1ae24", "reason": "See retained original report; details withheld from public summary"}]

| Suite | Scored accuracy | Critical recall | Mean tests | Mean turns |
|---|---:|---:|---:|---:|
| held_out | 1.0 | 1.0 | 9.222222222222221 | 28.166666666666668 |
| generalization_v2 | 1.0 | 1.0 | 7.277777777777778 | 20.5 |
| stress | 1.0 | 1.0 | 9.625 | 25.125 |
| round_d | 1.0 | 1.0 | 13.428571428571429 | 33.285714285714285 |
| round_e | 1.0 | 1.0 | 11.714285714285714 | 30.714285714285715 |
| round_g | 1.0 | 1.0 | 9.166666666666666 | 23.416666666666668 |
| round_i | 0.9473684210526315 | 1.0 | 6.95 | 18.75 |
| round_j | 0.9230769230769231 | 1.0 | 8.11111111111111 | 23.555555555555557 |

All per-case changes, including increases in test count or turns, are retained in `artifacts/clinical_review_pass/performance_comparison.json`.

## BLIND STATUS

v18: REFERENCE-ONLY. v19: NOT EXECUTED; PREEXECUTION INVALIDATED / REFERENCE-ONLY.
Fresh final blind: NOT YET AUTHORED. No v19 execution or v20 creation.

## COMPLIANCE

```json
{
  "Fixed model configured": "PASS",
  "Fixed revision configured": "PASS",
  "Fine-tuning absent": "PASS",
  "60-turn hard cap": "PASS",
  "Official 4 actions only": "PASS",
  "Case-related LLM success gate": "BLOCKED — organizer receipt semantics/transport not provided; development JSON validity is separate",
  "Competition provider lock": "PASS",
  "No online private-case learning": "PASS",
  "Case isolation": "PASS",
  "Static retrieval": "PASS",
  "Secret scan": "PASS",
  "Source documentation": "BLOCKED — new reference sources verified; legacy clinical origins unresolved",
  "License documentation": "BLOCKED — new reference terms documented; legacy rights unresolved",
  "LLM-generation log": "FAIL — log exists, historical exact model/prompt records unresolved"
}
```

Machine-readable rule matrix distinguishes PASS, BLOCKED and NOT_VERIFIED. Application-level fail-closed policy tested; OS network isolation not proven.

## OFFICIAL INTERFACE

Participant guide: not available to this audit. Official API: NOT VERIFIED. Schema: PLACEHOLDER.
Real organizer gpt-oss call: NOT VERIFIED. No guessed transport or official readiness claim.

## VERIFICATION

Version: v15; runtime SHA: `920eb608337fd035746be17cd87f12eb93bbe604`.
Submission ZIP: `artifacts/verification/nova-pre-guide-v15.zip`; bytes: 669434; SHA256: `607f58aedd599808346619a0d039a17cc778392b4a83fbde2f09a4fc6edbd661`.
Source/submission byte equivalence: PASS. Secret scan: PASS (heuristic scan limitations retained). UTF-8/Python, run.py and requirements.txt present; below 50 MB.
No evaluation data, tests, frontend/backend, training artifacts or model weights in candidate ZIP.

## BLOCKERS

1. Original clinical authorship/rights and historical AI-generation receipts remain unresolved for legacy assets.
2. Clinical review of rules and candidate replacements remains pending.
3. Official participant guide, exact schema/transport and real fixed-model validation are unavailable to this pass.
4. Development retrieval/rerank targets and independent clinical validation remain unmet.
