# Round U 후속 — 새 임상 관계·어휘의 출처

모든 항목은 엔지니어링 에이전트가 작성했고 임상의 검토를 받지 않았다(`PENDING`). 위험도는 어떤 항목에서도 진단 점수를 올리지 않는다.

## 새 KB 특징(임상 관계)

| 위치 | 추가 내용 | 출처 | 범위 제한 |
|---|---|---|---|
| `knowledge/diseases/cardiac.json` `cardiac_arrhythmia.typical_features` | `syncope without warning`, `palpitations before syncope` | Brignole M et al., 2018 ESC Guidelines for the diagnosis and management of syncope, Eur Heart J 2018;39:1883-1948, Table 5 (arrhythmic syncope high-risk features), doi:10.1093/eurheartj/ehy037 | 부정맥 **범주**만 지지. 리듬 subtype·ECG 결과를 만들지 않음. 엔트리의 `round_u_followup_provenance`에 기록 |
| `knowledge/diseases/neuro.json` `ischemic_stroke.typical_features` | `focal neurological deficit on examination` (진찰 소견, objective-only) | Sacco RL et al., An Updated Definition of Stroke, Stroke 2013;44:2064-2089; Powers WJ et al., 2019 AHA/ASA acute ischemic stroke guideline, Stroke 2019;50:e344 | 영상 확진이 아님. 부정된 진찰("No focal deficit")은 매칭 안 됨 |
| `knowledge/tier2_enrichment.json` `sjogren_syndrome` | 지속 안구건조, 지속 구강건조, 모래알 느낌, 마른 음식 삼킬 때 물 필요, 반복 침샘 종창 | Vitali C et al., Ann Rheum Dis 2002;61:554-558 (AECG 2002, Table 1 items I–II); Shiboski CH et al., Arthritis Rheumatol 2017;69:35-45 (2016 ACR/EULAR, 진입 기준) | confirmatory_findings는 미해결(검사 항목은 예선 불가). 필드별 `provenance` 포함 |
| `final_decision.py` 자궁외임신 required context | 통증 단독은 임신 맥락이 아님(생리 지연·임신·질출혈·양성 검사 필요) | NICE NG126 section 1.2/1.3(기존 인용 유지) | 후보 삭제·점수 변경·긴급 계획 변경 없음 |

## 어휘(의미 동일성, 새 임상 주장 아님)

| 대상 KB 문구 | 추가 표현 | 근거 |
|---|---|---|
| 영국/미국 철자 | oedema/edema, diarrhoea/diarrhea, haem-/hem-, -aemia/-emia, oesophag-/esophag-, paed-/ped-, foet-/fet-, tumour/colour/behaviour | 동일 단어의 철자 변형. KB 문구와 관찰 양쪽을 같은 형태로 정규화 |
| `abdominal pain` | stomach pain, stomach ache, tummy ache … | MedlinePlus "Abdominal pain" (003120): "often referred to as the stomach region or belly". bare "stomach"은 매핑하지 않음 |
| `kussmaul breathing` | deep laboured breathing, deep sighing respirations … | StatPearls "Kussmaul Respirations" (NBK470309) |
| `seizure` | short/brief fit, a fit this morning … (사건 표현만) | NHS "Epilepsy": seizures(fits). bare "fit"은 계속 제외 |
| `unable to lie flat` | three pillows to sleep … | NICE CKS "Heart failure – chronic": orthopnoea |
| `sulfonylurea use` | glibenclamide, gliclazide, tolbutamide | BNF sulfonylurea 계열(glibenclamide = glyburide) |
| `known diabetes`, `missed insulin doses`, `recent similar illness contact`, `diffuse crampy abdominal pain`, `food exposure`, `recent trauma`, `reproducible with palpation`, `ankle swelling`, `leg swelling`, `waking breathless at night`, `crackles in lungs`, `rebound tenderness`, `lying still`, `right upper quadrant pain`, `big toe joint involvement`, `night onset`, `visual disturbance`, `night time pain`, `persistent dry eyes/mouth` | 환자 표현 변형 | 기존 KB 문구의 동의 표현. 각 목록은 해당 문구 하나만 돕는다(`lay_language.py` 규칙). 개발 사례에서 발견되었음을 공개 |
| 한국어 `epigastric pain radiating to back`, `alcohol use` | 윗배·명치 … 등까지 뻗침, 과음·폭음 | 기존 KB 문구의 한국어 표현(`multilingual_concepts.py`) |
| 일본어 회전성 어지럼·두위 유발 | ぐるぐる回る, 回転性めまい, 寝返り, 数秒 | 기존 Round U 관계 문법(`feature_relations.py`)의 일본어 표현 |

## 검색 어휘 확장

`nova_agent/retrieval_vocabulary.py`는 위 기존 별칭과 기존 한/일 개념표만 사용해 관찰된 표현을 **기존** KB 문구로 바꾼다. 부정, 가족, 과거 문장은 제외한다. 최대 8개 용어이고 기존 12개 확장 상한 안에 있다. 자유 생성 질의, 진단명, 정답 정보, 위험도 가중은 쓰지 않는다. 결과는 결정 범위 memo에만 저장하고 프로세스 전체 캐시에는 저장하지 않는다(`tests/test_case_isolation.py`).
