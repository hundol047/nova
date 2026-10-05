# NOVA 임상 검토 요청 자료

퓨처랩스 · 작성 기준: 2026-10-05

이 문서는 교수님께 검토를 요청하기 위한 자료입니다. 검토 완료·자문 참여·추천·승인을 의미하지 않습니다.
실제 환자 기록 제공은 필요하지 않습니다. 현재 규칙의 타당성, 빠진 위험 신호, 잘못된 확진 표현을 우선 검토해 주시면 됩니다.

## 검토 순서

1. 위험 질환의 누락 가능성, 음성 검사로 배제하는 조건, 필요한 최소 검사.
2. 증상·검사 소견이 해당 질환에 얼마나 특이적인지와 수치·단위·시간 조건.
3. 임신·소아·고령자·면역저하자 등 적용 범위와 예외.
4. 한국어·일본어 표현이 같은 임상 개념을 뜻하는지.

## 자료 해석 시 주의

- 아래 문구와 수치는 현재 코드의 내용이며, 검증된 진료지침이라는 뜻이 아닙니다.
- 연결된 공개 자료는 새로 찾은 검토용 근거 후보입니다. 기존 규칙의 원출처나 동등성을 입증하지 않습니다.
- 출처의 이용 허용, 내용의 의학적 타당성, 교수님의 검토 여부는 각각 별도로 기록합니다.
- 소프트웨어 시험과 합성 사례 정확도는 독립적인 임상 검증을 대신하지 않습니다.
- 특정 문구가 출처에 등장해도 부정·시간·대상·검사 조건을 검토하기 전에는 근거 확인 완료로 표시하지 않습니다.

## 작성 양식

검토자 성명: ______ / 전문 분야: ______ / 검토일: ______
수정 권고에는 근거 URL·문서명·버전·해당 절/쪽·적용 대상·예외를 함께 적어 주세요.
기계 판독 양식은 CLINICAL_REVIEW_FORM.json의 review 항목입니다. 서명 없이 자동 승인되지 않습니다.

## Acute Abdomen (Surgical Abdomen) — acute_abdomen

파일: `nova_agent/knowledge/diseases/abdominal_gi.json`
현재 코드 분류: urgency=CRITICAL, dangerous=True (미검토)

- 증상 특징: ["severe abdominal pain", "rebound tenderness", "guarding", "rigid abdomen", "fever"]
- 현재 확진 관련 소견: ["free air", "peritoneal signs on imaging", "perforation"]
- 위험 인자: ["prior abdominal surgery", "elderly age"]
- 최소 검사: ["ct_abdomen"]
- 위험 신호: ["rebound tenderness", "guarding", "rigid abdomen", "peritoneal signs"]
- 구별용 검사: ["cbc", "lipase", "ct_abdomen"]

검토용 출처 후보:

