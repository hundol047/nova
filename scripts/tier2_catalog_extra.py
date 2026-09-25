"""Supplementary Tier-2 structured conditions (vNext coverage expansion to 500+).

Same honesty rules and tuple format as scripts/build_tier2_catalog.py:
    (id, name, category, urgency|None, icd10|None, [aliases])
urgency in {"CRITICAL","URGENT","ROUTINE"} — set ONLY when clinically well-established.
NO fabricated discriminating tests / confirmatory findings (that is Tier-1 deep territory).
ICD-10 codes are widely-published convenience anchors; the operator's Tier-3 snapshot is
authoritative. Where a code or urgency is uncertain it is left None rather than guessed.

These EXTEND (do not replace) the base 13 groups. build_tier2_catalog.py merges both and enforces
global id uniqueness, so nothing here may reuse a base id.
"""

from __future__ import annotations

from typing import List

C = List[tuple]

# ---------------------------------------------------------------------------
CARDIOLOGY_EXTRA: C = [
    ("aortic_stenosis", "Aortic Stenosis", "cardiovascular", "URGENT", "I35.0", ["as", "대동맥판막 협착"]),
    ("aortic_regurgitation", "Aortic Regurgitation", "cardiovascular", "URGENT", "I35.1", ["ar", "대동맥판막 폐쇄부전"]),
    ("mitral_stenosis", "Mitral Stenosis", "cardiovascular", "URGENT", "I05.0", ["ms", "승모판 협착"]),
    ("mitral_regurgitation", "Mitral Regurgitation", "cardiovascular", "URGENT", "I34.0", ["mr", "승모판 폐쇄부전"]),
    ("tricuspid_regurgitation", "Tricuspid Regurgitation", "cardiovascular", "ROUTINE", "I07.1", ["tr", "삼첨판 폐쇄부전"]),
    ("dilated_cardiomyopathy", "Dilated Cardiomyopathy", "cardiovascular", "URGENT", "I42.0", ["dcm", "확장성 심근병증"]),
    ("hypertrophic_cardiomyopathy", "Hypertrophic Cardiomyopathy", "cardiovascular", "URGENT", "I42.1", ["hcm", "비후성 심근병증"]),
    ("restrictive_cardiomyopathy", "Restrictive Cardiomyopathy", "cardiovascular", "URGENT", "I42.5", ["제한성 심근병증"]),
    ("chronic_heart_failure", "Chronic Heart Failure", "cardiovascular", "URGENT", "I50.22", ["chf", "만성 심부전"]),
    ("cardiogenic_shock", "Cardiogenic Shock", "cardiovascular", "CRITICAL", "R57.0", ["심인성 쇼크"]),
    ("ventricular_tachycardia", "Ventricular Tachycardia", "cardiovascular", "CRITICAL", "I47.2", ["vt", "심실빈맥"]),
    ("ventricular_fibrillation", "Ventricular Fibrillation", "cardiovascular", "CRITICAL", "I49.01", ["vfib", "심실세동"]),
    ("atrial_flutter", "Atrial Flutter", "cardiovascular", "URGENT", "I48.92", ["심방조동"]),
    ("supraventricular_tachycardia", "Supraventricular Tachycardia", "cardiovascular", "URGENT", "I47.1", ["svt", "상심실성 빈맥"]),
    ("wolff_parkinson_white", "Wolff-Parkinson-White Syndrome", "cardiovascular", "URGENT", "I45.6", ["wpw"]),
    ("long_qt_syndrome", "Long QT Syndrome", "cardiovascular", "URGENT", "I45.81", ["lqts"]),
    ("sick_sinus_syndrome", "Sick Sinus Syndrome", "cardiovascular", "URGENT", "I49.5", ["동기능 부전 증후군"]),
    ("stable_coronary_artery_disease", "Stable Coronary Artery Disease", "cardiovascular", "ROUTINE", "I25.10", ["cad", "관상동맥질환"]),
    ("rheumatic_heart_disease", "Rheumatic Heart Disease", "cardiovascular", "ROUTINE", "I09.9", ["류마티스 심장병"]),
    ("atrial_myxoma", "Atrial Myxoma", "cardiovascular", "URGENT", "D15.1", ["심방 점액종"]),
    ("takotsubo_cardiomyopathy", "Takotsubo Cardiomyopathy", "cardiovascular", "URGENT", "I51.81", ["stress cardiomyopathy", "broken heart syndrome"]),
    ("constrictive_pericarditis", "Constrictive Pericarditis", "cardiovascular", "URGENT", "I31.1", ["교착성 심막염"]),
    ("pericardial_effusion", "Pericardial Effusion", "cardiovascular", "URGENT", "I31.3", ["심낭 삼출"]),
    ("premature_ventricular_contractions", "Premature Ventricular Contractions", "cardiovascular", "ROUTINE", "I49.3", ["pvc", "심실조기수축"]),
]

VASCULAR_EXTRA: C = [
    ("ruptured_aaa", "Ruptured Abdominal Aortic Aneurysm", "vascular", "CRITICAL", "I71.3", ["ruptured aaa", "복부대동맥류 파열"]),
    ("thoracic_aortic_aneurysm", "Thoracic Aortic Aneurysm", "vascular", "URGENT", "I71.2", ["taa", "흉부대동맥류"]),
    ("acute_limb_ischemia", "Acute Limb Ischemia", "vascular", "CRITICAL", "I74.3", ["급성 사지 허혈"]),
    ("carotid_artery_stenosis", "Carotid Artery Stenosis", "vascular", "URGENT", "I65.2", ["경동맥 협착"]),
    ("superficial_thrombophlebitis", "Superficial Thrombophlebitis", "vascular", "ROUTINE", "I80.0", ["표재성 혈전정맥염"]),
    ("chronic_venous_insufficiency", "Chronic Venous Insufficiency", "vascular", "ROUTINE", "I87.2", ["만성 정맥부전"]),
    ("lymphedema", "Lymphedema", "vascular", "ROUTINE", "I89.0", ["림프부종"]),
    ("raynaud_phenomenon", "Raynaud Phenomenon", "vascular", "ROUTINE", "I73.00", ["레이노 현상"]),
    ("thromboangiitis_obliterans", "Thromboangiitis Obliterans (Buerger Disease)", "vascular", "URGENT", "I73.1", ["buerger disease", "버거병"]),
    ("renal_artery_stenosis", "Renal Artery Stenosis", "vascular", "URGENT", "I70.1", ["신동맥 협착"]),
    ("subclavian_steal_syndrome", "Subclavian Steal Syndrome", "vascular", "URGENT", "G45.8", ["쇄골하동맥 도류 증후군"]),
    ("arteriovenous_malformation", "Arteriovenous Malformation", "vascular", "URGENT", "Q27.30", ["avm", "동정맥 기형"]),
]

