"""Blind evaluation set v14 (Round D: root-cause chief-complaint generalization hardening).

Why v14: this round audited (never tuned directly against) Blind v13's own critical-recall drop at
an ABSTRACT architectural-failure-category level -- chief-complaint taxonomy coverage gaps, naive
truncation-based morphology, generic-alias shadowing of specific concepts, and a zero-evidence
fallback whose "winning" diagnosis was silently decided by disease-KB file load order -- and fixed
each root cause generically in nova_agent/chief_complaint.py, nova_agent/matching.py,
nova_agent/candidate_generator.py, nova_agent/differential.py, nova_agent/stop_policy.py, and
nova_agent/safety_validator.py (see the reasoning-freeze commit, FINAL_REASONING_SHA
202ed76c4b9bf49fffc62f1ba42f316fcc9f9b9b). Per the blind-set discipline (identical to every prior
round): **Blind v3-v13 are now REFERENCE-ONLY**. This fresh set is authored AFTER that reasoning
freeze and is the untouched check for the current code.

Authoring rules (identical discipline to every prior blind set):
  1. Written AFTER this round's four-defect-class fixes were complete, tested, and frozen.
  2. No sentence/clause/phrase copied from evaluation/cases.py, held_out_cases.py,
     generalization_cases_v2.py, generalization_stress_cases.py, generalization_dev_cases_round_d.py,
     or any blind_cases_v3..v13.py -- every vignette is freshly written. Deliberately does NOT
     reword any of Blind v13's own miss cases merely to prove they now pass -- samples a fresh,
     balanced distribution across the full required category spread instead.
  3. 56 cases -- prefer genuinely distinct cases over a padded larger count (v13 used 52; the 4
     extra here are not padding, they exist specifically to round out diagnosis coverage -- see
     point 3 below). Wider diagnosis spread than v13: touches every one of the 34 Tier-1 KB
     diagnoses at least once, plus 5 Tier-2 long-tail diagnoses and 2 genuinely unknown/OOD
     presentations.
  4. Representative across: common disease, critical emergency, dangerous mimic, benign mimic,
     unseen lay phrasing, objective-evidence-heavy, risk-context-heavy, medication-risk,
     negative-evidence-heavy, atypical presentation, elderly, pediatric, pregnancy, polypharmacy,
     multimorbidity, mixed-language, long-tail Tier-2, UNKNOWN/OOD, retrieval-miss trap, safety
     trap, over-testing trap, premature-diagnosis trap, conflicting evidence, sparse evidence.
     NOT an exhaustive enumeration, NOT tuned to any case.
  5. ground_truth_diagnosis frozen BEFORE the first run (see blind_v14_manifest.json SHA-256).
     Tier-1 targets use knowledge/diseases ids (validated against the real 33-diagnosis KB);
     Tier-2/long-tail use 'tier2:<id>' (validated against the real default ontology catalog),
     scoring_expected=False (excluded from the accuracy denominator, still checked for safe/crash/
     turn-limit behavior); unknown/OOD/sparse-information use 'unknown' + scoring_expected=False.
     FIRST RUN happens exactly once, reported as-is, never re-tuned against.

Hand-authored synthetic vignettes, never real patient data.
"""

from __future__ import annotations

from evaluation.cases import SyntheticCase

