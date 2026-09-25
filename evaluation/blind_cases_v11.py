"""Blind evaluation set v11 (5,000-diagnosis retrieval-architecture round).

Why v11: this round added a NEW reasoning-adjacent stack — the 5,000-disease retrieval architecture
(learning/retrieval embedding retrieval, learning/routing multi-specialty router, learning/
safety_recall deterministic must-not-miss expansion, learning/rerank deep reranker, learning/
pipeline retrieval->rerank->LLM assembly with a lexical-grounding UNKNOWN guard). Per the blind-set
discipline, a set frozen BEFORE a reasoning change can no longer be the untouched measure of the
changed code: **Blind v3–v10 are now REFERENCE-ONLY**, and this fresh set is the untouched check for
the current code.

Authoring rules (identical discipline to v6/v8/v9/v10):
  1. Written AFTER all 5,000-architecture reasoning code was complete.
  2. No sentence/clause/phrase copied from evaluation/cases.py, held_out_cases.py,
     generalization_cases_v2.py, generalization_stress_cases.py, or blind_cases_v3..v10.py — every
     vignette is freshly written, NOTHING keyed to a prior miss (leakage scan covers this file).
  3. Representative across the axes this round touches — common, critical, dangerous/benign mimic,
     rare, very rare, long-tail/ontology-only (Tier-3), UNKNOWN, OOD, multimorbidity, polypharmacy,
     pediatric, pregnancy, mixed-language, atypical, conflicting evidence, data-freshness,
     wrong-unit, PLUS two NEW trap axes: a RETRIEVAL-MISS trap (a true dx a naive lexical search
     would miss but embedding/hierarchy should recover) and a ROUTER-MISS trap (a presentation that
     mis-routes to the wrong specialty, where safety-recall must still keep the critical dx). NOT an
     exhaustive enumeration of 5,000. NOT tuned to any case.
  4. ground_truth_diagnosis frozen BEFORE the first run (see blind_v11_manifest.json SHA-256).
     Tier-1 targets use knowledge/diseases ids; Tier-2/rare use 'tier2:<id>'; unknown/OOD use
     'unknown' + scoring_expected=False. FIRST RUN happens exactly once in a runnable environment
     (needs pydantic); NOT run in this network-isolated env -> reported NOT VERIFIED until executed.

Hand-authored synthetic vignettes, never real patient data.
"""

from __future__ import annotations

from evaluation.cases import SyntheticCase

