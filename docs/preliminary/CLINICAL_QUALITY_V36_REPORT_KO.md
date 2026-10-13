# N.O.V.A. v36 변경·검증 보고서

정보수집의 확인 판정, 새 관찰 뒤 진단 재평가, 동일 진찰 중복, 실제 환자 설명과 추적 안내를 수정했다. 추가 턴은 사용자 지시에 따라 허용했다. **공식 점수 상승은 아직 증명하지 못했다.** 사용자 기준점 45.84/100은 공식 재실행 전까지 그대로다. 외부 2,000건 진단 재생 정확도도 개선되지 않았다.

## 비교 결과: 공식 점수가 아닌 로컬 process proxy

| 항목 | BEFORE | AFTER |
|---|---:|---:|
| 정보수집 /25 | 20.38 | 20.38 |
| 진단추론 /15 | 13.67 | 13.67 |
| 검사·추적 /10 | 10.00 | 10.00 |
| 안전 /15 | 14.86 | 14.86 |
| 의사소통 /15 | 10.02 | 12.11 |
| 효율 /20 | 20.00 | 20.00 |
| 합계 /100 | 88.94 | 91.02 |

정보수집은 scripted answer-key coverage, 진단은 deterministic fallback, 계획은 필드·기간 표식, 의사소통은 실제 발언과 기록의 일치다. 안전/효율도 로컬 정의다. 공식 배점과 같은 숫자 범위를 사용했지만 실제 공식 채점 결과를 예측하지 않는다. 정의와 before trace의 한계는 [평가 프로토콜](CLINICAL_QUALITY_V36_PROTOCOL.md)에 명시했다. 외부 데이터 before/after는 동일 비교기로 평가했고 정답을 바꾸지 않았다.

## 요청한 57개 항목

