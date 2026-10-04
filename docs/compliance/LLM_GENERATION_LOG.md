# LLM generation log

Historical generation records are incomplete. The exact tool/model, original prompt and source
material are UNRESOLVED unless explicitly stated below. A commit timestamp is not a generation
receipt. This log records gaps; it does not reconstruct invented provenance.

Machine-readable inventory: `artifacts/round_m/generation_inventory.json`.

| Output | Tool/model | Date | Prompt/instruction | Source material | Manual review |
|---|---|---|---|---|---|
| `nova_agent/knowledge/diagnostic_tests/notes.json` | UNRESOLVED: historical engineering-agent attribution is not an exact model/version | 2026-09-21T14:17:14Z | UNRESOLVED: original verbatim generation prompt not present | General knowledge claimed; no auditable medical source supplied | UNREVIEWED / no documented clinician signoff |
| `nova_agent/knowledge/diseases/abdominal_gi.json` | UNRESOLVED: historical engineering-agent attribution is not an exact model/version | 2026-10-04T13:26:41Z | UNRESOLVED: original verbatim generation prompt not present | General knowledge claimed; no auditable medical source supplied | UNREVIEWED / no documented clinician signoff |
| `nova_agent/knowledge/diseases/cardiac.json` | UNRESOLVED: historical engineering-agent attribution is not an exact model/version | 2026-10-04T13:26:41Z | UNRESOLVED: original verbatim generation prompt not present | General knowledge claimed; no auditable medical source supplied | UNREVIEWED / no documented clinician signoff |
| `nova_agent/knowledge/diseases/endocrine_metabolic.json` | UNRESOLVED: historical engineering-agent attribution is not an exact model/version | 2026-09-28T17:25:35Z | UNRESOLVED: original verbatim generation prompt not present | General knowledge claimed; no auditable medical source supplied | UNREVIEWED / no documented clinician signoff |
| `nova_agent/knowledge/diseases/genitourinary.json` | UNRESOLVED: historical engineering-agent attribution is not an exact model/version | 2026-10-04T13:26:41Z | UNRESOLVED: original verbatim generation prompt not present | General knowledge claimed; no auditable medical source supplied | UNREVIEWED / no documented clinician signoff |
| `nova_agent/knowledge/diseases/infectious.json` | UNRESOLVED: historical engineering-agent attribution is not an exact model/version | 2026-10-04T13:26:41Z | UNRESOLVED: original verbatim generation prompt not present | General knowledge claimed; no auditable medical source supplied | UNREVIEWED / no documented clinician signoff |
| `nova_agent/knowledge/diseases/neuro.json` | UNRESOLVED: historical engineering-agent attribution is not an exact model/version | 2026-10-04T13:26:41Z | UNRESOLVED: original verbatim generation prompt not present | General knowledge claimed; no auditable medical source supplied | UNREVIEWED / no documented clinician signoff |
| `nova_agent/knowledge/diseases/pulmonary.json` | UNRESOLVED: historical engineering-agent attribution is not an exact model/version | 2026-10-04T13:26:41Z | UNRESOLVED: original verbatim generation prompt not present | General knowledge claimed; no auditable medical source supplied | UNREVIEWED / no documented clinician signoff |
| `nova_agent/knowledge/guidelines/chief_complaint_guidelines.json` | UNRESOLVED: historical engineering-agent attribution is not an exact model/version | 2026-09-21T14:17:14Z | UNRESOLVED: original verbatim generation prompt not present | General knowledge claimed; no auditable medical source supplied | UNREVIEWED / no documented clinician signoff |
| `nova_agent/knowledge/red_flags/critical_conditions.json` | UNRESOLVED: historical engineering-agent attribution is not an exact model/version | 2026-09-28T08:03:53Z | UNRESOLVED: original verbatim generation prompt not present | General knowledge claimed; no auditable medical source supplied | UNREVIEWED / no documented clinician signoff |
| `nova_agent/knowledge/red_flags/demographic_and_medication_risk.json` | UNRESOLVED: historical engineering-agent attribution is not an exact model/version | 2026-09-22T07:19:54Z | UNRESOLVED: original verbatim generation prompt not present | General knowledge claimed; no auditable medical source supplied | UNREVIEWED / no documented clinician signoff |
| `nova_agent/knowledge/tier2_catalog.json` | UNRESOLVED: historical engineering-agent attribution is not an exact model/version | 2026-09-25T08:53:53Z | UNRESOLVED: original verbatim generation prompt not present | General knowledge claimed; no auditable medical source supplied | UNREVIEWED / no documented clinician signoff |
| `nova_agent/knowledge/tier2_enrichment.json` | UNRESOLVED: historical engineering-agent attribution is not an exact model/version | 2026-10-04T15:36:35Z | UNRESOLVED: original verbatim generation prompt not present | General knowledge claimed; no auditable medical source supplied | UNREVIEWED / no documented clinician signoff |
| `nova_agent/lay_language.py` | UNRESOLVED: historical engineering-agent attribution is not an exact model/version | 2026-10-04T16:57:36Z | UNRESOLVED: original verbatim generation prompt not present | General knowledge claimed; no auditable medical source supplied | UNREVIEWED / no documented clinician signoff |
| `evaluation/cases.py` | UNRESOLVED | UNRESOLVED | UNRESOLVED; scripts/ and case source retain construction code, not original chat prompt | Synthetic development hypotheses, not patient evidence | Not independently clinician-adjudicated |
| `evaluation/generalization_cases_v2.py` | UNRESOLVED | UNRESOLVED | UNRESOLVED; scripts/ and case source retain construction code, not original chat prompt | Synthetic development hypotheses, not patient evidence | Not independently clinician-adjudicated |
| `evaluation/generalization_dev_cases_round_d.py` | UNRESOLVED | UNRESOLVED | UNRESOLVED; scripts/ and case source retain construction code, not original chat prompt | Synthetic development hypotheses, not patient evidence | Not independently clinician-adjudicated |
| `evaluation/generalization_dev_cases_round_e.py` | UNRESOLVED | UNRESOLVED | UNRESOLVED; scripts/ and case source retain construction code, not original chat prompt | Synthetic development hypotheses, not patient evidence | Not independently clinician-adjudicated |
| `evaluation/generalization_dev_cases_round_g.py` | UNRESOLVED | UNRESOLVED | UNRESOLVED; scripts/ and case source retain construction code, not original chat prompt | Synthetic development hypotheses, not patient evidence | Not independently clinician-adjudicated |
| `evaluation/generalization_dev_cases_round_i.py` | UNRESOLVED | UNRESOLVED | UNRESOLVED; scripts/ and case source retain construction code, not original chat prompt | Synthetic development hypotheses, not patient evidence | Not independently clinician-adjudicated |
| `evaluation/generalization_dev_cases_round_j.py` | UNRESOLVED | UNRESOLVED | UNRESOLVED; scripts/ and case source retain construction code, not original chat prompt | Synthetic development hypotheses, not patient evidence | Not independently clinician-adjudicated |
| `evaluation/generalization_dev_cases_round_m.py` | UNRESOLVED | UNRESOLVED | UNRESOLVED; scripts/ and case source retain construction code, not original chat prompt | Synthetic development hypotheses, not patient evidence | Not independently clinician-adjudicated |
| `evaluation/generalization_stress_cases.py` | UNRESOLVED | UNRESOLVED | UNRESOLVED; scripts/ and case source retain construction code, not original chat prompt | Synthetic development hypotheses, not patient evidence | Not independently clinician-adjudicated |
| `evaluation/held_out_cases.py` | UNRESOLVED | UNRESOLVED | UNRESOLVED; scripts/ and case source retain construction code, not original chat prompt | Synthetic development hypotheses, not patient evidence | Not independently clinician-adjudicated |