BLIND_CASES_V11 = [
    # --- common (Tier-1) -------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind11_01_ExertionalChestPressure", category="common",
        chief_complaint="a heavy pressure grips my chest whenever I climb stairs and eases with rest",
        demographics={"age": 61, "sex": "male"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "2 hours ago, worse on exertion", "associated_symptoms": "sweaty, jaw ache",
                 "past_medical_history": "hyperlipidemia, ex-smoker"},
        exam_results={"vital_signs": "BP 152/90, HR 90, RR 18, Temp 36.8, SpO2 96%"},
        test_results={"ecg": "lateral ST depression", "troponin": "troponin above the reference limit"},
    ),
    SyntheticCase(
        case_id="Blind11_02_LowerUtiWoman", category="common",
        chief_complaint="stinging when I urinate and going much more often since yesterday",
        demographics={"age": 26, "sex": "female"}, ground_truth_diagnosis="uncomplicated_cystitis",
        answers={"associated_symptoms": "suprapubic ache; denies flank pain, denies fever"},
        exam_results={"vital_signs": "BP 116/72, HR 76, RR 16, Temp 36.8, SpO2 99%"},
        test_results={"urinalysis": "leukocyte esterase and nitrites positive"},
    ),
    # --- critical --------------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind11_03_ThunderclapHeadache", category="critical",
        chief_complaint="the most violent headache of my life exploded while I was gardening",
        demographics={"age": 50, "sex": "female"}, ground_truth_diagnosis="subarachnoid_hemorrhage",
        answers={"onset": "instant peak 25 minutes ago", "associated_symptoms": "vomited, neck stiff"},
        exam_results={"vital_signs": "BP 176/100, HR 84, RR 18, Temp 37.0, SpO2 98%"},
        test_results={"ct_head": "blood in the basal cisterns"},
    ),
    SyntheticCase(
        case_id="Blind11_04_FebrileHypotensiveConfused", category="critical",
        chief_complaint="feverish, muddled, and the pressure keeps sagging",
        demographics={"age": 72, "sex": "male"}, ground_truth_diagnosis="sepsis",
        answers={"onset": "6 hours worsening", "associated_symptoms": "rigors, low urine output",
                 "past_medical_history": "indwelling urinary catheter"},
        exam_results={"vital_signs": "BP 82/48, HR 124, RR 26, Temp 39.2, SpO2 92%"},
        test_results={"lactate": "lactate 4.8 mmol/L"},
    ),
    # --- dangerous mimic -------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind11_05_TearingInterscapular", category="dangerous_mimic",
        chief_complaint="a tearing pain tore from my breastbone straight through to the shoulder blades",
        demographics={"age": 69, "sex": "male"}, ground_truth_diagnosis="aortic_dissection",
        answers={"onset": "maximal at once 30 minutes ago", "character": "tearing, migrating down"},
        exam_results={"vital_signs": "BP 190/72 right arm, 148/60 left arm, HR 98"},
        test_results={"ct_angiogram": "intimal flap in the descending thoracic aorta"},
    ),
    # --- benign mimic ----------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind11_06_ReproduciblePleuriticYoung", category="benign_mimic",
        chief_complaint="a sharp poke over the breastbone that stabs when I press it or twist",
        demographics={"age": 24, "sex": "female"}, ground_truth_diagnosis="musculoskeletal_chest_pain",
        answers={"onset": "since heavy lifting two days ago", "associated_symptoms": "reproducible on palpation; denies dyspnea"},
        exam_results={"vital_signs": "BP 114/70, HR 68, RR 14, Temp 36.7, SpO2 99%",
                      "chest_exam": "tender costochondral junctions reproduce the pain"},
    ),
    # --- RETRIEVAL-MISS trap: uncommon phrasing a naive lexical search would miss -----------------
    SyntheticCase(
        case_id="Blind11_07_RetrievalMiss_AscendingParalysis", category="retrieval_miss_trap",
        chief_complaint="my legs went rubbery days after a stomach bug and now my hands tingle and weaken too",
        demographics={"age": 42, "sex": "male"}, ground_truth_diagnosis="tier2:guillain_barre",
        answers={"onset": "ascending over 4 days after gastroenteritis",
                 "associated_symptoms": "symmetric weakness, areflexia, paresthesias"},
        exam_results={"neuro_exam": "absent reflexes, ascending symmetric weakness"},
        scoring_expected=False,
        notes="Retrieval-miss trap: 'rubbery legs' phrasing must still recover GBS via embedding/hierarchy.",
    ),
    # --- ROUTER-MISS trap: presentation that mis-routes; safety-recall must keep the critical dx --
    SyntheticCase(
        case_id="Blind11_08_RouterMiss_EpigastricMI", category="router_miss_trap",
        chief_complaint="burning in the pit of my stomach with nausea and sweatiness",
        demographics={"age": 66, "sex": "female"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "40 minutes, not relieved by antacid", "associated_symptoms": "diaphoresis, mild dyspnea",
                 "past_medical_history": "type 2 diabetes"},
        exam_results={"vital_signs": "BP 138/84, HR 92, RR 20, Temp 36.7, SpO2 95%"},
        test_results={"ecg": "inferior ST elevation", "troponin": "troponin elevated"},
        notes="Router-miss trap: epigastric burning routes GI, but safety-recall must keep ACS.",
    ),
    # --- rare (Tier-2) ---------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind11_09_LeanForwardPleuriticViral", category="rare",
        chief_complaint="sharp chest pain that eases when I lean forward, a week after a cold",
        demographics={"age": 31, "sex": "male"}, ground_truth_diagnosis="tier2:pericarditis",
        answers={"onset": "3 days, worse supine, better sitting forward", "associated_symptoms": "low-grade fever"},
        exam_results={"cardiac_exam": "three-component friction rub"},
        test_results={"ecg": "diffuse concave ST elevation with PR depression"},
        scoring_expected=False, notes="Tier-2 rare target; retrieval/possibility check.",
    ),
    # --- very rare -------------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind11_10_SpellsHeadacheSweatHTN", category="very_rare",
        chief_complaint="pounding headaches with drenching sweats and a racing heart, in sudden spells",
        demographics={"age": 39, "sex": "female"}, ground_truth_diagnosis="tier2:pheochromocytoma",
        answers={"onset": "episodic over months", "associated_symptoms": "pallor, palpitations"},
        exam_results={"vital_signs": "BP 214/118 during a spell, normal between"},
        scoring_expected=False, notes="Very-rare Tier-2 target; possibility, never forced top-1.",
    ),
    # --- long-tail / ontology-only (Tier-3 territory) --------------------------------------------
    SyntheticCase(
        case_id="Blind11_11_LongTail_Acroparesthesia", category="long_tail",
        chief_complaint="burning pain in my hands and feet since childhood with odd reddish skin spots",
        demographics={"age": 28, "sex": "male"}, ground_truth_diagnosis="tier2:fabry_disease",
        answers={"onset": "years", "associated_symptoms": "heat intolerance, angiokeratomas, family history"},
        scoring_expected=False, notes="Long-tail/rare metabolic; must be RETRIEVABLE as a named possibility.",
    ),
    # --- UNKNOWN ---------------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind11_12_VagueMalaise", category="unknown",
        chief_complaint="I've just felt run-down and off for a few weeks, nothing I can pin down",
        demographics={"age": 54, "sex": "female"}, ground_truth_diagnosis="unknown",
        answers={"onset": "vague, weeks", "associated_symptoms": "denies fever, pain, focal or localizing symptoms"},
        exam_results={"vital_signs": "BP 122/78, HR 72, RR 14, Temp 36.7, SpO2 99%"},
        scoring_expected=False, notes="Insufficient localizing signal -> explicit uncertainty, not a forced label.",
    ),
    # --- OOD -------------------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind11_13_OOD_ExpeditionFevers", category="ood",
        chief_complaint="cyclical high fevers and joint pains after a remote jungle expedition",
        demographics={"age": 36, "sex": "male"}, ground_truth_diagnosis="unknown",
        answers={"onset": "fevers every 48 hours for a week", "associated_symptoms": "rigors, myalgia",
                 "past_medical_history": "returned from a malaria-endemic region"},
        exam_results={"vital_signs": "BP 108/68, HR 106, RR 20, Temp 39.5, SpO2 97%"},
        scoring_expected=False, notes="OOD-flavored: broad differential + explicit uncertainty.",
    ),
    # --- multimorbidity --------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind11_14_Multimorbid_Breathless", category="multimorbidity",
        chief_complaint="more breathless with swollen ankles and a wet cough",
        demographics={"age": 78, "sex": "female"}, ground_truth_diagnosis="asthma_copd_exacerbation",
        answers={"onset": "5 days, worse at night", "associated_symptoms": "orthopnea, ankle edema, wheeze",
                 "past_medical_history": "COPD, heart failure, atrial fibrillation on warfarin"},
        exam_results={"vital_signs": "BP 136/82, HR 98 irregular, RR 24, Temp 37.1, SpO2 89%",
                      "chest_exam": "diffuse wheeze with bibasal crackles"},
        notes="Overlapping cardiopulmonary disease; several dangerous candidates must stay alive.",
    ),
    # --- polypharmacy ----------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind11_15_Polypharmacy_Drowsy", category="polypharmacy",
        chief_complaint="my father is drowsy and confused since his medicines were adjusted",
        demographics={"age": 81, "sex": "male"}, ground_truth_diagnosis="hypoglycemia",
        answers={"onset": "this morning", "associated_symptoms": "sweaty, tremulous, poor intake",
                 "medications": "insulin glargine, glimepiride, metformin, tramadol, sertraline"},
        exam_results={"vital_signs": "BP 130/78, HR 96, RR 16, Temp 36.5, SpO2 97%"},
        test_results={"glucose_point_of_care": "glucose 36 mg/dL"},
        notes="Two hypoglycemic agents; objective glucose is decisive.",
    ),
    # --- pediatric -------------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind11_16_Peds_BarkingCough", category="pediatric",
        chief_complaint="my 2-year-old has a barking cough and noisy breathing tonight",
        demographics={"age": 2, "sex": "female"}, ground_truth_diagnosis="tier2:croup",
        answers={"onset": "worse overnight after a cold", "associated_symptoms": "hoarse, inspiratory stridor at rest"},
        exam_results={"vital_signs": "HR 132, RR 34, Temp 38.1, SpO2 95%",
                      "respiratory_exam": "barky cough, stridor at rest, no drooling"},
        scoring_expected=False, notes="Pediatric Tier-2 target; retrievable named possibility.",
    ),
    # --- pregnancy -------------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind11_17_Pregnancy_HeadacheHTN", category="pregnancy",
        chief_complaint="35 weeks pregnant with a bad headache, blurred vision and puffy face",
        demographics={"age": 30, "sex": "female"}, ground_truth_diagnosis="tier2:preeclampsia",
        answers={"onset": "since morning", "associated_symptoms": "epigastric pain, facial edema",
                 "past_medical_history": "primigravida, 35 weeks"},
        exam_results={"vital_signs": "BP 170/112, HR 88, RR 16, Temp 36.8, SpO2 98%"},
        test_results={"urinalysis": "3+ proteinuria"},
        scoring_expected=False, notes="Obstetric Tier-2 target; must be retrievable, never dismissed.",
    ),
    # --- mixed language --------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind11_18_MixedKoEn_MigratingRLQ", category="mixed_language",
        chief_complaint="배꼽 근처가 아프다가 지금은 right lower quadrant로 통증이 옮겨갔어요",
        demographics={"age": 23, "sex": "male"}, ground_truth_diagnosis="appendicitis",
        answers={"onset": "약 12시간 전, 이동성 통증", "associated_symptoms": "메스꺼움, 식욕 저하, low-grade fever"},
        exam_results={"abdominal_exam": "McBurney point tenderness with rebound"},
    ),
    SyntheticCase(
        case_id="Blind11_19_Ja_FlankFeverDysuria", category="mixed_language",
        chief_complaint="右の脇腹が痛く高熱があり、排尿時にしみます",
        demographics={"age": 47, "sex": "female"}, ground_truth_diagnosis="pyelonephritis",
        answers={"onset": "2日前から悪化", "associated_symptoms": "悪寒、嘔吐、CVA tenderness"},
        exam_results={"vital_signs": "BP 114/70, HR 104, RR 20, Temp 39.1, SpO2 97%"},
        test_results={"urinalysis": "pyuria with positive nitrites"},
    ),
    # --- atypical --------------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind11_20_Atypical_SilentMI", category="atypical",
        chief_complaint="just exhausted and a little queasy, no chest pain whatsoever",
        demographics={"age": 80, "sex": "female"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "since this morning", "associated_symptoms": "fatigue, nausea, mild dyspnea; denies chest pain",
                 "past_medical_history": "type 2 diabetes, prior stroke"},
        exam_results={"vital_signs": "BP 130/80, HR 56, RR 20, Temp 36.6, SpO2 94%"},
        test_results={"ecg": "new inferior Q waves", "troponin": "troponin elevated above reference"},
        notes="Silent/atypical MI in an elderly diabetic; objective evidence carries it.",
    ),
    # --- conflicting evidence --------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind11_21_Conflicting_PEvsAnxiety", category="conflicting_findings",
        chief_complaint="sudden breathlessness and a pounding heart; I also get panic attacks",
        demographics={"age": 43, "sex": "female"}, ground_truth_diagnosis="pulmonary_embolism",
        answers={"onset": "abrupt 2 hours ago", "associated_symptoms": "pleuritic pain, right calf swelling; recent long flight",
                 "past_medical_history": "anxiety disorder, on the oral contraceptive pill"},
        exam_results={"vital_signs": "BP 118/76, HR 118, RR 26, Temp 37.0, SpO2 90%",
                      "leg_exam": "right calf swollen and tender"},
        test_results={"d_dimer": "D-dimer markedly elevated"},
        notes="Anxiety distractor; DVT risk + hypoxia + D-dimer must keep PE alive.",
    ),
    # --- data freshness --------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind11_22_DataFreshness_StaleTroponin", category="data_freshness",
        chief_complaint="crushing chest pain that started just 30 minutes ago",
        demographics={"age": 60, "sex": "male"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "30 minutes ago, ongoing", "associated_symptoms": "diaphoresis, radiates to jaw",
                 "past_medical_history": "a troponin drawn 4 days ago at a checkup was normal"},
        exam_results={"vital_signs": "BP 150/90, HR 98, RR 20, Temp 36.9, SpO2 96%"},
        test_results={"ecg": "hyperacute anterior T waves"},
        notes="A 4-day-old normal troponin must NOT reassure for a 30-minute-old presentation.",
    ),
    # --- wrong / alternate units -----------------------------------------------------------------
    SyntheticCase(
        case_id="Blind11_23_Units_HemoglobinGramsPerLiter", category="unit_safety",
        chief_complaint="black tarry stools and I felt faint standing up",
        demographics={"age": 62, "sex": "male"}, ground_truth_diagnosis="gi_bleeding",
        answers={"onset": "since yesterday", "associated_symptoms": "lightheaded, epigastric pain",
                 "past_medical_history": "daily ibuprofen"},
        exam_results={"vital_signs": "BP 104/64, HR 108, RR 18, Temp 36.6, SpO2 98%"},
        test_results={"hemoglobin": "hemoglobin 68 g/L", "rectal_exam": "melena on the glove"},
        notes="Hemoglobin in g/L (not g/dL) — 68 g/L is severe; must not be read as a normal 68.",
    ),
    SyntheticCase(
        case_id="Blind11_24_Units_CreatinineSI", category="unit_safety",
        chief_complaint="I've barely passed urine for two days and my ankles are swelling",
        demographics={"age": 67, "sex": "male"}, ground_truth_diagnosis="tier2:acute_kidney_injury",
        answers={"onset": "48 hours", "associated_symptoms": "nausea, reduced urine output",
                 "past_medical_history": "started an NSAID last week"},
        exam_results={"vital_signs": "BP 150/92, HR 84, RR 18, Temp 36.7, SpO2 97%"},
        test_results={"creatinine": "creatinine 330 umol/L", "potassium": "potassium 6.0 mmol/L"},
        scoring_expected=False,
        notes="Creatinine in SI (umol/L) — must not be misread as a bare number; Tier-2 target.",
    ),
]