PULMONOLOGY_EXTRA: C = [
    ("ards", "Acute Respiratory Distress Syndrome", "pulmonary", "CRITICAL", "J80", ["ards", "급성호흡곤란증후군"]),
    ("acute_respiratory_failure", "Acute Respiratory Failure", "pulmonary", "CRITICAL", "J96.00", ["급성 호흡부전"]),
    ("pulmonary_hypertension", "Pulmonary Hypertension", "pulmonary", "URGENT", "I27.20", ["폐고혈압"]),
    ("simple_pneumothorax", "Simple Pneumothorax", "pulmonary", "URGENT", "J93.9", ["기흉"]),
    ("hemothorax", "Hemothorax", "pulmonary", "CRITICAL", "J94.2", ["혈흉"]),
    ("empyema", "Pleural Empyema", "pulmonary", "URGENT", "J86.9", ["농흉"]),
    ("lung_cancer", "Lung Malignancy", "pulmonary", "URGENT", "C34.90", ["lung cancer", "폐암"]),
    ("sarcoidosis", "Sarcoidosis", "pulmonary", "ROUTINE", "D86.0", ["유육종증"]),
    ("idiopathic_pulmonary_fibrosis", "Idiopathic Pulmonary Fibrosis", "pulmonary", "URGENT", "J84.112", ["ipf", "특발성 폐섬유증"]),
    ("hypersensitivity_pneumonitis", "Hypersensitivity Pneumonitis", "pulmonary", "URGENT", "J67.9", ["과민성 폐렴"]),
    ("obstructive_sleep_apnea", "Obstructive Sleep Apnea", "pulmonary", "ROUTINE", "G47.33", ["osa", "폐쇄성 수면무호흡"]),
    ("cystic_fibrosis", "Cystic Fibrosis", "pulmonary", "URGENT", "E84.9", ["cf", "낭성 섬유증"]),
    ("pertussis", "Pertussis (Whooping Cough)", "pulmonary", "URGENT", "A37.90", ["whooping cough", "백일해"]),
    ("legionella_pneumonia", "Legionella Pneumonia", "pulmonary", "URGENT", "A48.1", ["legionnaires", "레지오넬라 폐렴"]),
    ("pneumocystis_pneumonia", "Pneumocystis Pneumonia", "pulmonary", "CRITICAL", "B59", ["pcp", "pjp"]),
    ("fat_embolism_syndrome", "Fat Embolism Syndrome", "pulmonary", "CRITICAL", "T79.1", ["지방 색전 증후군"]),
    ("foreign_body_aspiration", "Foreign Body Aspiration", "pulmonary", "CRITICAL", "T17.900", ["이물 흡인"]),
    ("mesothelioma", "Pleural Mesothelioma", "pulmonary", "URGENT", "C45.0", ["중피종"]),
    ("bronchiolitis_obliterans", "Bronchiolitis Obliterans", "pulmonary", "URGENT", "J44.81", ["폐쇄성 세기관지염"]),
]

NEUROLOGY_EXTRA: C = [
    ("subdural_hematoma", "Subdural Hematoma", "neuro", "CRITICAL", "I62.00", ["sdh", "경막하 출혈"]),
    ("epidural_hematoma", "Epidural Hematoma", "neuro", "CRITICAL", "I62.1", ["edh", "경막외 출혈"]),
    ("encephalitis", "Viral Encephalitis", "neuro", "CRITICAL", "A86", ["뇌염"]),
    ("myasthenia_gravis", "Myasthenia Gravis", "neuro", "URGENT", "G70.00", ["mg", "중증 근무력증"]),
    ("myasthenic_crisis", "Myasthenic Crisis", "neuro", "CRITICAL", "G70.01", ["근무력성 위기"]),
    ("brain_tumor", "Brain Tumor", "neuro", "URGENT", "C71.9", ["뇌종양"]),
    ("brain_abscess", "Brain Abscess", "neuro", "CRITICAL", "G06.0", ["뇌 농양"]),
    ("normal_pressure_hydrocephalus", "Normal Pressure Hydrocephalus", "neuro", "URGENT", "G91.2", ["nph", "정상압 수두증"]),
    ("idiopathic_intracranial_hypertension", "Idiopathic Intracranial Hypertension", "neuro", "URGENT", "G93.2", ["iih", "pseudotumor cerebri"]),
    ("trigeminal_neuralgia", "Trigeminal Neuralgia", "neuro", "URGENT", "G50.0", ["삼차신경통"]),
    ("myelitis_transverse", "Transverse Myelitis", "neuro", "CRITICAL", "G37.3", ["횡단성 척수염"]),
    ("amyotrophic_lateral_sclerosis", "Amyotrophic Lateral Sclerosis", "neuro", "URGENT", "G12.21", ["als", "루게릭병"]),
    ("wernicke_encephalopathy", "Wernicke Encephalopathy", "neuro", "CRITICAL", "E51.2", ["베르니케 뇌병증"]),
    ("dementia_alzheimer", "Alzheimer Disease", "neuro", "ROUTINE", "G30.9", ["알츠하이머병"]),
    ("vascular_dementia", "Vascular Dementia", "neuro", "ROUTINE", "F01.50", ["혈관성 치매"]),
    ("cerebral_venous_thrombosis", "Cerebral Venous Sinus Thrombosis", "neuro", "CRITICAL", "I67.6", ["cvst", "뇌정맥동 혈전증"]),
    ("carpal_tunnel_syndrome", "Carpal Tunnel Syndrome", "neuro", "ROUTINE", "G56.00", ["손목터널 증후군"]),
    ("peripheral_neuropathy", "Peripheral Neuropathy", "neuro", "ROUTINE", "G62.9", ["말초 신경병증"]),
    ("essential_tremor", "Essential Tremor", "neuro", "ROUTINE", "G25.0", ["본태성 진전"]),
    ("huntington_disease", "Huntington Disease", "neuro", "ROUTINE", "G10", ["헌팅턴병"]),
    ("neuromyelitis_optica", "Neuromyelitis Optica", "neuro", "URGENT", "G36.0", ["nmo", "시신경 척수염"]),
    ("cerebellar_ataxia", "Cerebellar Ataxia", "neuro", "URGENT", "G11.9", ["소뇌 실조"]),
]

GASTROENTEROLOGY_EXTRA: C = [
    ("biliary_colic", "Biliary Colic", "abdominal_gi", "URGENT", "K80.20", ["담석 산통"]),
    ("crohn_disease", "Crohn Disease", "abdominal_gi", "URGENT", "K50.90", ["크론병"]),
    ("ulcerative_colitis", "Ulcerative Colitis", "abdominal_gi", "URGENT", "K51.90", ["궤양성 대장염"]),
    ("irritable_bowel_syndrome", "Irritable Bowel Syndrome", "abdominal_gi", "ROUTINE", "K58.9", ["ibs", "과민성 대장 증후군"]),
    ("large_bowel_obstruction", "Large Bowel Obstruction", "abdominal_gi", "URGENT", "K56.69", ["대장 폐색"]),
    ("sigmoid_volvulus", "Sigmoid Volvulus", "abdominal_gi", "CRITICAL", "K56.2", ["에스결장 염전"]),
    ("toxic_megacolon", "Toxic Megacolon", "abdominal_gi", "CRITICAL", "K59.31", ["독성 거대결장"]),
    ("gastric_cancer", "Gastric Cancer", "abdominal_gi", "URGENT", "C16.9", ["위암"]),
    ("colorectal_cancer", "Colorectal Cancer", "abdominal_gi", "URGENT", "C18.9", ["대장암"]),
    ("esophageal_cancer", "Esophageal Cancer", "abdominal_gi", "URGENT", "C15.9", ["식도암"]),
    ("achalasia", "Achalasia", "abdominal_gi", "ROUTINE", "K22.0", ["식도 이완불능증"]),
    ("esophageal_varices", "Esophageal Varices", "abdominal_gi", "CRITICAL", "I85.00", ["식도 정맥류"]),
    ("mallory_weiss_tear", "Mallory-Weiss Tear", "abdominal_gi", "URGENT", "K22.6", ["말로리-바이스 열상"]),
    ("boerhaave_syndrome", "Boerhaave Syndrome (Esophageal Rupture)", "abdominal_gi", "CRITICAL", "K22.3", ["식도 파열"]),
    ("celiac_disease", "Celiac Disease", "abdominal_gi", "ROUTINE", "K90.0", ["셀리악병"]),
    ("chronic_pancreatitis", "Chronic Pancreatitis", "abdominal_gi", "URGENT", "K86.1", ["만성 췌장염"]),
    ("pancreatic_cancer", "Pancreatic Cancer", "abdominal_gi", "URGENT", "C25.9", ["췌장암"]),
    ("gastroparesis", "Gastroparesis", "abdominal_gi", "ROUTINE", "K31.84", ["위마비"]),
    ("hemorrhoids_gi", "Symptomatic Hemorrhoids", "abdominal_gi", "ROUTINE", "K64.9", ["치핵"]),
    ("anal_fissure", "Anal Fissure", "abdominal_gi", "ROUTINE", "K60.2", ["항문 열창"]),
    ("perianal_abscess", "Perianal Abscess", "abdominal_gi", "URGENT", "K61.0", ["항문 주위 농양"]),
    ("ischemic_colitis", "Ischemic Colitis", "abdominal_gi", "URGENT", "K55.9", ["허혈성 대장염"]),
    ("gastritis", "Acute Gastritis", "abdominal_gi", "ROUTINE", "K29.00", ["위염"]),
    ("small_bowel_obstruction_extra", "Adhesive Small Bowel Obstruction", "abdominal_gi", "URGENT", "K56.5", ["유착성 소장 폐색"]),
]

