"""Fixed catalogs of history-taking questions, physical exams, and diagnostic tests.

Actions the agent proposes are drawn from these catalogs rather than free LLM text. This is what
makes duplicate detection deterministic (state.py checks catalog ids, not fuzzy text similarity)
and what makes turn-cost / redundancy scoring possible in action_selector.py. Each catalog entry
also carries bilingual (ko/en) keyword lists so free-text content (e.g. from an LLM-authored
question, or a competition observation echoing back what was asked) can still be mapped onto the
same canonical id -- this is what satisfies the "same-meaning paraphrase -> same normalized key"
requirement even when the exact wording differs.
"""

from __future__ import annotations

from typing import Dict, List, TypedDict


class QuestionSpec(TypedDict):
    category: str
    text_en: str
    text_ko: str
    keywords: List[str]
    turn_cost: int


class ProcedureSpec(TypedDict):
    id: str
    name_en: str
    name_ko: str
    keywords: List[str]
    turn_cost: int
    kind: str  # 'exam' | 'lab' | 'imaging'


# --- ASK catalog -----------------------------------------------------------------------------
# Core history-taking dimensions (section 8). "disease-specific" questions are added dynamically
# by differential.py/action_selector.py from each disease's `discriminating_questions` in the
# knowledge base, reusing the same QuestionSpec shape via `disease_specific_question()`.
QUESTION_CATALOG: Dict[str, QuestionSpec] = {
    "onset": {
        "category": "onset", "text_en": "When did the symptoms start?",
        "text_ko": "증상이 언제부터 시작되었습니까?",
        "keywords": ["onset", "when did", "start", "began", "언제", "부터", "시작"],
        "turn_cost": 1,
    },
    "location": {
        "category": "location", "text_en": "Where exactly do you feel it?",
        "text_ko": "정확히 어느 부위가 불편하십니까?",
        "keywords": ["where", "location", "site", "어디", "부위", "위치"],
        "turn_cost": 1,
    },
    "duration": {
        "category": "duration", "text_en": "How long does each episode last?",
        "text_ko": "증상이 얼마나 지속됩니까?",
        "keywords": ["how long", "duration", "lasting", "지속", "얼마나"],
        "turn_cost": 1,
    },
    "character": {
        "category": "character", "text_en": "How would you describe the quality of the symptom (sharp, dull, pressure, burning)?",
        "text_ko": "증상의 양상은 어떻습니까 (날카로운, 둔한, 압박감, 화끈거림 등)?",
        "keywords": ["describe", "quality", "character", "sharp", "dull", "pressure", "burning", "양상", "느낌"],
        "turn_cost": 1,
    },
    "severity": {
        "category": "severity", "text_en": "On a scale of 0 to 10, how severe is it?",
        "text_ko": "0에서 10점 중 통증/불편감의 정도는 어느 정도입니까?",
        "keywords": ["severity", "scale", "how bad", "severe", "강도", "정도", "심한"],
        "turn_cost": 1,
    },
    "aggravating": {
        "category": "aggravating", "text_en": "What makes it worse (exertion, movement, eating, breathing)?",
        "text_ko": "무엇을 할 때 악화됩니까 (운동, 움직임, 식사, 호흡 등)?",
        "keywords": ["worse", "aggravat", "trigger", "exertion", "악화", "심해"],
        "turn_cost": 1,
    },
    "relieving": {
        "category": "relieving", "text_en": "What makes it better (rest, medication, position)?",
        "text_ko": "무엇을 하면 호전됩니까 (휴식, 약물, 자세 등)?",
        "keywords": ["better", "reliev", "improve", "rest helps", "완화", "호전"],
        "turn_cost": 1,
    },
    "associated_symptoms": {
        "category": "associated_symptoms", "text_en": "Are there any other symptoms occurring alongside this?",
        "text_ko": "동반되는 다른 증상이 있습니까?",
        "keywords": ["associated", "other symptoms", "along with", "동반", "같이"],
        "turn_cost": 1,
    },
    "past_medical_history": {
        "category": "past_medical_history", "text_en": "Do you have any chronic illnesses or past major medical history?",
        "text_ko": "과거 병력이나 만성질환이 있습니까?",
        "keywords": ["past medical history", "chronic", "pmh", "history of", "병력", "기저질환"],
        "turn_cost": 1,
    },
    "medication": {
        "category": "medication", "text_en": "What medications are you currently taking?",
        "text_ko": "현재 복용 중인 약물이 있습니까?",
        "keywords": ["medication", "drugs", "taking any", "복용", "약물"],
        "turn_cost": 1,
    },
    "allergy": {
        "category": "allergy", "text_en": "Do you have any known drug or food allergies?",
        "text_ko": "알려진 약물 또는 음식 알레르기가 있습니까?",
        "keywords": ["allergy", "allergic", "알레르기"],
        "turn_cost": 1,
    },
    "family_history": {
        "category": "family_history", "text_en": "Is there a relevant family history of this kind of illness?",
        "text_ko": "관련된 가족력이 있습니까?",
        "keywords": ["family history", "runs in the family", "가족력"],
        "turn_cost": 1,
    },
    "social_history": {
        "category": "social_history", "text_en": "Do you smoke, drink alcohol, or use any recreational drugs?",
        "text_ko": "흡연, 음주 또는 기타 약물 사용력이 있습니까?",
        "keywords": ["smoke", "alcohol", "social history", "occupation", "흡연", "음주", "직업"],
        "turn_cost": 1,
    },
}


