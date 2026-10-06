"""Blind evaluation set v15 (Round E: generic-word/short-alias fuzzy-match hardening, context-aware
critical safety activation, diagnostic-specificity-vs-generic-severity separation, bounded
multilingual concept normalization, and residual morphology-truncation removal).

Why v15: this round audited (never tuned directly against) Blind v14's own critical misses and
Round D's own remaining architectural blind spots at an ABSTRACT failure-category level -- weak
lexical overlap on generic/relational words, a short KB alias (e.g. "PE") matching as a raw
substring inside an unrelated word, generic physiologic severity (tachycardia/hypotension/fever)
counting as if it were disease-specific evidence, a dangerous diagnosis reachable only through an
atypical/vague presentation with no unconditional safety-net coverage, and Japanese-mixed input not
reaching the same routing concepts English does -- and fixed each root cause generically in
nova_agent/matching.py, nova_agent/contextual_safety.py (new), nova_agent/candidate_generator.py,
nova_agent/differential.py, nova_agent/severity_evidence.py, nova_agent/multilingual_concepts.py
(new), nova_agent/chief_complaint.py, nova_agent/safety.py, nova_agent/safety_validator.py,
nova_agent/state.py, nova_agent/orchestrator.py, nova_agent/config.py, and competition/{schema,
adapter}.py (see the reasoning-freeze commit, FINAL_REASONING_SHA
659c7dc6cdb484dc7dc351a39c52eea71a5b621f). Per the blind-set discipline (identical to every prior
round): **Blind v3-v14 are now REFERENCE-ONLY**. This fresh set is authored AFTER that reasoning
freeze and is the untouched check for the current code.

Authoring rules (identical discipline to every prior blind set):
  1. Written AFTER this round's five-defect-class fixes were complete, tested, and frozen.
  2. No sentence/clause/phrase copied from evaluation/cases.py, held_out_cases.py,
     generalization_cases_v2.py, generalization_stress_cases.py, generalization_dev_cases_round_d.py,
     generalization_dev_cases_round_e.py, or any blind_cases_v3..v14.py -- every vignette is freshly
     written. Deliberately does NOT reword any of Blind v14's own miss cases merely to prove they now
     pass -- samples a fresh, balanced distribution across the full required category spread instead.
  3. 61 cases -- prefer genuinely distinct, independent cases over a padded larger count (spec:
     "prefer 60 high-quality independent cases over padding"; 60 core cases plus one appended case
     purely to reach full 34/34 Tier-1 diagnosis coverage -- vasovagal_syncope, otherwise untouched
     -- never padding toward a round number). Touches all 34 Tier-1 knowledge-base diagnoses at
     least once, plus 4 Tier-2 long-tail diagnoses and 2 genuinely unknown/OOD presentations.
  4. Representative across the full required spread: common, critical, dangerous mimic, benign
     mimic, unseen lay phrasing, objective-evidence-heavy, risk-context-heavy, medication-risk,
     negative-evidence-heavy, atypical presentation, elderly, pediatric, pregnancy, polypharmacy,
     multimorbidity, multilingual Korean, multilingual Japanese, mixed-language, reproductive-age
     emergency, specific-evidence-vs-generic-severity conflict, fuzzy-phrase-collision trap,
     long-tail Tier-2, UNKNOWN/OOD, retrieval-miss trap, routing trap, over-testing trap,
     premature-diagnosis trap, late-diagnosis trap, conflicting evidence, sparse evidence. NOT an
     exhaustive enumeration, NOT tuned to any case.
  5. ground_truth_diagnosis frozen BEFORE the first run (see blind_v15_manifest.json SHA-256).
     Tier-1 targets use knowledge/diseases ids (validated against the real 34-diagnosis KB); Tier-2/
     long-tail use 'tier2:<id>' (validated against the real default ontology catalog),
     scoring_expected=False (excluded from the accuracy denominator, still checked for safe/crash/
     turn-limit behavior); unknown/OOD/sparse-information use 'unknown' + scoring_expected=False.
     FIRST RUN happens exactly once, reported as-is, never re-tuned against.

Hand-authored synthetic vignettes, never real patient data.
"""

from __future__ import annotations

from evaluation.cases import SyntheticCase