HEPATOLOGY_EXTRA: C = [
    ("acute_liver_failure", "Acute Liver Failure", "hepatology", "CRITICAL", "K72.00", ["fulminant hepatic failure", "급성 간부전"]),
    ("cirrhosis", "Hepatic Cirrhosis", "hepatology", "URGENT", "K74.60", ["간경변"]),
    ("hepatic_encephalopathy", "Hepatic Encephalopathy", "hepatology", "CRITICAL", "K72.90", ["간성 뇌증"]),
    ("spontaneous_bacterial_peritonitis", "Spontaneous Bacterial Peritonitis", "hepatology", "CRITICAL", "K65.2", ["sbp", "자발성 세균성 복막염"]),
    ("hepatitis_a", "Hepatitis A", "hepatology", "URGENT", "B15.9", ["a형 간염"]),
    ("hepatitis_b", "Hepatitis B", "hepatology", "URGENT", "B16.9", ["b형 간염"]),
    ("hepatitis_c", "Hepatitis C", "hepatology", "URGENT", "B17.10", ["c형 간염"]),
    ("alcoholic_hepatitis", "Alcoholic Hepatitis", "hepatology", "URGENT", "K70.10", ["알코올성 간염"]),
    ("nafld", "Non-Alcoholic Fatty Liver Disease", "hepatology", "ROUTINE", "K76.0", ["nafld", "비알코올성 지방간"]),
    ("hepatocellular_carcinoma", "Hepatocellular Carcinoma", "hepatology", "URGENT", "C22.0", ["hcc", "간세포암"]),
    ("primary_biliary_cholangitis", "Primary Biliary Cholangitis", "hepatology", "ROUTINE", "K74.3", ["pbc", "원발성 담즙성 담관염"]),
    ("wilson_disease", "Wilson Disease", "hepatology", "URGENT", "E83.01", ["윌슨병"]),
    ("hemochromatosis", "Hereditary Hemochromatosis", "hepatology", "ROUTINE", "E83.110", ["혈색소증"]),
    ("portal_vein_thrombosis", "Portal Vein Thrombosis", "hepatology", "URGENT", "I81", ["문맥 혈전증"]),
]

NEPHROLOGY_EXTRA: C = [
    ("glomerulonephritis", "Acute Glomerulonephritis", "nephrology", "URGENT", "N05.9", ["사구체신염"]),
    ("nephrotic_syndrome", "Nephrotic Syndrome", "nephrology", "URGENT", "N04.9", ["신증후군"]),
    ("ckd_stage5", "End-Stage Renal Disease", "nephrology", "URGENT", "N18.6", ["esrd", "말기 신부전"]),
    ("hyperkalemia", "Hyperkalemia", "nephrology", "CRITICAL", "E87.5", ["고칼륨혈증"]),
    ("hyponatremia", "Hyponatremia", "nephrology", "URGENT", "E87.1", ["저나트륨혈증"]),
    ("hypernatremia", "Hypernatremia", "nephrology", "URGENT", "E87.0", ["고나트륨혈증"]),
    ("hypokalemia", "Hypokalemia", "nephrology", "URGENT", "E87.6", ["저칼륨혈증"]),
    ("metabolic_acidosis", "Metabolic Acidosis", "nephrology", "URGENT", "E87.2", ["대사성 산증"]),
    ("metabolic_alkalosis", "Metabolic Alkalosis", "nephrology", "URGENT", "E87.3", ["대사성 알칼리증"]),
    ("rhabdomyolysis_renal", "Rhabdomyolysis", "nephrology", "URGENT", "M62.82", ["횡문근융해증"]),
    ("polycystic_kidney_disease", "Polycystic Kidney Disease", "nephrology", "ROUTINE", "Q61.3", ["pkd", "다낭성 신질환"]),
    ("renal_tubular_acidosis", "Renal Tubular Acidosis", "nephrology", "ROUTINE", "N25.89", ["신세뇨관 산증"]),
    ("contrast_induced_nephropathy", "Contrast-Induced Nephropathy", "nephrology", "URGENT", "N14.11", ["조영제 신병증"]),
    ("hemolytic_uremic_syndrome", "Hemolytic Uremic Syndrome", "nephrology", "CRITICAL", "D59.30", ["hus", "용혈성 요독 증후군"]),
]

UROLOGY_EXTRA: C = [
    ("urinary_retention", "Acute Urinary Retention", "urology", "URGENT", "R33.8", ["요폐"]),
    ("renal_cell_carcinoma", "Renal Cell Carcinoma", "urology", "URGENT", "C64.9", ["rcc", "신세포암"]),
    ("bladder_cancer", "Bladder Cancer", "urology", "URGENT", "C67.9", ["방광암"]),
    ("prostate_cancer", "Prostate Cancer", "urology", "URGENT", "C61", ["전립선암"]),
    ("benign_prostatic_hyperplasia", "Benign Prostatic Hyperplasia", "urology", "ROUTINE", "N40.0", ["bph", "전립선 비대증"]),
    ("priapism", "Priapism", "urology", "CRITICAL", "N48.30", ["지속발기증"]),
    ("fournier_gangrene", "Fournier Gangrene", "urology", "CRITICAL", "N49.3", ["푸르니에 괴저"]),
    ("hydronephrosis", "Hydronephrosis", "urology", "URGENT", "N13.30", ["수신증"]),
    ("interstitial_cystitis", "Interstitial Cystitis", "urology", "ROUTINE", "N30.10", ["간질성 방광염"]),
    ("varicocele", "Varicocele", "urology", "ROUTINE", "I86.1", ["정계정맥류"]),
]

ENDOCRINOLOGY_EXTRA: C = [
    ("siadh", "Syndrome of Inappropriate ADH", "endocrine_metabolic", "URGENT", "E22.2", ["siadh", "항이뇨호르몬 부적절 분비 증후군"]),
    ("cushing_syndrome", "Cushing Syndrome", "endocrine_metabolic", "ROUTINE", "E24.9", ["쿠싱 증후군"]),
    ("addison_disease", "Addison Disease (Primary Adrenal Insufficiency)", "endocrine_metabolic", "URGENT", "E27.1", ["애디슨병"]),
    ("pheochromocytoma", "Pheochromocytoma", "endocrine_metabolic", "URGENT", "E27.5", ["갈색세포종"]),
    ("hyperparathyroidism", "Primary Hyperparathyroidism", "endocrine_metabolic", "ROUTINE", "E21.0", ["부갑상선 기능항진증"]),
    ("hypoparathyroidism", "Hypoparathyroidism", "endocrine_metabolic", "URGENT", "E20.9", ["부갑상선 기능저하증"]),
    ("diabetes_insipidus", "Diabetes Insipidus", "endocrine_metabolic", "URGENT", "E23.2", ["요붕증"]),
    ("hypoglycemia_severe", "Severe Hypoglycemia", "endocrine_metabolic", "CRITICAL", "E16.2", ["중증 저혈당"]),
    ("acromegaly", "Acromegaly", "endocrine_metabolic", "ROUTINE", "E22.0", ["말단비대증"]),
    ("hypopituitarism", "Hypopituitarism", "endocrine_metabolic", "URGENT", "E23.0", ["뇌하수체 기능저하증"]),
    ("thyroid_nodule", "Thyroid Nodule", "endocrine_metabolic", "ROUTINE", "E04.1", ["갑상선 결절"]),
    ("subacute_thyroiditis", "Subacute Thyroiditis", "endocrine_metabolic", "ROUTINE", "E06.1", ["아급성 갑상선염"]),
    ("primary_aldosteronism", "Primary Aldosteronism", "endocrine_metabolic", "ROUTINE", "E26.09", ["원발성 알도스테론증"]),
]

