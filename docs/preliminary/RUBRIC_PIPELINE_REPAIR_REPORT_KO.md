# 공식 평가 취약 영역의 일반 진료 흐름 수정 — 2026-10-12 KST

**LOCAL RUBRIC PROXY — NOT OFFICIAL SCORE. 공식 새 점수와 실제 GPT-OSS 성능은 아직 확인하지 않았습니다.** 참가자 키는 Codex에서 조회·사용하지 않았고, 공식 공개 샘플·샘플 검증·리더보드도 실행하지 않았습니다. 최신 검증 포인터는 `artifacts/verification/CURRENT_RELEASE.json`이며 v34 기록은 보존합니다. 새 런타임과 v35 증거를 고정했으며 아래 최종 실행 결과에 연결합니다.

## 출발 상태와 증거 범위

실제 원격 시작 HEAD는 `dc1b1b94182c8cd0d128f21bc78c215317945923`입니다. 로컬의 이전 `afee61e`에서 원격을 먼저 가져와 fast-forward했습니다. 원격의 Windows 경로·MANIFEST 정렬·해시 재현성 수정 5개 커밋을 모두 유지했습니다. main 변경, force-push, 이력 재작성, 기존 임상 자산 삭제는 하지 않았습니다.

사용자가 첨부 프롬프트로 제공한 공식 평가 수치는 아래와 같습니다. 원본 평가 응답/영수증은 이번 작업에 첨부되지 않았으므로 독립 인증된 측정이라고 주장하지 않습니다. 개발 방향을 정하는 신호로 사용했으며, 미공개 채점 규칙을 추측하지 않았습니다.

| 공식 평가 영역 — 사용자 제공 | 기존 점수 | 이번 작업의 방향 |
|---|---:|---|
| Information Gathering | 7.82/25 | 현재 알고 있는 사실은 반복하지 않고, 후보를 가르는 질문으로 교체 |
| Diagnostic Reasoning | 4.17/15 | 음성 소견·한영 근거 전달·지원 가능한 진단 범위·Doctor 조정 |
| Tests / Follow-up | 0.08/10 | 선택한 진단에 맞는 계획 검사, 추적 시점·목표·조기 재평가 조건 |
| Safety | 6.25/15 | 잘못된 응급 진단/전환 억제, 실제 응급 근거 보존 |
| Communication | 2.67/15 | 같은 최종 진단의 설명·다음 단계·경고 증상을 실제 SAY로 전달 |
| Efficiency | 20.00/20 | 턴을 추가하는 대신 가치가 낮은 턴을 교체; 호출·예산 한도 유지 |

합계는 40.99/100입니다. **새 공식 점수는 예측하거나 확정하지 않습니다.** 로컬 모의 결과와 새 공식 채점은 다른 증거입니다.

## 재현한 원인과 수정

