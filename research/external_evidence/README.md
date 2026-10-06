# 미지원 질환 근거·외부 정답 자료 확보 결과

확인일: 2026-10-03. 이번 작업은 자료 확보·품질 점검이다. 학습, NOVA 실행 엔진 수정,
진단 성능 평가를 수행하지 않았다. 전문가 검토는 아래 원저자 논문에서 보고한 절차이며,
NOVA용 정답 매핑을 임상의가 새로 승인했다는 뜻이 아니다.

## 확보한 원본

| 자료 | 실제 다운로드 | 전문가 검토 근거 | 이용 범위 |
|---|---:|---|---|
| MedXpertQA Text | test 2,450 + dev 5 = 2,455문항 | ICML 2025 논문 §3.2 / Appendix E: 의사 면허를 가진 전문가가 문항·선택지를 검토하고 오류 수정 | 공식 데이터 카드 MIT 표기, 저작권 고지 동봉 |
| DiagnosisArena | 공개 test 915증례 | ACL 2026 논문 §3.2: 전문의 검토, 정보 누락·진단 모호성 사례 제외 | 원저자 명시: 연구·모델 평가 전용. 임상 의사결정·의료 진단 사용 금지 |

총 3,370행이다. 서로 다른 평가 과제이므로 하나의 정확도 분모로 합치면 안 된다.
MedXpertQA 전체 4,460개를 받았다고 표현하지 않는다. 영상형 데이터는 받지 않았다.
DiagnosisArena 논문의 1,113개 전체도 확보한 것이 아니다. 저작권·시점 제한으로
저자가 공개한 915개만 받았다. 비공개 나머지는 수집하지 않았다.

