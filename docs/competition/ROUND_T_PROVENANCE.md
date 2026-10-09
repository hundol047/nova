# Round T: limited vocabulary and evidence-policy provenance

Read 2026-10-09. No new disease profile, medication indication or invented test result is added.

| Change | Basis | Scope / limitation |
|---|---|---|
| Passing urine with stinging/burning/pain → existing dysuria concept | NHS, [Urinary tract infections](https://www.nhs.uk/conditions/urinary-tract-infections-utis/); NHS/UKHSA [symptom poster](https://www.england.nhs.uk/south/wp-content/uploads/sites/6/2023/10/2023.08.03_UTI_Symptoms_Poster_A4.pdf) | Wording normalization only. Dysuria alone does not establish infection or retention. |
| Measured rate abnormality is not disease-specific rhythm confirmation | NICE [NG196 recommendations](https://www.nice.org.uk/guidance/ng196/chapter/recommendations), 1.1.1–1.1.2 | NICE requires electrical evidence for AF diagnosis. Our broader rule withholding a named cause from pulse-only support is an engineering restraint, not a new guideline threshold. Preliminary encounters may end without an ECG. |
| Urgent plan persists for actual marked pulse plus loss of consciousness | Existing Round S policy/provenance: NICE CG109 initial assessment and uncomplicated-faint conditions | Reuses existing thresholds; adds the already catalogued wording “lost consciousness”. Does not infer rhythm subtype or fabricate ECG. |
| Family/other experiencer, history/current, capability predicate binding | Original span/source + existing assertion_status lexical cues | Linguistic engineering rules, not clinical facts. A third-person clinical observation can concern the patient; explicit family antecedents must stay external. No general claim of perfect coreference resolution. |
| Clinical concept query expansion | Existing canonical_findings_for / multilingual / ontology aliases only | Bounded observed concepts. No disease-label generation, free-form LLM query expansion or larger Top150 budget. |

Family history is retained as risk context when appropriate; it is not erased from the patient's record.
All tests and new synthetic cases are engineering validation, not independent clinician review.

Caregiver-only current descriptions may justify gathering an existing bedside examination without becoming patient-positive scoring evidence. Attempts, refusal, unknown and true negatives remain distinct. Initial zero-support EXAM pruning was withdrawn after fresh-expression stroke regressions; exact phrase matching/routing failure does not justify deleting a bedside action. The older zero-support ontology-question budget remains unchanged.

Respiratory blood matching now binds the material to coughing/spitting or sputum, in either grammatical order. It cannot borrow blood from a blood-test/pressure clause. Real positive aliases (including blood in sputum and blood-stained sputum) remain recognized. This is assertion fidelity, not a new medical fact.

A single generic symptom cannot name an underlying cause solely because the candidate is classified non-dangerous. The same support constraint now covers a lone productive cough. This is a conservative engineering completion rule, not a validated diagnostic probability or clinical guideline.
