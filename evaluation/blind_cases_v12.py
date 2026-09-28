"""Blind evaluation set v12 (competition retrieval-recall round).

Why v12: this round rebuilt Stage 1 of the competition retrieval pipeline (nova_agent/
retrieval_pipeline.py's multi-query weighted RRF fusion, objective-finding/imaging signal
weighting) and nova_agent/ontology/search.py's matching (typical_features indexing, IDF-like
token weighting). Per the blind-set discipline: **Blind v3-v11 are now REFERENCE-ONLY** -- v11 was
frozen before this round's retrieval-recall changes, so it can no longer be the untouched measure
of the current code. This fresh set is authored AFTER those changes were frozen (commit b3fdccd)
and is the untouched check for the current code.

Authoring rules (identical discipline to v6/v8/v9/v10/v11):
  1. Written AFTER all this round's reasoning/retrieval code was complete and frozen.
  2. No sentence/clause/phrase copied from evaluation/cases.py, held_out_cases.py,
     generalization_cases_v2.py, generalization_stress_cases.py, or blind_cases_v3..v11.py --
     every vignette is freshly written, nothing keyed to a prior miss (leakage scan covers this).
  3. Deliberately smaller than an ideal 60-80 given this round's time budget (32 cases, similar
     in scale to v11's own 24) -- reported honestly, not padded to look larger.
  4. Representative across: common conditions, time-critical conditions, dangerous mimic, benign
     mimic, retrieval-miss trap, long-tail Tier-2, shallow Tier-3, rare-condition wording,
     synonym/paraphrase presentation, objective-evidence-heavy, negative-evidence-heavy,
     multimorbidity, polypharmacy, elderly, pediatric, pregnancy, atypical presentation,
     mixed-language, sparse information, conflicting evidence, unit issue, inter-arm BP,
     over-testing trap, premature-diagnosis trap, duplicate-question trap, UNKNOWN/OOD
     presentation. NOT an exhaustive enumeration, NOT tuned to any case.
  5. ground_truth_diagnosis frozen BEFORE the first run (see blind_v12_manifest.json SHA-256).
     Tier-1 targets use knowledge/diseases ids; Tier-2/rare/long-tail use 'tier2:<id>' with
     scoring_expected=False (excluded from the accuracy denominator, still checked for safe/crash/
     turn-limit behavior); unknown/OOD/sparse-information use 'unknown' + scoring_expected=False.
     FIRST RUN happens exactly once, reported as-is, never re-tuned against.

Hand-authored synthetic vignettes, never real patient data.
"""

from __future__ import annotations

from evaluation.cases import SyntheticCase

