"""Blind evaluation set v4 (spec: a second, genuinely blind final check, authored after this
session's chief-complaint routing rewrite and systemic-severity evidence layer, and never adjusted
afterward to match its own answers).

Authoring rules followed (self-imposed, left here for a future session to audit):
  1. No sentence, clause, or distinctive phrase was copied from evaluation/cases.py,
     evaluation/held_out_cases.py, evaluation/generalization_cases_v2.py,
     evaluation/generalization_stress_cases.py, evaluation/blind_cases_v3.py, or
     tests/test_severity_evidence.py -- every vignette was written fresh.
  2. Not a reworded variant of any prior miss: this file does not re-target the two historical
     generalization-v2 misses (hypoglycemia, migraine/stroke) with new wording, and does not copy
     any blind-v3 case's specific miss pattern.
  3. One case per diagnosis in the 34-disease knowledge base (never all 34 diagnoses were touched
     by any single earlier evaluation file), so this set exercises breadth blind v3 didn't.
  4. Every case's ground_truth_diagnosis, category tag, and vignette content was decided and
     frozen BEFORE running evaluation.blind_benchmark_v4 for the first time. This file is not
     edited after seeing that run's results, regardless of the score.

34 cases spanning common / critical / atypical / elderly / polypharmacy / multimorbidity /
negative-finding-centric / conflicting-findings / benign-mimic / dangerous-mimic / vague-language
presentations. Hand-authored synthetic vignettes, never real patient data.
"""

from __future__ import annotations

from evaluation.cases import SyntheticCase

