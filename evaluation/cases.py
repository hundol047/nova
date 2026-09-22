"""Synthetic / mock evaluation cases (spec section 17). NOT real patient data -- hand-authored
vignettes for local competition-development benchmarking only, one per required chief-complaint
category, with a mix of dangerous and benign ground truths so accuracy/critical-miss/duplicate
metrics are all meaningfully exercised.
"""

from __future__ import annotations

from typing import Dict

from pydantic import BaseModel, Field

from nova_agent.knowledge.retrieval import critical_condition_ids


class SyntheticCase(BaseModel):
    case_id: str
    chief_complaint: str
    demographics: Dict[str, object]
    ground_truth_diagnosis: str
    answers: Dict[str, str] = Field(default_factory=dict)
    exam_results: Dict[str, str] = Field(default_factory=dict)
    test_results: Dict[str, str] = Field(default_factory=dict)
    default_answer: str = "No, I don't have that."
    default_exam_result: str = "Unremarkable, within normal limits."
    default_test_result: str = "Normal / negative."
    # Reporting/breakdown only -- never read by the agent. "standard" = the original 8 cases this
    # repo's config defaults were tuned against; every other category lives in
    # evaluation/held_out_cases.py and was never used to shape a default (spec section 19/22).
    category: str = "standard"
    notes: str = ""
    # False only for genuinely ambiguous/insufficient-information cases where no single diagnosis
    # is clearly "the" right answer -- excluded from the accuracy denominator but still checked for
    # safety/crash/turn-limit behavior (spec section 19's "ambiguous case" / "insufficient
    # information case").
    scoring_expected: bool = True

    @property
    def critical(self) -> bool:
        return self.ground_truth_diagnosis in critical_condition_ids()