| 번호 | 항목 | 결과 |
|---|---|---|
| 1 | 시작 브랜치 | `offline/nova-competition-agent-optimization` |
| 2 | 시작 remote HEAD | `51c7282766db20d0fb2f1c906834a6d1b7e34c5e` — 작업 시작 시 fetch로 확인 |
| 3 | 재현된 원인 | 새 문진 회귀의 최초 실행 12 실패/6 통과; exact duplicate 진단 identity 회귀 2 실패/1 통과. 가족·불확실성·용량 연결·unknown 완료 처리·중복 진찰·request_id·객관적 근거 손실·중복 질환 identity 거절을 수정했다. |
| 4 | 읽은 소스 | 아래 소스 점검 목록과 PROTOCOL.md 참조. 변경 전 실제 SDK → state → reasoning → SOAP → package 경로를 읽었다. |
| 5 | 읽고 실행한 검사 | SDK/official transport, evidence/assertion/negation, clinical interview/profile, diagnosis normalization, rubric pipeline, final decision, safety, current release 및 rights evidence 검사. focused JUnit과 전체 JUnit을 보존했다. |
| 6 | 수정 파일 | runtime 4개: `competition/nova_sdk_adapter.py`, `nova_agent/clinical_interview.py`, `nova_agent/diagnosis_normalizer.py`, 새 `nova_agent/interview_evidence.py`; submission mirror 동기화. 테스트·평가·v36 문서·검증 기록 추가. 임상 질환 KB 내용은 변경하지 않았다. |
| 7 | 정보수집 | 시도/확인 분리, 가족·과거·unknown 범위, 약 이름·용량·횟수·기간, 양쪽 부모 키, 실제 성장/체중 수치, 관련 증상 시작 시점; 새 답변마다 질문 필요성을 재검사. |
| 8 | 진단추론 | 새 관찰이 있고 불확실하면 제한적으로 재평가. Doctor 지시문에 위험 감별·구별 질문·반증·남은 불확실성을 강화. 같은 canonical name의 core/Tier2 중복만 통합; 다른 질환의 모호한 별칭 거절은 유지. |
| 9 | 검사·추적 | 기존 임상 프로필 계획을 실제 환자 발언으로 연결. 검사 목적·우선순위·추적 시점 지시 강화. 시행하지 않은 검사 결과는 생성하지 않는다. |
| 10 | 안전 | 응급 의뢰를 재평가 때문에 늦추지 않도록 기존 disposition 우선. 약물·가족 소견의 잘못된 확정 방지. 안정 환자에게 프로필별 경고 증상 전달. |
| 11 | 의사소통 | 32건 closing 평균 2.00 → 2.94; 실제 SAY를 교육에 기록. 진단/다음 단계/악화 행동을 분리했다. |
| 12 | 효율 | 추가 턴 허용 지시 반영: 전체 목표 34→40, 공식 한도 50 안에서 여유 확보. 로컬 효율 proxy 20.00→20.00/20. 공식 효율 20점 유지 여부는 미검증. |
| 13 | assertion/negation | 기존 진단 assertion 경로 유지; 그 범위 판단을 문진 완료 판정에도 적용. 명시적 부정과 불확실성을 구분했다. |
| 14 | 한국어 정규화 | 기존 다국어/부정/진찰 표기 정규화를 재사용. 실제 이름 없는 수면제, 가족 주어, 숫자·단위의 연결을 보수적으로 처리하고 설명 표현을 정리했다. |
| 15 | Doctor arbitration | 기존 evidence grounding/final decision 규칙 유지; 최대 두 후속 라운드는 새 관찰·불확실성·남은 예산이 있을 때만 실행한다. 실제 gpt-oss 성능은 미검증. |
| 16 | transport/fallback | PROVIDER_UNAVAILABLE를 같은 logical request_id로 재시도. Doctor 최종 실패 시 실제 객관적 진찰과 병력 근거 보존. |
| 17 | action selection | 새 답변에 따른 known topic 재검사, 동일 단일 진찰 중복 제거. 해부 부위만 같은 서로 다른 검사는 합치지 않는다. |
| 18 | stop policy | 관련 프로필 필수 문진의 너무 이른 종료를 막고, 종료 설명 여유를 남겼다. 기존 엔진의 26턴 목표는 유지했다. |
| 19 | 평가 규모 | 기존 230개 기본 사례 × 5 관찰 조건 = 1,150 SDK 대화; 별도 DDXPlus 2,000개 서로 다른 evidence profile/49질환; 32건 closing, 3건 SDK fixture, 128건 legacy Round M. |
| 20 | development | SDK 690 시나리오/138 base cases; 외부 1,200건. |
| 21 | validation | SDK 230 시나리오/46 base cases; 외부 400건. |
| 22 | frozen holdout | SDK 230 시나리오/46 base cases; 외부 원래 test partition 400건. 그룹·hash 고정. 기존 SDK 사례 노출과 외부 before 집계 노출 때문에 독립 맹검으로 주장하지 않는다. historical blind v18/v19 재실행 없음. |
| 23 | BEFORE 로컬 proxy | 아래 여섯 항목 표. 공식 45.84점과 직접 비교 불가. |
| 24 | AFTER 로컬 proxy | 아래 여섯 항목 표. 가중치는 같지만 채점자는 scripted process checker다. |
| 25 | TOP1 | SDK 채점 가능 666→666회: 91.14% → 91.14%. 외부 2,000건 before/after 동일 4.00%. 기존 230건: 98.65%→98.65%. |
| 26 | TOP3 | SDK 채점 가능 666→666회: 97.60% → 97.60%. 외부 2,000건 before/after 동일 10.70%. 기존 230건: 99.10%→99.10%. |
| 27 | TOP5 | SDK 채점 가능 666→666회: 97.60% → 97.60%. 외부 2,000건 before/after 동일 13.25%. 기존 230건: 99.10%→99.10%. |
| 28 | critical recall | 93.73% → 93.73%; SDK critical=true 사례의 최종 Top1, 정식 triage 민감도와 다르다. |
| 29 | critical misses | 16→16건; 관찰 조건 변형이 포함된 횟수. |
| 30 | over-triage proxy | 159→159건. critical=false인데 응급 처분인 경우; 독립적으로 정한 정답 disposition이 없어 실제 과잉 의뢰율로 해석할 수 없다. |
| 31 | under-triage proxy | 6→6건. critical=true인데 응급 처분이 아닌 경우; 실제 임상 검토가 필요하다. |
| 32 | 평균 턴 | 17.76 → 18.19; 별도 3 SDK fixture 9.67→12.00. |
| 33 | 중앙값 턴 | 18.00 → 18.00 |
| 34 | p90 턴 | 25.00 → 25.00 |
| 35 | Doctor 요청 | 2.29 → 2.41회/대화; 모두 scripted SDK 요청이다. |
| 36 | 토큰·지연·비용 | 실제 모델 미호출로 측정하지 않았다. fixture usage 상수나 병렬 실행 시간을 실제 비용으로 대체하지 않았다. |
| 37 | 의사소통 일관성 | 32/32 설명 존재, 32/32 주의사항 존재; SOAP 교육에 실제 발언을 기록한다. SDK 반복 질문 비율 6.80% → 6.82%; 이미 공개된 사실 재질문 1.04% → 1.04%. 사람의 명료성 평가는 미실시. |
| 38 | 계획 일관성 | 32/32 검사 계획, 23/23 평가 가능한 계획 주제 일치, 30/32 명시적 추적 기간. 32/32 처분 일치, 미시행 검사 결과 0건. 계획 존재만으로 임상 적절성을 보장하지 않는다. |
| 39 | focused tests | 최종 165 passed. 최초 재현 실패 로그와 최종 JUnit을 validation 폴더에 보존했다. |
| 40 | 전체 tests | core 전체 실행 후 릴리스·권리 기록과 평가 비교기의 26개 검사를 별도 재실행해 합쳤다. 총계를 아래 Python별로 표시했다. |
| 41 | py3.11 | 2827 passed, 0 failed, 1 skipped. 유일한 skip은 Torch 미설치로 학습 checkpoint 검사 미실행; 제출 runtime에서 Torch를 사용하지 않는다. |
| 42 | py3.12 | 2827 passed, 0 failed, 1 skipped. 유일한 skip은 Torch 미설치로 학습 checkpoint 검사 미실행; 제출 runtime에서 Torch를 사용하지 않는다. |
| 43 | runtime commit | `955e55439f69c0b887a1aeaa19dc71d4795e699f`. 실제 장시간 평가 checkout `f3c30e4f6fd2ba2b3dd1d66fcfb91ec47fe0bf75`와 전체 Git tree가 동일함을 검증했다. ZIP은 게시 가능한 runtime checkout에서 새로 만들었다. |
| 44 | verification commit | 이 보고서와 CURRENT_RELEASE를 포함하는 GitHub 게시 commit. 자기 자신의 SHA는 commit 내용에 넣을 수 없으므로 최종 전달 메시지에 정확한 값을 제공한다. |
| 45 | pushed remote HEAD | 최종 전달 메시지에 실제 push 후 재조회한 SHA를 제공한다. main/force-push/history rewrite 없음. 시작 remote HEAD의 자손만 게시한다. |
| 46 | ZIP 경로 | `submission/submission.zip`; 제공 파일 이름 `nova-v36-submission.zip`. ZIP 자체는 Git에 올리지 않으며 member hash를 기록한다. |
| 47 | ZIP bytes | 913778 |
| 48 | ZIP SHA256 | `7da4f049459a273fea45c3b88b50cf22b73d5d188623ec85d4b765d5348dc202` |
| 49 | MANIFEST SHA256 | `0cffac5c390b1448bd912304255d34ca8f0730dea5efca03f4f14792135d8ebe` |
| 50 | root run.py | ZIP 최상위 `run.py` 확인; import/standalone/fake HTTP 실행 확인. |
| 51 | root requirements.txt | ZIP 최상위 확인; 실제 배포된 dependency 5종 exact pin 및 wheel 점검. |
| 52 | 남은 임상 위험 | 외부 진단 재생 Top1 4.00%, Top3 10.70%, Top5 13.25%로 개선 없음. 기존 개발 사례 성능을 일반 진단 능력으로 해석하면 안 된다. 새로운 프로필 밖 문진, 실제 Doctor 재평가 품질, 임상 계획·과잉/과소 의뢰는 아직 검증이 필요하다. |
| 53 | 대회·provenance 위험 | 기존 release gate는 NOT READY를 유지. 미완료 기술 검사: docker_offline_readonly_2cpu_8gb. Docker가 없어 동일 2 CPU/8GB/readonly/offline container 검증 미실시. full guideline corpus 미확보. 변경된 4개 코드/SDK 총 5개 member는 기존 hash-bound 권리 증거에 포함되지 않고 독립 clinician review도 대기 중이다. 이는 코드 수정/게시 중단이나 새 사용자 승인 요청의 이유로 사용하지 않았다. |
| 54 | 키 접근 | NOVA_DEV_KEY를 한 번도 읽거나 접근하지 않았다. key 값·환경 파일·참가자 credential을 검사하지 않았다. |
| 55 | 실제 organizer 실행 | 실제 organizer HUMAN-RUN, 참가자 sample API, 실제 Doctor 호출, 공식 제출 모두 수행하지 않았다. 공개 문서·공개 SDK·공개 benchmark 다운로드만 사용했다. |
| 56 | PowerShell | 아래 명령 참조. 참가자 본인 PC에서만 실행하며 키는 채팅에 보내지 않는다. |
| 57 | 돌려받을 자료 | C01.json/C03.json/C10.json, 각 공식 6개 항목 점수와 총점 화면, 오류 시 전체 stderr(키·세션 식별자 제거), runtime SHA·ZIP hash, 실제 턴/Doctor 호출/토큰/elapsed를 포함한 원본 capture. 공식 case ID와 C01/C03/C10 매핑도 함께 기록. |

