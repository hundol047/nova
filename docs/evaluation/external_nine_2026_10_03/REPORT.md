# 외부 고난도 9개 증례: 첫 실행 결과

2026-10-03 / 연구·모델 평가 전용. DiagnosisArena의 임상 사용 금지 조건을 따른다.

## 결과

- 9/9 실행 완료, 원문 최종진단 완전 일치 0/9 (0%).
- 판단 유보(unknown) 1건, 원문 최종진단과 다른 질환 출력 8건.
- 실제 LLM 호출 0회. mock 제공자를 통한 현행 규칙 기반 DoctorAgent 실행.
- 소요 92.11초. 학습·가중치 변경·임상 프로필 수정 없음.
- 이는 사전에 골라 살펴본 미지원 관련 복합 증례 9개의 결과다. 전체 NOVA 정확도로 일반화할 수 없다.
- 이전 합성 400/1,200건 점수와 입력·정답·사례 구성·평가 방식이 달라 직접 증감 비교할 수 없다.

| 사례 ID | 원문 최종진단 | NOVA 출력 |
|---|---|---|
| 87 | Myopericarditis | Acute Coronary Syndrome |
| 140 | Pheochromocytoma-induced cardiomyopathy | Aortic Dissection |
| 514 | Effusive-constrictive pericarditis | unknown |
| 586 | Rifampin-induced acute renal failure due to heme pigment-related injury | Gastrointestinal Bleeding |
| 628 | Peri-infarction pericarditis (PIP) | Acute Coronary Syndrome |
| 697 | Valproic acid-induced aplastic crisis and Stevens-Johnson syndrome | Asthma / COPD Exacerbation |
| 766 | Myopericarditis with cardiac conduction system involvement due to monkeypox virus infection with concurrent Lyme disease | Tension Pneumothorax |
| 770 | Leptospirosis with severe pneumonia, acute kidney injury, and acute liver injury | Community-Acquired Pneumonia |
| 822 | Pheochromocytoma presenting as left adrenal incidentaloma with diffuse alveolar hemorrhage | Acute Appendicitis |

## 실행·채점 방법

원본의 Case Information, Physical Examination, Diagnostic Tests 세 필드만
합쳐 처음부터 제공했다. Final Diagnosis, Options, Right Option은 전달하지 않았다.
정답 용어가 임상 원문 자체에 포함되는지 제거·편집하는 절차는 하지 않았다.
추가 질문·검사 요청에는 정보가 제공되지 않았다고 응답했으며 정상/음성을 만들어내지 않았다.
원본 검사 결과를 긴 텍스트로 준 방식이며, 개별 검사 ID에 정밀 매핑한 상호작용 평가가 아니다.
따라서 지식 부족뿐 아니라 입력 어댑터·문맥 파싱·제공자 미연결 문제가 함께 반영된다.

모든 예측을 파일로 먼저 저장한 다음 정답과 비교했다. 문장부호·공백·대소문자를
정규화한 완전 일치만 사용했다. 의학적 동의어/부분 정답/합병증 일치는 채점하지 않았다.
폐렴처럼 정답의 일부 현상에 해당할 수 있는 예측도 원인 질환 전체 정답으로 세지 않았다.
위험도 정답 라벨이 없으므로 위험질환 sensitivity/specificity를 산출하지 않았다.

## 확인한 실패와 다음 순서

1. 후보 지원 범위: 현재 심층 프로필은 34개이며 표적 갈색세포종·심낭염·급성 신손상·SJS의
   심층 프로필이 없다. 외부 자료 확보는 실행 엔진 지원 추가와 다르다.
2. 판단 유보: 미지원 복합 증례 8개에서도 다른 질환명을 최종 출력했다.
   이를 바로 진단 안전성이 입증된 결과로 볼 수 없다. 범위 밖 입력과 근거 부족을
   구별하는 기준 및 불확실성 동작부터 검토해야 한다.
3. 입력 해석: 긴 병력·검사·치료 경과를 하나의 텍스트로 처리했다.
   현재/과거·원인/합병증과 검사값을 원문에서 분리하는 어댑터 검증이 필요하다.
4. 실제 모델: 공모전 고정 LLM을 연결한 실행이 없어 모델의 실제 진단 능력은 평가하지 못했다.
5. 전문가 검토: 질환 매핑과 위험도 정답은 아직 미승인이다. 이 9개 정답에 맞춘 규칙을
   추가해 독립 검증이라고 주장하지 말고 별도 미노출 사례를 확보해야 한다.

## 검증·재현

- 9건 모두 세 임상 필드 allowlist와 원문 비교 통과, 입력 해시 일치, ID 누락·순서 오류 없음.
- 실행 전후 runtime SHA-256 동일. 예측/동작/Top-5/위험 후보는 predictions.jsonl에 보존.
- 기존 근거/불확실성 회귀 테스트 16개 통과(0.23초). 전체 서비스 회귀 재실행은 하지 않음.
- scripts/run_external_nine.py가 실행 코드이며 manifest.json에 코드·입력·런타임 해시가 있다.
- 결과 덮어쓰기를 막기 위해 기존 출력 폴더가 있으면 실행을 중단한다.