1. **음성 진찰이 양성 진단 근거가 됐습니다.** 원래 상태에서는 `경부 강직(-)`에서 `neck stiffness`가 생성돼 수막염 근거가 됐고, `수포음(-/-), 천명음(-/-)`가 폐렴의 청진 근거를 제공했습니다. 원문은 그대로 보존하고, 매칭용 표현에서만 `(-)`/`(-/-)`를 absent, `(+)`를 present로 투영합니다. 한 보고서의 양성·음성 항목을 각각 다룹니다. 혼합 양측 부호는 미확정이며, 기존 영어 부정문도 회귀 검사합니다.
2. **낮 졸림이 의식 변화로 바뀌었습니다.** 한국어 `졸려`를 무조건 altered mental status로 연결하던 매핑을 고쳤습니다. 수면 문제의 졸림과 실제 혼미·지남력 저하를 분리합니다. 기존 회귀 검사에서 발견한 `졸려하면서 대답/반응이 늦다`는 별도 반응 저하 소견으로 보존하고, 단순 졸림·반응 저하를 부인한 문장과 구분합니다. 관련 단어 `rebound insomnia`가 `rebound tenderness`로 오인되는 별도 결함도 발견해, 임상 관계와 진찰 표현이 일치할 때만 압통 근거로 쓰도록 고쳤습니다.
3. **실제 문진 내용이 임상 특징에 도달하지 않았습니다.** 체중 감소, 식욕 증가, 열 불내성, 떨림, 발한, 배변 변화, 미만성 갑상샘 비대, 안구 소견, 반사 항진을 일반 임상 개념으로 연결합니다. 부정·과거·가족 범위를 지키며 증상을 질병명으로 번역하지 않습니다. 요청한 진찰이 제공하는 해부학적 맥락을 사용하되 결과는 새로 만들지 않습니다.
4. **약물 문진에 있는 현재 소견도 빠졌습니다.** 복약·증량·금단 답이 과거력 쪽에 저장되기 때문에 현재 증상만 검사하는 선택기에서 사라졌습니다. 약물 관련 프로필에서 실제 현재 복약 답을 다시 투영합니다. `zopiclone을` 같은 영문 약명+한국어 조사의 경계도 처리합니다. 관계자 복약과 오래전 중단은 현재 환자 복약으로 만들지 않습니다.
5. **성장 기록의 날짜와 속도가 섞였습니다.** `1년 전 키 121cm`를 연간 성장량으로 오해하지 않습니다. 명시한 cm/year 또는 정확히 1년 간격의 제공된 두 신장으로만 계산합니다. 날짜나 신장, 골연령·호르몬 결과를 추정해 채우지 않습니다.
6. **일부 질환의 명칭/특징이 없었습니다.** 별도 보조 프로필 8개를 추가했습니다. 기존 34개 깊은 프로필과 1,246개 온톨로지 카탈로그는 유지합니다. 7개 신규 진단과 기존 항진증 프로필 보완 1개이며, 새 공식 코드 매핑은 없습니다: Graves병, 진정수면제 사용장애, 약물 관련 과다졸림, 반동 불면, 체질성 성장지연, 가족성 저신장, 성장호르몬 결핍 의심, 갑상샘항진증 보완. 임상 특징/계획은 엔지니어링 휴리스틱이며 임상의 검토·재배포 권리 확정은 아닙니다.
7. **최종 진단 조정 이후 다른 결정을 계속 사용했습니다.** 지지된 Doctor 제안을 채택하면 실제 최종 결정 객체도 변경합니다. 그 결정이 진단, 설명, A 근거, 검사/추적 계획과 disposition을 결정합니다. 현재 독립 근거와 구별 소견이 부족하거나 직접 상충하면 제안을 거부합니다. 가족력만으로 환자 질환을 확정하지 않습니다. 괄호 안 구체적 원인이 넓은 진단의 검증을 우회하지 못하도록 제한합니다.
8. **최종 호출 실패가 앞선 유용한 제안을 없앴습니다.** 한 증례 안에서만 최대 8개 제안을 보존하고 마지막 관찰로 재검증합니다. 실제 공개 문서는 `REQUEST_PENDING`에서 같은 request_id 재시도를 명시합니다. 기존 지연/마감/예산 한도를 유지하고, 유효한 앞선 제안이 있으면 한 차례 동일-ID 재시도 후 계속 pending인 최종 호출을 더 늘리지 않습니다. 유효한 제안이 없으면 기존 bounded retry를 유지합니다. 반영 효과도 이전 제안의 요청 번호에 연결합니다.

## 여섯 영역의 연결

**Information Gathering:** 수면/약물, 소아 성장, 체중 감소 등 일반 임상 문맥에서 가치가 높은 단일 질문을 먼저 선택합니다. 이미 제공한 성장 기록·식욕 등을 다시 묻지 않습니다. 증상 조합이 충분하면 추가 ROS보다 후보를 가르는 진찰을 앞세웁니다. 어린 아동에게 일상적인 흡연/음주 질문을 하지 않고, 청소년과 실제 노출 상황은 별도로 다룹니다. 새 급성 흉통·호흡·신경학적 문제를 만성 문진 경로로 돌리지 않습니다. 질문은 30 NFC 문자 이내이며 전체 기존 예산 안에서 교체합니다.

**Diagnostic Reasoning:** 현재 근거의 최소 수와 의미 있는 구별 소견을 모두 만족해야 보조 프로필이 진단 후보/주진단이 됩니다. 이를 단일 발한 같은 소견에 너무 일찍 적용한 초기 구현은 기존 ACS 검사 우선순위 회귀를 일으켰습니다. 후보 진입을 좁히고 기존 troponin 우선순위 검사를 그대로 통과시켰습니다. 또 기존 항진증의 감별 질문 4개를 보조 프로필에 보존하지 않은 초기 구현은 설사 사례에서 두근거림 확인을 빠뜨렸습니다. 질문 목록을 원래대로 복원하고 회귀 assertion을 추가했습니다. 단일 모호한 증상을 많은 만성 후보에 확장해 성능을 얻지 않습니다.

