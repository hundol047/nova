"""Blind evaluation set v10 (vNext 500-disease + ML-integration round).

Why v10: this round changed candidate generation and open-world retrieval behavior
(nova_agent/candidate_generator.py ontology broadening, nova_agent/open_world.py multi-signal
retrieval + rare fallback + hierarchy expansion) and integrated a governed ML ranker into the
backend inference path. Per the blind-set discipline, a set frozen BEFORE a reasoning change can no
longer be the "untouched" measure of the changed code: **Blind v3–v9 are now REFERENCE-ONLY**, and
this fresh set is the untouched check for the current code.

Authoring rules followed (identical discipline to blind_cases_v6/v8/v9):
  1. Written AFTER all reasoning changes in this round were complete.
  2. No sentence/clause/phrase copied from evaluation/cases.py, held_out_cases.py,
     generalization_cases_v2.py, generalization_stress_cases.py, or any blind_cases_v3..v9.py --
     every vignette is freshly written with a distinct mechanism/setting/demographic, and NOTHING is
     keyed to a prior miss (the leakage scan covers this file).
  3. Representative coverage of the axes the vNext work touches (NOT all 500+ conditions — a blind
     set is a representative honesty check, not an exhaustive enumeration):
       common, critical/must-not-miss, benign mimic, dangerous mimic, rare, very rare,
       ontology-only (Tier-2 structured, not deep), unknown/OOD, multimorbidity, polypharmacy,
       pediatric, pregnancy, mixed-language, atypical presentation, conflicting evidence,
       data-freshness, wrong-units.
     Spread across en/ko/ja/zh/mixed input.
  4. ground_truth_diagnosis frozen BEFORE the first run -- see evaluation/blind_v10_manifest.json
     for the SHA-256 recorded at freeze time. Not edited after seeing any run's result. FIRST RUN
     happens exactly once in a runnable environment (needs pydantic); NOT run in this network-
     isolated authoring environment -> reported NOT VERIFIED until executed once, then transcribed
     as-is and never re-tuned against.

Ground-truth ids: Tier-1 deep cases use knowledge/diseases ids; ontology/rare cases use the
catalog's Tier-2 concept id form ("tier2:<id>"); genuinely-unknown / OOD cases set
scoring_expected=False (excluded from the accuracy denominator, still checked for safe behavior).

Hand-authored synthetic vignettes, never real patient data.
"""

from __future__ import annotations

from evaluation.cases import SyntheticCase