## 읽은 핵심 경로

`competition/nova_sdk_adapter.py`, `competition/adapter.py`, `nova_agent/orchestrator.py`, `action_selector.py`, `stop_policy.py`, `final_decision.py`, `differential.py`, `candidate_generator.py`, `chief_complaint.py`, `clinical_presentation.py`, `state.py`, `matching.py`, `multilingual_concepts.py`, `diagnosis_normalizer.py`, `evidence_scope.py`, `evidence_grounding.py`, `objective_evidence.py`, `safety.py`, `safety_validator.py`, `disposition.py`, `soap.py`, `retrieval_pipeline.py`, `open_world.py`, `organizer_guidelines.py`, clinical interview/profile 및 ontology 코드; knowledge/diseases, tier2 catalog/enrichment/open features/MONDO synonyms, PROVENANCE; README·대회/릴리스 문서·CURRENT_RELEASE·빌드/검증 스크립트와 관련 테스트를 확인했다. 실제 변경은 위 4개 runtime 파일에 한정했다.

첨부 devkit와 sample ZIP은 정상 ZIP 구조를 확인하고 PPT 22장도 읽었다. 불완전한 guideline `.crdownload`는 완성된 전체 코퍼스로 취급하지 않았다. 로컬에서 확인하지 못한 공식 C01/C03/C10 원본 대화·채점 원인을 새로 확인했다고 주장하지 않는다.