METABOLIC_GENETIC_EXTRA: C = [
    ("phenylketonuria", "Phenylketonuria", "metabolic", "URGENT", "E70.0", ["pku", "페닐케톤뇨증"]),
    ("galactosemia", "Galactosemia", "metabolic", "URGENT", "E74.21", ["갈락토스혈증"]),
    ("maple_syrup_urine_disease", "Maple Syrup Urine Disease", "metabolic", "CRITICAL", "E71.0", ["msud", "단풍당뇨증"]),
    ("glycogen_storage_disease", "Glycogen Storage Disease", "metabolic", "URGENT", "E74.00", ["당원병"]),
    ("fabry_disease", "Fabry Disease", "metabolic", "ROUTINE", "E75.21", ["파브리병"]),
    ("gaucher_disease", "Gaucher Disease", "metabolic", "ROUTINE", "E75.22", ["고셰병"]),
    ("tay_sachs_disease", "Tay-Sachs Disease", "metabolic", "URGENT", "E75.02", ["테이-삭스병"]),
    ("porphyria_acute", "Acute Intermittent Porphyria", "metabolic", "URGENT", "E80.21", ["급성 간헐성 포르피린증"]),
    ("g6pd_deficiency", "G6PD Deficiency", "metabolic", "URGENT", "D55.0", ["g6pd 결핍증"]),
    ("mitochondrial_myopathy", "Mitochondrial Myopathy", "metabolic", "URGENT", "G71.3", ["미토콘드리아 근병증"]),
    ("marfan_syndrome", "Marfan Syndrome", "genetics", "URGENT", "Q87.40", ["마르판 증후군"]),
    ("ehlers_danlos_syndrome", "Ehlers-Danlos Syndrome", "genetics", "ROUTINE", "Q79.60", ["엘러스-단로스 증후군"]),
    ("down_syndrome", "Down Syndrome", "genetics", "ROUTINE", "Q90.9", ["다운 증후군"]),
    ("turner_syndrome", "Turner Syndrome", "genetics", "ROUTINE", "Q96.9", ["터너 증후군"]),
    ("neurofibromatosis", "Neurofibromatosis", "genetics", "ROUTINE", "Q85.00", ["신경섬유종증"]),
    ("cystic_fibrosis_genetic", "Cystic Fibrosis (Genetic)", "genetics", "URGENT", "E84.9", ["낭성 섬유증"]),
    ("sickle_cell_disease", "Sickle Cell Disease", "genetics", "URGENT", "D57.1", ["겸상 적혈구병"]),
    ("hereditary_angioedema", "Hereditary Angioedema", "genetics", "CRITICAL", "D84.1", ["유전성 혈관부종"]),
]

INFECTIOUS_EXTRA: C = [
    ("influenza", "Influenza", "infectious", "URGENT", "J11.1", ["flu", "인플루엔자", "독감"]),
    ("covid19", "COVID-19", "infectious", "URGENT", "U07.1", ["sars-cov-2", "코로나19"]),
    ("tuberculosis_pulmonary", "Pulmonary Tuberculosis", "infectious", "URGENT", "A15.0", ["tb", "폐결핵"]),
    ("cellulitis", "Cellulitis", "infectious", "URGENT", "L03.90", ["봉와직염"]),
    ("necrotizing_fasciitis", "Necrotizing Fasciitis", "infectious", "CRITICAL", "M72.6", ["괴사성 근막염"]),
    ("osteomyelitis", "Osteomyelitis", "infectious", "URGENT", "M86.9", ["골수염"]),
    ("septic_arthritis", "Septic Arthritis", "infectious", "CRITICAL", "M00.9", ["화농성 관절염"]),
    ("infectious_diarrhea", "Infectious Diarrhea", "infectious", "URGENT", "A09", ["감염성 설사"]),
    ("c_difficile_colitis", "Clostridioides difficile Colitis", "infectious", "URGENT", "A04.7", ["c diff", "위막성 대장염"]),
    ("malaria", "Malaria", "infectious", "CRITICAL", "B54", ["말라리아"]),
    ("dengue_fever", "Dengue Fever", "infectious", "URGENT", "A90", ["뎅기열"]),
    ("typhoid_fever", "Typhoid Fever", "infectious", "URGENT", "A01.00", ["장티푸스"]),
    ("lyme_disease", "Lyme Disease", "infectious", "URGENT", "A69.20", ["라임병"]),
    ("hiv_infection", "HIV Infection", "infectious", "URGENT", "B20", ["hiv", "인간면역결핍바이러스"]),
    ("infectious_mononucleosis", "Infectious Mononucleosis", "infectious", "ROUTINE", "B27.90", ["ebv", "전염성 단핵구증"]),
    ("herpes_zoster", "Herpes Zoster (Shingles)", "infectious", "URGENT", "B02.9", ["대상포진"]),
    ("measles", "Measles", "infectious", "URGENT", "B05.9", ["홍역"]),
    ("mumps", "Mumps", "infectious", "URGENT", "B26.9", ["볼거리"]),
    ("rubella", "Rubella", "infectious", "URGENT", "B06.9", ["풍진"]),
    ("varicella", "Varicella (Chickenpox)", "infectious", "URGENT", "B01.9", ["수두"]),
    ("scarlet_fever", "Scarlet Fever", "infectious", "URGENT", "A38.9", ["성홍열"]),
    ("tetanus", "Tetanus", "infectious", "CRITICAL", "A35", ["파상풍"]),
    ("rabies", "Rabies", "infectious", "CRITICAL", "A82.9", ["광견병"]),
    ("leptospirosis", "Leptospirosis", "infectious", "URGENT", "A27.9", ["렙토스피라증"]),
    ("brucellosis", "Brucellosis", "infectious", "URGENT", "A23.9", ["브루셀라증"]),
    ("candidemia", "Candidemia (Invasive Candidiasis)", "infectious", "CRITICAL", "B37.7", ["칸디다 혈증"]),
    ("toxic_shock_syndrome", "Toxic Shock Syndrome", "infectious", "CRITICAL", "A48.3", ["독성 쇼크 증후군"]),
    ("epiglottitis_inf", "Acute Epiglottitis", "infectious", "CRITICAL", "J05.10", ["후두개염"]),
]

HEMATOLOGY_EXTRA: C = [
    ("iron_deficiency_anemia", "Iron Deficiency Anemia", "hematology", "ROUTINE", "D50.9", ["철결핍성 빈혈"]),
    ("b12_deficiency", "Vitamin B12 Deficiency Anemia", "hematology", "ROUTINE", "D51.9", ["b12 결핍성 빈혈"]),
    ("folate_deficiency", "Folate Deficiency Anemia", "hematology", "ROUTINE", "D52.9", ["엽산 결핍성 빈혈"]),
    ("hemolytic_anemia", "Hemolytic Anemia", "hematology", "URGENT", "D59.9", ["용혈성 빈혈"]),
    ("aplastic_anemia", "Aplastic Anemia", "hematology", "URGENT", "D61.9", ["재생불량성 빈혈"]),
    ("thalassemia", "Thalassemia", "hematology", "ROUTINE", "D56.9", ["지중해빈혈"]),
    ("itp", "Immune Thrombocytopenic Purpura", "hematology", "URGENT", "D69.3", ["itp", "면역 혈소판감소성 자반증"]),
    ("ttp", "Thrombotic Thrombocytopenic Purpura", "hematology", "CRITICAL", "M31.19", ["ttp", "혈전성 혈소판감소성 자반증"]),
    ("dic", "Disseminated Intravascular Coagulation", "hematology", "CRITICAL", "D65", ["파종성 혈관내 응고"]),
    ("neutropenic_fever", "Neutropenic Fever", "hematology", "CRITICAL", "D70.9", ["호중구감소성 발열"]),
    ("hemophilia", "Hemophilia", "hematology", "URGENT", "D66", ["혈우병"]),
    ("von_willebrand_disease", "Von Willebrand Disease", "hematology", "ROUTINE", "D68.0", ["폰빌레브란트병"]),
    ("polycythemia_vera", "Polycythemia Vera", "hematology", "URGENT", "D45", ["진성 적혈구증가증"]),
    ("essential_thrombocythemia", "Essential Thrombocythemia", "hematology", "URGENT", "D47.3", ["본태성 혈소판증가증"]),
    ("myelodysplastic_syndrome", "Myelodysplastic Syndrome", "hematology", "URGENT", "D46.9", ["mds", "골수형성이상 증후군"]),
]