def disease_specific_question(disease_id: str, discriminator: str) -> QuestionSpec:
    """Build a QuestionSpec for a disease-specific discriminating item declared in the knowledge
    base (e.g. "associated_symptoms:diaphoresis" -> a targeted yes/no question). Falls back to the
    base catalog entry when the discriminator is already a known category with no sub-detail."""
    if ":" in discriminator:
        category, detail = discriminator.split(":", 1)
    else:
        category, detail = discriminator, None
    base = QUESTION_CATALOG.get(category)
    if detail is None and base is not None:
        return base
    detail_label = detail or category
    return {
        "category": category,
        "text_en": f"Do you have {detail_label.replace('_', ' ')}?",
        "text_ko": f"{detail_label} 증상이 있습니까?",
        "keywords": [detail_label.replace("_", " "), detail_label, category],
        "turn_cost": 1,
    }


def question_key(disease_id: str, discriminator: str) -> str:
    """Stable catalog key for a (possibly disease-specific) question, used as the dedup key."""
    return f"ask:{discriminator}"


# --- EXAM catalog (physical examination maneuvers) -------------------------------------------
EXAM_CATALOG: Dict[str, ProcedureSpec] = {
    "vital_signs": {"id": "vital_signs", "name_en": "Vital signs (BP/HR/RR/Temp/SpO2)", "name_ko": "활력징후 측정",
                     "keywords": ["vital", "blood pressure", "heart rate", "활력징후"], "turn_cost": 1, "kind": "exam"},
    "general_appearance": {"id": "general_appearance", "name_en": "General appearance / distress level",
                            "name_ko": "전반적 외관 및 고통 정도", "keywords": ["general appearance", "distress", "외관"],
                            "turn_cost": 1, "kind": "exam"},
    "cardiac_auscultation": {"id": "cardiac_auscultation", "name_en": "Cardiac auscultation", "name_ko": "심음 청진",
                              "keywords": ["heart sounds", "murmur", "cardiac auscultation", "심음"], "turn_cost": 1, "kind": "exam"},
    "lung_auscultation": {"id": "lung_auscultation", "name_en": "Lung auscultation", "name_ko": "폐 청진",
                           "keywords": ["breath sounds", "wheeze", "crackles", "lung auscultation", "호흡음"], "turn_cost": 1, "kind": "exam"},
    "abdominal_exam": {"id": "abdominal_exam", "name_en": "Abdominal palpation / peritoneal signs",
                        "name_ko": "복부 촉진 및 복막자극징후", "keywords": ["abdomen", "rebound", "guarding", "복부"],
                        "turn_cost": 1, "kind": "exam"},
    "neuro_exam": {"id": "neuro_exam", "name_en": "Focal neurological exam", "name_ko": "국소 신경학적 검진",
                   "keywords": ["neuro exam", "focal deficit", "cranial nerve", "신경학적"], "turn_cost": 1, "kind": "exam"},
    "meningeal_signs": {"id": "meningeal_signs", "name_en": "Meningeal signs (neck stiffness, Kernig/Brudzinski)",
                         "name_ko": "수막자극징후 (경부강직, Kernig/Brudzinski)",
                         "keywords": ["neck stiffness", "kernig", "brudzinski", "meningeal", "경부강직"], "turn_cost": 1, "kind": "exam"},
    "skin_exam": {"id": "skin_exam", "name_en": "Skin exam (rash, cyanosis, diaphoresis, urticaria)",
                  "name_ko": "피부 검진 (발진, 청색증, 발한, 두드러기)",
                  "keywords": ["rash", "cyanosis", "diaphoresis", "urticaria", "skin", "피부"], "turn_cost": 1, "kind": "exam"},
    "extremity_exam": {"id": "extremity_exam", "name_en": "Extremity exam (edema, pulses, calf tenderness)",
                        "name_ko": "사지 검진 (부종, 맥박, 종아리 압통)",
                        "keywords": ["edema", "pulses", "calf tenderness", "extremity", "사지", "부종"], "turn_cost": 1, "kind": "exam"},
    "costovertebral_tenderness": {"id": "costovertebral_tenderness", "name_en": "Costovertebral angle tenderness",
                                   "name_ko": "늑골척추각 압통", "keywords": ["cva tenderness", "flank pain on percussion", "늑골척추각"],
                                   "turn_cost": 1, "kind": "exam"},
    "pelvic_exam": {"id": "pelvic_exam", "name_en": "Pelvic / obstetric exam", "name_ko": "골반/산부인과 검진",
                    "keywords": ["pelvic exam", "adnexal tenderness", "골반"], "turn_cost": 1, "kind": "exam"},
    "mental_status_exam": {"id": "mental_status_exam", "name_en": "Mental status / GCS exam", "name_ko": "의식수준/GCS 평가",
                            "keywords": ["mental status", "gcs", "orientation", "의식수준"], "turn_cost": 1, "kind": "exam"},
}

