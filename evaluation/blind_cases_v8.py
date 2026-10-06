"""Blind evaluation set v8 (spec / steering sections 46-47: the untouched final generalization
check authored AFTER this pilot-readiness workstream's only reasoning-code change -- the
glucose unit-safety guard in nova_agent/glucose_evidence.py (Stage 4) -- was complete and
re-verified against held-out / generalization-v2 / stress via CI, and never adjusted afterward
regardless of its own first-run score).

Why v8 (not v7): no Blind v7 was ever authored in this workstream; Blind v6 was the prior round's
untouched set and is now reference-only. A fresh, untouched set is required because reasoning code
changed. This file follows the identical authoring discipline as blind_cases_v6.py:

Authoring rules followed (self-imposed, left here for a future session to audit):
  1. Written AFTER the Stage 4 glucose unit-safety fix was finished and CI-verified -- not before,
     not interleaved with it.
  2. No sentence, clause, or distinctive phrase copied from evaluation/cases.py,
     held_out_cases.py, generalization_cases_v2.py, generalization_stress_cases.py, or any
     blind_cases_v3/v4/v5/v6.py -- every vignette is written fresh, with a distinct mechanism /
     setting / demographic than any same-diagnosis case in an earlier file. In particular NOTHING
     here is keyed to a specific earlier miss (that would be exactly the leakage
     scripts/check_eval_leakage.py exists to catch).
  3. One fresh vignette per diagnosis in the 34-disease knowledge base, PLUS additional cases
     explicitly targeting, as their OWN axis (independent of which diagnosis they land on):
     multimorbidity, polypharmacy, pregnancy/pelvic, trauma, GI bleeding, atypical neurologic,
     atypical infection, metabolic derangement, conflicting findings, sparse information,
     negative-finding-centric presentation, benign mimic, dangerous mimic, stale-lab / wrong-unit
     data-freshness, and objective-lab-confirmed presentations -- and spread across ko / en / ja /
     zh / mixed-language input so the four-language canonical-equivalence behavior is exercised on
     genuinely blind vignettes, not translated reuse.
  4. Every case's ground_truth_diagnosis, category tag, and content was decided and frozen BEFORE
     running evaluation.blind_benchmark_v8 for the first time -- see evaluation/blind_v8_manifest.json
     for the file hash recorded at freeze time. This file is not edited after seeing that run's
     results, regardless of the score. A genuine pre-first-run correction would require a new
     manifest entry documenting why, never a silent edit.

72 cases. Hand-authored synthetic vignettes, never real patient data. Ground-truth ids are all
members of the 34-entry knowledge base.
"""

from __future__ import annotations

from evaluation.cases import SyntheticCase