ONCOLOGY_EXTRA: C = [
    ("acute_myeloid_leukemia", "Acute Myeloid Leukemia", "oncology", "CRITICAL", "C92.00", ["aml", "급성 골수성 백혈병"]),
    ("acute_lymphoblastic_leukemia", "Acute Lymphoblastic Leukemia", "oncology", "CRITICAL", "C91.00", ["all", "급성 림프모구 백혈병"]),
    ("chronic_myeloid_leukemia", "Chronic Myeloid Leukemia", "oncology", "URGENT", "C92.10", ["cml", "만성 골수성 백혈병"]),
    ("chronic_lymphocytic_leukemia", "Chronic Lymphocytic Leukemia", "oncology", "URGENT", "C91.10", ["cll", "만성 림프구성 백혈병"]),
    ("hodgkin_lymphoma", "Hodgkin Lymphoma", "oncology", "URGENT", "C81.90", ["호지킨 림프종"]),
    ("non_hodgkin_lymphoma", "Non-Hodgkin Lymphoma", "oncology", "URGENT", "C85.90", ["비호지킨 림프종"]),
    ("multiple_myeloma", "Multiple Myeloma", "oncology", "URGENT", "C90.00", ["다발성 골수종"]),
    ("tumor_lysis_syndrome", "Tumor Lysis Syndrome", "oncology", "CRITICAL", "E88.3", ["tls", "종양용해 증후군"]),
    ("spinal_cord_compression_malig", "Malignant Spinal Cord Compression", "oncology", "CRITICAL", "G95.20", ["악성 척수 압박"]),
    ("svc_syndrome", "Superior Vena Cava Syndrome", "oncology", "URGENT", "I87.1", ["상대정맥 증후군"]),
    ("breast_cancer", "Breast Cancer", "oncology", "URGENT", "C50.919", ["유방암"]),
    ("ovarian_cancer", "Ovarian Cancer", "oncology", "URGENT", "C56.9", ["난소암"]),
    ("cervical_cancer", "Cervical Cancer", "oncology", "URGENT", "C53.9", ["자궁경부암"]),
    ("thyroid_cancer", "Thyroid Cancer", "oncology", "URGENT", "C73", ["갑상선암"]),
    ("melanoma", "Malignant Melanoma", "oncology", "URGENT", "C43.9", ["흑색종"]),
    ("malignant_hypercalcemia", "Hypercalcemia of Malignancy", "oncology", "CRITICAL", "E83.52", ["악성 고칼슘혈증"]),
]

RHEUMATOLOGY_IMMUNOLOGY_EXTRA: C = [
    ("systemic_lupus", "Systemic Lupus Erythematosus", "rheumatology", "URGENT", "M32.9", ["sle", "루푸스"]),
    ("rheumatoid_arthritis", "Rheumatoid Arthritis", "rheumatology", "URGENT", "M06.9", ["ra", "류마티스 관절염"]),
    ("polymyalgia_rheumatica", "Polymyalgia Rheumatica", "rheumatology", "URGENT", "M35.3", ["pmr", "류마티스성 다발근통"]),
    ("scleroderma", "Systemic Sclerosis (Scleroderma)", "rheumatology", "URGENT", "M34.9", ["전신 경화증"]),
    ("sjogren_syndrome", "Sjogren Syndrome", "rheumatology", "ROUTINE", "M35.00", ["쇼그렌 증후군"]),
    ("dermatomyositis", "Dermatomyositis", "rheumatology", "URGENT", "M33.90", ["피부근염"]),
    ("polymyositis", "Polymyositis", "rheumatology", "URGENT", "M33.20", ["다발근염"]),
    ("ankylosing_spondylitis", "Ankylosing Spondylitis", "rheumatology", "ROUTINE", "M45.9", ["강직성 척추염"]),
    ("psoriatic_arthritis", "Psoriatic Arthritis", "rheumatology", "ROUTINE", "L40.50", ["건선성 관절염"]),
    ("gout", "Gout", "rheumatology", "URGENT", "M10.9", ["통풍"]),
    ("pseudogout", "Pseudogout (CPPD)", "rheumatology", "URGENT", "M11.20", ["가성통풍"]),
    ("gca", "Giant Cell Arteritis", "rheumatology", "CRITICAL", "M31.6", ["측두동맥염"]),
    ("granulomatosis_polyangiitis", "Granulomatosis with Polyangiitis", "rheumatology", "URGENT", "M31.30", ["gpa", "베게너 육아종증"]),
    ("polyarteritis_nodosa", "Polyarteritis Nodosa", "rheumatology", "URGENT", "M30.0", ["결절성 다발동맥염"]),
    ("behcet_disease", "Behcet Disease", "rheumatology", "URGENT", "M35.2", ["베체트병"]),
    ("reactive_arthritis", "Reactive Arthritis", "rheumatology", "ROUTINE", "M02.9", ["반응성 관절염"]),
    ("antiphospholipid_syndrome", "Antiphospholipid Syndrome", "immunology", "URGENT", "D68.61", ["aps", "항인지질 증후군"]),
    ("common_variable_immunodeficiency", "Common Variable Immunodeficiency", "immunology", "URGENT", "D83.9", ["cvid"]),
    ("sarcoidosis_rheum", "Sarcoidosis (Systemic)", "rheumatology", "ROUTINE", "D86.9", ["유육종증"]),
]

ALLERGY_EXTRA: C = [
    ("allergic_rhinitis", "Allergic Rhinitis", "allergy", "ROUTINE", "J30.9", ["알레르기 비염"]),
    ("food_allergy", "Food Allergy", "allergy", "URGENT", "Z91.018", ["식품 알레르기"]),
    ("drug_allergy", "Drug Allergy", "allergy", "URGENT", "T88.7XXA", ["약물 알레르기"]),
    ("angioedema_allergy", "Allergic Angioedema", "allergy", "CRITICAL", "T78.3XXA", ["혈관부종"]),
    ("atopic_dermatitis", "Atopic Dermatitis", "allergy", "ROUTINE", "L20.9", ["아토피 피부염"]),
    ("contact_dermatitis", "Allergic Contact Dermatitis", "allergy", "ROUTINE", "L23.9", ["접촉성 피부염"]),
    ("eosinophilic_esophagitis", "Eosinophilic Esophagitis", "allergy", "ROUTINE", "K20.0", ["호산구성 식도염"]),
]

