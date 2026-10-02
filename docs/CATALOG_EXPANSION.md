# 68-condition catalog expansion

The local catalog now contains 68 diagnostic entries: the original 34 plus 34 additions.
Some entries describe syndromes or findings (such as pleural effusion), not an established
underlying cause. This is expanded software coverage, not proof of clinical diagnostic ability.

## Behavior

- Added 16 named procedures, including thyroid/iron panels, echocardiography, venous ultrasound,
  synovial analysis and co-oximetry. These belong to the local action vocabulary; availability
  and mapping in the official competition runtime remain unverified.
- New evidence rules bind each report phrase to its examination or laboratory/imaging source.
  Patient history, an unrelated procedure, tentative text and negated findings cannot substitute.
- Alternative phrasings within one rule count once. Conflicting positive/negative observations
  cannot complete that rule and are reported as contradictions.
- Source-supported dangerous alternatives remain visible to safety even outside the top ranks.
- Incomplete required evidence caps confidence at LOW and blocks early finalization. The hard
  turn-limit submission fallback still applies and is explicitly uncalibrated.
- Generic normal tests do not automatically resolve new diagnoses. A disease-specific exclusion
  must appear in a relevant report. These are conservative software guards, not clinical criteria.
- Diagnosis-name mapping uses whole phrases, never reverse substring matches such as “acute” or
  accidental acronym matches inside a word.

The matching vocabulary is bounded and mostly English. New numeric panels currently need an
explicit qualitative interpretation; unparsed numbers do not create evidence automatically.
Coexisting diseases, atypical presentations, pediatric/pregnancy differences, arbitrary Korean
phrasing and overlapping syndromes need broader independent evaluation. The all-rules support
requirement is an implementation guard, not a claim that each feature is medically mandatory.

## Added entries and reference provenance

Rules and urgency labels are internally authored; the sources below inform the features but
have not medically reviewed or approved this software. Entries include individual limitations.
The reference links were checked via web retrieval on 2026-10-02 (Asia/Seoul).

