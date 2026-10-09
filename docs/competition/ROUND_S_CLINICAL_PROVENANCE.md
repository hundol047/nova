# Round S clinical-rule provenance

Checked 2026-10-09. Engineering implementation, not clinician adjudication. No new disease profiles, treatments, probabilities or diagnosis-specific score boosts.

| Behavior | Source | Scope and limitation |
|---|---|---|
| Postural symptom relation; benign faint must not conceal an alternative cause | NICE CG109 initial assessment / 1.1.4.3, accessed via Royal College of Physicians, https://www.rcp.ac.uk/resources/transient-loss-of-consciousness-blackouts-in-over-16s-nice-guideline/ | Event posture, preceding symptoms and cardiac findings need assessment. A measured pulse is not an ECG rhythm diagnosis. Existing <50 / >=150 bounds remain engineering triage guards; not represented as NICE numeric diagnostic criteria. |
| Orthostatic hypotension needs a typical history and no competing explanation | NICE CG109, cross-referenced by NICE ESNM61, https://www.nice.org.uk/advice/esnm61/chapter/full-evidence-summary | A standing token or denied trigger is not evidence of a postural relationship. No BP fall is invented. |
| Bilateral pressing/tightening head pain | NICE CG150 table 1, https://www.nice.org.uk/guidance/cg150/chapter/recommendations | Bounded normalization of existing feature. Both location and quality required in one positive assertion. It supplies support, not automatic diagnosis; headache alone is insufficient. |
| CTA pulmonary-arterial filling-defect context | ESC/ERS 2019 guideline, https://publications.ersnet.org/index.php/content/erj/54/3/1901647; 2025 ESC/Fleischner/ACVC/EACVI consensus, https://academic.oup.com/ehjcimaging/article/26/7/1085/8123211 | The arterial compartment and study matter. Definite segmental/proximal pulmonary clot on CTPA is diagnostic evidence; artifacts/uncertain descriptions are not. Do not interpret a patient's guess, nonpulmonary study, or vague blood near the brain as a specific objective diagnosis. |

NICE direct page fetches returned HTTP403; the indexed NICE recommendations and accessible RCP guidance were read. Sources are attribution, not a claim that the entire ruleset or existing asset licence has been clinically reviewed/cleared.

Unknown replies, comma-list scope, provenance filtering, selected-ID consistency and workup coverage are software contracts. They add no new medical facts. Existing vital red-flag thresholds are reused only for disposition, never diagnosis ranking. Family history requires disease content; adding a wrapper cannot manufacture it.

Generic symptom absence: NICE NG228 recommendations 1.1 and context (https://www.nice.org.uk/guidance/ng228/chapter/Recommendations ; https://www.nice.org.uk/guidance/ng228/chapter/Context) identify thunderclap onset as a red flag, with possible additional symptoms. This motivated a diagnosis-independent numerical repair: generic symptom denials use the existing generic-symptom list and are combined inside the symptom evidence cap. Specific contradictions, objective negatives and explicit reassuring findings retain full penalties. Engineering scores are not calibrated likelihood ratios and do not confirm SAH without diagnostic evidence. NICE indexed primary text was accessible; direct recommendation fetch returned 403.

Shared temporal words cannot establish another symptom: sudden-onset headache does not assert dyspnea or palpitations. This is a logical matching constraint, not a new medical association. Undifferentiated SOAP retains actual missing discriminators from alternatives instead of declaring that none remain.
