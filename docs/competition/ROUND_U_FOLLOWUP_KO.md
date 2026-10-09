# Round U 잔여 작업서 — 실제 실패와 별도 검증 범위

대상 runtime: `da7cfca7eb80f09af82019326f9964a285946f1d`. 이번 구현 프롬프트와 완료 증거는 `ROUND_U_IMPLEMENTATION_PROMPT_KO.md`, `ROUND_U_REPAIR_REPORT_KO.md`에 있다. 이 문서는 **아직 해결되지 않은 부분**이다. 기존 labels/scorer/fixtures를 바꾸거나 위험도를 진단 보너스로 복구하지 않는다. U20/U12/U10은 개발 세트이며, 다음 수정부터 Closing U8도 개발 세트다.

## P0. 얕은 근거로 구체적인 위험 원인 명명

- 위치: `nova_agent/final_decision.py:166 support_problems`, `:220 decide_final`; `nova_agent/differential.py:593 _score_disease`; `nova_agent/disposition.py:37 disposition_for`.
- 재현: 동일 Round P 예선의 `ValP_10`은 양성 근골격성 흉통 라벨인데 `Tension Pneumothorax`를 출력한다. 최종 support는 `chest pain after trauma` 하나다. 이번에 새로 생긴 오답은 아니지만 여전히 중요한 과잉 명명이다. 현재 alias/feature가 기록된 사실인지와 그 사실이 원인을 구별하는지는 다르다.
- 재현: 기존 수용 개발 세트 `Fresh05`는 DKA 라벨인데 `Acute Pancreatitis`를 출력한다. DKA는 최종 2위에 존재하며 support는 `polyuria`, `polydipsia`; 1위는 `nausea`, `vomiting`이다. 25회 상호작용 후 `information_exhausted`, 미해결 위험 대안 2개 상태다. 같은 pancreatitis 명명은 양성 위장관 라벨 `Fresh16`에도 발생한다. 단순 retrieval 누락으로 분류하면 안 된다.
- Fresh05 원문에는 insulin pump 중단, 후속 기록에는 type 1 diabetes, 실제 EXAM에는 deep laboured breathing/dry mucous membranes가 있다. 이 관찰이 DKA support로 전달되지 않은 부분과 순위 결정을 구분해 추적한다. 긴급 처분과 glucose/ketone 계획은 현재도 보존되지만, 그것이 잘못된 1위 명명을 정당화하지는 않는다.
- 명세: 기존 per-observation source/span과 generic/specific/risk/objective 구분을 재사용한다. 단순 외상 관계 또는 서로 겹치는 일반 증상이 특정 원인의 확정적 지지로 승격되는 경로를 제한한다. disease ID를 하드코딩해 정답을 선택하지 않는다. 현재 `dangerous_if_missed` 메타데이터와 실제 임상 중증도가 일치한다는 가정도 하지 않는다. 일반성 검사는 높은 위험 플래그에만 의존하지 않아야 한다.
- 부족한 정보: 예선에서 glucose/ketone/전해질 등 얻지 않은 검사를 추정할 수 없다. 충분히 구별하지 못하면 기존 미분화 종료와 관찰된 위험에 따른 계획을 분리한다. 이 수정이 DKA 라벨을 반드시 맞힌다고 약속하지 않는다.
- 회귀: 실제 현재 문서 확진, 실제 관찰된 특정 객관 소견, 진단 지지 흉통/위장관/내분비 대조군, 단일 외상성 통증, 심한 맥박 이상, EXAM 거절. 위험 진단을 일괄 억제하지 않는다.
- 완료: 위 과잉 명명 기전의 새 대조쌍 통과, 기존 여러 근거의 위험 사례 유지, 새 critical miss 0. 기존 label과 미분화 결과의 차이는 오답으로 계속 집계한다.

## P1. 남은 전해질·진단 계층·명칭 문제