- [MedXpertQA 원저자 논문](https://proceedings.mlr.press/v267/zuo25a.html)
- [MedXpertQA 공식 데이터](https://huggingface.co/datasets/TsinghuaC3I/MedXpertQA)
- [DiagnosisArena 원저자 논문](https://aclanthology.org/2026.findings-acl.151/)
- [DiagnosisArena 공식 저장소 및 이용 조건](https://github.com/SPIRAL-MED/DiagnosisArena)

원문 정답은 수정하지 않았다. MedXpertQA는 시험 문항의 합성·증강과 사람의 검토를
거친 자료다. DiagnosisArena는 출판 증례를 AI·전문가 검토로 구성한 후향적 공개
벤치마크다. 둘 다 NOVA의 독립적 전향 임상시험이 아니며 사전학습 오염 여부는 모른다.
문항별 전문가 서명·검토 일지는 제공 자료에 없고, 전문가 검토 절차는 논문 근거다.
MedXpertQA 텍스트 파일에는 전문가 해설 필드가 없으므로 해설까지 확보했다고 하지 않는다.

## 미지원 질환별 확보 수준

최근 abstention_cycle6 실패의 7개 질환군에 더해 기존 hard_seven 검토 목록의
길랭–바레 증후군·Fabry병도 확인했다. 실패 라벨이 흉통/긴장성 두통이더라도
임신 관련 복통·불충분한 두통 정보를 잘못 대리한 사례는 새 정답으로 확정하지 않았다.

아래 수는 **DiagnosisArena 최종진단 문자열의 관련 용어 일치 수**다.
실제 NOVA 질환 매핑과 현재 지침 적합성은 전문가 검토 전이다. 0은 이번 용어 검색에서
못 찾았다는 뜻이며 데이터 전체에 관련 사례가 전혀 없음을 보증하지 않는다.

| 대상 | 정답 용어 일치 | 검토할 사례 ID | 임상 근거 원문 |
|---|---:|---|---|
| 갈색세포종 | 2 | 140, 822 | [Endocrine Society PPGL 2014](https://academic.oup.com/jcem/article/99/6/1915/2537399) |
| 크루프 | 0 | 추가 확보 필요 | [CPS, 2026-03-06 갱신](https://cps.ca/en/documents/position/acute-management-of-croup) |
| 전자간증 | 0 | 추가 확보 필요 | [NICE NG133](https://www.nice.org.uk/guidance/ng133/chapter/recommendations) |
| 췌장암 | 0 | 추가 확보 필요 | [NICE NG85](https://www.nice.org.uk/guidance/ng85/chapter/Recommendations) |
| 급성 신손상 | 2 | 586, 770 | [NICE NG148](https://www.nice.org.uk/guidance/ng148/chapter/Recommendations) |
| 심낭염 계열 | 4 | 87, 514, 628, 766 | [ESC 2025](https://www.escardio.org/guidelines/clinical-practice-guidelines/all-esc-practice-guidelines/myocarditis-and-pericarditis/) |
| SJS/TEN | 1 | 697 | [BAD 성인 지침 2016](https://academic.oup.com/bjd/article/174/6/1194/6617016), [BAD 환자 안내](https://www.bad.org.uk/pils/sjs-ten) |
| 길랭–바레 증후군 | 0 | 추가 확보 필요 | [EAN/PNS 2023](https://onlinelibrary.wiley.com/doi/10.1111/ene.16073) |
| Fabry병 | 0 | 추가 확보 필요 | [GeneReviews](https://www.ncbi.nlm.nih.gov/books/NBK1292/) |

관련 9개 증례의 원문·정답은 `target_cases_9.jsonl`에 모았다. 이 파일도 원본의
연구·평가 전용 조건을 따른다. 단순 심낭염과 심근심낭염, 질환과 합병증을 합쳐
정답 처리하지 않는다. 예컨대 770번은 렙토스피라증의 여러 장기 합병증을 포함한다.

MedXpertQA에는 갈색세포종 용어가 정답에 들어간 1문항(Text-1544)이 있으나
기초의학 진술형이다. 전자간증 정답 1문항(Text-921)은 신생아 상태의 모체 원인을
묻는다. 이 두 문항을 본인 증상 기반 직접 진단 정답 사례로 세지 않았다.
그 밖의 오답 선택지·본문 언급도 직접 진단 정답 수에 포함하지 않았다.

## 임상 근거에서 확인할 검토 항목

다음은 검토 의뢰 항목이며 자동 진단 규칙이나 전문가 승인 정답이 아니다.

- 갈색세포종: 혈장/소변 생화학검사와 영상검사의 해석, 비특이 증상만 있는 사례의 불확실성.
- 크루프: 짖는 기침·흡기성 협착음의 문맥, 침흘림·삼킴곤란·심한 호흡곤란에서 다른 위험 원인.
- 전자간증: 임신 주수·산후 상태·혈압·단백뇨 및 장기 이상. 두통만으로 확정하지 않는 기준.
- 급성 신손상: 기저 크레아티닌과 시간 변화, 실제 소변량·체중·시간 단위. 단일 이상 수치의 한계.
- 췌장암: 의심 소견과 영상·조직 검사 근거를 구분. 체중 감소나 황달 단독으로 확정 금지.
- 심낭염: 2025 지침을 기준으로 심근 침범·급성 관상동맥 원인·심장압전과 구별.
- SJS/TEN: 약물 노출, 피부 통증·수포·점막 침범, 임상의 피부 평가 및 필요 시 조직검사.
- 길랭–바레/Fabry: 기존 `../clinical_review/hard_seven/profiles.json` 초안을 전문가에게 함께 전달.

지침은 링크·서지와 자체 검토 메모만 보존했다. 전문 복제·재배포·지침 텍스트의
학습 사용 권한을 획득했다고 주장하지 않는다. NICE 전문 직접 열람은 403으로 차단되어
공식 검색 색인에서 확인한 범위를 넘는 최신 전문 검토는 완료로 표시하지 않았다.
PPGL 전문 열람도 리디렉션 오류가 있었다. 원문 링크 존재와 전문 열람 완료를 구별한다.

## 검증 결과와 격리

`intake_audit.json`은 재현 가능한 수집 검증 결과다.

- 9개 다운로드 파일 SHA-256 일치. JSONL 압축 해제 후 원본 해시도 일치.
- 3,370행 파싱, 정답 선택지 키 검사 통과. 데이터셋 내부 중복 ID 0, 정규화 입력 완전 중복 0.
- 의미상 유사 문항·기존 NOVA 50,000 합성 사례와의 교차 누출 검사는 아직 미완료.
- `review_queue`는 자동 용어 검색 결과이며 `clinical_gold_approved_for_nova=false`다.
- 학습 데이터, 검색 인덱스, 서비스 실행 코드, 공모전 제출물에 연결하지 않았다.
- 정답을 살펴본 표적 9개는 향후 미노출 독립 테스트로 주장하지 않는다.
- 기존 근거 검토·불확실성 관련 회귀 테스트: 16개 통과(0.25초). 전체 서비스 회귀는 이번 자료 수집에서 재실행하지 않았다.
- 성능 변화: 측정하지 않음. 모델 호출/학습 0회. 수집만으로 정확도가 올랐다고 하지 않는다.

재현: pyarrow가 설치된 환경에서 `python scripts/audit_external_evidence.py`.
각 `manifest.json`에 고정 데이터 revision, 다운로드 URL, 파일 크기, 해시가 있다.
출처 README·LICENSE는 수집 당시 사본이며 가변 main URL은 해시로 시점을 고정했다.
원본 데이터의 세부 조건이 프로젝트 코드의 MIT 고지보다 우선한다.

## 보류한 자료

| 자료 | 보류 이유 | 원본 |
|---|---|---|
| AfriMed-QA | 원본 GitHub의 CC BY-NC-SA와 v2 카드의 상이한 표기를 확인. 창업·상용 활용 조건 정리 필요 | https://github.com/intron-innovation/AfriMed-QA |
| MedExQA | 원저자 논문이 CC BY-NC-SA 명시. 상업적 제품용 데이터로 편입하지 않음 | https://aclanthology.org/2024.bionlp-1.14.pdf |
| MedThink-Bench | 전문가 상세 근거 주석은 유용하나 저장소의 명시적 데이터 라이선스 및 상위 자료 권리 미확정 | https://github.com/plusnli/MedThink-Bench |
| Medbullets / JAMA Clinical Challenge | 상용 문제은행·비공개 배포 제한. 미러 표기만으로 이용 허락을 간주하지 않음 | https://github.com/HanjieChen/ChallengeClinicalQA |
| MedQA | 시험 자료와 교과서가 함께 제공됨. 전체 문항 개별 전문가 재검토 및 각 자료 재사용 권한을 이번에 확정하지 못함 | https://github.com/jind11/MedQA |

## 다음 개발에 필요한 실제 승인

1. 해당 분야 의사가 표적 증례의 최종진단·근거 충분성·NOVA 질환 매핑을 검토한다.
2. 별도 검토자가 위험도/권장 행동/불확실 응답의 정답을 정한다. 현재 데이터에는 그 정답이 없다.
3. 의견 불일치는 제3 검토자가 조정하고 검토 날짜·근거 출처·이해관계를 기록한다.
4. 크루프·전자간증·췌장암·GBS·Fabry의 직접 사례를 추가 확보하고, 한국어 번역도 임상의 검토를 받는다.
5. 사용 조건·누출 검사와 평가 형식 검토 후 외부 평가를 실행한다. 학습은 별도 승인된 개발 자료로만 진행한다.

전문가 검토자를 실제로 섭외하거나 서명을 받은 단계는 아니다. 공식 공개 정답 확보와
NOVA용 임상 검증 완료를 명확히 구분한다.