**Tests / Follow-up:** P에 실제로 수행하지 않은 검사를 향후 계획으로 씁니다. 항진증은 TSH/free T4와 조건에 따른 원인 감별·ECG, 성장 문제는 성장곡선/기록 및 필요시 골연령·표적 내분비 평가, 약물 문제는 복약·용량·기간·병용/금단 검토를 제시합니다. 추적에는 결과·맥박·체중·성장속도·금단 등 목표와 시점, 더 이른 평가 조건을 넣습니다. 정상 성장속도에서는 조건부 표적 평가이며 무조건 광범위 검사를 나열하지 않습니다. O.tests는 예선에서 비워 둡니다.

**Safety:** Doctor의 `urgent=true`만으로 응급 전환하지 않습니다. 최종 선택과 실제 수치/소견, 지지되는 위험한 대안을 평가합니다. 정상 안정 맥박에서 두근거림 하나만으로 위험 부정맥 대안을 응급 사유로 만들지 않습니다. 실제 부정맥 소견·실신·현저한 증상성 맥박 이상은 유지합니다. 다른 신체진찰에서 제공한 SpO2 같은 실제 수치도 놓치지 않습니다. 모델이 제안한 약물 용량을 치료 항목에 복사하지 않고 확인 전 처방을 보류합니다. 약물 의존/사용장애는 작업 가설이며, 단순 신체적 의존이 곧 사용장애 확진이라는 주장은 하지 않습니다.

**Communication:** 모델의 검증되지 않은 short_name을 그대로 말하지 않습니다. 선택한 진단의 안전한 동의어로 설명하고, 같은 계획의 다음 단계/경고 증상을 말합니다. 종결 SAY는 기존과 같이 최대 2회입니다. 공식 기록의 education에는 실제로 한 설명만 기록합니다. 설명·A·P·DIAGNOSE의 진단이 갈라지는 문제를 회귀 검사합니다.

**Efficiency:** Doctor soft target 16, 최대 200회, 입력 500k/출력 100k, 토큰 상한, 240초 SDK timeout과 마감 여유는 유지합니다. 모의 지연을 근거로 reasoning effort나 토큰 정책을 바꾸지 않았습니다. 선택적 문진은 12회 이내의 교체 흐름이며 실제 해당 소견이 있으면 더 일찍 끝납니다. 모의 실행의 감소가 실제 공식 효율 20/20을 보장한다는 주장은 하지 않습니다.

## 새 로컬 비교의 정의와 결과

32개 새 관찰 재생 사례와 3개 새 전체 fake-SDK 진료를 고정해 전후 비교했습니다. 공모전의 UUID/환자명/정확한 첫 문장으로 정답을 찾는 구현은 없습니다. 사례는 실패 유형과 코드를 본 사람이 만든 개발 자료이며 blind 검사·독립 임상 검증이 아닙니다. Doctor 응답은 모의 검사에서 미리 작성한 응답입니다.

| LOCAL RUBRIC PROXY — NOT OFFICIAL SCORE | 이전 | 수정 후 |
|---|---:|---:|
| 32개 재생: 참조 질환 범위에 맞는 결정 | 11/32 | 32/32 |
| 기대 응급도 일치 | 21/32 | 32/32 |
| 질환 영역에 맞는 계획 주제 — 문자열 proxy | 2/23 | 23/23 |
| 추적에 수치 시점 있음 | 0/32 | 30/32 |
| 실제 종결 설명 있음 | 32/32 | 32/32 |
| 평균 종결 SAY | 2 | 2 |
| 만들어 넣은 미시행 검사 결과 | 0 | 0 |
| 전체 fake-SDK 3개: 필요한 정보 주제 수집률 평균 | 54.29% | 100% |
| 평균 환자 턴 | 21.67 | 9.67 |
| 평균 EXAM 요청 | 8.67 | 1.33 |
| 평균 Doctor 물리 요청 | 2.33 | 2.33 |
| 해당 3개 기대 진단 제출 | 0/3 | 3/3 |
| 부적절한 아동 사회력 질문 | 1 | 0 |
| 안정 사례의 부적절한 응급 disposition | 1 | 0 |

