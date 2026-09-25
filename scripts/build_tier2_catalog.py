#!/usr/bin/env python3
"""Generate nova_agent/knowledge/tier2_catalog.json — the broad Tier-2 structured disease catalog.

Design / honesty rules (do NOT relax):
  - Every entry carries ONLY fields we can state accurately: canonical name, common aliases, a
    specialty category, an urgency hint, and (where confident) an ICD-10 code. We do NOT invent
    discriminating tests / confirmatory findings here — that is Tier-1 (deep) territory. Tier-2 is
    "structured but shallow": enough to be a searchable, nameable differential candidate.
  - We NEVER fabricate a condition to inflate the count. Entries flagged curated=False are surfaced
    as NOT_CURATED and their clinical hints are treated as ABSENT by the reasoning engine.
  - Tier-2 must NOT duplicate the 34 Tier-1 deep concepts (different clinical entities only). Where
    a Tier-2 entry is a sibling/variant of a Tier-1 one, that's fine (distinct concept id).
  - ICD-10 codes are widely-published category codes; the operator's terminology snapshot remains
    the authoritative source (Tier-3). These are convenience anchors, clearly labeled ICD10.

This script is deterministic and dependency-free (stdlib json only). Re-run to regenerate.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

OUT_PATH = Path(__file__).resolve().parent.parent / "nova_agent" / "knowledge" / "tier2_catalog.json"

# ---------------------------------------------------------------------------
# Curated conditions. Grouped by specialty for readability; emitted flat.
# Tuple form: (id, name, category, urgency, icd10 or None, [aliases])
# urgency in {"CRITICAL","URGENT","ROUTINE"}. Only set when clinically well-established.
# ---------------------------------------------------------------------------

C = List[tuple]

CARDIOVASCULAR: C = [
    ("heart_failure_acute", "Acute Decompensated Heart Failure", "cardiovascular", "URGENT", "I50.9",
     ["chf exacerbation", "acute heart failure", "심부전 악화"]),
    ("stable_angina", "Stable Angina Pectoris", "cardiovascular", "URGENT", "I20.9",
     ["angina", "effort angina", "협심증"]),
    ("pericarditis", "Acute Pericarditis", "cardiovascular", "URGENT", "I30.9",
     ["pericarditis", "심낭염"]),
    ("myocarditis", "Myocarditis", "cardiovascular", "URGENT", "I40.9",
     ["myocarditis", "심근염"]),
    ("infective_endocarditis", "Infective Endocarditis", "cardiovascular", "CRITICAL", "I33.0",
     ["endocarditis", "감염성 심내막염"]),
    ("hypertensive_emergency", "Hypertensive Emergency", "cardiovascular", "CRITICAL", "I16.1",
     ["hypertensive crisis", "malignant hypertension", "고혈압 응급"]),
    ("hypertensive_urgency", "Hypertensive Urgency", "cardiovascular", "URGENT", "I16.0",
     ["고혈압 긴급"]),
    ("deep_vein_thrombosis", "Deep Vein Thrombosis", "cardiovascular", "URGENT", "I82.409",
     ["dvt", "심부정맥혈전증"]),
    ("aortic_aneurysm_unruptured", "Abdominal Aortic Aneurysm (Unruptured)", "cardiovascular", "URGENT", "I71.4",
     ["aaa", "복부대동맥류"]),
    ("cardiac_tamponade", "Cardiac Tamponade", "cardiovascular", "CRITICAL", "I31.4",
     ["tamponade", "심장눌림증"]),
    ("bradyarrhythmia_heart_block", "Symptomatic Bradyarrhythmia / Heart Block", "cardiovascular", "URGENT", "I44.2",
     ["complete heart block", "av block", "서맥성 부정맥"]),
    ("peripheral_arterial_disease", "Peripheral Arterial Disease", "cardiovascular", "ROUTINE", "I73.9",
     ["pad", "claudication", "말초동맥질환"]),
]

PULMONARY: C = [
    ("copd_stable", "Chronic Obstructive Pulmonary Disease (Stable)", "pulmonary", "ROUTINE", "J44.9",
     ["copd", "emphysema", "만성폐쇄성폐질환"]),
    ("asthma_stable", "Asthma (Stable / Chronic)", "pulmonary", "ROUTINE", "J45.909",
     ["asthma", "천식"]),
    ("pleural_effusion", "Pleural Effusion", "pulmonary", "URGENT", "J90",
     ["pleural effusion", "흉수"]),
    ("spontaneous_pneumothorax", "Spontaneous Pneumothorax (Non-tension)", "pulmonary", "URGENT", "J93.11",
     ["pneumothorax", "기흉"]),
    ("bronchiectasis", "Bronchiectasis", "pulmonary", "ROUTINE", "J47.9",
     ["bronchiectasis", "기관지확장증"]),
    ("pulmonary_tuberculosis", "Pulmonary Tuberculosis", "pulmonary", "URGENT", "A15.0",
     ["tb", "폐결핵"]),
    ("interstitial_lung_disease", "Interstitial Lung Disease", "pulmonary", "URGENT", "J84.9",
     ["ild", "pulmonary fibrosis", "간질성폐질환"]),
    ("influenza", "Influenza", "pulmonary", "ROUTINE", "J11.1",
     ["flu", "인플루엔자", "독감"]),
    ("covid19", "COVID-19", "pulmonary", "URGENT", "U07.1",
     ["sars-cov-2", "코로나19"]),
    ("aspiration_pneumonia", "Aspiration Pneumonia", "pulmonary", "URGENT", "J69.0",
     ["aspiration pneumonia", "흡인성 폐렴"]),
    ("acute_respiratory_distress", "Acute Respiratory Distress Syndrome", "pulmonary", "CRITICAL", "J80",
     ["ards", "급성호흡곤란증후군"]),
]

GASTROINTESTINAL: C = [
    ("cholecystitis", "Acute Cholecystitis", "abdominal_gi", "URGENT", "K81.0",
     ["cholecystitis", "gallbladder infection", "담낭염"]),
    ("cholangitis", "Acute Cholangitis", "abdominal_gi", "CRITICAL", "K83.09",
     ["ascending cholangitis", "담관염"]),
    ("choledocholithiasis", "Choledocholithiasis (CBD Stone)", "abdominal_gi", "URGENT", "K80.50",
     ["cbd stone", "bile duct stone", "총담관결석"]),
    ("diverticulitis", "Acute Diverticulitis", "abdominal_gi", "URGENT", "K57.92",
     ["diverticulitis", "게실염"]),
    ("bowel_obstruction", "Small Bowel Obstruction", "abdominal_gi", "URGENT", "K56.60",
     ["sbo", "ileus", "장폐색"]),
    ("mesenteric_ischemia", "Acute Mesenteric Ischemia", "abdominal_gi", "CRITICAL", "K55.0",
     ["mesenteric ischemia", "장간막 허혈"]),
    ("peptic_ulcer_disease", "Peptic Ulcer Disease", "abdominal_gi", "URGENT", "K27.9",
     ["pud", "gastric ulcer", "duodenal ulcer", "소화성궤양"]),
    ("perforated_viscus", "Perforated Viscus", "abdominal_gi", "CRITICAL", "K63.1",
     ["gi perforation", "장천공"]),
    ("inflammatory_bowel_disease", "Inflammatory Bowel Disease (Flare)", "abdominal_gi", "URGENT", "K52.9",
     ["ibd", "crohn", "ulcerative colitis", "염증성 장질환"]),
    ("acute_hepatitis", "Acute Hepatitis", "abdominal_gi", "URGENT", "K72.00",
     ["hepatitis", "간염"]),
    ("liver_cirrhosis_decompensated", "Decompensated Cirrhosis", "abdominal_gi", "URGENT", "K74.60",
     ["cirrhosis", "간경변"]),
    ("biliary_colic", "Biliary Colic", "abdominal_gi", "URGENT", "K80.20",
     ["gallstone colic", "담석산통"]),
    ("appendiceal_abscess", "Appendiceal Abscess", "abdominal_gi", "URGENT", None,
     ["appendix abscess"]),
    ("constipation", "Constipation", "abdominal_gi", "ROUTINE", "K59.00",
     ["변비"]),
    ("hemorrhoids", "Hemorrhoids", "abdominal_gi", "ROUTINE", "K64.9",
     ["piles", "치질"]),
]

NEUROLOGY: C = [
    ("tia", "Transient Ischemic Attack", "neuro", "CRITICAL", "G45.9",
     ["tia", "mini stroke", "일과성 허혈발작"]),
    ("intracerebral_hemorrhage", "Intracerebral Hemorrhage", "neuro", "CRITICAL", "I61.9",
     ["ich", "hemorrhagic stroke", "뇌내출혈"]),
    ("status_epilepticus", "Status Epilepticus", "neuro", "CRITICAL", "G41.9",
     ["status epilepticus", "경련지속상태"]),
    ("seizure_first", "First Unprovoked Seizure", "neuro", "URGENT", "R56.9",
     ["seizure", "발작"]),
    ("epilepsy", "Epilepsy", "neuro", "ROUTINE", "G40.909",
     ["epilepsy", "뇌전증"]),
    ("cluster_headache", "Cluster Headache", "neuro", "URGENT", "G44.009",
     ["cluster headache", "군발두통"]),
    ("giant_cell_arteritis", "Giant Cell (Temporal) Arteritis", "neuro", "CRITICAL", "M31.6",
     ["temporal arteritis", "gca", "측두동맥염"]),
    ("guillain_barre", "Guillain-Barré Syndrome", "neuro", "CRITICAL", "G61.0",
     ["gbs", "길랑바레증후군"]),
    ("bell_palsy", "Bell's Palsy", "neuro", "URGENT", "G51.0",
     ["facial palsy", "벨마비"]),
    ("multiple_sclerosis", "Multiple Sclerosis", "neuro", "URGENT", "G35",
     ["ms", "다발성경화증"]),
    ("parkinson_disease", "Parkinson's Disease", "neuro", "ROUTINE", "G20",
     ["parkinsonism", "파킨슨병"]),
    ("vestibular_neuritis", "Vestibular Neuritis", "neuro", "URGENT", "H81.23",
     ["vestibular neuronitis", "전정신경염"]),
    ("spinal_cord_compression", "Acute Spinal Cord Compression", "neuro", "CRITICAL", "G95.20",
     ["cord compression", "척수압박"]),
    ("cauda_equina", "Cauda Equina Syndrome", "neuro", "CRITICAL", "G83.4",
     ["cauda equina", "마미증후군"]),
    ("delirium", "Delirium", "neuro", "URGENT", "F05",
     ["acute confusional state", "섬망"]),
]

ENDOCRINE: C = [
    ("hyperosmolar_hyperglycemic", "Hyperosmolar Hyperglycemic State", "endocrine_metabolic", "CRITICAL", "E11.00",
     ["hhs", "고삼투압성 고혈당"]),
    ("thyroid_storm", "Thyroid Storm", "endocrine_metabolic", "CRITICAL", "E05.91",
     ["thyrotoxic crisis", "갑상선 폭풍"]),
    ("myxedema_coma", "Myxedema Coma", "endocrine_metabolic", "CRITICAL", "E03.5",
     ["severe hypothyroidism", "점액수종성 혼수"]),
    ("adrenal_crisis", "Adrenal Crisis", "endocrine_metabolic", "CRITICAL", "E27.2",
     ["addisonian crisis", "부신위기"]),
    ("hyperthyroidism", "Hyperthyroidism", "endocrine_metabolic", "ROUTINE", "E05.90",
     ["thyrotoxicosis", "graves", "갑상선기능항진증"]),
    ("hypothyroidism", "Hypothyroidism", "endocrine_metabolic", "ROUTINE", "E03.9",
     ["갑상선기능저하증"]),
    ("type2_diabetes", "Type 2 Diabetes Mellitus", "endocrine_metabolic", "ROUTINE", "E11.9",
     ["t2dm", "제2형 당뇨병"]),
    ("hypercalcemia", "Hypercalcemia", "endocrine_metabolic", "URGENT", "E83.52",
     ["고칼슘혈증"]),
    ("hypocalcemia", "Hypocalcemia", "endocrine_metabolic", "URGENT", "E83.51",
     ["저칼슘혈증"]),
    ("pituitary_apoplexy", "Pituitary Apoplexy", "endocrine_metabolic", "CRITICAL", "E23.6",
     ["뇌하수체 졸중"]),
]

GENITOURINARY_RENAL: C = [
    ("acute_kidney_injury", "Acute Kidney Injury", "genitourinary", "URGENT", "N17.9",
     ["aki", "acute renal failure", "급성 신손상"]),
    ("chronic_kidney_disease", "Chronic Kidney Disease", "genitourinary", "ROUTINE", "N18.9",
     ["ckd", "만성 신질환"]),
    ("urinary_retention", "Acute Urinary Retention", "genitourinary", "URGENT", "R33.8",
     ["요폐"]),
    ("testicular_torsion", "Testicular Torsion", "genitourinary", "CRITICAL", "N44.00",
     ["고환 염전"]),
    ("epididymitis", "Epididymitis", "genitourinary", "URGENT", "N45.1",
     ["부고환염"]),
    ("prostatitis", "Acute Prostatitis", "genitourinary", "URGENT", "N41.0",
     ["전립선염"]),
    ("bph", "Benign Prostatic Hyperplasia", "genitourinary", "ROUTINE", "N40.0",
     ["bph", "전립선비대증"]),
    ("pelvic_inflammatory_disease", "Pelvic Inflammatory Disease", "genitourinary", "URGENT", "N73.9",
     ["pid", "골반염"]),
    ("ovarian_torsion", "Ovarian Torsion", "genitourinary", "CRITICAL", "N83.51",
     ["난소 염전"]),
    ("ruptured_ovarian_cyst", "Ruptured Ovarian Cyst", "genitourinary", "URGENT", "N83.20",
     ["난소낭종 파열"]),
    ("rhabdomyolysis", "Rhabdomyolysis", "genitourinary", "URGENT", "M62.82",
     ["횡문근융해증"]),
]

INFECTIOUS: C = [
    ("cellulitis", "Cellulitis", "infectious", "URGENT", "L03.90",
     ["봉와직염"]),
    ("necrotizing_fasciitis", "Necrotizing Fasciitis", "infectious", "CRITICAL", "M72.6",
     ["nec fasc", "괴사성 근막염"]),
    ("septic_arthritis", "Septic Arthritis", "infectious", "CRITICAL", "M00.9",
     ["화농성 관절염"]),
    ("osteomyelitis", "Osteomyelitis", "infectious", "URGENT", "M86.9",
     ["골수염"]),
    ("infectious_mononucleosis", "Infectious Mononucleosis", "infectious", "ROUTINE", "B27.90",
     ["mono", "ebv", "전염성 단핵구증"]),
    ("peritonsillar_abscess", "Peritonsillar Abscess", "infectious", "URGENT", "J36",
     ["quinsy", "편도주위 농양"]),
    ("epiglottitis", "Acute Epiglottitis", "infectious", "CRITICAL", "J05.10",
     ["후두개염"]),
    ("herpes_zoster", "Herpes Zoster (Shingles)", "infectious", "ROUTINE", "B02.9",
     ["shingles", "대상포진"]),
    ("malaria", "Malaria", "infectious", "URGENT", "B54",
     ["말라리아"]),
    ("dengue", "Dengue Fever", "infectious", "URGENT", "A90",
     ["뎅기열"]),
    ("clostridioides_difficile", "Clostridioides difficile Colitis", "infectious", "URGENT", "A04.7",
     ["c diff", "pseudomembranous colitis"]),
    ("toxic_shock_syndrome", "Toxic Shock Syndrome", "infectious", "CRITICAL", "A48.3",
     ["tss", "독성쇼크증후군"]),
]

HEMATOLOGY_ONCOLOGY: C = [
    ("anemia_unspecified", "Anemia (Unspecified)", "hematology_oncology", "ROUTINE", "D64.9",
     ["빈혈"]),
    ("iron_deficiency_anemia", "Iron Deficiency Anemia", "hematology_oncology", "ROUTINE", "D50.9",
     ["철결핍성 빈혈"]),
    ("neutropenic_fever", "Febrile Neutropenia", "hematology_oncology", "CRITICAL", "D70.9",
     ["neutropenic sepsis", "호중구감소성 발열"]),
    ("tumor_lysis_syndrome", "Tumor Lysis Syndrome", "hematology_oncology", "CRITICAL", "E88.3",
     ["tls", "종양용해증후군"]),
    ("acute_leukemia", "Acute Leukemia (Presentation)", "hematology_oncology", "CRITICAL", "C95.00",
     ["급성 백혈병"]),
    ("lymphoma", "Lymphoma (Presentation)", "hematology_oncology", "URGENT", "C85.90",
     ["림프종"]),
    ("thrombocytopenia", "Thrombocytopenia", "hematology_oncology", "URGENT", "D69.6",
     ["low platelets", "혈소판감소증"]),
    ("dic", "Disseminated Intravascular Coagulation", "hematology_oncology", "CRITICAL", "D65",
     ["파종성 혈관내 응고"]),
    ("sickle_cell_crisis", "Sickle Cell Vaso-occlusive Crisis", "hematology_oncology", "URGENT", "D57.00",
     ["sickle cell crisis"]),
    ("superior_vena_cava_syndrome", "Superior Vena Cava Syndrome", "hematology_oncology", "URGENT", "I87.1",
     ["svc syndrome", "상대정맥증후군"]),
    ("malignant_spinal_cord_compression", "Malignant Spinal Cord Compression", "hematology_oncology", "CRITICAL", None,
     ["mscc"]),
]

RHEUM_MSK: C = [
    ("gout", "Acute Gout Flare", "musculoskeletal", "URGENT", "M10.9",
     ["gouty arthritis", "통풍"]),
    ("pseudogout", "Pseudogout (CPPD)", "musculoskeletal", "URGENT", "M11.20",
     ["cppd", "가성통풍"]),
    ("rheumatoid_arthritis", "Rheumatoid Arthritis", "musculoskeletal", "ROUTINE", "M06.9",
     ["ra", "류마티스 관절염"]),
    ("systemic_lupus", "Systemic Lupus Erythematosus", "musculoskeletal", "URGENT", "M32.9",
     ["sle", "lupus", "루푸스"]),
    ("polymyalgia_rheumatica", "Polymyalgia Rheumatica", "musculoskeletal", "URGENT", "M35.3",
     ["pmr", "류마티스성 다발근통"]),
    ("low_back_pain_mechanical", "Mechanical Low Back Pain", "musculoskeletal", "ROUTINE", "M54.50",
     ["lumbago", "요통"]),
    ("lumbar_disc_herniation", "Lumbar Disc Herniation", "musculoskeletal", "URGENT", "M51.26",
     ["hivd", "추간판 탈출증"]),
    ("compartment_syndrome", "Acute Compartment Syndrome", "musculoskeletal", "CRITICAL", "T79.A0XA",
     ["구획증후군"]),
    ("vertebral_compression_fracture", "Vertebral Compression Fracture", "musculoskeletal", "URGENT", "M48.50XA",
     ["척추 압박골절"]),
]

PSYCH: C = [
    ("major_depression", "Major Depressive Episode", "psychiatric", "URGENT", "F32.9",
     ["depression", "우울증"]),
    ("suicidal_ideation", "Suicidal Ideation / Crisis", "psychiatric", "CRITICAL", "R45.851",
     ["suicidal ideation", "자살 사고"]),
    ("generalized_anxiety", "Generalized Anxiety Disorder", "psychiatric", "ROUTINE", "F41.1",
     ["gad", "불안장애"]),
    ("alcohol_withdrawal", "Alcohol Withdrawal", "psychiatric", "URGENT", "F10.239",
     ["dt", "delirium tremens", "알코올 금단"]),
    ("acute_psychosis", "Acute Psychosis", "psychiatric", "URGENT", "F29",
     ["정신병적 삽화"]),
    ("serotonin_syndrome", "Serotonin Syndrome", "psychiatric", "CRITICAL", "T43.225A",
     ["세로토닌 증후군"]),
    ("neuroleptic_malignant_syndrome", "Neuroleptic Malignant Syndrome", "psychiatric", "CRITICAL", "G21.0",
     ["nms", "신경이완제 악성증후군"]),
]

TOXICOLOGY_ENV: C = [
    ("acetaminophen_overdose", "Acetaminophen Overdose", "toxicology", "CRITICAL", "T39.1X1A",
     ["paracetamol overdose", "아세트아미노펜 중독"]),
    ("opioid_overdose", "Opioid Overdose", "toxicology", "CRITICAL", "T40.2X1A",
     ["opioid toxicity", "아편유사제 중독"]),
    ("carbon_monoxide_poisoning", "Carbon Monoxide Poisoning", "toxicology", "CRITICAL", "T58.91XA",
     ["co poisoning", "일산화탄소 중독"]),
    ("organophosphate_poisoning", "Organophosphate Poisoning", "toxicology", "CRITICAL", "T60.0X1A",
     ["유기인계 중독"]),
    ("salicylate_toxicity", "Salicylate Toxicity", "toxicology", "CRITICAL", "T39.011A",
     ["aspirin overdose", "살리실산 중독"]),
    ("tca_overdose", "Tricyclic Antidepressant Overdose", "toxicology", "CRITICAL", "T43.011A",
     ["tca overdose"]),
    ("heat_stroke", "Heat Stroke", "environmental", "CRITICAL", "T67.0XXA",
     ["열사병"]),
    ("hypothermia", "Hypothermia", "environmental", "CRITICAL", "T68.XXXA",
     ["저체온증"]),
    ("anaphylactoid_reaction", "Anaphylactoid Reaction", "toxicology", "CRITICAL", None,
     ["아나필락시양 반응"]),
]

DERM_ENT_EYE: C = [
    ("acute_angle_closure_glaucoma", "Acute Angle-Closure Glaucoma", "ophthalmology", "CRITICAL", "H40.219",
     ["급성 폐쇄각 녹내장"]),
    ("central_retinal_artery_occlusion", "Central Retinal Artery Occlusion", "ophthalmology", "CRITICAL", "H34.10",
     ["crao", "망막중심동맥폐쇄"]),
    ("orbital_cellulitis", "Orbital Cellulitis", "ophthalmology", "CRITICAL", "H05.019",
     ["안와 봉와직염"]),
    ("acute_otitis_media", "Acute Otitis Media", "ent", "ROUTINE", "H66.90",
     ["중이염"]),
    ("epistaxis", "Epistaxis", "ent", "URGENT", "R04.0",
     ["nosebleed", "비출혈"]),
    ("sudden_sensorineural_hearing_loss", "Sudden Sensorineural Hearing Loss", "ent", "URGENT", "H91.20",
     ["ssnhl", "돌발성 난청"]),
    ("stevens_johnson_syndrome", "Stevens-Johnson Syndrome", "dermatology", "CRITICAL", "L51.1",
     ["sjs", "스티븐스존슨 증후군"]),
    ("angioedema", "Angioedema", "dermatology", "CRITICAL", "T78.3XXA",
     ["혈관부종"]),
    ("urticaria", "Urticaria", "dermatology", "ROUTINE", "L50.9",
     ["hives", "두드러기"]),
]

OB_PEDS: C = [
    ("preeclampsia", "Preeclampsia", "obstetric", "CRITICAL", "O14.90",
     ["전자간증"]),
    ("eclampsia", "Eclampsia", "obstetric", "CRITICAL", "O15.9",
     ["자간증"]),
    ("placental_abruption", "Placental Abruption", "obstetric", "CRITICAL", "O45.90",
     ["태반조기박리"]),
    ("hyperemesis_gravidarum", "Hyperemesis Gravidarum", "obstetric", "URGENT", "O21.0",
     ["임신오조"]),
    ("febrile_infant", "Febrile Infant (<90 days)", "pediatric", "CRITICAL", None,
     ["neonatal fever"]),
    ("croup", "Croup (Laryngotracheobronchitis)", "pediatric", "URGENT", "J05.0",
     ["크룹"]),
    ("bronchiolitis", "Bronchiolitis", "pediatric", "URGENT", "J21.9",
     ["세기관지염"]),
    ("intussusception", "Intussusception", "pediatric", "CRITICAL", "K56.1",
     ["장중첩증"]),
    ("kawasaki_disease", "Kawasaki Disease", "pediatric", "URGENT", "M30.3",
     ["가와사키병"]),
]


ALL_GROUPS = [
    CARDIOVASCULAR, PULMONARY, GASTROINTESTINAL, NEUROLOGY, ENDOCRINE,
    GENITOURINARY_RENAL, INFECTIOUS, HEMATOLOGY_ONCOLOGY, RHEUM_MSK, PSYCH,
    TOXICOLOGY_ENV, DERM_ENT_EYE, OB_PEDS,
]

# Supplementary groups (vNext coverage expansion). Loaded lazily so the base catalog still builds
# even if the extra module is absent. build_conditions() de-duplicates against the base by id AND
# canonical name, so an extra entry that clinically overlaps a base one is skipped, never crashing.
try:
    from tier2_catalog_extra import EXTRA_GROUPS  # when run from scripts/
except ImportError:  # pragma: no cover - path fallback when invoked from repo root
    try:
        from scripts.tier2_catalog_extra import EXTRA_GROUPS
    except ImportError:
        EXTRA_GROUPS = []

# Large 5,000-diagnosis-round expansion (ICD-10-chapter organized). Same tuple form + dedup.
try:
    from tier2_catalog_expansion import ALL_EXPANSION_GROUPS
except ImportError:  # pragma: no cover
    try:
        from scripts.tier2_catalog_expansion import ALL_EXPANSION_GROUPS
    except ImportError:
        ALL_EXPANSION_GROUPS = []

try:
    from tier2_catalog_expansion2 import ALL_EXPANSION2_GROUPS
except ImportError:  # pragma: no cover
    try:
        from scripts.tier2_catalog_expansion2 import ALL_EXPANSION2_GROUPS
    except ImportError:
        ALL_EXPANSION2_GROUPS = []

try:
    from tier2_catalog_expansion3 import ALL_EXPANSION3_GROUPS
except ImportError:  # pragma: no cover
    try:
        from scripts.tier2_catalog_expansion3 import ALL_EXPANSION3_GROUPS
    except ImportError:
        ALL_EXPANSION3_GROUPS = []


def build_conditions() -> List[Dict]:
    conditions: List[Dict] = []
    seen_ids = set()
    seen_names = set()

    def _make_entry(cid, name, category, urgency, icd10, aliases) -> Dict:
        entry: Dict = {
            "id": cid,
            "name": name,
            "category": category,
            "aliases": aliases,
            "semantic_type": "DISEASE",
            "curated": True,
        }
        if urgency:
            entry["urgency"] = urgency
            entry["dangerous"] = urgency in ("CRITICAL", "URGENT")
        if icd10:
            entry["external_codes"] = [{"system": "ICD10", "code": icd10, "display": name}]
        return entry

    # Base groups: id collisions here are an authoring error and must fail loudly.
    for group in ALL_GROUPS:
        for cid, name, category, urgency, icd10, aliases in group:
            if cid in seen_ids:
                raise SystemExit(f"duplicate tier2 id (base): {cid}")
            seen_ids.add(cid)
            seen_names.add(name.strip().lower())
            conditions.append(_make_entry(cid, name, category, urgency, icd10, aliases))

    # Supplementary groups: silently DEDUP against the base by id AND canonical name so a clinically
    # overlapping entry (e.g. a variant already present in the base 140) is skipped rather than
    # crashing. Within the extras, a duplicate id is still an authoring error and fails loudly.
    extra_ids = set()
    for group in (list(EXTRA_GROUPS) + list(ALL_EXPANSION_GROUPS)
                  + list(ALL_EXPANSION2_GROUPS) + list(ALL_EXPANSION3_GROUPS)):
        for cid, name, category, urgency, icd10, aliases in group:
            if cid in extra_ids:
                raise SystemExit(f"duplicate tier2 id (extra): {cid}")
            extra_ids.add(cid)
            if cid in seen_ids or name.strip().lower() in seen_names:
                continue  # overlaps a base/earlier concept -> skip (never double-count)
            seen_ids.add(cid)
            seen_names.add(name.strip().lower())
            conditions.append(_make_entry(cid, name, category, urgency, icd10, aliases))

    conditions.sort(key=lambda e: (e["category"], e["id"]))
    return conditions


def main() -> None:
    conditions = build_conditions()
    payload = {
        "schema_version": "tier2.v1",
        "description": (
            "Broad Tier-2 structured disease catalog for N.O.V.A. open-world differential. "
            "Shallow-but-accurate: name/aliases/category/urgency/ICD-10 only. NOT a substitute for "
            "the 34 Tier-1 deep profiles. Conditions with curated=false are surfaced as NOT_CURATED."
        ),
        "provenance": (
            "Internally curated from standard clinical references; ICD-10 codes are convenience "
            "anchors. The operator's terminology snapshot (Tier-3) is authoritative for coding."
        ),
        "count": len(conditions),
        "conditions": conditions,
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(conditions)} Tier-2 conditions -> {OUT_PATH}")


if __name__ == "__main__":
    main()