- [Peritoneal Disorders](https://medlineplus.gov/peritonealdisorders.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `peritonitis`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Acute Coronary Syndrome — acute_coronary_syndrome

파일: `nova_agent/knowledge/diseases/cardiac.json`
현재 코드 분류: urgency=CRITICAL, dangerous=True (미검토)

- 증상 특징: ["exertional chest pain", "substernal pressure", "radiates to arm or jaw", "diaphoresis", "nausea", "dyspnea on exertion", "left arm pain"]
- 현재 확진 관련 소견: ["ST elevation", "ST depression", "elevated troponin", "troponin elevated"]
- 위험 인자: ["hypertension", "diabetes", "smoking", "hyperlipidemia", "family history", "male over 45", "female over 55", "prior coronary disease"]
- 최소 검사: ["ecg", "troponin"]
- 위험 신호: ["diaphoresis", "radiating pain", "crushing", "pressure", "hypotension", "sweating"]
- 구별용 검사: ["ecg", "troponin", "cxr"]

검토용 출처 후보:

- [Heart Attack](https://medlineplus.gov/heartattack.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `MI`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Anaphylaxis — anaphylaxis

파일: `nova_agent/knowledge/diseases/infectious.json`
현재 코드 분류: urgency=CRITICAL, dangerous=True (미검토)

- 증상 특징: ["sudden onset urticaria", "facial swelling", "wheeze", "throat tightness", "hypotension", "recent allergen exposure"]
- 현재 확진 관련 소견: ["elevated tryptase"]
- 위험 인자: ["known allergy", "recent new medication", "insect sting", "food exposure"]
- 최소 검사: []
- 위험 신호: ["urticaria", "facial swelling", "throat tightness", "wheeze after exposure", "hypotension"]
- 구별용 검사: []

검토용 출처 후보:

- [Anaphylaxis](https://medlineplus.gov/anaphylaxis.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `Anaphylaxis`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Aortic Dissection — aortic_dissection

파일: `nova_agent/knowledge/diseases/cardiac.json`
현재 코드 분류: urgency=CRITICAL, dangerous=True (미검토)

- 증상 특징: ["tearing chest pain", "ripping pain", "pain radiates to back", "sudden onset severe pain", "pulse differential", "unequal blood pressure between arms"]
- 현재 확진 관련 소견: ["widened mediastinum", "dissection flap", "intimal flap"]
- 위험 인자: ["hypertension", "marfan syndrome", "bicuspid aortic valve", "cocaine use", "connective tissue disease"]
- 최소 검사: ["ct_aorta"]
- 위험 신호: ["tearing", "ripping", "sudden onset", "radiates to back", "pulse differential", "unequal blood pressure"]
- 구별용 검사: ["ct_aorta", "cxr", "ecg"]

검토용 출처 후보:

- [Aortic Aneurysm](https://medlineplus.gov/aorticaneurysm.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `Aortic Dissection`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Bacterial Meningitis — meningitis

파일: `nova_agent/knowledge/diseases/neuro.json`
현재 코드 분류: urgency=CRITICAL, dangerous=True (미검토)

- 증상 특징: ["fever", "neck stiffness", "photophobia", "headache", "altered mental status", "rash"]
- 현재 확진 관련 소견: ["CSF pleocytosis", "gram-negative diplococci", "gram-positive", "elevated white blood cell count"]
- 위험 인자: ["recent infection", "immunosuppression", "close contact exposure", "no vaccination"]
- 최소 검사: ["lumbar_puncture"]
- 위험 신호: ["neck stiffness", "photophobia", "petechial rash", "fever with headache", "altered mental status"]
- 구별용 검사: ["lumbar_puncture", "blood_culture", "cbc"]

검토용 출처 후보:

- [Meningitis](https://medlineplus.gov/meningitis.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `meningitis`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Cardiac Arrhythmia (e.g. Atrial Fibrillation, SVT) — cardiac_arrhythmia

파일: `nova_agent/knowledge/diseases/cardiac.json`
현재 코드 분류: urgency=MEDIUM, dangerous=True (미검토)

- 증상 특징: ["sudden onset palpitations", "irregular heartbeat", "racing heart", "associated lightheadedness", "known history of arrhythmia"]
- 현재 확진 관련 소견: ["irregularly irregular rhythm", "narrow complex tachycardia", "atrial fibrillation on ecg"]
- 위험 인자: ["hypertension", "structural heart disease", "hyperthyroidism", "excessive caffeine or stimulant use", "advanced age"]
- 최소 검사: []
- 위험 신호: ["hypotension", "syncope with palpitations", "chest pain with palpitations"]
- 구별용 검사: ["ecg", "bmp"]

검토용 출처 후보:

- [Arrhythmia](https://medlineplus.gov/arrhythmia.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `arrhythmia`와 문자 일치. 임상적 동등성 미확인.
- [Atrial Fibrillation](https://medlineplus.gov/atrialfibrillation.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `atrial fibrillation`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Diabetic Ketoacidosis — diabetic_ketoacidosis

파일: `nova_agent/knowledge/diseases/endocrine_metabolic.json`
현재 코드 분류: urgency=CRITICAL, dangerous=True (미검토)

- 증상 특징: ["polyuria", "polydipsia", "nausea and vomiting", "abdominal pain", "fruity breath odor", "kussmaul breathing", "confusion"]
- 현재 확진 관련 소견: ["large ketones", "metabolic acidosis", "kussmaul breathing"]
- 위험 인자: ["known diabetes", "missed insulin doses", "recent infection"]
- 최소 검사: ["glucose_point_of_care", "ketones"]
- 위험 신호: ["kussmaul breathing", "fruity breath", "confusion with known diabetes", "polyuria polydipsia"]
- 구별용 검사: ["glucose_point_of_care", "ketones", "abg", "bmp"]

검토용 출처 후보:

- 현재 묶음에서 정확한 이름 연결을 찾지 못했습니다. 별도 근거가 필요합니다.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Ectopic Pregnancy — ectopic_pregnancy

파일: `nova_agent/knowledge/diseases/abdominal_gi.json`
현재 코드 분류: urgency=CRITICAL, dangerous=True (미검토)

- 증상 특징: ["lower abdominal pain", "vaginal bleeding", "missed period", "unilateral pelvic pain", "dizziness"]
- 현재 확진 관련 소견: ["positive beta-hCG", "no intrauterine pregnancy", "adnexal mass"]
- 위험 인자: ["prior ectopic pregnancy", "pelvic inflammatory disease", "IUD use", "tubal surgery", "childbearing age female"]
- 최소 검사: ["beta_hcg", "pelvic_ultrasound"]
- 위험 신호: ["vaginal bleeding", "missed period", "unilateral pelvic pain", "hypotension", "syncope"]
- 구별용 검사: ["beta_hcg", "pelvic_ultrasound"]

검토용 출처 후보:

- [Ectopic Pregnancy](https://medlineplus.gov/ectopicpregnancy.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `Ectopic Pregnancy`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Gastrointestinal Bleeding — gi_bleeding

파일: `nova_agent/knowledge/diseases/abdominal_gi.json`
현재 코드 분류: urgency=CRITICAL, dangerous=True (미검토)

- 증상 특징: ["hematemesis", "melena", "hematochezia", "lightheadedness", "pallor", "tachycardia"]
- 현재 확진 관련 소견: ["positive fecal occult blood", "hemoglobin drop", "low hemoglobin"]
- 위험 인자: ["NSAID use", "anticoagulant use", "antiplatelet use", "liver disease", "peptic ulcer disease", "alcohol use"]
- 최소 검사: ["cbc"]
- 위험 신호: ["hematemesis", "melena", "hematochezia", "hypotension", "tachycardia", "pallor"]
- 구별용 검사: ["cbc", "fecal_occult_blood"]

검토용 출처 후보:

- [Gastrointestinal Bleeding](https://medlineplus.gov/gastrointestinalbleeding.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `Gastrointestinal Bleeding`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Ischemic Stroke — ischemic_stroke

파일: `nova_agent/knowledge/diseases/neuro.json`
현재 코드 분류: urgency=CRITICAL, dangerous=True (미검토)

- 증상 특징: ["sudden onset focal weakness", "facial droop", "slurred speech", "aphasia", "unilateral numbness", "sudden vision loss", "ataxia"]
- 현재 확진 관련 소견: ["acute infarct", "diffusion restriction"]
- 위험 인자: ["atrial fibrillation", "hypertension", "diabetes", "smoking", "prior stroke or TIA", "advanced age"]
- 최소 검사: ["ct_head", "glucose_point_of_care"]
- 위험 신호: ["facial droop", "slurred speech", "unilateral weakness", "sudden onset", "focal deficit"]
- 구별용 검사: ["ct_head", "mri_brain", "glucose_point_of_care"]

검토용 출처 후보:

- [Ischemic Stroke](https://medlineplus.gov/ischemicstroke.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `Ischemic Stroke`와 문자 일치. 임상적 동등성 미확인.
- [Stroke](https://medlineplus.gov/stroke.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `stroke`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Pulmonary Embolism — pulmonary_embolism

파일: `nova_agent/knowledge/diseases/pulmonary.json`
현재 코드 분류: urgency=CRITICAL, dangerous=True (미검토)

- 증상 특징: ["sudden onset dyspnea", "pleuritic chest pain", "tachycardia", "hemoptysis", "calf swelling", "unilateral leg pain"]
- 현재 확진 관련 소견: ["filling defect in the pulmonary artery", "elevated D-dimer"]
- 위험 인자: ["recent surgery", "immobilization", "long travel", "malignancy", "oral contraceptive use", "prior DVT or PE", "pregnancy"]
- 최소 검사: ["d_dimer", "ct_chest_angio"]
- 위험 신호: ["sudden onset dyspnea", "pleuritic", "calf swelling", "hemoptysis", "tachycardia", "hypoxia"]
- 구별용 검사: ["d_dimer", "ct_chest_angio", "ecg"]

검토용 출처 후보:

- [Pulmonary Embolism](https://medlineplus.gov/pulmonaryembolism.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `Pulmonary Embolism`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Sepsis — sepsis

파일: `nova_agent/knowledge/diseases/infectious.json`
현재 코드 분류: urgency=CRITICAL, dangerous=True (미검토)

- 증상 특징: ["fever", "tachycardia", "hypotension", "altered mental status", "tachypnea", "suspected infection source"]
- 현재 확진 관련 소견: ["positive blood culture", "gram-negative rods", "gram-positive cocci", "gram-negative diplococci"]
- 위험 인자: ["immunosuppression", "recent infection", "indwelling catheter", "advanced age", "diabetes"]
- 최소 검사: ["lactate", "blood_culture"]
- 위험 신호: ["hypotension", "tachycardia", "altered mental status", "tachypnea", "fever with confusion"]
- 구별용 검사: ["lactate", "blood_culture", "cbc", "bmp"]

검토용 출처 후보:

- [Sepsis](https://medlineplus.gov/sepsis.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `Sepsis`와 문자 일치. 임상적 동등성 미확인.
- [Shock](https://medlineplus.gov/shock.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `septic shock`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Severe Electrolyte Disorder (e.g. Hyperkalemia/Hyponatremia) — severe_electrolyte_disorder

파일: `nova_agent/knowledge/diseases/endocrine_metabolic.json`
현재 코드 분류: urgency=CRITICAL, dangerous=True (미검토)

- 증상 특징: ["muscle weakness", "palpitations", "confusion", "arrhythmia", "seizure"]
- 현재 확진 관련 소견: ["peaked t waves", "hyperkalemia", "elevated potassium", "hyponatremia", "low sodium", "widened qrs"]
- 위험 인자: ["chronic kidney disease", "diuretic use", "vomiting or diarrhea", "renin-angiotensin system inhibitor use"]
- 최소 검사: ["bmp"]
- 위험 신호: ["arrhythmia", "muscle weakness with renal disease", "confusion with renal disease"]
- 구별용 검사: ["bmp", "ecg"]

검토용 출처 후보:

- [Potassium](https://medlineplus.gov/potassium.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `hyperkalemia`와 문자 일치. 임상적 동등성 미확인.
- [Sodium](https://medlineplus.gov/sodium.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `hyponatremia`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Subarachnoid Hemorrhage — subarachnoid_hemorrhage

파일: `nova_agent/knowledge/diseases/neuro.json`
현재 코드 분류: urgency=CRITICAL, dangerous=True (미검토)

- 증상 특징: ["thunderclap headache", "worst headache of life", "sudden onset severe headache", "neck stiffness", "photophobia", "vomiting"]
- 현재 확진 관련 소견: ["subarachnoid blood", "xanthochromia"]
- 위험 인자: ["hypertension", "smoking", "family history of aneurysm", "polycystic kidney disease"]
- 최소 검사: ["ct_head"]
- 위험 신호: ["thunderclap", "worst headache of life", "sudden onset severe", "neck stiffness"]
- 구별용 검사: ["ct_head", "lumbar_puncture"]

검토용 출처 후보:

- [Hemorrhagic Stroke](https://medlineplus.gov/hemorrhagicstroke.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `Subarachnoid Hemorrhage`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Tension Pneumothorax — tension_pneumothorax

파일: `nova_agent/knowledge/diseases/pulmonary.json`
현재 코드 분류: urgency=CRITICAL, dangerous=True (미검토)

- 증상 특징: ["sudden onset dyspnea", "unilateral absent breath sounds", "tracheal deviation", "hypotension", "chest pain after trauma"]
- 현재 확진 관련 소견: ["absent breath sounds", "tracheal deviation"]
- 위험 인자: ["chest trauma", "tall thin body habitus", "COPD", "mechanical ventilation"]
- 최소 검사: ["lung_auscultation", "cxr"]
- 위험 신호: ["absent breath sounds", "tracheal deviation", "hypotension", "sudden onset dyspnea", "distended neck veins"]
- 구별용 검사: ["cxr"]

검토용 출처 후보:

- 현재 묶음에서 정확한 이름 연결을 찾지 못했습니다. 별도 근거가 필요합니다.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Acute Appendicitis — appendicitis

파일: `nova_agent/knowledge/diseases/abdominal_gi.json`
현재 코드 분류: urgency=MEDIUM, dangerous=False (미검토)

- 증상 특징: ["periumbilical pain migrating to right lower quadrant", "anorexia", "low grade fever", "nausea"]
- 현재 확진 관련 소견: ["inflamed appendix", "appendiceal wall thickening", "dilated appendix", "periappendiceal fat stranding", "appendicolith"]
- 위험 인자: ["young age"]
- 최소 검사: []
- 위험 신호: ["rebound tenderness", "guarding"]
- 구별용 검사: ["cbc", "ct_abdomen"]

검토용 출처 후보:

- [Appendicitis](https://medlineplus.gov/appendicitis.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `appendicitis`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Acute Bronchitis — acute_bronchitis

파일: `nova_agent/knowledge/diseases/pulmonary.json`
현재 코드 분류: urgency=LOW, dangerous=False (미검토)

- 증상 특징: ["productive cough", "mild fever", "no focal consolidation", "recent viral illness", "chest wall soreness from coughing"]
- 현재 확진 관련 소견: []
- 위험 인자: ["smoking", "recent viral upper respiratory infection"]
- 최소 검사: []
- 위험 신호: []
- 구별용 검사: ["cxr"]

검토용 출처 후보:

- [Acute Bronchitis](https://medlineplus.gov/acutebronchitis.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `Acute Bronchitis`와 문자 일치. 임상적 동등성 미확인.
- [Chronic Bronchitis](https://medlineplus.gov/chronicbronchitis.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `bronchitis`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Acute Gastroenteritis — gastroenteritis

파일: `nova_agent/knowledge/diseases/abdominal_gi.json`
현재 코드 분류: urgency=LOW, dangerous=False (미검토)

- 증상 특징: ["diffuse crampy abdominal pain", "diarrhea", "vomiting", "recent similar illness contact"]
- 현재 확진 관련 소견: []
- 위험 인자: ["recent travel", "sick contacts", "food exposure"]
- 최소 검사: []
- 위험 신호: []
- 구별용 검사: ["cbc"]

검토용 출처 후보:

- [Gastroenteritis](https://medlineplus.gov/gastroenteritis.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `gastroenteritis`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Acute Pancreatitis — acute_pancreatitis

파일: `nova_agent/knowledge/diseases/abdominal_gi.json`
현재 코드 분류: urgency=MEDIUM, dangerous=False (미검토)

- 증상 특징: ["epigastric pain radiating to back", "nausea", "vomiting", "worse after eating fatty food"]
- 현재 확진 관련 소견: ["elevated lipase", "pancreatic inflammation on imaging", "peripancreatic fat stranding"]
- 위험 인자: ["alcohol use", "gallstones", "hypertriglyceridemia"]
- 최소 검사: []
- 위험 신호: []
- 구별용 검사: ["lipase", "abdominal_ultrasound"]

검토용 출처 후보:

- [Pancreatitis](https://medlineplus.gov/pancreatitis.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `Acute Pancreatitis`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Acute Pyelonephritis — pyelonephritis

파일: `nova_agent/knowledge/diseases/genitourinary.json`
현재 코드 분류: urgency=MEDIUM, dangerous=False (미검토)

- 증상 특징: ["flank pain", "fever", "costovertebral angle tenderness", "dysuria", "nausea and vomiting"]
- 현재 확진 관련 소견: ["positive leukocyte esterase", "positive nitrites", "elevated white blood cell count"]
- 위험 인자: ["female sex", "diabetes", "urinary obstruction", "pregnancy"]
- 최소 검사: []
- 위험 신호: ["fever with flank pain", "hypotension", "confusion"]
- 구별용 검사: ["urinalysis", "urine_culture", "cbc", "bmp"]

검토용 출처 후보:

- [Urinary Tract Infections](https://medlineplus.gov/urinarytractinfections.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `pyelonephritis`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Asthma / COPD Exacerbation — asthma_copd_exacerbation

파일: `nova_agent/knowledge/diseases/pulmonary.json`
현재 코드 분류: urgency=MEDIUM, dangerous=False (미검토)

- 증상 특징: ["wheeze", "known asthma or COPD", "worse with triggers", "prolonged expiration"]
- 현재 확진 관련 소견: ["reduced peak flow", "hyperinflation on chest x-ray"]
- 위험 인자: ["smoking", "known reactive airway disease", "allergen exposure"]
- 최소 검사: []
- 위험 신호: ["silent chest", "unable to speak in full sentences", "hypoxia"]
- 구별용 검사: ["cxr", "abg"]

검토용 출처 후보:

- 현재 묶음에서 정확한 이름 연결을 찾지 못했습니다. 별도 근거가 필요합니다.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Benign Paroxysmal Positional Vertigo — bppv

파일: `nova_agent/knowledge/diseases/neuro.json`
현재 코드 분류: urgency=LOW, dangerous=False (미검토)

- 증상 특징: ["brief episodic vertigo", "triggered by head position change", "no focal neuro deficit", "no hearing loss"]
- 현재 확진 관련 소견: ["positive dix-hallpike", "positional nystagmus", "torsional nystagmus"]
- 위험 인자: ["prior episodes", "recent head trauma", "advanced age"]
- 최소 검사: []
- 위험 신호: []
- 구별용 검사: []

검토용 출처 후보:

- 현재 묶음에서 정확한 이름 연결을 찾지 못했습니다. 별도 근거가 필요합니다.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Community-Acquired Pneumonia — pneumonia

파일: `nova_agent/knowledge/diseases/pulmonary.json`
현재 코드 분류: urgency=MEDIUM, dangerous=False (미검토)

- 증상 특징: ["productive cough", "fever", "pleuritic chest pain", "crackles on auscultation", "dyspnea"]
- 현재 확진 관련 소견: ["consolidation", "infiltrate", "focal consolidation", "crackles"]
- 위험 인자: ["elderly age", "smoking", "COPD", "immunosuppression"]
- 최소 검사: []
- 위험 신호: ["hypoxia", "confusion", "hypotension"]
- 구별용 검사: ["cxr", "cbc"]

검토용 출처 후보:

- [Pneumonia](https://medlineplus.gov/pneumonia.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `pneumonia`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Gastroesophageal Reflux Disease — gerd

파일: `nova_agent/knowledge/diseases/cardiac.json`
현재 코드 분류: urgency=LOW, dangerous=False (미검토)

- 증상 특징: ["burning chest pain", "worse after meals", "worse lying down", "relieved by antacids", "sour taste"]
- 현재 확진 관련 소견: ["esophagitis on endoscopy"]
- 위험 인자: ["obesity", "hiatal hernia", "smoking"]
- 최소 검사: []
- 위험 신호: []
- 구별용 검사: ["ecg", "troponin"]

검토용 출처 후보:

- [GERD](https://medlineplus.gov/gerd.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `Gastroesophageal Reflux Disease`와 문자 일치. 임상적 동등성 미확인.
- [Heartburn](https://medlineplus.gov/heartburn.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `acid reflux`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Hypoglycemia — hypoglycemia

파일: `nova_agent/knowledge/diseases/endocrine_metabolic.json`
현재 코드 분류: urgency=MEDIUM, dangerous=False (미검토)

- 증상 특징: ["diaphoresis", "confusion", "tremor", "known diabetes on insulin", "resolves with glucose"]
- 현재 확진 관련 소견: []
- 위험 인자: ["insulin use", "sulfonylurea use", "missed meal"]
- 최소 검사: []
- 위험 신호: []
- 구별용 검사: ["glucose_point_of_care"]

검토용 출처 후보:

- [Hypoglycemia](https://medlineplus.gov/hypoglycemia.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `Hypoglycemia`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Migraine — migraine

파일: `nova_agent/knowledge/diseases/neuro.json`
현재 코드 분류: urgency=LOW, dangerous=False (미검토)

- 증상 특징: ["unilateral pulsating headache", "photophobia", "phonophobia", "nausea", "aura", "recurrent similar episodes"]
- 현재 확진 관련 소견: []
- 위험 인자: ["family history of migraine", "female sex", "known migraine history"]
- 최소 검사: []
- 위험 신호: []
- 구별용 검사: ["ct_head"]

검토용 출처 후보:

- [Migraine](https://medlineplus.gov/migraine.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `Migraine`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Musculoskeletal Chest Pain (Costochondritis) — musculoskeletal_chest_pain

파일: `nova_agent/knowledge/diseases/cardiac.json`
현재 코드 분류: urgency=LOW, dangerous=False (미검토)

- 증상 특징: ["reproducible with palpation", "worse with movement", "localized tenderness", "sharp pain"]
- 현재 확진 관련 소견: ["reproducible chest wall tenderness", "pain reproduced on palpation"]
- 위험 인자: ["recent physical strain", "recent trauma"]
- 최소 검사: []
- 위험 신호: []
- 구별용 검사: ["ecg"]

검토용 출처 후보:

- [Cartilage Disorders](https://medlineplus.gov/cartilagedisorders.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `costochondritis`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Nephrolithiasis (Kidney Stone) — nephrolithiasis

파일: `nova_agent/knowledge/diseases/genitourinary.json`
현재 코드 분류: urgency=MEDIUM, dangerous=False (미검토)

- 증상 특징: ["colicky flank pain", "pain radiates to groin", "hematuria", "nausea", "unable to find comfortable position"]
- 현재 확진 관련 소견: ["ureteral stone on imaging", "hydronephrosis", "blood in urine on urinalysis"]
- 위험 인자: ["prior kidney stones", "dehydration", "family history"]
- 최소 검사: []
- 위험 신호: []
- 구별용 검사: ["urinalysis", "ct_abdomen"]

검토용 출처 후보:

- [Kidney Stones](https://medlineplus.gov/kidneystones.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `nephrolithiasis`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Orthostatic Hypotension — orthostatic_hypotension

파일: `nova_agent/knowledge/diseases/neuro.json`
현재 코드 분류: urgency=LOW, dangerous=False (미검토)

- 증상 특징: ["lightheadedness on standing up", "improves with sitting or lying down", "no focal neurological deficit", "no chest pain", "no palpitations before the episode"]
- 현재 확진 관련 소견: ["orthostatic drop in blood pressure", "blood pressure falls on standing"]
- 위험 인자: ["dehydration", "diuretic use", "prolonged bed rest", "advanced age"]
- 최소 검사: []
- 위험 신호: []
- 구별용 검사: []

검토용 출처 후보:

- [Low Blood Pressure](https://medlineplus.gov/lowbloodpressure.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `Orthostatic Hypotension`와 문자 일치. 임상적 동등성 미확인.
- [Autonomic Nervous System Disorders](https://medlineplus.gov/autonomicnervoussystemdisorders.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `Orthostatic Hypotension`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Panic Attack — panic_attack

파일: `nova_agent/knowledge/diseases/cardiac.json`
현재 코드 분류: urgency=LOW, dangerous=False (미검토)

- 증상 특징: ["sudden onset intense anxiety or fear", "hyperventilation", "tingling around the mouth or fingers", "fear of dying or losing control", "chest tightness", "palpitations", "symptoms peak within minutes then improve", "resolves with calming down or reassurance"]
- 현재 확진 관련 소견: []
- 위험 인자: ["history of anxiety or panic disorder", "recent significant stressor"]
- 최소 검사: []
- 위험 신호: []
- 구별용 검사: ["ecg"]

검토용 출처 후보:

- 현재 묶음에서 정확한 이름 연결을 찾지 못했습니다. 별도 근거가 필요합니다.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Tension-Type Headache — tension_headache

파일: `nova_agent/knowledge/diseases/neuro.json`
현재 코드 분류: urgency=LOW, dangerous=False (미검토)

- 증상 특징: ["bilateral band-like pressure", "mild to moderate intensity", "no nausea", "stress related"]
- 현재 확진 관련 소견: []
- 위험 인자: ["stress", "poor sleep", "prolonged screen time"]
- 최소 검사: []
- 위험 신호: []
- 구별용 검사: []

검토용 출처 후보:

- [Headache](https://medlineplus.gov/headache.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `tension headache`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Uncomplicated Cystitis (Lower UTI) — uncomplicated_cystitis

파일: `nova_agent/knowledge/diseases/genitourinary.json`
현재 코드 분류: urgency=LOW, dangerous=False (미검토)

- 증상 특징: ["dysuria", "urinary frequency", "urinary urgency", "suprapubic discomfort", "no fever", "no flank pain"]
- 현재 확진 관련 소견: ["positive leukocyte esterase", "positive nitrites"]
- 위험 인자: ["female sex", "sexual activity", "prior UTI"]
- 최소 검사: []
- 위험 신호: []
- 구별용 검사: ["urinalysis", "urine_culture"]

검토용 출처 후보:

- [Urinary Tract Infections](https://medlineplus.gov/urinarytractinfections.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `UTI`와 문자 일치. 임상적 동등성 미확인.
- [Interstitial Cystitis](https://medlineplus.gov/interstitialcystitis.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `cystitis`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Vasovagal (Reflex) Syncope — vasovagal_syncope

파일: `nova_agent/knowledge/diseases/cardiac.json`
현재 코드 분류: urgency=LOW, dangerous=False (미검토)

- 증상 특징: ["prodrome of lightheadedness", "triggered by standing or pain or fear", "brief loss of consciousness", "rapid spontaneous recovery", "no chest pain", "no palpitations before the episode"]
- 현재 확진 관련 소견: []
- 위험 인자: ["prolonged standing", "dehydration", "emotional stress", "young age"]
- 최소 검사: []
- 위험 신호: []
- 구별용 검사: ["ecg"]

검토용 출처 후보:

- [Fainting](https://medlineplus.gov/fainting.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `vasovagal syncope`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________

## Viral Upper Respiratory Infection — viral_uri

파일: `nova_agent/knowledge/diseases/infectious.json`
현재 코드 분류: urgency=LOW, dangerous=False (미검토)

- 증상 특징: ["low grade fever", "rhinorrhea", "sore throat", "cough", "mild symptoms"]
- 현재 확진 관련 소견: []
- 위험 인자: ["sick contacts", "seasonal exposure"]
- 최소 검사: []
- 위험 신호: []
- 구별용 검사: []

검토용 출처 후보:

- [Common Cold](https://medlineplus.gov/commoncold.html) — 2026-10-03; Public-domain health-topic summaries; NLM scope-specific reuse terms; 기존 이름 `common cold`와 문자 일치. 임상적 동등성 미확인.

판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족
수정안 및 근거: ____________________
음성 결과만으로 배제하면 안 되는 상황: ____________________
대상 환자·시간·수치·검사법 예외: ____________________