| Korean name | Canonical ID | Reference |
|---|---|---|
| 급성 심낭염 | `acute_pericarditis` | [Reference](https://www.merckmanuals.com/professional/cardiovascular-disorders/myocarditis-and-pericarditis/pericarditis) |
| 급성 심부전 | `acute_heart_failure` | [Reference](https://www.merckmanuals.com/professional/cardiovascular-disorders/heart-failure/acute-heart-failure) |
| 흉막삼출 | `pleural_effusion` | [Reference](https://www.merckmanuals.com/professional/pulmonary-disorders/mediastinal-and-pleural-disorders/pleural-effusion) |
| 급성 담낭염 | `acute_cholecystitis` | [Reference](https://www.merckmanuals.com/professional/hepatic-and-biliary-disorders/gallbladder-and-bile-duct-disorders/acute-cholecystitis) |
| 급성 담관염 | `acute_cholangitis` | [Reference](https://www.merckmanuals.com/professional/hepatic-and-biliary-disorders/gallbladder-and-bile-duct-disorders/choledocholithiasis-and-cholangitis) |
| 급성 게실염 | `acute_diverticulitis` | [Reference](https://www.merckmanuals.com/professional/gastrointestinal-disorders/diverticular-disease/colonic-diverticulitis) |
| 소장폐색 | `small_bowel_obstruction` | [Reference](https://www.merckmanuals.com/professional/gastrointestinal-disorders/acute-abdomen-and-surgical-gastroenterology/intestinal-obstruction) |
| 급성 장간막허혈 | `acute_mesenteric_ischemia` | [Reference](https://www.merckmanuals.com/professional/gastrointestinal-disorders/acute-abdomen-and-surgical-gastroenterology/acute-mesenteric-ischemia) |
| 난소염전 | `ovarian_torsion` | [Reference](https://www.merckmanuals.com/professional/gynecology-and-obstetrics/miscellaneous-gynecologic-disorders/adnexal-torsion) |
| 골반염 | `pelvic_inflammatory_disease` | [Reference](https://www.merckmanuals.com/professional/gynecology-and-obstetrics/vaginitis-cervicitis-and-pelvic-inflammatory-disease/pelvic-inflammatory-disease-pid) |
| 출혈성 난소낭종 | `hemorrhagic_ovarian_cyst` | [Reference](https://www.merckmanuals.com/professional/gynecology-and-obstetrics/miscellaneous-gynecologic-disorders/benign-adnexal-masses) |
| 뇌내출혈 | `intracerebral_hemorrhage` | [Reference](https://www.merckmanuals.com/professional/neurologic-disorders/stroke/intracerebral-hemorrhage) |
| 경막하혈종 | `subdural_hematoma` | [Reference](https://www.merckmanuals.com/professional/injuries-poisoning/traumatic-brain-injury-tbi/traumatic-brain-injury-tbi) |
| 경막외혈종 | `epidural_hematoma` | [Reference](https://www.merckmanuals.com/professional/injuries-poisoning/traumatic-brain-injury-tbi/traumatic-brain-injury-tbi) |
| 뇌농양 | `brain_abscess` | [Reference](https://www.merckmanuals.com/professional/neurologic-disorders/brain-infections/brain-abscess) |
| 경막하축농 | `subdural_empyema` | [Reference](https://www.merckmanuals.com/professional/neurologic-disorders/brain-infections/intracranial-epidural-abscess-and-subdural-empyema) |
| 폐농양 | `lung_abscess` | [Reference](https://www.merckmanuals.com/professional/pulmonary-disorders/lung-abscess/lung-abscess) |
| 신장경색 | `renal_infarction` | [Reference](https://www.merckmanuals.com/professional/nephrology/renovascular-disorders/renal-artery-stenosis-and-occlusion) |
| 폐쇄성 요로병증 | `obstructive_uropathy` | [Reference](https://www.merckmanuals.com/professional/genitourinary-disorders/obstructive-uropathy/obstructive-uropathy) |
| 급성 요폐 | `acute_urinary_retention` | [Reference](https://www.merckmanuals.com/professional/genitourinary-disorders/voiding-disorders/urinary-retention) |
| 급성 신손상 | `acute_kidney_injury` | [Reference](https://www.merckmanuals.com/professional/nephrology/acute-kidney-injury/acute-kidney-injury-aki) |
| 고삼투압 고혈당 상태 | `hyperosmolar_hyperglycemic_state` | [Reference](https://www.merckmanuals.com/professional/endocrine-and-metabolic-disorders/diabetes-mellitus-and-hypoglycemia/acute-complications-of-diabetes-mellitus) |
| 철결핍빈혈 | `iron_deficiency_anemia` | [Reference](https://www.merckmanuals.com/professional/hematology/anemias-caused-by-deficient-erythropoiesis/iron-deficiency-anemia) |
| 일차성 갑상선기능저하증 | `primary_hypothyroidism` | [Reference](https://www.merckmanuals.com/professional/endocrine-and-metabolic-disorders/thyroid-disorders/hypothyroidism) |
| 갑상선기능항진증 | `hyperthyroidism` | [Reference](https://www.merckmanuals.com/professional/endocrine-and-metabolic-disorders/thyroid-disorders/hyperthyroidism) |
| 심부정맥혈전증 | `deep_vein_thrombosis` | [Reference](https://www.merckmanuals.com/professional/cardiovascular-disorders/peripheral-venous-disorders/deep-venous-thrombosis-dvt) |
| 봉와직염 | `cellulitis` | [Reference](https://www.merckmanuals.com/professional/infectious-diseases/bacterial-skin-infections/cellulitis) |
| 대상포진 | `herpes_zoster` | [Reference](https://www.merckmanuals.com/professional/infectious-diseases/herpesviruses/herpes-zoster) |
| 화농성 관절염 | `septic_arthritis` | [Reference](https://www.merckmanuals.com/professional/musculoskeletal-and-connective-tissue-disorders/infections-of-joints-and-bones/acute-infectious-arthritis) |
| 급성 통풍 | `acute_gout` | [Reference](https://www.merckmanuals.com/professional/musculoskeletal-and-connective-tissue-disorders/crystal-induced-arthritides/gout) |
| 급성 간염 | `acute_hepatitis` | [Reference](https://www.merckmanuals.com/professional/hepatic-and-biliary-disorders/hepatitis/causes-of-hepatitis) |
| 횡문근융해증 | `rhabdomyolysis` | [Reference](https://www.merckmanuals.com/professional/nephrology/acute-kidney-injury/rhabdomyolysis) |
| 일산화탄소 중독 | `carbon_monoxide_poisoning` | [Reference](https://www.merckmanuals.com/professional/injuries-poisoning/poisoning/carbon-monoxide-poisoning) |
| 인플루엔자 | `influenza` | [Reference](https://www.merckmanuals.com/professional/infectious-diseases/respiratory-viruses/influenza) |

Hemorrhagic-cyst morphology also uses the [O-RADS US v2022 consensus](https://pubs.rsna.org/radiology/doi/10.1148/radiol.230685).
No guideline-derived diagnostic score or calibrated probability is claimed.

## Reproducible regression gate

```bash
python -m pytest tests -q
python -m evaluation.catalog_regression --save-json evaluation/catalog_results.json
python scripts/build_nova_submission.py
```

The gate fails for any scored wrong diagnosis, critical miss, malformed action or duplicate
operation. It reports all unscored cases separately and hashes every case set and the catalog.
The original case texts and labels are unchanged. CI now runs this enforcing check.

`evaluation/expanded_cases.py` contains 34 same-author synthetic development vignettes with
qualitative reports using the supported vocabulary. Unknown unscripted observations remain
unknown. They are software integration checks, not a blind or independently adjudicated set.
The unit suite also checks pending/negative/history statements, wrong sources, alias collisions,
conflicting evidence and incomplete-workup finalization. Current measured results are in
`evaluation/catalog_results.json`; live-model and independent clinical validation remain absent.


### Executed results

379 tests pass. Final mock gate: original scored development 49/49, V3 32/32, V4 34/34,
V5 44/44, V6 12/12, additions 34/34. Total 205/205 scored, with 3 additional unscored cases
reported separately. Zero critical misses, duplicate operations or malformed outputs.
Submission build, source synchronization, adversarial checks and existing-case leakage scan pass.
These results do not establish independent, real-model, or clinical accuracy.