CASES = [
    SyntheticCase(
        case_id="ChestPain01", chief_complaint="chest pain", demographics={"age": 58, "sex": "male"},
        ground_truth_diagnosis="acute_coronary_syndrome",
        answers={
            "onset": "started suddenly about 1 hour ago",
            "character": "substernal pressure, like someone sitting on my chest",
            "aggravating": "worse with exertion; denies tearing or ripping pain",
            "relieving": "somewhat better with rest",
            "associated_symptoms": "diaphoresis, nausea, and pain radiates to the left arm and jaw; "
                                    "denies calf swelling, denies hemoptysis, denies unilateral leg pain",
            "past_medical_history": "hypertension, diabetes, hyperlipidemia",
            "family_history": "father had a heart attack at 55",
            "social_history": "smokes one pack per day",
        },
        exam_results={
            "vital_signs": "BP 150/95, HR 105, RR 20, Temp 37.0, SpO2 97%",
            "cardiac_auscultation": "normal heart sounds, no murmur",
            "general_appearance": "diaphoretic, appears uncomfortable",
        },
        test_results={
            "ecg": "ST elevation in anterior leads",
            "troponin": "elevated troponin",
            "cxr": "no widened mediastinum, no pneumothorax",
        },
    ),
    SyntheticCase(
        case_id="AbdominalPain01", chief_complaint="abdominal pain", demographics={"age": 28, "sex": "female"},
        ground_truth_diagnosis="ectopic_pregnancy",
        answers={
            "onset": "sudden onset lower abdominal pain 3 hours ago",
            "location": "lower abdominal pain, more on one side, unilateral pelvic pain",
            "character": "sharp pain",
            "associated_symptoms": "vaginal bleeding and my period is late, missed period; also feeling dizzy; "
                                    "denies fever, denies rebound tenderness or guarding, denies vomiting bile",
            "past_medical_history": "prior pelvic inflammatory disease, had an IUD placed previously",
        },
        exam_results={
            "vital_signs": "BP 90/60, HR 118, RR 18, Temp 36.8, SpO2 99%",
            "pelvic_exam": "unilateral adnexal tenderness",
            "abdominal_exam": "mild lower abdominal tenderness, no rebound or guarding",
        },
        test_results={
            "beta_hcg": "positive beta-hCG",
            "pelvic_ultrasound": "no intrauterine pregnancy seen, free fluid in pelvis, adnexal mass",
        },
    ),
    SyntheticCase(
        case_id="Headache01", chief_complaint="headache", demographics={"age": 45, "sex": "female"},
        ground_truth_diagnosis="subarachnoid_hemorrhage",
        answers={
            "onset": "sudden onset, thunderclap, worst headache of my life",
            "character": "severe, thunderclap quality",
            "severity": "10 out of 10, worst headache of my life",
            "associated_symptoms": "neck stiffness, photophobia, and vomiting; "
                                    "denies fever, denies focal weakness or slurred speech",
            "past_medical_history": "hypertension",
            "family_history": "family history of brain aneurysm",
            "social_history": "smokes",
        },
        exam_results={
            "meningeal_signs": "positive neck stiffness, positive Kernig sign",
            "neuro_exam": "no focal neurological deficit",
            "vital_signs": "BP 165/100, HR 88, RR 16, Temp 36.9, SpO2 98%",
        },
        test_results={"ct_head": "subarachnoid blood seen on non-contrast CT"},
    ),
    SyntheticCase(
        case_id="Fever01", chief_complaint="fever", demographics={"age": 22, "sex": "male"},
        ground_truth_diagnosis="meningitis",
        answers={
            "onset": "started yesterday, fever and headache",
            "associated_symptoms": "neck stiffness, photophobia, and confusion; "
                                    "denies thunderclap or worst headache of life, denies focal weakness",
            "past_medical_history": "no chronic illnesses",
            "social_history": "college dormitory, close contact with a sick roommate",
        },
        exam_results={
            "meningeal_signs": "positive neck stiffness, positive Brudzinski sign",
            "skin_exam": "petechial rash on the trunk",
            "vital_signs": "BP 100/65, HR 122, RR 22, Temp 39.5, SpO2 96%",
            "mental_status_exam": "mildly confused, oriented to person only",
        },
        test_results={
            "lumbar_puncture": "CSF pleocytosis with elevated protein and low glucose",
            "blood_culture": "gram-negative diplococci on gram stain",
            "cbc": "elevated white blood cell count",
        },
    ),
    SyntheticCase(
        case_id="Dyspnea01", chief_complaint="shortness of breath", demographics={"age": 50, "sex": "female"},
        ground_truth_diagnosis="pulmonary_embolism",
        answers={
            "onset": "sudden onset shortness of breath 30 minutes ago",
            "character": "pleuritic chest pain, sharp pain worse with breathing",
            "associated_symptoms": "unilateral leg pain and calf swelling; "
                                    "denies wheeze, denies fever, denies absent breath sounds",
            "past_medical_history": "recent long haul flight, recent surgery on the leg",
            "medication": "oral contraceptive pills",
        },
        exam_results={
            "vital_signs": "BP 110/70, HR 128, RR 26, Temp 37.1, SpO2 89%",
            "extremity_exam": "right calf swelling and tenderness",
            "lung_auscultation": "clear breath sounds bilaterally",
        },
        test_results={
            "d_dimer": "elevated D-dimer",
            "ct_chest_angio": "filling defect in the right pulmonary artery consistent with pulmonary embolism",
            "ecg": "sinus tachycardia, no ST elevation",
        },
    ),
    SyntheticCase(
        case_id="Dizziness01", chief_complaint="dizziness", demographics={"age": 65, "sex": "female"},
        ground_truth_diagnosis="bppv",
        answers={
            "onset": "brief episodes for the past week",
            "duration": "each episode lasts less than a minute",
            "aggravating": "triggered by turning my head or rolling over in bed",
            "associated_symptoms": "denies focal weakness, denies slurred speech, denies hearing loss, "
                                    "denies severe headache",
            "past_medical_history": "no chronic illnesses",
        },
        exam_results={
            "neuro_exam": "no focal neurological deficit",
            "vital_signs": "BP 130/80, HR 76, RR 16, Temp 36.8, SpO2 98%",
        },
    ),
    SyntheticCase(
        case_id="AlteredMentalStatus01", chief_complaint="confusion", demographics={"age": 19, "sex": "female"},
        ground_truth_diagnosis="diabetic_ketoacidosis",
        answers={
            "onset": "over the past day, increasingly confused",
            "associated_symptoms": "polyuria, polydipsia, nausea and vomiting, abdominal pain; "
                                    "denies focal weakness, denies neck stiffness, denies fever",
            "past_medical_history": "type 1 diabetes",
            "medication": "ran out of insulin three days ago",
        },
        exam_results={
            "mental_status_exam": "confused, oriented to person only",
            "vital_signs": "BP 100/65, HR 118, RR 28, Temp 37.0, SpO2 98%",
            "abdominal_exam": "mild diffuse tenderness, no rebound or guarding",
        },
        test_results={
            "glucose_point_of_care": "blood glucose 450 mg/dL",
            "ketones": "large ketones present",
            "abg": "metabolic acidosis with kussmaul breathing, pH 7.15",
        },
    ),
    SyntheticCase(
        case_id="UrinarySymptoms01", chief_complaint="painful urination", demographics={"age": 30, "sex": "female"},
        ground_truth_diagnosis="uncomplicated_cystitis",
        answers={
            "onset": "started 2 days ago",
            "associated_symptoms": "dysuria, urinary frequency and urgency; "
                                    "denies fever, denies flank pain, denies nausea or vomiting",
            "past_medical_history": "prior urinary tract infection last year",
        },
        exam_results={
            "abdominal_exam": "mild suprapubic tenderness",
            "vital_signs": "BP 118/76, HR 82, RR 16, Temp 36.9, SpO2 99%",
            "costovertebral_tenderness": "no costovertebral angle tenderness",
        },
        test_results={"urinalysis": "positive leukocyte esterase and nitrites"},
    ),
]
