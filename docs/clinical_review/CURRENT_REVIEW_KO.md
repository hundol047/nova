# 최신 임상 검토 전달 자료

현재 검토자와 승인 기록은 없습니다. 아래 항목은 코드와 문헌을 읽은 엔지니어의 관찰입니다.

검토 대상 런타임: `fb4b69b72639c5fb5a90df54bad3dfc07443442d`. 핵심 34개 + 추가 8개 프로필 = 42개 카드.
Tier-2 1,246개 전체가 검토된다는 뜻은 아닙니다. 먼저 위험 규칙과 아래 6개 질문을 검토해 주세요.

기계 판독 자료: `../../artifacts/rights_and_review/clinical_review_packet.json`.
답변 양식: `../../artifacts/rights_and_review/clinician_response_template.json`.

의사 등 적절한 분야의 의료 전문가가 성명·자격 확인 근거·일자·이해관계·서명 근거와 검토 범위를 남겨야 합니다.
실제 환자 개인정보는 제출하지 않아도 됩니다. 판단은 APPROVE / CHANGES_REQUIRED / INSUFFICIENT_EVIDENCE 중 선택합니다.
각 항목에 문헌 URL·버전·절, 적용 대상과 예외, 권고 수정을 적어 주세요. 부분 검토는 부분 검토로만 집계합니다.

## 우선 검토 질문

### CR-01 — 진정수면제 의존과 사용장애의 구분 (HIGH)

용량 증가·금단·감량 어려움만으로 사용장애를 선택할 수 있음. 치료 중 생리적 의존과 사용장애의 동등성은 입증되지 않음.

처방대로 복용하던 환자의 금단을 사용장애로 단정하지 않는지, 기능 손상·조절 실패·유해 사용 조건과 명칭을 검토.

검토용 근거: https://www.nice.org.uk/guidance/ng215/chapter/Recommendations — NG215 1.2, 1.3, 1.5; 사용장애 진단 기준 자체를 제공하는 근거는 아님

### CR-02 — 갑상샘 비대는 확진 검사가 아님 (HIGH)

Hyperthyroidism confirmatory_findings에 diffuse goiter가 포함됨. Graves와 thyrotoxicosis 명칭 범위도 별도 검토 필요.

혈액검사 전 작업 가설과 확진을 구분하고, 미만성 비대만으로 원인 확진·확정 문구가 출력되는지 검토.

검토용 근거: https://www.niddk.nih.gov/health-information/endocrine-diseases/hyperthyroidism — How do doctors diagnose hyperthyroidism?

### CR-03 — 소아 성장속도와 사춘기 상태 (HIGH)

3≤나이<12에서 4~7 cm/year를 prepubertal로 투영하지만 실제 사춘기 단계는 확인하지 않음. 골연령 지연은 단독 확진이 아님.

성별·사춘기 단계·키 백분위·측정 간격·부모키·만성 질환을 검토하고 성장호르몬 결핍 과진단 가능성 확인.

검토용 근거: https://pedsendo.org/patient-resource/short-stature/ — What Kind of Growth Pattern is Atypical? / What Tests Might Be Used to Assess Your Child?

### CR-04 — 응급 전환과 부정·시간·가족 정보의 분리 (HIGH)

의식 저하와 단순 졸림, 현재 위험과 과거·가족·부정 소견은 서로 다른 근거임.

성인·영아·소아의 실제 위험 소견, 정상 재측정, (-)/(+/-), 가족 병력만 존재하는 상황을 각각 검토.

검토용 근거: 별도 근거 필요 — 기존 위험 규칙 원출처 미확정; 해당 전문 분야의 최신 근거 필요

### CR-05 — 추적 간격과 약물 계획 (MEDIUM)

1주·1~2주·3~6개월 간격은 일부 일반화한 개발 휴리스틱. 심한 금단·의식 저하 등에 일률적 추적 간격 적용은 부적절할 수 있음.

환자 상태별 추적 간격과 즉시 평가 예외, 임의 중단·증량 금지 및 치료 계획의 적용 대상을 검토.

검토용 근거: https://www.nice.org.uk/guidance/ng215/chapter/Recommendations — NG215 1.4, 1.5; 개별 간격의 검증을 의미하지 않음