수치 추적 시점이 없는 2개는 급성 위험 사례로, 즉시 응급 평가와 재평가를 명시합니다. 위의 검사/추적·참조 범위·응급도 수치는 한정된 엔지니어링 assertion입니다. 임상적 질의 가치와 의학적 정확도를 자동 인증하지 않습니다. 실제 모델의 토큰, 서버 지연, 비용은 미측정이며 고정 모의 usage를 실제 비용으로 표현하지 않습니다. 별도로 한 warmed differential update의 cProfile CPU 계측은 이전 1.103초, 최종 0.399초였습니다. 단일 입력·프로파일링 오버헤드·공유 기계 부하가 통제되지 않은 계측이므로 성능 향상/회귀 또는 실제 서버 지연 판정에 사용하지 않습니다. 최종 230개 전수 회귀와 두 Python의 전체 결과, 패키지 값은 아래에서 확인할 수 있습니다.

## Windows PowerShell: 새 버전을 본인 컴퓨터에서만 검사

**Codex/Claude Code/Cursor/CI 터미널에서 참가자 키를 사용하지 마세요.** 아래의 참가자 키 명령은 이번 작업에서 실행하지 않았습니다. 키는 채팅·GitHub·스크린샷에 넣지 않습니다. 기존 작업 폴더를 덮어쓰지 않도록 새 폴더에 받으며, 기록된 LF 해시를 유지하기 위해 이 새 clone에만 autocrlf=false를 설정합니다.

```powershell
$novaCheckout = Join-Path $env:USERPROFILE ("nova-v35-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
git clone --config core.autocrlf=false --branch offline/nova-competition-agent-optimization https://github.com/hundol047/nova.git $novaCheckout
if ($LASTEXITCODE -ne 0) { throw "Git clone failed" }
Set-Location -LiteralPath $novaCheckout
py -3.12 -m venv .venv
$novaPython = Join-Path $novaCheckout ".venv\Scripts\python.exe"
& $novaPython -m pip install -r submission\requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed" }
$novaPreflight = Join-Path $env:TEMP ("nova-preflight-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
& $novaPython scripts\pre_sample_validation.py --output-dir $novaPreflight
```

Docker Desktop가 실행되어야 2 CPU/8 GB·인터넷 차단·읽기 전용 검사를 할 수 있습니다. 검사 결과의 `LOCAL_TECHNICAL_CHECKS`와 각 항목을 확인하세요. 기존 출처/라이선스가 미해결인 동안 `READY_FOR_HUMAN_SAMPLE_VALIDATION=NO`, exit 2가 정상입니다. 기술 실패는 그와 구분해 해결합니다. 이 preflight는 업로드나 참가자 API 호출을 하지 않습니다. 공개 개발 샘플 실행을 통한 피드백과 제출 권리 확정은 별개입니다.

실제 진료지침 사용도 검사하려면 먼저 공개 파일을 내려받아 SHA256을 검사한 뒤만 풉니다. 재배포/제출 ZIP에는 넣지 않습니다.

```powershell
$novaGuideZip = Join-Path $env:TEMP "nova-guidelines-2026.zip"
Invoke-WebRequest https://nova.snubhai.org/downloads/nova-guidelines-2026.zip -OutFile $novaGuideZip
$novaExpectedGuideHash = "ef58c2f4369750af382f2706dcc1c9c7a85e3a93c261d880f7470d695eaf30d5"
if ((Get-FileHash -LiteralPath $novaGuideZip -Algorithm SHA256).Hash.ToLower() -ne $novaExpectedGuideHash) { throw "Guideline hash mismatch" }
$novaGuideRoot = Join-Path $env:TEMP ("nova-guidelines-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
Expand-Archive -LiteralPath $novaGuideZip -DestinationPath $novaGuideRoot
$env:NOVA_GUIDELINES_DIR = Join-Path $novaGuideRoot "guidelines"
& $novaPython scripts\pre_sample_validation.py --output-dir $novaPreflight --corpus-root $env:NOVA_GUIDELINES_DIR
```

본인 컴퓨터의 독립 PowerShell에서만 키를 입력합니다. `--list`에서 공개 case_id를 확인한 다음 C01/C03/C10 각각에 대응하는 ID를 직접 설정합니다. UUID가 C01 같은 이름이라고 가정하지 않습니다. 원문이 필요 없는 모든 분석 작업은 키를 제거한 뒤 수행합니다.