- `ValP_12`: severe_electrolyte_disorder 라벨, 실제 최종 `Undifferentiated presentation`; 확인된 양성은 confusion/headache/nausea다. 이 사례의 남은 오답과 저나트륨 확정 불가능성을 구분한다. `missing_info.py:157 analyze`, `action_selector.py:211 generate_and_select`에서 실제 약물/섭취/손실/신장 관련 질문 후보와 선택 이유를 추적하되, 한 단서만으로 전해질 이상을 올리지 않는다.
- `ValP_17`: cardiac_arrhythmia 라벨과 미분화 종료의 차이. 실제 HR38/실신의 긴급 계획과 ECG **계획**은 보존한다. 맥박수만으로 리듬 원인이나 subtype을 생성하지 않는다.
- `ValP_21`: acute_abdomen 라벨과 Perforated Viscus 출력은 상위 증후군과 구체 원인의 계층 문제를 포함한다. 구체 원인 지지가 충분한지 별도로 검토한다. 부모/자식을 무조건 정답으로 인정하도록 scorer를 느슨하게 바꾸지 않는다.
- `ValP_08`: heart_failure 라벨과 Community-Acquired Pneumonia 출력. crackles/dyspnea의 공유 소견과 heart_failure/Chronic Heart Failure 명칭 매핑을 별도로 추적한다. 모든 차이를 동의어 문제로 설명하지 않는다.
- 완료: 각 사례에 대해 획득 사실, 미획득 정보, 후보 순위, 행동 후보/선택 이유, 명명 근거를 고정 형식으로 기록하고 실제 추론 오류/임상적 모호성/명칭 문제를 구분한다. TEST 없는 경로에서 확진 검사 완료를 종료 필수 조건으로 두지 않는다.

## P1. 초기 retrieval과 Tier-2 깊이

- 위치: `retrieval_pipeline.py:116 build_signal_queries`, `:169 retrieve_high_recall`, `:253 lightweight_rerank`; `scripts/prioritize_tier2_depth.py`, `scripts/analyze_rerank_losses.py`, `scripts/audit_round_u_retrieval.py`.
- 최종 주호소 개발 proxy: Top150 118/164, Top25 117/164. 진단 후보를 안전 watch가 밀어내는 문제는 개선됐지만 최초 검색 손실은 여전히 크다. 전체 scripted-history를 미리 준 상한은 실제로 얻은 대화 성적이 아니다.
- M long-tail 종료 시 Top25는 25/26→24/26이다. 새 손실 `RoundM_106`(Pelvic Inflammatory Disease)은 active에서 최종 1위를 유지하지만 retrieval/rerank 경로와 active 직접 유지 경로를 혼동하지 않는다. 전체 Top25 100/123→114/123 개선과 이 하위 집합의 회귀를 함께 보고한다.
- 명세: 실패를 vocabulary/lay-language/follow-up representation/synonym/weighting/query construction으로 분류한다. 실제 관찰만 existing canonical concept/alias/anatomy/objective feature로 제한 확장한다. Top150·Weighted RRF·Top25를 유지하고 LLM 자유 확장을 쓰지 않는다.
- Tier-2 1,246 중 enrichment 항목 없는 수 1,163. 기존 83항목도 임상 완성 인증이 아니다. 이번 새 깊이 프로필은 0개다. 개발 검색 빈도/유용한 감별/위험/혼동 관계로 30–80개 우선 집합을 먼저 결정한다. 각 새 사실은 공신력 있는 원문과 필드별 provenance가 필요하며, 출처가 없으면 빈칸/미해결로 둔다.
- 완료: 단순 질환 수 증가 없이 초기/후속 retrieval, rerank, active, long-tail Top1/5/10을 각각 개선. 기존 Tier-1 새 위험 누락 없음. 위험도 자체는 진단 점수로 사용하지 않는다.

## P1. 관계 일반화와 행동 비용

