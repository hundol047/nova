"""Blind evaluation set v3 (spec: a genuinely blind final check, authored before any further
tuning pass and never adjusted afterward to match its own answers).

Unlike `generalization_cases_v2.py` (which DID end up driving two real code fixes after its
failures were analyzed -- see README.md's "Evaluation & results" section for that history) and
`generalization_stress_cases.py` (deliberately built to probe those exact two fix patterns), this
file exists to answer a different question: does the agent generalize to a batch of cases nobody
looked at while writing the fixes at all?

Rules followed while authoring this file (self-imposed, and left here so a future session can
audit them):
  1. No sentence, clause, or distinctive phrase was copied from evaluation/cases.py,
     evaluation/held_out_cases.py, evaluation/generalization_cases_v2.py, or
     evaluation/generalization_stress_cases.py -- each vignette was written fresh.
  2. Not a single case is a reworded variant of a previously-known failure (no case targets the
     hypoglycemia or migraine/stroke patterns specifically -- those are what the stress set is for).
  3. Every case's ground_truth_diagnosis and reasoning was decided BEFORE running any benchmark
     against this file, and this file was not edited after seeing blind_benchmark's results.

32 cases across common / dangerous / atypical / elderly / polypharmacy / negative-finding /
conflicting-evidence categories, spanning the majority of this repo's 34-diagnosis knowledge base.
Still hand-authored synthetic vignettes, never real patient data.
"""

from __future__ import annotations

from evaluation.cases import SyntheticCase