BLIND_CASES_V4 = [
    SyntheticCase(
        case_id="Blind4_01_ScratchyThroatCongestion", category="common",
        chief_complaint="my throat feels scratchy and my nose won't stop running", demographics={"age": 27, "sex": "male"},
        ground_truth_diagnosis="viral_uri",
        answers={
            "duration": "since yesterday evening",
            "associated_symptoms": "sneezing a lot and a little tickly cough; no trouble breathing, no ear pain, no rash",
            "social_history": "coworker was out sick with a cold last week",
        },
        exam_results={"vital_signs": "BP 118/74, HR 80, RR 14, Temp 37.3, SpO2 99%",
                      "lung_auscultation": "clear bilaterally"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind4_02_StomachBugAfterPicnic", category="common",
        chief_complaint="I've been throwing up and running to the bathroom all afternoon", demographics={"age": 31, "sex": "female"},
        ground_truth_diagnosis="gastroenteritis",
        answers={
            "onset": "started about four hours after a picnic lunch",
            "associated_symptoms": "watery diarrhea, crampy belly pain, felt a little feverish; denies blood in stool, denies severe localized pain",
            "social_history": "two other people at the picnic mentioned feeling sick too",
        },
        exam_results={"vital_signs": "BP 108/68, HR 96, RR 16, Temp 37.9, SpO2 99%",
                      "abdominal_exam": "diffusely mildly tender, no rebound, no guarding, bowel sounds present"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind4_03_BandLikeHeadacheStress", category="common",
        chief_complaint="I've got this tight band around my head, been building all week", demographics={"age": 40, "sex": "female"},
        ground_truth_diagnosis="tension_headache",
        answers={
            "character": "a dull, squeezing pressure on both sides, not throbbing",
            "aggravating": "worse when I'm stressed at work; denies nausea, denies sensitivity to light or sound, denies vision changes",
            "past_medical_history": "nothing significant",
        },
        exam_results={"vital_signs": "BP 122/78, HR 74, RR 14, Temp 36.9, SpO2 99%",
                      "neuro_exam": "normal neuro exam, no focal deficits"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind4_04_LingeringCoughAfterCold", category="common",
        chief_complaint="I've had this cough for two weeks now and it won't quit", demographics={"age": 35, "sex": "male"},
        ground_truth_diagnosis="acute_bronchitis",
        answers={
            "onset": "started after a cold about two weeks ago; the stuffy nose cleared up but the cough stayed",
            "associated_symptoms": "bringing up some clear-ish mucus; denies fever, denies shortness of breath at rest, denies chest pain",
            "past_medical_history": "no asthma, no COPD",
        },
        exam_results={"vital_signs": "BP 116/72, HR 78, RR 16, Temp 36.9, SpO2 98%",
                      "lung_auscultation": "scattered rhonchi, clears with cough, no wheeze, no crackles"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind4_05_CrushingChestPressureExertion", category="critical",
        chief_complaint="I got this crushing pressure in my chest carrying groceries up the stairs", demographics={"age": 61, "sex": "male"},
        ground_truth_diagnosis="acute_coronary_syndrome",
        answers={
            "onset": "started about 40 minutes ago and hasn't let up",
            "character": "heavy pressure, like a weight sitting on my chest",
            "associated_symptoms": "sweating, a little short of breath, some nausea; pain goes into my jaw",
            "past_medical_history": "high cholesterol, high blood pressure",
            "family_history": "brother had a stent placed at 58",
            "social_history": "quit smoking three years ago after a 20-year habit",
        },
        exam_results={"vital_signs": "BP 158/96, HR 102, RR 20, Temp 36.9, SpO2 96%",
                      "cardiac_auscultation": "regular rhythm, no murmur", "general_appearance": "diaphoretic, uncomfortable"},
        test_results={"ecg": "ST depression in the anterolateral leads", "troponin": "elevated troponin"},
    ),
    SyntheticCase(
        case_id="Blind4_06_SuddenPleuriticChestPainPostFlight", category="critical",
        chief_complaint="sharp pain in my side every time I breathe in, right after a long flight", demographics={"age": 47, "sex": "female"},
        ground_truth_diagnosis="pulmonary_embolism",
        answers={
            "onset": "started suddenly a couple hours after landing from a 10-hour flight",
            "character": "sharp, stabbing, worse with a deep breath",
            "associated_symptoms": "short of breath, heart racing; one calf feels swollen and sore; denies fever, denies cough",
            "past_medical_history": "takes oral contraceptives",
        },
        exam_results={"vital_signs": "BP 112/70, HR 118, RR 26, Temp 37.1, SpO2 91%",
                      "extremity_exam": "right calf swelling and tenderness, left calf normal",
                      "lung_auscultation": "clear bilaterally"},
        test_results={"d_dimer": "markedly elevated", "ct_chest_angio": "filling defect in the right pulmonary artery"},
    ),
    SyntheticCase(
        case_id="Blind4_07_SuddenFacialDroopSlurredSpeech", category="critical",
        chief_complaint="his face suddenly drooped on one side and his words are slurring", demographics={"age": 70, "sex": "male"},
        ground_truth_diagnosis="ischemic_stroke",
        answers={
            "onset": "about 25 minutes ago, witnessed by his wife, sudden",
            "associated_symptoms": "left arm feels weak and heavy; denies headache, denies loss of consciousness",
            "past_medical_history": "atrial fibrillation, hypertension",
            "medication": "not on any blood thinner currently",
        },
        exam_results={"neuro_exam": "left facial droop, left arm drift, slurred speech",
                      "vital_signs": "BP 176/100, HR 88 irregularly irregular, RR 16, Temp 36.8, SpO2 97%"},
        test_results={"ct_head": "acute infarct in the right MCA territory", "glucose_point_of_care": "112 mg/dL"},
    ),
    SyntheticCase(
        case_id="Blind4_08_FeverConfusionAfterIndwellingCatheter", category="critical",
        chief_complaint="grandma has a high fever and isn't making sense today", demographics={"age": 82, "sex": "female"},
        ground_truth_diagnosis="sepsis",
        notes="Systemic-severity evidence (shock, AMS, high lactate) should let sepsis outrank a "
              "purely localized urinary-source diagnosis here -- not a hand-coded rule, just the "
              "generic derangement signals actually being present in this vignette.",
        answers={
            "onset": "started shaky and feverish yesterday, confusion got worse overnight",
            "associated_symptoms": "she has a long-term urinary catheter from a nursing facility; not eating, very drowsy",
            "past_medical_history": "recurrent urinary tract infections, indwelling catheter for six months",
        },
        exam_results={"vital_signs": "BP 82/54, HR 128, RR 28, Temp 39.4, SpO2 90%",
                      "mental_status_exam": "confused, disoriented to time and place, drowsy",
                      "general_appearance": "ill-appearing, mottled skin"},
        test_results={"lactate": "Lactate 5.1 mmol/L", "urinalysis": "cloudy, positive for leukocyte esterase and nitrites"},
    ),
    SyntheticCase(
        case_id="Blind4_09_TearingBackPainRadiating", category="critical",
        chief_complaint="sudden ripping pain between my shoulder blades", demographics={"age": 64, "sex": "male"},
        ground_truth_diagnosis="aortic_dissection",
        answers={
            "onset": "came on all at once about 20 minutes ago",
            "character": "tearing, ripping sensation, worst pain of my life",
            "associated_symptoms": "denies shortness of breath, denies leg swelling; feels a bit lightheaded",
            "past_medical_history": "poorly controlled high blood pressure for years",
        },
        exam_results={"vital_signs": "BP 190/70 right arm, 148/62 left arm, HR 96, RR 18, Temp 36.9, SpO2 97%",
                      "cardiac_auscultation": "new soft diastolic murmur"},
        test_results={"ct_aorta": "intimal flap consistent with type A dissection"},
    ),
    SyntheticCase(
        case_id="Blind4_10_WorstHeadacheOfLifeSudden", category="critical",
        chief_complaint="my head exploded with pain out of nowhere, worst I've ever felt", demographics={"age": 45, "sex": "female"},
        ground_truth_diagnosis="subarachnoid_hemorrhage",
        answers={
            "onset": "hit like a thunderclap, peaked within a minute",
            "character": "worst headache of my life, nothing like my usual headaches",
            "associated_symptoms": "neck feels stiff, vomited once; denies fever",
            "past_medical_history": "none",
        },
        exam_results={"neuro_exam": "neck stiffness, no focal motor deficit",
                      "vital_signs": "BP 164/92, HR 88, RR 16, Temp 36.9, SpO2 98%"},
        test_results={"ct_head": "blood in the subarachnoid space", "lumbar_puncture": "xanthochromia present"},
    ),
    SyntheticCase(
        case_id="Blind4_11_FeverStiffNeckPhotophobia", category="critical",
        chief_complaint="I've got a fever and my neck is so stiff I can't look down", demographics={"age": 22, "sex": "male"},
        ground_truth_diagnosis="meningitis",
        answers={
            "onset": "started yesterday, getting worse fast",
            "associated_symptoms": "bright lights hurt my eyes, headache, feel foggy; denies rash on questioning at first",
            "social_history": "lives in a college dorm, a dorm-mate was hospitalized last week",
        },
        exam_results={"neuro_exam": "nuchal rigidity, positive Kernig's sign",
                      "vital_signs": "BP 106/64, HR 112, RR 22, Temp 39.6, SpO2 96%",
                      "skin_exam": "no rash noted"},
        test_results={"lumbar_puncture": "cloudy CSF, elevated white count, low glucose"},
    ),
    SyntheticCase(
        case_id="Blind4_12_NewOnsetType1DiabetesVomitingFruityBreath", category="critical",
        chief_complaint="my son has been throwing up all day and breathing really fast", demographics={"age": 14, "sex": "male"},
        ground_truth_diagnosis="diabetic_ketoacidosis",
        answers={
            "onset": "started vomiting this morning, breathing has gotten faster over the last few hours",
            "associated_symptoms": "drinking a lot of water and going to the bathroom constantly for the past week, lost some weight; his breath smells sweet/fruity",
            "past_medical_history": "no prior diagnosis of diabetes",
        },
        exam_results={"vital_signs": "BP 100/60, HR 118, RR 32, Temp 37.0, SpO2 97%",
                      "general_appearance": "lethargic, dry mucous membranes"},
        test_results={"glucose_point_of_care": "486 mg/dL", "ketones": "large ketones in urine"},
    ),
    SyntheticCase(
        case_id="Blind4_13_HivesThroatTightnessAfterPeanuts", category="critical",
        chief_complaint="my whole body broke out in hives and my throat feels like it's closing", demographics={"age": 19, "sex": "female"},
        ground_truth_diagnosis="anaphylaxis",
        answers={
            "onset": "within ten minutes of eating a cookie that had peanuts in it",
            "associated_symptoms": "lips and face are swelling, wheezing when I breathe; feel dizzy",
            "past_medical_history": "known peanut allergy since childhood",
        },
        exam_results={"vital_signs": "BP 84/52, HR 122, RR 26, Temp 36.9, SpO2 93%",
                      "skin_exam": "diffuse urticaria, facial and lip swelling",
                      "lung_auscultation": "bilateral wheeze"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind4_14_SuddenChestPainAfterCarAccidentNoBreathSounds", category="critical",
        chief_complaint="I can't breathe right after hitting the steering wheel in a crash", demographics={"age": 29, "sex": "male"},
        ground_truth_diagnosis="tension_pneumothorax",
        answers={
            "onset": "immediately after the collision about 15 minutes ago",
            "character": "sharp pain on the left side, getting harder to breathe",
            "associated_symptoms": "feels like the pain is worse than before, more short of breath now",
        },
        exam_results={"vital_signs": "BP 84/56, HR 130, RR 32, Temp 36.8, SpO2 87%",
                      "lung_auscultation": "absent breath sounds on the left",
                      "general_appearance": "tracheal deviation to the right, jugular venous distension"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind4_15_RightLowerAbdomenPainMigrating", category="dangerous_mimic",
        chief_complaint="my belly pain started near my belly button and moved down to the right", demographics={"age": 24, "sex": "male"},
        ground_truth_diagnosis="appendicitis",
        answers={
            "onset": "started yesterday around my belly button, moved to the lower right side overnight",
            "aggravating": "worse with movement, coughing; denies improvement with antacids",
            "associated_symptoms": "nausea, lost my appetite, low-grade fever",
        },
        exam_results={"vital_signs": "BP 118/76, HR 96, RR 18, Temp 38.1, SpO2 98%",
                      "abdominal_exam": "tenderness and guarding at McBurney's point, rebound tenderness present"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind4_16_MissedPeriodLowerAbdomenPain", category="dangerous",
        chief_complaint="I missed my period and now I have sharp pain on one side", demographics={"age": 28, "sex": "female"},
        ground_truth_diagnosis="ectopic_pregnancy",
        answers={
            "onset": "sharp pain started a few hours ago, was a dull ache for the past two days before that",
            "associated_symptoms": "some light vaginal spotting; period is about six weeks late; feels lightheaded standing up",
            "past_medical_history": "prior pelvic infection two years ago",
        },
        exam_results={"vital_signs": "BP 96/62, HR 108, RR 18, Temp 37.0, SpO2 98%",
                      "abdominal_exam": "left lower quadrant tenderness, no rebound"},
        test_results={"beta_hcg": "positive, quantitative 1800 mIU/mL"},
    ),
    SyntheticCase(
        case_id="Blind4_17_FlankPainBloodInUrine", category="benign_mimic",
        chief_complaint="sudden awful pain in my side that comes in waves, and my pee looks pink", demographics={"age": 38, "sex": "male"},
        ground_truth_diagnosis="nephrolithiasis",
        answers={
            "onset": "started about three hours ago, comes and goes in waves",
            "character": "sharp, colicky pain that radiates from my flank down toward my groin",
            "associated_symptoms": "nausea, restless, can't find a comfortable position; denies fever, denies burning with urination",
            "past_medical_history": "had a kidney stone five years ago",
        },
        exam_results={"vital_signs": "BP 128/80, HR 92, RR 16, Temp 37.0, SpO2 99%",
                      "abdominal_exam": "costovertebral angle tenderness on the right, no rebound"},
        test_results={"urinalysis": "microscopic hematuria, no signs of infection"},
    ),
    SyntheticCase(
        case_id="Blind4_18_FeverFlankPainElderly", category="elderly",
        chief_complaint="my back and side have been hurting and I've had chills for two days", demographics={"age": 76, "sex": "female"},
        ground_truth_diagnosis="pyelonephritis",
        answers={
            "onset": "started two days ago, fevers and chills came on yesterday",
            "associated_symptoms": "burning with urination, going more often; feels tired but otherwise thinking clearly",
            "past_medical_history": "type 2 diabetes",
        },
        exam_results={"vital_signs": "BP 128/76, HR 94, RR 18, Temp 38.7, SpO2 97%",
                      "abdominal_exam": "left costovertebral angle tenderness",
                      "mental_status_exam": "alert and oriented, conversing normally"},
        test_results={"urinalysis": "cloudy, positive for leukocyte esterase, nitrites, and white cells"},
    ),
    SyntheticCase(
        case_id="Blind4_19_BurningUrinationYoungWoman", category="common",
        chief_complaint="it burns every time I pee and I keep needing to go", demographics={"age": 26, "sex": "female"},
        ground_truth_diagnosis="uncomplicated_cystitis",
        answers={
            "onset": "started yesterday",
            "associated_symptoms": "no back pain, no fever, no chills; just the burning and frequency, and it feels like I can't empty my bladder all the way",
            "past_medical_history": "healthy, not pregnant",
        },
        exam_results={"vital_signs": "BP 114/72, HR 76, RR 14, Temp 36.9, SpO2 99%",
                      "abdominal_exam": "mild suprapubic tenderness, no costovertebral angle tenderness"},
        test_results={"urinalysis": "positive for leukocyte esterase and nitrites"},
    ),
    SyntheticCase(
        case_id="Blind4_20_BlackTarryStoolsDizzy", category="dangerous",
        chief_complaint="my stools have gone black and tarry and I feel lightheaded", demographics={"age": 58, "sex": "male"},
        ground_truth_diagnosis="gi_bleeding",
        answers={
            "onset": "noticed the black stools over the last two days, dizziness started today",
            "associated_symptoms": "felt weak standing up, a little short of breath; denies vomiting blood",
            "past_medical_history": "takes daily ibuprofen for chronic back pain",
        },
        exam_results={"vital_signs": "BP 96/64, HR 112, RR 20, Temp 36.8, SpO2 97%",
                      "abdominal_exam": "mild diffuse tenderness, no rigidity",
                      "general_appearance": "pale"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind4_21_SevereEpigastricPainRadiatingBackAlcohol", category="dangerous",
        chief_complaint="this pain in my upper stomach is boring straight through to my back", demographics={"age": 49, "sex": "male"},
        ground_truth_diagnosis="acute_pancreatitis",
        answers={
            "onset": "started last night after a night of heavy drinking, steadily worsening",
            "character": "constant, boring pain in the upper belly radiating to my back",
            "aggravating": "worse lying flat, a little better leaning forward; denies improvement with antacids",
            "associated_symptoms": "vomiting repeatedly, no appetite",
            "social_history": "drinks heavily most weekends",
        },
        exam_results={"vital_signs": "BP 118/76, HR 106, RR 20, Temp 37.8, SpO2 97%",
                      "abdominal_exam": "epigastric tenderness, voluntary guarding, no rebound"},
        test_results={"lipase": "markedly elevated"},
    ),
    SyntheticCase(
        case_id="Blind4_22_SuddenSevereAbdominalPainRigidElderly", category="dangerous_elderly",
        chief_complaint="his stomach pain came on all of a sudden and it's board-hard", demographics={"age": 80, "sex": "male"},
        ground_truth_diagnosis="acute_abdomen",
        answers={
            "onset": "sudden onset about two hours ago, severe from the start",
            "associated_symptoms": "won't let anyone touch his belly, hasn't passed gas since it started",
            "past_medical_history": "diverticulosis",
        },
        exam_results={"vital_signs": "BP 100/64, HR 116, RR 24, Temp 38.3, SpO2 95%",
                      "abdominal_exam": "rigid abdomen, diffuse rebound tenderness, involuntary guarding",
                      "mental_status_exam": "alert but in obvious distress"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind4_23_BurningChestAfterMealsLyingDown", category="benign_mimic",
        chief_complaint="I get this burning in my chest after big meals, especially lying down", demographics={"age": 42, "sex": "male"},
        ground_truth_diagnosis="gerd",
        answers={
            "onset": "happens on and off for months, worse the last week",
            "character": "burning sensation rising up from my stomach into my chest",
            "aggravating": "worse after eating, worse lying down at night; better sitting up; denies exertional pattern",
            "associated_symptoms": "sour taste in my mouth; denies sweating, denies radiation to jaw or arm",
        },
        exam_results={"vital_signs": "BP 124/78, HR 74, RR 14, Temp 36.8, SpO2 99%",
                      "cardiac_auscultation": "normal heart sounds"},
        test_results={"ecg": "normal sinus rhythm, no ST changes", "troponin": "not elevated"},
    ),
    SyntheticCase(
        case_id="Blind4_24_ChestWallTendernessAfterLifting", category="benign_mimic",
        chief_complaint="I strained something in my chest moving furniture yesterday", demographics={"age": 33, "sex": "male"},
        ground_truth_diagnosis="musculoskeletal_chest_pain",
        answers={
            "onset": "started yesterday while lifting a heavy couch",
            "character": "sharp, localized pain over one spot on the left side of my chest",
            "aggravating": "worse when I press on it or twist my torso; denies exertional chest pain, denies shortness of breath",
        },
        exam_results={"vital_signs": "BP 118/76, HR 72, RR 14, Temp 36.8, SpO2 99%",
                      "cardiac_auscultation": "normal heart sounds",
                      "abdominal_exam": "reproducible tenderness over the left chest wall with palpation"},
        test_results={"ecg": "normal sinus rhythm, no ST changes"},
    ),
    SyntheticCase(
        case_id="Blind4_25_ChestTightnessAnxietyCollegeExam", category="conflicting_findings",
        chief_complaint="my chest went tight and my heart started pounding right before my final exam", demographics={"age": 20, "sex": "female"},
        ground_truth_diagnosis="panic_attack",
        answers={
            "onset": "started about ten minutes before the exam, peaked within a few minutes",
            "associated_symptoms": "tingling in my fingers, felt like I couldn't get a full breath, felt like something terrible was about to happen; denies chest pain with exertion normally",
            "past_medical_history": "had similar episodes before big tests in the past",
        },
        exam_results={"vital_signs": "BP 128/80, HR 108, RR 22, Temp 37.0, SpO2 99%",
                      "cardiac_auscultation": "normal heart sounds"},
        test_results={"ecg": "sinus tachycardia, otherwise normal"},
    ),
    SyntheticCase(
        case_id="Blind4_26_FaintedAfterBloodDrawStandingLong", category="benign",
        chief_complaint="I saw stars and went down right after they drew my blood", demographics={"age": 25, "sex": "female"},
        ground_truth_diagnosis="vasovagal_syncope",
        answers={
            "onset": "happened right at the clinic during a blood draw",
            "associated_symptoms": "felt warm, nauseated, and sweaty right before, then everything went gray; woke up within a few seconds, felt fine after resting",
            "past_medical_history": "always felt queasy around needles",
        },
        exam_results={"vital_signs": "BP 112/70, HR 68, RR 14, Temp 36.7, SpO2 99%",
                      "cardiac_auscultation": "normal heart sounds"},
        test_results={"ecg": "normal sinus rhythm"},
    ),
    SyntheticCase(
        case_id="Blind4_27_RoomSpinningRollingOverInBed", category="benign",
        chief_complaint="the room spins for a few seconds every time I roll over in bed", demographics={"age": 52, "sex": "female"},
        ground_truth_diagnosis="bppv",
        answers={
            "onset": "started three days ago, keeps happening with certain head movements",
            "character": "brief spinning sensation, lasts under a minute each time",
            "associated_symptoms": "a little nausea during the spells; denies hearing loss, denies ringing in ears, denies weakness or numbness, denies headache",
        },
        exam_results={"neuro_exam": "normal neuro exam, no focal deficits",
                      "vital_signs": "BP 120/76, HR 74, RR 14, Temp 36.8, SpO2 99%"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind4_28_DizzyStandingUpElderlyPolypharmacy", category="elderly_polypharmacy",
        chief_complaint="every time I stand up from my chair the room goes dark for a second", demographics={"age": 84, "sex": "male"},
        ground_truth_diagnosis="orthostatic_hypotension",
        answers={
            "onset": "been happening for about two weeks, worse in the mornings",
            "associated_symptoms": "feels fine once he sits back down; denies chest pain, denies palpitations",
            "past_medical_history": "hypertension, benign prostatic hyperplasia, depression",
            "medication": "takes a blood pressure pill, tamsulosin for his prostate, and an antidepressant",
        },
        exam_results={"vital_signs": "BP 124/78 lying down, HR 74; BP 92/58 standing, HR 88; RR 16, Temp 36.7, SpO2 98%"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind4_29_PalpitationsElderlyIrregularPulse", category="elderly",
        chief_complaint="my heart keeps doing this fluttery skipping thing on and off", demographics={"age": 73, "sex": "female"},
        ground_truth_diagnosis="cardiac_arrhythmia",
        answers={
            "onset": "comes and goes over the past week, lasts a few minutes each time",
            "associated_symptoms": "a little short of breath during episodes; denies chest pain, denies fainting",
            "past_medical_history": "hypertension, hyperthyroidism",
        },
        exam_results={"cardiac_auscultation": "irregularly irregular rhythm during the episode",
                      "vital_signs": "BP 132/82, HR 128 irregularly irregular, RR 18, Temp 36.8, SpO2 97%"},
        test_results={"ecg": "atrial fibrillation with rapid ventricular response"},
    ),
    SyntheticCase(
        case_id="Blind4_30_WeaknessElderlyRenalFailureDialysisMissed", category="elderly_multimorbidity",
        chief_complaint="I'm so weak today I can barely get out of bed, and my dad missed dialysis", demographics={"age": 68, "sex": "male"},
        ground_truth_diagnosis="severe_electrolyte_disorder",
        answers={
            "onset": "weakness started yesterday, worse today",
            "associated_symptoms": "some tingling around his mouth and hands; denies chest pain, denies confusion",
            "past_medical_history": "end-stage renal disease on hemodialysis, missed his last two scheduled dialysis sessions",
            "medication": "none new",
        },
        exam_results={"vital_signs": "BP 148/88, HR 52, RR 18, Temp 36.8, SpO2 97%",
                      "cardiac_auscultation": "regular but slow rhythm",
                      "extremity_exam": "generalized weakness, symmetric"},
        test_results={"bmp": "potassium 7.2 mEq/L", "ecg": "peaked T waves, widened QRS"},
    ),
    SyntheticCase(
        case_id="Blind4_31_FeverProductiveCoughElderlyNursingHome", category="elderly",
        chief_complaint="mom's been coughing up thick phlegm and burning up with fever", demographics={"age": 88, "sex": "female"},
        ground_truth_diagnosis="pneumonia",
        answers={
            "onset": "started three days ago, worsening",
            "associated_symptoms": "shortness of breath with any activity, chills; eating less than usual",
            "past_medical_history": "lives in a nursing facility, mild dementia",
        },
        exam_results={"vital_signs": "BP 116/70, HR 100, RR 24, Temp 38.9, SpO2 92%",
                      "lung_auscultation": "crackles at the right lower lung base",
                      "mental_status_exam": "alert, mildly more confused than her baseline per staff"},
        test_results={"cxr": "right lower lobe consolidation"},
    ),
    SyntheticCase(
        case_id="Blind4_32_ThrobbingOneSidedHeadacheAuraFamilyHistory", category="conflicting_findings",
        chief_complaint="I saw shimmering zigzag lines before this pounding headache started", demographics={"age": 29, "sex": "female"},
        ground_truth_diagnosis="migraine",
        answers={
            "onset": "the visual shimmering lasted about 20 minutes, then the headache followed",
            "character": "throbbing, one-sided, over my right temple",
            "associated_symptoms": "light and noise bother me a lot right now, some nausea; denies weakness, denies numbness, denies slurred speech",
            "family_history": "my mother gets the same kind of headaches",
        },
        exam_results={"neuro_exam": "normal neuro exam, no focal deficits",
                      "vital_signs": "BP 118/74, HR 76, RR 14, Temp 36.8, SpO2 99%"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind4_33_VagueUnwellElderlySulfonylureaHypoglycemia", category="vague_language",
        chief_complaint="grandpa just isn't acting like himself and seems out of it", demographics={"age": 79, "sex": "male"},
        ground_truth_diagnosis="hypoglycemia",
        notes="Elderly, oral-sulfonylurea-driven hypoglycemia -- a distinct mechanism from every "
              "hypoglycemia case elsewhere in this repo (not insulin, not young-adult, not "
              "post-bariatric), and the chief complaint is deliberately vague rather than "
              "symptom-specific, testing the soft-routing/cross-cutting-diagnosis pathway.",
        answers={
            "onset": "family noticed him acting strangely about an hour ago, skipped lunch today",
            "associated_symptoms": "sweaty, trembling a little, not answering questions clearly; family says he seems 'far away'",
            "past_medical_history": "type 2 diabetes managed with glipizide",
            "medication": "glipizide twice daily",
        },
        exam_results={"mental_status_exam": "confused, slow to respond, diaphoretic",
                      "vital_signs": "BP 132/80, HR 98, RR 16, Temp 36.6, SpO2 98%"},
        test_results={"glucose_point_of_care": "41 mg/dL"},
    ),
    SyntheticCase(
        case_id="Blind4_34_WheezeNormalOxygenationNoAllergen", category="negative_finding_centric",
        chief_complaint="I'm wheezing and a bit short of breath, same as my usual flare-ups", demographics={"age": 30, "sex": "female"},
        ground_truth_diagnosis="asthma_copd_exacerbation",
        notes="Negative-finding-centric: normal oxygenation and no allergen exposure, so a real "
              "systemic-derangement signal never fires here -- the dangerous mimic (anaphylaxis) "
              "must not win just because both diagnoses share 'wheeze'.",
        answers={
            "onset": "started this morning after a run in cold air",
            "associated_symptoms": "just the wheeze and a tight chest; denies hives, denies facial swelling, denies throat tightness, denies new food or medication",
            "past_medical_history": "known asthma since childhood, usually triggered by cold air and exercise",
            "medication": "uses an albuterol inhaler as needed",
        },
        exam_results={"vital_signs": "BP 118/74, HR 92, RR 20, Temp 36.9, SpO2 96%",
                      "lung_auscultation": "bilateral expiratory wheeze, prolonged expiration",
                      "skin_exam": "no urticaria, no swelling"},
        test_results={},
    ),
]