### CR-06 — 시행 전 검사 계획과 실제 환자 근거의 분리 (HIGH)

검사 권고·질문·외부 배경 문서는 실제 환자의 양성 검사 결과가 아님.

감별·A/P·환자 설명이 같은 결정에 근거하는지, 시행되지 않은 검사·음성 근거가 확진 근거로 출력되는지 검토.

검토용 근거: 별도 근거 필요 — 실제 전문가 판독 및 독립 사례 필요; 합성 테스트는 검토 완료 증거가 아님

## 포함된 프로필

| 유형 | ID | 이름 |
|---|---|---|
| core_profile | `acute_abdomen` | Acute Abdomen (Surgical Abdomen) |
| core_profile | `gi_bleeding` | Gastrointestinal Bleeding |
| core_profile | `ectopic_pregnancy` | Ectopic Pregnancy |
| core_profile | `acute_pancreatitis` | Acute Pancreatitis |
| core_profile | `appendicitis` | Acute Appendicitis |
| core_profile | `gastroenteritis` | Acute Gastroenteritis |
| core_profile | `acute_coronary_syndrome` | Acute Coronary Syndrome |
| core_profile | `aortic_dissection` | Aortic Dissection |
| core_profile | `gerd` | Gastroesophageal Reflux Disease |
| core_profile | `musculoskeletal_chest_pain` | Musculoskeletal Chest Pain (Costochondritis) |
| core_profile | `vasovagal_syncope` | Vasovagal (Reflex) Syncope |
| core_profile | `cardiac_arrhythmia` | Cardiac Arrhythmia (e.g. Atrial Fibrillation, SVT) |
| core_profile | `panic_attack` | Panic Attack |
| core_profile | `diabetic_ketoacidosis` | Diabetic Ketoacidosis |
| core_profile | `severe_electrolyte_disorder` | Severe Electrolyte Disorder (e.g. Hyperkalemia/Hyponatremia) |
| core_profile | `hypoglycemia` | Hypoglycemia |
| core_profile | `uncomplicated_cystitis` | Uncomplicated Cystitis (Lower UTI) |
| core_profile | `pyelonephritis` | Acute Pyelonephritis |
| core_profile | `nephrolithiasis` | Nephrolithiasis (Kidney Stone) |
| core_profile | `sepsis` | Sepsis |
| core_profile | `anaphylaxis` | Anaphylaxis |
| core_profile | `viral_uri` | Viral Upper Respiratory Infection |
| core_profile | `ischemic_stroke` | Ischemic Stroke |
| core_profile | `subarachnoid_hemorrhage` | Subarachnoid Hemorrhage |
| core_profile | `meningitis` | Bacterial Meningitis |
| core_profile | `migraine` | Migraine |
| core_profile | `tension_headache` | Tension-Type Headache |
| core_profile | `bppv` | Benign Paroxysmal Positional Vertigo |
| core_profile | `orthostatic_hypotension` | Orthostatic Hypotension |
| core_profile | `pulmonary_embolism` | Pulmonary Embolism |
| core_profile | `tension_pneumothorax` | Tension Pneumothorax |
| core_profile | `pneumonia` | Community-Acquired Pneumonia |
| core_profile | `asthma_copd_exacerbation` | Asthma / COPD Exacerbation |
| core_profile | `acute_bronchitis` | Acute Bronchitis |
| supplemental_profile | `onto::tier2:hyperthyroidism` | Hyperthyroidism |
| supplemental_profile | `clinical:graves_disease` | Graves disease |
| supplemental_profile | `clinical:sedative_hypnotic_use_disorder` | Sedative-Hypnotic Use Disorder |
| supplemental_profile | `clinical:medication_related_hypersomnia` | Medication-related hypersomnia |
| supplemental_profile | `clinical:rebound_insomnia` | Rebound insomnia |
| supplemental_profile | `clinical:constitutional_growth_delay` | Constitutional growth delay |
| supplemental_profile | `clinical:familial_short_stature` | Familial short stature |
| supplemental_profile | `clinical:growth_hormone_deficiency` | Growth hormone deficiency |