BLIND_CASES_V3 = [
    SyntheticCase(
        case_id="Blind01_ClassicViralPharyngitis", category="common",
        chief_complaint="my throat is scratchy and I feel congested", demographics={"age": 23, "sex": "female"},
        ground_truth_diagnosis="viral_uri",
        answers={
            "duration": "a day and a half so far",
            "associated_symptoms": "stuffy nose and a mild cough; no trouble swallowing, no rash, no ear pain",
            "social_history": "my boyfriend had the same thing last week",
        },
        exam_results={"vital_signs": "BP 112/70, HR 76, RR 14, Temp 37.4, SpO2 99%",
                      "lung_auscultation": "clear bilaterally"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind02_ElderlySilentMI", category="atypical_elderly",
        chief_complaint="I just don't feel right, very tired", demographics={"age": 79, "sex": "female"},
        ground_truth_diagnosis="acute_coronary_syndrome",
        notes="Diabetic-neuropathy-blunted, silent presentation -- fatigue and mild nausea instead "
              "of classic chest pain, a well-documented atypical MI pattern in elderly diabetics.",
        answers={
            "onset": "started sometime yesterday, hard to say exactly when",
            "associated_symptoms": "just tired and a little queasy, and short of breath walking to "
                                    "the bathroom; no chest pain that she's noticed",
            "past_medical_history": "type 2 diabetes for twenty years, high blood pressure",
            "medication": "metformin and lisinopril",
        },
        exam_results={"vital_signs": "BP 100/62, HR 96, RR 20, Temp 36.6, SpO2 94%",
                      "cardiac_auscultation": "soft S1, no murmur", "general_appearance": "pale, diaphoretic"},
        test_results={"ecg": "ST depression in the inferior leads", "troponin": "elevated troponin"},
    ),
    SyntheticCase(
        case_id="Blind03_WakeUpStroke", category="atypical",
        chief_complaint="my husband can't move his right arm, we just woke up", demographics={"age": 66, "sex": "male"},
        ground_truth_diagnosis="ischemic_stroke",
        notes="'Wake-up stroke' -- exact symptom onset is unknown (occurred sometime during sleep), "
              "a genuinely different discriminating challenge from a witnessed sudden-onset case.",
        answers={
            "onset": "unknown -- he went to bed fine and woke up like this this morning",
            "associated_symptoms": "his speech sounds slurred and the right side of his mouth droops; "
                                    "denies headache, denies confusion otherwise",
            "past_medical_history": "atrial fibrillation, high cholesterol",
            "medication": "not currently on a blood thinner, stopped it a year ago",
        },
        exam_results={"neuro_exam": "right facial droop, right arm drift, dysarthria",
                      "vital_signs": "BP 172/98, HR 84 irregularly irregular, RR 16, Temp 36.9, SpO2 97%"},
        test_results={"ct_head": "acute infarct in the left MCA territory", "glucose_point_of_care": "108 mg/dL"},
    ),
    SyntheticCase(
        case_id="Blind04_PostBariatricHypoglycemia", category="atypical",
        chief_complaint="I get shaky and confused a couple hours after eating", demographics={"age": 34, "sex": "female"},
        ground_truth_diagnosis="hypoglycemia",
        notes="Late dumping syndrome / reactive post-bariatric-surgery hypoglycemia -- not "
              "medication-related and not diabetic, a genuinely distinct mechanism from every "
              "hypoglycemia case elsewhere in this repo's evaluation suite.",
        answers={
            "onset": "about two hours after lunch, comes on gradually then hits hard",
            "associated_symptoms": "shaky, sweaty, heart racing, and my thoughts get foggy; "
                                    "eating something sweet fixes it within a few minutes",
            "past_medical_history": "gastric bypass surgery eighteen months ago, otherwise healthy",
            "medication": "just a daily multivitamin",
        },
        exam_results={"mental_status_exam": "mildly confused, diaphoretic", "vital_signs": "BP 108/66, HR 110, RR 16, Temp 36.7, SpO2 99%"},
        test_results={"glucose_point_of_care": "44 mg/dL"},
    ),
    SyntheticCase(
        case_id="Blind05_TraumaticPneumothorax", category="dangerous",
        chief_complaint="sharp pain in my side and I can't get a full breath", demographics={"age": 29, "sex": "male"},
        ground_truth_diagnosis="tension_pneumothorax",
        notes="Traumatic mechanism (fall + rib fracture) rather than spontaneous, a distinct "
              "scenario from the existing spontaneous-pneumothorax case elsewhere.",
        answers={
            "onset": "right after I fell off a ladder about twenty minutes ago",
            "character": "sharp, stabbing, worse every time I try to breathe deep",
            "associated_symptoms": "feels like I can't get enough air, and my neck veins look "
                                    "bulgy according to my coworker",
            "past_medical_history": "none",
        },
        exam_results={"vital_signs": "BP 84/56, HR 128, RR 32, Temp 36.8, SpO2 86%",
                      "lung_auscultation": "absent breath sounds on the right side, trachea shifted to the left"},
        test_results={"cxr": "large right-sided pneumothorax with mediastinal shift"},
    ),
    SyntheticCase(
        case_id="Blind06_RuralEctopic", category="dangerous",
        chief_complaint="sharp pain on one side of my belly and I feel like I might pass out", demographics={"age": 27, "sex": "female"},
        ground_truth_diagnosis="ectopic_pregnancy",
        answers={
            "onset": "started a few hours ago, getting worse",
            "location": "lower left side",
            "associated_symptoms": "my period is about three weeks late, and some spotting; felt "
                                    "dizzy and almost fainted when I stood up",
            "past_medical_history": "had a pelvic infection two years ago",
            "social_history": "sexually active, not currently using contraception",
        },
        exam_results={"vital_signs": "BP 92/58, HR 118, RR 18, Temp 36.9, SpO2 98%",
                      "pelvic_exam": "left adnexal tenderness"},
        test_results={"beta_hcg": "positive, elevated", "pelvic_ultrasound": "left adnexal mass, no intrauterine pregnancy seen"},
    ),
    SyntheticCase(
        case_id="Blind07_PeanutAnaphylaxis", category="dangerous",
        chief_complaint="my throat feels like it's closing up", demographics={"age": 19, "sex": "male"},
        ground_truth_diagnosis="anaphylaxis",
        answers={
            "onset": "within a few minutes of eating something at a restaurant, maybe peanuts",
            "associated_symptoms": "lips are swelling, hives all over my arms and chest, feel "
                                    "wheezy and lightheaded",
            "past_medical_history": "known peanut allergy since childhood, usually carries an epi-pen but forgot it today",
        },
        exam_results={"vital_signs": "BP 82/50, HR 132, RR 28, Temp 36.9, SpO2 91%",
                      "skin_exam": "diffuse urticaria, lip and tongue swelling",
                      "lung_auscultation": "diffuse wheezing"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind08_DormMeningitis", category="dangerous",
        chief_complaint="pounding headache and my neck feels locked up", demographics={"age": 20, "sex": "male"},
        ground_truth_diagnosis="meningitis",
        notes="College-dorm-outbreak framing rather than the existing cases' presentations -- a "
              "distinct social/epidemiologic context for the same diagnosis.",
        answers={
            "onset": "started yesterday afternoon, steadily worse since",
            "associated_symptoms": "fever, can't stand bright light, threw up twice; two of my "
                                    "roommates also got sick this week",
            "social_history": "lives in a crowded dorm, hasn't had all his vaccinations",
        },
        exam_results={"meningeal_signs": "positive Kernig's sign, resists neck flexion",
                      "skin_exam": "scattered petechiae on the trunk",
                      "vital_signs": "BP 108/68, HR 112, RR 20, Temp 39.4, SpO2 97%"},
        test_results={"lumbar_puncture": "cloudy CSF, elevated white blood cell count, gram-negative diplococci seen"},
    ),
    SyntheticCase(
        case_id="Blind09_LiftingSAH", category="dangerous",
        chief_complaint="my head exploded with pain while I was lifting weights", demographics={"age": 41, "sex": "male"},
        ground_truth_diagnosis="subarachnoid_hemorrhage",
        notes="Exertional trigger (weightlifting) rather than the other SAH scenarios in this "
              "suite, which is itself a recognized real-world precipitant.",
        answers={
            "onset": "instant, right at the top of a heavy lift, about forty minutes ago",
            "character": "the single worst pain I've ever had in my life, like a bomb went off",
            "associated_symptoms": "vomited once, everything is too bright; denies any prior headaches like this",
            "past_medical_history": "high blood pressure, doesn't take medication regularly",
        },
        exam_results={"meningeal_signs": "mild nuchal rigidity", "neuro_exam": "no focal deficit",
                      "vital_signs": "BP 178/100, HR 90, RR 16, Temp 37.0, SpO2 98%"},
        test_results={"ct_head": "diffuse subarachnoid blood in the basal cisterns"},
    ),
    SyntheticCase(
        case_id="Blind10_SilentPESyncope", category="atypical",
        chief_complaint="I blacked out for a few seconds at work", demographics={"age": 52, "sex": "female"},
        ground_truth_diagnosis="pulmonary_embolism",
        notes="Syncope as the ONLY presenting complaint (no dyspnea or chest pain volunteered up "
              "front) -- a genuinely atypical, easy-to-miss PE presentation.",
        answers={
            "onset": "happened suddenly about an hour ago, came to within a few seconds",
            "associated_symptoms": "felt a little winded climbing the stairs earlier today, didn't "
                                    "think much of it; denies chest pain, denies palpitations before it happened",
            "past_medical_history": "had knee replacement surgery three weeks ago",
            "medication": "stopped the blood thinner they gave her after surgery a week early because she felt fine",
        },
        exam_results={"vital_signs": "BP 100/64, HR 118, RR 24, Temp 37.1, SpO2 91%",
                      "extremity_exam": "mild swelling and tenderness in the left calf"},
        test_results={"d_dimer": "markedly elevated", "ct_chest_angio": "filling defect in the left main pulmonary artery"},
    ),
    SyntheticCase(
        case_id="Blind11_ElderlyConfusedPneumonia", category="elderly_atypical",
        chief_complaint="grandma seems really out of it today", demographics={"age": 86, "sex": "female"},
        ground_truth_diagnosis="pneumonia",
        notes="Confusion as the presenting complaint rather than cough/fever -- the classic atypical "
              "elderly infection presentation, distinct from the held-out pneumonia case's clearly "
              "respiratory presentation.",
        answers={
            "onset": "family noticed she seemed more confused than usual starting this morning",
            "associated_symptoms": "not eating much the last two days, family says she has a "
                                    "little cough but wasn't a big complaint",
            "past_medical_history": "mild dementia, lives in a nursing facility",
        },
        exam_results={"mental_status_exam": "more disoriented than her baseline per staff",
                      "lung_auscultation": "crackles at the left base",
                      "vital_signs": "BP 100/60, HR 108, RR 24, Temp 38.5, SpO2 90%"},
        test_results={"cxr": "left lower lobe infiltrate", "cbc": "elevated white blood cell count"},
    ),
    SyntheticCase(
        case_id="Blind12_ElderlyAtypicalAppendicitis", category="elderly_atypical",
        chief_complaint="my stomach has felt off for a few days", demographics={"age": 81, "sex": "male"},
        ground_truth_diagnosis="appendicitis",
        notes="Vague, delayed, low-grade presentation typical of elderly appendicitis (often missed "
              "because it doesn't follow the classic young-adult migrating-pain script) -- a "
              "deliberately different presentation from the existing classic young-adult case.",
        answers={
            "onset": "started vaguely three days ago, gradually gotten worse, not sudden",
            "location": "lower right side now, though it was hard to pinpoint at first",
            "associated_symptoms": "not much appetite, low-grade fever; denies vomiting, denies diarrhea",
        },
        exam_results={"abdominal_exam": "right lower quadrant tenderness, mild guarding",
                      "vital_signs": "BP 128/78, HR 92, RR 16, Temp 37.9, SpO2 97%"},
        test_results={"cbc": "elevated white blood cell count", "ct_abdomen": "enlarged, inflamed appendix with a small abscess"},
    ),
    SyntheticCase(
        case_id="Blind13_PolypharmacyGIBleedApixaban", category="polypharmacy",
        chief_complaint="I've been passing dark stools and feel wiped out", demographics={"age": 74, "sex": "male"},
        ground_truth_diagnosis="gi_bleeding",
        notes="A different anticoagulant/NSAID pairing (apixaban + naproxen) and demographic from "
              "the existing warfarin+aspirin GI-bleed case, testing the same risk mechanism "
              "generalizes beyond the exact drug names already exercised.",
        answers={
            "associated_symptoms": "stools have been tarry and sticky for three days, and I get "
                                    "winded doing things that never used to bother me",
            "medication": "apixaban for an irregular heartbeat, and naproxen for my knee arthritis",
            "past_medical_history": "atrial fibrillation, osteoarthritis",
        },
        exam_results={"abdominal_exam": "soft, mild epigastric tenderness, no rebound",
                      "vital_signs": "BP 102/64, HR 106, RR 18, Temp 36.8, SpO2 97%",
                      "fecal_occult_blood": "positive"},
        test_results={"cbc": "hemoglobin 8.2, down from a baseline of 13"},
    ),
    SyntheticCase(
        case_id="Blind14_PolypharmacyOrthostaticDizzy", category="polypharmacy_elderly",
        chief_complaint="I get dizzy every time I get up from a chair", demographics={"age": 83, "sex": "female"},
        ground_truth_diagnosis="orthostatic_hypotension",
        answers={
            "onset": "been happening for a couple of weeks, gradually worse",
            "aggravating": "always when I stand up quickly; sitting back down makes it go away within a minute",
            "medication": "amlodipine, hydrochlorothiazide, and losartan",
            "past_medical_history": "hypertension and osteoporosis",
            "associated_symptoms": "no chest pain, no palpitations before it happens, hasn't fully fainted",
        },
        exam_results={"vital_signs": "lying BP 132/80 HR 74; standing BP 98/58 HR 92, RR 16, Temp 36.6, SpO2 98%",
                      "neuro_exam": "no focal neurological deficit",
                      "cardiac_auscultation": "normal heart sounds, no murmur"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind15_ACEInhibitorNSAIDHyperkalemia", category="polypharmacy",
        chief_complaint="my legs feel heavy and weak the last two days", demographics={"age": 70, "sex": "male"},
        ground_truth_diagnosis="severe_electrolyte_disorder",
        notes="A different medication combination (ACE inhibitor + regular ibuprofen use, reducing "
              "renal clearance) driving hyperkalemia -- distinct from the spironolactone-based "
              "electrolyte-disorder cases already in this suite.",
        answers={
            "associated_symptoms": "legs feel heavy and weak, and my heart feels like it's doing "
                                    "something funny sometimes; denies chest pain, denies confusion",
            "medication": "lisinopril for blood pressure, and he's been taking ibuprofen daily for back pain for two weeks",
            "past_medical_history": "chronic kidney disease, hypertension",
        },
        exam_results={"cardiac_auscultation": "irregular rhythm noted", "vital_signs": "BP 118/72, HR 48, RR 16, Temp 36.7, SpO2 98%"},
        test_results={"bmp": "potassium 6.9, creatinine elevated above baseline", "ecg": "peaked T waves, widened QRS"},
    ),
    SyntheticCase(
        case_id="Blind16_BenignGastroReassuring", category="negative_finding_centric",
        chief_complaint="I've been throwing up and having diarrhea since last night", demographics={"age": 29, "sex": "male"},
        ground_truth_diagnosis="gastroenteritis",
        answers={
            "onset": "started last night after dinner, several episodes since",
            "associated_symptoms": "crampy belly pain that comes and goes, no appetite; denies "
                                    "blood in the stool, denies severe unrelenting pain",
            "social_history": "a few coworkers have had the same stomach bug this week",
        },
        exam_results={"abdominal_exam": "soft, mildly tender throughout, no rebound, no guarding, no rigidity",
                      "vital_signs": "BP 118/74, HR 90, RR 16, Temp 37.6, SpO2 99%"},
        test_results={"cbc": "within normal limits"},
    ),
    SyntheticCase(
        case_id="Blind17_CostochondritisReassuring", category="negative_finding_centric",
        chief_complaint="my chest hurts when I press on it", demographics={"age": 31, "sex": "female"},
        ground_truth_diagnosis="musculoskeletal_chest_pain",
        notes="A different mechanism from the existing musculoskeletal case (post-viral-cough "
              "costochondritis rather than heavy-lifting strain) -- reassuring exam/ECG must again "
              "override the alarming keyword 'chest pain'.",
        answers={
            "onset": "started three days ago after a coughing fit from a cold",
            "character": "sharp, right over the breastbone, gets worse when I press there or take a deep breath",
            "aggravating": "pressing on the spot reproduces it exactly; denies exertional worsening, denies radiation to the arm",
            "past_medical_history": "none",
        },
        exam_results={"abdominal_exam": "not applicable",
                      "cardiac_auscultation": "normal heart sounds, no murmur",
                      "vital_signs": "BP 116/72, HR 72, RR 14, Temp 37.0, SpO2 99%"},
        test_results={"ecg": "normal sinus rhythm, no ST changes", "troponin": "within normal limits"},
    ),
    SyntheticCase(
        case_id="Blind18_ClassicBPPV", category="negative_finding_centric",
        chief_complaint="the room spins for a few seconds when I roll over in bed", demographics={"age": 58, "sex": "female"},
        ground_truth_diagnosis="bppv",
        answers={
            "onset": "started a week ago, brief episodes several times a day",
            "duration": "each spell lasts less than a minute",
            "aggravating": "rolling over in bed or looking up triggers it; denies hearing loss, denies ringing in the ears",
            "associated_symptoms": "a little nauseous during the spells but no vomiting; denies weakness, denies slurred speech",
        },
        exam_results={"neuro_exam": "no focal neurological deficit", "vital_signs": "BP 124/76, HR 70, RR 14, Temp 36.8, SpO2 99%"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind19_PancreatitisMimicsCardiac", category="conflicting_findings",
        chief_complaint="crushing pain in my upper chest and stomach", demographics={"age": 48, "sex": "male"},
        ground_truth_diagnosis="acute_pancreatitis",
        notes="'Crushing' upper-chest-and-stomach pain sounds cardiac at first, but the radiation "
              "pattern, alcohol history, and lipase should redirect the diagnosis -- a different "
              "conflicting-evidence setup from the existing pancreatitis case.",
        answers={
            "location": "right where my chest meets my stomach, goes straight through to my back",
            "character": "constant, boring, crushing -- kept me up all night",
            "aggravating": "worse lying flat, a little better leaning forward; denies exertional pattern",
            "social_history": "drank heavily at a wedding this weekend, more than usual",
        },
        exam_results={"cardiac_auscultation": "normal heart sounds, no murmur",
                      "abdominal_exam": "epigastric tenderness with voluntary guarding",
                      "vital_signs": "BP 112/70, HR 104, RR 18, Temp 37.6, SpO2 97%"},
        test_results={"ecg": "normal sinus rhythm, no ST changes", "lipase": "markedly elevated"},
    ),
    SyntheticCase(
        case_id="Blind20_MigratingStoneMimicsAppendicitis", category="conflicting_findings",
        chief_complaint="pain moved from my back to my groin", demographics={"age": 36, "sex": "male"},
        ground_truth_diagnosis="nephrolithiasis",
        notes="Migrating pain pattern could sound like appendicitis at first glance, but the "
              "flank-to-groin trajectory, hematuria, and CT should clearly distinguish it -- a "
              "different framing from the existing 'something feels wrong in my side' stone case.",
        answers={
            "location": "started in my right flank, now radiates down into my groin",
            "character": "comes in waves, sharp, can't find a comfortable position",
            "associated_symptoms": "some pink-tinged urine; denies fever, denies vomiting",
            "family_history": "brother has had kidney stones twice",
        },
        exam_results={"costovertebral_tenderness": "positive right-sided", "abdominal_exam": "soft, no rebound, no guarding",
                      "vital_signs": "BP 136/84, HR 96, RR 16, Temp 36.9, SpO2 98%"},
        test_results={"urinalysis": "gross and microscopic hematuria", "ct_abdomen": "6mm right ureterovesical junction stone"},
    ),
    SyntheticCase(
        case_id="Blind21_YoungPanicAttack", category="common",
        chief_complaint="my heart is racing and I can't catch my breath, I think I'm dying", demographics={"age": 24, "sex": "female"},
        ground_truth_diagnosis="panic_attack",
        answers={
            "onset": "sudden, about fifteen minutes ago, out of nowhere while studying",
            "associated_symptoms": "tingling in my fingers, chest feels tight, dizzy, this has "
                                    "happened before during finals week; denies leg swelling",
            "past_medical_history": "anxiety diagnosed two years ago",
            "social_history": "big exam tomorrow, hasn't slept much this week",
        },
        exam_results={"cardiac_auscultation": "normal heart sounds, no murmur",
                      "lung_auscultation": "clear bilaterally",
                      "vital_signs": "BP 128/80, HR 118, RR 24, Temp 36.9, SpO2 99%"},
        test_results={"ecg": "sinus tachycardia, otherwise normal", "troponin": "within normal limits"},
    ),
    SyntheticCase(
        case_id="Blind22_KnownSVTPalpitations", category="common",
        chief_complaint="my heart suddenly started racing really fast", demographics={"age": 33, "sex": "female"},
        ground_truth_diagnosis="cardiac_arrhythmia",
        answers={
            "onset": "came on suddenly about half an hour ago while climbing stairs",
            "associated_symptoms": "just the racing feeling, a little lightheaded; denies chest "
                                    "pain, denies fainting",
            "past_medical_history": "diagnosed with SVT a few years ago, this feels exactly the same as before",
            "duration": "usually lasts until it suddenly stops on its own",
        },
        exam_results={"cardiac_auscultation": "rapid, regular rhythm", "vital_signs": "BP 110/70, HR 176 regular, RR 18, Temp 36.8, SpO2 98%"},
        test_results={"ecg": "narrow complex tachycardia at 176 bpm, consistent with SVT"},
    ),
    SyntheticCase(
        case_id="Blind23_PostSurgicalBowelObstruction", category="dangerous",
        chief_complaint="my belly is swollen and I haven't been able to go to the bathroom", demographics={"age": 67, "sex": "female"},
        ground_truth_diagnosis="acute_abdomen",
        notes="Adhesion-related bowel obstruction from a prior surgery, a distinct mechanism from "
              "the existing gallbladder-removal perforated-viscus acute-abdomen case.",
        answers={
            "onset": "gradually over the last two days, progressively worse",
            "associated_symptoms": "no bowel movement or gas in two days, vomiting green fluid; "
                                    "belly keeps getting more swollen",
            "past_medical_history": "had a hysterectomy eight years ago",
        },
        exam_results={"abdominal_exam": "distended, diffusely tender, high-pitched bowel sounds early then absent",
                      "vital_signs": "BP 106/64, HR 112, RR 20, Temp 37.8, SpO2 96%"},
        test_results={"cbc": "elevated white blood cell count", "ct_abdomen": "dilated small bowel loops with a transition point, adhesive obstruction"},
    ),
    SyntheticCase(
        case_id="Blind24_ClassicCystitis", category="common",
        chief_complaint="it burns every time I pee", demographics={"age": 26, "sex": "female"},
        ground_truth_diagnosis="uncomplicated_cystitis",
        answers={
            "onset": "started yesterday, getting more uncomfortable",
            "associated_symptoms": "going more often than usual, feels like I can't fully empty; "
                                    "denies fever, denies back pain",
            "past_medical_history": "had a bladder infection once before in college",
        },
        exam_results={"abdominal_exam": "mild suprapubic tenderness, no costovertebral tenderness",
                      "vital_signs": "BP 114/72, HR 78, RR 14, Temp 36.9, SpO2 99%"},
        test_results={"urinalysis": "positive leukocyte esterase, positive nitrites"},
    ),
    SyntheticCase(
        case_id="Blind25_HeartburnGERD", category="common",
        chief_complaint="burning feeling behind my breastbone after I eat", demographics={"age": 44, "sex": "male"},
        ground_truth_diagnosis="gerd",
        answers={
            "onset": "off and on for a few months, worse the last week",
            "aggravating": "worse lying down after big meals, worse with spicy food and coffee; "
                           "antacids help within minutes",
            "character": "burning, not a pressure or squeezing sensation",
            "past_medical_history": "none",
            "social_history": "drinks coffee daily, eats late at night often",
        },
        exam_results={"cardiac_auscultation": "normal heart sounds, no murmur",
                      "abdominal_exam": "soft, mild epigastric tenderness",
                      "vital_signs": "BP 122/78, HR 74, RR 14, Temp 36.8, SpO2 99%"},
        test_results={"ecg": "normal sinus rhythm, no ST changes"},
    ),
    SyntheticCase(
        case_id="Blind26_SmokerBronchitis", category="common_elderly",
        chief_complaint="I can't shake this cough", demographics={"age": 68, "sex": "male"},
        ground_truth_diagnosis="acute_bronchitis",
        notes="Elderly long-time smoker with a benign self-limited bronchitis -- tests the agent "
              "doesn't over-call pneumonia/malignancy just because of age and smoking history when "
              "the exam and imaging are reassuring.",
        answers={
            "duration": "about ten days, started after a cold, slowly improving",
            "associated_symptoms": "coughing up some clear-to-white mucus, chest feels raw from "
                                    "coughing; denies high fever, denies weight loss, denies coughing up blood",
            "social_history": "smoked a pack a day for forty years",
        },
        exam_results={"lung_auscultation": "scattered rhonchi, clears with cough, no focal crackles",
                      "vital_signs": "BP 130/80, HR 84, RR 18, Temp 37.2, SpO2 96%"},
        test_results={"cxr": "no focal consolidation, chronic changes only"},
    ),
    SyntheticCase(
        case_id="Blind27_TensionHeadacheStress", category="negative_finding_centric",
        chief_complaint="tight band-like headache the last few days", demographics={"age": 37, "sex": "female"},
        ground_truth_diagnosis="tension_headache",
        answers={
            "character": "feels like a tight band squeezing around my whole head, not throbbing, not one-sided",
            "location": "both sides, more toward the back of my head and neck",
            "aggravating": "worse with stress and after long hours at the computer; denies visual "
                           "changes, denies nausea, denies sensitivity to light",
            "social_history": "big work deadline this week, barely sleeping",
        },
        exam_results={"neuro_exam": "no focal neurological deficit", "vital_signs": "BP 118/76, HR 72, RR 14, Temp 36.7, SpO2 99%"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind28_NursingHomeHyponatremia", category="elderly",
        chief_complaint="grandpa has seemed more tired and mixed up lately", demographics={"age": 88, "sex": "male"},
        ground_truth_diagnosis="severe_electrolyte_disorder",
        notes="Poor oral intake in a nursing-home resident driving hyponatremia -- a different "
              "electrolyte-disorder mechanism from the hyperkalemia cases elsewhere in this suite.",
        answers={
            "onset": "family says it's been getting worse over about a week",
            "associated_symptoms": "hasn't been drinking much water, seems drowsy and a bit "
                                    "confused; denies fever, denies vomiting",
            "past_medical_history": "mild heart failure, on a water pill",
            "medication": "furosemide",
        },
        exam_results={"mental_status_exam": "drowsy, oriented to person only", "vital_signs": "BP 104/62, HR 88, RR 16, Temp 36.5, SpO2 97%"},
        test_results={"bmp": "sodium 118, consistent with severe hyponatremia"},
    ),
    SyntheticCase(
        case_id="Blind29_YoungFemaleVasovagal", category="common",
        chief_complaint="I fainted after getting a shot at the pharmacy", demographics={"age": 22, "sex": "female"},
        ground_truth_diagnosis="vasovagal_syncope",
        answers={
            "onset": "right after the flu shot this morning",
            "aggravating": "felt hot and queasy right before, vision tunneled, then went down; "
                           "woke up within seconds feeling okay",
            "associated_symptoms": "denies chest pain, denies palpitations beforehand, denies tongue biting or incontinence",
            "past_medical_history": "always gets lightheaded around needles",
        },
        exam_results={"cardiac_auscultation": "normal heart sounds, no murmur", "vital_signs": "BP 106/66, HR 62, RR 14, Temp 36.7, SpO2 99%"},
        test_results={"ecg": "normal sinus rhythm"},
    ),
    SyntheticCase(
        case_id="Blind30_NewOnsetTeenDKA", category="dangerous",
        chief_complaint="I've been so thirsty and tired for weeks, and now I feel awful", demographics={"age": 15, "sex": "female"},
        ground_truth_diagnosis="diabetic_ketoacidosis",
        notes="New-onset, previously-undiagnosed diabetes in a teenager (not a known-diabetic "
              "missed-insulin-dose framing like the existing DKA cases) -- the risk-factor signal "
              "has to come from the symptom pattern itself, not a stated diagnosis history.",
        answers={
            "onset": "the thirst and weight loss have built up over about a month; today she's "
                     "vomiting and breathing weird",
            "associated_symptoms": "drinking huge amounts of water, peeing constantly, lost weight "
                                    "without trying, now nauseous and vomiting, breathing fast and deep",
            "past_medical_history": "none known, never diagnosed with diabetes before",
        },
        exam_results={"mental_status_exam": "drowsy but arousable", "abdominal_exam": "diffuse mild tenderness",
                      "vital_signs": "BP 100/60, HR 118, RR 32 deep, Temp 37.0, SpO2 98%"},
        test_results={"glucose_point_of_care": "612 mg/dL", "ketones": "large ketones present", "abg": "pH 7.1, metabolic acidosis"},
    ),
    SyntheticCase(
        case_id="Blind31_PollenAsthmaExacerbation", category="common",
        chief_complaint="I've been wheezing all afternoon since I mowed the lawn", demographics={"age": 26, "sex": "male"},
        ground_truth_diagnosis="asthma_copd_exacerbation",
        notes="Allergen (pollen/grass) trigger rather than the existing case's cold-air/exercise "
              "trigger -- a different precipitant for the same diagnosis.",
        answers={
            "onset": "started about two hours ago while mowing the lawn",
            "aggravating": "grass and pollen always set it off; usually the inhaler helps within minutes",
            "past_medical_history": "asthma since childhood, uses an albuterol inhaler as needed",
            "associated_symptoms": "tight chest and wheezing; denies fever, denies chest pain",
        },
        exam_results={"lung_auscultation": "bilateral expiratory wheeze",
                      "vital_signs": "BP 124/76, HR 100, RR 24, Temp 36.8, SpO2 95%"},
        test_results={"cxr": "hyperinflated lungs, no focal consolidation"},
    ),
    SyntheticCase(
        case_id="Blind32_ElderlyBPHUrosepsis", category="dangerous_elderly",
        chief_complaint="dad is burning up and can barely stand", demographics={"age": 77, "sex": "male"},
        ground_truth_diagnosis="sepsis",
        notes="Urinary-source sepsis in an elderly man with underlying BPH/urinary retention -- a "
              "different route to sepsis than the diabetic-urosepsis case already in the suite "
              "(here the risk factor is obstruction, not diabetes).",
        answers={
            "onset": "fever started overnight, weakness this morning, worse very quickly",
            "associated_symptoms": "trouble starting his stream for months, now burning with "
                                    "urination and shaking chills; confused compared to his normal self",
            "past_medical_history": "enlarged prostate, hasn't seen a urologist in years",
        },
        exam_results={"mental_status_exam": "confused, lethargic",
                      "vital_signs": "BP 82/50, HR 128, RR 26, Temp 39.6, SpO2 93%"},
        test_results={"urinalysis": "positive leukocyte esterase, positive nitrites", "lactate": "elevated",
                      "blood_culture": "pending", "cbc": "markedly elevated white blood cell count"},
    ),
]
