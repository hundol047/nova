"""Blind evaluation set v9 (independent-re-audit round).

Why v9: the independent re-audit changed reasoning code -- the lab-unit safety guard was
generalized beyond glucose (nova_agent/unit_safety.py + objective_evidence.py disallowed_units for
creatinine/hemoglobin, severity_evidence lactate) and the objective-evidence registry gained
lipase + urinalysis-infection markers. Per the blind-set discipline (a set frozen before a reasoning
change can no longer be the "untouched" measure of the changed code), Blind v6 and Blind v8 are now
REFERENCE-ONLY and this fresh set is the untouched check for the current code.

Authoring rules followed (identical discipline to blind_cases_v6/v8):
  1. Written AFTER all reasoning changes in this round were complete.
  2. No sentence/clause/phrase copied from evaluation/cases.py, held_out_cases.py,
     generalization_cases_v2.py, generalization_stress_cases.py, or any blind_cases_v3/v4/v5/v6/v8.py
     -- every vignette is freshly written with a distinct mechanism/setting/demographic, and NOTHING
     is keyed to a prior miss (the leakage scan covers this file).
  3. Covers all 34 knowledge-base diagnoses at least once, PLUS an explicit UNIT-SAFETY /
     DATA-FRESHNESS axis: cases that state a lab in an SI/alternate unit (creatinine umol/L,
     hemoglobin g/L, lactate) exactly to confirm the reasoning does NOT misread the bare number,
     plus lipase-driven pancreatitis and dipstick-driven UTI (the newly-registered analytes).
     Spread across ko/en/ja/zh/mixed input.
  4. ground_truth_diagnosis / category / content frozen BEFORE the first run -- see
     evaluation/blind_v9_manifest.json for the SHA-256 recorded at freeze time. Not edited after
     seeing any run's result. FIRST RUN happens exactly once in a runnable environment.

44 cases. Hand-authored synthetic vignettes, never real patient data. All ground-truth ids are
members of the 34-entry knowledge base.
"""

from __future__ import annotations

from evaluation.cases import SyntheticCase