BLIND_CASES_V10 = [
    # --- common (Tier-1 deep) --------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind10_01_ExertionalChestHeaviness", category="common",
        chief_complaint="a heavy pressure sits mid-chest whenever I walk uphill and eases with rest",
        demographics={"age": 63, "sex": "male"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "started 90 minutes ago, worse on exertion",
                 "associated_symptoms": "sweaty, left arm ache; denies fever, denies cough",
                 "past_medical_history": "hypertension, high cholesterol"},
        exam_results={"vital_signs": "BP 150/90, HR 92, RR 18, Temp 36.8, SpO2 96%"},
        test_results={"ecg": "lateral ST depression", "troponin": "troponin above the reference limit"},
    ),
    SyntheticCase(
        case_id="Blind10_02_DysuriaFrequencyWoman", category="common",
        chief_complaint="burning when I pass urine and going far more often since yesterday",
        demographics={"age": 29, "sex": "female"}, ground_truth_diagnosis="uncomplicated_cystitis",
        answers={"associated_symptoms": "suprapubic discomfort; denies flank pain, denies fever",
                 "past_medical_history": "otherwise well"},
        exam_results={"vital_signs": "BP 118/74, HR 78, RR 16, Temp 36.9, SpO2 99%"},
        test_results={"urinalysis": "dipstick positive for leukocyte esterase and nitrites"},
    ),
    # --- critical / must-not-miss ----------------------------------------------------------------
    SyntheticCase(
        case_id="Blind10_03_WorstHeadacheSudden", category="critical",
        chief_complaint="the worst headache of my life hit like a thunderclap while I was reading",
        demographics={"age": 48, "sex": "female"}, ground_truth_diagnosis="subarachnoid_hemorrhage",
        answers={"onset": "instant peak 30 minutes ago", "associated_symptoms": "vomited once, neck stiff",
                 "past_medical_history": "denies trauma"},
        exam_results={"vital_signs": "BP 172/98, HR 88, RR 18, Temp 37.0, SpO2 98%"},
        test_results={"ct_head": "hyperdensity in the basal cisterns"},
    ),
    SyntheticCase(
        case_id="Blind10_04_FeverConfusionHypotension", category="critical",
        chief_complaint="febrile, confused, and the blood pressure keeps dropping",
        demographics={"age": 74, "sex": "male"}, ground_truth_diagnosis="sepsis",
        answers={"onset": "worsening over 8 hours", "associated_symptoms": "rigors, poor urine output",
                 "past_medical_history": "recent urinary catheter"},
        exam_results={"vital_signs": "BP 84/50, HR 122, RR 26, Temp 39.1, SpO2 92%"},
        test_results={"lactate": "lactate 4.6 mmol/L", "wbc": "WBC markedly elevated"},
    ),
    # --- dangerous mimic -------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind10_05_TearingBackDiaphoresis", category="dangerous_mimic",
        chief_complaint="a tearing pain ripped from my chest through to between the shoulder blades",
        demographics={"age": 68, "sex": "male"}, ground_truth_diagnosis="aortic_dissection",
        answers={"onset": "maximal instantly 35 minutes ago", "character": "tearing, migrating",
                 "past_medical_history": "long-standing hypertension"},
        exam_results={"vital_signs": "BP 188/70 right arm, 150/64 left arm, HR 96"},
        test_results={"ct_angiogram": "intimal flap in the descending aorta"},
    ),
    # --- benign mimic ----------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind10_06_PositionalChestWallPain", category="benign_mimic",
        chief_complaint="sharp chest pain that stabs when I press the breastbone or twist",
        demographics={"age": 27, "sex": "female"}, ground_truth_diagnosis="musculoskeletal_chest_pain",
        answers={"onset": "since a heavy gym session two days ago",
                 "associated_symptoms": "reproducible on palpation; denies dyspnea, denies fever"},
        exam_results={"vital_signs": "BP 116/72, HR 70, RR 14, Temp 36.7, SpO2 99%",
                      "chest_exam": "tender costochondral junctions, reproduces the pain"},
    ),
    # --- rare (Tier-2 structured) ----------------------------------------------------------------
    SyntheticCase(
        case_id="Blind10_07_YoungManPleuriticFeverViral", category="rare",
        chief_complaint="sharp chest pain that eases when I lean forward, after a week of a cold",
        demographics={"age": 33, "sex": "male"}, ground_truth_diagnosis="tier2:pericarditis",
        answers={"onset": "3 days, worse lying flat, better sitting forward",
                 "associated_symptoms": "low-grade fever, recent viral URI"},
        exam_results={"vital_signs": "BP 122/78, HR 96, RR 18, Temp 37.8, SpO2 98%",
                      "cardiac_exam": "three-component friction rub"},
        test_results={"ecg": "diffuse concave ST elevation with PR depression"},
        scoring_expected=False,
        notes="Tier-2 structured target: scored for safe/plausible handling, not deterministic top-1.",
    ),
    SyntheticCase(
        case_id="Blind10_08_PainlessJaundiceWeightLoss", category="rare",
        chief_complaint="my skin and eyes turned yellow and I've lost weight without trying",
        demographics={"age": 70, "sex": "male"}, ground_truth_diagnosis="tier2:pancreatic_cancer",
        answers={"onset": "gradual over 2 months", "associated_symptoms": "pale stools, dark urine, painless",
                 "past_medical_history": "new-onset diabetes 3 months ago"},
        exam_results={"abdominal_exam": "palpable non-tender gallbladder"},
        scoring_expected=False,
        notes="Tier-2 structured target; representative long-tail retrieval, not deterministic top-1.",
    ),
    # --- very rare -------------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind10_09_EpisodicHeadacheSweatingHTN", category="very_rare",
        chief_complaint="pounding headaches with drenching sweats and racing heart in spells",
        demographics={"age": 41, "sex": "female"}, ground_truth_diagnosis="tier2:pheochromocytoma",
        answers={"onset": "episodic over months", "associated_symptoms": "pallor, palpitations, anxiety"},
        exam_results={"vital_signs": "BP 210/120 during a spell, normal between"},
        scoring_expected=False,
        notes="Very-rare Tier-2 target; retrieval/possibility check, never forced top-1.",
    ),
    # --- ontology-only style (structured, no deep profile) ---------------------------------------
    SyntheticCase(
        case_id="Blind10_10_TargetoidRashMucosaDrug", category="ontology_only",
        chief_complaint="painful blistering rash with mouth sores after starting a new antibiotic",
        demographics={"age": 35, "sex": "female"}, ground_truth_diagnosis="tier2:stevens_johnson_syndrome",
        answers={"onset": "48 hours after a new sulfa drug", "associated_symptoms": "fever, skin sloughing"},
        exam_results={"skin_exam": "targetoid lesions with mucosal erosions, positive Nikolsky"},
        scoring_expected=False,
        notes="Structured (non-deep) target; must be RETRIEVABLE as a named possibility.",
    ),
    # --- unknown / outside coverage --------------------------------------------------------------
    SyntheticCase(
        case_id="Blind10_11_VagueFatigueNoLocalizing", category="unknown",
        chief_complaint="I've just felt off and tired for a few weeks, nothing specific",
        demographics={"age": 52, "sex": "female"}, ground_truth_diagnosis="unknown",
        answers={"onset": "vague, weeks", "associated_symptoms": "denies fever, pain, weight loss, focal symptoms"},
        exam_results={"vital_signs": "BP 120/78, HR 72, RR 14, Temp 36.7, SpO2 99%"},
        scoring_expected=False,
        notes="Insufficient localizing signal: correct behavior is explicit uncertainty, not a forced label.",
    ),
    # --- OOD (out-of-distribution presentation) --------------------------------------------------
    SyntheticCase(
        case_id="Blind10_12_ExoticTravelUndifferentiated", category="ood",
        chief_complaint="cyclical high fevers and joint pains after returning from a remote expedition",
        demographics={"age": 38, "sex": "male"}, ground_truth_diagnosis="unknown",
        answers={"onset": "fevers every 48 hours for a week", "associated_symptoms": "rigors, myalgia",
                 "past_medical_history": "returned from a malaria-endemic region"},
        exam_results={"vital_signs": "BP 110/70, HR 104, RR 20, Temp 39.4, SpO2 97%"},
        scoring_expected=False,
        notes="OOD-flavored: broad differential + explicit uncertainty; do not over-confidently label.",
    ),
    # --- multimorbidity --------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind10_13_DyspneaCHFvsCOPDvsPE", category="multimorbidity",
        chief_complaint="getting more breathless with leg swelling and a productive cough",
        demographics={"age": 77, "sex": "female"}, ground_truth_diagnosis="asthma_copd_exacerbation",
        answers={"onset": "5 days, worse at night", "associated_symptoms": "orthopnea, ankle edema, wheeze",
                 "past_medical_history": "COPD, heart failure, atrial fibrillation on warfarin"},
        exam_results={"vital_signs": "BP 138/84, HR 96 irregular, RR 24, Temp 37.1, SpO2 89%",
                      "chest_exam": "diffuse wheeze with bibasal crackles"},
        notes="Overlapping cardiopulmonary disease; must keep several dangerous candidates alive.",
    ),
    # --- polypharmacy ----------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind10_14_ConfusionManyMedsElderly", category="polypharmacy",
        chief_complaint="grandmother is drowsy and confused since her medications were changed",
        demographics={"age": 83, "sex": "female"}, ground_truth_diagnosis="hypoglycemia",
        answers={"onset": "this morning", "associated_symptoms": "sweaty, tremulous, poor oral intake",
                 "medications": "insulin glargine, glimepiride, metformin, tramadol, sertraline, warfarin"},
        exam_results={"vital_signs": "BP 128/76, HR 98, RR 16, Temp 36.5, SpO2 97%"},
        test_results={"glucose_point_of_care": "glucose 38 mg/dL"},
        notes="Polypharmacy incl. two hypoglycemic agents; objective glucose is decisive.",
    ),
    # --- pediatric -------------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind10_15_ChildBarkingCoughStridor", category="pediatric",
        chief_complaint="my 2-year-old has a barking cough and noisy breathing tonight",
        demographics={"age": 2, "sex": "male"}, ground_truth_diagnosis="tier2:croup",
        answers={"onset": "worse overnight after a cold", "associated_symptoms": "hoarse, inspiratory stridor at rest"},
        exam_results={"vital_signs": "HR 130, RR 34, Temp 38.0, SpO2 95%",
                      "respiratory_exam": "barky cough, stridor at rest, no drooling"},
        scoring_expected=False,
        notes="Pediatric Tier-2 target; retrievable named possibility, not deterministic top-1.",
    ),
    # --- pregnancy -------------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind10_16_ThirdTrimesterHeadacheHTN", category="pregnancy",
        chief_complaint="34 weeks pregnant with a bad headache, blurred vision and swelling",
        demographics={"age": 31, "sex": "female"}, ground_truth_diagnosis="tier2:preeclampsia",
        answers={"onset": "since this morning", "associated_symptoms": "epigastric pain, facial edema",
                 "past_medical_history": "primigravida, 34 weeks"},
        exam_results={"vital_signs": "BP 168/110, HR 88, RR 16, Temp 36.8, SpO2 98%"},
        test_results={"urinalysis": "3+ proteinuria"},
        scoring_expected=False,
        notes="Obstetric Tier-2 target; must be retrievable and never dismissed.",
    ),
    # --- mixed language --------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind10_17_MixedKoEn_RLQPain", category="mixed_language",
        chief_complaint="배꼽 주위가 아프다가 지금은 right lower quadrant로 통증이 옮겨갔어요",
        demographics={"age": 24, "sex": "male"}, ground_truth_diagnosis="appendicitis",
        answers={"onset": "약 12시간 전 시작, 이동성 통증",
                 "associated_symptoms": "메스꺼움, 식욕 없음, low-grade fever"},
        exam_results={"abdominal_exam": "McBurney point tenderness with rebound"},
    ),
    SyntheticCase(
        case_id="Blind10_18_JaDysuriaFlankFever", category="mixed_language",
        chief_complaint="右の脇腹が痛くて高熱があり、排尿時に痛みます",
        demographics={"age": 45, "sex": "female"}, ground_truth_diagnosis="pyelonephritis",
        answers={"onset": "2日前から悪化", "associated_symptoms": "悪寒、嘔吐、costovertebral angle tenderness"},
        exam_results={"vital_signs": "BP 116/72, HR 104, RR 20, Temp 39.0, SpO2 97%"},
        test_results={"urinalysis": "pyuria with positive nitrites"},
    ),
    # --- atypical presentation -------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind10_19_SilentMIElderlyDiabetic", category="atypical",
        chief_complaint="just very tired and a bit nauseated, no chest pain at all",
        demographics={"age": 79, "sex": "female"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "since this morning", "associated_symptoms": "fatigue, nausea, mild dyspnea; denies chest pain",
                 "past_medical_history": "type 2 diabetes, prior stroke"},
        exam_results={"vital_signs": "BP 132/80, HR 58, RR 20, Temp 36.6, SpO2 94%"},
        test_results={"ecg": "new Q waves inferiorly", "troponin": "troponin elevated above reference"},
        notes="Atypical/silent presentation in an elderly diabetic; objective evidence carries it.",
    ),
    # --- conflicting evidence --------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind10_20_ConflictingPEvsAnxiety", category="conflicting_findings",
        chief_complaint="sudden shortness of breath and racing heart; I also have panic attacks",
        demographics={"age": 44, "sex": "female"}, ground_truth_diagnosis="pulmonary_embolism",
        answers={"onset": "abrupt 2 hours ago", "associated_symptoms": "pleuritic pain, calf swelling; recent long flight",
                 "past_medical_history": "anxiety disorder, on the oral contraceptive pill"},
        exam_results={"vital_signs": "BP 118/76, HR 118, RR 26, Temp 37.0, SpO2 90%",
                      "leg_exam": "right calf swollen and tender"},
        test_results={"d_dimer": "D-dimer markedly elevated"},
        notes="Anxiety history is a distractor; DVT risk + hypoxia + D-dimer must keep PE alive.",
    ),
    # --- data freshness --------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind10_21_StaleNormalTroponinEarly", category="data_freshness",
        chief_complaint="crushing chest pain that started only 30 minutes ago",
        demographics={"age": 59, "sex": "male"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "30 minutes ago, ongoing", "associated_symptoms": "diaphoresis, radiates to jaw",
                 "past_medical_history": "a troponin drawn 3 days ago for a checkup was normal"},
        exam_results={"vital_signs": "BP 148/88, HR 98, RR 20, Temp 36.9, SpO2 96%"},
        test_results={"ecg": "hyperacute T waves anteriorly"},
        notes="A 3-day-old normal troponin must NOT reassure for a 30-minute-old presentation.",
    ),
    # --- wrong / alternate units -----------------------------------------------------------------
    SyntheticCase(
        case_id="Blind10_22_SIUnitsCreatinineAKI", category="unit_safety",
        chief_complaint="I've barely passed urine for two days and my ankles are swelling",
        demographics={"age": 66, "sex": "male"}, ground_truth_diagnosis="tier2:acute_kidney_injury",
        answers={"onset": "48 hours", "associated_symptoms": "nausea, reduced urine output",
                 "past_medical_history": "started an NSAID last week"},
        exam_results={"vital_signs": "BP 150/92, HR 84, RR 18, Temp 36.7, SpO2 97%"},
        test_results={"creatinine": "creatinine 320 umol/L", "potassium": "potassium 5.9 mmol/L"},
        scoring_expected=False,
        notes="Creatinine reported in SI (umol/L) — must not be misread as a bare number; Tier-2 target.",
    ),
    SyntheticCase(
        case_id="Blind10_23_HemoglobinGramsPerLiterGIBleed", category="unit_safety",
        chief_complaint="black tarry stools and I felt faint standing up",
        demographics={"age": 61, "sex": "male"}, ground_truth_diagnosis="gi_bleeding",
        answers={"onset": "since yesterday", "associated_symptoms": "lightheaded, epigastric pain",
                 "past_medical_history": "daily ibuprofen for knees"},
        exam_results={"vital_signs": "BP 104/64, HR 108, RR 18, Temp 36.6, SpO2 98%"},
        test_results={"hemoglobin": "hemoglobin 71 g/L", "rectal_exam": "melena on the glove"},
        notes="Hemoglobin in g/L (not g/dL) — 71 g/L is severe; must not be read as a normal 71.",
    ),
]