## 참가자 PC의 PowerShell 명령

다음 명령은 사람이 일반 PowerShell에서 실행한다. 현재 release gate의 권리·clinician·container 미완료 사항은 위에 별도 표시했다. 실제 참가자 키는 coding agent에 주지 않는다.

```powershell
cd C:\path\to\nova
git fetch origin
git switch offline/nova-competition-agent-optimization
git pull --ff-only origin offline/nova-competition-agent-optimization
git rev-parse HEAD

py -3.12 -m venv .venv-human
.\.venv-human\Scripts\python.exe -m pip install -r submission\requirements.txt
$releasePointer = Get-Content artifacts\verification\CURRENT_RELEASE.json -Raw | ConvertFrom-Json
$release = Get-Content $releasePointer.current_verification_artifact -Raw | ConvertFrom-Json
$env:SOURCE_DATE_EPOCH = (git show -s --format=%ct $releasePointer.verified_runtime_sha).Trim()
.\.venv-human\Scripts\python.exe scripts\build_nova_submission.py
$zipHash = (Get-FileHash submission\submission.zip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($zipHash -ne $release.submission.sha256) { throw 'ZIP hash differs from verified release' }
.\.venv-human\Scripts\python.exe scripts\validate_submission_zip.py

$env:NOVA_API_BASE = 'https://nova.snubhai.org'
$sampleOutput = Join-Path ([Environment]::GetFolderPath('MyDocuments')) ('nova-v36-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
$sampleSecret = Read-Host 'Participant development key (hidden)' -AsSecureString
$sampleKeyPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sampleSecret)
try {
    $env:NOVA_DEV_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($sampleKeyPtr)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($sampleKeyPtr)
}
try {
    .\.venv-human\Scripts\python.exe scripts\run_dev_samples.py --human-run --list --output $sampleOutput
    # 위 목록의 실제 published case ID를 입력. C01 등의 로컬 이름과 혼동하지 않기.
    $case01 = Read-Host 'C01 published case_id'
    $case03 = Read-Host 'C03 published case_id'
    $case10 = Read-Host 'C10 published case_id'
    .\.venv-human\Scripts\python.exe scripts\run_dev_samples.py --human-run C01 C03 C10 --case-id "C01=$case01" --case-id "C03=$case03" --case-id "C10=$case10" --output $sampleOutput
} finally {
    Remove-Item Env:NOVA_DEV_KEY -ErrorAction SilentlyContinue
    Remove-Variable sampleSecret, sampleKeyPtr -ErrorAction SilentlyContinue
}
```

`C:\path\to\nova`만 실제 저장소 폴더로 바꾼다. 출력은 저장소 밖 새 폴더에 남긴다. 키·토큰·쿠키 화면은 보내지 않는다. 실제 세션의 식별자는 제거하고 임상 대화·SOAP·점수·runtime 식별 정보는 보존한다.

## 근거 파일

- `artifacts/clinical_quality_v36/comparison.json`: 비교 수치와 split별 집계.
- `before/`, `after/`: case별 최종 결과. 초기 before SDK 원본 trace는 gzip으로 보존.
- `validation/`: 최초 실패 재현, focused 및 Python별 core/deferred JUnit과 최종 통합 결과.
- `final/`: 현재 runtime에 묶인 Round M 요약·실패 분석과 패키지 preflight.
- `artifacts/verification/CURRENT_RELEASE.json`: 현재 v36 pointer. 기존 v35 및 과거 기록 보존.
- `evaluation/external_ddxplus_v36/`: 외부 데이터 출처, CC BY 4.0, 고정 split/hash와 변환 범위.

대회 근거: [공식 문서](https://nova.snubhai.org/docs/), [공식 대회 사이트](https://nova.snubhai.org/). 외부 데이터: [DDXPlus English v2](https://doi.org/10.6084/m9.figshare.22687585.v2).