BLIND_CASES_V8 = [
    # ============================================================================================
    # PART A -- one fresh vignette per knowledge-base diagnosis (34), spread across ko/en/ja/zh.
    # ============================================================================================

    # 1. acute_coronary_syndrome (en)
    SyntheticCase(
        case_id="Blind8_01_ShovelingSnowPressure", category="cardiac",
        chief_complaint="a heavy pressure clamped down on my chest while I was clearing the driveway",
        demographics={"age": 63, "sex": "male"},
        ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "came on with exertion about 40 minutes ago and hasn't fully let go",
                 "associated_symptoms": "sweaty, a little short of breath, ache down the left arm; denies fever",
                 "past_medical_history": "high cholesterol, father had a heart attack at 60"},
        exam_results={"vital_signs": "BP 152/94, HR 96, RR 20, Temp 36.9, SpO2 96%"},
        test_results={"ecg": "ST depression in the lateral leads", "troponin": "troponin elevated above the reference limit"},
    ),
    # 2. aortic_dissection (en)
    SyntheticCase(
        case_id="Blind8_02_TearingBetweenShoulderBlades", category="dangerous_mimic",
        chief_complaint="a sudden tearing pain ripped straight through to between my shoulder blades",
        demographics={"age": 68, "sex": "male"},
        ground_truth_diagnosis="aortic_dissection",
        answers={"onset": "maximal the instant it started, about an hour ago",
                 "character": "tearing, moving down toward my back; denies cough",
                 "past_medical_history": "long-standing poorly controlled hypertension"},
        exam_results={"vital_signs": "BP 188/70 right arm, 150/64 left arm, HR 100, RR 22, SpO2 97%",
                      "cardiovascular_exam": "faint early diastolic murmur, unequal radial pulses"},
        test_results={},
    ),
    # 3. pulmonary_embolism (ko)
    SyntheticCase(
        case_id="Blind8_03_LongHaulFlightPleuritic", category="cardiac",
        chief_complaint="장거리 비행 다음 날부터 갑자기 숨이 차고 숨 쉴 때 오른쪽 가슴이 찌르듯 아파요",
        demographics={"age": 45, "sex": "female"},
        ground_truth_diagnosis="pulmonary_embolism",
        answers={"onset": "어제 12시간 비행 후 오늘 아침 갑자기 시작됐어요",
                 "associated_symptoms": "왼쪽 종아리가 붓고 아파요; 발열은 없음, 기침 가래는 없음",
                 "medications": "경구 피임약 복용 중"},
        exam_results={"vital_signs": "BP 118/74, HR 112, RR 24, Temp 37.0, SpO2 91%",
                      "extremity_exam": "왼쪽 종아리 부종과 압통"},
        test_results={"d_dimer": "D-dimer markedly elevated"},
    ),
    # 4. tension_pneumothorax (en)
    SyntheticCase(
        case_id="Blind8_04_GymBarbellSuddenDyspnea", category="dangerous_mimic",
        chief_complaint="my chest suddenly caved in on one side and I can barely breathe after a heavy lift",
        demographics={"age": 24, "sex": "male"},
        ground_truth_diagnosis="tension_pneumothorax",
        answers={"onset": "sudden, right after a max deadlift ten minutes ago",
                 "associated_symptoms": "sharp right chest pain, getting more breathless fast; denies fever",
                 "past_medical_history": "tall and thin, smokes socially"},
        exam_results={"vital_signs": "BP 96/60, HR 128, RR 32, Temp 36.8, SpO2 86%",
                      "chest_exam": "absent breath sounds on the right, trachea deviated to the left, distended neck veins"},
        test_results={},
    ),
    # 5. pneumonia (ja)
    SyntheticCase(
        case_id="Blind8_05_ElderlyProductiveCough", category="infectious",
        chief_complaint="3日前から咳と黄色い痰が出て、熱と息苦しさもあります",
        demographics={"age": 74, "sex": "female"},
        ground_truth_diagnosis="pneumonia",
        answers={"duration": "3日前から徐々に悪化しています",
                 "associated_symptoms": "右胸の痛み、悪寒、食欲低下; めまいはない",
                 "past_medical_history": "軽い心不全があります"},
        exam_results={"vital_signs": "BP 128/78, HR 104, RR 26, Temp 38.7, SpO2 90%",
                      "chest_exam": "右下肺野に湿性ラ音、呼吸音低下"},
        test_results={"wbc": "leukocytosis, elevated white blood cell count", "chest_xray": "right lower lobe consolidation"},
    ),
    # 6. asthma_copd_exacerbation (en)
    SyntheticCase(
        case_id="Blind8_06_ColdSnapWheeze", category="pulmonary",
        chief_complaint="my wheezing and breathlessness flared up badly when the cold weather hit",
        demographics={"age": 58, "sex": "male"},
        ground_truth_diagnosis="asthma_copd_exacerbation",
        answers={"onset": "worsening over three days with the cold snap",
                 "associated_symptoms": "productive cough with clear-white sputum, chest tightness; denies fever, denies leg swelling",
                 "social_history": "40 pack-year smoker, uses an inhaler most days"},
        exam_results={"vital_signs": "BP 138/86, HR 100, RR 24, Temp 37.0, SpO2 92%",
                      "chest_exam": "diffuse expiratory wheeze, prolonged expiration"},
        test_results={},
    ),
    # 7. acute_bronchitis (zh)
    SyntheticCase(
        case_id="Blind8_07_PostColdLingeringCough", category="common",
        chief_complaint="感冒后咳嗽一直不好，已经咳了十天了",
        demographics={"age": 33, "sex": "female"},
        ground_truth_diagnosis="acute_bronchitis",
        answers={"duration": "感冒好了以后咳嗽还持续了十天",
                 "associated_symptoms": "偶尔有少量白痰，胸口有点发紧; 没有高热，没有呼吸困难, 没有咯血"},
        exam_results={"vital_signs": "BP 116/72, HR 78, RR 16, Temp 37.2, SpO2 98%",
                      "chest_exam": "偶闻散在干啰音，无实变体征"},
        test_results={},
    ),
    # 8. ischemic_stroke (ko)
    SyntheticCase(
        case_id="Blind8_08_MorningFacialDroop", category="neuro",
        chief_complaint="아침에 일어나 보니 오른쪽 얼굴이 처지고 말이 어눌해졌어요",
        demographics={"age": 71, "sex": "male"},
        ground_truth_diagnosis="ischemic_stroke",
        answers={"onset": "약 1시간 전 갑자기 발생, 계속 지속됨",
                 "associated_symptoms": "오른쪽 팔에 힘이 빠지고 물을 마실 때 사레가 들려요; 두통은 없음",
                 "past_medical_history": "심방세동, 당뇨"},
        exam_results={"vital_signs": "BP 172/96, HR 88 irregularly irregular, RR 16, Temp 36.9, SpO2 97%",
                      "neuro_exam": "right facial droop, right arm drift, dysarthria, no neck stiffness"},
        test_results={},
    ),
    # 9. subarachnoid_hemorrhage (en)
    SyntheticCase(
        case_id="Blind8_09_ThunderclapAtGym", category="dangerous_mimic",
        chief_complaint="the worst headache of my life exploded out of nowhere while I was lifting",
        demographics={"age": 49, "sex": "female"},
        ground_truth_diagnosis="subarachnoid_hemorrhage",
        answers={"onset": "instantly maximal about 30 minutes ago, like being hit in the back of the head",
                 "associated_symptoms": "vomited once, neck feels stiff, light hurts my eyes; denies weakness",
                 "past_medical_history": "smoker, sister had a brain aneurysm"},
        exam_results={"vital_signs": "BP 168/98, HR 92, RR 18, Temp 37.1, SpO2 98%",
                      "neuro_exam": "neck stiffness on flexion, no focal motor deficit, photophobia"},
        test_results={},
    ),
    # 10. meningitis (ja)
    SyntheticCase(
        case_id="Blind8_10_DormFeverStiffNeck", category="infectious",
        chief_complaint="高熱と激しい頭痛、首が硬くて曲げられません",
        demographics={"age": 20, "sex": "male"},
        ground_truth_diagnosis="meningitis",
        answers={"onset": "昨夜から急速に悪化しています",
                 "associated_symptoms": "光がまぶしい、吐き気、ぐったりしている; 手足の麻痺はない",
                 "social_history": "大学の寮で生活、周囲に似た症状の人がいる"},
        exam_results={"vital_signs": "BP 118/72, HR 116, RR 22, Temp 39.4, SpO2 97%",
                      "neuro_exam": "項部硬直あり、羞明、局所神経脱落なし"},
        test_results={},
    ),
    # 11. migraine (en, benign neuro)
    SyntheticCase(
        case_id="Blind8_11_AuraThenThrob", category="benign_mimic",
        chief_complaint="I get a shimmering zigzag in my vision and then a pounding headache on one side",
        demographics={"age": 30, "sex": "female"},
        ground_truth_diagnosis="migraine",
        answers={"onset": "the visual shimmer came first for 20 minutes, then the throbbing started, same as my usual episodes",
                 "associated_symptoms": "nauseated, bright light and noise make it worse; denies neck stiffness, denies weakness or slurred speech",
                 "past_medical_history": "diagnosed with migraine with aura in my twenties"},
        exam_results={"vital_signs": "BP 118/74, HR 72, RR 14, Temp 36.8, SpO2 99%",
                      "neuro_exam": "no focal neurological deficit, neck supple"},
        test_results={},
    ),
    # 12. tension_headache (zh, benign)
    SyntheticCase(
        case_id="Blind8_12_DeadlineBandHeadache", category="common",
        chief_complaint="最近赶项目，头两侧像被带子勒住一样闷痛",
        demographics={"age": 38, "sex": "male"},
        ground_truth_diagnosis="tension_headache",
        answers={"character": "两侧持续性压迫感，不是跳痛",
                 "aggravating": "工作压力大、久坐后加重; 没有恶心，没有畏光, 没有视力变化, 没有肢体无力"},
        exam_results={"vital_signs": "BP 122/78, HR 74, RR 14, Temp 36.7, SpO2 99%",
                      "neuro_exam": "神经系统检查正常，无局灶体征"},
        test_results={},
    ),
    # 13. bppv (en, benign vertigo)
    SyntheticCase(
        case_id="Blind8_13_RollingOverSpins", category="benign_mimic",
        chief_complaint="the room spins hard for about half a minute every time I roll over in bed",
        demographics={"age": 55, "sex": "female"},
        ground_truth_diagnosis="bppv",
        answers={"onset": "started two days ago, only with head position changes",
                 "associated_symptoms": "brief spinning, a little nausea with it; denies hearing loss, denies weakness, denies slurred speech, denies headache"},
        exam_results={"vital_signs": "BP 128/80, HR 76, RR 14, Temp 36.8, SpO2 99%",
                      "neuro_exam": "positional nystagmus on the Dix-Hallpike, otherwise normal, gait steady"},
        test_results={},
    ),
    # 14. vasovagal_syncope (ko, benign)
    SyntheticCase(
        case_id="Blind8_14_BloodDrawFaint", category="benign_mimic",
        chief_complaint="채혈하다가 속이 메스껍고 식은땀이 나더니 잠깐 정신을 잃었어요",
        demographics={"age": 26, "sex": "female"},
        ground_truth_diagnosis="vasovagal_syncope",
        answers={"onset": "채혈 도중 서 있다가 쓰러졌고 금방 깨어났어요",
                 "associated_symptoms": "쓰러지기 전 메스꺼움과 식은땀, 시야가 좁아짐; 가슴 두근거림 없음, 흉통 없음, 발작 없음",
                 "past_medical_history": "예전에도 주사 맞을 때 비슷하게 실신한 적 있음"},
        exam_results={"vital_signs": "BP 118/72, HR 70, RR 14, Temp 36.7, SpO2 99%",
                      "cardiovascular_exam": "정상 심음, 기립 시 어지럼 재현되지 않음"},
        test_results={"ecg": "normal sinus rhythm"},
    ),
    # 15. orthostatic_hypotension (en)
    SyntheticCase(
        case_id="Blind8_15_NewBPMedDizzyStanding", category="metabolic",
        chief_complaint="I get lightheaded and my vision grays out every time I stand up quickly",
        demographics={"age": 72, "sex": "male"},
        ground_truth_diagnosis="orthostatic_hypotension",
        answers={"onset": "started a few days after my doctor added a new blood-pressure pill",
                 "associated_symptoms": "only when standing, resolves when I sit back down; denies chest pain, denies palpitations, denies loss of consciousness",
                 "medications": "recently started a diuretic and an ACE inhibitor"},
        exam_results={"vital_signs": "BP 132/80 lying, 104/64 standing with a 22-point drop, HR 78 to 92 on standing, SpO2 98%"},
        test_results={},
    ),
    # 16. cardiac_arrhythmia (ja)
    SyntheticCase(
        case_id="Blind8_16_SuddenPalpitations", category="cardiac",
        chief_complaint="突然心臓がバクバクして、めまいと息苦しさがあります",
        demographics={"age": 66, "sex": "female"},
        ground_truth_diagnosis="cardiac_arrhythmia",
        answers={"onset": "1時間前に急に始まり、脈が速くて不規則です",
                 "associated_symptoms": "軽い胸の違和感とふらつき; 発熱はない, 咳はない",
                 "past_medical_history": "高血圧、甲状腺機能亢進の既往"},
        exam_results={"vital_signs": "BP 108/70, HR 148 irregularly irregular, RR 20, Temp 36.9, SpO2 96%",
                      "cardiovascular_exam": "不整な頻脈、雑音なし"},
        test_results={"ecg": "atrial fibrillation with rapid ventricular response"},
    ),
    # 17. musculoskeletal_chest_pain (en, benign)
    SyntheticCase(
        case_id="Blind8_17_MovedFurnitureChestWall", category="benign_mimic",
        chief_complaint="my chest is sore right over one spot ever since I helped move furniture",
        demographics={"age": 34, "sex": "male"},
        ground_truth_diagnosis="musculoskeletal_chest_pain",
        answers={"onset": "since lifting a heavy couch yesterday",
                 "character": "sharp, reproducible when I press on it or twist; denies sweating, denies shortness of breath, denies radiation to the arm"},
        exam_results={"vital_signs": "BP 124/78, HR 72, RR 14, Temp 36.8, SpO2 99%",
                      "chest_exam": "point tenderness over the left costochondral junction, pain reproduced by palpation"},
        test_results={"ecg": "normal sinus rhythm, no ischemic changes"},
    ),
    # 18. gerd (zh, benign)
    SyntheticCase(
        case_id="Blind8_18_NightBurningReflux", category="common",
        chief_complaint="晚上躺下后胸口烧灼感，嘴里泛酸水",
        demographics={"age": 44, "sex": "male"},
        ground_truth_diagnosis="gerd",
        answers={"onset": "最近几周，尤其吃夜宵后加重",
                 "associated_symptoms": "平躺加重，坐起来缓解，有反酸; 没有出汗, 没有气短, 运动时不加重"},
        exam_results={"vital_signs": "BP 126/80, HR 74, RR 14, Temp 36.7, SpO2 99%"},
        test_results={"ecg": "normal sinus rhythm"},
    ),
    # 19. appendicitis (en)
    SyntheticCase(
        case_id="Blind8_19_MigratingRLQPain", category="abdominal",
        chief_complaint="my belly ache started around my navel and has moved to the lower right and gotten sharper",
        demographics={"age": 22, "sex": "male"},
        ground_truth_diagnosis="appendicitis",
        answers={"onset": "started around the belly button yesterday, now sharp in the right lower belly",
                 "associated_symptoms": "no appetite, nauseated, low-grade fever, worse when the car hits a bump; denies diarrhea",
                 "past_medical_history": "none"},
        exam_results={"vital_signs": "BP 124/78, HR 96, RR 16, Temp 37.9, SpO2 99%",
                      "abdominal_exam": "tenderness and guarding at McBurney's point, rebound tenderness"},
        test_results={"wbc": "elevated white blood cell count"},
    ),
    # 20. acute_pancreatitis (ko)
    SyntheticCase(
        case_id="Blind8_20_BingeDrinkEpigastric", category="abdominal",
        chief_complaint="어제 과음한 뒤부터 명치 통증이 등까지 뻗치고 계속 토해요",
        demographics={"age": 47, "sex": "male"},
        ground_truth_diagnosis="acute_pancreatitis",
        answers={"onset": "어제 폭음 후 밤부터 심해졌어요",
                 "character": "명치에서 등 쪽으로 뚫는 듯한 통증, 앞으로 숙이면 조금 나아요",
                 "associated_symptoms": "구역 구토 반복; 설사 없음, 흉통 없음",
                 "social_history": "주 5회 음주"},
        exam_results={"vital_signs": "BP 110/70, HR 108, RR 20, Temp 37.8, SpO2 97%",
                      "abdominal_exam": "상복부 압통, 장음 감소"},
        test_results={"lipase": "lipase markedly elevated, over three times the upper limit"},
    ),
    # 21. acute_abdomen (en, surgical peritonitis)
    SyntheticCase(
        case_id="Blind8_21_RigidBoardBelly", category="dangerous_mimic",
        chief_complaint="my whole belly is rigid and any movement makes the pain unbearable",
        demographics={"age": 60, "sex": "male"},
        ground_truth_diagnosis="acute_abdomen",
        answers={"onset": "sudden severe pain a few hours ago, now the whole abdomen",
                 "associated_symptoms": "can't get comfortable, feverish, hasn't passed gas; denies chest pain",
                 "past_medical_history": "peptic ulcer disease, takes daily NSAIDs for arthritis"},
        exam_results={"vital_signs": "BP 104/66, HR 118, RR 24, Temp 38.3, SpO2 97%",
                      "abdominal_exam": "board-like rigidity, diffuse rebound and guarding, absent bowel sounds"},
        test_results={},
    ),
    # 22. gi_bleeding (ja)
    SyntheticCase(
        case_id="Blind8_22_BlackTarryStools", category="gi_bleeding",
        chief_complaint="黒くてタール状の便が続いて、立ちくらみがします",
        demographics={"age": 69, "sex": "male"},
        ground_truth_diagnosis="gi_bleeding",
        answers={"onset": "2日前から黒い便が出ています",
                 "associated_symptoms": "ふらつき、疲れやすい; 鮮血の嘔吐はない, 発熱はない",
                 "medications": "心房細動のため抗凝固薬を服用、痛み止めも時々"},
        exam_results={"vital_signs": "BP 98/62, HR 112, RR 18, Temp 36.8, SpO2 98%",
                      "abdominal_exam": "軽度心窩部圧痛、直腸診で黒色便"},
        test_results={"hemoglobin": "hemoglobin low at 8.1 g/dL"},
    ),
    # 23. gastroenteritis (zh, benign)
    SyntheticCase(
        case_id="Blind8_23_SharedHotpotDiarrhea", category="common",
        chief_complaint="昨天吃了火锅，今天上吐下泻，肚子绞痛",
        demographics={"age": 29, "sex": "female"},
        ground_truth_diagnosis="gastroenteritis",
        answers={"onset": "昨晚聚餐后大约半天开始",
                 "associated_symptoms": "水样腹泻，呕吐几次，阵发绞痛; 大便没有血, 没有高热, 没有剧烈局部压痛",
                 "social_history": "同桌另一个朋友也拉肚子"},
        exam_results={"vital_signs": "BP 112/70, HR 92, RR 16, Temp 37.5, SpO2 99%",
                      "abdominal_exam": "全腹轻压痛，肠鸣音活跃，无反跳痛"},
        test_results={},
    ),
    # 24. nephrolithiasis (en)
    SyntheticCase(
        case_id="Blind8_24_ColickyFlankToGroin", category="abdominal",
        chief_complaint="a wave of agonizing pain in my left flank keeps shooting down toward my groin",
        demographics={"age": 41, "sex": "male"},
        ground_truth_diagnosis="nephrolithiasis",
        answers={"onset": "came in waves starting this morning, can't find a comfortable position",
                 "associated_symptoms": "nauseated, pink-tinged urine; denies fever, denies chills, denies diarrhea",
                 "past_medical_history": "had a kidney stone two years ago"},
        exam_results={"vital_signs": "BP 142/88, HR 96, RR 18, Temp 36.9, SpO2 99%",
                      "abdominal_exam": "left costovertebral angle tenderness, soft abdomen"},
        test_results={"urinalysis": "microscopic hematuria, no nitrites, no leukocyte esterase"},
    ),
    # 25. uncomplicated_cystitis (ko, benign)
    SyntheticCase(
        case_id="Blind8_25_DysuriaFrequency", category="common",
        chief_complaint="이틀 전부터 소변 볼 때 아프고 자주 마려워요",
        demographics={"age": 28, "sex": "female"},
        ground_truth_diagnosis="uncomplicated_cystitis",
        answers={"onset": "이틀 전부터",
                 "associated_symptoms": "배뇨통, 빈뇨, 잔뇨감; 옆구리 통증 없음, 발열 없음, 오한 없음",
                 "past_medical_history": "특이 병력 없음"},
        exam_results={"vital_signs": "BP 118/74, HR 74, RR 14, Temp 36.9, SpO2 99%",
                      "abdominal_exam": "치골 상부 경미한 압통, 늑골척추각 압통 없음"},
        test_results={"urinalysis": "positive leukocyte esterase and nitrites"},
    ),
    # 26. pyelonephritis (en)
    SyntheticCase(
        case_id="Blind8_26_FlankPainRigorsFever", category="infectious",
        chief_complaint="my lower back on one side aches badly and I've been shaking with fever and chills",
        demographics={"age": 35, "sex": "female"},
        ground_truth_diagnosis="pyelonephritis",
        answers={"onset": "urinary burning for three days, then high fever and back pain today",
                 "associated_symptoms": "nausea, rigors, painful urination; denies vaginal bleeding",
                 "past_medical_history": "recurrent bladder infections"},
        exam_results={"vital_signs": "BP 116/72, HR 108, RR 20, Temp 39.1, SpO2 98%",
                      "abdominal_exam": "marked right costovertebral angle tenderness"},
        test_results={"urinalysis": "pyuria, positive nitrites", "wbc": "leukocytosis"},
    ),
    # 27. ectopic_pregnancy (en, pelvic)
    SyntheticCase(
        case_id="Blind8_27_MissedPeriodPelvicPain", category="pregnancy",
        chief_complaint="I have sharp one-sided pelvic pain and some spotting, and my period is late",
        demographics={"age": 29, "sex": "female"},
        ground_truth_diagnosis="ectopic_pregnancy",
        answers={"onset": "pelvic pain started yesterday, sharp on the right",
                 "associated_symptoms": "light vaginal spotting, a bit lightheaded; denies diarrhea, denies urinary symptoms",
                 "last_menstrual_period": "about seven weeks ago, then a missed period"},
        exam_results={"vital_signs": "BP 104/66, HR 104, RR 18, Temp 37.0, SpO2 99%",
                      "abdominal_exam": "right lower quadrant tenderness, cervical motion tenderness"},
        test_results={"beta_hcg": "urine pregnancy test positive"},
    ),
    # 28. diabetic_ketoacidosis (en, metabolic, objective-lab-confirmed, mg/dL)
    SyntheticCase(
        case_id="Blind8_28_ThirstyPolyuriaKussmaul", category="metabolic",
        chief_complaint="I've been unbelievably thirsty, peeing constantly, and now I'm nauseated and breathing hard",
        demographics={"age": 19, "sex": "male"},
        ground_truth_diagnosis="diabetic_ketoacidosis",
        answers={"onset": "worsening over two days, ran out of my insulin",
                 "associated_symptoms": "abdominal pain, vomiting, deep rapid breathing; denies chest pain",
                 "past_medical_history": "type 1 diabetes"},
        exam_results={"vital_signs": "BP 108/68, HR 118, RR 30 and deep, Temp 37.2, SpO2 99%",
                      "general_exam": "dry mucous membranes, fruity breath odor"},
        test_results={"glucose_point_of_care": "blood glucose 512 mg/dL",
                      "ketones": "serum ketones strongly positive", "bicarbonate": "bicarbonate 9 mEq/L"},
    ),
    # 29. hypoglycemia (en, metabolic, mg/dL numeric)
    SyntheticCase(
        case_id="Blind8_29_SkippedMealSweatyConfused", category="metabolic",
        chief_complaint="my elderly father suddenly got sweaty, shaky and confused before dinner",
        demographics={"age": 78, "sex": "male"},
        ground_truth_diagnosis="hypoglycemia",
        answers={"onset": "came on over 20 minutes after he skipped lunch",
                 "associated_symptoms": "diaphoretic, tremulous, confused, better with juice; denies chest pain, denies focal weakness",
                 "medications": "takes glipizide for diabetes"},
        exam_results={"vital_signs": "BP 138/82, HR 98, RR 16, Temp 36.8, SpO2 98%",
                      "neuro_exam": "confused but no focal deficit, no neck stiffness"},
        test_results={"glucose_point_of_care": "fingerstick glucose 44 mg/dL"},
    ),
    # 30. severe_electrolyte_disorder (en, hyperkalemia, objective)
    SyntheticCase(
        case_id="Blind8_30_DialysisMissedWeakness", category="metabolic",
        chief_complaint="I feel weak all over and my heart feels like it's skipping since I missed dialysis",
        demographics={"age": 62, "sex": "male"},
        ground_truth_diagnosis="severe_electrolyte_disorder",
        answers={"onset": "generalized weakness building over a day after missing a dialysis session",
                 "associated_symptoms": "muscle weakness, palpitations; denies fever, denies focal weakness or slurred speech",
                 "past_medical_history": "end-stage renal disease on hemodialysis"},
        exam_results={"vital_signs": "BP 150/88, HR 58, RR 16, Temp 36.8, SpO2 98%",
                      "neuro_exam": "diffuse weakness, no focal deficit"},
        test_results={"potassium": "potassium 7.1 mEq/L", "ecg": "peaked T waves, widened QRS"},
    ),
    # 31. sepsis (en, infectious/dangerous)
    SyntheticCase(
        case_id="Blind8_31_NursingHomeAlteredHypotension", category="infectious",
        chief_complaint="my mother from her care home is confused, feverish and her blood pressure is low",
        demographics={"age": 83, "sex": "female"},
        ground_truth_diagnosis="sepsis",
        answers={"onset": "increasingly drowsy and hot over the last day",
                 "associated_symptoms": "confused, not drinking, cool clammy skin; a productive cough for two days",
                 "past_medical_history": "recent urinary catheter, mild dementia"},
        exam_results={"vital_signs": "BP 86/52, HR 122, RR 26, Temp 38.9, SpO2 92%",
                      "general_exam": "confused, poor peripheral perfusion, cap refill 4 seconds"},
        test_results={"lactate": "lactate 4.2 mmol/L", "wbc": "leukocytosis"},
    ),
    # 32. anaphylaxis (en, allergic/dangerous)
    SyntheticCase(
        case_id="Blind8_32_PeanutHivesThroatTight", category="dangerous_mimic",
        chief_complaint="right after eating I broke out in hives and my throat feels like it's closing",
        demographics={"age": 27, "sex": "female"},
        ground_truth_diagnosis="anaphylaxis",
        answers={"onset": "minutes after eating a dish at a new restaurant",
                 "associated_symptoms": "widespread hives, throat tightness, wheezing, lightheaded; denies chest pressure",
                 "past_medical_history": "known peanut allergy"},
        exam_results={"vital_signs": "BP 92/58, HR 122, RR 26, Temp 36.9, SpO2 93%",
                      "general_exam": "diffuse urticaria, lip swelling, audible wheeze, stridor"},
        test_results={},
    ),
    # 33. panic_attack (en, benign mimic of dangerous)
    SyntheticCase(
        case_id="Blind8_33_MeetingPalpitationsDoom", category="benign_mimic",
        chief_complaint="my heart raced, my hands tingled and I felt a wave of doom during a work meeting",
        demographics={"age": 32, "sex": "female"},
        ground_truth_diagnosis="panic_attack",
        answers={"onset": "peaked within a few minutes and eased over 20 minutes",
                 "associated_symptoms": "palpitations, tingling in fingers and around the mouth, sense of impending doom; denies exertional chest pain, denies fever",
                 "past_medical_history": "several similar episodes tied to stress, otherwise healthy"},
        exam_results={"vital_signs": "BP 128/82, HR 104, RR 22, Temp 36.8, SpO2 99%",
                      "cardiovascular_exam": "tachycardic, regular, no murmur"},
        test_results={"ecg": "sinus tachycardia, no ischemic changes", "troponin": "troponin not elevated"},
    ),
    # 34. viral_uri (ja, benign)
    SyntheticCase(
        case_id="Blind8_34_KidBroughtHomeCold", category="common",
        chief_complaint="子供から風邪をもらったようで、鼻水と喉の痛みがあります",
        demographics={"age": 39, "sex": "female"},
        ground_truth_diagnosis="viral_uri",
        answers={"duration": "3日前から",
                 "associated_symptoms": "くしゃみ、軽い喉の痛み、微熱程度; 高熱はない, 息苦しさはない, 耳の痛みはない"},
        exam_results={"vital_signs": "BP 116/72, HR 76, RR 14, Temp 37.2, SpO2 99%",
                      "throat_exam": "軽度の咽頭発赤、滲出物なし"},
        test_results={},
    ),
]


