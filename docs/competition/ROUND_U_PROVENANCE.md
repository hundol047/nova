# Round U evidence and normalization provenance

No disease profiles or clinical likelihood ratios were authored in this round. The new rules are bounded engineering interpretation of observations and existing catalog features; they are not clinician-adjudicated.

| Change | Source / limit |
|---|---|
| Worsening/relief predicate retained across canonical/alias/disjunction matching | Linguistic observation fidelity. Mere meal/posture mentions do not state symptom direction. Existing feature vocabulary only. |
| Fluttering no longer asserts an irregular rhythm | Removes an unsupported alias. Explicit cardiac fluttering can still represent subjective palpitations; it does not supply a measured rhythm. |
| Rotation, short duration and position trigger | Compositional normalization into existing `vertigo`, `brief episodic vertigo`, `triggered by head position change` features. No maneuver result or BPPV confirmation inferred. |
| Nonspecific measured severity cannot establish a cause | Retains the existing measured-rate restriction and refuses an underlying cause supported only by rate/perfusion findings. Constitutional severity adjectives do not identify an adrenal cause. A broader all-abnormal-vitals gate was rejected after critical regressions; fever/hypoxic/cognitive observations are not erased. No new numeric threshold. |
| Observed detail precedence | Engineering ordering rule for a strict fragment vs the fuller observed pattern when the latter has only optional, never-positive generic symptom denials. Raw scores and contradiction records remain unchanged; no clinical probabilities or disease-specific bonus. |
| Reassurance-only candidates | Absence of symptoms and risk context may adjust a differential but cannot establish its current cause. Stable priority for positive-net-score candidates with a current positive observation; candidates, raw scores and contradictions remain visible. No dangerousness bonus. |
| Single diarrhea observation | Adds the existing catalog symptom to the existing single-nonspecific-observation abstention contract. Converging observations and current documented diagnosis remain eligible. This is an engineering naming threshold, not a diagnostic criterion or a new disease profile. |
| Observed examination features | At most 12 exact, multi-word feature phrases from the existing catalog, present in an actually obtained bedside observation after assertion/subject/time filtering. No new clinical feature or diagnosis generated. |
| Unconfirmed findings | Shared assertion uncertainty cues distinguish inability to confirm from a positive finding or definite exclusion; the existing per-diagnosis scope parser is retained. |
| Anatomical pressure/spread wording | Existing substernal-pressure and arm-radiation features receive complete anatomical/symptom paraphrases. A rash spreading to an arm is not pressure/pain radiating there. |
| Diagnostic Top25 vs safety watch | Retrieval architecture. Dangerousness supplies no score or support. Existing legacy API remains testable; production uses separate watch. |
| Symptomatic marked-rate concern retains ECG in SOAP plan | Existing concern/thresholds from `disposition.py`; existing catalog test `ecg`. NICE CG109 recommendation 1.1.2.2 and QS71 statement 2 recommend ECG in initial assessment of transient loss of consciousness. This does not establish the cause, execute a preliminary TEST, or fabricate a result. |

Authoritative references checked 2026-10-09:

- NICE CG109, recommendation 1.1.2.2: https://www.nice.org.uk/guidance/cg109/chapter/Recommendations
- NICE QS71, statement 2: https://www.nice.org.uk/guidance/QS71/chapter/quality-statement-2-initial-assessment-12-lead-electrocardiogram-ecg

The recommendation was confirmed from official NICE search-index text. Direct chapter retrieval returned HTTP 403 and PDF retrieval timed out; no claim of a complete new guideline review. The broader retained symptomatic-rate concern is a pre-existing engineering safety heuristic, not a newly guideline-validated triage rule. Existing rights/provenance statuses are not upgraded by hash refreshes.

## Subsequent compositional refinement (before final freeze)

- Sensation + chest/sternal anatomy and pain + arm/shoulder/jaw spread are projected only from current affirmative patient observations. This extends the existing KB pressure feature family; the internal feature name is not an independently confirmed anatomical lesion or coronary diagnosis. Raw patient wording stays in SOAP.
- The American Heart Association describes pressure/squeezing and upper-body discomfort among warning symptoms. This supports the vocabulary family, not the software thresholds or a clinical accuracy claim. Source checked 2026-10-09: https://www.heart.org/en/health-topics/heart-attack/warning-signs-of-a-heart-attack . NICE CG95 is supporting context: https://www.nice.org.uk/guidance/cg95/chapter/recommendations .
- Korean vomiting predicate forms normalize the actual act of vomiting, with subject and negation controls. Neither nausea nor the word for Saturday supplies vomiting. This is translation of an existing symptom, not new disease metadata.
- Joining existing generic symptoms with and/or/with does not make a single catalog feature discriminating. Existing non-generic anatomy/trigger components remain distinct. Observed vital red flags still trigger disposition; no normal laboratory result or disease exclusion is inferred.
- U20 and U12 were promoted to development. A separate final U10 fixture was authored and frozen before execution. All three are implementation-aware synthetic engineering fixtures, not independent clinical validation.

## Abdominal descriptors and thin alternative disposition

- Shared protected-qualifier matching now requires actually stated severe/diffuse and lower-abdominal descriptors for the two existing catalog features. Aliases cannot bypass these conditions. This is linguistic evidence fidelity, not new medical content.
- A shallow ontology alternative supported by one subjective symptom is retained in the differential, but cannot by itself trigger emergency disposition. Current documentation, an actually observed objective phrase, an existing explicit profile discriminator or corroborating positive observations preserve the pathway. Selected urgent diagnoses and measured vital/rate concerns are unchanged. This is an engineering safeguard for sparse metadata and needs independent clinical validation; it is not a validated clinical threshold.
- U10 was promoted to development after its disposition failure informed this repair. Closing U8 is a separate small, implementation-aware control set frozen before execution, not independent clinical or broad generalization evidence.
