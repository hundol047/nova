# 고정 모델 비교용 외부 연구 자료 v1

출처: [DiagnosisArena 공식 공개 자료](https://huggingface.co/datasets/SII-SPIRAL-MED/DiagnosisArena).
원본 revision, 파일 SHA-256, 변환 코드 SHA-256, 입력/정답 SHA-256은 `manifest.json`에 있다.
원본 고지와 이용 조건은 상위 `diagnosisarena/source/` 및 [수집 보고서](../README.md)를 따른다.
**연구·모델 평가 전용이며 임상 서비스 지식, 학습 자료 또는 제출물로 편입하지 않는다.**

| NOVA 내부 분할 | 사례 수 | 용도 |
|---|---:|---|
| development | 59 | 기존에 살펴본 표적 9개 + 새 비교 50개 |
| validation | 50 | 개발 후 별도 확인 |
| holdout | 100 | 개발 선택에 사용하지 않고 최종 평가까지 보관 |

이는 원저자의 공개 test 중 일부를 NOVA 연구 목적으로 다시 나눈 것이다. 새로운 환자
209명을 모집하거나 임상의가 NOVA 답변을 검증한 것이 아니다. 사전학습 오염 여부는 모른다.
`previously_inspected`는 NOVA에서 표적 분석에 사용한 9개를 식별하며, 모든 개발 이력을
자동으로 증명하는 필드는 아니다. 원본의 전문의 검토와 NOVA용 정답 재검토를 구별한다.

`inputs.jsonl`에는 원문 임상 정보만 있고 정답·선택지는 없다. `labels.jsonl`은 채점 단계에만
파싱한다. 추론 입력 스키마는 정의되지 않은 정답 필드를 거부한다. 변환 시 전체 정답 문자열이
입력에 이미 나타난 새 후보 2개(ID 194, 345)는 제외했다. 이것만으로 모든 진단명 누출이나
의미 중복이 해결되지는 않는다.

같은 family ID, 정규화 입력의 완전 중복, 토큰 Jaccard 0.9 이상 유사 입력의 분할 간
누출은 실행 전에 검사한다. 환자·논문 family ID가 원본에 없어 어휘 기반 그룹만 사용한다.
기존 합성 50,000개와의 의미 중복, 원문 논문 중복, 한국어 번역 품질 검토는 미완료다.

이 정적 자료에는 질문·검사 키별로 검토된 응답 맵과 응급도 정답이 없다.
`interactive_reviewed=false`를 유지한다. 전체 정보 비교는 가능하지만 대화형 비교는
자료 부족으로 차단하며, 없는 응답을 합성하거나 위험도 Recall을 만들어 보고하지 않는다.

재현에는 `pyarrow`가 필요하다. 런타임과 제출물에는 필요하지 않다.

```bash
python scripts/prepare_external_comparison.py --help
python scripts/run_model_comparison.py --dataset research/external_evidence/comparison_v1 --output /tmp/nova-comparison-check --validate-only
```

현재 입력·정답 파일을 덮어써서 평가 조건을 바꾸지 않는다. 수정된 매핑·승인 정답이 생기면
출처와 검토 기록을 갖춘 새 버전으로 준비한다.