BLIND_CASES_V15 = [
    # ================= common (4) =================
    SyntheticCase(
        case_id="Blind15_01_SharedOfficeColdGoingAround", category="common",
        chief_complaint="runny nose, sore throat, and a dry cough for the past three days, a few coworkers have the same thing",
        demographics={"age": 27, "sex": "female"}, ground_truth_diagnosis="viral_uri",
        answers={"associated_symptoms": "low grade fever, no trouble breathing", "duration": "three days, slowly improving"},
        exam_results={"vital_signs": "BP 116/72, HR 76, RR 14, Temp 37.3, SpO2 99%"},
    ),
    SyntheticCase(
        case_id="Blind15_02_PainfulUrinationCollegeStudent", category="common",
        chief_complaint="it stings every time I use the bathroom and I feel like I need to go every few minutes",
        demographics={"age": 21, "sex": "female"}, ground_truth_diagnosis="uncomplicated_cystitis",
        answers={"associated_symptoms": "mild pressure low in my belly, no fever, no back pain", "past_medical_history": "none"},
        exam_results={"vital_signs": "BP 112/68, HR 74, RR 14, Temp 36.8, SpO2 99%"},
        test_results={"urinalysis": "positive leukocyte esterase and nitrites"},
    ),
    SyntheticCase(
        case_id="Blind15_03_FoodTruckStomachBug", category="common",
        chief_complaint="been throwing up and running to the bathroom with diarrhea since we ate at that food truck last night",
        demographics={"age": 33, "sex": "male"}, ground_truth_diagnosis="gastroenteritis",
        answers={"associated_symptoms": "cramping all over my belly, stools are loose and watery but nothing bloody, two friends from the table are sick too",
                  "onset": "started about 10 hours ago"},
        exam_results={"vital_signs": "BP 112/70, HR 92, RR 16, Temp 37.6, SpO2 99%",
                      "abdominal_exam": "diffuse mild tenderness, soft, no rebound"},
    ),
    SyntheticCase(
        case_id="Blind15_04_AllDayScreenTimeHeadache", category="common",
        chief_complaint="a dull squeezing feeling all around my head that's been building up all afternoon at my desk",
        demographics={"age": 42, "sex": "male"}, ground_truth_diagnosis="tension_headache",
        answers={"associated_symptoms": "no nausea, no sensitivity to light or sound", "social_history": "long stretch of back-to-back meetings, hasn't slept well this week"},
        exam_results={"vital_signs": "BP 122/80, HR 74, RR 14, Temp 36.9, SpO2 99%", "neuro_exam": "grossly intact"},
    ),

    # ================= critical (7) =================
    SyntheticCase(
        case_id="Blind15_05_CrushingPressureShovelingSnow", category="critical",
        chief_complaint="this crushing weight on my chest hit me while I was clearing the driveway, hasn't let up",
        demographics={"age": 61, "sex": "male"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "about 30 minutes ago, constant", "character": "heavy pressure, not sharp",
                  "associated_symptoms": "sweating, queasy, aching down my left arm",
                  "past_medical_history": "high blood pressure, type 2 diabetes"},
        exam_results={"vital_signs": "BP 152/94, HR 102, RR 18, Temp 36.9, SpO2 95%"},
        test_results={"ecg": "ST depression in leads V3-V5", "troponin": "elevated troponin"},
    ),
    SyntheticCase(
        case_id="Blind15_06_SuddenFaceDropAndArmWeakness", category="critical",
        chief_complaint="one side of his face suddenly dropped and he can't lift his right arm anymore",
        demographics={"age": 71, "sex": "male"}, ground_truth_diagnosis="ischemic_stroke",
        answers={"onset": "his wife noticed it about 20 minutes ago, sudden", "past_medical_history": "atrial fibrillation, hypertension"},
        exam_results={"neuro_exam": "right facial droop, right arm drift, slurred speech", "vital_signs": "BP 164/96, HR 88, RR 16, Temp 36.8, SpO2 98%"},
        test_results={"ct_head": "no hemorrhage, early ischemic changes in the left MCA territory", "glucose_point_of_care": "normal glucose"},
    ),
    SyntheticCase(
        case_id="Blind15_07_InstantExplosiveHeadachePool", category="critical",
        chief_complaint="a headache like a bomb went off in my skull, hit me all at once while I was swimming laps",
        demographics={"age": 47, "sex": "female"}, ground_truth_diagnosis="subarachnoid_hemorrhage",
        answers={"onset": "instant, maximum intensity within seconds", "severity": "worst headache of my life",
                  "associated_symptoms": "neck feels stiff, vomited once, sensitive to the pool lights"},
        exam_results={"meningeal_signs": "positive nuchal rigidity", "neuro_exam": "no focal deficit", "vital_signs": "BP 158/94, HR 92, RR 16, Temp 37.0, SpO2 98%"},
        test_results={"ct_head": "hyperdensity in the basal cisterns consistent with subarachnoid blood"},
    ),
    SyntheticCase(
        case_id="Blind15_08_NursingHomeFeverAndConfusion", category="critical",
        chief_complaint="she's spiking a fever and barely making sense today, they said she had a UTI treated last week",
        demographics={"age": 82, "sex": "female"}, ground_truth_diagnosis="sepsis",
        answers={"onset": "family noticed this morning, worsening", "past_medical_history": "recent urinary tract infection, diabetes",
                  "associated_symptoms": "shaking chills, hasn't been eating"},
        exam_results={"vital_signs": "BP 84/52, HR 124, RR 26, Temp 39.4, SpO2 93%", "mental_status_exam": "disoriented to place and time", "skin_exam": "warm, flushed, no rash"},
        test_results={"lactate": "elevated lactate", "blood_culture": "pending, drawn", "cbc": "elevated white blood cell count"},
    ),
    SyntheticCase(
        case_id="Blind15_09_SuddenBreathlessAfterCastRemoval", category="critical",
        chief_complaint="my breathing just seized up out of nowhere and it stabs when I breathe in deep",
        demographics={"age": 55, "sex": "female"}, ground_truth_diagnosis="pulmonary_embolism",
        answers={"onset": "very abrupt, maybe 45 minutes back", "character": "stabbing, worse with a deep breath",
                  "past_medical_history": "leg was casted for six weeks after a fracture, cast came off three days ago"},
        exam_results={"vital_signs": "BP 108/68, HR 118, RR 26, Temp 37.1, SpO2 90%", "extremity_exam": "the previously casted calf is swollen and tender"},
        test_results={"d_dimer": "elevated d-dimer", "ct_chest_angio": "filling defect in the right lower lobe pulmonary artery"},
    ),
    SyntheticCase(
        case_id="Blind15_10_DormRoommateFeverNeckPain", category="critical",
        chief_complaint="he's burning up, says his head is pounding, and he can barely tuck his chin to his chest",
        demographics={"age": 19, "sex": "male"}, ground_truth_diagnosis="meningitis",
        answers={"onset": "started last night, getting worse fast", "associated_symptoms": "bright lights are unbearable, roommate says he seems out of it",
                  "past_medical_history": "lives in a dorm, not sure about his vaccination record"},
        exam_results={"meningeal_signs": "positive Kernig sign", "mental_status_exam": "slow to answer, oriented x2", "vital_signs": "BP 100/64, HR 112, RR 20, Temp 39.6, SpO2 97%"},
        test_results={"lumbar_puncture": "cloudy CSF, elevated white cell count, low glucose", "blood_culture": "pending, drawn"},
    ),
    SyntheticCase(
        case_id="Blind15_11_ThroatClosingAfterShrimpDinner", category="critical",
        chief_complaint="my lips are huge, I'm covered in welts, and it feels like my throat is squeezing shut, we just had shrimp",
        demographics={"age": 29, "sex": "male"}, ground_truth_diagnosis="anaphylaxis",
        answers={"onset": "within ten minutes of eating", "allergy": "never had a reaction to shellfish before this",
                  "associated_symptoms": "wheezy when I breathe, feel like I might pass out"},
        exam_results={"skin_exam": "diffuse hives, lips and tongue swollen", "lung_auscultation": "audible wheeze bilaterally",
                      "vital_signs": "BP 82/50, HR 128, RR 28, Temp 37.0, SpO2 91%"},
    ),

    # ================= dangerous_mimic (3) =================
    SyntheticCase(
        case_id="Blind15_12_TearingBetweenShoulderBladesCalledItAPulledMuscle", category="dangerous_mimic",
        chief_complaint="a tearing feeling between my shoulder blades, I figured I threw my back out moving furniture",
        demographics={"age": 63, "sex": "male"}, ground_truth_diagnosis="aortic_dissection",
        answers={"onset": "sudden, mid-lift, hasn't eased at all", "character": "tearing, ripping, worst pain of my life",
                  "past_medical_history": "poorly controlled high blood pressure"},
        exam_results={"vital_signs": "BP 178/62 in the right arm, BP 142/58 in the left arm, HR 96, RR 18, Temp 36.9, SpO2 97%",
                      "extremity_exam": "diminished pulse in the left arm compared to the right"},
        test_results={"ct_aorta": "intimal flap in the descending thoracic aorta", "ecg": "no acute ischemic changes"},
    ),
    SyntheticCase(
        case_id="Blind15_13_SkateboardFallThoughtItWasJustHisAsthma", category="dangerous_mimic",
        chief_complaint="he went down hard on his bike and now he's gasping, his mom thought his asthma was just acting up",
        demographics={"age": 16, "sex": "male"}, ground_truth_diagnosis="tension_pneumothorax",
        answers={"onset": "right after the crash, rapidly worse", "past_medical_history": "mild asthma as a kid, hasn't needed an inhaler in years"},
        exam_results={"lung_auscultation": "absent breath sounds on the left, trachea shifted to the right",
                      "vital_signs": "BP 88/56, HR 128, RR 32, Temp 36.8, SpO2 87%", "general_appearance": "visibly struggling to breathe"},
        test_results={"cxr": "large left-sided pneumothorax with mediastinal shift"},
    ),
    SyntheticCase(
        case_id="Blind15_14_DarkStoolsBlamedOnBeetSalad", category="dangerous_mimic",
        chief_complaint="my stools have looked black and tarry for two days, I figured it was from the beet salad I ate",
        demographics={"age": 68, "sex": "male"}, ground_truth_diagnosis="gi_bleeding",
        answers={"medication": "takes daily aspirin and ibuprofen for his knees", "associated_symptoms": "feels unusually tired and lightheaded standing up",
                  "past_medical_history": "history of a stomach ulcer years ago"},
        exam_results={"vital_signs": "BP 96/60, HR 108, RR 18, Temp 36.9, SpO2 98%", "abdominal_exam": "mild epigastric tenderness, no rebound"},
        test_results={"cbc": "low hemoglobin", "fecal_occult_blood": "positive"},
    ),

    # ================= benign_mimic (4) =================
    SyntheticCase(
        case_id="Blind15_15_SorePecsAfterBenchPressDay", category="benign_mimic",
        chief_complaint="a sharp spot on my left chest wall that flares up if I poke at it, the day after a heavy bench press session",
        demographics={"age": 26, "sex": "male"}, ground_truth_diagnosis="musculoskeletal_chest_pain",
        answers={"character": "sharp, one exact spot, flares up when I poke it", "aggravating": "worse turning my torso or lifting my arm, breathing is fine"},
        exam_results={"vital_signs": "BP 118/74, HR 70, RR 14, Temp 36.8, SpO2 99%", "abdominal_exam": "point tenderness over the left costal cartilage, chest wall otherwise unremarkable"},
        test_results={"ecg": "normal sinus rhythm, no acute changes"},
    ),
    SyntheticCase(
        case_id="Blind15_16_WorldSpinsFlippingPillowOver", category="benign_mimic",
        chief_complaint="every time I roll over to flip my pillow the room spins hard for a few seconds",
        demographics={"age": 57, "sex": "female"}, ground_truth_diagnosis="bppv",
        answers={"onset": "started a few nights ago, brief episodes only", "duration": "each spell lasts maybe 20-30 seconds",
                  "associated_symptoms": "no ringing in the ears, no hearing change, nothing between episodes"},
        exam_results={"neuro_exam": "fully intact, no focal deficit", "vital_signs": "BP 124/78, HR 72, RR 14, Temp 36.9, SpO2 99%"},
    ),
    SyntheticCase(
        case_id="Blind15_17_HeartPoundingBeforeBoardExam", category="benign_mimic",
        chief_complaint="my heart is pounding, my hands are tingling, and I feel like I'm about to lose it right before my licensing exam",
        demographics={"age": 30, "sex": "female"}, ground_truth_diagnosis="panic_attack",
        answers={"onset": "started about 15 minutes ago while waiting in line", "duration": "already easing off a bit",
                  "past_medical_history": "history of anxiety, similar episodes before big tests"},
        exam_results={"vital_signs": "BP 128/80, HR 104, RR 22, Temp 36.9, SpO2 99%", "general_appearance": "anxious but alert, improving with reassurance"},
        test_results={"ecg": "normal sinus rhythm, no acute changes"},
    ),
    SyntheticCase(
        case_id="Blind15_18_BurningChestAfterLateNightPizza", category="benign_mimic",
        chief_complaint="this burning feeling climbs up my chest almost every night after I eat a big late dinner",
        demographics={"age": 44, "sex": "male"}, ground_truth_diagnosis="gerd",
        answers={"character": "burning, rises up toward my throat", "aggravating": "worse lying flat after eating, worse with spicy food",
                  "relieving": "some relief with antacids"},
        exam_results={"vital_signs": "BP 126/80, HR 76, RR 14, Temp 36.8, SpO2 99%", "abdominal_exam": "soft, mild epigastric tenderness"},
        test_results={"ecg": "normal sinus rhythm, no acute changes", "troponin": "normal troponin"},
    ),

    # ================= unseen_lay_phrasing (2) =================
    SyntheticCase(
        case_id="Blind15_19_LayLanguageWetLungInfection", category="unseen_lay_phrasing",
        chief_complaint="coughing up thick gunk for days, my side aches when I breathe deep, and I'm shivering and sweating by turns",
        demographics={"age": 49, "sex": "male"}, ground_truth_diagnosis="pneumonia",
        answers={"associated_symptoms": "short of breath climbing stairs", "onset": "started about five days ago, worse the last two"},
        exam_results={"lung_auscultation": "crackles at the right base", "vital_signs": "BP 118/76, HR 104, RR 24, Temp 38.9, SpO2 92%"},
        test_results={"cxr": "right lower lobe consolidation", "cbc": "elevated white blood cell count"},
    ),
    SyntheticCase(
        case_id="Blind15_20_LayLanguageSugarCrisis", category="unseen_lay_phrasing",
        chief_complaint="can't stop drinking water, peeing nonstop, belly hurts, and my breath smells weird like nail polish",
        demographics={"age": 17, "sex": "female"}, ground_truth_diagnosis="diabetic_ketoacidosis",
        answers={"past_medical_history": "type 1 diabetic, insulin pen has been empty since the weekend and she hasn't refilled it", "associated_symptoms": "throwing up, breathing fast and deep"},
        exam_results={"mental_status_exam": "drowsy but arousable", "abdominal_exam": "diffuse mild tenderness", "vital_signs": "BP 100/64, HR 116, RR 30, Temp 37.0, SpO2 97%"},
        test_results={"glucose_point_of_care": "critically high glucose", "ketones": "large ketones", "abg": "metabolic acidosis"},
    ),

    # ================= objective_evidence (2) =================
    SyntheticCase(
        case_id="Blind15_21_UpperBellyPainRadiatingToBackLipaseConfirms", category="objective_evidence",
        chief_complaint="a boring pain right in the pit of my stomach that shoots straight through to my back",
        demographics={"age": 46, "sex": "male"}, ground_truth_diagnosis="acute_pancreatitis",
        answers={"location": "upper belly, radiates to the back", "social_history": "drinks heavily most weekends",
                  "aggravating": "worse after eating anything greasy"},
        exam_results={"abdominal_exam": "epigastric tenderness, no rebound", "vital_signs": "BP 110/70, HR 98, RR 18, Temp 37.4, SpO2 98%"},
        test_results={"lipase": "elevated lipase"},
    ),
    SyntheticCase(
        case_id="Blind15_22_FlutteryHeartECGConfirmsIrregularRhythm", category="objective_evidence",
        chief_complaint="my heart keeps doing this fluttery, skipping thing on and off since yesterday afternoon",
        demographics={"age": 66, "sex": "female"}, ground_truth_diagnosis="cardiac_arrhythmia",
        answers={"onset": "on and off since yesterday afternoon", "duration": "episodes last a few minutes at a time",
                  "associated_symptoms": "a little lightheaded during the episodes, no chest pain"},
        exam_results={"cardiac_auscultation": "irregularly irregular rhythm", "vital_signs": "BP 128/80, HR 128 irregular, RR 16, Temp 36.9, SpO2 98%"},
        test_results={"ecg": "atrial fibrillation with rapid ventricular response", "bmp": "normal electrolytes"},
    ),

    # ================= risk_context_heavy (1) =================
    SyntheticCase(
        case_id="Blind15_23_SameStoneAgainRightFlank", category="risk_context_heavy",
        chief_complaint="this is the exact same awful pain from my side down into my groin I had two years ago with a kidney stone",
        demographics={"age": 39, "sex": "male"}, ground_truth_diagnosis="nephrolithiasis",
        answers={"location": "right flank radiating into the groin", "character": "comes in waves, can't get comfortable in any position",
                  "family_history": "father also gets kidney stones"},
        exam_results={"costovertebral_tenderness": "positive on the right", "vital_signs": "BP 132/82, HR 94, RR 16, Temp 37.0, SpO2 99%"},
        test_results={"urinalysis": "microscopic hematuria"},
    ),

    # ================= medication_risk (1) =================
    SyntheticCase(
        case_id="Blind15_24_InsulinPenDoubleDoseConfusion", category="medication_risk",
        chief_complaint="he's sweaty, shaky, and not making much sense the last little while",
        demographics={"age": 60, "sex": "male"}, ground_truth_diagnosis="hypoglycemia",
        answers={"medication": "takes long-acting insulin, may have accidentally taken an extra dose this morning",
                  "past_medical_history": "type 2 diabetes", "onset": "his daughter says it's been maybe half an hour since she noticed"},
        exam_results={"mental_status_exam": "confused, diaphoretic, tremulous", "vital_signs": "BP 124/78, HR 102, RR 16, Temp 36.6, SpO2 98%"},
        test_results={"glucose_point_of_care": "critically low glucose"},
    ),

    # ================= negative_evidence_heavy (1) =================
    SyntheticCase(
        case_id="Blind15_25_LightheadedOnStandingEverythingElseNormal", category="negative_evidence_heavy",
        chief_complaint="every single time I stand up from my chair too fast I get lightheaded for a few seconds",
        demographics={"age": 74, "sex": "female"}, ground_truth_diagnosis="orthostatic_hypotension",
        answers={"onset": "past week or so, worse in the mornings", "medication": "started a new water pill three weeks ago",
                  "associated_symptoms": "no chest pain, denies palpitations before it happens, resolves quickly sitting back down"},
        exam_results={"vital_signs": "BP 126/78 lying, BP 96/60 standing, HR 88 standing, RR 14, Temp 36.8, SpO2 99%", "neuro_exam": "fully intact"},
    ),

    # ================= atypical_presentation (1) =================
    SyntheticCase(
        case_id="Blind15_26_ClumsyAndOffBalanceNothingElseObvious", category="atypical_presentation",
        chief_complaint="she just seems off balance and clumsy on her feet today, nothing else really stands out",
        demographics={"age": 69, "sex": "female"}, ground_truth_diagnosis="ischemic_stroke",
        answers={"onset": "family noticed a couple hours ago, hasn't improved", "past_medical_history": "hypertension, high cholesterol"},
        exam_results={"neuro_exam": "unsteady gait, past-pointing on finger-to-nose testing on the left, no facial droop",
                      "vital_signs": "BP 158/92, HR 78, RR 16, Temp 36.9, SpO2 98%"},
        test_results={"ct_head": "no hemorrhage, subtle hypodensity in the left cerebellum", "glucose_point_of_care": "normal glucose"},
    ),

    # ================= elderly (1) =================
    SyntheticCase(
        case_id="Blind15_27_GrandpaJustNotEatingOrTalkingMuch", category="elderly",
        chief_complaint="grandpa's barely touched his dinner the last two days and isn't talking as much as usual",
        demographics={"age": 87, "sex": "male"}, ground_truth_diagnosis="pneumonia",
        answers={"associated_symptoms": "denies cough that anyone's noticed, denies fever per the family, just quieter and more tired",
                  "past_medical_history": "mild dementia at baseline"},
        exam_results={"lung_auscultation": "crackles at the left base", "vital_signs": "BP 108/64, HR 98, RR 22, Temp 37.0, SpO2 91%"},
        test_results={"cxr": "left lower lobe consolidation", "cbc": "elevated white blood cell count"},
    ),

    # ================= pediatric (1) =================
    SyntheticCase(
        case_id="Blind15_28_KidWheezingAfterRecess", category="pediatric",
        chief_complaint="he came in from recess wheezing hard and can't finish a sentence without stopping to breathe",
        demographics={"age": 8, "sex": "male"}, ground_truth_diagnosis="asthma_copd_exacerbation",
        answers={"past_medical_history": "diagnosed with asthma at age 5, uses an inhaler sometimes",
                  "aggravating": "cold air outside always sets it off", "associated_symptoms": "tight chest, no fever"},
        exam_results={"lung_auscultation": "diffuse expiratory wheeze, prolonged expiratory phase", "vital_signs": "BP 104/66, HR 118, RR 32, Temp 36.9, SpO2 93%"},
        test_results={"cxr": "hyperinflated lungs, no focal consolidation"},
    ),

    # ================= pregnancy (1) =================
    SyntheticCase(
        case_id="Blind15_29_PregnantWithSuddenBreathlessness", category="pregnancy",
        chief_complaint="I'm 28 weeks along and I suddenly can't catch my breath, my chest hurts when I breathe in",
        demographics={"age": 31, "sex": "female"}, ground_truth_diagnosis="pulmonary_embolism",
        answers={"onset": "sudden, about an hour ago", "past_medical_history": "28 weeks pregnant, otherwise healthy",
                  "associated_symptoms": "one calf feels more swollen than the other"},
        exam_results={"vital_signs": "BP 110/70, HR 116, RR 26, Temp 37.0, SpO2 91%", "extremity_exam": "left calf swollen and tender compared to the right"},
        test_results={"d_dimer": "elevated d-dimer", "ct_chest_angio": "filling defect in the left pulmonary artery"},
    ),

    # ================= polypharmacy (1) =================
    SyntheticCase(
        case_id="Blind15_30_BloodPressurePillsPlusPotassiumPills", category="polypharmacy",
        chief_complaint="my legs feel weak all over and my heart's been doing this weird skipping thing since yesterday",
        demographics={"age": 71, "sex": "male"}, ground_truth_diagnosis="severe_electrolyte_disorder",
        answers={"medication": "takes lisinopril and started a potassium supplement his neighbor recommended a week ago",
                  "past_medical_history": "chronic kidney disease, hypertension"},
        exam_results={"cardiac_auscultation": "irregular rhythm noted", "vital_signs": "BP 118/72, HR 54 irregular, RR 16, Temp 36.8, SpO2 98%"},
        test_results={"bmp": "hyperkalemia", "ecg": "peaked T waves, widened QRS"},
    ),

    # ================= multimorbidity (1) =================
    SyntheticCase(
        case_id="Blind15_31_CKDDiabetesHypertensionWithNewPalpitations", category="multimorbidity",
        chief_complaint="my heart's been racing and fluttering off and on since this morning, on top of everything else I've got going on",
        demographics={"age": 76, "sex": "female"}, ground_truth_diagnosis="cardiac_arrhythmia",
        answers={"onset": "started this morning, comes and goes", "past_medical_history": "chronic kidney disease, diabetes, hypertension",
                  "associated_symptoms": "feels a bit woozy while it's happening, denies any chest discomfort"},
        exam_results={"cardiac_auscultation": "irregularly irregular rhythm", "vital_signs": "BP 138/84, HR 134 irregular, RR 16, Temp 36.9, SpO2 97%"},
        test_results={"ecg": "atrial fibrillation with rapid ventricular response", "bmp": "mildly elevated creatinine, normal potassium"},
    ),

    # ================= multilingual_korean (2) =================
    SyntheticCase(
        case_id="Blind15_32_KoreanMixedAppendicitis", category="multilingual_korean",
        chief_complaint="오른쪽 아랫배가 아파요, started around my belly button yesterday and moved down",
        demographics={"age": 20, "sex": "male"}, ground_truth_diagnosis="appendicitis",
        answers={"associated_symptoms": "no appetite, mild fever, nauseous", "onset": "started yesterday morning, worse today"},
        exam_results={"abdominal_exam": "right lower quadrant tenderness with rebound and guarding", "vital_signs": "BP 120/76, HR 98, RR 16, Temp 38.0, SpO2 99%"},
        test_results={"cbc": "elevated white blood cell count", "ct_abdomen": "dilated, thickened appendix"},
        notes="Korean for 'my lower right belly hurts' plus English onset/migration detail -- fresh "
              "domain (abdominal_pain) and diagnosis pairing distinct from any Blind v14 mixed-"
              "language case, proving the multilingual concept layer generalizes beyond chest pain.",
    ),
    SyntheticCase(
        case_id="Blind15_33_KoreanMixedMigraine", category="multilingual_korean",
        chief_complaint="머리 한쪽이 지끈지끈 아파요 and bright light makes it so much worse",
        demographics={"age": 34, "sex": "female"}, ground_truth_diagnosis="migraine",
        answers={"associated_symptoms": "nauseated, noticed some flickering spots in my vision just beforehand",
                  "family_history": "mother gets bad headaches too", "past_medical_history": "this is a recurring thing for her, has been for years"},
        exam_results={"neuro_exam": "fully intact, no focal deficit", "vital_signs": "BP 118/74, HR 76, RR 14, Temp 36.8, SpO2 99%"},
        notes="Korean for 'one side of my head throbs' plus English aura/photophobia detail -- fresh "
              "headache-domain multilingual pairing.",
    ),

    # ================= multilingual_japanese (1) =================
    SyntheticCase(
        case_id="Blind15_34_JapaneseMixedAsthmaExacerbation", category="multilingual_japanese",
        chief_complaint="息が苦しいです, been wheezing since I walked home in the cold air",
        demographics={"age": 24, "sex": "male"}, ground_truth_diagnosis="asthma_copd_exacerbation",
        answers={"past_medical_history": "diagnosed with asthma as a teenager", "aggravating": "cold air and exercise always set it off"},
        exam_results={"lung_auscultation": "diffuse expiratory wheeze", "vital_signs": "BP 118/74, HR 104, RR 26, Temp 36.9, SpO2 94%"},
        test_results={"cxr": "hyperinflated lungs, no focal consolidation"},
        notes="Japanese for 'I'm having trouble breathing' plus English trigger/history detail -- "
              "fresh dyspnea-domain multilingual pairing, distinct diagnosis from Blind v14's own "
              "Japanese-mixed appendicitis case.",
    ),

    # ================= mixed_language (1) =================
    SyntheticCase(
        case_id="Blind15_35_KoreanMixedPyelonephritisFeverFlank", category="mixed_language",
        chief_complaint="열이 나고 오른쪽 옆구리가 아파요, started two days ago and getting worse",
        demographics={"age": 41, "sex": "female"}, ground_truth_diagnosis="pyelonephritis",
        answers={"associated_symptoms": "stings going to the bathroom, shaking chills, stomach feels off", "past_medical_history": "none"},
        exam_results={"costovertebral_tenderness": "positive on the right", "vital_signs": "BP 108/68, HR 106, RR 18, Temp 38.9, SpO2 98%"},
        test_results={"urinalysis": "positive leukocyte esterase and nitrites", "urine_culture": "pending, sent"},
        notes="Korean for 'I have a fever and my right side hurts' plus English associated-symptom "
              "detail -- a fever/flank-pain domain pairing distinct from the abdominal_pain "
              "multilingual_korean cases above, exercising the multilingual layer on a third domain.",
    ),

    # ================= reproductive_age_emergency (2) =================
    SyntheticCase(
        case_id="Blind15_36_VagueCrampyDiscomfortMissedPeriod", category="reproductive_age_emergency",
        chief_complaint="honestly I can't even describe it well, just a nagging ache down low on my left that won't quit",
        demographics={"age": 24, "sex": "female"}, ground_truth_diagnosis="ectopic_pregnancy",
        answers={"onset": "started yesterday, has been coming in waves ever since", "location": "left side, low down near the hip bone",
                  "character": "cramp-like, tightens up then eases off",
                  "associated_symptoms": "noticed some brownish spotting, hasn't had a fever, hasn't thrown up",
                  "social_history": "has a boyfriend, her cycle is running well behind schedule this month",
                  "past_medical_history": "nothing chronic that she's aware of"},
        exam_results={"abdominal_exam": "mild left lower quadrant tenderness, no rebound", "vital_signs": "BP 98/60, HR 108, RR 16, Temp 36.8, SpO2 99%"},
        test_results={"beta_hcg": "positive beta-hCG", "pelvic_ultrasound": "no intrauterine pregnancy, left adnexal mass"},
    ),
    SyntheticCase(
        case_id="Blind15_37_SuddenGroinPainAfterGymClass", category="reproductive_age_emergency",
        chief_complaint="a sudden sharp pain low in her belly during gym class, she went pale and almost fainted",
        demographics={"age": 16, "sex": "female"}, ground_truth_diagnosis="tier2:ovarian_torsion",
        scoring_expected=False,
        answers={"onset": "sudden, about an hour ago, still severe", "location": "lower right side",
                  "associated_symptoms": "nauseous, vomited once, denies fever",
                  "past_medical_history": "none", "social_history": "not sexually active"},
        exam_results={"abdominal_exam": "right lower quadrant tenderness, no rebound", "vital_signs": "BP 106/68, HR 112, RR 18, Temp 36.9, SpO2 99%"},
        test_results={"beta_hcg": "negative beta-hCG", "pelvic_ultrasound": "enlarged right ovary with absent Doppler flow"},
        notes="A second, DIFFERENT reproductive-age-emergency mechanism (adnexal torsion, not "
              "pregnancy) -- proves contextual_safety's activation logic is about the presenting "
              "context (reproductive-age + abdominal/pelvic symptoms), not a single hardcoded "
              "diagnosis. Tier-2/scoring_expected=False since ovarian_torsion carries no curated "
              "Tier-1 KB entry of its own; checked for safe, non-dangerous-appearing handling.",
    ),

    # ================= specific_vs_generic_severity_conflict (3) =================
    SyntheticCase(
        case_id="Blind15_38_MassivePEWithShockLikeVitals", category="specific_vs_generic_severity_conflict",
        chief_complaint="he went from fine to gasping and gray-looking in the span of a couple minutes",
        demographics={"age": 64, "sex": "male"}, ground_truth_diagnosis="pulmonary_embolism",
        answers={"onset": "abrupt, roughly 20 minutes back", "character": "stabbing, worse breathing in",
                  "past_medical_history": "had his knee replaced eight days ago", "associated_symptoms": "no fever reported, no chills"},
        exam_results={"vital_signs": "BP 82/50, HR 132, RR 32, Temp 36.8, SpO2 86%", "extremity_exam": "operative leg swollen and tender"},
        test_results={"d_dimer": "elevated d-dimer", "ct_chest_angio": "large saddle filling defect"},
        notes="Deranged vitals (hypotension, tachycardia, tachypnea, hypoxia) alone are equally "
              "consistent with septic shock, but only PE has real disease-specific support here "
              "(pleuritic pain, recent surgery risk factor, unilateral leg swelling, confirmatory "
              "imaging) -- a fresh specific-vs-generic-severity pairing distinct from any "
              "development case.",
    ),
    SyntheticCase(
        case_id="Blind15_39_AnaphylaxisWithSepticLookingVitals", category="specific_vs_generic_severity_conflict",
        chief_complaint="his whole body broke out in hives right after his bee sting and now he looks like he's going into shock",
        demographics={"age": 34, "sex": "male"}, ground_truth_diagnosis="anaphylaxis",
        answers={"onset": "within five minutes of the sting", "allergy": "stung on the forearm, never reacted to a sting before",
                  "associated_symptoms": "throat feels tight, wheezy"},
        exam_results={"skin_exam": "diffuse urticaria, lips swollen", "lung_auscultation": "audible wheeze",
                      "vital_signs": "BP 78/48, HR 134, RR 30, Temp 37.1, SpO2 89%"},
        notes="Hypotension/tachycardia/tachypnea/hypoxia alone would equally fit septic shock, but "
              "the specific trigger (bee sting), hives, facial swelling, and wheeze are real "
              "disease-specific evidence for anaphylaxis that must not be outranked by generic "
              "severity findings shared with sepsis.",
    ),
    SyntheticCase(
        case_id="Blind15_40_DKAWithFeverLookingLikeSepsis", category="specific_vs_generic_severity_conflict",
        chief_complaint="he's breathing really fast and deep, running a fever, and seems out of it since this afternoon",
        demographics={"age": 22, "sex": "male"}, ground_truth_diagnosis="diabetic_ketoacidosis",
        answers={"past_medical_history": "type 1 diabetic, hasn't been able to afford his insulin refill this week", "associated_symptoms": "vomiting, very thirsty, urinating constantly",
                  "onset": "worsening over the past day"},
        exam_results={"mental_status_exam": "lethargic but arousable", "vital_signs": "BP 100/62, HR 122, RR 32, Temp 38.2, SpO2 96%"},
        test_results={"glucose_point_of_care": "critically high glucose", "ketones": "large ketones", "abg": "metabolic acidosis"},
        notes="Fever plus tachycardia/tachypnea alone would equally fit sepsis, but polyuria/"
              "polydipsia, a missed-insulin risk factor, and the glucose/ketone/ABG confirmatory "
              "results are specific to DKA -- generic severity from the fever must not let sepsis "
              "outrank the specifically-supported diagnosis here.",
    ),

    # ================= fuzzy_phrase_collision_trap (3) =================
    SyntheticCase(
        case_id="Blind15_41_ChestBurnWorseAfterExerciseNotMeals", category="fuzzy_phrase_collision_trap",
        chief_complaint="a squeezing chest tightness that's worse when I push myself on the elliptical, eases off when I stop",
        demographics={"age": 56, "sex": "male"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "over the last two weeks, only with exertion", "aggravating": "worse climbing stairs or on the elliptical, never with food",
                  "past_medical_history": "high cholesterol, father had a heart attack young"},
        exam_results={"vital_signs": "BP 138/86, HR 88, RR 16, Temp 36.9, SpO2 98%"},
        test_results={"ecg": "ST depression with exertion on repeat tracing", "troponin": "mildly elevated troponin"},
        notes="Shares the generic relational word 'worse' with GERD's own 'worse after meals' "
              "typical_feature, but the trigger is exertion, never meals -- tests that the "
              "distinguishing-token gate doesn't let GERD win on generic overlap while ACS's own "
              "exertional/risk-factor/confirmatory evidence carries the real diagnosis.",
    ),
    SyntheticCase(
        case_id="Blind15_42_SharpChestPainAfterArgumentNotTrauma", category="fuzzy_phrase_collision_trap",
        chief_complaint="a sudden sharp chest pain and I can barely breathe, it started right after a huge argument with my brother",
        demographics={"age": 44, "sex": "female"}, ground_truth_diagnosis="pulmonary_embolism",
        answers={"onset": "sudden, during the argument, hasn't eased", "character": "sharp, worse with breathing",
                  "past_medical_history": "started an oral contraceptive two months ago", "social_history": "long international flight two weeks ago"},
        exam_results={"vital_signs": "BP 106/68, HR 116, RR 26, Temp 37.0, SpO2 91%", "extremity_exam": "mild left calf swelling"},
        test_results={"d_dimer": "elevated d-dimer", "ct_chest_angio": "filling defect in the left pulmonary artery"},
        notes="Shares the generic relational word 'after' with tension_pneumothorax's own 'chest "
              "pain after trauma' typical_feature (and 'chest pain' itself), but there is no trauma "
              "here at all -- an argument is not a physical injury. Tests that the phrase-matching "
              "gate doesn't let tension_pneumothorax win on 'chest pain after X' alone while PE's "
              "own risk factors (oral contraceptive, long flight) and pleuritic quality carry the "
              "real diagnosis.",
    ),
    SyntheticCase(
        case_id="Blind15_43_DizzyOnStandingNotABenignFaint", category="fuzzy_phrase_collision_trap",
        chief_complaint="I get lightheaded almost every time I stand up quickly, and once my heart was pounding hard right before it happened",
        demographics={"age": 52, "sex": "male"}, ground_truth_diagnosis="cardiac_arrhythmia",
        answers={"onset": "over the past week, several episodes", "associated_symptoms": "one episode this week I definitely felt my heart racing and skipping right before I got dizzy",
                  "past_medical_history": "none known"},
        exam_results={"cardiac_auscultation": "irregular rhythm noted during one episode", "vital_signs": "BP 122/78, HR 100 irregular, RR 16, Temp 36.9, SpO2 98%"},
        test_results={"ecg": "paroxysmal atrial fibrillation captured on the tracing", "bmp": "normal electrolytes"},
        notes="orthostatic_hypotension and vasovagal_syncope both carry a typical_feature of 'no "
              "palpitations before the episode' -- this patient explicitly DOES report palpitations "
              "before one episode, the real distinguishing content word this phrase's relational-"
              "word gate must not let a superficial 'before the episode' overlap paper over. Tests "
              "that a negated/contradicted KB phrase doesn't spuriously support the wrong benign "
              "diagnosis via generic overlap.",
    ),

    # ================= long_tail (4, Tier-2) =================
    SyntheticCase(
        case_id="Blind15_44_LongTailGallbladderAttack", category="long_tail",
        chief_complaint="a gripping pain just under my right ribcage, comes on strong whenever I have something greasy, wraps around toward my back",
        demographics={"age": 45, "sex": "female"}, ground_truth_diagnosis="tier2:cholecystitis",
        scoring_expected=False,
        answers={"aggravating": "greasy or fried food sets it off every time", "associated_symptoms": "queasy, running a low fever"},
        exam_results={"abdominal_exam": "right upper quadrant tenderness, positive Murphy sign", "vital_signs": "BP 124/78, HR 92, RR 16, Temp 37.9, SpO2 98%"},
        test_results={"cbc": "elevated white blood cell count"},
    ),
    SyntheticCase(
        case_id="Blind15_45_LongTailSwollenCalfNoInjury", category="long_tail",
        chief_complaint="my right lower leg has puffed up and gotten hot and achy over the past three days, no idea why",
        demographics={"age": 58, "sex": "male"}, ground_truth_diagnosis="tier2:deep_vein_thrombosis",
        scoring_expected=False,
        answers={"past_medical_history": "drove cross-country last week, over ten hours behind the wheel", "associated_symptoms": "breathing is fine, no chest discomfort"},
        exam_results={"extremity_exam": "right calf swollen, warm, tender to palpation", "vital_signs": "BP 128/80, HR 84, RR 16, Temp 37.2, SpO2 99%"},
    ),
    SyntheticCase(
        case_id="Blind15_46_LongTailLeftSidedBellyPainWithFever", category="long_tail",
        chief_complaint="crampy pain low on my left side for two days, feverish, and my bowel habits have been off",
        demographics={"age": 62, "sex": "female"}, ground_truth_diagnosis="tier2:diverticulitis",
        scoring_expected=False,
        answers={"location": "lower left belly", "associated_symptoms": "low fever, constipated the last two days"},
        exam_results={"abdominal_exam": "left lower quadrant tenderness, mild guarding", "vital_signs": "BP 130/82, HR 94, RR 16, Temp 38.1, SpO2 98%"},
        test_results={"cbc": "elevated white blood cell count"},
    ),
    SyntheticCase(
        case_id="Blind15_47_LongTailSuddenGroinPainTeenBoy", category="long_tail",
        chief_complaint="sudden severe pain in his groin during soccer practice, one side looks swollen now",
        demographics={"age": 14, "sex": "male"}, ground_truth_diagnosis="tier2:testicular_torsion",
        scoring_expected=False,
        answers={"onset": "sudden, about an hour ago, severe", "associated_symptoms": "nauseous, vomited once"},
        exam_results={"abdominal_exam": "no abdominal tenderness", "vital_signs": "BP 116/70, HR 104, RR 16, Temp 36.9, SpO2 99%"},
        notes="Time-critical Tier-2 diagnosis (viability window) with no curated Tier-1 KB entry -- "
              "checked for safe, urgent-appropriate handling (never dismissed as low-acuity), not "
              "for a single deterministic top-1 answer.",
    ),

    # ================= unknown_ood (2) =================
    SyntheticCase(
        case_id="Blind15_48_CantPutItIntoWordsMalaise", category="unknown_ood", scoring_expected=False,
        chief_complaint="I don't know how to describe it, I just haven't felt like myself in a while",
        demographics={"age": 40, "sex": "female"}, ground_truth_diagnosis="unknown",
        answers={"onset": "hard to say, gradual over a couple weeks", "associated_symptoms": "nothing specific I can point to"},
        exam_results={"vital_signs": "BP 118/74, HR 76, RR 14, Temp 36.9, SpO2 99%"},
    ),
    SyntheticCase(
        case_id="Blind15_49_OffTopicComplaintAboutTheWeather", category="unknown_ood", scoring_expected=False,
        chief_complaint="honestly the humidity has been brutal this week and I think it's throwing everything off for me",
        demographics={"age": 35, "sex": "male"}, ground_truth_diagnosis="unknown",
        answers={"associated_symptoms": "hard to pin down, just generally uncomfortable"},
        exam_results={"vital_signs": "BP 120/78, HR 78, RR 14, Temp 37.0, SpO2 99%"},
    ),

    # ================= retrieval_miss_trap (2) =================
    SyntheticCase(
        case_id="Blind15_50_VagueOutOfItTeenagerLabsRevealDKA", category="retrieval_miss_trap",
        chief_complaint="he's just not acting like himself today, kind of out of it, hard to get a straight answer from him",
        demographics={"age": 15, "sex": "male"}, ground_truth_diagnosis="diabetic_ketoacidosis",
        answers={"past_medical_history": "diagnosed with type 1 diabetes two years ago", "associated_symptoms": "mom says he's been drinking a lot of water lately"},
        exam_results={"mental_status_exam": "drowsy, slow to respond", "vital_signs": "BP 104/66, HR 118, RR 28, Temp 36.9, SpO2 97%"},
        test_results={"glucose_point_of_care": "critically high glucose", "ketones": "large ketones", "abg": "metabolic acidosis"},
    ),
    SyntheticCase(
        case_id="Blind15_51_VagueChestDiscomfortImagingRevealsDissection", category="retrieval_miss_trap",
        chief_complaint="there's this deep discomfort spanning my chest into my upper back that I just can't shake off",
        demographics={"age": 59, "sex": "male"}, ground_truth_diagnosis="aortic_dissection",
        answers={"onset": "came on all at once roughly an hour ago", "past_medical_history": "blood pressure runs high, inconsistent about taking his medication"},
        exam_results={"vital_signs": "BP 172/66 right arm, BP 138/64 left arm, HR 92, RR 18, Temp 36.9, SpO2 97%"},
        test_results={"ct_aorta": "intimal flap extending into the descending aorta", "ecg": "no acute ischemic changes"},
    ),

    # ================= routing_trap (2) =================
    SyntheticCase(
        case_id="Blind15_52_StomachThenSideAmbiguousMigration", category="routing_trap",
        chief_complaint="my stomach's been off since this morning, now it's more just this side that bothers me",
        demographics={"age": 25, "sex": "female"}, ground_truth_diagnosis="appendicitis",
        answers={"location": "started around the belly button, now it's the lower right side", "associated_symptoms": "no appetite, mild fever, nauseous"},
        exam_results={"abdominal_exam": "right lower quadrant tenderness with guarding", "vital_signs": "BP 116/72, HR 96, RR 16, Temp 38.0, SpO2 99%"},
        test_results={"cbc": "elevated white blood cell count", "ct_abdomen": "dilated, thickened appendix"},
        notes="Ambiguous early wording ('stomach' then 'side') could route toward a generic "
              "abdominal-only or even flank/back-pain concept before the migration detail is "
              "known -- tests that routing correctly follows the evolving, more specific detail "
              "rather than anchoring on the vaguer initial phrasing.",
    ),
    SyntheticCase(
        case_id="Blind15_53_BackThenFlankAmbiguousFeverPain", category="routing_trap",
        chief_complaint="my lower back's been killing me since yesterday, and now with this fever I'm starting to wonder if it's something else",
        demographics={"age": 36, "sex": "female"}, ground_truth_diagnosis="pyelonephritis",
        answers={"location": "right side, more toward the flank than the middle of the back", "associated_symptoms": "burning when I urinate, chills, nauseous"},
        exam_results={"costovertebral_tenderness": "positive on the right", "vital_signs": "BP 110/70, HR 104, RR 18, Temp 39.0, SpO2 98%"},
        test_results={"urinalysis": "positive leukocyte esterase and nitrites", "urine_culture": "pending, sent"},
        notes="Ambiguous 'lower back' wording could route toward a pure musculoskeletal back-pain "
              "concept rather than the urinary/flank-pain domain -- tests that the added fever and "
              "urinary symptom correctly redirect routing rather than getting stuck on the initial "
              "back-pain framing.",
    ),

    # ================= over_testing_trap (2) =================
    SyntheticCase(
        case_id="Blind15_54_TextbookMigraineNotSAH", category="over_testing_trap",
        chief_complaint="a pounding headache on the right side, happens every couple months like clockwork, can't stand any light when it hits",
        demographics={"age": 29, "sex": "female"}, ground_truth_diagnosis="migraine",
        answers={"character": "pounding, one-sided", "associated_symptoms": "queasy stomach, a shimmering blind spot warned me it was coming",
                  "family_history": "mother and sister both get migraines", "past_medical_history": "diagnosed with migraines years ago, this feels identical to the usual ones"},
        exam_results={"neuro_exam": "fully intact, no focal deficit", "vital_signs": "BP 116/72, HR 74, RR 14, Temp 36.8, SpO2 99%"},
    ),
    SyntheticCase(
        case_id="Blind15_55_TextbookBronchitisNotPneumonia", category="over_testing_trap",
        chief_complaint="can't shake this hacking cough, bringing up clear phlegm, it followed right on the heels of a cold",
        demographics={"age": 33, "sex": "male"}, ground_truth_diagnosis="acute_bronchitis",
        answers={"duration": "going on nine days now, gradually easing", "associated_symptoms": "ran a low fever the first couple days, breathing feels fine now",
                  "social_history": "was pretty congested with a head cold right before the cough kicked in"},
        exam_results={"lung_auscultation": "clear breath sounds, no focal consolidation", "vital_signs": "BP 118/76, HR 78, RR 16, Temp 37.1, SpO2 99%"},
    ),

    # ================= premature_diagnosis_trap (2) =================
    SyntheticCase(
        case_id="Blind15_56_VagueEarlyBellyPainActuallyPerforation", category="premature_diagnosis_trap",
        chief_complaint="just a vague, uncomfortable feeling in my stomach since this morning, figured it was something I ate",
        demographics={"age": 54, "sex": "male"}, ground_truth_diagnosis="acute_abdomen",
        answers={"onset": "started mild this morning, now much worse and constant", "severity": "started mild, now the worst pain I've ever had",
                  "past_medical_history": "takes ibuprofen regularly for back pain"},
        exam_results={"abdominal_exam": "rigid abdomen, diffuse rebound and guarding", "vital_signs": "BP 100/62, HR 116, RR 22, Temp 38.3, SpO2 96%"},
        test_results={"cbc": "elevated white blood cell count", "lipase": "normal lipase"},
        notes="Early wording sounds like ordinary indigestion; by the time exam findings return the "
              "picture is a surgical abdomen -- tests that the agent doesn't lock onto a benign "
              "early impression (gastritis/indigestion) before gathering the exam evidence that "
              "changes the picture.",
    ),
    SyntheticCase(
        case_id="Blind15_57_VagueFluLikeStartActuallyDKA", category="premature_diagnosis_trap",
        chief_complaint="feels like the flu, achy, tired, keeps throwing up since yesterday",
        demographics={"age": 26, "sex": "female"}, ground_truth_diagnosis="diabetic_ketoacidosis",
        answers={"past_medical_history": "type 1 diabetes, hasn't been able to keep insulin down with the vomiting",
                  "associated_symptoms": "very thirsty, breathing feels different, deeper"},
        exam_results={"mental_status_exam": "slightly drowsy", "vital_signs": "BP 104/66, HR 112, RR 28, Temp 37.5, SpO2 97%"},
        test_results={"glucose_point_of_care": "critically high glucose", "ketones": "large ketones", "abg": "metabolic acidosis"},
        notes="Early wording ('feels like the flu') invites a premature viral-illness impression; "
              "the diabetes history and confirmatory labs must still be pursued rather than settling "
              "for the first plausible benign explanation.",
    ),

    # ================= late_diagnosis_trap (1) =================
    SyntheticCase(
        case_id="Blind15_58_ComplexElderlyMultiSystemSepsisMustNotDawdle", category="late_diagnosis_trap",
        chief_complaint="she's got a bit of everything going on today, more tired than usual, a little confused, and now this fever on top of it",
        demographics={"age": 84, "sex": "female"}, ground_truth_diagnosis="sepsis",
        answers={"past_medical_history": "diabetes, chronic kidney disease, and a recent hip fracture repair",
                  "medication": "on several medications including a diuretic and a blood thinner",
                  "associated_symptoms": "family says the confusion started today, no clear cough or urinary complaint volunteered",
                  "onset": "gradually over the last day"},
        exam_results={"mental_status_exam": "disoriented to time", "skin_exam": "surgical hip incision looks red and warm",
                      "vital_signs": "BP 88/54, HR 118, RR 24, Temp 38.6, SpO2 94%"},
        test_results={"lactate": "elevated lactate", "cbc": "elevated white blood cell count", "blood_culture": "pending, drawn"},
        notes="Multiple comorbidities and medications create plenty of plausible distractors (a "
              "medication side effect, a baseline-confusion red herring, an isolated wound issue) -- "
              "tests that the agent still converges on sepsis efficiently from the vitals/exam/lab "
              "picture rather than spending the turn budget chasing every comorbidity in sequence.",
    ),

    # ================= conflicting_evidence (1) =================
    SyntheticCase(
        case_id="Blind15_59_NormalECGButHighRiskHistoryChestPain", category="conflicting_evidence",
        chief_complaint="a tight squeeze in my chest that kicked in hauling groceries up two flights of stairs",
        demographics={"age": 67, "sex": "male"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "within the last hour, brought on by the exertion", "associated_symptoms": "sweaty, a bit queasy",
                  "past_medical_history": "had a heart attack a few years back, also diabetic and his cholesterol runs high"},
        exam_results={"vital_signs": "BP 142/88, HR 92, RR 16, Temp 36.9, SpO2 97%"},
        test_results={"ecg": "normal sinus rhythm, no acute ST changes", "troponin": "mildly elevated troponin"},
        notes="A reassuring-looking ECG conflicts with a genuinely high-risk history and a real "
              "confirmatory troponin -- tests that a single reassuring finding doesn't override the "
              "rest of the specific evidence.",
    ),

    # ================= sparse_evidence (1) =================
    SyntheticCase(
        case_id="Blind15_60_MinimalDetailBladderInfection", category="sparse_evidence",
        chief_complaint="bathroom stuff has been off since yesterday",
        demographics={"age": 29, "sex": "female"}, ground_truth_diagnosis="uncomplicated_cystitis",
        answers={"associated_symptoms": "burns a bit"},
        exam_results={"vital_signs": "BP 114/70, HR 78, RR 14, Temp 36.9, SpO2 99%"},
        test_results={"urinalysis": "positive leukocyte esterase and nitrites"},
    ),

    # ================= benign_mimic (+1, appended: vasovagal_syncope was the one Tier-1 diagnosis
    #     not yet touched above -- a fresh trigger/wording from any prior blind set's own fainting
    #     case) =================
    SyntheticCase(
        case_id="Blind15_61_StoodTooLongAtTheWeddingThenWentDown", category="benign_mimic",
        chief_complaint="I was on my feet in the sun for the whole outdoor ceremony and then just crumpled for a couple seconds",
        demographics={"age": 22, "sex": "female"}, ground_truth_diagnosis="vasovagal_syncope",
        answers={"onset": "got a wave of heat and nausea right beforehand, then lost consciousness briefly",
                  "aggravating": "being locked in place standing for so long in the heat", "associated_symptoms": "no chest pain at all, snapped back quickly and felt normal again",
                  "past_medical_history": "skipped breakfast that day"},
        exam_results={"cardiac_auscultation": "normal heart sounds, regular rhythm", "vital_signs": "BP 106/68, HR 68, RR 14, Temp 36.9, SpO2 99%"},
        test_results={"ecg": "normal sinus rhythm, no acute changes"},
    ),
]
