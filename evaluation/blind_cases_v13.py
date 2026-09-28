"""Blind evaluation set v13 (critical-generalization hardening round).

Why v13: this round audited (never tuned directly against) Blind v12's 4 critical misses at an
ABSTRACT failure-category level only -- candidate present-then-dropped, objective evidence not
recognized due to narrow vocabulary, lay-language/risk-context not reaching candidate pool
membership, and converging generic-keyword volume outranking a decisive confirmatory finding -- and
fixed each root cause generically in nova_agent/candidate_generator.py, differential.py,
objective_evidence.py, and matching.py (see the "Generalize critical presentation recognition
without blind-case tuning" commit). Per the blind-set discipline (identical to v6/v8/v9/v10/v11/
v12): **Blind v3-v12 are now REFERENCE-ONLY**. This fresh set is authored AFTER the reasoning
freeze (FINAL_REASONING_SHA faa1701a1954239074cc9dea1137525eb19b3a22) and is the untouched check for
the current code.

Authoring rules (identical discipline to every prior blind set):
  1. Written AFTER this round's generalization-hardening code was complete and frozen.
  2. No sentence/clause/phrase copied from evaluation/cases.py, held_out_cases.py,
     generalization_cases_v2.py, generalization_stress_cases.py, or any blind_cases_v3..v12.py --
     every vignette is freshly written, nothing keyed to a prior miss (leakage scan covers this).
     v13 deliberately does NOT reword v12's own ACS/PE/GI-bleed/stroke miss cases merely to prove
     those four now pass -- it samples a fresh, balanced distribution across the full required
     category spread instead.
  3. 52 cases -- prefer genuinely distinct cases over a padded larger count.
  4. Representative across: common disease, critical emergency, dangerous mimic, benign mimic,
     unseen lay phrasing, objective-evidence-heavy, risk-context-heavy, medication-risk,
     negative-evidence-heavy, atypical presentation, elderly, pediatric, pregnancy, polypharmacy,
     multimorbidity, mixed-language, long-tail Tier-2, UNKNOWN/OOD, retrieval-miss trap, safety
     trap, over-testing trap, premature-diagnosis trap, conflicting evidence, sparse evidence.
     NOT an exhaustive enumeration, NOT tuned to any case.
  5. ground_truth_diagnosis frozen BEFORE the first run (see blind_v13_manifest.json SHA-256).
     Tier-1 targets use knowledge/diseases ids (validated against the real 34-diagnosis KB);
     Tier-2/long-tail use 'tier2:<id>' (validated against the real default ontology catalog),
     scoring_expected=False (excluded from the accuracy denominator, still checked for safe/crash/
     turn-limit behavior); unknown/OOD/sparse-information use 'unknown' + scoring_expected=False.
     FIRST RUN happens exactly once, reported as-is, never re-tuned against.

Hand-authored synthetic vignettes, never real patient data.
"""

from __future__ import annotations

from evaluation.cases import SyntheticCase