DERMATOLOGY_EXTRA: C = [
    ("stevens_johnson_syndrome", "Stevens-Johnson Syndrome", "dermatology", "CRITICAL", "L51.1", ["sjs", "스티븐스-존슨 증후군"]),
    ("toxic_epidermal_necrolysis", "Toxic Epidermal Necrolysis", "dermatology", "CRITICAL", "L51.2", ["ten", "독성 표피 괴사용해"]),
    ("erythema_multiforme", "Erythema Multiforme", "dermatology", "URGENT", "L51.9", ["다형 홍반"]),
    ("dress_syndrome", "DRESS Syndrome", "dermatology", "CRITICAL", "L27.0", ["약물반응 호산구증가 전신증상"]),
    ("psoriasis", "Psoriasis", "dermatology", "ROUTINE", "L40.9", ["건선"]),
    ("pemphigus_vulgaris", "Pemphigus Vulgaris", "dermatology", "URGENT", "L10.0", ["천포창"]),
    ("bullous_pemphigoid", "Bullous Pemphigoid", "dermatology", "URGENT", "L12.0", ["수포성 유천포창"]),
    ("cellulitis_derm", "Skin Cellulitis", "dermatology", "URGENT", "L03.90", ["피부 봉와직염"]),
    ("erysipelas", "Erysipelas", "dermatology", "URGENT", "A46", ["단독"]),
    ("urticaria", "Urticaria", "dermatology", "ROUTINE", "L50.9", ["두드러기"]),
    ("melanoma_derm", "Cutaneous Melanoma", "dermatology", "URGENT", "C43.9", ["피부 흑색종"]),
    ("basal_cell_carcinoma", "Basal Cell Carcinoma", "dermatology", "ROUTINE", "C44.91", ["기저세포암"]),
    ("squamous_cell_carcinoma_skin", "Cutaneous Squamous Cell Carcinoma", "dermatology", "URGENT", "C44.92", ["편평세포암"]),
    ("scabies", "Scabies", "dermatology", "ROUTINE", "B86", ["옴"]),
    ("herpes_simplex", "Herpes Simplex", "dermatology", "ROUTINE", "B00.9", ["단순 포진"]),
]

PSYCHIATRY_EXTRA: C = [
    ("major_depressive_disorder", "Major Depressive Disorder", "psychiatric", "URGENT", "F32.9", ["우울증"]),
    ("bipolar_disorder", "Bipolar Disorder", "psychiatric", "URGENT", "F31.9", ["양극성 장애"]),
    ("generalized_anxiety_disorder", "Generalized Anxiety Disorder", "psychiatric", "ROUTINE", "F41.1", ["범불안장애"]),
    ("schizophrenia", "Schizophrenia", "psychiatric", "URGENT", "F20.9", ["조현병"]),
    ("acute_psychosis", "Acute Psychosis", "psychiatric", "URGENT", "F23", ["급성 정신병"]),
    ("suicidal_ideation", "Suicidal Ideation", "psychiatric", "CRITICAL", "R45.851", ["자살 사고"]),
    ("alcohol_withdrawal", "Alcohol Withdrawal Syndrome", "psychiatric", "CRITICAL", "F10.239", ["delirium tremens", "알코올 금단"]),
    ("serotonin_syndrome", "Serotonin Syndrome", "psychiatric", "CRITICAL", "T43.225A", ["세로토닌 증후군"]),
    ("neuroleptic_malignant_syndrome", "Neuroleptic Malignant Syndrome", "psychiatric", "CRITICAL", "G21.0", ["nms", "신경이완제 악성 증후군"]),
    ("panic_disorder", "Panic Disorder", "psychiatric", "ROUTINE", "F41.0", ["공황장애"]),
    ("ptsd", "Post-Traumatic Stress Disorder", "psychiatric", "ROUTINE", "F43.10", ["외상후 스트레스 장애"]),
    ("anorexia_nervosa", "Anorexia Nervosa", "psychiatric", "URGENT", "F50.00", ["신경성 식욕부진증"]),
    ("catatonia", "Catatonia", "psychiatric", "URGENT", "F06.1", ["긴장증"]),
]

TOXICOLOGY_EXTRA: C = [
    ("acetaminophen_toxicity", "Acetaminophen Toxicity", "toxicology", "CRITICAL", "T39.1X1A", ["아세트아미노펜 중독"]),
    ("opioid_toxicity", "Opioid Toxicity", "toxicology", "CRITICAL", "T40.2X1A", ["아편유사제 중독"]),
    ("benzodiazepine_toxicity", "Benzodiazepine Toxicity", "toxicology", "URGENT", "T42.4X1A", ["벤조디아제핀 중독"]),
    ("carbon_monoxide_poisoning", "Carbon Monoxide Poisoning", "toxicology", "CRITICAL", "T58.91XA", ["일산화탄소 중독"]),
    ("organophosphate_poisoning", "Organophosphate Poisoning", "toxicology", "CRITICAL", "T60.0X1A", ["유기인계 중독"]),
    ("salicylate_toxicity", "Salicylate Toxicity", "toxicology", "CRITICAL", "T39.011A", ["살리실산 중독"]),
    ("tricyclic_overdose", "Tricyclic Antidepressant Overdose", "toxicology", "CRITICAL", "T43.011A", ["삼환계 항우울제 중독"]),
    ("methanol_poisoning", "Methanol Poisoning", "toxicology", "CRITICAL", "T51.1X1A", ["메탄올 중독"]),
    ("ethylene_glycol_poisoning", "Ethylene Glycol Poisoning", "toxicology", "CRITICAL", "T52.8X1A", ["에틸렌글리콜 중독"]),
    ("digoxin_toxicity", "Digoxin Toxicity", "toxicology", "CRITICAL", "T46.0X1A", ["디곡신 중독"]),
    ("lithium_toxicity", "Lithium Toxicity", "toxicology", "URGENT", "T43.591A", ["리튬 중독"]),
    ("iron_overdose", "Iron Overdose", "toxicology", "CRITICAL", "T45.4X1A", ["철분 과다복용"]),
    ("beta_blocker_overdose", "Beta-Blocker Overdose", "toxicology", "CRITICAL", "T44.7X1A", ["베타차단제 중독"]),
    ("calcium_channel_blocker_overdose", "Calcium Channel Blocker Overdose", "toxicology", "CRITICAL", "T46.1X1A", ["칼슘차단제 중독"]),
    ("cyanide_poisoning", "Cyanide Poisoning", "toxicology", "CRITICAL", "T57.3X1A", ["시안화물 중독"]),
]

ENVIRONMENTAL_EXTRA: C = [
    ("heat_stroke", "Heat Stroke", "environmental", "CRITICAL", "T67.0XXA", ["열사병"]),
    ("hypothermia", "Hypothermia", "environmental", "CRITICAL", "T68.XXXA", ["저체온증"]),
    ("frostbite", "Frostbite", "environmental", "URGENT", "T33.90XA", ["동상"]),
    ("high_altitude_pulmonary_edema", "High-Altitude Pulmonary Edema", "environmental", "CRITICAL", "T70.29XA", ["hape", "고산성 폐부종"]),
    ("decompression_sickness", "Decompression Sickness", "environmental", "CRITICAL", "T70.3XXA", ["잠수병"]),
    ("drowning", "Drowning / Submersion Injury", "environmental", "CRITICAL", "T75.1XXA", ["익수"]),
    ("electrical_injury", "Electrical Injury", "environmental", "CRITICAL", "T75.4XXA", ["전기 손상"]),
    ("anaphylaxis_env", "Anaphylaxis (Envenomation)", "environmental", "CRITICAL", "T63.91XA", ["교상 아나필락시스"]),
]

