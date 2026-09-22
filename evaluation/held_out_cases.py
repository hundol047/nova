"""Held-out evaluation cases (spec section 19/22): NEVER used to tune any default in
nova_agent/config.py (unlike evaluation/cases.py's original 8, which the current stop-policy/
utility-weight defaults were iterated against during development). These exist specifically to
check generalization: paraphrases, demographic variation, ambiguity, misleading presentations,
negative-finding-centric cases, mimics in both directions, insufficient information, noisy
free text, an unmapped chief complaint, a Korean-language case, a pregnancy risk-factor case, a
medication-risk case, a multi-system comorbidity case, and three long-tail critical diagnoses
(anaphylaxis, aortic dissection via back pain, tension pneumothorax) never exercised as a ground
truth anywhere in evaluation/cases.py's tuning set.

Deliberately a moderate expansion (18 cases), not padding toward a round number: each case below
covers a genuinely distinct clinical scenario/category, not a reworded duplicate of an existing
one (spec section 15/29 explicitly warns against same-template-different-wording padding).

Still hand-authored synthetic vignettes, never real patient data.
"""

from __future__ import annotations

from evaluation.cases import SyntheticCase

HELD_OUT_CASES = [
    SyntheticCase(
        case_id="ChestPain02_Paraphrase", category="paraphrase",
        chief_complaint="pressure in my chest", demographics={"age": 62, "sex": "female"},
        ground_truth_diagnosis="acute_coronary_syndrome",
        notes="Same underlying presentation as ChestPain01 but reworded throughout and a different "
              "age/sex -- checks the agent isn't just pattern-matching the tuning case's exact wording.",
        answers={
            "onset": "it came on out of nowhere about forty minutes ago",
            "character": "it feels like a heavy weight sitting on top of my chest, not a sharp pain",
            "aggravating": "climbing the stairs makes it worse; nothing feels like it's tearing or ripping",
            "associated_symptoms": "I broke out in a cold sweat and felt sick to my stomach, and it "
                                    "spread down into my left arm; no cough, no calf pain, no coughing up blood",
            "past_medical_history": "high blood pressure and high cholesterol",
            "family_history": "my brother had a heart attack in his fifties",
            "social_history": "quit smoking five years ago",
        },
        exam_results={
            "vital_signs": "BP 148/92, HR 98, RR 18, Temp 36.9, SpO2 96%",
            "general_appearance": "pale, sweaty, clutching her chest",
        },
        test_results={"ecg": "ST depression in the lateral leads", "troponin": "elevated troponin",
                      "cxr": "no widened mediastinum"},
    ),
    SyntheticCase(
        case_id="Dyspnea02_AgeSexVariation", category="age_sex_variation",
        chief_complaint="short of breath", demographics={"age": 74, "sex": "male"},
        ground_truth_diagnosis="pulmonary_embolism",
        notes="Same diagnosis as Dyspnea01 but opposite demographic (elderly male, post-surgical "
              "risk factor instead of young female on OCPs) -- checks risk-factor matching "
              "generalizes across different demographic risk-factor phrasing.",
        answers={
            "onset": "sudden, about an hour ago",
            "character": "sharp pain that's worse when I breathe in",
            "associated_symptoms": "my right calf has been swollen and sore since my hip surgery last week; "
                                    "denies fever, denies wheeze",
            "past_medical_history": "had hip replacement surgery eight days ago, otherwise healthy",
        },
        exam_results={
            "vital_signs": "BP 118/76, HR 115, RR 24, Temp 37.0, SpO2 90%",
            "extremity_exam": "right calf swelling, warmth, and tenderness",
            "lung_auscultation": "clear bilaterally",
        },
        test_results={"d_dimer": "elevated D-dimer",
                      "ct_chest_angio": "filling defect in the right pulmonary artery",
                      "ecg": "sinus tachycardia"},
    ),
    SyntheticCase(
        case_id="ChestPain03_Ambiguous", category="ambiguous", scoring_expected=False,
        chief_complaint="mild chest discomfort", demographics={"age": 29, "sex": "female"},
        ground_truth_diagnosis="gerd",
        notes="Genuinely borderline: young, low cardiac risk, vague symptoms that could plausibly "
              "be GERD, musculoskeletal, or anxiety. Excluded from the strict accuracy denominator "
              "-- checked instead for safe, non-overconfident behavior (see benchmark.py).",
        answers={
            "onset": "on and off for the past two days",
            "character": "a mild burning feeling, comes and goes",
            "aggravating": "seems worse after eating, and when I lie down after a meal",
            "relieving": "antacid tablets seem to help a little",
            "associated_symptoms": "denies radiation to my arm, denies shortness of breath, denies sweating",
            "past_medical_history": "none",
            "social_history": "drinks coffee daily, occasional spicy food",
        },
        exam_results={"vital_signs": "BP 112/70, HR 74, RR 14, Temp 36.7, SpO2 99%"},
        test_results={"ecg": "normal sinus rhythm"},
    ),
    SyntheticCase(
        case_id="AbdominalPain02_DangerousMimic", category="dangerous_mimic",
        chief_complaint="nausea and vomiting", demographics={"age": 71, "sex": "female"},
        ground_truth_diagnosis="acute_coronary_syndrome",
        notes="Atypical ('silent') MI presenting as nausea/vomiting rather than classic chest pain "
              "-- a well-documented real pattern in elderly/diabetic/female patients. Tests whether "
              "the agent anchors on the chief-complaint tag alone or follows the evidence "
              "(vomiting is already tagged onto acute_coronary_syndrome for exactly this reason).",
        answers={
            "onset": "started a couple hours ago, feels different from my usual stomach troubles",
            "associated_symptoms": "some chest tightness and sweating along with the nausea; "
                                    "denies abdominal tenderness, denies diarrhea, denies fever",
            "past_medical_history": "type 2 diabetes, high blood pressure",
            "family_history": "mother had heart disease",
        },
        exam_results={
            "vital_signs": "BP 100/68, HR 102, RR 20, Temp 36.8, SpO2 95%",
            "abdominal_exam": "soft, mild epigastric discomfort, no rebound or guarding",
            "general_appearance": "diaphoretic, uncomfortable",
        },
        test_results={"ecg": "ST elevation in inferior leads", "troponin": "elevated troponin",
                      "lipase": "normal"},
    ),
    SyntheticCase(
        case_id="ChestPain04_BenignMimic", category="benign_mimic",
        chief_complaint="chest tightness and racing heart", demographics={"age": 24, "sex": "female"},
        ground_truth_diagnosis="panic_attack",
        notes="Dramatic, alarming-SOUNDING presentation (chest tightness, palpitations, fear of "
              "dying) that is actually benign -- the mirror image of the dangerous-mimic case: "
              "tests that the agent doesn't over-call ACS/PE just because the complaint sounds scary.",
        answers={
            "onset": "sudden, about 15 minutes ago, right after a big argument with my roommate",
            "associated_symptoms": "I feel like I can't catch my breath, tingling around my lips and "
                                    "fingers, and I felt like I was going to die; "
                                    "denies radiation to my arm, denies calf swelling, denies fever",
            "past_medical_history": "I've had panic attacks before, diagnosed with anxiety",
            "social_history": "stressful week at work",
        },
        exam_results={"vital_signs": "BP 128/80, HR 108, RR 22, Temp 36.9, SpO2 99%",
                      "general_appearance": "anxious, hyperventilating, but improving as she calms down"},
        test_results={"ecg": "sinus tachycardia, no ST changes"},
    ),
    SyntheticCase(
        case_id="Dizziness02_NegativeFindingCentric", category="negative_finding_centric",
        chief_complaint="dizzy spells", demographics={"age": 68, "sex": "male"},
        ground_truth_diagnosis="orthostatic_hypotension",
        notes="Defined almost entirely by systematic exclusion of dangerous causes rather than by "
              "strong positive findings for the true diagnosis -- tests whether ruling things out "
              "is itself recognized as diagnostically useful.",
        answers={
            "onset": "happens when I stand up quickly from sitting or lying down",
            "relieving": "goes away within a few seconds if I sit back down",
            "associated_symptoms": "denies chest pain, denies palpitations before the episodes, "
                                    "denies slurred speech, denies focal weakness, denies severe headache, "
                                    "denies hearing loss",
            "medication": "I take a water pill for my blood pressure",
            "social_history": "haven't been drinking much water lately",
        },
        exam_results={"vital_signs": "BP 98/62, HR 88, RR 16, Temp 36.8, SpO2 98%",
                      "neuro_exam": "no focal neurological deficit"},
    ),
    SyntheticCase(
        case_id="Headache02_InsufficientInfo", category="insufficient_info", scoring_expected=False,
        chief_complaint="headache", demographics={"age": 40, "sex": "male"},
        ground_truth_diagnosis="tension_headache",
        notes="An uncooperative/vague historian -- almost every answer is non-informative. Checked "
              "for safe behavior (no crash, no duplicate actions, forced diagnosis within the turn "
              "limit) rather than for diagnostic accuracy, since the true diagnosis genuinely can't "
              "be pinned down from these responses.",
        answers={
            "onset": "I don't really remember, it's just been going on",
            "character": "I don't know, it just hurts",
            "severity": "not sure, maybe medium?",
            "associated_symptoms": "I don't know, maybe? Hard to say",
            "past_medical_history": "I don't know, I don't really go to the doctor",
        },
        default_answer="I'm not sure.",
        default_exam_result="Unremarkable.",
        default_test_result="Normal.",
        exam_results={"vital_signs": "BP 122/78, HR 76, RR 16, Temp 36.8, SpO2 99%"},
    ),
    SyntheticCase(
        case_id="ChestPain05_NoisyText", category="noisy_text",
        chief_complaint="chest thing", demographics={"age": 55, "sex": "male"},
        ground_truth_diagnosis="acute_coronary_syndrome",
        notes="Same clinical picture as ChestPain01 but every answer is wrapped in rambling, "
              "off-topic, typo'd free text -- tests robustness of the keyword/negation parsing "
              "against real-world messy input rather than clean scripted sentences.",
        answers={
            "onset": "um so basically like an hour ago i was jsut sitting on the couch watching tv, "
                     "kinda randomly it just started, sry for the long message lol",
            "character": "idk how to describe it exactly but its like a really heavy pressure thing, "
                         "not rly sharp if that makes sense, also my dog needed a walk earlier lol anyway",
            "aggravating": "it got worse when i tried to walk to the kitchen, denies any tearing or "
                           "ripping feeling tho, more like squeezing",
            "associated_symptoms": "omg yeah i started sweating like crazy out of nowhere and felt "
                                    "kinda sick, and theres this achy feeling going down my left arm, "
                                    "denies coughing up blood, denies leg swelling, sry this is so long",
            "past_medical_history": "i have high blood pressure i think, and my cholesterol is bad too "
                                     "according to my last checkup",
            "family_history": "my dad had a heart attack when he was like 58 i think",
        },
        exam_results={"vital_signs": "BP 152/94, HR 104, RR 20, Temp 37.0, SpO2 96%",
                      "general_appearance": "diaphoretic, uncomfortable"},
        test_results={"ecg": "ST elevation in anterior leads", "troponin": "elevated troponin"},
    ),
    SyntheticCase(
        case_id="Unknown01_UnmappedComplaint", category="unknown_complaint", scoring_expected=False,
        chief_complaint="tingling in my fingers and toes", demographics={"age": 45, "sex": "female"},
        ground_truth_diagnosis="severe_electrolyte_disorder",
        notes="Chief complaint doesn't match any of the 15 classifier tags (falls through to the "
              "whole-catalog fallback) -- checked for graceful, non-crashing handling and a "
              "turn-limit-respecting diagnosis rather than for exact accuracy.",
        answers={
            "onset": "started a few days ago, gradually",
            "associated_symptoms": "some muscle weakness and my heart feels like it skips sometimes; "
                                    "denies chest pain, denies headache, denies fever",
            "past_medical_history": "chronic kidney disease",
            "medication": "I take a potassium-sparing blood pressure medication",
        },
        exam_results={"vital_signs": "BP 132/84, HR 58, RR 16, Temp 36.8, SpO2 98%",
                      "cardiac_auscultation": "irregular rhythm noted"},
        test_results={"bmp": "potassium 6.8", "ecg": "peaked T waves"},
    ),
    SyntheticCase(
        case_id="ChestPain06_Korean", category="korean_language",
        chief_complaint="가슴 통증", demographics={"age": 60, "sex": "male"},
        ground_truth_diagnosis="acute_coronary_syndrome",
        notes="Same ACS presentation as ChestPain01, entirely in Korean -- tests that the "
              "Korean-language negation markers and keyword matching (matching.py/state.py include "
              "Korean tokens) work end to end, not just as an afterthought.",
        answers={
            "onset": "한 시간 전에 갑자기 시작되었습니다",
            "character": "가슴을 무언가로 누르는 듯한 느낌입니다",
            "aggravating": "운동하면 더 심해집니다; 찢어지는 듯한 통증은 아닙니다",
            "associated_symptoms": "식은땀이 나고 메스꺼우며 왼쪽 팔로 통증이 퍼집니다; "
                                    "종아리 부종은 없습니다, 객혈은 없습니다",
            "past_medical_history": "고혈압과 당뇨병이 있습니다",
            "family_history": "아버지가 55세에 심근경색을 앓으셨습니다",
        },
        exam_results={"vital_signs": "BP 150/95, HR 105, RR 20, Temp 37.0, SpO2 97%"},
        test_results={"ecg": "ST elevation in anterior leads", "troponin": "elevated troponin"},
    ),
    SyntheticCase(
        case_id="Fever02_MeningitisPresentation", category="paraphrase",
        chief_complaint="really high fever and can't think straight", demographics={"age": 35, "sex": "female"},
        ground_truth_diagnosis="meningitis",
        notes="Same diagnosis as Fever01 but different phrasing/demographics -- another "
              "generalization check for a different critical diagnosis.",
        answers={
            "onset": "since last night, getting worse",
            "associated_symptoms": "my neck feels really stiff and light hurts my eyes, and I've "
                                    "been confused; denies a sudden severe headache, denies weakness on one side",
            "past_medical_history": "none",
            "social_history": "one of my coworkers was out sick with something similar last week",
        },
        exam_results={
            "meningeal_signs": "positive neck stiffness",
            "vital_signs": "BP 98/60, HR 128, RR 24, Temp 39.8, SpO2 95%",
            "mental_status_exam": "confused, slow to respond",
        },
        test_results={"lumbar_puncture": "CSF pleocytosis, low glucose", "blood_culture": "gram-positive cocci",
                      "cbc": "elevated white blood cell count"},
    ),
    SyntheticCase(
        case_id="Dyspnea03_PregnancyRiskFactor", category="pregnancy_risk_factor",
        chief_complaint="short of breath", demographics={"age": 31, "sex": "female"},
        ground_truth_diagnosis="pulmonary_embolism",
        notes="Pregnancy itself is a major, independent VTE risk factor (distinct from Dyspnea02's "
              "post-surgical elderly-male presentation) -- checks the agent weighs a risk factor "
              "that is a demographic/history fact rather than a dramatic symptom.",
        answers={
            "onset": "sudden, about two hours ago",
            "character": "sharp pain on the right side of my chest, worse when I breathe in",
            "associated_symptoms": "my right leg has been swollen for a few days; "
                                    "denies fever, denies wheeze, denies cough",
            "past_medical_history": "currently 28 weeks pregnant, otherwise healthy",
            "social_history": "denies smoking, denies recent travel",
        },
        exam_results={
            "vital_signs": "BP 112/70, HR 118, RR 26, Temp 37.0, SpO2 91%",
            "extremity_exam": "right calf swelling and tenderness",
            "lung_auscultation": "clear bilaterally",
        },
        test_results={"d_dimer": "elevated D-dimer",
                      "ct_chest_angio": "filling defect in the right pulmonary artery",
                      "ecg": "sinus tachycardia"},
    ),
    SyntheticCase(
        case_id="Headache03_AnticoagulantRisk", category="medication_risk",
        chief_complaint="bad headache", demographics={"age": 76, "sex": "male"},
        ground_truth_diagnosis="subarachnoid_hemorrhage",
        notes="Anticoagulant use (warfarin) is itself a documented medication-risk trigger in "
              "red_flags/demographic_and_medication_risk.json for headache presentations -- tests "
              "that the agent weighs that risk factor together with, not instead of, the classic "
              "thunderclap-headache features.",
        answers={
            "onset": "sudden, about thirty minutes ago, worst headache I've ever had",
            "character": "explosive, thunderclap quality",
            "severity": "10 out of 10",
            "associated_symptoms": "neck stiffness and one episode of vomiting; "
                                    "denies fever, denies focal weakness",
            "past_medical_history": "atrial fibrillation, takes warfarin daily",
            "medication": "warfarin for atrial fibrillation",
        },
        exam_results={
            "meningeal_signs": "positive neck stiffness",
            "neuro_exam": "no focal neurological deficit",
            "vital_signs": "BP 172/98, HR 92, RR 16, Temp 37.0, SpO2 98%",
        },
        test_results={"ct_head": "subarachnoid blood seen on non-contrast CT"},
    ),
    SyntheticCase(
        case_id="Fever03_DiabeticUrosepsis", category="comorbidity",
        chief_complaint="fever and feeling confused", demographics={"age": 79, "sex": "female"},
        ground_truth_diagnosis="sepsis",
        notes="Multi-system comorbidity case: diabetes (infection risk) + an untreated urinary "
              "source progressing to systemic sepsis with altered mental status and hypotension -- "
              "tests whether the agent connects a urinary-symptom history to a fever/confusion "
              "chief complaint rather than treating them as unrelated.",
        answers={
            "onset": "fever started two days ago, confusion since this morning",
            "associated_symptoms": "burning with urination for the past three days, chills; "
                                    "denies neck stiffness, denies severe headache, denies rash",
            "past_medical_history": "type 2 diabetes, poorly controlled",
            "social_history": "lives alone, family says she seemed 'not herself' today",
        },
        exam_results={
            "vital_signs": "BP 84/52, HR 128, RR 26, Temp 39.4, SpO2 93%",
            "mental_status_exam": "confused, oriented to person only",
            "skin_exam": "warm, flushed, no rash",
        },
        test_results={"lactate": "elevated lactate", "blood_culture": "gram-negative rods",
                      "urinalysis": "positive leukocyte esterase and nitrites",
                      "cbc": "elevated white blood cell count"},
    ),
    SyntheticCase(
        case_id="Dyspnea04_Anaphylaxis", category="long_tail",
        chief_complaint="trouble breathing after a bee sting", demographics={"age": 26, "sex": "male"},
        ground_truth_diagnosis="anaphylaxis",
        notes="Long-tail critical diagnosis never exercised as a held-out ground truth before, and "
              "the only critical disease in the catalog with an EMPTY minimum_workup/discriminating_"
              "tests list -- tests that the agent can still recognize and act on a clinical "
              "diagnosis made entirely from history/exam, with no confirmatory lab required.",
        answers={
            "onset": "sudden, within minutes of being stung on the arm",
            "associated_symptoms": "my lips and face are swelling up and my throat feels tight, "
                                    "and I'm covered in hives; denies chest pain, denies fever",
            "allergy": "I think I'm allergic to bee stings, never confirmed",
            "past_medical_history": "none",
        },
        exam_results={
            "skin_exam": "diffuse urticaria, facial and lip swelling",
            "lung_auscultation": "bilateral wheeze",
            "vital_signs": "BP 82/50, HR 130, RR 28, Temp 36.9, SpO2 92%",
        },
        test_results={},
    ),
    SyntheticCase(
        case_id="BackPain01_AorticDissection", category="long_tail",
        chief_complaint="sudden severe back pain", demographics={"age": 67, "sex": "male"},
        ground_truth_diagnosis="aortic_dissection",
        notes="Aortic dissection appears in the tuning set only as a chest-pain differential "
              "candidate to be ruled out, never as a held-out ground truth reached via a different "
              "chief-complaint tag (back_pain) -- tests generalization of the same disease entry "
              "across chief complaints, not just across phrasing of the same complaint.",
        answers={
            "onset": "sudden onset ten minutes ago",
            "character": "tearing, ripping pain between my shoulder blades",
            "location": "upper back, between the shoulder blades",
            "past_medical_history": "poorly controlled high blood pressure",
        },
        exam_results={
            "vital_signs": "BP 190/110, HR 96, RR 18, Temp 36.8, SpO2 97%",
            "extremity_exam": "diminished pulse in the left arm compared to the right",
            "cardiac_auscultation": "new diastolic murmur",
        },
        test_results={"ct_aorta": "intimal flap seen in the descending aorta",
                      "cxr": "widened mediastinum", "ecg": "normal sinus rhythm, no ST changes"},
    ),
    SyntheticCase(
        case_id="Dyspnea05_TensionPneumothorax", category="long_tail",
        chief_complaint="can't breathe after a car accident", demographics={"age": 34, "sex": "male"},
        ground_truth_diagnosis="tension_pneumothorax",
        notes="Another long-tail critical diagnosis never exercised as a held-out ground truth --  "
              "post-trauma presentation with classic unilateral absent breath sounds, testing exam-"
              "finding-driven (not history-driven) recognition.",
        answers={
            "onset": "sudden, right after the car accident about 20 minutes ago",
            "character": "sharp right-sided chest pain, worse with breathing",
            "past_medical_history": "none",
        },
        exam_results={
            "lung_auscultation": "absent breath sounds on the right side",
            "vital_signs": "BP 88/58, HR 132, RR 34, Temp 36.9, SpO2 85%",
            "general_appearance": "in severe respiratory distress, tracheal deviation to the left",
        },
        test_results={"cxr": "large right-sided pneumothorax with mediastinal shift"},
    ),
    SyntheticCase(
        case_id="Urinary02_Pyelonephritis", category="paraphrase",
        chief_complaint="burning when I pee and my side hurts", demographics={"age": 42, "sex": "female"},
        ground_truth_diagnosis="pyelonephritis",
        notes="A different genitourinary diagnosis than UrinarySymptoms01 (upper vs. lower UTI) "
              "phrased colloquially -- checks the agent doesn't default to the 'easy' benign answer "
              "(cystitis) when systemic/flank findings point higher.",
        answers={
            "onset": "started three days ago, been getting worse",
            "location": "pain in my right lower back/side",
            "associated_symptoms": "fever, chills, nausea, and it burns when I urinate; denies vaginal bleeding",
            "past_medical_history": "had a bladder infection a few months ago that wasn't treated",
        },
        exam_results={
            "costovertebral_tenderness": "positive right-sided costovertebral angle tenderness",
            "vital_signs": "BP 108/68, HR 110, RR 20, Temp 38.9, SpO2 97%",
        },
        test_results={"urinalysis": "positive leukocyte esterase and nitrites", "urine_culture": "pending",
                      "cbc": "elevated white blood cell count"},
    ),
]