BLIND_CASES_V14 = [
    # ================= common (4) =================
    SyntheticCase(
        case_id="Blind14_01_ClassicColdAfterOfficeOutbreak", category="common",
        chief_complaint="stuffy nose, scratchy throat, and a mild cough since Tuesday, half my office has it",
        demographics={"age": 31, "sex": "male"}, ground_truth_diagnosis="viral_uri",
        answers={"associated_symptoms": "low-grade fever, no shortness of breath", "past_medical_history": "none"},
        exam_results={"vital_signs": "BP 118/76, HR 78, RR 14, Temp 37.4, SpO2 99%"},
    ),
    SyntheticCase(
        case_id="Blind14_02_TypicalCystitisYoungWoman", category="common",
        chief_complaint="burning every time I pee and I've been going constantly since yesterday",
        demographics={"age": 24, "sex": "female"}, ground_truth_diagnosis="uncomplicated_cystitis",
        answers={"associated_symptoms": "mild lower belly ache, no fever, no back pain"},
        exam_results={"vital_signs": "BP 114/70, HR 76, RR 14, Temp 36.9, SpO2 99%"},
        test_results={"urinalysis": "positive leukocyte esterase and nitrites"},
    ),
    SyntheticCase(
        case_id="Blind14_03_WeekendPotluckGastro", category="common",
        chief_complaint="throwing up and really watery diarrhea since last night, we all ate at the same potluck",
        demographics={"age": 36, "sex": "male"}, ground_truth_diagnosis="gastroenteritis",
        answers={"associated_symptoms": "crampy stomach pain, no blood in the stool", "duration": "started about 14 hours ago"},
        exam_results={"vital_signs": "BP 110/68, HR 96, RR 16, Temp 37.7, SpO2 99%",
                      "abdominal_exam": "diffuse mild tenderness, no rebound, no guarding"},
    ),
    SyntheticCase(
        case_id="Blind14_04_WorkStressBandHeadache", category="common",
        chief_complaint="tight band of pressure around my whole head, been coming and going all week during crunch time",
        demographics={"age": 38, "sex": "female"}, ground_truth_diagnosis="tension_headache",
        answers={"associated_symptoms": "no nausea, no light or sound sensitivity", "social_history": "big project deadline, barely sleeping"},
        exam_results={"vital_signs": "BP 120/78, HR 72, RR 14, Temp 36.8, SpO2 99%", "neuro_exam": "fully intact"},
    ),

    # ================= critical (6) =================
    SyntheticCase(
        case_id="Blind14_05_SubsternalPressureShoveling", category="critical",
        chief_complaint="a heavy pressure right in the middle of my chest that started while I was shoveling snow",
        demographics={"age": 58, "sex": "male"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "45 minutes ago, constant since", "character": "pressure, not sharp",
                  "associated_symptoms": "sweaty, nauseated, left arm feels heavy",
                  "past_medical_history": "high cholesterol, smoker"},
        exam_results={"vital_signs": "BP 148/92, HR 98, RR 18, Temp 36.9, SpO2 96%"},
        test_results={"ecg": "ST depression in leads V4-V6", "troponin": "elevated troponin"},
    ),
    SyntheticCase(
        case_id="Blind14_06_SuddenOneSidedWeaknessAndSlur", category="critical",
        chief_complaint="his speech suddenly got slurred and his right hand went limp",
        demographics={"age": 70, "sex": "male"}, ground_truth_diagnosis="ischemic_stroke",
        answers={"onset": "sudden, about 25 minutes ago", "associated_symptoms": "right arm and leg feel weak, denies headache",
                  "past_medical_history": "atrial fibrillation, hypertension", "medication": "takes a blood thinner most days"},
        exam_results={"neuro_exam": "right facial droop, right arm and leg weakness, dysarthria",
                      "vital_signs": "BP 176/98, HR 88 irregularly irregular, RR 16, Temp 36.8, SpO2 97%"},
        test_results={"ct_head": "acute infarct in the left MCA territory", "glucose_point_of_care": "102 mg/dL"},
    ),
    SyntheticCase(
        case_id="Blind14_07_ThunderclapHeadacheAtTheGym", category="critical",
        chief_complaint="the worst headache of my entire life hit me all at once mid-workout",
        demographics={"age": 47, "sex": "female"}, ground_truth_diagnosis="subarachnoid_hemorrhage",
        answers={"onset": "instant, like a bolt", "character": "explosive, unlike any headache before",
                  "associated_symptoms": "vomited twice, neck feels stiff", "past_medical_history": "none"},
        exam_results={"meningeal_signs": "positive nuchal rigidity", "vital_signs": "BP 158/94, HR 90, RR 16, Temp 37.0, SpO2 98%",
                      "neuro_exam": "no focal deficit"},
        test_results={"ct_head": "subarachnoid blood in the basal cisterns"},
    ),
    SyntheticCase(
        case_id="Blind14_08_PostSurgicalFeverAndConfusion", category="critical",
        chief_complaint="he's burning up and not making sense today, three days after his knee surgery",
        demographics={"age": 74, "sex": "male"}, ground_truth_diagnosis="sepsis",
        answers={"onset": "started overnight", "associated_symptoms": "shaking chills, confused about where he is",
                  "past_medical_history": "knee replacement three days ago"},
        exam_results={"vital_signs": "BP 88/54, HR 122, RR 26, Temp 39.4, SpO2 92%",
                      "mental_status_exam": "confused, oriented to person only"},
        test_results={"lactate": "elevated lactate, 4.8 mmol/L", "blood_culture": "pending", "cbc": "elevated white blood cell count"},
    ),
    SyntheticCase(
        case_id="Blind14_09_SharpChestPainAfterLongDrive", category="critical",
        chief_complaint="sharp pain in my chest that's worse when I breathe, right after a 9-hour drive home",
        demographics={"age": 49, "sex": "male"}, ground_truth_diagnosis="pulmonary_embolism",
        answers={"onset": "sudden, about an hour ago", "character": "sharp, worse with deep breath",
                  "associated_symptoms": "short of breath, heart racing", "social_history": "just finished a 9-hour road trip"},
        exam_results={"vital_signs": "BP 122/78, HR 116, RR 24, Temp 37.1, SpO2 91%",
                      "extremity_exam": "left calf mildly swollen and tender"},
        test_results={"d_dimer": "elevated D-dimer", "ct_chest_angio": "filling defect in the left pulmonary artery"},
    ),
    SyntheticCase(
        case_id="Blind14_10_FeverStiffNeckCollegeDorm", category="critical",
        chief_complaint="high fever, splitting headache, and his neck feels locked up, his roommate had it last week too",
        demographics={"age": 19, "sex": "male"}, ground_truth_diagnosis="meningitis",
        answers={"onset": "started this morning, worsening fast", "associated_symptoms": "bright light really bothers him, feels foggy",
                  "past_medical_history": "none", "social_history": "lives in a college dorm"},
        exam_results={"meningeal_signs": "positive Kernig's sign", "vital_signs": "BP 108/66, HR 112, RR 20, Temp 39.6, SpO2 97%",
                      "mental_status_exam": "drowsy but arousable"},
        test_results={"lumbar_puncture": "CSF pleocytosis, elevated protein"},
    ),

    # ================= dangerous_mimic (3) =================
    SyntheticCase(
        case_id="Blind14_11_RippingBackPainMistakenForMuscleStrain", category="dangerous_mimic",
        chief_complaint="sudden ripping pain between my shoulder blades, felt like I pulled something lifting furniture",
        demographics={"age": 63, "sex": "male"}, ground_truth_diagnosis="aortic_dissection",
        answers={"onset": "instant, while moving a couch", "character": "tearing, migrated from chest to back",
                  "past_medical_history": "poorly controlled high blood pressure for years"},
        exam_results={"vital_signs": "BP 192/68 right arm, 148/70 left arm, HR 96, RR 18, Temp 36.9, SpO2 97%",
                      "cardiac_auscultation": "diastolic murmur heard"},
        test_results={"ct_aorta": "intimal flap in the descending aorta", "cxr": "widened mediastinum"},
    ),
    SyntheticCase(
        case_id="Blind14_12_LatePeriodMistakenForStomachBug", category="dangerous_mimic",
        chief_complaint="nauseous and crampy on one side, figured it was the same stomach bug going around",
        demographics={"age": 26, "sex": "female"}, ground_truth_diagnosis="ectopic_pregnancy",
        answers={"onset": "on and off for a day", "associated_symptoms": "mild spotting, denies fever, denies diarrhea",
                  "social_history": "sexually active, period is about six weeks late"},
        exam_results={"abdominal_exam": "right adnexal tenderness, no rebound", "vital_signs": "BP 102/64, HR 108, RR 16, Temp 36.8, SpO2 99%"},
        test_results={"beta_hcg": "positive beta-hCG", "pelvic_ultrasound": "no intrauterine pregnancy, right adnexal mass"},
    ),
    SyntheticCase(
        case_id="Blind14_13_AsthmaFlareThatWasActuallyCollapsedLung", category="dangerous_mimic",
        chief_complaint="sudden trouble breathing after a hard fall skateboarding, figured it was his asthma acting up",
        demographics={"age": 22, "sex": "male"}, ground_truth_diagnosis="tension_pneumothorax",
        answers={"onset": "right after the fall, about 15 minutes ago", "associated_symptoms": "sharp right-sided chest pain",
                  "past_medical_history": "mild asthma since childhood"},
        exam_results={"lung_auscultation": "absent breath sounds on the right side", "vital_signs": "BP 88/56, HR 128, RR 32, Temp 36.9, SpO2 84%",
                      "general_appearance": "tracheal deviation to the left, distended neck veins"},
        test_results={},
    ),

    # ================= benign_mimic (3) =================
    SyntheticCase(
        case_id="Blind14_14_RibCagePainAfterGymDay", category="benign_mimic",
        chief_complaint="sharp pain on the left side of my chest, worse when I press on it, day after a heavy gym session",
        demographics={"age": 27, "sex": "male"}, ground_truth_diagnosis="musculoskeletal_chest_pain",
        answers={"onset": "started this morning, gradual", "character": "sharp, reproducible with pressing",
                  "associated_symptoms": "denies shortness of breath, denies sweating", "social_history": "did a heavy chest workout yesterday"},
        exam_results={"vital_signs": "BP 118/74, HR 72, RR 14, Temp 36.8, SpO2 99%",
                      "cardiac_auscultation": "reproducible tenderness on palpation of the chest wall"},
        test_results={"ecg": "normal sinus rhythm, no ST changes"},
    ),
    SyntheticCase(
        case_id="Blind14_15_RoomSpinsWhenRollingOverInBed", category="benign_mimic",
        chief_complaint="the room spins for a few seconds every time I roll over in bed",
        demographics={"age": 55, "sex": "female"}, ground_truth_diagnosis="bppv",
        answers={"onset": "started three days ago", "duration": "each episode lasts under a minute",
                  "associated_symptoms": "denies hearing loss, denies weakness, denies slurred speech"},
        exam_results={"neuro_exam": "no focal neurological deficit", "vital_signs": "BP 122/78, HR 74, RR 14, Temp 36.7, SpO2 99%"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind14_16_RacingHeartBeforeBigPresentation", category="benign_mimic",
        chief_complaint="my heart started pounding and I felt like I couldn't breathe right before my big presentation",
        demographics={"age": 29, "sex": "female"}, ground_truth_diagnosis="panic_attack",
        answers={"onset": "sudden, 20 minutes before the meeting", "associated_symptoms": "tingling in her hands, felt like she was going to die, denies chest pressure",
                  "past_medical_history": "similar episodes before big deadlines in the past"},
        exam_results={"vital_signs": "BP 128/80, HR 112, RR 22, Temp 36.9, SpO2 99%", "cardiac_auscultation": "regular rhythm, no murmur"},
        test_results={"ecg": "sinus tachycardia, no ischemic changes"},
    ),

    # ================= unseen_lay_phrasing (2) =================
    SyntheticCase(
        case_id="Blind14_17_LayLanguagePneumonia", category="unseen_lay_phrasing",
        chief_complaint="been hacking up gunk for days and now I'm burning up and my side hurts when I breathe",
        demographics={"age": 67, "sex": "male"}, ground_truth_diagnosis="pneumonia",
        answers={"onset": "cough started five days ago, fever and side pain since yesterday",
                  "associated_symptoms": "bringing up yellow-green gunk"},
        exam_results={"lung_auscultation": "crackles heard at the right base", "vital_signs": "BP 128/80, HR 100, RR 22, Temp 38.9, SpO2 93%"},
        test_results={"cxr": "right lower lobe infiltrate"},
    ),
    SyntheticCase(
        case_id="Blind14_18_LayLanguageDKA", category="unseen_lay_phrasing",
        chief_complaint="been peeing constantly, so thirsty I can't keep up, and my breath smells weird according to my wife",
        demographics={"age": 24, "sex": "male"}, ground_truth_diagnosis="diabetic_ketoacidosis",
        answers={"onset": "getting worse over the last two days", "associated_symptoms": "belly hurts, threw up twice, breathing fast",
                  "past_medical_history": "type 1 diabetes, ran out of insulin last week"},
        exam_results={"vital_signs": "BP 104/64, HR 118, RR 30, Temp 37.2, SpO2 98%", "general_appearance": "fruity-smelling breath, breathing deep and fast"},
        test_results={"glucose_point_of_care": "512 mg/dL", "ketones": "large ketones", "abg": "metabolic acidosis"},
    ),

    # ================= objective_evidence_heavy (2) =================
    SyntheticCase(
        case_id="Blind14_19_EpigastricPainConfirmedByLipase", category="objective_evidence_heavy",
        chief_complaint="steady pain right in the middle of my upper belly that goes straight through to my back",
        demographics={"age": 44, "sex": "male"}, ground_truth_diagnosis="acute_pancreatitis",
        answers={"onset": "12 hours ago, constant", "associated_symptoms": "nausea, vomited once, worse after eating a fatty dinner",
                  "social_history": "drinks heavily most weekends"},
        exam_results={"abdominal_exam": "epigastric tenderness, no rebound", "vital_signs": "BP 118/76, HR 98, RR 18, Temp 37.6, SpO2 98%"},
        test_results={"lipase": "lipase markedly elevated, 5x upper limit of normal"},
    ),
    SyntheticCase(
        case_id="Blind14_20_FlankPainConfirmedByUrineWorkup", category="objective_evidence_heavy",
        chief_complaint="pain in my lower back on one side and I've felt feverish and shaky since yesterday",
        demographics={"age": 34, "sex": "female"}, ground_truth_diagnosis="pyelonephritis",
        answers={"onset": "started yesterday, worsening", "associated_symptoms": "burning when urinating, chills"},
        exam_results={"vital_signs": "BP 104/64, HR 108, RR 18, Temp 39.0, SpO2 98%",
                      "costovertebral_tenderness": "positive on the right"},
        test_results={"urinalysis": "positive leukocyte esterase and nitrites", "cbc": "elevated white blood cell count"},
    ),

    # ================= risk_context_heavy (2) =================
    SyntheticCase(
        case_id="Blind14_21_KnownAfibWithNewPalpitations", category="risk_context_heavy",
        chief_complaint="my heart feels like it's fluttering irregularly, on and off for the last hour",
        demographics={"age": 68, "sex": "female"}, ground_truth_diagnosis="cardiac_arrhythmia",
        answers={"onset": "started an hour ago, comes and goes", "associated_symptoms": "mild lightheadedness, denies chest pain",
                  "past_medical_history": "known atrial fibrillation, hyperthyroidism"},
        exam_results={"cardiac_auscultation": "irregularly irregular rhythm", "vital_signs": "BP 132/84, HR 138 irregular, RR 18, Temp 36.8, SpO2 98%"},
        test_results={"ecg": "irregularly irregular rhythm, no discrete P waves"},
    ),
    SyntheticCase(
        case_id="Blind14_22_PriorStonesWithNewFlankPain", category="risk_context_heavy",
        chief_complaint="that same excruciating pain from my side down to my groin that I got with my kidney stone two years ago",
        demographics={"age": 41, "sex": "male"}, ground_truth_diagnosis="nephrolithiasis",
        answers={"onset": "sudden, an hour ago, comes in waves", "associated_symptoms": "blood-tinged urine, restless, can't get comfortable",
                  "past_medical_history": "kidney stones twice before"},
        exam_results={"vital_signs": "BP 138/86, HR 102, RR 18, Temp 37.0, SpO2 99%", "costovertebral_tenderness": "positive on the left"},
        test_results={"urinalysis": "microscopic hematuria"},
    ),

    # ================= medication_risk (2) =================
    SyntheticCase(
        case_id="Blind14_23_SulfonylureaMissedMealConfusion", category="medication_risk",
        chief_complaint="he's been acting strange and hard to wake up this afternoon",
        demographics={"age": 79, "sex": "male"}, ground_truth_diagnosis="hypoglycemia",
        answers={"onset": "family noticed about 30 minutes ago", "associated_symptoms": "sweaty, trembling",
                  "past_medical_history": "type 2 diabetes", "medication": "takes glyburide, skipped lunch today"},
        exam_results={"mental_status_exam": "somnolent, arousable, confused", "vital_signs": "BP 122/76, HR 92, RR 16, Temp 36.5, SpO2 98%"},
        test_results={"glucose_point_of_care": "38 mg/dL"},
    ),
    SyntheticCase(
        case_id="Blind14_24_AnticoagulantBlackStools", category="medication_risk",
        chief_complaint="my stools have been really dark and tarry-looking for a couple days, and I feel wiped out",
        demographics={"age": 71, "sex": "female"}, ground_truth_diagnosis="gi_bleeding",
        answers={"onset": "noticed the stool color two days ago", "associated_symptoms": "lightheaded when standing, denies vomiting blood",
                  "past_medical_history": "atrial fibrillation", "medication": "takes apixaban"},
        exam_results={"vital_signs": "BP 96/60, HR 112, RR 18, Temp 36.8, SpO2 98%", "abdominal_exam": "mild diffuse tenderness"},
        test_results={"cbc": "hemoglobin drop from baseline", "fecal_occult_blood": "positive fecal occult blood"},
    ),

    # ================= negative_evidence_heavy (2) =================
    SyntheticCase(
        case_id="Blind14_25_RightLowerAbdPainWithReassuringLabsStillAppendicitis", category="negative_evidence_heavy",
        chief_complaint="woke up with a dull ache in the middle of my gut, and now it's a sharp stab down on my right side",
        demographics={"age": 20, "sex": "male"}, ground_truth_diagnosis="appendicitis",
        answers={"onset": "about 10 hours ago, has shifted location overnight", "associated_symptoms": "no appetite, mild nausea, denies vomiting, denies diarrhea"},
        exam_results={"abdominal_exam": "right lower quadrant tenderness, positive rebound", "vital_signs": "BP 122/78, HR 94, RR 16, Temp 37.8, SpO2 99%"},
        test_results={"cbc": "mildly elevated white blood cell count"},
    ),
    SyntheticCase(
        case_id="Blind14_26_DizzyOnStandingAllOtherFindingsNegative", category="negative_evidence_heavy",
        chief_complaint="lightheaded every time I stand up from the couch, been happening for two days",
        demographics={"age": 76, "sex": "male"}, ground_truth_diagnosis="orthostatic_hypotension",
        answers={"onset": "two days ago", "relieving": "goes away within seconds of sitting back down",
                  "associated_symptoms": "denies chest pain, denies palpitations, denies slurred speech, denies focal weakness, denies severe headache",
                  "medication": "started a new water pill last week"},
        exam_results={"vital_signs": "BP 94/58 standing, 130/80 sitting, HR 84, RR 16, Temp 36.7, SpO2 98%", "neuro_exam": "no focal neurological deficit"},
        test_results={},
    ),

    # ================= atypical_presentation (2) =================
    SyntheticCase(
        case_id="Blind14_27_SilentMICInDiabeticWoman", category="atypical_presentation",
        chief_complaint="just really tired and a bit nauseated since this morning, nothing dramatic",
        demographics={"age": 66, "sex": "female"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "gradual since waking up", "associated_symptoms": "some jaw discomfort, denies classic chest pressure",
                  "past_medical_history": "type 2 diabetes, high blood pressure"},
        exam_results={"vital_signs": "BP 152/94, HR 92, RR 18, Temp 36.9, SpO2 96%"},
        test_results={"ecg": "ST depression in the inferior leads", "troponin": "elevated troponin"},
    ),
    SyntheticCase(
        case_id="Blind14_28_IsolatedImbalanceStroke", category="atypical_presentation",
        chief_complaint="just feels off-balance and a little clumsy walking today, nothing else really",
        demographics={"age": 69, "sex": "female"}, ground_truth_diagnosis="ischemic_stroke",
        answers={"onset": "sudden, about two hours ago", "associated_symptoms": "words felt slightly slurred to her, denies headache, denies chest pain",
                  "past_medical_history": "atrial fibrillation, hypertension"},
        exam_results={"neuro_exam": "mild ataxia, subtle dysarthria", "vital_signs": "BP 168/92, HR 86 irregularly irregular, RR 16, Temp 36.8, SpO2 97%"},
        test_results={"ct_head": "acute infarct in the cerebellum", "glucose_point_of_care": "96 mg/dL"},
    ),

    # ================= elderly (1) =================
    SyntheticCase(
        case_id="Blind14_29_ElderlyPneumoniaWithoutFever", category="elderly",
        chief_complaint="grandma seems more confused than usual and won't eat much today",
        demographics={"age": 88, "sex": "female"}, ground_truth_diagnosis="pneumonia",
        answers={"onset": "gradually worse over two days", "associated_symptoms": "mild cough, denies fever noticed at home",
                  "past_medical_history": "mild dementia at baseline"},
        exam_results={"lung_auscultation": "crackles at the left base", "vital_signs": "BP 110/68, HR 102, RR 24, Temp 37.6, SpO2 90%",
                      "mental_status_exam": "more confused than her documented baseline"},
        test_results={"cxr": "left lower lobe consolidation", "cbc": "elevated white blood cell count"},
    ),

    # ================= pediatric (2) =================
    SyntheticCase(
        case_id="Blind14_30_ToddlerColdFromDaycare", category="pediatric",
        chief_complaint="my daughter has a runny nose and a little cough, half her daycare class is sick too",
        demographics={"age": 3, "sex": "female"}, ground_truth_diagnosis="viral_uri",
        answers={"associated_symptoms": "low fever, still eating and playing normally", "past_medical_history": "none"},
        exam_results={"vital_signs": "BP 96/60, HR 108, RR 22, Temp 37.9, SpO2 99%", "lung_auscultation": "clear bilaterally"},
    ),
    SyntheticCase(
        case_id="Blind14_31_TeenAsthmaFlareAfterSoccer", category="pediatric",
        chief_complaint="he's wheezing and can't catch his breath after soccer practice, forgot his inhaler",
        demographics={"age": 14, "sex": "male"}, ground_truth_diagnosis="asthma_copd_exacerbation",
        answers={"onset": "during practice, about 30 minutes ago", "associated_symptoms": "chest feels tight",
                  "past_medical_history": "known asthma since childhood"},
        exam_results={"lung_auscultation": "diffuse expiratory wheeze, prolonged expiration", "vital_signs": "BP 118/72, HR 112, RR 26, Temp 37.0, SpO2 94%"},
        test_results={},
    ),

    # ================= pregnancy (1) =================
    SyntheticCase(
        case_id="Blind14_32_PregnantWithFlankPainAndFever", category="pregnancy",
        chief_complaint="I'm pregnant and I've had a fever and pain on my right side under my ribs since this morning",
        demographics={"age": 28, "sex": "female"}, ground_truth_diagnosis="pyelonephritis",
        answers={"onset": "since this morning, worsening", "associated_symptoms": "burning with urination, chills",
                  "past_medical_history": "20 weeks pregnant, otherwise healthy"},
        exam_results={"vital_signs": "BP 108/68, HR 104, RR 18, Temp 38.7, SpO2 98%", "costovertebral_tenderness": "positive on the right"},
        test_results={"urinalysis": "positive leukocyte esterase and nitrites"},
    ),

    # ================= polypharmacy (1) =================
    SyntheticCase(
        case_id="Blind14_33_ACEInhibitorPlusPotassiumSupplement", category="polypharmacy",
        chief_complaint="he's felt weak all over and his heart feels like it's skipping since yesterday",
        demographics={"age": 77, "sex": "male"}, ground_truth_diagnosis="severe_electrolyte_disorder",
        answers={"onset": "gradual since yesterday", "associated_symptoms": "generalized weakness, denies chest pain",
                  "past_medical_history": "chronic kidney disease, hypertension",
                  "medication": "takes lisinopril and a potassium supplement his cardiologist prescribed"},
        exam_results={"cardiac_auscultation": "irregular rhythm noted", "vital_signs": "BP 128/80, HR 52, RR 16, Temp 36.8, SpO2 98%"},
        test_results={"bmp": "potassium 7.1", "ecg": "peaked T waves, widened QRS"},
    ),

    # ================= multimorbidity (1) =================
    SyntheticCase(
        case_id="Blind14_34_DiabeticCKDPatientWithChestTightness", category="multimorbidity",
        chief_complaint="a tightness across my chest that started while I was walking to the mailbox",
        demographics={"age": 64, "sex": "male"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "20 minutes ago, brought on by walking", "associated_symptoms": "short of breath, mild nausea",
                  "past_medical_history": "type 2 diabetes, chronic kidney disease, hypertension"},
        exam_results={"vital_signs": "BP 156/94, HR 96, RR 18, Temp 36.9, SpO2 96%"},
        test_results={"ecg": "ST depression in the lateral leads", "troponin": "elevated troponin"},
    ),

    # ================= mixed_language (2) =================
    SyntheticCase(
        case_id="Blind14_35_KoreanMixedChestPain", category="mixed_language",
        chief_complaint="가슴에 crushing pressure 느낌이 있고 땀이 나요",
        demographics={"age": 55, "sex": "male"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "30분 전부터, sudden onset", "associated_symptoms": "diaphoresis, nausea, left arm에 heaviness",
                  "past_medical_history": "hypertension, smoker"},
        exam_results={"vital_signs": "BP 150/92, HR 100, RR 18, Temp 36.9, SpO2 96%"},
        test_results={"ecg": "ST elevation in the anterior leads", "troponin": "elevated troponin"},
    ),
    SyntheticCase(
        case_id="Blind14_36_JapaneseMixedAbdominalPain", category="mixed_language",
        chief_complaint="右下腹部に sharp pain があって、昨日から始まりました",
        demographics={"age": 25, "sex": "female"}, ground_truth_diagnosis="appendicitis",
        answers={"onset": "昨日から, migrated to the right lower quadrant", "associated_symptoms": "食欲不振, mild nausea, denies vomiting"},
        exam_results={"abdominal_exam": "right lower quadrant tenderness, positive rebound", "vital_signs": "BP 116/74, HR 92, RR 16, Temp 37.9, SpO2 99%"},
        test_results={"cbc": "mildly elevated white blood cell count"},
    ),

    # ================= long_tail Tier-2 (5) =================
    SyntheticCase(
        case_id="Blind14_37_LongTailCholecystitis", category="long_tail", scoring_expected=False,
        chief_complaint="sharp pain under my right ribs that comes on after I eat fried food, worse tonight after dinner",
        demographics={"age": 46, "sex": "female"}, ground_truth_diagnosis="tier2:cholecystitis",
        answers={"onset": "about two hours after dinner, worsening", "associated_symptoms": "nausea, vomited once, fever"},
        exam_results={"abdominal_exam": "right upper quadrant tenderness, positive Murphy's sign", "vital_signs": "BP 124/78, HR 98, RR 18, Temp 38.2, SpO2 98%"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind14_38_LongTailBowelObstruction", category="long_tail", scoring_expected=False,
        chief_complaint="crampy belly pain, bloating, and I haven't passed gas or a bowel movement in two days",
        demographics={"age": 72, "sex": "male"}, ground_truth_diagnosis="tier2:bowel_obstruction",
        answers={"onset": "two days ago, worsening", "associated_symptoms": "repeated vomiting, abdomen feels very bloated",
                  "past_medical_history": "abdominal surgery years ago"},
        exam_results={"abdominal_exam": "distended, high-pitched bowel sounds", "vital_signs": "BP 118/72, HR 104, RR 18, Temp 37.2, SpO2 98%"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind14_39_LongTailShingles", category="long_tail", scoring_expected=False,
        chief_complaint="burning pain along one side of my ribs and a rash of little blisters showed up there today",
        demographics={"age": 68, "sex": "female"}, ground_truth_diagnosis="tier2:herpes_zoster",
        answers={"onset": "pain for three days, rash appeared today", "associated_symptoms": "burning, tingling along the rash line"},
        exam_results={"skin_exam": "grouped vesicles on an erythematous base in a band on one side of the chest"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind14_40_LongTailDVT", category="long_tail", scoring_expected=False,
        chief_complaint="my calf has been swollen, warm, and sore for two days, no injury I can think of",
        demographics={"age": 59, "sex": "female"}, ground_truth_diagnosis="tier2:deep_vein_thrombosis",
        answers={"onset": "two days ago, gradually worsening", "associated_symptoms": "denies chest pain, denies shortness of breath",
                  "social_history": "long flight home from overseas last week"},
        exam_results={"extremity_exam": "left calf swelling, warmth, and tenderness, positive Homan's sign"},
        test_results={"d_dimer": "elevated D-dimer"},
    ),
    SyntheticCase(
        case_id="Blind14_41_LongTailPericarditis", category="long_tail", scoring_expected=False,
        chief_complaint="sharp chest pain that gets better when I lean forward, started after a cold last week",
        demographics={"age": 32, "sex": "male"}, ground_truth_diagnosis="tier2:pericarditis",
        answers={"onset": "two days ago", "character": "sharp, worse lying flat, better leaning forward",
                  "past_medical_history": "had a viral cold about a week ago"},
        exam_results={"cardiac_auscultation": "pericardial friction rub", "vital_signs": "BP 120/76, HR 88, RR 16, Temp 37.5, SpO2 99%"},
        test_results={"ecg": "diffuse ST elevation with PR depression"},
    ),

    # ================= unknown_ood (2) =================
    SyntheticCase(
        case_id="Blind14_42_TrulyVagueMalaise", category="unknown_ood", scoring_expected=False,
        chief_complaint="I just don't feel right, hard to put into words, been like this a few days",
        demographics={"age": 40, "sex": "male"}, ground_truth_diagnosis="unknown",
        answers={}, exam_results={}, test_results={},
    ),
    SyntheticCase(
        case_id="Blind14_43_NonMedicalRamblingComplaint", category="unknown_ood", scoring_expected=False,
        chief_complaint="my horoscope said today would be rough and honestly my whole week has felt off",
        demographics={"age": 35, "sex": "female"}, ground_truth_diagnosis="unknown",
        answers={"associated_symptoms": "denies any specific symptom"}, exam_results={}, test_results={},
    ),

    # ================= retrieval_miss_trap (2) =================
    SyntheticCase(
        case_id="Blind14_44_VagueComplaintDKAOnlyOnLabs", category="retrieval_miss_trap",
        chief_complaint="he just seems really out of it and breathing kind of heavy today, hard to explain",
        demographics={"age": 17, "sex": "male"}, ground_truth_diagnosis="diabetic_ketoacidosis",
        answers={"onset": "gradual over the last day", "associated_symptoms": "family noticed him drinking water nonstop, denies fever",
                  "past_medical_history": "type 1 diabetes"},
        exam_results={"vital_signs": "BP 100/62, HR 122, RR 30, Temp 37.0, SpO2 98%", "general_appearance": "breathing deep and fast"},
        test_results={"glucose_point_of_care": "488 mg/dL", "ketones": "large ketones", "abg": "metabolic acidosis"},
    ),
    SyntheticCase(
        case_id="Blind14_45_VagueChestComplaintDissectionOnImaging", category="retrieval_miss_trap",
        chief_complaint="something feels really wrong in my chest and upper back, can't quite describe it",
        demographics={"age": 66, "sex": "male"}, ground_truth_diagnosis="aortic_dissection",
        answers={"onset": "sudden, an hour ago", "associated_symptoms": "denies classic sharp or crushing pain, just a deep, severe discomfort",
                  "past_medical_history": "longstanding poorly controlled hypertension"},
        exam_results={"vital_signs": "BP 188/72 right arm, 142/68 left arm, HR 92, RR 18, Temp 36.9, SpO2 97%"},
        test_results={"ct_aorta": "intimal flap in the descending aorta", "cxr": "widened mediastinum"},
    ),

    # ================= safety_trap (1) =================
    SyntheticCase(
        case_id="Blind14_46_ReassuringHeadacheHistoryMaskingSAH", category="safety_trap",
        chief_complaint="a bad headache, similar to migraines I've had before, but this one feels worse",
        demographics={"age": 43, "sex": "female"}, ground_truth_diagnosis="subarachnoid_hemorrhage",
        answers={"onset": "sudden, reached full intensity within seconds", "character": "the worst one I've ever had, unlike my usual migraines",
                  "associated_symptoms": "neck stiffness, vomited once", "past_medical_history": "history of migraines for years"},
        exam_results={"meningeal_signs": "mild nuchal rigidity", "vital_signs": "BP 152/90, HR 86, RR 16, Temp 36.9, SpO2 98%",
                      "neuro_exam": "no focal deficit"},
        test_results={"ct_head": "subarachnoid blood near the circle of Willis"},
    ),

    # ================= over_testing_trap (2) =================
    SyntheticCase(
        case_id="Blind14_47_ClassicMigraineNotSAH", category="over_testing_trap",
        chief_complaint="a throbbing headache on one side with some light sensitivity, I get these a few times a year",
        demographics={"age": 34, "sex": "female"}, ground_truth_diagnosis="migraine",
        answers={"character": "throbbing, one-sided, feels the same as my usual migraines", "associated_symptoms": "nausea, sees shimmering lights before it starts",
                  "family_history": "mother also gets migraines"},
        exam_results={"neuro_exam": "no focal neurological deficit", "vital_signs": "BP 118/76, HR 74, RR 14, Temp 36.8, SpO2 99%"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind14_48_ClassicBronchitisNotPneumonia", category="over_testing_trap",
        chief_complaint="a nagging cough that's brought up some mucus for about a week, started after a cold",
        demographics={"age": 30, "sex": "male"}, ground_truth_diagnosis="acute_bronchitis",
        answers={"duration": "about a week now, started after a cold", "associated_symptoms": "chest feels sore from coughing, denies shortness of breath at rest, denies high fever",
                  "social_history": "doesn't smoke"},
        exam_results={"lung_auscultation": "clear to mildly coarse breath sounds, no focal consolidation", "vital_signs": "BP 116/74, HR 82, RR 16, Temp 37.2, SpO2 98%"},
        test_results={},
    ),

    # ================= premature_diagnosis_trap (2) =================
    SyntheticCase(
        case_id="Blind14_49_EarlyAppendicitisLooksLikeGastro", category="premature_diagnosis_trap",
        chief_complaint="nausea and some vague belly discomfort since this morning, thought it might just be something I ate",
        demographics={"age": 23, "sex": "male"}, ground_truth_diagnosis="appendicitis",
        answers={"onset": "this morning, felt centered near his navel at first", "associated_symptoms": "no appetite, the ache has drifted toward his right hip area over the last few hours"},
        exam_results={"abdominal_exam": "right lower quadrant tenderness developing, mild rebound", "vital_signs": "BP 120/76, HR 90, RR 16, Temp 37.6, SpO2 99%"},
        test_results={"cbc": "mildly elevated white blood cell count"},
    ),
    SyntheticCase(
        case_id="Blind14_50_EarlyHyperkalemiaLooksLikeSimpleWeakness", category="premature_diagnosis_trap",
        chief_complaint="just feeling generally weak the last day, nothing else really going on",
        demographics={"age": 62, "sex": "male"}, ground_truth_diagnosis="severe_electrolyte_disorder",
        answers={"onset": "gradual over the last day", "past_medical_history": "chronic kidney disease",
                  "medication": "recently started a potassium-sparing blood pressure medication"},
        exam_results={"cardiac_auscultation": "regular rhythm currently", "vital_signs": "BP 138/86, HR 58, RR 16, Temp 36.8, SpO2 98%"},
        test_results={"bmp": "potassium 6.9", "ecg": "peaked T waves"},
    ),

    # ================= conflicting_evidence (1) =================
    SyntheticCase(
        case_id="Blind14_51_ChestPainNormalECGHighRiskHistory", category="conflicting_evidence",
        chief_complaint="a squeezing feeling in my chest that started an hour ago while I was at my desk",
        demographics={"age": 60, "sex": "male"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "an hour ago, constant", "associated_symptoms": "mild nausea, sweaty",
                  "past_medical_history": "prior heart attack four years ago, diabetes, smoker"},
        exam_results={"vital_signs": "BP 142/88, HR 90, RR 16, Temp 36.9, SpO2 97%"},
        test_results={"ecg": "normal sinus rhythm, no acute ST changes", "troponin": "elevated troponin"},
    ),

    # ================= sparse_evidence (1) =================
    SyntheticCase(
        case_id="Blind14_52_MinimalInformationGastro", category="sparse_evidence",
        chief_complaint="stomach's been upset since last night, some diarrhea",
        demographics={"age": 33, "sex": "female"}, ground_truth_diagnosis="gastroenteritis",
        answers={"associated_symptoms": "mild cramping, denies blood in stool, denies high fever"},
        exam_results={"vital_signs": "BP 114/72, HR 84, RR 16, Temp 37.3, SpO2 99%"},
        test_results={},
    ),

    # ================= additional critical/benign_mimic (4): diagnosis-spread coverage =============
    # These 4 round out Tier-1 diagnosis coverage to all 34 KB diagnoses (the 52 cases above already
    # touch 30 of them) -- added rather than displacing any of the 52 above, per "prefer genuinely
    # distinct cases over a padded count" (each is its own independent vignette, not filler).
    SyntheticCase(
        case_id="Blind14_53_PerforatedUlcerRigidAbdomen", category="critical",
        chief_complaint="sudden, excruciating pain across my whole stomach, it's never hurt like this before",
        demographics={"age": 57, "sex": "male"}, ground_truth_diagnosis="acute_abdomen",
        answers={"onset": "instant, about 40 minutes ago", "associated_symptoms": "can't move without agony, denies diarrhea",
                  "past_medical_history": "chronic NSAID use for back pain"},
        exam_results={"abdominal_exam": "rigid abdomen, diffuse guarding, positive rebound", "vital_signs": "BP 100/62, HR 118, RR 22, Temp 37.9, SpO2 97%"},
        test_results={"cxr": "free air under the diaphragm"},
    ),
    SyntheticCase(
        case_id="Blind14_54_PeanutReactionAtRestaurant", category="critical",
        chief_complaint="my throat feels like it's closing up and I'm covered in hives, I just ate at a new restaurant",
        demographics={"age": 26, "sex": "female"}, ground_truth_diagnosis="anaphylaxis",
        answers={"onset": "sudden, within minutes of eating", "associated_symptoms": "lips and tongue feel swollen, wheezing, denies prior reactions like this",
                  "social_history": "possible peanut exposure at the restaurant"},
        exam_results={"vital_signs": "BP 84/52, HR 128, RR 28, Temp 36.9, SpO2 91%", "skin_exam": "diffuse urticaria", "lung_auscultation": "audible wheeze"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind14_55_BurningChestAfterBigMeals", category="benign_mimic",
        chief_complaint="a burning feeling in my chest that keeps coming back after I eat big meals or lie down",
        demographics={"age": 39, "sex": "male"}, ground_truth_diagnosis="gerd",
        answers={"onset": "recurring for a few weeks, worse at night", "associated_symptoms": "sour taste in his mouth, denies shortness of breath, denies sweating",
                  "aggravating": "worse after large or spicy meals and lying down"},
        exam_results={"vital_signs": "BP 122/78, HR 74, RR 14, Temp 36.8, SpO2 99%"},
        test_results={"ecg": "normal sinus rhythm, no ST changes"},
    ),
    SyntheticCase(
        case_id="Blind14_56_FaintedAtTheSightOfBlood", category="benign_mimic",
        chief_complaint="I felt hot and nauseated and then blacked out for a few seconds while getting my blood drawn",
        demographics={"age": 21, "sex": "male"}, ground_truth_diagnosis="vasovagal_syncope",
        answers={"onset": "sudden, during the blood draw", "associated_symptoms": "felt warm and queasy right before, denies chest pain, denies palpitations before the episode",
                  "relieving": "came right back around once he was laid flat"},
        exam_results={"vital_signs": "BP 112/70, HR 68, RR 14, Temp 36.7, SpO2 99%", "neuro_exam": "no focal neurological deficit"},
        test_results={"ecg": "normal sinus rhythm"},
    ),
]