BLIND_CASES_V12 = [
    # --- common (Tier-1) ---------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind12_01_ClassicViralSoreThroat", category="common",
        chief_complaint="scratchy sore throat and a runny nose since yesterday, feeling a bit run down",
        demographics={"age": 24, "sex": "female"}, ground_truth_diagnosis="viral_uri",
        answers={"associated_symptoms": "mild cough, no trouble breathing",
                 "past_medical_history": "none"},
        exam_results={"vital_signs": "BP 112/70, HR 78, RR 14, Temp 37.4, SpO2 99%"},
    ),
    SyntheticCase(
        case_id="Blind12_02_StraightforwardCystitis", category="common",
        chief_complaint="it burns every time I pass water and I've been going constantly since this morning",
        demographics={"age": 31, "sex": "female"}, ground_truth_diagnosis="uncomplicated_cystitis",
        answers={"associated_symptoms": "pressure low in the belly; no fever, no back pain"},
        exam_results={"vital_signs": "BP 118/74, HR 80, RR 16, Temp 36.9, SpO2 99%"},
        test_results={"urinalysis": "positive leukocyte esterase and nitrites"},
    ),
    # --- time-critical -------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind12_03_CrushingChestPainDiaphoresis", category="time_critical",
        chief_complaint="a crushing weight sat on my chest on the way up the stairs and won't let go",
        demographics={"age": 58, "sex": "male"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "45 minutes, constant since", "associated_symptoms": "clammy, sick to my stomach",
                 "past_medical_history": "high cholesterol"},
        exam_results={"vital_signs": "BP 150/92, HR 96, RR 19, Temp 36.8, SpO2 96%"},
        test_results={"ecg": "ST depression anterolateral leads", "troponin": "troponin above threshold"},
    ),
    SyntheticCase(
        case_id="Blind12_04_SuddenOneSidedWeaknessSlur", category="time_critical",
        chief_complaint="my face drooped on one side and my words came out garbled while eating lunch",
        demographics={"age": 70, "sex": "female"}, ground_truth_diagnosis="ischemic_stroke",
        answers={"onset": "35 minutes ago, sudden", "past_medical_history": "atrial fibrillation, not on anticoagulation"},
        exam_results={"vital_signs": "BP 168/94, HR 88 irregular, RR 18, Temp 36.9, SpO2 97%",
                      "neuro_exam": "right facial droop, right arm drift, slurred speech"},
        test_results={"ct_head": "no hemorrhage"},
    ),
    # --- dangerous mimic (presents like something benign but is not) ---------------------------
    SyntheticCase(
        case_id="Blind12_05_TearingBackPainMimicsMusclePull", category="dangerous_mimic",
        chief_complaint="a tearing pain ripped through my back like I pulled something lifting a box",
        demographics={"age": 63, "sex": "male"}, ground_truth_diagnosis="aortic_dissection",
        answers={"onset": "sudden, 20 minutes ago", "past_medical_history": "poorly controlled hypertension"},
        exam_results={"vital_signs": "left arm BP 168/96, right arm BP 128/80, HR 92, RR 20, Temp 36.8, SpO2 97%"},
        test_results={"cxr": "widened mediastinum"},
    ),
    SyntheticCase(
        case_id="Blind12_06_HeartburnMimicsACS", category="dangerous_mimic",
        chief_complaint="burning behind my breastbone that started right after dinner, thought it was just heartburn",
        demographics={"age": 55, "sex": "male"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "1 hour, worsening not relieved by antacid", "associated_symptoms": "sweating, left arm heaviness",
                 "past_medical_history": "diabetes"},
        exam_results={"vital_signs": "BP 144/88, HR 100, RR 18, Temp 36.9, SpO2 95%"},
        test_results={"ecg": "ST elevation inferior leads", "troponin": "markedly elevated"},
    ),
    # --- benign mimic (presents alarmingly but is benign) --------------------------------------
    SyntheticCase(
        case_id="Blind12_07_PalpitationsAfterCoffeeAnxious", category="benign_mimic",
        chief_complaint="my heart started racing out of nowhere and I got so scared I could barely breathe",
        demographics={"age": 27, "sex": "female"}, ground_truth_diagnosis="panic_attack",
        answers={"onset": "sudden, 15 minutes, resolving now", "associated_symptoms": "tingling fingers, tight chest",
                 "history": "three cups of coffee this morning, big exam today"},
        exam_results={"vital_signs": "BP 122/78, HR 104, RR 22, Temp 36.8, SpO2 99%"},
        test_results={"ecg": "sinus tachycardia, no ischemic changes"},
    ),
    SyntheticCase(
        case_id="Blind12_08_BriefRoomSpinningAfterRolling", category="benign_mimic",
        chief_complaint="the room spun violently for a few seconds every time I rolled over in bed last night",
        demographics={"age": 44, "sex": "female"}, ground_truth_diagnosis="bppv",
        answers={"associated_symptoms": "no weakness, no slurred speech, no double vision",
                 "past_medical_history": "none"},
        exam_results={"vital_signs": "BP 118/76, HR 74, RR 16, Temp 36.8, SpO2 99%",
                      "neuro_exam": "fully intact, no focal deficit"},
    ),
    # --- retrieval-miss trap (true dx a naive keyword search would likely miss) -----------------
    SyntheticCase(
        case_id="Blind12_09_WristDropAfterSleepingOnArm", category="retrieval_miss_trap",
        chief_complaint="I woke up and my wrist just flops, I can't lift my hand up at all",
        demographics={"age": 35, "sex": "male"}, ground_truth_diagnosis="unknown",
        answers={"onset": "on waking, fell asleep with arm under a partner's head", "associated_symptoms": "numb patch on back of hand"},
        exam_results={"vital_signs": "BP 120/76, HR 72, RR 14, Temp 36.7, SpO2 99%",
                      "neuro_exam": "wrist and finger extension weak, sensation reduced over dorsal web space"},
        scoring_expected=False,
        notes="Retrieval-miss trap: 'wrist drop after sleeping on arm' shares almost no vocabulary "
              "with the formal name; recall depends on retrieval finding it via broader signal fusion.",
    ),
    # --- long-tail Tier-2 -----------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind12_10_SuddenOneEarHearingLossRinging", category="long_tail",
        chief_complaint="I lost hearing in my right ear overnight and there's a constant ringing now",
        demographics={"age": 48, "sex": "male"}, ground_truth_diagnosis="tier2:sudden_sensorineural_hearing_loss",
        answers={"onset": "noticed on waking this morning", "associated_symptoms": "mild dizziness, no ear pain, no discharge"},
        exam_results={"vital_signs": "BP 128/80, HR 76, RR 15, Temp 36.8, SpO2 99%"},
        scoring_expected=False,
    ),
    SyntheticCase(
        case_id="Blind12_11_DifficultySwallowingRegurgitatingFood", category="long_tail",
        chief_complaint="food feels like it just sits in my chest and comes back up, been getting worse for months",
        demographics={"age": 52, "sex": "female"}, ground_truth_diagnosis="tier2:achalasia",
        answers={"onset": "gradual over 6 months", "associated_symptoms": "unintentional weight loss, no heartburn"},
        exam_results={"vital_signs": "BP 116/72, HR 70, RR 14, Temp 36.7, SpO2 99%"},
        scoring_expected=False,
    ),
    # --- shallow Tier-3 (named-only, no curated clinical claims) --------------------------------
    SyntheticCase(
        case_id="Blind12_12_VagueRareSyndromeName", category="shallow_tier3",
        chief_complaint="my doctor back home mentioned a rare syndrome but I don't remember much else, I just feel generally unwell",
        demographics={"age": 40, "sex": "male"}, ground_truth_diagnosis="unknown",
        answers={"associated_symptoms": "vague fatigue, no fever, no focal complaint"},
        exam_results={"vital_signs": "BP 122/78, HR 76, RR 16, Temp 36.8, SpO2 99%"},
        scoring_expected=False,
        notes="Shallow/underspecified presentation -- correct behavior is explicit uncertainty "
              "(POSSIBLE_UNMAPPED/UNKNOWN), never a forced label onto the nearest known disease.",
    ),
    # --- rare-condition wording (uses an unusual clinical term the patient overheard) -----------
    SyntheticCase(
        case_id="Blind12_13_PatientUsesMedicalJargon", category="rare_wording",
        chief_complaint="the ER doctor said I might be having a 'STEMI', now my chest still hurts and I'm scared",
        demographics={"age": 61, "sex": "male"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "ongoing 2 hours", "associated_symptoms": "diaphoresis, nausea",
                 "past_medical_history": "prior heart attack"},
        exam_results={"vital_signs": "BP 138/86, HR 98, RR 20, Temp 36.9, SpO2 95%"},
        test_results={"ecg": "ST elevation anterior leads", "troponin": "markedly elevated"},
    ),
    # --- synonym / paraphrase presentation -------------------------------------------------------
    SyntheticCase(
        case_id="Blind12_14_LayPhrasingOfDKA", category="synonym_paraphrase",
        chief_complaint="I've been peeing constantly, so thirsty I can't keep up, and my breath smells fruity my roommate says",
        demographics={"age": 22, "sex": "female"}, ground_truth_diagnosis="diabetic_ketoacidosis",
        answers={"onset": "2 days worsening", "past_medical_history": "type 1 diabetes, ran out of insulin"},
        exam_results={"vital_signs": "BP 100/64, HR 118, RR 28, Temp 37.1, SpO2 97%"},
        test_results={"glucose_point_of_care": "glucose 480 mg/dL", "ketones": "large ketones"},
    ),
    SyntheticCase(
        case_id="Blind12_15_LayPhrasingOfPE", category="synonym_paraphrase",
        chief_complaint="all of a sudden I can't catch my breath and there's a stabbing feeling when I breathe in deep",
        demographics={"age": 46, "sex": "female"}, ground_truth_diagnosis="pulmonary_embolism",
        answers={"onset": "sudden, 1 hour ago", "history": "long flight two days ago, started birth control pills recently"},
        exam_results={"vital_signs": "BP 112/70, HR 118, RR 26, Temp 37.0, SpO2 90%"},
        test_results={"d_dimer": "d-dimer markedly elevated"},
    ),
    # --- objective-evidence-heavy (decisive labs should dominate vague symptom text) ------------
    SyntheticCase(
        case_id="Blind12_16_VagueSymptomsDecisivePotassium", category="objective_evidence_heavy",
        chief_complaint="I just feel weak and off today, hard to explain",
        demographics={"age": 67, "sex": "male"}, ground_truth_diagnosis="severe_electrolyte_disorder",
        answers={"past_medical_history": "chronic kidney disease", "medications": "lisinopril, spironolactone"},
        exam_results={"vital_signs": "BP 132/84, HR 58, RR 16, Temp 36.7, SpO2 98%"},
        test_results={"potassium": "potassium 7.1 mEq/L", "ecg": "peaked T waves"},
    ),
    # --- negative-evidence-heavy (a run of pertinent negatives should still permit a diagnosis) --
    SyntheticCase(
        case_id="Blind12_17_ManyNegativesStillDiagnosable", category="negative_evidence_heavy",
        chief_complaint="sharp pain in my lower right belly that started around my belly button",
        demographics={"age": 19, "sex": "male"}, ground_truth_diagnosis="appendicitis",
        answers={"onset": "12 hours, migrated and worsening",
                 "associated_symptoms": "denies vomiting, denies diarrhea, denies urinary symptoms, denies fever, mild nausea only"},
        exam_results={"vital_signs": "BP 124/78, HR 92, RR 16, Temp 37.6, SpO2 99%",
                      "abdominal_exam": "right lower quadrant tenderness with guarding"},
        test_results={"cbc": "mild leukocytosis"},
    ),
    # --- multimorbidity ---------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind12_18_DiabeticHypertensiveCKDConfused", category="multimorbidity",
        chief_complaint="my father has been more confused than usual and hasn't wanted to eat for two days",
        demographics={"age": 79, "sex": "male"}, ground_truth_diagnosis="sepsis",
        answers={"past_medical_history": "type 2 diabetes, hypertension, chronic kidney disease, recent urinary catheter",
                 "associated_symptoms": "foul-smelling urine per caregiver"},
        exam_results={"vital_signs": "BP 96/58, HR 110, RR 24, Temp 38.6, SpO2 94%"},
        test_results={"lactate": "lactate 3.6 mmol/L", "urinalysis": "positive leukocyte esterase and nitrites"},
    ),
    # --- polypharmacy ------------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind12_19_WarfarinPatientBlackStools", category="polypharmacy",
        chief_complaint="I've been so tired lately and I noticed my stool looks almost black",
        demographics={"age": 74, "sex": "female"}, ground_truth_diagnosis="gi_bleeding",
        answers={"medications": "warfarin, aspirin, ibuprofen for arthritis pain",
                 "associated_symptoms": "lightheaded on standing"},
        exam_results={"vital_signs": "BP 100/62, HR 108, RR 18, Temp 36.8, SpO2 97%"},
        test_results={"hemoglobin": "hemoglobin 7.2 g/dL"},
    ),
    # --- elderly -------------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind12_20_ElderlyAtypicalSilentMI", category="elderly",
        chief_complaint="grandmother just seems unusually tired and a bit short of breath doing her usual chores",
        demographics={"age": 84, "sex": "female"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "gradual over the day", "associated_symptoms": "denies chest pain, mild nausea",
                 "past_medical_history": "diabetes, hypertension"},
        exam_results={"vital_signs": "BP 100/64, HR 92, RR 22, Temp 36.7, SpO2 93%"},
        test_results={"ecg": "ST depression inferolateral leads", "troponin": "elevated"},
    ),
    # --- pediatric -----------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind12_21_ToddlerBarkingCough", category="pediatric",
        chief_complaint="my two-year-old has a harsh barking cough and sounds like a seal, started tonight",
        demographics={"age": 2, "sex": "male"}, ground_truth_diagnosis="tier2:croup",
        answers={"onset": "sudden this evening, worse when crying", "associated_symptoms": "hoarse voice, mild fever"},
        exam_results={"vital_signs": "HR 130, RR 32, Temp 38.1, SpO2 96%",
                      "general_appearance": "stridor audible at rest when upset"},
        scoring_expected=False,
    ),
    # --- pregnancy -----------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind12_22_PregnantSuddenSevereHeadacheSwelling", category="pregnancy",
        chief_complaint="I'm 32 weeks pregnant and this headache won't go away and my hands are so swollen",
        demographics={"age": 29, "sex": "female", "pregnant": True}, ground_truth_diagnosis="tier2:preeclampsia",
        answers={"onset": "headache for 6 hours, swelling for two days", "associated_symptoms": "spots in vision"},
        exam_results={"vital_signs": "BP 162/104, HR 88, RR 18, Temp 36.8, SpO2 98%"},
        test_results={"urinalysis": "protein 2+"},
        scoring_expected=False,
    ),
    # --- atypical presentation --------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind12_23_DiabeticSilentAbdomenMimicsIndigestion", category="atypical",
        chief_complaint="just some indigestion after eating, nothing major, happens sometimes",
        demographics={"age": 60, "sex": "male"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "on and off for an hour", "past_medical_history": "longstanding diabetes with neuropathy",
                 "associated_symptoms": "mild sweating, denies typical chest pain"},
        exam_results={"vital_signs": "BP 140/88, HR 94, RR 18, Temp 36.8, SpO2 95%"},
        test_results={"ecg": "ST elevation inferior leads", "troponin": "elevated"},
    ),
    # --- mixed-language ------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind12_24_KoreanChestPainMixedEnglish", category="mixed_language",
        chief_complaint="가슴이 너무 아파요, like someone is sitting on my chest, 숨쉬기 힘들어요",
        demographics={"age": 56, "sex": "male"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "30분 전, sudden", "associated_symptoms": "sweating a lot, 팔도 아파요 (arm hurts too)"},
        exam_results={"vital_signs": "BP 148/90, HR 100, RR 20, Temp 36.9, SpO2 95%"},
        test_results={"ecg": "ST elevation anterior leads", "troponin": "elevated"},
    ),
    SyntheticCase(
        case_id="Blind12_25_JapaneseAbdominalPain", category="mixed_language",
        chief_complaint="お腹が痛いです、右下のほう、昨日からだんだん悪化しています",
        demographics={"age": 21, "sex": "male"}, ground_truth_diagnosis="appendicitis",
        answers={"onset": "started yesterday around the belly button, moved to the right side",
                 "associated_symptoms": "吐き気があります (nauseous), denies diarrhea"},
        exam_results={"vital_signs": "BP 122/76, HR 90, RR 16, Temp 37.7, SpO2 99%",
                      "abdominal_exam": "right lower quadrant tenderness"},
        test_results={"cbc": "leukocytosis"},
    ),
    # --- sparse information (genuinely insufficient to name a condition yet) ---------------------
    SyntheticCase(
        case_id="Blind12_26_SingleWordComplaintNoElaboration", category="sparse_information",
        chief_complaint="pain",
        demographics={"age": 35, "sex": "female"}, ground_truth_diagnosis="unknown",
        scoring_expected=False,
        notes="Deliberately near-zero information at intake -- correct behavior is to gather more "
              "evidence, never guess from one word.",
    ),
    # --- conflicting evidence --------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind12_27_ReassuringVitalsButAlarmingECG", category="conflicting_evidence",
        chief_complaint="chest tightness that started while I was resting, feels different from usual heartburn",
        demographics={"age": 65, "sex": "male"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "40 minutes, at rest", "past_medical_history": "hypertension"},
        exam_results={"vital_signs": "BP 128/80, HR 76, RR 16, Temp 36.8, SpO2 98%",
                      "general_appearance": "comfortable, not visibly distressed"},
        test_results={"ecg": "ST depression lateral leads", "troponin": "elevated"},
        notes="Conflicting-evidence trap: reassuring vitals/appearance vs. decisive ECG+troponin -- "
              "objective evidence must not be discounted just because the patient looks well.",
    ),
    # --- unit issue ------------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind12_28_GlucoseReportedInMmolL", category="unit_issue",
        chief_complaint="shaky, sweaty, and confused since a few minutes ago",
        demographics={"age": 45, "sex": "male"}, ground_truth_diagnosis="hypoglycemia",
        answers={"onset": "sudden, 10 minutes ago", "medications": "insulin", "past_medical_history": "type 1 diabetes"},
        exam_results={"vital_signs": "BP 118/76, HR 102, RR 18, Temp 36.6, SpO2 98%"},
        test_results={"glucose_point_of_care": "glucose 2.1 mmol/L (38 mg/dL)"},
        notes="Unit-safety trap: glucose given in mmol/L with an explicit mg/dL conversion present -- "
              "must be read correctly, never misinterpreted as a normal mg/dL value.",
    ),
    # --- inter-arm BP --------------------------------------------------------------------------
    SyntheticCase(
        case_id="Blind12_29_UnequalArmPressuresChestPain", category="inter_arm_bp",
        chief_complaint="ripping pain between my shoulder blades that started all at once while gardening",
        demographics={"age": 59, "sex": "male"}, ground_truth_diagnosis="aortic_dissection",
        answers={"onset": "sudden, 15 minutes ago", "past_medical_history": "hypertension, Marfan-like build per family"},
        exam_results={"vital_signs": "left arm BP 176/98, right arm BP 132/82, HR 96, RR 20, Temp 36.8, SpO2 96%"},
        test_results={"cxr": "widened mediastinum"},
    ),
    # --- over-testing trap (clear diagnosis reachable quickly -- watches for unnecessary extra tests) --
    SyntheticCase(
        case_id="Blind12_30_ClearCutCaseWatchForOvertesting", category="over_testing_trap",
        chief_complaint="sudden severe one-sided facial weakness and I can't lift my right arm at all, started while I was talking on the phone",
        demographics={"age": 68, "sex": "male"}, ground_truth_diagnosis="ischemic_stroke",
        answers={"onset": "20 minutes ago, sudden", "past_medical_history": "atrial fibrillation, hypertension"},
        exam_results={"vital_signs": "BP 172/98, HR 90 irregular, RR 18, Temp 36.8, SpO2 97%",
                      "neuro_exam": "right facial droop, right arm plegia, expressive aphasia"},
        test_results={"ct_head": "no hemorrhage"},
        notes="Over-testing trap: the presentation + exam + one confirmatory imaging result is "
              "already decisive -- watches whether the agent still orders redundant/unnecessary "
              "additional tests before diagnosing (unnecessary_test_rate/duplicate_action_rate).",
    ),
    # --- premature-diagnosis trap (genuinely ambiguous early on, punishes diagnosing too soon) ----
    SyntheticCase(
        case_id="Blind12_31_AmbiguousEarlyPresentationNeedsWorkup", category="premature_diagnosis_trap",
        chief_complaint="just don't feel right, a bit of belly discomfort and tired the last day or so",
        demographics={"age": 50, "sex": "female"}, ground_truth_diagnosis="diabetic_ketoacidosis",
        answers={"onset": "gradual over 24 hours", "associated_symptoms": "nausea, increased thirst and urination",
                 "past_medical_history": "type 1 diabetes, insulin pump malfunctioned yesterday"},
        exam_results={"vital_signs": "BP 108/68, HR 108, RR 24, Temp 37.0, SpO2 97%"},
        test_results={"glucose_point_of_care": "glucose 410 mg/dL", "ketones": "large ketones"},
        notes="Premature-diagnosis trap: the opening line is vague ('just don't feel right') -- a "
              "correct agent gathers the decisive history/labs before committing, rather than "
              "diagnosing (or dismissing) from the vague chief complaint alone.",
    ),
    # --- duplicate-question trap -----------------------------------------------------------------
    SyntheticCase(
        case_id="Blind12_32_AnswerAlreadyVolunteeredUpFront", category="duplicate_question_trap",
        chief_complaint="sudden crushing chest pain, and I should mention I already take aspirin daily and have high cholesterol",
        demographics={"age": 57, "sex": "male"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "30 minutes, at rest", "associated_symptoms": "sweating, nausea"},
        exam_results={"vital_signs": "BP 146/90, HR 98, RR 19, Temp 36.9, SpO2 95%"},
        test_results={"ecg": "ST elevation anterior leads", "troponin": "elevated"},
        notes="Duplicate-question trap: medication/PMH info is volunteered in the chief complaint "
              "itself -- a correct agent must not re-ask for the same already-known medication or "
              "past-history fact as a separate ASK turn (semantic-duplicate prevention).",
    ),
]