```powershell
$env:NOVA_API_BASE = "https://nova.snubhai.org"
$novaSecret = Read-Host "개인 개발 키 (채팅에 붙여 넣지 마세요)" -AsSecureString
$env:NOVA_DEV_KEY = [System.Net.NetworkCredential]::new("", $novaSecret).Password
try {
    & $novaPython scripts\run_dev_samples.py --human-run --list
    if ($LASTEXITCODE -ne 0) { throw "Sample listing failed" }
    $novaC01 = Read-Host "목록의 C01 공개 case_id"
    $novaC03 = Read-Host "목록의 C03 공개 case_id"
    $novaC10 = Read-Host "목록의 C10 공개 case_id"
    $novaResults = Join-Path $env:USERPROFILE ("nova-public-results-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
    & $novaPython scripts\run_dev_samples.py --human-run C01 C03 C10 --case-id "C01=$novaC01" --case-id "C03=$novaC03" --case-id "C10=$novaC10" --output $novaResults
} finally {
    Remove-Item Env:\NOVA_DEV_KEY -ErrorAction SilentlyContinue
    Remove-Variable novaSecret -ErrorAction SilentlyContinue
}
$novaAnalysis = Join-Path $env:TEMP "nova-public-analysis-v35.json"
& $novaPython scripts\analyze_official_samples.py $novaResults --output $novaAnalysis
& $novaPython scripts\import_human_official_results.py $novaResults
```