# ================================================================================================
# PART B -- additional cases targeting specific presentation AXES (independent of which diagnosis
# they land on): multimorbidity, polypharmacy, mixed-language, data-freshness/stale-lab, wrong-unit,
# conflicting findings, sparse information, negative-centric, trauma, atypical presentations.
# ================================================================================================

BLIND_CASES_V8 += [
    # 35. mixed ko/en -- dyspnea + objective hypoxia
    SyntheticCase(
        case_id="Blind8_35_MixedKoEnDyspneaHypoxia", category="mixed_language",
        chief_complaint="환자 dyspnea 있고 기침 가래, SpO2 86%로 낮아요",
        demographics={"age": 70, "sex": "male"},
        ground_truth_diagnosis="pneumonia",
        answers={"duration": "3일 전부터 fever랑 productive cough 있었어요",
                 "associated_symptoms": "오른쪽 chest pain when breathing; no leg swelling, no hemoptysis",
                 "past_medical_history": "COPD, diabetes"},
        exam_results={"vital_signs": "BP 130/80, HR 106, RR 26, Temp 38.6, SpO2 86%",
                      "chest_exam": "right base crackles, bronchial breathing"},
        test_results={"chest_xray": "right lower lobe consolidation", "wbc": "leukocytosis"},
    ),
    # 36. mixed ja/en -- focal weakness (aphasia/arm) stroke
    SyntheticCase(
        case_id="Blind8_36_MixedJaEnArmWeakness", category="mixed_language",
        chief_complaint="右腕 weakness があります、急に言葉が出にくくなりました",
        demographics={"age": 66, "sex": "female"},
        ground_truth_diagnosis="ischemic_stroke",
        answers={"onset": "1時間前に sudden に発症、持続しています",
                 "associated_symptoms": "right arm drift and word-finding difficulty; no headache, no neck stiffness",
                 "past_medical_history": "atrial fibrillation, not on anticoagulation"},
        exam_results={"vital_signs": "BP 176/98, HR 92 irregular, RR 16, Temp 36.8, SpO2 98%",
                      "neuro_exam": "expressive aphasia, right arm weakness, no meningismus"},
        test_results={},
    ),
    # 37. mixed zh/en -- chest pain worsening ACS
    SyntheticCase(
        case_id="Blind8_37_MixedZhEnChestPain", category="mixed_language",
        chief_complaint="患者 chest pain 加重，向左臂放射，伴出汗",
        demographics={"age": 59, "sex": "male"},
        ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "休息时发作，about 30 minutes，没有缓解",
                 "associated_symptoms": "radiating to left arm, sweating, mild dyspnea; no fever",
                 "past_medical_history": "diabetes, hypertension, smoker"},
        exam_results={"vital_signs": "BP 148/90, HR 98, RR 20, Temp 36.9, SpO2 96%"},
        test_results={"ecg": "ST depression inferolateral", "troponin": "troponin elevated"},
    ),
    # 38. mixed zh/en -- imaging-confirmed PE ("CT에서 PE suspicious" style, zh)
    SyntheticCase(
        case_id="Blind8_38_MixedImagingPE", category="mixed_language",
        chief_complaint="术后卧床几天，突然 shortness of breath，CT 提示 PE suspicious",
        demographics={"age": 54, "sex": "female"},
        ground_truth_diagnosis="pulmonary_embolism",
        answers={"onset": "突然发作 this morning after days of bed rest post-op",
                 "associated_symptoms": "pleuritic right chest pain, 小腿肿胀; 没有发热",
                 "past_medical_history": "recent knee surgery, immobilized"},
        exam_results={"vital_signs": "BP 116/74, HR 116, RR 26, Temp 37.1, SpO2 90%",
                      "extremity_exam": "right calf swelling and tenderness"},
        test_results={"ct_chest": "filling defect in the right pulmonary artery consistent with embolus"},
    ),
    # 39. polypharmacy elderly -- hypoglycemia vs many culprits (mg/dL)
    SyntheticCase(
        case_id="Blind8_39_PolypharmacyConfusion", category="polypharmacy",
        chief_complaint="my grandmother on many medications became suddenly confused this afternoon",
        demographics={"age": 81, "sex": "female"},
        ground_truth_diagnosis="hypoglycemia",
        answers={"onset": "confusion came on within half an hour, ate very little at lunch",
                 "associated_symptoms": "sweaty, tremulous, drowsy; denies fever, denies focal weakness, denies chest pain",
                 "medications": "glyburide, metformin, lisinopril, atorvastatin, warfarin, omeprazole, furosemide"},
        exam_results={"vital_signs": "BP 142/84, HR 96, RR 16, Temp 36.7, SpO2 98%",
                      "neuro_exam": "confused, no focal deficit, no neck stiffness"},
        test_results={"glucose_point_of_care": "capillary glucose 38 mg/dL"},
    ),
    # 40. WRONG-UNIT data-freshness trap: glucose stated in mmol/L must NOT be read as mg/dL.
    #     True cause is a bleed, not a glucose problem -- the mmol/L glucose is a normal 5.1 that
    #     must not be misread as a hypoglycemic mg/dL number.
    SyntheticCase(
        case_id="Blind8_40_WrongUnitGlucoseGIBleed", category="conflicting_findings",
        chief_complaint="I feel faint and weak, and I've been passing dark, tarry stools",
        demographics={"age": 64, "sex": "male"},
        ground_truth_diagnosis="gi_bleeding",
        answers={"onset": "black stools for two days, lightheaded when standing today",
                 "associated_symptoms": "fatigue, dizziness on standing; denies focal weakness, denies chest pain, denies fever",
                 "medications": "daily aspirin and an NSAID for back pain"},
        exam_results={"vital_signs": "BP 96/60, HR 114, RR 18, Temp 36.8, SpO2 98%",
                      "abdominal_exam": "epigastric tenderness, melena on rectal exam"},
        # The glucose is reported in mmol/L (normal ~5.1) -- it must not be misinterpreted as a low
        # mg/dL value and pull the differential toward hypoglycemia. The real story is the drop in
        # hemoglobin + melena.
        test_results={"glucose_point_of_care": "glucose 5.1 mmol/L",
                      "hemoglobin": "hemoglobin fallen to 7.4 g/dL"},
    ),
    # 41. STALE-lab trap: an old normal troponin should not reassure against a NEW acute event.
    SyntheticCase(
        case_id="Blind8_41_StaleTroponinNewACS", category="data_freshness",
        chief_complaint="crushing chest pressure started an hour ago with sweating and nausea",
        demographics={"age": 61, "sex": "male"},
        ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "sudden crushing pressure one hour ago, ongoing",
                 "associated_symptoms": "diaphoresis, nausea, radiation to jaw; denies fever",
                 "past_medical_history": "a normal troponin and stress test six months ago; hypertension, smoker"},
        exam_results={"vital_signs": "BP 158/96, HR 100, RR 20, Temp 36.9, SpO2 96%"},
        # The relevant evidence is the CURRENT ECG + a fresh troponin, not the 6-month-old normal one.
        test_results={"ecg": "new ST elevation in the inferior leads",
                      "troponin": "current troponin elevated and rising"},
    ),
    # 42. multimorbidity -- sepsis from a urinary source in a diabetic with CKD
    SyntheticCase(
        case_id="Blind8_42_MultimorbidUrosepsis", category="multimorbidity",
        chief_complaint="feverish, shaky and increasingly drowsy with burning urination",
        demographics={"age": 76, "sex": "female"},
        ground_truth_diagnosis="sepsis",
        answers={"onset": "urinary burning for two days, then rigors and drowsiness today",
                 "associated_symptoms": "confusion, flank discomfort, poor oral intake; denies cough, denies chest pain",
                 "past_medical_history": "type 2 diabetes, chronic kidney disease, hypertension"},
        exam_results={"vital_signs": "BP 88/54, HR 120, RR 24, Temp 39.0, SpO2 94%",
                      "general_exam": "confused, warm peripheries then clammy, CVA tenderness"},
        test_results={"lactate": "lactate 3.8 mmol/L", "urinalysis": "pyuria with nitrites", "wbc": "leukocytosis"},
    ),
    # 43. sparse information -- minimal data, dangerous can't-miss must stay considered
    SyntheticCase(
        case_id="Blind8_43_SparseSuddenWorstHeadache", category="sparse_information",
        chief_complaint="worst headache ever, came on all at once",
        demographics={"age": 52, "sex": "female"},
        ground_truth_diagnosis="subarachnoid_hemorrhage",
        answers={"onset": "instant, a few minutes ago"},
        exam_results={"vital_signs": "BP 174/100, HR 90, RR 18, Temp 37.0, SpO2 98%"},
        test_results={},
    ),
    # 44. negative-finding-centric -- reassuring benign headache, danger ruled out by negatives
    SyntheticCase(
        case_id="Blind8_44_NegativeCentricBenignHeadache", category="negative_centric",
        chief_complaint="I've had my usual dull headache for a couple of days",
        demographics={"age": 34, "sex": "female"},
        ground_truth_diagnosis="tension_headache",
        answers={"onset": "gradual over two days, same as headaches I get monthly",
                 "associated_symptoms": "denies sudden onset, denies worst-ever, denies neck stiffness, denies fever, "
                                        "denies visual aura, denies weakness or numbness, denies vomiting",
                 "character": "mild bilateral pressure, relieved by rest"},
        exam_results={"vital_signs": "BP 120/76, HR 72, RR 14, Temp 36.8, SpO2 99%",
                      "neuro_exam": "completely normal, no meningismus"},
        test_results={},
    ),
    # 45. trauma-context but atraumatic dangerous cause -- syncope-caused fall, real cause arrhythmia
    SyntheticCase(
        case_id="Blind8_45_FallAfterBlackout", category="trauma",
        chief_complaint="I blacked out with no warning and fell, hitting my head",
        demographics={"age": 68, "sex": "male"},
        ground_truth_diagnosis="cardiac_arrhythmia",
        answers={"onset": "no warning at all, collapsed mid-sentence, brief loss of consciousness",
                 "associated_symptoms": "palpitations just before, no aura, no tongue biting, no incontinence; denies chest pain",
                 "past_medical_history": "coronary disease, on no rhythm-control medication"},
        exam_results={"vital_signs": "BP 118/74, HR 44, RR 16, Temp 36.8, SpO2 98%",
                      "neuro_exam": "scalp laceration, neurologically intact"},
        test_results={"ecg": "high-grade AV block with bradycardia"},
    ),
    # 46. pregnancy physiologic mimic -- benign, not ectopic (contrast to case 27)
    SyntheticCase(
        case_id="Blind8_46_EarlyPregnancyRoundLigament", category="pregnancy",
        chief_complaint="I'm early pregnant and get brief sharp twinges low on one side when I move",
        demographics={"age": 31, "sex": "female"},
        ground_truth_diagnosis="musculoskeletal_chest_pain",
        notes="pelvic/pregnancy benign mimic axis; MSK-type positional pain, not an emergency",
        answers={"onset": "brief seconds-long twinges with position change over a week",
                 "associated_symptoms": "no bleeding, no dizziness, no fever, no urinary symptoms; eases when I rest",
                 "last_menstrual_period": "confirmed intrauterine pregnancy on ultrasound last week"},
        exam_results={"vital_signs": "BP 116/72, HR 78, RR 14, Temp 36.8, SpO2 99%",
                      "abdominal_exam": "soft, non-tender, no cervical motion tenderness"},
        test_results={"beta_hcg": "consistent with a confirmed intrauterine pregnancy"},
        scoring_expected=False,
    ),
    # 47. atypical infection -- afebrile elderly pneumonia presenting as confusion
    SyntheticCase(
        case_id="Blind8_47_AfebrileElderlyPneumonia", category="atypical_infection",
        chief_complaint="my elderly mother just seems off and confused, breathing a bit fast",
        demographics={"age": 88, "sex": "female"},
        ground_truth_diagnosis="pneumonia",
        answers={"onset": "gradually more confused and less active over two days",
                 "associated_symptoms": "occasional weak cough, poor appetite; no reported fever",
                 "past_medical_history": "dementia, prior aspiration"},
        exam_results={"vital_signs": "BP 118/70, HR 100, RR 26, Temp 37.3, SpO2 89%",
                      "chest_exam": "right basal crackles"},
        test_results={"chest_xray": "right lower lobe airspace opacity", "wbc": "mildly elevated white blood cell count"},
    ),
    # 48. conflicting findings -- fever + cough but pleuritic + hypoxia + tachycardia (PE over PNA)
    SyntheticCase(
        case_id="Blind8_48_ConflictingPEvsPneumonia", category="conflicting_findings",
        chief_complaint="I have a low fever and a cough but also sudden sharp pain when I breathe in",
        demographics={"age": 48, "sex": "female"},
        ground_truth_diagnosis="pulmonary_embolism",
        answers={"onset": "the sharp pleuritic pain and breathlessness came on suddenly today",
                 "associated_symptoms": "one swollen tender calf, mild dry cough, low-grade temperature; scant sputum",
                 "medications": "hormone replacement therapy",
                 "past_medical_history": "recent long car journey"},
        exam_results={"vital_signs": "BP 118/76, HR 118, RR 26, Temp 37.6, SpO2 90%",
                      "chest_exam": "clear lungs bilaterally, no consolidation", "extremity_exam": "left calf swelling"},
        test_results={"d_dimer": "D-dimer elevated", "chest_xray": "no consolidation or effusion"},
    ),
    # 49. dangerous mimic -- GERD-sounding but is ACS (do not anchor on reflux)
    SyntheticCase(
        case_id="Blind8_49_RefluxSoundingACS", category="dangerous_mimic",
        chief_complaint="I thought it was bad heartburn but this burning chest tightness won't go and I'm sweating",
        demographics={"age": 57, "sex": "male"},
        ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "started 45 minutes ago at rest, not relieved by antacids",
                 "associated_symptoms": "cold sweat, mild nausea, tightness into the jaw; came on at rest not after food",
                 "past_medical_history": "reflux, but also diabetes and a family history of early MI"},
        exam_results={"vital_signs": "BP 150/92, HR 98, RR 20, Temp 36.9, SpO2 96%"},
        test_results={"ecg": "hyperacute T waves, early ST changes", "troponin": "troponin elevated"},
    ),
    # 50. benign mimic -- ACS-sounding but reproducible MSK (contrast to 49)
    SyntheticCase(
        case_id="Blind8_50_ScaryButMSKChest", category="benign_mimic",
        chief_complaint="I got scared by a sharp chest pain but it only hurts when I press or twist",
        demographics={"age": 40, "sex": "female"},
        ground_truth_diagnosis="musculoskeletal_chest_pain",
        answers={"onset": "since a heavy workout two days ago",
                 "associated_symptoms": "sharp, localized, worse with deep breath and pressing; denies sweating, denies nausea, not related to exertion now",
                 "past_medical_history": "healthy, no cardiac risk factors"},
        exam_results={"vital_signs": "BP 118/74, HR 70, RR 14, Temp 36.8, SpO2 99%",
                      "chest_exam": "reproducible tenderness over the sternocostal margin"},
        test_results={"ecg": "normal", "troponin": "not elevated"},
    ),
    # 51. metabolic -- euglycemic-ish DKA presenting with vomiting (ketones drive it, ko)
    SyntheticCase(
        case_id="Blind8_51_SickDayKetosis", category="metabolic",
        chief_complaint="당뇨가 있는데 감기 앓고 나서 계속 토하고 숨을 깊게 몰아쉬어요",
        demographics={"age": 24, "sex": "female"},
        ground_truth_diagnosis="diabetic_ketoacidosis",
        answers={"onset": "이틀간 감기 앓으면서 인슐린을 줄였어요",
                 "associated_symptoms": "구역 구토, 복통, 깊고 빠른 호흡; 흉통 없음",
                 "past_medical_history": "제1형 당뇨"},
        exam_results={"vital_signs": "BP 112/70, HR 116, RR 28 deep, Temp 37.4, SpO2 99%",
                      "general_exam": "탈수 소견, 과일 냄새 나는 호흡"},
        test_results={"glucose_point_of_care": "blood glucose 268 mg/dL",
                      "ketones": "ketones strongly positive", "bicarbonate": "bicarbonate 12 mEq/L"},
    ),
    # 52. atypical neuro -- posterior circulation stroke as isolated vertigo + gait (not BPPV)
    SyntheticCase(
        case_id="Blind8_52_PersistentVertigoAtaxia", category="atypical_neuro",
        chief_complaint="constant spinning that won't stop and I keep veering to one side when I walk",
        demographics={"age": 67, "sex": "male"},
        ground_truth_diagnosis="ischemic_stroke",
        answers={"onset": "sudden and CONSTANT for the last two hours, not just with head movement",
                 "associated_symptoms": "unsteady gait, mild double vision; denies ear fullness, denies hearing loss",
                 "past_medical_history": "hypertension, diabetes, smoker"},
        exam_results={"vital_signs": "BP 178/98, HR 84, RR 16, Temp 36.8, SpO2 98%",
                      "neuro_exam": "gait ataxia, direction-changing nystagmus, unable to walk unaided"},
        test_results={},
    ),
    # 53. sparse -- isolated syncope in young, benign vasovagal (contrast to 45)
    SyntheticCase(
        case_id="Blind8_53_ChoirStandingFaint", category="benign_mimic",
        chief_complaint="I fainted standing in a hot crowded hall",
        demographics={"age": 19, "sex": "female"},
        ground_truth_diagnosis="vasovagal_syncope",
        answers={"onset": "felt hot, nauseated and tunnel-visioned, then briefly passed out, recovered in seconds",
                 "associated_symptoms": "prodrome of warmth and nausea; denies palpitations, denies chest pain, denies exertion, no injury",
                 "past_medical_history": "healthy, similar episode once as a teenager"},
        exam_results={"vital_signs": "BP 116/72, HR 72, RR 14, Temp 36.8, SpO2 99%"},
        test_results={"ecg": "normal sinus rhythm, normal intervals"},
    ),
    # 54. abdominal -- appendicitis atypical (retrocecal, zh)
    SyntheticCase(
        case_id="Blind8_54_AtypicalRetrocecalAppendicitis", category="abdominal",
        chief_complaint="右下腹隐痛两天，走路和咳嗽时加重，有点低烧",
        demographics={"age": 31, "sex": "male"},
        ground_truth_diagnosis="appendicitis",
        answers={"onset": "两天前脐周不适，逐渐转到右下腹",
                 "associated_symptoms": "食欲差，恶心，低烧，咳嗽时右下腹痛; 没有腹泻, 没有血便",
                 "past_medical_history": "既往体健"},
        exam_results={"vital_signs": "BP 122/78, HR 94, RR 16, Temp 37.8, SpO2 99%",
                      "abdominal_exam": "右下腹压痛，咳嗽征阳性，轻度肌紧张"},
        test_results={"wbc": "白细胞升高 leukocytosis"},
    ),
    # 55. cystitis-vs-pyelo axis -- afebrile lower tract only, benign (contrast to 26)
    SyntheticCase(
        case_id="Blind8_55_LowerTractOnly", category="common",
        chief_complaint="burning when I urinate and going often for two days, but I feel otherwise well",
        demographics={"age": 24, "sex": "female"},
        ground_truth_diagnosis="uncomplicated_cystitis",
        answers={"onset": "two days of dysuria and frequency",
                 "associated_symptoms": "suprapubic discomfort; denies fever, denies flank pain, denies rigors, denies nausea"},
        exam_results={"vital_signs": "BP 118/74, HR 72, RR 14, Temp 36.8, SpO2 99%",
                      "abdominal_exam": "mild suprapubic tenderness, no CVA tenderness"},
        test_results={"urinalysis": "leukocyte esterase positive, nitrites positive"},
    ),
    # 56. pancreatitis by gallstones (en) -- different mechanism than case 20's alcohol
    SyntheticCase(
        case_id="Blind8_56_GallstoneEpigastric", category="abdominal",
        chief_complaint="severe upper belly pain wrapping to my back after a fatty meal, and I keep vomiting",
        demographics={"age": 52, "sex": "female"},
        ground_truth_diagnosis="acute_pancreatitis",
        answers={"onset": "began a few hours after a rich dinner, steadily severe",
                 "associated_symptoms": "boring pain to the back, relieved by leaning forward, repeated vomiting; denies chest pain",
                 "past_medical_history": "known gallstones, does not drink alcohol"},
        exam_results={"vital_signs": "BP 128/80, HR 104, RR 20, Temp 37.9, SpO2 98%",
                      "abdominal_exam": "epigastric tenderness, voluntary guarding"},
        test_results={"lipase": "lipase over four times the upper limit of normal"},
    ),
    # 57. sepsis-vs-meningitis conflicting -- fever + neck discomfort but source is chest (multimorbid)
    SyntheticCase(
        case_id="Blind8_57_FeverNeckButChestSource", category="conflicting_findings",
        chief_complaint="high fever, feeling awful, and my neck is a bit stiff and sore",
        demographics={"age": 71, "sex": "male"},
        ground_truth_diagnosis="pneumonia",
        answers={"onset": "two days of fever and productive cough, neck soreness today",
                 "associated_symptoms": "green sputum, right-sided pleuritic pain, generalized aches; no photophobia, neck sore but flexes fully",
                 "past_medical_history": "COPD, diabetes"},
        exam_results={"vital_signs": "BP 118/74, HR 108, RR 24, Temp 39.0, SpO2 90%",
                      "neuro_exam": "neck supple to full flexion, no true meningismus, no focal deficit",
                      "chest_exam": "right upper lobe bronchial breathing"},
        test_results={"chest_xray": "right upper lobe consolidation", "wbc": "leukocytosis"},
    ),
    # 58. asthma exacerbation in young adult (ko) -- distinct from COPD case 6
    SyntheticCase(
        case_id="Blind8_58_CatDanderWheeze", category="pulmonary",
        chief_complaint="친구 집 고양이 만난 뒤부터 쌕쌕거리고 숨쉬기가 힘들어요",
        demographics={"age": 23, "sex": "female"},
        ground_truth_diagnosis="asthma_copd_exacerbation",
        answers={"onset": "몇 시간 전 고양이 노출 후 시작",
                 "associated_symptoms": "쌕쌕거림, 가슴 답답함, 마른기침; 발열 없음, 다리 부종 없음",
                 "past_medical_history": "어릴 때부터 천식, 흡입기 사용"},
        exam_results={"vital_signs": "BP 122/76, HR 104, RR 24, Temp 36.8, SpO2 93%",
                      "chest_exam": "양폐야 호기성 천명, 호기 연장"},
        test_results={},
    ),
    # 59. bradyarrhythmia vs orthostatic -- dizziness axis, true cause arrhythmia (en)
    SyntheticCase(
        case_id="Blind8_59_DizzyBradyPalpitations", category="cardiac",
        chief_complaint="I keep feeling faint and my pulse feels very slow and irregular",
        demographics={"age": 75, "sex": "female"},
        ground_truth_diagnosis="cardiac_arrhythmia",
        answers={"onset": "recurrent near-faint spells over two days, not just on standing",
                 "associated_symptoms": "palpitations, fatigue, occurs sitting too; denies positional-only symptoms, denies bleeding",
                 "medications": "a rate-lowering heart medication was recently increased"},
        exam_results={"vital_signs": "BP 124/78 with no significant orthostatic drop, HR 40 irregular, RR 16, SpO2 98%",
                      "cardiovascular_exam": "slow irregular pulse"},
        test_results={"ecg": "sinus bradycardia with dropped beats (second-degree AV block)"},
    ),
    # 60. severe electrolyte -- hyponatremia (en), numeric sodium
    SyntheticCase(
        case_id="Blind8_60_ThiazideHyponatremia", category="metabolic",
        chief_complaint="I've been increasingly confused, nauseated and unsteady over a few days",
        demographics={"age": 79, "sex": "female"},
        ground_truth_diagnosis="severe_electrolyte_disorder",
        answers={"onset": "gradual over three to four days",
                 "associated_symptoms": "headache, nausea, unsteadiness, one brief episode of muscle twitching; denies fever, denies focal weakness",
                 "medications": "recently started a thiazide diuretic; drinks a lot of water"},
        exam_results={"vital_signs": "BP 128/78, HR 82, RR 16, Temp 36.7, SpO2 98%",
                      "neuro_exam": "disoriented, no focal deficit, no meningismus"},
        test_results={"sodium": "sodium 118 mEq/L"},
    ),
    # 61. anaphylaxis biphasic-ish (ja) drug trigger
    SyntheticCase(
        case_id="Blind8_61_DrugAllergyThroat", category="dangerous_mimic",
        chief_complaint="新しい薬を飲んだ後、全身にじんましんが出て喉が締まる感じがします",
        demographics={"age": 45, "sex": "male"},
        ground_truth_diagnosis="anaphylaxis",
        answers={"onset": "服薬から15分後に発症",
                 "associated_symptoms": "全身じんましん、喉の圧迫感、喘鳴、ふらつき; 胸痛はない",
                 "past_medical_history": "以前ペニシリンで発疹"},
        exam_results={"vital_signs": "BP 94/58, HR 120, RR 26, Temp 36.9, SpO2 92%",
                      "general_exam": "全身蕁麻疹、口唇腫脹、吸気性喘鳴"},
        test_results={},
    ),
    # 62. panic vs arrhythmia conflicting -- palpitations, but objectively benign (contrast 16/59)
    SyntheticCase(
        case_id="Blind8_62_StressPalpitationsNormalECG", category="benign_mimic",
        chief_complaint="my heart pounds and I feel breathless and terrified during exams",
        demographics={"age": 21, "sex": "male"},
        ground_truth_diagnosis="panic_attack",
        answers={"onset": "episodes last 10-20 minutes, tied to stress, resolve on their own",
                 "associated_symptoms": "palpitations, chest tightness, tingling hands, fear; denies syncope, denies exertional trigger, denies fever",
                 "past_medical_history": "healthy, high anxiety around exams"},
        exam_results={"vital_signs": "BP 126/80, HR 100, RR 22, Temp 36.8, SpO2 99%"},
        test_results={"ecg": "normal sinus rhythm, normal intervals", "troponin": "not elevated"},
    ),
    # 63. GI bleed upper vs lower -- hematemesis (zh), distinct from melena case 22
    SyntheticCase(
        case_id="Blind8_63_HematemesisVariceal", category="gi_bleeding",
        chief_complaint="呕出鲜红色血液，头晕乏力",
        demographics={"age": 58, "sex": "male"},
        ground_truth_diagnosis="gi_bleeding",
        answers={"onset": "今天呕血两次",
                 "associated_symptoms": "头晕、心慌、乏力; 无发热, 无胸痛",
                 "past_medical_history": "肝硬化病史，长期饮酒"},
        exam_results={"vital_signs": "BP 92/58, HR 116, RR 20, Temp 36.7, SpO2 98%",
                      "abdominal_exam": "腹部膨隆，脾大，直肠可见黑便"},
        test_results={"hemoglobin": "hemoglobin 6.9 g/dL"},
    ),
    # 64. nephrolithiasis vs AAA dangerous mimic -- flank pain in older man (must not miss dissection/AAA-like)
    SyntheticCase(
        case_id="Blind8_64_OlderFlankPainCaution", category="dangerous_mimic",
        chief_complaint="sudden severe left flank and back pain with lightheadedness",
        demographics={"age": 70, "sex": "male"},
        ground_truth_diagnosis="aortic_dissection",
        notes="flank/back pain in an older vasculopath is a can't-miss for aortic catastrophe, not just a stone",
        answers={"onset": "sudden and severe 30 minutes ago",
                 "associated_symptoms": "back and flank pain, faint, cold sweat; denies urinary symptoms",
                 "past_medical_history": "hypertension, smoker, known abdominal aortic aneurysm on surveillance"},
        exam_results={"vital_signs": "BP 96/58, HR 118, RR 22, Temp 36.8, SpO2 97%",
                      "abdominal_exam": "pulsatile expansile abdominal mass, unequal femoral pulses"},
        test_results={},
    ),
    # 65. BPPV vs central (ko) -- benign positional, danger excluded by negatives (contrast 52)
    SyntheticCase(
        case_id="Blind8_65_PositionalOnlyVertigo", category="benign_mimic",
        chief_complaint="누웠다 일어날 때만 몇 초 핑 도는 어지럼이 있어요",
        demographics={"age": 50, "sex": "female"},
        ground_truth_diagnosis="bppv",
        answers={"onset": "이틀 전부터, 오직 머리 위치 바꿀 때만 수 초간",
                 "associated_symptoms": "짧은 회전성 어지럼; 지속적 어지럼 없음, 보행 정상, 복시 없음, 난청 없음, 두통 없음, 위약 없음"},
        exam_results={"vital_signs": "BP 124/78, HR 74, RR 14, Temp 36.8, SpO2 99%",
                      "neuro_exam": "Dix-Hallpike 유발성 안진, 보행 안정, 국소 신경학적 이상 없음"},
        test_results={},
    ),
    # 66. sparse dangerous -- one-line dyspnea + hypoxia, undifferentiated
    SyntheticCase(
        case_id="Blind8_66_SparseAcuteDyspnea", category="sparse_information",
        chief_complaint="can't breathe, came on suddenly",
        demographics={"age": 60, "sex": "male"},
        ground_truth_diagnosis="pulmonary_embolism",
        answers={"onset": "sudden, minutes ago",
                 "associated_symptoms": "one leg swollen"},
        exam_results={"vital_signs": "BP 108/70, HR 122, RR 28, Temp 37.0, SpO2 88%"},
        test_results={},
    ),
    # 67. orthostatic from dehydration (en) -- benign volume depletion (contrast med-induced 15)
    SyntheticCase(
        case_id="Blind8_67_GastroDehydrationOrthostasis", category="metabolic",
        chief_complaint="I get very lightheaded standing up after two days of diarrhea",
        demographics={"age": 34, "sex": "female"},
        ground_truth_diagnosis="orthostatic_hypotension",
        answers={"onset": "since a bout of gastroenteritis, worse each time I stand",
                 "associated_symptoms": "dry mouth, reduced urination, resolves lying down; denies chest pain, denies palpitations, denies black stools",
                 "past_medical_history": "otherwise healthy"},
        exam_results={"vital_signs": "BP 122/78 lying, 98/60 standing, HR 88 to 110 on standing, Temp 37.0, SpO2 99%",
                      "general_exam": "dry mucous membranes"},
        test_results={},
    ),
    # 68. meningitis atypical (en) -- immunocompromised, subtle
    SyntheticCase(
        case_id="Blind8_68_ImmunocompromisedHeadacheFever", category="atypical_infection",
        chief_complaint="a bad headache and fever for a day, and now I feel drowsy and my neck aches",
        demographics={"age": 44, "sex": "male"},
        ground_truth_diagnosis="meningitis",
        answers={"onset": "headache and fever since yesterday, drowsiness today",
                 "associated_symptoms": "photophobia, nausea, neck stiffness; denies focal weakness",
                 "past_medical_history": "on immunosuppressants after a kidney transplant"},
        exam_results={"vital_signs": "BP 122/76, HR 108, RR 20, Temp 38.8, SpO2 97%",
                      "neuro_exam": "neck stiffness, photophobia, no focal deficit"},
        test_results={},
    ),
    # 69. GERD vs ACS benign resolution (zh) -- reflux confirmed benign, danger excluded
    SyntheticCase(
        case_id="Blind8_69_RefluxBenignResolved", category="common",
        chief_complaint="饭后胸口烧灼，坐起来和吃抑酸药就好转",
        demographics={"age": 47, "sex": "female"},
        ground_truth_diagnosis="gerd",
        answers={"onset": "反复几个月，餐后和平躺时明显",
                 "associated_symptoms": "反酸、烧心，抑酸药有效; 不出汗, 不放射到手臂, 运动时不加重, 无气短"},
        exam_results={"vital_signs": "BP 120/76, HR 72, RR 14, Temp 36.8, SpO2 99%"},
        test_results={"ecg": "normal sinus rhythm, no ischemic changes", "troponin": "not elevated"},
    ),
    # 70. multimorbidity + stale imaging -- old normal CXR should not reassure new pneumonia
    SyntheticCase(
        case_id="Blind8_70_StaleImagingNewPneumonia", category="data_freshness",
        chief_complaint="new fever, worsening cough and breathlessness over three days",
        demographics={"age": 68, "sex": "female"},
        ground_truth_diagnosis="pneumonia",
        answers={"onset": "three days of worsening cough, fever and breathlessness",
                 "associated_symptoms": "green sputum, right pleuritic pain; a chest x-ray six months ago was normal",
                 "past_medical_history": "COPD, heart failure, diabetes"},
        exam_results={"vital_signs": "BP 124/78, HR 106, RR 26, Temp 38.7, SpO2 89%",
                      "chest_exam": "new right basal crackles and dullness"},
        test_results={"chest_xray": "new right lower lobe consolidation on today's film", "wbc": "leukocytosis"},
    ),
    # 71. anaphylaxis vs panic conflicting -- objective hives/hypotension decide it (en)
    SyntheticCase(
        case_id="Blind8_71_AllergicNotPanic", category="conflicting_findings",
        chief_complaint="I suddenly felt a wave of panic, racing heart and breathlessness at a party",
        demographics={"age": 30, "sex": "female"},
        ground_truth_diagnosis="anaphylaxis",
        answers={"onset": "within minutes of a canape, felt panicky and flushed",
                 "associated_symptoms": "spreading itchy hives, lip tingling, throat tightening, wheeze; more than her usual panic episodes",
                 "past_medical_history": "anxiety with panic attacks, and a shellfish allergy"},
        exam_results={"vital_signs": "BP 90/56, HR 124, RR 26, Temp 36.9, SpO2 92%",
                      "general_exam": "urticarial rash spreading, mild lip swelling, expiratory wheeze"},
        test_results={},
    ),
    # 72. mixed ko/en sparse metabolic -- hypoglycemia, mg/dL, must beat DKA on the number
    SyntheticCase(
        case_id="Blind8_72_MixedSparseHypoglycemia", category="mixed_language",
        chief_complaint="당뇨 환자, sudden confusion and sweating, fingerstick 낮게 나왔어요",
        demographics={"age": 69, "sex": "female"},
        ground_truth_diagnosis="hypoglycemia",
        answers={"onset": "식사 거른 뒤 20분간 confusion",
                 "associated_symptoms": "sweating, tremor, drowsy; no focal weakness, no chest pain",
                 "medications": "insulin glargine, glipizide"},
        exam_results={"vital_signs": "BP 140/84, HR 100, RR 16, Temp 36.8, SpO2 98%",
                      "neuro_exam": "confused, no focal deficit"},
        test_results={"glucose_point_of_care": "fingerstick glucose 40 mg/dL"},
    ),
]