OBSTETRICS_EXTRA: C = [
    ("preeclampsia", "Preeclampsia", "obstetric", "CRITICAL", "O14.90", ["전자간증"]),
    ("eclampsia", "Eclampsia", "obstetric", "CRITICAL", "O15.9", ["자간증"]),
    ("hellp_syndrome", "HELLP Syndrome", "obstetric", "CRITICAL", "O14.20", ["헬프 증후군"]),
    ("placental_abruption", "Placental Abruption", "obstetric", "CRITICAL", "O45.90", ["태반조기박리"]),
    ("placenta_previa", "Placenta Previa", "obstetric", "CRITICAL", "O44.10", ["전치태반"]),
    ("postpartum_hemorrhage", "Postpartum Hemorrhage", "obstetric", "CRITICAL", "O72.1", ["산후 출혈"]),
    ("hyperemesis_gravidarum", "Hyperemesis Gravidarum", "obstetric", "URGENT", "O21.0", ["임신오조"]),
    ("gestational_diabetes", "Gestational Diabetes", "obstetric", "ROUTINE", "O24.419", ["임신성 당뇨"]),
    ("miscarriage", "Miscarriage (Spontaneous Abortion)", "obstetric", "URGENT", "O03.9", ["유산"]),
    ("chorioamnionitis", "Chorioamnionitis", "obstetric", "CRITICAL", "O41.1030", ["융모양막염"]),
    ("amniotic_fluid_embolism", "Amniotic Fluid Embolism", "obstetric", "CRITICAL", "O88.13", ["양수 색전증"]),
    ("preterm_labor", "Preterm Labor", "obstetric", "URGENT", "O60.00", ["조기 진통"]),
    ("gestational_trophoblastic_disease", "Gestational Trophoblastic Disease", "obstetric", "URGENT", "O01.9", ["포상기태"]),
]

GYNECOLOGY_EXTRA: C = [
    ("ovarian_torsion", "Ovarian Torsion", "gynecology", "CRITICAL", "N83.51", ["난소 염전"]),
    ("pelvic_inflammatory_disease", "Pelvic Inflammatory Disease", "gynecology", "URGENT", "N73.9", ["pid", "골반염"]),
    ("endometriosis", "Endometriosis", "gynecology", "ROUTINE", "N80.9", ["자궁내막증"]),
    ("ruptured_ovarian_cyst", "Ruptured Ovarian Cyst", "gynecology", "URGENT", "N83.20", ["난소낭종 파열"]),
    ("uterine_fibroids", "Uterine Fibroids", "gynecology", "ROUTINE", "D25.9", ["자궁근종"]),
    ("dysfunctional_uterine_bleeding", "Abnormal Uterine Bleeding", "gynecology", "URGENT", "N93.9", ["비정상 자궁출혈"]),
    ("tubo_ovarian_abscess", "Tubo-Ovarian Abscess", "gynecology", "CRITICAL", "N70.93", ["난관난소 농양"]),
    ("bartholin_abscess", "Bartholin Gland Abscess", "gynecology", "URGENT", "N75.1", ["바르톨린선 농양"]),
    ("endometrial_cancer", "Endometrial Cancer", "gynecology", "URGENT", "C54.1", ["자궁내막암"]),
]

PEDIATRICS_EXTRA: C = [
    ("croup", "Croup (Laryngotracheobronchitis)", "pediatric", "URGENT", "J05.0", ["크룹"]),
    ("epiglottitis_peds", "Pediatric Epiglottitis", "pediatric", "CRITICAL", "J05.10", ["소아 후두개염"]),
    ("bronchiolitis", "Bronchiolitis", "pediatric", "URGENT", "J21.9", ["세기관지염"]),
    ("kawasaki_disease", "Kawasaki Disease", "pediatric", "URGENT", "M30.3", ["가와사키병"]),
    ("febrile_seizure", "Febrile Seizure", "pediatric", "URGENT", "R56.00", ["열성 경련"]),
    ("pediatric_sepsis", "Pediatric Sepsis", "pediatric", "CRITICAL", "A41.9", ["소아 패혈증"]),
    ("intussusception", "Intussusception", "pediatric", "CRITICAL", "K56.1", ["장중첩증"]),
    ("pyloric_stenosis", "Hypertrophic Pyloric Stenosis", "pediatric", "URGENT", "Q40.0", ["유문 협착증"]),
    ("febrile_infant", "Febrile Young Infant (<90 days)", "pediatric", "CRITICAL", "R50.9", ["영아 발열"]),
    ("neonatal_jaundice", "Neonatal Jaundice", "pediatric", "URGENT", "P59.9", ["신생아 황달"]),
    ("henoch_schonlein_purpura", "Henoch-Schonlein Purpura", "pediatric", "URGENT", "D69.0", ["hsp", "헤노흐-쇤라인 자반증"]),
    ("hand_foot_mouth_disease", "Hand-Foot-Mouth Disease", "pediatric", "ROUTINE", "B08.4", ["수족구병"]),
    ("rsv_infection", "Respiratory Syncytial Virus Infection", "pediatric", "URGENT", "B97.4", ["rsv 감염"]),
    ("congenital_heart_disease", "Congenital Heart Disease", "congenital", "URGENT", "Q24.9", ["선천성 심장병"]),
    ("neural_tube_defect", "Neural Tube Defect", "congenital", "URGENT", "Q00.0", ["신경관 결손"]),
    ("cleft_lip_palate", "Cleft Lip and Palate", "congenital", "ROUTINE", "Q37.9", ["구순구개열"]),
    ("hirschsprung_disease", "Hirschsprung Disease", "congenital", "URGENT", "Q43.1", ["히르슈슈프룽병"]),
    ("biliary_atresia", "Biliary Atresia", "congenital", "URGENT", "Q44.2", ["담도 폐쇄증"]),
]

ENT_EXTRA: C = [
    ("acute_otitis_media", "Acute Otitis Media", "ent", "ROUTINE", "H66.90", ["급성 중이염"]),
    ("otitis_externa", "Otitis Externa", "ent", "ROUTINE", "H60.90", ["외이도염"]),
    ("mastoiditis", "Mastoiditis", "ent", "URGENT", "H70.90", ["유양돌기염"]),
    ("acute_sinusitis", "Acute Sinusitis", "ent", "ROUTINE", "J01.90", ["급성 부비동염"]),
    ("peritonsillar_abscess", "Peritonsillar Abscess", "ent", "URGENT", "J36", ["편도주위 농양"]),
    ("retropharyngeal_abscess", "Retropharyngeal Abscess", "ent", "CRITICAL", "J39.0", ["후인두 농양"]),
    ("ludwig_angina", "Ludwig Angina", "ent", "CRITICAL", "K12.2", ["루드비히 안기나"]),
    ("epistaxis", "Epistaxis", "ent", "URGENT", "R04.0", ["비출혈"]),
    ("sudden_hearing_loss", "Sudden Sensorineural Hearing Loss", "ent", "URGENT", "H91.20", ["돌발성 난청"]),
    ("bppv_ent", "Benign Paroxysmal Positional Vertigo", "ent", "ROUTINE", "H81.10", ["bppv", "이석증"]),
    ("meniere_disease", "Meniere Disease", "ent", "ROUTINE", "H81.09", ["메니에르병"]),
    ("laryngeal_cancer", "Laryngeal Cancer", "ent", "URGENT", "C32.9", ["후두암"]),
    ("nasopharyngeal_cancer", "Nasopharyngeal Carcinoma", "ent", "URGENT", "C11.9", ["비인두암"]),
]

OPHTHALMOLOGY_EXTRA: C = [
    ("acute_angle_closure_glaucoma", "Acute Angle-Closure Glaucoma", "ophthalmology", "CRITICAL", "H40.219", ["급성 폐쇄각 녹내장"]),
    ("central_retinal_artery_occlusion", "Central Retinal Artery Occlusion", "ophthalmology", "CRITICAL", "H34.10", ["망막중심동맥 폐쇄"]),
    ("central_retinal_vein_occlusion", "Central Retinal Vein Occlusion", "ophthalmology", "URGENT", "H34.8110", ["망막중심정맥 폐쇄"]),
    ("retinal_detachment", "Retinal Detachment", "ophthalmology", "CRITICAL", "H33.20", ["망막 박리"]),
    ("orbital_cellulitis", "Orbital Cellulitis", "ophthalmology", "CRITICAL", "H05.019", ["안와 봉와직염"]),
    ("optic_neuritis", "Optic Neuritis", "ophthalmology", "URGENT", "H46.9", ["시신경염"]),
    ("uveitis", "Uveitis", "ophthalmology", "URGENT", "H20.9", ["포도막염"]),
    ("bacterial_keratitis", "Bacterial Keratitis", "ophthalmology", "URGENT", "H16.009", ["세균성 각막염"]),
    ("endophthalmitis", "Endophthalmitis", "ophthalmology", "CRITICAL", "H44.009", ["안내염"]),
    ("acute_conjunctivitis", "Acute Conjunctivitis", "ophthalmology", "ROUTINE", "H10.9", ["급성 결막염"]),
    ("diabetic_retinopathy", "Diabetic Retinopathy", "ophthalmology", "URGENT", "E11.319", ["당뇨망막병증"]),
    ("chemical_eye_burn", "Chemical Eye Injury", "ophthalmology", "CRITICAL", "T26.60XA", ["화학 안 손상"]),
]