- 위치: `feature_relations.py`, `matching.py`, `clinical_concepts.py:181 canonical_findings_for`, `:262 bedside_exam_for_feature`, `resolution.py:148 workup_coverage`, `stop_policy.py:101 evaluate`.
- 식후/자세 방향, 복통의 severe/lower, fluttering, 흉부 압박/방사, 회전감의 제한된 정규화는 구현됐다. 유한한 패턴만으로 임의의 자연어 관계를 완전히 해결했다고 주장하지 않는다. 복수 절/대명사/긴 수식/한국어 조합은 새 동결 대조군이 필요하다.
- 기존 fixture의 `dix_hallpike`처럼 실행 catalog에 없는 키를 이미 수행된 EXAM으로 처리하지 않는다. 실제 지원되는 검사만 매핑하고 공식 프로토콜을 추측하지 않는다.
- 미실시/불명/거절/불가능은 질환 배제가 아니다. 반면 의미 없는 반복 EXAM도 무한히 수행하지 않는다. Round P 불필요 EXAM은 59→74로 증가했으므로 정확도만 보고 효율 개선을 주장하지 않는다.
- shallow ontology 대안에 도입한 corroboration은 엔지니어링 heuristic이다. 같은 관찰의 두 별칭이 독립 근거 2개로 세어지는지 source/span으로 별도 검사하고, 실제 단일 특이 소견/위험 활력징후 대조군을 보존한다. 안전 대안을 조용히 삭제하거나 negative로 표시하지 않는다.
- 완료: 실제 반복/의미 중복/거절 횟수와 미해결 위험 대안을 각각 집계. 긴급 처분 false positive와 false negative를 사전 정의한 새로운 대조군으로 측정한다.

## 별도 평가 도구 작업 — 알고리즘 성적과 섞지 않음

- 위치: `evaluation/preliminary_driver.py:111 _episode`, `:223 _score`; SyntheticCase 기본 응답.
- 정의되지 않은 질문이 기본 "No"로 응답되는 기존 fixture 구조는 미지의 정보를 임상적 음성으로 바꿀 수 있다. 이번 기준 비교에서는 그대로 유지했다. 기존 `unscripted_unknown` variant는 별도 실험으로만 보고하고 원래 결과를 교체하지 않는다.
- `RoundM_066` 예선은 "Bad tummy since last night"와 scripted `diarrhea` 외 추가 원인 지지가 빈약하다. 새 명명 제한으로 기존 gastroenteritis 라벨을 놓친다면 그것은 scored 회귀로 공개해야 한다. 이 사례 하나를 맞히려고 단일 설사에서 원인을 무조건 명명하도록 복구하지 않는다. 추가 병력/진찰이나 임상 판정이 필요하다.
- 행동 계약은 모든 임상적 실패를 포괄하지 않는다. U12/U10에서 채점 정답과 양성 사례의 과도한 긴급 처분을 별도로 검토해 결함을 발견했다. 새 평가에서는 라벨, 미분화 허용, 긴급 처분, SOAP 사실 보존을 실행 전에 각각 고정한다.
- TEST 허용 `evaluation.failure_analysis`는 채점 제외 `Headache02_InsufficientInfo`에서 Bacterial Meningitis 명명을 보고한다. excluded라는 이유로 과잉 명명 검토에서 삭제하지 않는다. 예선과 TEST 허용 경로의 최종 진단 정책 차이도 별도로 확인한다.
- ClosingU_05의 급성 복부 증후군은 원인 라벨이 불명확해 채점 제외이며 urgent 계약만 있다. evaluator의 premature 값과 사전 계약 결과를 서로 대체하지 않는다.

## 후속 최종 검증

1. 이 보고서에서 본 모든 사례는 개발/회귀로 취급한다. 새 합성 확인 세트는 구현 노출, 동결 시각, fixture/정답/계약 해시를 실행 전에 기록한다. 임상 전문가 판정이 없으면 독립 임상 검증이라고 부르지 않는다.
2. mock + competition retrieval로 같은 예선230/P/Q/R/S/T/U와 TEST 허용 M/G/I/J 등 비교. 새 정답/새 오답/critical miss/불필요 명명/처분/턴을 별도 보고한다. 전체 테스트·규칙 검사·source mirror·격리 ZIP 감사·독립 mock을 최종 runtime에 연결한다.
3. 공식 모델/인터페이스 연결이 없으면 NOT VERIFIED를 유지한다. API 키나 모델 다운로드로 우회하지 않는다. provenance coverage PASS는 권리 검토 완료가 아니며, 현재 permission BLOCKED/공식 NOT READY를 임의 해제하지 않는다.
4. 상세 trace/XML/ZIP 공개 제한과 소스 공개를 분리한다. 공개 CURRENT_RELEASE의 역사적 포인터를 현재 소스 전체의 검증 증명처럼 표현하지 않는다.
