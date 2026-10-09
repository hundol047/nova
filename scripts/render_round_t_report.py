"""Render actual recorded metrics into the Round T review; never edit evaluation data."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text())
def count(rate,n):return round(rate*n)
def main():
 c=read('artifacts/round_t/final/comparison.json');tests=read('artifacts/round_t/final/test_summary.json')
 lines=['## 최종 동일 조건 비교','', '예선은 mock + competition retrieval, TEST 없음. 이전과 같은 scorer·분모·기본 응답이다. 첫9행은 개발/회귀이며 마지막12개만 마지막 runtime에서 처음 실행한 새 확인이다.','',
 '| 세트 | 전체/채점 | 정답 전→후 | 위험 정답 전→후 | 평균 턴 전→후 | 최대 턴 전→후 | 새 정답/새 오답 |',
 '|---|---:|---:|---:|---:|---:|---:|']
 names={'preliminary':'예선 개발','round_p':'P 개발','round_q':'Q 개발','round_r':'R 개발','round_s':'S 개발','acceptance_development':'기존 검수 개발','round_t_promoted_development':'T32 개발 전환','prior_confirmation_development':'confirmation12 개발 전환','final_probe_promoted_development':'probe8 개발 전환','unused_postfreeze_confirmation':'새 postfreeze12'}
 for k,name in names.items():
  d=c[k];b,a=d['before'],d['after']
  lines.append(f"| {name} | {a['cases']}/{a['scored']} | {b['correct']}→{a['correct']}/{a['scored']} | {b['critical_correct']}→{a['critical_correct']}/{a['critical_cases']} | {b['avg_interactions']:.2f}→{a['avg_interactions']:.2f} | {b['max_interactions']}→{a['max_interactions']} | {len(d['new_correct'])}/{len(d['new_wrong'])} |")
 lines+=['','새 scored 오답(동일 세트 비교):','']
 for k,name in names.items():
  if c[k]['new_wrong']:lines.append('- '+name+': '+', '.join(c[k]['new_wrong']))
 lines+=['','ValP17/DevQ28의 미분화는 rate-only 명명 제한의 채점 손실과 구분해 해석한다. ValP29의 악화→호전 역전, RoundI_enzyme_sparse의 선택적 증상 No 뒤 위험 대안 명명은 실제 잔여 기전이다. PrelimKo_Abd_Pancreatitis도 새 오답으로 남기며, 이를 제외하거나 정답으로 바꾸지 않았다.','',
 '### 효율·규칙·SOAP', '', '| 세트 | 의미 중복 전→후 | 불필요 EXAM 전→후 | 미해결 위험 대안 사례 전→후 |', '|---|---:|---:|---:|']
 for k,name in names.items():
  b,a=c[k]['before'],c[k]['after'];lines.append(f"| {name} | {b['semantic_duplicate_questions']}→{a['semantic_duplicate_questions']} | {b['unnecessary_exams']}→{a['unnecessary_exams']} | {b['unresolved_critical_cases']}→{a['unresolved_critical_cases']}/{a['cases']} |")
 totals={key:sum(c[k]['after'][key] for k in names) for key in ['rule_violations','duplicate_actions','malformed','soap_unsupported_lines']}
 lines+=['',f"위 세트의 규칙 위반 {totals['rule_violations']}, 완전 동일 행동 반복 {totals['duplicate_actions']}, malformed {totals['malformed']}, 문자열 기반 unsupported SOAP line {totals['soap_unsupported_lines']}. 세트 사이에 동일·유사 사례가 있으므로 합산해 독립 표본의 성능 분모로 사용하지 않는다. 전체적으로 효율 개선을 주장하지 않는다. SOAP 의미 오류는 앞서 별도 공개했다.", '',
 '### TEST 허용 개발 회귀', '', '| suite | 정답/분모 | 위험 정답/분모 | 새 오답 |', '|---|---:|---:|---|']
 for k,v in c['test_enabled'].items():
  a=v['after'];n=a['n_scored_cases'];nc=a['n_critical_cases'];lines.append(f"| {k} | {count(a['scored_diagnostic_accuracy'],n)}/{n} | {count(a['critical_diagnosis_recall'],nc)}/{nc} | {', '.join(v['new_wrong']) or '0'} |")
 m=c['round_m_test_enabled'];b,a=m['before'],m['after'];n=a['scored_cases'];nc=a['critical_count'];lt=a['long_tail'];bl=b['long_tail'];ln=lt['count']
 lines += ['',f"M: {b['cases']}전체/{n}채점, Top1 {count(b['Top1'],n)}→{count(a['Top1'],n)}/{n}, 위험 {count(b['critical_Top1'],nc)}→{count(a['critical_Top1'],nc)}/{nc}; 새 오답 {', '.join(m['new_wrong']) or '0'}. 평균 턴 {b['average_turns']:.2f}→{a['average_turns']:.2f}. 예선 점수와 혼합하지 않는다.",
 f"Long-tail {ln}개: Top1 {count(bl['Top1'],ln)}→{count(lt['Top1'],ln)}/{ln}, Top5 {count(bl['Top5'],ln)}→{count(lt['Top5'],ln)}/{ln}, Top10 {count(bl['Top10'],ln)}→{count(lt['Top10'],ln)}/{ln}. Category 기반 개발 수치이며 임상 검증률이 아니다. 같은 M의 non-long-tail common/control은97/97이며 전체 common 질환 성능으로 일반화하지 않는다.", '', '### 검색·재순위', '', '| 입력 / 단계 | 기준선 | 최종 |', '|---|---:|---:|']
 for mode,label in [('chief_only','chief-only'),('all_scripted_history_upper_bound','scripted history upper bound')]:
  before=c['retrieval_proxy']['before'][mode];after=c['retrieval_proxy']['after'][mode];nn=after['n']
  for key,stage in [('retrieved','@150'),('retained25','엄격 Top25'),('before_safety25','안전 교체 전 evidence Top25')]:
   lines.append(f"| {label} / {stage} | {before[key]}/{nn} ({before[key]/nn:.1%}) | {after[key]}/{nn} ({after[key]/nn:.1%}) |")
 lines+=['',f"실제 M 대화 **종료 시점**: @150 {count(b['retrieval_at150'],n)}→{count(a['retrieval_at150'],n)}/{n}, 엄격 Top25 {count(b['rerank_at25'],n)}→{count(a['rerank_at25'],n)}/{n}, safety overflow 포함 {count(b['rerank_truth_retention'],n)}→{count(a['rerank_truth_retention'],n)}/{n}, active {count(b['active_truth_retention'],n)}→{count(a['active_truth_retention'],n)}/{n}. 초기 검색 proxy와 다르다. M에서 retrieval≥90%, strict rerank≥80%, active≥95%는 달성했으나 초기 chief-only 목표와 전체 예선 회귀 기준은 미달이다.",
 '','### 테스트·패키지·판정','',f"전체 tests/: **{tests['passed']:,} passed / {tests['failed']} failed / {tests['skipped']} skipped / {tests['deselected']} deselected**. runtime·NCIt·release-binding의 서로 겹치지 않는 실행이다. 별도 반복한 문서/최소 대조쌍 검사는 중복 합산하지 않았다. skip은 torch training roundtrip 환경 부재다. 문서 진단 추출+실제 후보 가산10/10. static leakage scan807사례/16module/158core파일은 NO OBVIOUS LEAKAGE이며 blind 실행이 아니다. specificity audit의 reviewed 표시는 의미 정확성 보증이 아니다.",
 '', '97개 root/submission runtime 바이트 일치, 임시 checkout 빌드, ZIP 감사·secret scan·validation·독립 mock PASS. 99개 runtime+launcher 파일이 공개 소스 commit과 byte-identical이다. 로컬 v25 ZIP SHA-256: `252220bb578639d3c88d0a53805de01e26d8a1871c2068cefcaafaac8573eeeb`, runtime761fcda에 연결했다. 자산 hash coverage와 별개로86개 제출 자산의 권한/저자 확인은 미해결이다.',
 '', '| 판정 | 결과 |', '|---|---|', '| 실행한 전체 테스트 | PASS |', '| 오프라인 구현 전체 수락 | **FAIL — 일부 기전 개선, 새 scored 회귀 남음** |', '| 마지막 새 사례 전체 수락 | **FAIL — 6/6 진단 점수와 별개로 정보 부족2건 명명 실패** |', '| 로컬 패키지 무결성·독립 mock | PASS |', '| 완결된 공개 v25 배포 | 미완료 — 소스 검토 브랜치만 게시 |', '| 실제 GPT-OSS / 공식 API | **미검증 / 미검증** |', '| 독립 임상 검증 | **미검증** |',
 '', '이전 자동 승인 검토가 상세 평가 묶음 공개를 거절한 범위를 넘어 새 trace/XML/ZIP을 게시하지 않았다. 공개 CURRENT_RELEASE는 이전 배포 기록이며 이 소스 검토 브랜치의 완결된 release binding이 아니다. 로컬 원본 기록에는 실패 후보·중단 실행·최종 실행을 분리 보존했다. main/원래 Claude 브랜치 이동·force-push는 없다.']
 p=ROOT/'docs/competition/ROUND_T_REPAIR_REPORT_KO.md';s=p.read_text();s=s.replace('<!-- RESULTS -->','\n'.join(lines));p.write_text(s)
 summary={'executed_local_runtime':'761fcda7f4f5b6c58b0e0b6e8b77047b37301782','public_source_runtime':'0b9cd87c7509e2703b877939cb3fc89c70e0741d','full_release_published':False,'tests':tests,'comparison':c,'new_profile_count':0,'tier2_catalog':1246,'tier2_enrichment_entries':83,'remaining_without_enrichment_file_entry':1163,'official_api':'NOT VERIFIED','real_model':'NOT VERIFIED','overall_acceptance':'FAIL / partial repair','local_zip_sha256':'252220bb578639d3c88d0a53805de01e26d8a1871c2068cefcaafaac8573eeeb'}
 (ROOT/'docs/competition/ROUND_T_VERIFICATION_SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 status=ROOT/'docs/CURRENT_STATUS.md';s=status.read_text();a=c['preliminary']['after'];s=s.replace('<!-- ROUND_T_FINAL_SUMMARY -->',f"Full local tests: **{tests['passed']:,} passed, 0 failed, 1 skipped, 0 deselected**. Preliminary: **{a['correct']}/{a['scored']}**, critical **{a['critical_correct']}/{a['critical_cases']}**. Local v25 package integrity/mock PASS; overall regression acceptance FAIL. Public byte-equivalent source runtime: `0b9cd87c7509e2703b877939cb3fc89c70e0741d` on `codex/nova-round-t-source-review-20261009`. Source parity covers97 runtime files plus launcher/requirements, not the full Git tree.");status.write_text(s)
 print('Rendered report and aggregate summary from recorded artifacts.')
if __name__=='__main__':main()
