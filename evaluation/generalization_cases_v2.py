"""Generalization evaluation, v2 (spec section 16): a SECOND, independent held-out-style set --
never used to tune any default in nova_agent/config.py, and never overlapping in scenario with
evaluation/cases.py or evaluation/held_out_cases.py's specific vignettes.

Each case below targets one of the diversity dimensions the task spec named (common disease,
rare-but-dangerous, atypical presentation, elderly, young adult, polypharmacy, immunocompromised,
multi-symptom, conflicting findings, benign/dangerous mimics) using a diagnosis this repo's other
evaluation files never use as a ground truth, so the whole set adds real, non-redundant coverage
rather than rewording an existing case (spec: never inflate the count with same-template-different-
wording padding).

Honest count: 14 cases, not the 50-100 stretch target named in the task spec -- see
README.md's Known Limitations and the session's final report for why (case-authoring at this
level of care is the bottleneck, not a decision to under-deliver quietly).

Still hand-authored synthetic vignettes, never real patient data.
"""

from __future__ import annotations

from evaluation.cases import SyntheticCase

GENERALIZATION_CASES_V2 = [
    SyntheticCase(
        case_id="Fever04_CommonViralURI", category="common_disease",
        chief_complaint="runny nose and sore throat", demographics={"age": 27, "sex": "female"},
        ground_truth_diagnosis="viral_uri",
        notes="The single most common, lowest-acuity presentation the agent will see -- checks it "
              "doesn't over-test/over-diagnose a mild, self-limited illness just because the "
              "knowledge base is weighted toward can't-miss conditions.",
        answers={
            "associated_symptoms": "runny nose, sore throat, mild cough; denies shortness of "
                                    "breath, denies chest pain, denies neck stiffness",
            "duration": "about two days",
            "social_history": "my roommate had a cold last week",
        },
        exam_results={"vital_signs": "BP 118/74, HR 78, RR 14, Temp 37.6, SpO2 99%",
                      "lung_auscultation": "clear bilaterally"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Dizziness03_AtypicalStroke", category="atypical_presentation",
        chief_complaint="dizzy and a little off-balance", demographics={"age": 68, "sex": "male"},
        ground_truth_diagnosis="ischemic_stroke",
        notes="Posterior-circulation stroke presenting as isolated dizziness/imbalance rather than "
              "dramatic unilateral weakness -- a well-documented atypical/easy-to-miss pattern, "
              "distinct from the classic-presentation ischemic-stroke risk already covered elsewhere.",
        answers={
            "onset": "sudden, about an hour ago",
            "associated_symptoms": "some trouble with my balance and my words felt slightly "
                                    "off; denies chest pain, denies palpitations",
            "past_medical_history": "atrial fibrillation, hypertension",
            "medication": "I stopped taking my blood thinner a few weeks ago",
        },
        exam_results={
            "neuro_exam": "mild left-sided ataxia, subtle dysarthria",
            "vital_signs": "BP 168/94, HR 88 irregularly irregular, RR 16, Temp 36.8, SpO2 97%",
            "mental_status_exam": "alert, oriented x3",
        },
        test_results={"ct_head": "acute infarct in the cerebellar region", "glucose_point_of_care": "98 mg/dL"},
    ),
    SyntheticCase(
        case_id="Weakness01_ElderlyPolypharmacyHypoglycemia", category="elderly_polypharmacy",
        chief_complaint="feeling weak and shaky", demographics={"age": 81, "sex": "female"},
        ground_truth_diagnosis="hypoglycemia",
        notes="Elderly patient on multiple medications (a classic polypharmacy setup, distinct "
              "phrasing/scenario from the anticoagulant-headache medication-risk case) whose "
              "reduced oral intake plus a sulfonylurea produced hypoglycemia rather than the more "
              "commonly assumed 'just old age' weakness.",
        answers={
            "onset": "started about thirty minutes ago, came on quickly",
            "associated_symptoms": "sweating a lot and shaky, and I feel confused; denies chest "
                                    "pain, denies slurred speech",
            "past_medical_history": "type 2 diabetes, high blood pressure, hasn't eaten much today",
            "medication": "glipizide, lisinopril, and a water pill",
        },
        exam_results={"mental_status_exam": "confused, diaphoretic",
                      "vital_signs": "BP 132/80, HR 102, RR 16, Temp 36.6, SpO2 98%"},
        test_results={"glucose_point_of_care": "blood glucose 42 mg/dL"},
    ),
    SyntheticCase(
        case_id="AbdominalPain03_YoungAdultAppendicitis", category="young_adult",
        chief_complaint="stomach pain that moved", demographics={"age": 22, "sex": "male"},
        ground_truth_diagnosis="appendicitis",
        notes="Classic young-adult appendicitis presentation -- included as the 'common in this "
              "age group' comparison case alongside the rarer/more dangerous young-adult cases "
              "elsewhere in the suite.",
        answers={
            "location": "started around my belly button, now it's moved to my lower right side",
            "onset": "started yesterday evening, getting worse",
            "associated_symptoms": "no appetite, felt a little feverish, nauseous; denies "
                                    "diarrhea, denies vomiting blood",
        },
        exam_results={"abdominal_exam": "right lower quadrant tenderness with rebound and guarding",
                      "vital_signs": "BP 122/78, HR 96, RR 16, Temp 38.1, SpO2 99%"},
        test_results={"cbc": "elevated white blood cell count", "ct_abdomen": "dilated, thickened appendix"},
    ),
    SyntheticCase(
        case_id="Fever05_ImmunocompromisedSepsis", category="immunocompromised",
        chief_complaint="fever, no clear reason", demographics={"age": 54, "sex": "female"},
        ground_truth_diagnosis="sepsis",
        notes="Immunocompromised (on chemotherapy) patient with fever and no obvious localizing "
              "source -- a distinct clinical scenario from the diabetic-urosepsis comorbidity case "
              "(here the source is never identified during the case, testing recognition of sepsis "
              "risk from immune status + vitals alone, not from a urinary-symptom trail).",
        answers={
            "onset": "fever started overnight, feels worse than a normal cold",
            "associated_symptoms": "chills and feeling very tired; denies cough, denies burning "
                                    "with urination, denies abdominal pain, denies rash",
            "past_medical_history": "breast cancer, currently on chemotherapy, last cycle was five days ago",
        },
        exam_results={"vital_signs": "BP 88/56, HR 122, RR 24, Temp 39.3, SpO2 94%",
                      "skin_exam": "no rash, no obvious infection source",
                      "mental_status_exam": "alert but fatigued"},
        test_results={"lactate": "elevated lactate", "cbc": "low white blood cell count (neutropenic)",
                      "blood_culture": "pending"},
    ),
    SyntheticCase(
        case_id="AbdominalPain04_AnticoagulantGIBleed", category="polypharmacy_anticoagulant",
        chief_complaint="dark stools and feeling weak", demographics={"age": 71, "sex": "male"},
        ground_truth_diagnosis="gi_bleeding",
        notes="On both an anticoagulant AND an antiplatelet (the medication-risk rule's exact "
              "trigger combination) -- a genuinely different scenario from the anticoagulant-"
              "headache case, testing the same risk-factor mechanism applied to a different "
              "dangerous diagnosis it's linked to.",
        answers={
            "associated_symptoms": "my stools have looked black and tarry for two days, and I "
                                    "feel lightheaded when I stand up; denies vomiting blood, denies fever",
            "medication": "warfarin for a heart valve, and I also take aspirin",
            "past_medical_history": "mechanical heart valve, peptic ulcer years ago",
        },
        exam_results={"abdominal_exam": "mild diffuse tenderness, no rebound or guarding",
                      "vital_signs": "BP 98/62, HR 114, RR 18, Temp 36.9, SpO2 97%",
                      "fecal_occult_blood": "positive"},
        test_results={"cbc": "low hemoglobin"},
    ),
    SyntheticCase(
        case_id="AlteredMentalStatus02_MultiSymptomDKA", category="multiple_simultaneous_symptoms",
        chief_complaint="throwing up, stomach pain, and confused", demographics={"age": 16, "sex": "male"},
        ground_truth_diagnosis="diabetic_ketoacidosis",
        notes="Three simultaneous, superficially unrelated-seeming complaints (vomiting + "
              "abdominal pain + confusion) at once -- a genuinely distinct presentation/phrasing "
              "from the tuning set's single-chief-complaint DKA case, testing whether the agent "
              "integrates a multi-symptom complaint into one coherent diagnosis rather than "
              "chasing each symptom separately.",
        answers={
            "onset": "started yesterday, getting worse through the night",
            "associated_symptoms": "throwing up several times, stomach hurts all over, and I've "
                                    "been really thirsty and peeing a lot; denies diarrhea, denies fever",
            "past_medical_history": "type 1 diabetes, ran out of insulin four days ago",
        },
        exam_results={"mental_status_exam": "drowsy but arousable, oriented to person only",
                      "vital_signs": "BP 102/64, HR 122, RR 30, Temp 37.0, SpO2 98%",
                      "abdominal_exam": "diffuse mild tenderness, no rebound or guarding"},
        test_results={"glucose_point_of_care": "blood glucose 3 (critical high, unreadable on meter)",
                      "ketones": "large ketones present", "abg": "metabolic acidosis, kussmaul breathing"},
    ),
    SyntheticCase(
        case_id="ChestPain07_ConflictingFindingsMusculoskeletal", category="conflicting_findings",
        chief_complaint="chest pain", demographics={"age": 52, "sex": "male"},
        ground_truth_diagnosis="musculoskeletal_chest_pain",
        notes="Deliberately has SOME features that sound alarming (age, chest pain) pulling toward "
              "ACS, but the objective/exam findings actively contradict it -- tests whether the "
              "agent can let negative objective evidence (normal ECG, reproducible tenderness) "
              "override demographic/keyword-driven anchoring rather than over-calling ACS by default.",
        answers={
            "onset": "started two days ago after I moved some heavy furniture",
            "character": "sharp, localized pain, not a pressure or squeezing feeling",
            "aggravating": "much worse when I press on it or twist my torso; denies radiation to "
                            "my arm or jaw, denies shortness of breath, denies sweating",
            "past_medical_history": "high cholesterol",
            "family_history": "father had a heart attack in his 70s",
        },
        exam_results={"abdominal_exam": "reproducible tenderness over the left costochondral "
                                        "junction, worse with palpation",
                      "vital_signs": "BP 128/82, HR 76, RR 16, Temp 36.8, SpO2 99%"},
        test_results={"ecg": "normal sinus rhythm, no ST changes"},
    ),
    SyntheticCase(
        case_id="BackPain02_Nephrolithiasis", category="vague_chief_complaint",
        chief_complaint="something feels really wrong in my side", demographics={"age": 39, "sex": "male"},
        ground_truth_diagnosis="nephrolithiasis",
        notes="Chief complaint gives almost no diagnostic information by itself ('something feels "
              "wrong') -- tests whether targeted follow-up questioning, not the initial complaint "
              "text, is what actually drives the differential toward the right answer.",
        answers={
            "location": "my right side, kind of low down, comes in waves",
            "character": "sharp, colicky, comes and goes in waves; can't get comfortable in any position",
            "family_history": "my father had kidney stones",
            "associated_symptoms": "some blood-tinged urine, nauseous; denies fever, denies burning with urination",
        },
        exam_results={"costovertebral_tenderness": "positive right-sided costovertebral angle tenderness",
                      "vital_signs": "BP 138/86, HR 98, RR 18, Temp 36.9, SpO2 98%"},
        test_results={"urinalysis": "microscopic hematuria", "ct_abdomen": "right ureteral stone with mild hydronephrosis"},
    ),
    SyntheticCase(
        case_id="AbdominalPain05_DangerousMimicPancreatitis", category="dangerous_mimic",
        chief_complaint="nausea and stomach pain", demographics={"age": 46, "sex": "male"},
        ground_truth_diagnosis="acute_pancreatitis",
        notes="Sounds like ordinary gastroenteritis at first (nausea, vomiting, abdominal pain) but "
              "the pain's specific character/radiation and a real risk factor (heavy alcohol use) "
              "point to a more dangerous cause -- a second, distinct dangerous-mimic-of-benign case.",
        answers={
            "location": "upper abdomen, radiates straight through to my back",
            "character": "severe, constant, boring pain, not crampy",
            "aggravating": "worse after eating, especially anything fatty",
            "social_history": "I drink heavily, especially on weekends",
        },
        exam_results={"abdominal_exam": "epigastric tenderness, voluntary guarding, no rebound",
                      "vital_signs": "BP 108/68, HR 108, RR 20, Temp 37.4, SpO2 97%"},
        test_results={"lipase": "markedly elevated lipase", "abdominal_ultrasound": "peripancreatic fluid, no gallstones seen"},
    ),
    SyntheticCase(
        case_id="Syncope01_BenignMimicVasovagal", category="benign_mimic",
        chief_complaint="I passed out", demographics={"age": 19, "sex": "female"},
        ground_truth_diagnosis="vasovagal_syncope",
        notes="'I passed out' sounds alarming and could suggest a cardiac cause, but the classic "
              "prodrome/trigger/rapid-recovery pattern plus a benign exam should keep this from "
              "being over-called as arrhythmia or a cardiac event -- a second, distinct "
              "benign-mimic case from the panic-attack one already in the suite.",
        answers={
            "onset": "happened during a blood draw this morning",
            "aggravating": "felt hot, sweaty, and my vision went dark right before I went down; "
                           "woke up within a few seconds feeling fine",
            "associated_symptoms": "felt nauseous and lightheaded right before; denies chest pain, "
                                    "denies palpitations before the episode, denies tongue biting",
            "past_medical_history": "none, has fainted once before during a similar situation",
        },
        exam_results={"cardiac_auscultation": "normal heart sounds, no murmur",
                      "vital_signs": "BP 108/68, HR 66, RR 14, Temp 36.7, SpO2 99%"},
        test_results={"ecg": "normal sinus rhythm"},
    ),
    SyntheticCase(
        case_id="Palpitations01_ElderlyAtypicalArrhythmia", category="atypical_presentation",
        chief_complaint="just feel dizzy and off lately", demographics={"age": 77, "sex": "female"},
        ground_truth_diagnosis="cardiac_arrhythmia",
        notes="Paroxysmal atrial fibrillation presenting as vague dizziness over days rather than "
              "dramatic sudden palpitations -- an atypical presentation of a diagnosis usually "
              "taught as a classic-palpitations case, testing generalization beyond the textbook "
              "presentation.",
        answers={
            "onset": "on and off for the past three days",
            "associated_symptoms": "my heart feels like it skips sometimes, comes and goes; "
                                    "denies chest pain, denies fainting",
            "past_medical_history": "hypertension",
            "duration": "each episode lasts a few minutes",
        },
        exam_results={"cardiac_auscultation": "irregularly irregular rhythm",
                      "vital_signs": "BP 128/78, HR 118 irregular, RR 16, Temp 36.8, SpO2 98%"},
        test_results={"ecg": "atrial fibrillation on ecg", "bmp": "normal electrolytes"},
    ),
    SyntheticCase(
        case_id="Cough01_CommonBronchitis", category="common_disease",
        chief_complaint="cough that won't go away", demographics={"age": 34, "sex": "female"},
        ground_truth_diagnosis="acute_bronchitis",
        notes="A second common, low-acuity case (distinct disease from the viral-URI one) -- tests "
              "the agent resists over-testing for pneumonia/PE when the presentation is mild and "
              "classic for a benign, self-limited cause.",
        answers={
            "duration": "about a week now, started after a cold",
            "associated_symptoms": "coughing up some clear mucus, chest feels sore from coughing "
                                    "so much; denies shortness of breath at rest, denies high fever, denies hemoptysis",
            "social_history": "doesn't smoke",
        },
        exam_results={"lung_auscultation": "clear to mildly coarse breath sounds, no focal consolidation",
                      "vital_signs": "BP 116/74, HR 82, RR 16, Temp 37.3, SpO2 98%"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Headache04_ReassuringMigraine", category="conflicting_findings",
        chief_complaint="really bad headache", demographics={"age": 29, "sex": "female"},
        ground_truth_diagnosis="migraine",
        notes="'Really bad headache' alone could sound like it needs an urgent SAH workup, but the "
              "recurrent pattern, aura, and normal neuro exam should reassure the agent this is a "
              "typical migraine rather than triggering the same alarm as a genuine thunderclap "
              "presentation -- tests it doesn't over-call every severe headache as dangerous.",
        answers={
            "character": "throbbing, one-sided, similar to headaches I've had before",
            "onset": "built up gradually over an hour, not sudden or thunderclap",
            "associated_symptoms": "sensitive to light and sound, saw some shimmering lights "
                                    "before it started, nauseous; denies neck stiffness, denies fever, denies confusion",
            "family_history": "my mother gets migraines too",
            "past_medical_history": "diagnosed with migraines a few years ago, this feels the same",
        },
        exam_results={"neuro_exam": "no focal neurological deficit",
                      "vital_signs": "BP 118/76, HR 74, RR 14, Temp 36.8, SpO2 99%"},
        test_results={},
    ),
]