# --- TEST catalog (laboratory + imaging) ------------------------------------------------------
TEST_CATALOG: Dict[str, ProcedureSpec] = {
    "ecg": {"id": "ecg", "name_en": "12-lead ECG", "name_ko": "12유도 심전도", "keywords": ["ecg", "ekg", "심전도"],
            "turn_cost": 1, "kind": "imaging"},
    "troponin": {"id": "troponin", "name_en": "Troponin", "name_ko": "트로포닌", "keywords": ["troponin", "트로포닌"],
                 "turn_cost": 1, "kind": "lab"},
    "d_dimer": {"id": "d_dimer", "name_en": "D-dimer", "name_ko": "D-dimer", "keywords": ["d-dimer", "d dimer"],
                "turn_cost": 1, "kind": "lab"},
    "cxr": {"id": "cxr", "name_en": "Chest X-ray", "name_ko": "흉부 X-ray", "keywords": ["chest x-ray", "cxr", "흉부"],
            "turn_cost": 1, "kind": "imaging"},
    "ct_chest_angio": {"id": "ct_chest_angio", "name_en": "CT chest angiography (PE protocol)",
                        "name_ko": "흉부 CT 혈관조영술 (PE protocol)",
                        "keywords": ["ct chest angio", "ct pe protocol", "cta chest", "chest cta",
                                     "ct angiogram chest", "폐색전 ct"],
                        "turn_cost": 2, "kind": "imaging"},
    "ct_aorta": {"id": "ct_aorta", "name_en": "CT angiography of the aorta", "name_ko": "대동맥 CT 혈관조영술",
                 "keywords": ["ct aorta", "aortic dissection ct", "cta aorta", "cta chest abdomen pelvis"],
                 "turn_cost": 2, "kind": "imaging"},
    "cbc": {"id": "cbc", "name_en": "Complete blood count", "name_ko": "전혈구검사(CBC)", "keywords": ["cbc", "complete blood count", "전혈구"],
            "turn_cost": 1, "kind": "lab"},
    "bmp": {"id": "bmp", "name_en": "Basic metabolic panel (electrolytes/renal function)",
            "name_ko": "기본대사패널(전해질/신기능)", "keywords": ["bmp", "electrolytes", "renal panel", "전해질"], "turn_cost": 1, "kind": "lab"},
    "lactate": {"id": "lactate", "name_en": "Serum lactate", "name_ko": "혈중 젖산(lactate)", "keywords": ["lactate", "젖산"],
                "turn_cost": 1, "kind": "lab"},
    "blood_culture": {"id": "blood_culture", "name_en": "Blood cultures", "name_ko": "혈액배양검사",
                       "keywords": ["blood culture", "혈액배양"], "turn_cost": 1, "kind": "lab"},
    "urinalysis": {"id": "urinalysis", "name_en": "Urinalysis", "name_ko": "요검사", "keywords": ["urinalysis", "urine test", "요검사"],
                    "turn_cost": 1, "kind": "lab"},
    "urine_culture": {"id": "urine_culture", "name_en": "Urine culture", "name_ko": "소변배양검사",
                       "keywords": ["urine culture", "소변배양"], "turn_cost": 1, "kind": "lab"},
    "ct_head": {"id": "ct_head", "name_en": "Non-contrast CT head", "name_ko": "비조영 뇌 CT",
                "keywords": ["ct head", "head ct", "뇌ct"], "turn_cost": 1, "kind": "imaging"},
    "mri_brain": {"id": "mri_brain", "name_en": "MRI brain with diffusion", "name_ko": "뇌 MRI (확산강조)",
                  "keywords": ["mri brain", "diffusion mri", "뇌mri"], "turn_cost": 2, "kind": "imaging"},
    "lumbar_puncture": {"id": "lumbar_puncture", "name_en": "Lumbar puncture (CSF analysis)",
                         "name_ko": "요추천자(뇌척수액 검사)", "keywords": ["lumbar puncture", "csf analysis", "요추천자"],
                         "turn_cost": 2, "kind": "lab"},
    "beta_hcg": {"id": "beta_hcg", "name_en": "Serum/urine beta-hCG", "name_ko": "베타hCG 검사",
                 "keywords": ["beta-hcg", "pregnancy test", "hcg", "임신반응"], "turn_cost": 1, "kind": "lab"},
    "pelvic_ultrasound": {"id": "pelvic_ultrasound", "name_en": "Pelvic ultrasound", "name_ko": "골반 초음파",
                           "keywords": ["pelvic ultrasound", "transvaginal ultrasound", "골반초음파"], "turn_cost": 2, "kind": "imaging"},
    "abdominal_ultrasound": {"id": "abdominal_ultrasound", "name_en": "Abdominal ultrasound", "name_ko": "복부 초음파",
                              "keywords": ["abdominal ultrasound", "복부초음파"], "turn_cost": 2, "kind": "imaging"},
    "ct_abdomen": {"id": "ct_abdomen", "name_en": "CT abdomen/pelvis with contrast", "name_ko": "복부/골반 조영증강 CT",
                    "keywords": ["ct abdomen", "abdominal ct", "복부ct"], "turn_cost": 2, "kind": "imaging"},
    "lipase": {"id": "lipase", "name_en": "Serum lipase", "name_ko": "혈청 리파아제", "keywords": ["lipase", "리파아제"],
               "turn_cost": 1, "kind": "lab"},
    "abg": {"id": "abg", "name_en": "Arterial blood gas", "name_ko": "동맥혈가스분석(ABG)", "keywords": ["abg", "arterial blood gas", "동맥혈가스"],
            "turn_cost": 1, "kind": "lab"},
    "ketones": {"id": "ketones", "name_en": "Serum/urine ketones", "name_ko": "케톤 검사", "keywords": ["ketones", "케톤"],
                "turn_cost": 1, "kind": "lab"},
    "glucose_point_of_care": {"id": "glucose_point_of_care", "name_en": "Point-of-care glucose", "name_ko": "즉시혈당검사",
                               "keywords": ["glucose", "blood sugar", "혈당"], "turn_cost": 1, "kind": "lab"},
    "fecal_occult_blood": {"id": "fecal_occult_blood", "name_en": "Fecal occult blood / rectal exam",
                            "name_ko": "대변잠혈검사/직장수지검사", "keywords": ["fecal occult blood", "rectal exam", "대변잠혈"],
                            "turn_cost": 1, "kind": "lab"},
}


def normalize_free_text_to_category(text: str, catalog: dict) -> str | None:
    """Best-effort keyword match of free text onto a catalog id/category, used only as a
    fallback dedup path for text that did not originate from our own catalog-driven generation
    (e.g. echoed competition observations)."""
    lowered = text.lower().strip()
    best_id, best_score = None, 0
    for key, spec in catalog.items():
        score = sum(1 for kw in spec["keywords"] if kw.lower() in lowered)
        if score > best_score:
            best_id, best_score = key, score
    return best_id
