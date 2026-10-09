# LLM generation log

Historical generation records are incomplete. The exact tool/model, original prompt and source
material are UNRESOLVED unless explicitly stated below. A commit timestamp is not a generation
receipt. This log records gaps; it does not reconstruct invented provenance.

Machine-readable inventory: `artifacts/round_m/generation_inventory.json`.

| Output | Tool/model | Recorded commit date, NOT generation date | Prompt/instruction | Source material | Manual review |
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

## 2026-10-05 compliance boundary pass

Instruction: user's numbered compliance/provenance/release request, sections 0–14 supplied
in this session. Tool: ChatGPT Work coding assistant; exact model/version unavailable.
Outputs: separate official/local entrypoints, lifecycle and emitted-action guards, synthetic
engineering boundary tests, rule matrix, historical-evidence inventory and replacement plan.
No clinical facts or disease labels were generated, and no clinical runtime asset was replaced.
Clinical assets remain byte-identical to 5413af9. Engineering tests are not clinician review.
Sources: current repository and genuine Git object history; official N.O.V.A. rules/evaluation/FAQ;
MedlinePlus publisher reuse terms and XML index. Exact historical generation records remain
unresolved; this entry does not retrospectively create them.

## 2026-10-05 licensed reference extraction

Output: `nova_agent/knowledge/licensed_references.json`.
Clinical-content generation tool/model/version/prompt: NOT APPLICABLE. Clinical text
was selected from the named publishers and deterministically transformed by
`scripts/import_licensed_references.py`; original markup, source metadata and hashes
are retained in `research/licensed_references/source_snapshot.json`. No LLM clinical
paraphrasing, translation, diagnosis labels, features or thresholds were generated.

The coding assistant wrote extraction/integration code and documentation following
the user's instruction `반영해줘` to integrate the previously identified MedlinePlus
and Orphanet materials, subject to the preceding provenance and competition constraints.
Its exact model/version is unavailable and is NOT claimed as a reproducibility receipt.
Reproduction of the clinical text depends only on retained inputs and code, not on
re-running the coding assistant. Review: engineering tests and source/terms inspection;
clinician review NOT PERFORMED. Earlier clinical-generation gaps remain unresolved.

## 2026-10-05 clinical review and engineering experiments

User instruction: complete provenance follow-up, retrieval/rerank improvement, action
efficiency evaluation, and a professor review packet. Coding assistant exact model/build
remains UNRESOLVED; no reproducible external-LLM clinical generation is claimed.
`prepare_clinical_review.py` enumerates existing data and links exact names to already
retained publisher references; lexical matches do not validate a clinical rule.
`prepare_test_note_replacements.py` extracts the first complete publisher paragraph
with the retained HTML parser, without paraphrase. Five excerpts are review candidates,
not promoted diagnostic replacements. Source markup, publisher terms, version and hashes
are retained. Neither new clinical facts nor new case labels were generated.
Review status: no clinician has reviewed or approved this packet. Runtime engineering
experiments and their rejected variants are recorded in artifacts/clinical_review_pass.

## Pass of 2026-10-07 (preliminary integration / backend load / evidence interpretation)

Tool: Claude Code (an Anthropic Claude model; the exact model identifier is not recorded in repository artifacts by
session policy). Instruction: the repository owner's written task for this pass (backend load-test fix, preliminary
diagnostic error analysis, provenance status, submission packaging). No external clinical source was consulted.
Runtime content authored or edited in this pass, all engineering-authored and **not clinician-reviewed**:

| File | What was written |
|---|---|
| `nova_agent/lay_language.py` | additive lay aliases: medication omission (`missed insulin doses`), VTE context (`recent surgery`, `immobilization`), exertional wording, `polydipsia` <- `thirsty`, confusion/sleepiness, dysuria wording |
| `nova_agent/matching.py` | turn-scoped memoisation; regex-free word-boundary check; medication-USE features ignore stopped/run-out/skipped drugs |
| `nova_agent/vitals_parser.py` | descriptive `Tachycardia` (HR 101-119) and `Fever` (38.0-38.9 C) findings below the existing red-flag thresholds |
| `nova_agent/chief_complaint.py` | `pain on urinating/urination` routing aliases |
| `nova_agent/orchestrator.py` | decision-scoped memo; legacy learning/ catalog context never runs under preliminary rules |
| `nova_agent/soap.py` | clause-level answer classification merged with the integration branch's unclear/education handling |
Existing rows above remain UNRESOLVED; this pass does not reconstruct earlier generation records.

## Round R assertion and observation repair — 2026-10-09

Engineering assistant changes on the Round Q working branch; no external LLM call,
model download, fine-tuning, evaluation-label edit or blind execution. User request:
implement the preceding acceptance work order, preserve observed evidence and fix
negation, information collection and unsupported final diagnoses. New tests and
fixtures are agent-authored synthetic development material, not independent clinical
validation. Exact runtime and executed hashes are recorded in verification v23.

Clinical guard provenance (not clearance of historical KB sources or licence):
- ESC 2022 ventricular arrhythmia guideline, section 5.1.3, DOI
  https://doi.org/10.1093/eurheartj/ehac262 : ECG evidence identifies the rhythm
  subtype. The implementation does not infer ventricular origin from pulse rate.
- NICE CG109 recommendations 1.1.2 and 1.1.4.3,
  https://www.nice.org.uk/guidance/cg109/chapter/Recommendations : uncomplicated
  faint requires no features suggesting another diagnosis. The final-label guard
  reuses existing pulse thresholds and retains the cardiac alternative for evaluation.
- Murmur and lung-sound EXAM routing reuses the existing taxonomy's auscultation
  maneuvers. Electrolyte follow-ups reuse existing KB risk context; they add no
  laboratory value, electrolyte direction, diagnostic weight or treatment instruction.
- Generic-support and risk-only naming guards are uncalibrated engineering policies,
  not clinical exclusion criteria. Source matching, timestamps and experiencer are
  linguistic assertions; raw observations remain in the record.