공식 샘플 검증 업로드는 출처/권리 문제와 기술 검사를 해결한 뒤 본인이 [공식 제출 UI](https://nova.snubhai.org/submissions/)에서 수행합니다. ZIP은 `$novaCheckout\submission\submission.zip`입니다. 문서에 없는 업로드 API/CLI는 만들지 않았습니다.

## 다음 검토에 제공할 자료와 남은 한계

- 새 공식 평가 화면의 6개 영역 점수, 제출 버전/시간, 완료·오류 상태가 보이는 스크린샷. 키·개인 식별자·민감한 세션 정보는 가립니다.
- `artifacts/human_official_review/`의 `official_sample_summary.json`, `doctor_quality.json`, `latency_tokens.json`, `exam_metrics.json`, `record_grounding.json`, `model_identity.json`, `rag_metrics.json`.
- 의학적 검토를 원하면 확인 후 민감 정보가 제거된 C01/C03/C10 결과와 per-call A–M 검토 annotation. 원문 프롬프트·진료지침 발췌·키/토큰·환경 전체 출력은 제공하지 않습니다.

실제 Doctor JSON/성능·서버 지연/토큰/EXAM 거절·새 점수는 HUMAN-RUN 증거가 필요합니다. API가 실제 revision을 노출하지 않으면 NOT EXPOSED / NOT DIRECTLY VERIFIED입니다. 새 프로필과 계획의 의학적 일반화·추적 간격은 임상 검토로 보강해야 합니다. 언어 근거 판정은 보수적인 어휘/범위 해석이며 완전한 의미 이해가 아닙니다. 기존 출처/권리 미해결 자산과 새 프로필의 권리 상태를 임의로 해제하지 않습니다. **기술 검사 통과와 공식 제출 준비 완료는 구분합니다.**

## 최종 전체 검사 실행 조건

전체 `tests/` 검사는 `NOVA_LLM_PROVIDER=mock NOVA_COMPETITION_RETRIEVAL=0`인 기존 개발 기본 설정에서 실행합니다. 예선 검색 모드는 별도 230개 전수 회귀와 실제 fake-SDK 검사에서 켭니다. 전역 검색 모드를 강제한 중간 실행에서 기존 검사 4개가 실패했으며, 시작 HEAD에서도 같은 4개 실패를 재현했습니다. 설정을 되돌리면 같은 assertion으로 4개 모두 통과했습니다. 중단한 중간 실행은 최종 통과 수에 합산하지 않습니다. 최종 검증 기록을 고정해야 가능한 런타임 바인딩 검사 1개만 전체 실행에서 미뤄 두고, 새 기록 생성 후 두 Python에서 따로 수행해 실제 합계에 포함합니다.

## 변경 파일 묶음

- 부호·문장 범위·한영 임상 개념: `nova_agent/clinical_assertions.py`, `clinical_concepts.py`, `multilingual_concepts.py`, `matching.py`, `feature_relations.py`, `competition/official_evidence.py`.
- 질환·동의어·관찰·후보/지원 판단: `nova_agent/clinical_profiles.py`, `knowledge/clinical_profiles.json`, `diagnosis_normalizer.py`, `state.py`, `differential.py`, `missing_info.py`, `final_decision.py`, `disposition.py`.
- 실제 예선 문진·Doctor 재시도·최종 기록/설명: `nova_agent/clinical_interview.py`, `competition/nova_sdk_adapter.py`.
- 개발 비교 도구: `evaluation/rubric_proxy_cases.json`, `scripts/evaluate_rubric_proxy.py`, `scripts/evaluate_official_fixture_efficiency.py`.
- Windows UTF-8 운영 보완: `scripts/human_sample_capture.py`, `scripts/pre_sample_validation.py`. 시작 HEAD의 Windows 경로·MANIFEST 수정은 보존했습니다.
- 검사: `tests/test_rubric_pipeline.py`, `tests/test_current_pre_guide_release.py`, `tests/test_verification_v7_consistency.py`. 뒤의 두 파일은 새 v35 스키마를 허용하며 기존 해시·진실성 assertion은 유지합니다.
- 대응하는 `submission/nova_agent/`·`submission/competition/` 미러, 현재 출처 목록/검사, README·현재 상태·이 보고서, 새 `artifacts/rubric_repair/` 증거와 v35 포인터/기록. 과거 v34 기록은 변경하지 않습니다.

## 최종 실행 결과와 고정 패키지

- 시작 원격 HEAD: `dc1b1b94182c8cd0d128f21bc78c215317945923`.
- 불변 런타임 커밋: `fb4b69b72639c5fb5a90df54bad3dfc07443442d`. 먼저 대상 브랜치에 push했습니다.
- 새 검증 기록: `artifacts/verification/local-release-fb4b69b-v35.json`; 이전 v34를 보존한 새 포인터와 이 증거는 두 번째 검증 커밋으로 push합니다. 검증 커밋/원격 최종 HEAD는 GitHub 브랜치의 해당 커밋과 `git rev-parse HEAD`로 확인합니다(자기 자신의 커밋 해시를 파일 안에 넣는 순환 기록은 만들지 않습니다).
- 확대한 집중 검사: **239 passed / 0 failed**. 전체 결과와 겹치므로 합산하지 않았습니다.
- Python 3.11.16: **2,772 passed / 0 failed / 1 skipped**. Python 3.12.14: **2,772 passed / 0 failed / 1 skipped**. 새 기록 이후의 바인딩 1개가 각 합계에 포함됩니다. 최종 deselected 0입니다. Torch가 없는 선택적 ML 학습 검사 1개는 예상 건너뜀이며 제출 모델 검사가 아닙니다.
- 최종 같은 조건 230개 회귀: Top-1 **219/222 → 219/222**, Top-3/5 **220/222 → 220/222**, critical **85/85 → 85/85**, 새 오답 **0**, 새 critical miss **0**. 평균 상호작용 **19.6435 → 19.6696**; EXAM **1,207 → 1,208**; 위반·미지원 SOAP 정보 **0**, 정보 유지 **100%**. 새 32개 재생과 3개 전체 fake-SDK 결과도 앞 표와 일치합니다.
- 마지막 기술 preflight **12/12 PASS**: 소스/미러/ZIP, SDK byte-identical, 핀, secret·누출 검사, 새 디렉터리·fake HTTP, 인터넷 차단·읽기 전용·2 CPU/8 GB Docker 및 실제 15,904문서 준비. Docker corpus peak RSS **65,220 KiB**. 출처/권리 BLOCKED이므로 READY=NO / exit 2이며, 기술 실패가 아닙니다.
- ZIP 로컬 경로: `/workspace/nova/submission/submission.zip`(Git에는 ZIP 자체를 올리지 않았습니다).
- ZIP **909,211 bytes**, **111 files**, <50 MB. `run.py`, `requirements.txt`, `nova_sdk.py`가 모두 archive root에 있습니다. 중첩 submission 폴더·venv·코퍼스·모델 가중치·키·실제 서버 원문 로그·중복 경로·symlink·encrypted entry가 없습니다.
- ZIP SHA256: `17e11b90ffdb5c62533bcc2ef6bde52796dd09c25a8e374e50ce04a9ac4c3ecf`.
- MANIFEST SHA256: `a08e2fea96b5d2329b48448658a7a55372d5310120385d8ae92f5b16edb050d4`.
- 정확한 source/staging/member runtime verifier: **PASS**; SOURCE_DATE_EPOCH는 위 런타임 커밋으로 고정했습니다. 최종 preflight 재생성 ZIP도 동일 SHA256입니다.

참가자 키를 조회·사용하지 않았고 실제 공식 공개 샘플·GPT-OSS·샘플 검증 업로드를 실행하지 않았습니다. 새 공식 점수는 없습니다. 미해결 권리 94개, 임상 검토 부재, 새 사례의 비독립성과 실제 모델/서버 동작은 앞서 표시한 그대로입니다. 같은 내용으로 다시 첨부한 프롬프트는 중복 실행하지 않고 이 결과로 함께 충족합니다.
