"""Held-out evaluation cases (spec section 19/22): NEVER used to tune any default in
nova_agent/config.py (unlike evaluation/cases.py's original 8, which the current stop-policy/
utility-weight defaults were iterated against during development). These exist specifically to
check generalization: paraphrases, demographic variation, ambiguity, misleading presentations,
negative-finding-centric cases, mimics in both directions, insufficient information, noisy
free text, an unmapped chief complaint, and a Korean-language case.

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