## This pass

Tool: ChatGPT Work / Codex coding assistant; exact underlying model build is not exposed, so no
model version is claimed. Date: 2026-10-05 KST. Instruction: user-supplied current-state recovery,
Round M validation, competition compliance, pre-guide release hardening; preserve v19 unused,
no v20, no guessed organizer API, local regression, commit/push. Output: boundary code/tests,
provenance inventories, evaluation summaries and release documentation. Source: current repository,
public rules/evaluation/FAQ. General code corrections: comma-bounded negation scope and whole-word alias matching. No new clinical facts, development labels or private evaluation labels
were generated in this pass. Code reviewed through local tests; no clinician review claimed.

## Compliance repair follow-up

The historical inventory now includes `nova_agent/multilingual_concepts.py`, previously
omitted by the generation-audit script. Original tool/model/prompt and clinical/translation
review remain UNRESOLVED; its last commit date is not a generation timestamp.

Execution date: 2026-10-04 UTC (2026-10-05 KST).
Current instruction: `docs/compliance/REPAIR_PROMPT_KO.md`. Tool: ChatGPT Work coding
assistant; exact model build not available. Outputs: packaging guard/tests, provenance
audit, development retrieval-depth experiment, and execution report. Sources: repository
code and https://nova.snubhai.org/rules/ and /evaluation/. No clinical facts, synthetic
case labels or patient data are generated or altered by this repair.