BLIND_CASES_V9 = [
    # --- one fresh vignette per knowledge-base diagnosis (34) --------------------------------------
    SyntheticCase(
        case_id="Blind9_01_StairsChestTightness", category="cardiac",
        chief_complaint="climbing two flights left me with a heavy squeezing across the chest that hasn't eased",
        demographics={"age": 66, "sex": "male"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "with exertion about 50 minutes ago, still there at rest",
                 "associated_symptoms": "clammy, jaw ache, short of breath; denies fever",
                 "past_medical_history": "hyperlipidemia, ex-smoker"},
        exam_results={"vital_signs": "BP 156/92, HR 94, RR 20, Temp 36.9, SpO2 96%"},
        test_results={"ecg": "ST depression laterally", "troponin": "troponin elevated above the reference limit"},
    ),
    SyntheticCase(
        case_id="Blind9_02_RippingBackOlderMan", category="dangerous_mimic",
        chief_complaint="an abrupt ripping pain shot through to my back and I feel faint",
        demographics={"age": 71, "sex": "male"}, ground_truth_diagnosis="aortic_dissection",
        answers={"onset": "maximal instantly about 40 minutes ago",
                 "character": "tearing, migrating downward; denies cough, denies fever",
                 "past_medical_history": "long-standing hypertension"},
        exam_results={"vital_signs": "BP 190/72 right arm, 148/60 left arm, HR 104, RR 22, SpO2 97%",
                      "cardiovascular_exam": "pulse deficit between arms, soft diastolic murmur"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind9_03_PostpartumSuddenDyspnea", category="cardiac",
        chief_complaint="갑자기 숨이 차고 오른쪽 가슴이 숨쉴 때 찌릿하게 아파요",
        demographics={"age": 33, "sex": "female"}, ground_truth_diagnosis="pulmonary_embolism",
        answers={"onset": "오늘 아침 갑자기 시작", "associated_symptoms": "왼쪽 종아리 부종과 압통; 발열 없음, 가래 없음",
                 "past_medical_history": "2주 전 출산"},
        exam_results={"vital_signs": "BP 116/74, HR 116, RR 26, Temp 37.0, SpO2 90%",
                      "extremity_exam": "왼쪽 종아리 부종·압통"},
        test_results={"d_dimer": "D-dimer markedly elevated"},
    ),
    SyntheticCase(
        case_id="Blind9_04_DivingSuddenChestCollapse", category="dangerous_mimic",
        chief_complaint="my right chest suddenly gave out and I can't get a full breath",
        demographics={"age": 27, "sex": "male"}, ground_truth_diagnosis="tension_pneumothorax",
        answers={"onset": "sudden, minutes ago, worsening fast", "associated_symptoms": "sharp right chest pain; denies fever",
                 "past_medical_history": "tall, thin, smoker"},
        exam_results={"vital_signs": "BP 94/58, HR 130, RR 34, Temp 36.8, SpO2 85%",
                      "chest_exam": "absent right breath sounds, tracheal shift to the left, distended neck veins"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind9_05_ElderlyWetCough", category="infectious",
        chief_complaint="咳嗽伴黄痰三天，还有发热和呼吸急促",
        demographics={"age": 76, "sex": "male"}, ground_truth_diagnosis="pneumonia",
        answers={"duration": "三天，逐渐加重", "associated_symptoms": "右侧胸痛、寒战; 无腿肿, 无咯血",
                 "past_medical_history": "慢阻肺"},
        exam_results={"vital_signs": "BP 130/80, HR 106, RR 26, Temp 38.8, SpO2 90%",
                      "chest_exam": "右下肺湿啰音、支气管呼吸音"},
        test_results={"chest_xray": "right lower lobe consolidation", "wbc": "leukocytosis"},
    ),
    SyntheticCase(
        case_id="Blind9_06_WinterInhalerFlare", category="pulmonary",
        chief_complaint="the cold air set off my wheezing and I'm working hard to breathe",
        demographics={"age": 61, "sex": "female"}, ground_truth_diagnosis="asthma_copd_exacerbation",
        answers={"onset": "worse over 2 days with the cold", "associated_symptoms": "cough with clear sputum, chest tightness; denies fever, denies calf swelling",
                 "social_history": "35 pack-year smoker, daily inhaler"},
        exam_results={"vital_signs": "BP 140/86, HR 100, RR 24, Temp 37.0, SpO2 92%",
                      "chest_exam": "diffuse expiratory wheeze, prolonged expiration"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind9_07_LingeringPostViralCough", category="common",
        chief_complaint="風邪の後、咳だけが十日以上続いています",
        demographics={"age": 35, "sex": "male"}, ground_truth_diagnosis="acute_bronchitis",
        answers={"duration": "風邪が治った後も十日以上", "associated_symptoms": "少量の白い痰、胸のいがらっぽさ; 高熱なし, 息切れなし, 血痰なし"},
        exam_results={"vital_signs": "BP 118/74, HR 76, RR 16, Temp 37.1, SpO2 98%",
                      "chest_exam": "散発性の乾性ラ音、実変なし"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind9_08_WokeWithSlurredSpeech", category="neuro",
        chief_complaint="자고 일어나니 왼쪽 팔에 힘이 없고 말이 어눌해요",
        demographics={"age": 73, "sex": "female"}, ground_truth_diagnosis="ischemic_stroke",
        answers={"onset": "약 90분 전 갑자기, 지속됨", "associated_symptoms": "왼팔 위약, 안면 처짐; 두통 없음, 목 뻣뻣함 없음",
                 "past_medical_history": "심방세동, 고혈압"},
        exam_results={"vital_signs": "BP 178/98, HR 90 irregular, RR 16, Temp 36.8, SpO2 97%",
                      "neuro_exam": "left facial droop, left arm drift, dysarthria, no meningismus"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind9_09_ThunderclapCleaningHouse", category="dangerous_mimic",
        chief_complaint="the most explosive headache of my life hit me out of nowhere",
        demographics={"age": 51, "sex": "female"}, ground_truth_diagnosis="subarachnoid_hemorrhage",
        answers={"onset": "instantly maximal ~20 minutes ago", "associated_symptoms": "vomited, stiff neck, light hurts; denies weakness",
                 "past_medical_history": "smoker"},
        exam_results={"vital_signs": "BP 172/100, HR 92, RR 18, Temp 37.0, SpO2 98%",
                      "neuro_exam": "neck stiffness, photophobia, no focal deficit"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind9_10_CampFeverStiffNeck", category="infectious",
        chief_complaint="高熱と激しい頭痛、首が硬くて曲がりません",
        demographics={"age": 19, "sex": "female"}, ground_truth_diagnosis="meningitis",
        answers={"onset": "昨夜から急速に", "associated_symptoms": "光がまぶしい、嘔気、ぐったり; 手足の麻痺なし",
                 "social_history": "合宿中、周囲に発熱者"},
        exam_results={"vital_signs": "BP 116/72, HR 118, RR 22, Temp 39.5, SpO2 97%",
                      "neuro_exam": "項部硬直、羞明、局所神経脱落なし"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind9_11_AuraZigzagOneSided", category="benign_mimic",
        chief_complaint="a shimmering arc crossed my vision then a one-sided throbbing headache set in",
        demographics={"age": 28, "sex": "female"}, ground_truth_diagnosis="migraine",
        answers={"onset": "visual aura first for 15 min then throbbing, like my usual attacks",
                 "associated_symptoms": "nausea, light and sound worsen it; denies neck stiffness, denies weakness or slurred speech",
                 "past_medical_history": "migraine with aura since teens"},
        exam_results={"vital_signs": "BP 116/72, HR 70, RR 14, Temp 36.8, SpO2 99%",
                      "neuro_exam": "no focal deficit, neck supple"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind9_12_ExamWeekBandPressure", category="common",
        chief_complaint="시험 기간 내내 머리 양쪽을 띠로 조이는 듯한 둔통이 있어요",
        demographics={"age": 24, "sex": "male"}, ground_truth_diagnosis="tension_headache",
        answers={"character": "양측성 지속적 압박감, 박동성 아님", "aggravating": "스트레스와 오래 앉아 있을 때; 구역 없음, 빛 예민함 없음, 위약 없음"},
        exam_results={"vital_signs": "BP 120/78, HR 72, RR 14, Temp 36.7, SpO2 99%",
                      "neuro_exam": "정상, 국소 소견 없음"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind9_13_TurningInBedSpins", category="benign_mimic",
        chief_complaint="the room whirls for about 20 seconds whenever I turn over in bed",
        demographics={"age": 58, "sex": "female"}, ground_truth_diagnosis="bppv",
        answers={"onset": "2 days, only with head position changes", "associated_symptoms": "brief spinning, slight nausea; denies hearing loss, denies weakness, denies headache, denies slurred speech"},
        exam_results={"vital_signs": "BP 126/78, HR 74, RR 14, Temp 36.8, SpO2 99%",
                      "neuro_exam": "positional nystagmus on Dix-Hallpike, gait steady, otherwise normal"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind9_14_HotChurchFaint", category="benign_mimic",
        chief_complaint="站在闷热的礼堂里突然眼前发黑晕倒了一下",
        demographics={"age": 22, "sex": "female"}, ground_truth_diagnosis="vasovagal_syncope",
        answers={"onset": "站立时先觉恶心出汗然后短暂晕厥，很快清醒", "associated_symptoms": "晕前恶心、出汗、视野变窄; 无心悸, 无胸痛, 无抽搐",
                 "past_medical_history": "以前打针时也晕过"},
        exam_results={"vital_signs": "BP 116/72, HR 70, RR 14, Temp 36.7, SpO2 99%"},
        test_results={"ecg": "normal sinus rhythm"},
    ),
    SyntheticCase(
        case_id="Blind9_15_NewPillDizzyStanding", category="metabolic",
        chief_complaint="I get lightheaded and gray out each time I stand since starting a new pill",
        demographics={"age": 70, "sex": "male"}, ground_truth_diagnosis="orthostatic_hypotension",
        answers={"onset": "a few days after a new blood-pressure medication",
                 "associated_symptoms": "only on standing, resolves sitting; denies chest pain, denies palpitations",
                 "medications": "recently added a diuretic and an ACE inhibitor"},
        exam_results={"vital_signs": "BP 134/82 lying, 106/64 standing (24-point drop), HR 76 to 92 standing, SpO2 98%"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind9_16_SuddenFlutterDizzy", category="cardiac",
        chief_complaint="突然胸がドキドキして、めまいと息苦しさがあります",
        demographics={"age": 64, "sex": "male"}, ground_truth_diagnosis="cardiac_arrhythmia",
        answers={"onset": "1時間前に急に、脈が速く不規則", "associated_symptoms": "胸の違和感、ふらつき; 発熱なし",
                 "past_medical_history": "高血圧"},
        exam_results={"vital_signs": "BP 106/68, HR 152 irregularly irregular, RR 20, Temp 36.9, SpO2 96%",
                      "cardiovascular_exam": "不整な頻脈"},
        test_results={"ecg": "atrial fibrillation with rapid ventricular response"},
    ),
    SyntheticCase(
        case_id="Blind9_17_PaintedCeilingChestSore", category="benign_mimic",
        chief_complaint="my chest is sore in one spot after painting the ceiling all weekend",
        demographics={"age": 37, "sex": "male"}, ground_truth_diagnosis="musculoskeletal_chest_pain",
        answers={"onset": "since a weekend of overhead work", "character": "sharp, reproduced by pressing and twisting; denies sweating, denies dyspnea, denies arm radiation"},
        exam_results={"vital_signs": "BP 122/78, HR 70, RR 14, Temp 36.8, SpO2 99%",
                      "chest_exam": "point tenderness over the costochondral junction, reproduced on palpation"},
        test_results={"ecg": "normal sinus rhythm, no ischemic changes"},
    ),
    SyntheticCase(
        case_id="Blind9_18_LateSupperBurn", category="common",
        chief_complaint="야식 먹고 누우면 명치 위가 타는 듯하고 신물이 올라와요",
        demographics={"age": 46, "sex": "male"}, ground_truth_diagnosis="gerd",
        answers={"onset": "몇 주째, 야식과 눕는 자세에 악화", "associated_symptoms": "신물, 앉으면 완화; 발한 없음, 운동 시 악화 없음, 팔로 방사 없음"},
        exam_results={"vital_signs": "BP 124/80, HR 74, RR 14, Temp 36.7, SpO2 99%"},
        test_results={"ecg": "normal sinus rhythm"},
    ),
    SyntheticCase(
        case_id="Blind9_19_NavelToRLQBump", category="abdominal",
        chief_complaint="the ache started at my belly button and moved to the lower right, sharper now",
        demographics={"age": 20, "sex": "female"}, ground_truth_diagnosis="appendicitis",
        answers={"onset": "started peri-umbilical yesterday, now sharp RLQ", "associated_symptoms": "no appetite, nausea, low fever, hurts over bumps in the road; denies diarrhea"},
        exam_results={"vital_signs": "BP 120/76, HR 96, RR 16, Temp 37.9, SpO2 99%",
                      "abdominal_exam": "RLQ guarding and rebound at McBurney's point"},
        test_results={"wbc": "elevated white blood cell count"},
    ),
    # acute_pancreatitis -- lipase-driven (newly registered analyte), en
    SyntheticCase(
        case_id="Blind9_20_GallstoneBoringBack", category="abdominal",
        chief_complaint="severe upper-belly pain boring to my back after a fatty meal, keep vomiting",
        demographics={"age": 53, "sex": "female"}, ground_truth_diagnosis="acute_pancreatitis",
        answers={"onset": "hours after a rich dinner", "associated_symptoms": "pain eases leaning forward, repeated vomiting; denies chest pain",
                 "past_medical_history": "gallstones, does not drink"},
        exam_results={"vital_signs": "BP 126/80, HR 104, RR 20, Temp 37.9, SpO2 98%",
                      "abdominal_exam": "epigastric tenderness, voluntary guarding"},
        test_results={"lipase": "lipase over three times the upper limit of normal"},
    ),
    SyntheticCase(
        case_id="Blind9_21_BoardRigidAbdomenNSAID", category="dangerous_mimic",
        chief_complaint="my whole abdomen went rigid and any movement is agony",
        demographics={"age": 58, "sex": "male"}, ground_truth_diagnosis="acute_abdomen",
        answers={"onset": "sudden severe pain hours ago, now whole abdomen", "associated_symptoms": "feverish, no flatus; denies chest pain",
                 "past_medical_history": "peptic ulcer, daily NSAIDs"},
        exam_results={"vital_signs": "BP 104/64, HR 118, RR 24, Temp 38.3, SpO2 97%",
                      "abdominal_exam": "board-like rigidity, diffuse rebound, absent bowel sounds"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind9_22_TarryStoolsAnticoag", category="gi_bleeding",
        chief_complaint="黒いタール状の便と立ちくらみが続いています",
        demographics={"age": 70, "sex": "male"}, ground_truth_diagnosis="gi_bleeding",
        answers={"onset": "2日前から黒色便", "associated_symptoms": "ふらつき、易疲労; 吐血なし, 発熱なし",
                 "medications": "抗凝固薬と時々鎮痛薬"},
        exam_results={"vital_signs": "BP 98/60, HR 112, RR 18, Temp 36.8, SpO2 98%",
                      "abdominal_exam": "心窩部圧痛、直腸診で黒色便"},
        test_results={"hemoglobin": "hemoglobin low at 8.0 g/dL"},
    ),
    SyntheticCase(
        case_id="Blind9_23_PicnicVomitDiarrhea", category="common",
        chief_complaint="野餐后上吐下泻，肚子一阵阵绞痛",
        demographics={"age": 30, "sex": "male"}, ground_truth_diagnosis="gastroenteritis",
        answers={"onset": "聚餐后大约半天", "associated_symptoms": "水样腹泻、呕吐、阵发绞痛; 无血便, 无高热, 无固定压痛",
                 "social_history": "同行者也有类似症状"},
        exam_results={"vital_signs": "BP 112/70, HR 94, RR 16, Temp 37.5, SpO2 99%",
                      "abdominal_exam": "全腹轻压痛，肠鸣活跃，无反跳痛"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind9_24_WaveFlankToGroin", category="abdominal",
        chief_complaint="waves of severe left flank pain keep radiating down to my groin",
        demographics={"age": 43, "sex": "male"}, ground_truth_diagnosis="nephrolithiasis",
        answers={"onset": "colicky since morning, can't sit still", "associated_symptoms": "nausea, pink urine; denies fever, denies chills",
                 "past_medical_history": "prior kidney stone"},
        exam_results={"vital_signs": "BP 144/88, HR 96, RR 18, Temp 36.9, SpO2 99%",
                      "abdominal_exam": "left CVA tenderness, soft abdomen"},
        test_results={"urinalysis": "microscopic hematuria, no nitrites, no leukocyte esterase"},
    ),
    # uncomplicated_cystitis -- dipstick-driven (newly registered), ko
    SyntheticCase(
        case_id="Blind9_25_BurningFrequencyWell", category="common",
        chief_complaint="이틀 전부터 소변이 따갑고 자주 마렵지만 다른 곳은 괜찮아요",
        demographics={"age": 26, "sex": "female"}, ground_truth_diagnosis="uncomplicated_cystitis",
        answers={"onset": "이틀 전부터", "associated_symptoms": "배뇨통, 빈뇨, 잔뇨감; 옆구리 통증 없음, 발열 없음, 오한 없음, 구역 없음"},
        exam_results={"vital_signs": "BP 118/74, HR 74, RR 14, Temp 36.8, SpO2 99%",
                      "abdominal_exam": "치골 상부 경미한 압통, 늑골척추각 압통 없음"},
        test_results={"urinalysis": "positive leukocyte esterase and positive nitrites"},
    ),
    SyntheticCase(
        case_id="Blind9_26_FlankRigorsFever", category="infectious",
        chief_complaint="one-sided lower back pain with shaking chills and high fever",
        demographics={"age": 37, "sex": "female"}, ground_truth_diagnosis="pyelonephritis",
        answers={"onset": "dysuria 3 days then fever and back pain today", "associated_symptoms": "nausea, rigors; denies vaginal bleeding",
                 "past_medical_history": "recurrent UTIs"},
        exam_results={"vital_signs": "BP 116/72, HR 108, RR 20, Temp 39.1, SpO2 98%",
                      "abdominal_exam": "marked right CVA tenderness"},
        test_results={"urinalysis": "pyuria with positive nitrites", "wbc": "leukocytosis"},
    ),
    SyntheticCase(
        case_id="Blind9_27_LatePeriodPelvicOneSide", category="pregnancy",
        chief_complaint="sharp pain low on one side with light spotting and my period is late",
        demographics={"age": 30, "sex": "female"}, ground_truth_diagnosis="ectopic_pregnancy",
        answers={"onset": "pelvic pain since yesterday, sharp on the left", "associated_symptoms": "light spotting, lightheaded; denies urinary symptoms, denies diarrhea",
                 "last_menstrual_period": "about 7 weeks ago, then missed"},
        exam_results={"vital_signs": "BP 104/66, HR 104, RR 18, Temp 37.0, SpO2 99%",
                      "abdominal_exam": "left lower quadrant tenderness, cervical motion tenderness"},
        test_results={"beta_hcg": "urine pregnancy test positive"},
    ),
    SyntheticCase(
        case_id="Blind9_28_ThirstBreathingHardTeen", category="metabolic",
        chief_complaint="I'm parched, peeing nonstop, nauseated and breathing deep and fast",
        demographics={"age": 17, "sex": "female"}, ground_truth_diagnosis="diabetic_ketoacidosis",
        answers={"onset": "worsening over 2 days, missed insulin", "associated_symptoms": "abdominal pain, vomiting, deep rapid breathing; denies chest pain",
                 "past_medical_history": "type 1 diabetes"},
        exam_results={"vital_signs": "BP 108/68, HR 120, RR 30 and deep, Temp 37.2, SpO2 99%",
                      "general_exam": "dry mucous membranes, fruity breath"},
        test_results={"glucose_point_of_care": "blood glucose 486 mg/dL", "ketones": "serum ketones strongly positive",
                      "bicarbonate": "bicarbonate 10 mEq/L"},
    ),
    SyntheticCase(
        case_id="Blind9_29_MissedLunchShaky", category="metabolic",
        chief_complaint="my elderly mother went sweaty, shaky and confused before dinner",
        demographics={"age": 79, "sex": "female"}, ground_truth_diagnosis="hypoglycemia",
        answers={"onset": "over 20 min after skipping lunch", "associated_symptoms": "diaphoretic, tremulous, confused, better with juice; denies focal weakness, denies chest pain",
                 "medications": "takes glyburide"},
        exam_results={"vital_signs": "BP 140/84, HR 98, RR 16, Temp 36.8, SpO2 98%",
                      "neuro_exam": "confused, no focal deficit, no neck stiffness"},
        test_results={"glucose_point_of_care": "fingerstick glucose 42 mg/dL"},
    ),
    SyntheticCase(
        case_id="Blind9_30_MissedDialysisWeak", category="metabolic",
        chief_complaint="weak all over with a fluttering heartbeat since I missed dialysis",
        demographics={"age": 60, "sex": "male"}, ground_truth_diagnosis="severe_electrolyte_disorder",
        answers={"onset": "building over a day after a missed session", "associated_symptoms": "muscle weakness, palpitations; denies fever, denies focal weakness",
                 "past_medical_history": "end-stage renal disease on hemodialysis"},
        exam_results={"vital_signs": "BP 150/88, HR 56, RR 16, Temp 36.8, SpO2 98%",
                      "neuro_exam": "diffuse weakness, no focal deficit"},
        test_results={"potassium": "potassium 7.2 mEq/L", "ecg": "peaked T waves with widened QRS"},
    ),
    SyntheticCase(
        case_id="Blind9_31_CareHomeAlteredHot", category="infectious",
        chief_complaint="my father from his care home is confused, hot and his blood pressure is low",
        demographics={"age": 84, "sex": "male"}, ground_truth_diagnosis="sepsis",
        answers={"onset": "drowsy and hot over a day", "associated_symptoms": "confused, not drinking, cool clammy skin, productive cough 2 days",
                 "past_medical_history": "recent urinary catheter"},
        exam_results={"vital_signs": "BP 84/50, HR 124, RR 26, Temp 39.0, SpO2 92%",
                      "general_exam": "confused, poor perfusion, cap refill 4s"},
        test_results={"lactate": "lactate 4.5 mmol/L", "wbc": "leukocytosis"},
    ),
    SyntheticCase(
        case_id="Blind9_32_NutBarHivesThroat", category="dangerous_mimic",
        chief_complaint="minutes after a snack bar I broke out in hives and my throat feels tight",
        demographics={"age": 25, "sex": "male"}, ground_truth_diagnosis="anaphylaxis",
        answers={"onset": "within minutes of eating", "associated_symptoms": "hives, throat tightness, wheeze, lightheaded; denies chest pressure",
                 "past_medical_history": "tree-nut allergy"},
        exam_results={"vital_signs": "BP 90/56, HR 124, RR 26, Temp 36.9, SpO2 92%",
                      "general_exam": "diffuse urticaria, lip swelling, stridor"},
        test_results={},
    ),
    SyntheticCase(
        case_id="Blind9_33_PresentationRacingDoom", category="benign_mimic",
        chief_complaint="during a presentation my heart raced, hands tingled and a wave of dread hit",
        demographics={"age": 29, "sex": "female"}, ground_truth_diagnosis="panic_attack",
        answers={"onset": "peaked in minutes, eased over 20 min", "associated_symptoms": "palpitations, perioral tingling, dread; denies exertional chest pain, denies fever",
                 "past_medical_history": "recurrent stress episodes, otherwise healthy"},
        exam_results={"vital_signs": "BP 128/82, HR 104, RR 22, Temp 36.8, SpO2 99%",
                      "cardiovascular_exam": "tachycardic, regular, no murmur"},
        test_results={"ecg": "sinus tachycardia, no ischemic changes", "troponin": "troponin not elevated"},
    ),
    SyntheticCase(
        case_id="Blind9_34_DaycareSnifflesSoreThroat", category="common",
        chief_complaint="鼻水と喉の痛みが二日前から、微熱もあります",
        demographics={"age": 34, "sex": "female"}, ground_truth_diagnosis="viral_uri",
        answers={"duration": "二日前から", "associated_symptoms": "くしゃみ、軽い喉の痛み; 高熱なし, 息切れなし, 耳痛なし"},
        exam_results={"vital_signs": "BP 116/72, HR 76, RR 14, Temp 37.2, SpO2 99%",
                      "throat_exam": "軽度咽頭発赤、滲出物なし"},
        test_results={},
    ),

    # --- UNIT-SAFETY / DATA-FRESHNESS axis (the reasoning change this round) ------------------------
    # 35. Creatinine reported in SI umol/L must NOT be read as a huge mg/dL number; true story is a
    #     benign stone, renal function is normal.
    SyntheticCase(
        case_id="Blind9_35_SIUnitCreatinineStone", category="unit_safety",
        chief_complaint="colicky right flank pain radiating to the groin, comes in waves",
        demographics={"age": 39, "sex": "male"}, ground_truth_diagnosis="nephrolithiasis",
        answers={"onset": "since this morning, waves", "associated_symptoms": "nausea, pink urine; denies fever, denies chills"},
        exam_results={"vital_signs": "BP 140/86, HR 92, RR 18, Temp 36.9, SpO2 99%",
                      "abdominal_exam": "right CVA tenderness"},
        # 88 umol/L == 1.0 mg/dL (normal). Must not be misread as 88 (critical) -> no false AKI/sepsis pull.
        test_results={"creatinine": "creatinine 88 umol/L", "urinalysis": "microscopic hematuria, no nitrites"},
    ),
    # 36. Hemoglobin reported in SI g/L; a real GI bleed -- the g/L number must not read as 'normal'.
    SyntheticCase(
        case_id="Blind9_36_SIUnitHemoglobinBleed", category="unit_safety",
        chief_complaint="dark tarry stools for two days and I feel faint standing up",
        demographics={"age": 66, "sex": "male"}, ground_truth_diagnosis="gi_bleeding",
        answers={"onset": "black stools 2 days", "associated_symptoms": "dizzy on standing, fatigue; denies chest pain, denies fever",
                 "medications": "daily aspirin"},
        exam_results={"vital_signs": "BP 98/60, HR 112, RR 18, Temp 36.8, SpO2 98%",
                      "abdominal_exam": "epigastric tenderness, melena on rectal exam"},
        # 74 g/L == 7.4 g/dL (low). The g/L value must not be read as 74 (normal) and hide anemia; the
        # melena + hemodynamics still drive gi_bleeding regardless.
        test_results={"hemoglobin": "hemoglobin 74 g/L"},
    ),
    # 37. Lipase-confirmed pancreatitis, mixed ko/en.
    SyntheticCase(
        case_id="Blind9_37_MixedLipasePancreatitis", category="unit_safety",
        chief_complaint="명치에서 등으로 뻗치는 severe pain, 계속 vomiting 해요",
        demographics={"age": 49, "sex": "male"}, ground_truth_diagnosis="acute_pancreatitis",
        answers={"onset": "어젯밤 heavy drinking 후", "associated_symptoms": "boring to the back, relieved leaning forward; 설사 없음",
                 "social_history": "잦은 음주"},
        exam_results={"vital_signs": "BP 112/70, HR 106, RR 20, Temp 37.8, SpO2 97%",
                      "abdominal_exam": "epigastric tenderness, reduced bowel sounds"},
        test_results={"lipase": "lipase markedly elevated, over three times the upper limit"},
    ),
    # 38. Stale normal troponin must not reassure against a new acute MI.
    SyntheticCase(
        case_id="Blind9_38_StaleTroponinNewMI", category="data_freshness",
        chief_complaint="crushing chest pressure for an hour with sweating and nausea",
        demographics={"age": 62, "sex": "male"}, ground_truth_diagnosis="acute_coronary_syndrome",
        answers={"onset": "sudden crushing pressure an hour ago", "associated_symptoms": "diaphoresis, nausea, jaw radiation; denies fever",
                 "past_medical_history": "a normal troponin 8 months ago; hypertension, smoker"},
        exam_results={"vital_signs": "BP 158/96, HR 100, RR 20, Temp 36.9, SpO2 96%"},
        test_results={"ecg": "new inferior ST elevation", "troponin": "current troponin elevated and rising"},
    ),
    # 39. Wrong-unit glucose (mmol/L) must not be misread as a hypoglycemic mg/dL number; the real
    #     issue is sepsis, not glucose.
    SyntheticCase(
        case_id="Blind9_39_WrongUnitGlucoseSepsis", category="unit_safety",
        chief_complaint="feverish, confused and my blood pressure keeps dropping",
        demographics={"age": 77, "sex": "female"}, ground_truth_diagnosis="sepsis",
        answers={"onset": "hot and drowsy over a day", "associated_symptoms": "confusion, productive cough, poor intake; denies focal weakness",
                 "past_medical_history": "diabetes, recent catheter"},
        exam_results={"vital_signs": "BP 86/52, HR 122, RR 26, Temp 39.0, SpO2 92%",
                      "general_exam": "confused, poor perfusion"},
        # glucose 6.1 mmol/L (~110 mg/dL, normal) must NOT be read as a low mg/dL value; lactate drives it.
        test_results={"glucose_point_of_care": "glucose 6.1 mmol/L", "lactate": "lactate 4.1 mmol/L", "wbc": "leukocytosis"},
    ),

    # --- multimorbidity / conflicting / sparse / anchoring axis ------------------------------------
    # 40. prior migraine + NEW focal deficit -> must not anchor on migraine (stroke).
    SyntheticCase(
        case_id="Blind9_40_MigraineHistoryNewDeficit", category="anchoring",
        chief_complaint="another headache, but this time my right arm is weak and words won't come",
        demographics={"age": 62, "sex": "female"}, ground_truth_diagnosis="ischemic_stroke",
        answers={"onset": "sudden 1 hour ago, unlike my usual migraines", "associated_symptoms": "right arm weakness, word-finding trouble; the headache is mild this time",
                 "past_medical_history": "long history of migraine with aura; hypertension"},
        exam_results={"vital_signs": "BP 176/96, HR 84, RR 16, Temp 36.8, SpO2 98%",
                      "neuro_exam": "right arm drift, expressive aphasia, NEW focal deficit"},
        test_results={},
    ),
    # 41. prior anxiety + objective hypoxia -> must not anchor on panic (PE).
    SyntheticCase(
        case_id="Blind9_41_AnxietyHistoryHypoxia", category="anchoring",
        chief_complaint="I feel panicky and breathless like my anxiety, but it won't settle",
        demographics={"age": 40, "sex": "female"}, ground_truth_diagnosis="pulmonary_embolism",
        answers={"onset": "sudden breathlessness today", "associated_symptoms": "pleuritic right chest pain, one swollen calf; more than my usual panic",
                 "past_medical_history": "generalized anxiety; recent long flight, oral contraceptive"},
        exam_results={"vital_signs": "BP 118/76, HR 118, RR 26, Temp 37.1, SpO2 89%",
                      "extremity_exam": "right calf swelling and tenderness"},
        test_results={"d_dimer": "D-dimer elevated"},
    ),
    # 42. sparse dangerous -- one-line worst headache.
    SyntheticCase(
        case_id="Blind9_42_SparseWorstHeadache", category="sparse_information",
        chief_complaint="worst headache ever, hit all at once",
        demographics={"age": 54, "sex": "male"}, ground_truth_diagnosis="subarachnoid_hemorrhage",
        answers={"onset": "instant, minutes ago"},
        exam_results={"vital_signs": "BP 178/102, HR 90, RR 18, Temp 37.0, SpO2 98%"},
        test_results={},
    ),
    # 43. negative-centric reassuring benign headache.
    SyntheticCase(
        case_id="Blind9_43_NegativeCentricHeadache", category="negative_centric",
        chief_complaint="my usual dull two-day headache is back",
        demographics={"age": 33, "sex": "female"}, ground_truth_diagnosis="tension_headache",
        answers={"onset": "gradual over 2 days, like my monthly ones",
                 "associated_symptoms": "denies sudden onset, denies worst-ever, denies neck stiffness, denies fever, denies aura, denies weakness or numbness, denies vomiting",
                 "character": "mild bilateral pressure relieved by rest"},
        exam_results={"vital_signs": "BP 120/76, HR 72, RR 14, Temp 36.8, SpO2 99%",
                      "neuro_exam": "completely normal, no meningismus"},
        test_results={},
    ),
    # 44. conflicting -- fever+cough but pleuritic+hypoxia+DVT -> PE over pneumonia.
    SyntheticCase(
        case_id="Blind9_44_ConflictingPEvsPneumonia", category="conflicting_findings",
        chief_complaint="low fever and a cough but also sudden sharp pain when I breathe in",
        demographics={"age": 47, "sex": "female"}, ground_truth_diagnosis="pulmonary_embolism",
        answers={"onset": "sharp pleuritic pain and breathlessness came on suddenly today",
                 "associated_symptoms": "one swollen tender calf, scant dry cough, low-grade temperature",
                 "medications": "hormone replacement therapy", "past_medical_history": "recent long car journey"},
        exam_results={"vital_signs": "BP 118/76, HR 118, RR 26, Temp 37.6, SpO2 90%",
                      "chest_exam": "clear lungs, no consolidation", "extremity_exam": "left calf swelling"},
        test_results={"d_dimer": "D-dimer elevated", "chest_xray": "no consolidation or effusion"},
    ),
]