ORTHOPEDICS_TRAUMA_EXTRA: C = [
    ("hip_fracture", "Hip Fracture", "orthopedics", "URGENT", "S72.009A", ["고관절 골절"]),
    ("open_fracture", "Open Fracture", "trauma", "CRITICAL", "T14.8", ["개방성 골절"]),
    ("compartment_syndrome", "Acute Compartment Syndrome", "orthopedics", "CRITICAL", "T79.A0XA", ["구획 증후군"]),
    ("septic_arthritis_ortho", "Septic Arthritis (Joint)", "orthopedics", "CRITICAL", "M00.9", ["화농성 관절염"]),
    ("cervical_spine_injury", "Cervical Spine Injury", "trauma", "CRITICAL", "S14.109A", ["경추 손상"]),
    ("pelvic_fracture", "Pelvic Fracture", "trauma", "CRITICAL", "S32.9XXA", ["골반 골절"]),
    ("rotator_cuff_tear", "Rotator Cuff Tear", "orthopedics", "ROUTINE", "M75.100", ["회전근개 파열"]),
    ("achilles_tendon_rupture", "Achilles Tendon Rupture", "orthopedics", "URGENT", "S86.011A", ["아킬레스건 파열"]),
    ("lumbar_disc_herniation", "Lumbar Disc Herniation", "orthopedics", "URGENT", "M51.26", ["요추 추간판 탈출증"]),
    ("cauda_equina_syndrome", "Cauda Equina Syndrome", "orthopedics", "CRITICAL", "G83.4", ["마미 증후군"]),
    ("osteoporotic_fracture", "Osteoporotic Vertebral Fracture", "orthopedics", "URGENT", "M80.08XA", ["골다공증성 척추 골절"]),
    ("traumatic_brain_injury", "Traumatic Brain Injury", "trauma", "CRITICAL", "S06.9X9A", ["외상성 뇌손상"]),
    ("hemorrhagic_shock", "Hemorrhagic Shock", "trauma", "CRITICAL", "R57.1", ["출혈성 쇼크"]),
    ("tension_pneumothorax_trauma", "Traumatic Tension Pneumothorax", "trauma", "CRITICAL", "S27.0XXA", ["긴장성 기흉"]),
    ("splenic_rupture", "Splenic Rupture", "trauma", "CRITICAL", "S36.09XA", ["비장 파열"]),
    ("dislocation_shoulder", "Shoulder Dislocation", "orthopedics", "URGENT", "S43.006A", ["어깨 탈구"]),
]

IMMUNOLOGY_EXTRA2: C = [
    ("selective_iga_deficiency", "Selective IgA Deficiency", "immunology", "ROUTINE", "D80.2", ["선택적 IgA 결핍"]),
    ("severe_combined_immunodeficiency", "Severe Combined Immunodeficiency", "immunology", "CRITICAL", "D81.9", ["scid", "중증 복합 면역결핍증"]),
    ("chronic_granulomatous_disease", "Chronic Granulomatous Disease", "immunology", "URGENT", "D71", ["만성 육아종병"]),
    ("hereditary_c1_inhibitor_deficiency", "C1 Esterase Inhibitor Deficiency", "immunology", "CRITICAL", "D84.1", ["c1 억제제 결핍"]),
    ("graft_versus_host_disease", "Graft-versus-Host Disease", "immunology", "CRITICAL", "D89.813", ["gvhd", "이식편대숙주병"]),
]

GYNECOLOGY_EXTRA2: C = [
    ("cervical_dysplasia", "Cervical Dysplasia", "gynecology", "ROUTINE", "N87.9", ["자궁경부 이형성증"]),
    ("polycystic_ovary_syndrome", "Polycystic Ovary Syndrome", "gynecology", "ROUTINE", "E28.2", ["pcos", "다낭성 난소 증후군"]),
    ("vulvovaginal_candidiasis", "Vulvovaginal Candidiasis", "gynecology", "ROUTINE", "B37.3", ["외음질 칸디다증"]),
    ("bacterial_vaginosis", "Bacterial Vaginosis", "gynecology", "ROUTINE", "N76.0", ["세균성 질증"]),
    ("uterine_prolapse", "Uterine Prolapse", "gynecology", "ROUTINE", "N81.4", ["자궁 탈출증"]),
]

ORTHOPEDICS_EXTRA2: C = [
    ("frozen_shoulder", "Adhesive Capsulitis (Frozen Shoulder)", "orthopedics", "ROUTINE", "M75.00", ["오십견"]),
    ("meniscal_tear", "Meniscal Tear", "orthopedics", "ROUTINE", "S83.209A", ["반월상 연골 파열"]),
    ("acl_tear", "Anterior Cruciate Ligament Tear", "orthopedics", "URGENT", "S83.519A", ["전십자인대 파열"]),
    ("plantar_fasciitis", "Plantar Fasciitis", "orthopedics", "ROUTINE", "M72.2", ["족저 근막염"]),
    ("osteoarthritis", "Osteoarthritis", "orthopedics", "ROUTINE", "M19.90", ["골관절염"]),
    ("stress_fracture", "Stress Fracture", "orthopedics", "URGENT", "M84.30XA", ["피로 골절"]),
]

CONGENITAL_EXTRA2: C = [
    ("tetralogy_of_fallot", "Tetralogy of Fallot", "congenital", "URGENT", "Q21.3", ["팔로4징"]),
    ("ventricular_septal_defect", "Ventricular Septal Defect", "congenital", "URGENT", "Q21.0", ["vsd", "심실중격결손"]),
    ("atrial_septal_defect", "Atrial Septal Defect", "congenital", "ROUTINE", "Q21.1", ["asd", "심방중격결손"]),
    ("coarctation_of_aorta", "Coarctation of the Aorta", "congenital", "URGENT", "Q25.1", ["대동맥 축착"]),
    ("esophageal_atresia", "Esophageal Atresia", "congenital", "CRITICAL", "Q39.0", ["식도 폐쇄증"]),
]

# All supplementary groups.
EXTRA_GROUPS = [
    IMMUNOLOGY_EXTRA2, GYNECOLOGY_EXTRA2, ORTHOPEDICS_EXTRA2, CONGENITAL_EXTRA2,
    CARDIOLOGY_EXTRA, VASCULAR_EXTRA, PULMONOLOGY_EXTRA, NEUROLOGY_EXTRA,
    GASTROENTEROLOGY_EXTRA, HEPATOLOGY_EXTRA, NEPHROLOGY_EXTRA, UROLOGY_EXTRA,
    ENDOCRINOLOGY_EXTRA, METABOLIC_GENETIC_EXTRA, INFECTIOUS_EXTRA, HEMATOLOGY_EXTRA,
    ONCOLOGY_EXTRA, RHEUMATOLOGY_IMMUNOLOGY_EXTRA, ALLERGY_EXTRA, DERMATOLOGY_EXTRA,
    PSYCHIATRY_EXTRA, TOXICOLOGY_EXTRA, ENVIRONMENTAL_EXTRA, OBSTETRICS_EXTRA,
    GYNECOLOGY_EXTRA, PEDIATRICS_EXTRA, ENT_EXTRA, OPHTHALMOLOGY_EXTRA,
    ORTHOPEDICS_TRAUMA_EXTRA,
]