BLIND_CASES_V13 = [
    # --- common (Tier-1, non-critical) -----------------------------------------------------------
    SyntheticCase(
        case_id="Blind13_01_ColdSymptomsAfterKidsGotSick", category="common",
        chief_complaint="stuffy nose and a scratchy throat since yesterday, my kids had the same thing last week",
        demographics={"age": 33, "sex": "female"}, ground_truth_diagnosis="viral_uri",
        answers={"associated_symptoms": "mild cough, no shortness of breath", "past_medical_history": "none"},
        exam_results={"vital_signs": "BP 116/74, HR 76, RR 14, Temp 37.3, SpO2 99%"},
    ),
    SyntheticCase(
        case_id="Blind13_02_UncomplicatedUTI", category="common",
        chief_complaint="it stings when I urinate and I keep needing to go every few minutes",
        demographics={"age": 27, "sex": "female"}, ground_truth_diagnosis="uncomplicated_cystitis",
        answers={"associated_symptoms": "mild suprapubic discomfort, no fever, no flank pain"},
        exam_results={"vital_signs": "BP 116/72, HR 78, RR 16, Temp 37.0, SpO2 99%"},
        test_results={"urinalysis": "positive leukocyte esterase and nitrites"},
    ),
    SyntheticCase(
        case_id="Blind13_03_ClassicViralGastroenteritis", category="common",
        chief_complaint="I've been throwing up and having watery diarrhea since last night",
        demographics={"age": 29, "sex": "male"}, ground_truth_diagnosis="gastroenteritis",
        answers={"associated_symptoms": "crampy belly pain, no blood in stool", "history": "coworker had the same bug"},
        exam_results={"vital_signs": "BP 112/70, HR 92, RR 16, Temp 37.6, SpO2 99%"},
    ),
    SyntheticCase(
        case_id="Blind13_04_StressTensionHeadache", category="common",
        chief_complaint="a dull band-like pressure around my head that's been on and off all week at work",
        demographics={"age": 41, "sex": "male"}, ground_truth_diagnosis="tension_headache",
        answers={"associated_symptoms": "no nausea, no light sensitivity", "history": "big deadline this week, not sleeping well"},
        exam_results={"vital_signs": "BP 122/80, HR 74, RR 14, Temp 36.8, SpO2 99%",
                      "neuro_exam": "fully intact, no focal deficit"},
    ),
    # --- critical emergency --------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind13_05_PressureAcrossChestOnExertion", category="critical",
        chief_complaint="a heavy pressure spread across my chest while I was mowing the lawn and it hasn't gone away",
        demographics={"age": 61, "sex": "male"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "30 minutes, constant", "associated_symptoms": "sweaty, queasy, left arm heaviness",
                 "past_medical_history": "elevated cholesterol, type 2 diabetes"},
        exam_results={"vital_signs": "BP 148/90, HR 98, RR 18, Temp 36.9, SpO2 96%"},
        test_results={"ecg": "ST elevation in the anterior leads", "troponin": "troponin flagged high"},
    ),
    SyntheticCase(
        case_id="Blind13_06_SuddenBreathlessnessAfterSurgery", category="critical",
        chief_complaint="all of a sudden I can't get enough air in and there's a sharp stab on my right side when I breathe",
        demographics={"age": 52, "sex": "female"}, ground_truth_diagnosis="pulmonary_embolism",
        answers={"onset": "sudden, 40 minutes ago", "history": "knee replacement surgery four days ago"},
        exam_results={"vital_signs": "BP 106/68, HR 124, RR 27, Temp 37.1, SpO2 88%"},
        test_results={"d_dimer": "d-dimer above the upper limit of normal"},
    ),
    SyntheticCase(
        case_id="Blind13_07_SuddenRightSidedWeaknessAndGarbledWords", category="critical",
        chief_complaint="his right arm suddenly stopped working and he's not making sense when he talks",
        demographics={"age": 76, "sex": "male"}, ground_truth_diagnosis="ischemic_stroke",
        answers={"onset": "40 minutes ago, sudden", "past_medical_history": "atrial fibrillation, not on blood thinners"},
        exam_results={"vital_signs": "BP 172/96, HR 90 irregular, RR 18, Temp 36.9, SpO2 97%",
                      "neuro_exam": "right arm and leg weakness, expressive aphasia"},
        test_results={"ct_head": "no hemorrhage"},
    ),
    SyntheticCase(
        case_id="Blind13_08_ConfusedFeverishNursingHomeResident", category="critical",
        chief_complaint="my mother is much more confused than normal and burning up, the nursing home called us",
        demographics={"age": 84, "sex": "female"}, ground_truth_diagnosis="sepsis",
        answers={"past_medical_history": "dementia, recurrent urinary infections",
                 "associated_symptoms": "foul-smelling urine, hasn't been eating"},
        exam_results={"vital_signs": "BP 88/54, HR 118, RR 26, Temp 39.4, SpO2 93%"},
        test_results={"lactate": "lactate 4.2 mmol/L", "urinalysis": "positive leukocyte esterase and nitrites"},
    ),
    SyntheticCase(
        case_id="Blind13_09_ExtremeThirstAndFruitySmellingBreath", category="critical",
        chief_complaint="I can't stop drinking water and going to the bathroom, and my breath smells strange",
        demographics={"age": 19, "sex": "male"}, ground_truth_diagnosis="diabetic_ketoacidosis",
        answers={"onset": "two days, worsening", "past_medical_history": "type 1 diabetes, pump ran out of insulin"},
        exam_results={"vital_signs": "BP 100/62, HR 122, RR 30, Temp 37.0, SpO2 98%"},
        test_results={"glucose_point_of_care": "glucose 512 mg/dL", "ketones": "large ketones"},
    ),
    SyntheticCase(
        case_id="Blind13_10_ThroatSwellingAfterShellfish", category="critical",
        chief_complaint="my lips and tongue swelled up right after dinner and now I'm wheezing",
        demographics={"age": 26, "sex": "female"}, ground_truth_diagnosis="anaphylaxis",
        answers={"onset": "10 minutes ago", "history": "ate shrimp for the first time in years",
                 "associated_symptoms": "hives all over, throat feels tight"},
        exam_results={"vital_signs": "BP 84/52, HR 128, RR 28, Temp 37.0, SpO2 91%",
                      "skin_exam": "diffuse urticaria, lip and tongue swelling"},
    ),
    # --- dangerous mimic (presents like something benign but is not) ---------------------------
    SyntheticCase(
        case_id="Blind13_11_RippingBackPainThoughtItWasAPulledMuscle", category="dangerous_mimic",
        chief_complaint="a ripping pain tore through my back while I was gardening, figured I just strained something",
        demographics={"age": 67, "sex": "male"}, ground_truth_diagnosis="aortic_dissection",
        answers={"onset": "sudden, 25 minutes ago", "past_medical_history": "hypertension, never takes his pills regularly"},
        exam_results={"vital_signs": "right arm BP 174/98, left arm BP 132/80, HR 94, RR 20, Temp 36.8, SpO2 96%"},
        test_results={"cxr": "widened mediastinum"},
    ),
    SyntheticCase(
        case_id="Blind13_12_LowerAbdominalPainThoughtItWasABladderInfection", category="dangerous_mimic",
        chief_complaint="sharp pain low in my belly, figured it was just another bladder infection",
        demographics={"age": 29, "sex": "female"}, ground_truth_diagnosis="ectopic_pregnancy",
        answers={"onset": "6 hours, worsening", "history": "period is about three weeks late",
                 "associated_symptoms": "some light vaginal spotting, feels lightheaded standing up"},
        exam_results={"vital_signs": "BP 96/60, HR 112, RR 18, Temp 37.0, SpO2 98%",
                      "abdominal_exam": "left lower quadrant tenderness"},
        test_results={"beta_hcg": "positive pregnancy test"},
    ),
    SyntheticCase(
        case_id="Blind13_13_WorstHeadacheThoughtItWasJustAMigraine", category="dangerous_mimic",
        chief_complaint="the worst headache of my life hit me like a thunderclap while I was lifting weights",
        demographics={"age": 45, "sex": "female"}, ground_truth_diagnosis="subarachnoid_hemorrhage",
        answers={"onset": "sudden, instant peak, 30 minutes ago", "associated_symptoms": "vomited once, neck feels stiff",
                 "past_medical_history": "occasional migraines, but says this is completely different"},
        exam_results={"vital_signs": "BP 158/94, HR 88, RR 16, Temp 36.9, SpO2 98%",
                      "meningeal_signs": "neck stiffness present"},
        test_results={"ct_head": "subarachnoid blood in the basal cisterns"},
    ),
    # --- benign mimic (presents alarmingly but is benign) ---------------------------------------
    SyntheticCase(
        case_id="Blind13_14_ChestTightnessDuringExamStress", category="benign_mimic",
        chief_complaint="my chest got tight and my heart was pounding right in the middle of my final exam",
        demographics={"age": 21, "sex": "male"}, ground_truth_diagnosis="panic_attack",
        answers={"onset": "sudden, 20 minutes, now easing off", "associated_symptoms": "hands tingling, felt like doom was coming",
                 "history": "extremely stressed about this exam, drank several energy drinks"},
        exam_results={"vital_signs": "BP 126/78, HR 110, RR 24, Temp 36.8, SpO2 99%"},
        test_results={"ecg": "sinus tachycardia, no ischemic changes"},
    ),
    SyntheticCase(
        case_id="Blind13_15_RoomSpinsOnlyWhenTurningOverInBed", category="benign_mimic",
        chief_complaint="every time I roll over in bed the room spins violently for a few seconds then it stops",
        demographics={"age": 58, "sex": "female"}, ground_truth_diagnosis="bppv",
        answers={"associated_symptoms": "no weakness, no double vision, no trouble speaking",
                 "past_medical_history": "none"},
        exam_results={"vital_signs": "BP 120/76, HR 72, RR 16, Temp 36.7, SpO2 99%",
                      "neuro_exam": "fully intact, no focal deficit"},
    ),
    SyntheticCase(
        case_id="Blind13_16_SharpChestPainWorseWhenPressingOnIt", category="benign_mimic",
        chief_complaint="sharp pain right over my breastbone that gets worse when I push on it or take a deep breath",
        demographics={"age": 24, "sex": "male"}, ground_truth_diagnosis="musculoskeletal_chest_pain",
        answers={"onset": "started after a heavy gym session two days ago", "associated_symptoms": "no sweating, no arm pain",
                 "past_medical_history": "none"},
        exam_results={"vital_signs": "BP 118/76, HR 74, RR 16, Temp 36.8, SpO2 99%",
                      "cardiac_auscultation": "reproducible tenderness over the costochondral joints"},
        test_results={"ecg": "normal sinus rhythm, no ischemic changes"},
    ),
    # --- unseen lay phrasing (deliberately avoids clinical vocabulary) --------------------------
    SyntheticCase(
        case_id="Blind13_17_CollapsedLungAfterCarAccident", category="unseen_lay_phrasing",
        chief_complaint="ever since the crash it feels like my chest won't fill up all the way and the pain is way worse on one side",
        demographics={"age": 34, "sex": "male"}, ground_truth_diagnosis="tension_pneumothorax",
        answers={"history": "hit the steering wheel in a car accident an hour ago"},
        exam_results={"vital_signs": "BP 88/56, HR 130, RR 32, Temp 36.9, SpO2 86%",
                      "lung_auscultation": "absent breath sounds on the right, trachea shifted to the left"},
    ),
    SyntheticCase(
        case_id="Blind13_18_BrainInfectionDescribedAsFluWithNeckPain", category="unseen_lay_phrasing",
        chief_complaint="feels like the worst flu ever and my neck won't bend forward, bright lights are killing me",
        demographics={"age": 22, "sex": "female"}, ground_truth_diagnosis="meningitis",
        answers={"onset": "12 hours, rapidly worsening", "associated_symptoms": "a few small purple spots on her legs"},
        exam_results={"vital_signs": "BP 100/64, HR 120, RR 22, Temp 39.6, SpO2 96%",
                      "meningeal_signs": "neck stiffness, positive Kernig sign",
                      "skin_exam": "scattered petechiae on lower legs"},
    ),
    # --- objective-evidence-heavy (decisive labs must dominate vague symptom text) ---------------
    SyntheticCase(
        case_id="Blind13_19_VagueWeaknessDecisivePotassiumOnDialysisPatient", category="objective_evidence_heavy",
        chief_complaint="I just feel off and weak all over, can't really describe it better than that",
        demographics={"age": 63, "sex": "male"}, ground_truth_diagnosis="severe_electrolyte_disorder",
        answers={"past_medical_history": "end-stage renal disease on dialysis", "history": "missed his last two dialysis sessions"},
        exam_results={"vital_signs": "BP 128/82, HR 52, RR 16, Temp 36.7, SpO2 98%"},
        test_results={"potassium": "potassium 7.4 mEq/L", "ecg": "peaked T waves"},
    ),
    SyntheticCase(
        case_id="Blind13_20_MildBellyDiscomfortDecisiveLipase", category="objective_evidence_heavy",
        chief_complaint="just some mild discomfort in my upper belly after dinner, didn't think much of it",
        demographics={"age": 47, "sex": "male"}, ground_truth_diagnosis="acute_pancreatitis",
        answers={"onset": "6 hours, gradually worsening", "history": "heavy drinker, big night out yesterday",
                 "associated_symptoms": "a couple episodes of vomiting"},
        exam_results={"vital_signs": "BP 118/76, HR 102, RR 18, Temp 37.4, SpO2 97%"},
        test_results={"lipase": "lipase above the upper limit of normal, roughly four times the reference range"},
    ),
    # --- risk-context-heavy ----------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind13_21_PalpitationsInPatientWithKnownHeartDisease", category="risk_context_heavy",
        chief_complaint="my heart suddenly started pounding irregularly and I feel a bit lightheaded",
        demographics={"age": 70, "sex": "male"}, ground_truth_diagnosis="cardiac_arrhythmia",
        answers={"onset": "sudden, 45 minutes ago", "past_medical_history": "structural heart disease, prior stent",
                 "history": "drank several cups of coffee this morning"},
        exam_results={"vital_signs": "BP 108/70, HR 152 irregular, RR 18, Temp 36.8, SpO2 97%"},
        test_results={"ecg": "irregularly irregular rhythm, no discrete P waves"},
    ),
    SyntheticCase(
        case_id="Blind13_22_CalfSwellingAfterLongFlight", category="risk_context_heavy",
        chief_complaint="my calf has been swollen and sore for two days, noticed it after I got back from my trip",
        demographics={"age": 56, "sex": "female"}, ground_truth_diagnosis="tier2:deep_vein_thrombosis",
        answers={"onset": "two days, worsening", "social_history": "long flight home last week",
                 "past_medical_history": "on the pill"},
        exam_results={"vital_signs": "BP 122/78, HR 88, RR 16, Temp 37.1, SpO2 98%",
                      "extremity_exam": "unilateral left calf swelling and tenderness"},
        scoring_expected=False,
    ),
    # --- medication-risk --------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind13_23_FatigueAndDarkStoolsOnBloodThinnersAndPainkillers", category="medication_risk",
        chief_complaint="I've been so tired lately and my stool has looked really dark, almost black",
        demographics={"age": 69, "sex": "male"}, ground_truth_diagnosis="gi_bleeding",
        answers={"medications": "apixaban, and I take naproxen most days for my knee", "associated_symptoms": "dizzy when I stand up"},
        exam_results={"vital_signs": "BP 96/60, HR 114, RR 18, Temp 36.9, SpO2 97%"},
        test_results={"hemoglobin": "hemoglobin 7.4 g/dL"},
    ),
    SyntheticCase(
        case_id="Blind13_24_ConfusedAndSweatyOnMultipleDiabetesMedications", category="medication_risk",
        chief_complaint="he got shaky, sweaty, and confused about twenty minutes ago and isn't making sense",
        demographics={"age": 78, "sex": "male"}, ground_truth_diagnosis="hypoglycemia",
        answers={"medications": "glipizide and lantus, family says he skipped lunch today"},
        exam_results={"vital_signs": "BP 128/78, HR 104, RR 18, Temp 36.6, SpO2 98%",
                      "mental_status_exam": "confused, diaphoretic"},
        test_results={"glucose_point_of_care": "glucose 38 mg/dL"},
    ),
    # --- negative-evidence-heavy (many pertinent negatives, still diagnosable) --------------------
    SyntheticCase(
        case_id="Blind13_25_MigratingBellyPainDespiteFewOtherSymptoms", category="negative_evidence_heavy",
        chief_complaint="pain started around my belly button and moved down to the lower right side over the day",
        demographics={"age": 16, "sex": "male"}, ground_truth_diagnosis="appendicitis",
        answers={"onset": "14 hours, migrated and worsening",
                 "associated_symptoms": "denies vomiting, denies diarrhea, denies fever, just a little queasy"},
        exam_results={"vital_signs": "BP 118/72, HR 96, RR 16, Temp 37.5, SpO2 99%",
                      "abdominal_exam": "right lower quadrant tenderness with guarding"},
        test_results={"cbc": "mild leukocytosis"},
    ),
    SyntheticCase(
        case_id="Blind13_26_FlankPainWithoutObviousInfectionSigns", category="negative_evidence_heavy",
        chief_complaint="my side and back have been hurting and I feel warm, but nothing else really",
        demographics={"age": 31, "sex": "female"}, ground_truth_diagnosis="pyelonephritis",
        answers={"onset": "2 days", "associated_symptoms": "denies vomiting, denies vaginal discharge, mild urinary frequency only"},
        exam_results={"vital_signs": "BP 112/70, HR 100, RR 18, Temp 38.4, SpO2 98%",
                      "abdominal_exam": "left costovertebral angle tenderness"},
        test_results={"urinalysis": "positive leukocyte esterase and nitrites"},
    ),
    # --- atypical presentation ---------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind13_27_ElderlyPneumoniaPresentingAsConfusion", category="atypical_presentation",
        chief_complaint="grandpa hasn't been himself the last day, more confused than usual, not really coughing much",
        demographics={"age": 88, "sex": "male"}, ground_truth_diagnosis="pneumonia",
        answers={"associated_symptoms": "mild cough, decreased appetite", "past_medical_history": "mild dementia at baseline"},
        exam_results={"vital_signs": "BP 108/68, HR 100, RR 24, Temp 38.1, SpO2 91%",
                      "lung_auscultation": "crackles at the right base"},
        test_results={"cxr": "right lower lobe consolidation"},
    ),
    SyntheticCase(
        case_id="Blind13_28_YoungAthleteWithFatigueAndVagueChestDiscomfortAfterViralIllness", category="atypical_presentation",
        chief_complaint="I've just felt wiped out and my chest feels weird ever since I had that cold last week",
        demographics={"age": 23, "sex": "male"}, ground_truth_diagnosis="tier2:myocarditis",
        answers={"history": "had a bad cold with fever about ten days ago", "associated_symptoms": "mild exertional chest discomfort"},
        exam_results={"vital_signs": "BP 108/68, HR 104, RR 18, Temp 37.2, SpO2 97%"},
        test_results={"troponin": "troponin mildly elevated", "ecg": "diffuse ST changes"},
        scoring_expected=False,
    ),
    # --- elderly --------------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind13_29_ElderlyRightUpperQuadrantPainAfterFattyMeal", category="elderly",
        chief_complaint="sharp pain under my right ribs that started after the big fatty dinner we had last night",
        demographics={"age": 74, "sex": "female"}, ground_truth_diagnosis="tier2:cholecystitis",
        answers={"onset": "12 hours, constant now", "associated_symptoms": "nausea, one episode of vomiting"},
        exam_results={"vital_signs": "BP 130/80, HR 96, RR 18, Temp 38.0, SpO2 98%",
                      "abdominal_exam": "right upper quadrant tenderness, positive Murphy sign"},
        scoring_expected=False,
    ),
    # --- pediatric ------------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind13_30_ToddlerWheezingAfterColdSymptoms", category="pediatric",
        chief_complaint="my three-year-old is wheezing and breathing fast, started with a runny nose two days ago",
        demographics={"age": 3, "sex": "male"}, ground_truth_diagnosis="asthma_copd_exacerbation",
        answers={"past_medical_history": "has wheezed with colds before", "associated_symptoms": "using extra chest muscles to breathe"},
        exam_results={"vital_signs": "BP 96/60, HR 128, RR 36, Temp 37.6, SpO2 93%",
                      "lung_auscultation": "diffuse expiratory wheezing"},
    ),
    SyntheticCase(
        case_id="Blind13_31_ToddlerSealLikeCoughAtNight", category="pediatric",
        chief_complaint="my two-year-old woke up with a cough that sounds like a seal barking and a raspy voice",
        demographics={"age": 2, "sex": "female"}, ground_truth_diagnosis="tier2:croup",
        answers={"onset": "started tonight, worse lying down", "associated_symptoms": "noisy breathing when upset"},
        exam_results={"vital_signs": "BP 92/58, HR 120, RR 30, Temp 38.0, SpO2 96%",
                      "lung_auscultation": "inspiratory stridor when agitated"},
        scoring_expected=False,
    ),
    # --- pregnancy ------------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind13_32_PregnantWomanWithSwellingHeadacheAndHighBloodPressure", category="pregnancy",
        chief_complaint="my hands and face have been puffy and I have a pounding headache that won't go away",
        demographics={"age": 30, "sex": "female"}, ground_truth_diagnosis="tier2:preeclampsia",
        answers={"history": "32 weeks pregnant", "associated_symptoms": "seeing some spots in my vision"},
        exam_results={"vital_signs": "BP 168/108, HR 92, RR 18, Temp 36.9, SpO2 98%"},
        test_results={"urinalysis": "significant protein on dipstick"},
        scoring_expected=False,
    ),
    # --- polypharmacy ---------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind13_33_ElderlyOnManyMedicationsWithWeaknessAndSlowPulse", category="polypharmacy",
        chief_complaint="I've felt weak and a little dizzy the last two days, hard to put my finger on why",
        demographics={"age": 81, "sex": "female"}, ground_truth_diagnosis="severe_electrolyte_disorder",
        answers={"past_medical_history": "chronic kidney disease",
                 "medications": "lisinopril, spironolactone, and a potassium supplement my doctor added last month"},
        exam_results={"vital_signs": "BP 118/72, HR 48, RR 16, Temp 36.8, SpO2 98%"},
        test_results={"potassium": "potassium 6.8 mEq/L", "ecg": "peaked T waves, widened QRS"},
    ),
    # --- multimorbidity -------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind13_34_DiabeticCatheterizedPatientWithFeverAndLowBloodPressure", category="multimorbidity",
        chief_complaint="dad has been running a fever and seems really out of it since this morning",
        demographics={"age": 72, "sex": "male"}, ground_truth_diagnosis="sepsis",
        answers={"past_medical_history": "type 2 diabetes, chronic kidney disease, has a long-term urinary catheter",
                 "associated_symptoms": "cloudy, foul-smelling urine per caregiver"},
        exam_results={"vital_signs": "BP 90/56, HR 116, RR 24, Temp 38.9, SpO2 93%"},
        test_results={"lactate": "lactate 3.8 mmol/L", "urinalysis": "positive leukocyte esterase and nitrites"},
    ),
    # --- mixed-language -------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind13_35_KoreanPhrasedChestPressure", category="mixed_language",
        chief_complaint="가슴이 아파요, and there's a heavy 압박감 that's been there for an hour",
        demographics={"age": 59, "sex": "male"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"associated_symptoms": "sweating a lot, nauseated", "past_medical_history": "high cholesterol, smoker"},
        exam_results={"vital_signs": "BP 152/94, HR 100, RR 19, Temp 36.9, SpO2 95%"},
        test_results={"ecg": "ST depression in the lateral leads", "troponin": "troponin above the reference range"},
    ),
    SyntheticCase(
        case_id="Blind13_36_JapanesePhrasedDyspnea", category="mixed_language",
        chief_complaint="息が苦しい, all of a sudden I can't breathe right and my chest hurts when I inhale",
        demographics={"age": 48, "sex": "female"}, ground_truth_diagnosis="pulmonary_embolism",
        answers={"history": "long car trip two days ago"},
        exam_results={"vital_signs": "BP 110/70, HR 118, RR 26, Temp 37.0, SpO2 90%"},
        test_results={"d_dimer": "d-dimer flagged high"},
    ),
    # --- long-tail Tier-2 -------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind13_37_ScalpTendernessAndJawPainWhileChewing", category="long_tail",
        chief_complaint="my scalp is tender to touch and my jaw gets tired and achy when I chew",
        demographics={"age": 71, "sex": "female"}, ground_truth_diagnosis="tier2:giant_cell_arteritis",
        answers={"associated_symptoms": "new headache, some blurry vision on the right"},
        exam_results={"vital_signs": "BP 138/84, HR 84, RR 16, Temp 37.2, SpO2 98%"},
        scoring_expected=False,
    ),
    SyntheticCase(
        case_id="Blind13_38_SuddenSevereTesticularPainInTeen", category="long_tail",
        chief_complaint="sudden really bad pain in one testicle, started about an hour ago",
        demographics={"age": 15, "sex": "male"}, ground_truth_diagnosis="tier2:testicular_torsion",
        answers={"associated_symptoms": "nausea, one episode of vomiting"},
        exam_results={"vital_signs": "BP 122/76, HR 100, RR 18, Temp 36.9, SpO2 99%",
                      "genital_exam": "high-riding, tender, swollen right testicle"},
        scoring_expected=False,
    ),
    SyntheticCase(
        case_id="Blind13_39_AscendingLegWeaknessAfterDiarrheaIllness", category="long_tail",
        chief_complaint="my legs have gotten weaker over the last three days, starting from my feet moving up",
        demographics={"age": 38, "sex": "male"}, ground_truth_diagnosis="tier2:guillain_barre",
        answers={"history": "had a bad stomach bug about two weeks ago", "associated_symptoms": "tingling in both feet"},
        exam_results={"vital_signs": "BP 118/74, HR 88, RR 18, Temp 36.9, SpO2 98%",
                      "neuro_exam": "symmetric ascending weakness, absent reflexes in the legs"},
        scoring_expected=False,
    ),
    SyntheticCase(
        case_id="Blind13_40_RacingHeartFeverAndTremorInKnownThyroidDisease", category="long_tail",
        chief_complaint="my heart is racing, I'm burning up, and my hands won't stop shaking",
        demographics={"age": 34, "sex": "female"}, ground_truth_diagnosis="tier2:thyroid_storm",
        answers={"past_medical_history": "Graves disease, ran out of her thyroid medication weeks ago",
                  "associated_symptoms": "very agitated, sweating heavily"},
        exam_results={"vital_signs": "BP 148/70, HR 152, RR 24, Temp 39.8, SpO2 97%"},
        scoring_expected=False,
    ),
    SyntheticCase(
        case_id="Blind13_41_SeverePainOutOfProportionToExamAfterAtrialFibrillation", category="long_tail",
        chief_complaint="the pain in my belly is unbearable, way worse than anything the doctor can find on exam",
        demographics={"age": 79, "sex": "male"}, ground_truth_diagnosis="tier2:mesenteric_ischemia",
        answers={"past_medical_history": "atrial fibrillation", "onset": "2 hours, severe and constant"},
        exam_results={"vital_signs": "BP 100/64, HR 110 irregular, RR 20, Temp 37.3, SpO2 96%",
                      "abdominal_exam": "diffusely tender but soft, pain out of proportion to findings"},
        test_results={"lactate": "lactate 5.1 mmol/L"},
        scoring_expected=False,
    ),
    # --- UNKNOWN / OOD ----------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind13_42_VagueMalaiseNoLocalizingFeatures", category="unknown_ood",
        chief_complaint="I just don't feel like myself lately, can't really point to anything specific",
        demographics={"age": 40, "sex": "female"}, ground_truth_diagnosis="unknown",
        answers={"associated_symptoms": "denies fever, denies weight loss, denies pain anywhere"},
        exam_results={"vital_signs": "BP 118/76, HR 74, RR 15, Temp 36.9, SpO2 99%"},
        scoring_expected=False,
        notes="Deliberately underspecified -- genuinely insufficient information for any single diagnosis; checked for safe, non-crashing handling only.",
    ),
    SyntheticCase(
        case_id="Blind13_43_InventedNonclinicalComplaint", category="unknown_ood",
        chief_complaint="my zephyrtonic sense has been completely off-kilter since Tuesday",
        demographics={"age": 45, "sex": "male"}, ground_truth_diagnosis="unknown",
        answers={},
        exam_results={"vital_signs": "BP 120/78, HR 76, RR 16, Temp 36.8, SpO2 99%"},
        scoring_expected=False,
        notes="A nonsense chief complaint -- checks the agent degrades gracefully instead of crashing or hallucinating false confidence.",
    ),
    # --- retrieval-miss trap (true dx a naive keyword search would likely miss) -------------------
    SyntheticCase(
        case_id="Blind13_44_HandFallsAsleepAtNightWakingHerUp", category="retrieval_miss_trap",
        chief_complaint="my hand keeps falling asleep at night and wakes me up, I have to shake it out",
        demographics={"age": 44, "sex": "female"}, ground_truth_diagnosis="tier2:carpal_tunnel_syndrome",
        answers={"associated_symptoms": "tingling mainly in the thumb and first two fingers", "history": "works long hours typing"},
        exam_results={"vital_signs": "BP 118/74, HR 72, RR 14, Temp 36.7, SpO2 99%",
                      "neuro_exam": "reduced sensation in the thumb, index, and middle fingers"},
        scoring_expected=False,
        notes="Retrieval-miss trap: 'hand falls asleep at night' shares almost no vocabulary with the formal name.",
    ),
    SyntheticCase(
        case_id="Blind13_45_BriefElectricShockFeelingInCheekWhenTouched", category="retrieval_miss_trap",
        chief_complaint="the side of my face gets zapped with a brief electric-shock feeling whenever I touch it or chew",
        demographics={"age": 62, "sex": "female"}, ground_truth_diagnosis="tier2:trigeminal_neuralgia",
        answers={"onset": "started a few weeks ago, episodes last seconds"},
        exam_results={"vital_signs": "BP 128/80, HR 76, RR 15, Temp 36.8, SpO2 99%",
                      "neuro_exam": "normal facial sensation between episodes"},
        scoring_expected=False,
        notes="Retrieval-miss trap: 'electric shock feeling in my cheek' shares almost no vocabulary with the formal name.",
    ),
    # --- safety trap (a subtle but dangerous finding hidden in an apparently benign story) --------
    SyntheticCase(
        case_id="Blind13_46_MinorFallWithDelayedOnsetBellyPain", category="safety_trap",
        chief_complaint="I fell off my bike yesterday, seemed fine, but now my belly is getting really rigid and painful",
        demographics={"age": 26, "sex": "male"}, ground_truth_diagnosis="acute_abdomen",
        answers={"onset": "started worsening about six hours ago", "history": "handlebar hit his stomach in the fall"},
        exam_results={"vital_signs": "BP 92/58, HR 122, RR 22, Temp 37.6, SpO2 97%",
                      "abdominal_exam": "rigid abdomen with rebound tenderness and guarding"},
        test_results={"cxr": "free air under the diaphragm"},
    ),
    # --- over-testing trap (clear diagnosis reachable quickly) -------------------------------------
    SyntheticCase(
        case_id="Blind13_47_ClearCutFacialDroopAndArmParalysisWatchForOvertesting", category="over_testing_trap",
        chief_complaint="the left side of her face suddenly dropped and she can't move her left arm at all, it happened while she was cooking",
        demographics={"age": 66, "sex": "female"}, ground_truth_diagnosis="ischemic_stroke",
        answers={"onset": "15 minutes ago, sudden", "past_medical_history": "atrial fibrillation, hypertension"},
        exam_results={"vital_signs": "BP 178/100, HR 92 irregular, RR 18, Temp 36.8, SpO2 97%",
                      "neuro_exam": "left facial droop, left arm plegia, dysarthria"},
        test_results={"ct_head": "no hemorrhage"},
        notes="Over-testing trap: presentation + exam + one confirmatory imaging result is already decisive -- watches whether the agent keeps ordering redundant tests before diagnosing.",
    ),
    SyntheticCase(
        case_id="Blind13_48_ObviousSTEMIWatchForOvertesting", category="over_testing_trap",
        chief_complaint="crushing chest pressure radiating down my left arm, started while shoveling snow twenty minutes ago",
        demographics={"age": 55, "sex": "male"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"associated_symptoms": "sweating profusely, nauseated", "past_medical_history": "smoker, high cholesterol"},
        exam_results={"vital_signs": "BP 100/62, HR 108, RR 20, Temp 36.9, SpO2 95%"},
        test_results={"ecg": "ST elevation in the inferior leads", "troponin": "troponin critically elevated"},
        notes="Over-testing trap: ECG + troponin are already diagnostic -- watches whether the agent orders unnecessary additional workup before diagnosing.",
    ),
    # --- premature-diagnosis trap (genuinely ambiguous early on) -----------------------------------
    SyntheticCase(
        case_id="Blind13_49_VagueEarlyDKANeedsWorkupBeforeDiagnosing", category="premature_diagnosis_trap",
        chief_complaint="I've just felt kind of sick and tired the last day, and my stomach hurts a bit",
        demographics={"age": 24, "sex": "female"}, ground_truth_diagnosis="diabetic_ketoacidosis",
        answers={"onset": "gradual, about 24 hours", "associated_symptoms": "increased thirst and urination, some nausea",
                 "past_medical_history": "type 1 diabetes, insulin pump alarm went off yesterday and she ignored it"},
        exam_results={"vital_signs": "BP 106/68, HR 106, RR 24, Temp 37.0, SpO2 97%"},
        notes="Premature-diagnosis trap: early presentation is genuinely nonspecific; punishes diagnosing before the glucose/ketone workup is obtained.",
    ),
    SyntheticCase(
        case_id="Blind13_50_VagueEarlyAppendicitisNeedsWorkupBeforeDiagnosing", category="premature_diagnosis_trap",
        chief_complaint="just some mild queasiness and discomfort around my belly button since this morning",
        demographics={"age": 20, "sex": "male"}, ground_truth_diagnosis="appendicitis",
        answers={"onset": "8 hours, mild and vague so far"},
        exam_results={"vital_signs": "BP 122/76, HR 88, RR 16, Temp 37.3, SpO2 99%",
                      "abdominal_exam": "mild diffuse tenderness, no localization yet"},
        notes="Premature-diagnosis trap: findings are genuinely nonlocalizing at this point; punishes diagnosing before repeat exam/labs clarify.",
    ),
    # --- conflicting evidence -----------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind13_51_FeverAndCoughButAlsoPleuriticPainAndRecentSurgery", category="conflicting_evidence",
        chief_complaint="I've had a cough and fever for two days, but today breathing in deep gives me a sharp stab on the right",
        demographics={"age": 51, "sex": "female"}, ground_truth_diagnosis="pneumonia",
        answers={"associated_symptoms": "productive cough with yellow phlegm", "past_medical_history": "no recent surgery, no travel, no immobility"},
        exam_results={"vital_signs": "BP 116/74, HR 96, RR 20, Temp 38.6, SpO2 94%",
                      "lung_auscultation": "crackles at the right base"},
        test_results={"cxr": "right lower lobe consolidation"},
        notes="Conflicting evidence: pleuritic pain suggests PE, but the productive cough/fever/consolidation and absence of any thrombotic risk factor point clearly to pneumonia instead.",
    ),
    # --- sparse evidence -------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind13_52_BriefLightheadednessOnStandingSparseInfo", category="sparse_evidence",
        chief_complaint="I got lightheaded for a few seconds when I stood up too fast this morning, feel fine now",
        demographics={"age": 68, "sex": "male"}, ground_truth_diagnosis="orthostatic_hypotension",
        answers={"associated_symptoms": "denies chest pain, denies palpitations before the episode",
                  "medications": "furosemide"},
        exam_results={"vital_signs": "BP 108/64, HR 78, RR 15, Temp 36.8, SpO2 99%",
                      "neuro_exam": "fully intact, no focal deficit"},
    ),
]
