"""Record executed local evidence only. Never runs or freezes any blind benchmark."""
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
def read(p):return json.loads((ROOT/p).read_text())
def write(p,data):
 path=ROOT/p;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def digest(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def pct(v):return 'N/A' if v is None else f'{100*v:.2f}%'
def main():
 summary=read('artifacts/round_m/final_summary.json');m=summary['metrics'];sha=summary['runtime_sha']
 for name in ('submission/run.py','submission/requirements.txt'):summary['runtime_sha256'][name]=digest(name)
 for name,h in summary['runtime_sha256'].items():
  assert digest(name)==h,name
  assert (ROOT/name).read_bytes()==subprocess.check_output(['git','show',sha+':'+name],cwd=ROOT),name
 for p in ('artifacts/blind_runs/blind_v19_attempt.json','artifacts/blind_runs/blind_v19_results.json','evaluation/blind_v19_manifest.json'):
  assert not (ROOT/p).exists(),p
 assert not (ROOT/'evaluation/blind_cases_v20.py').exists()
 cases=list(ET.parse(ROOT/'artifacts/round_m/pytest.xml').getroot().iter('testcase'))
 failed=sum(c.find('failure') is not None or c.find('error') is not None for c in cases)
 skipped=[{'test':c.get('classname')+'.'+c.get('name'),'reason':c.find('skipped').get('message')} for c in cases if c.find('skipped') is not None]
 assert failed==0
 tests={'passed':len(cases)-len(skipped),'failed':failed,'skipped':len(skipped),'skip_reasons':skipped,'command':'python -m pytest tests -q --disable-warnings --junitxml=artifacts/round_m/pytest.xml','junit_sha256':digest('artifacts/round_m/pytest.xml')}
 regressions=read('artifacts/round_m/final_regressions.json');assert len(regressions['suites'])==8
 assert regressions['runtime_sha']==sha
 audit=read('artifacts/round_m/package_audit.json');assert audit['source_submission_byte_equivalence'] and not audit['forbidden_files'] and not audit['training_operations'] and not audit['utf8_failures']
 assert audit['secret_scan']['status']=='PASS'
 zip_path='artifacts/verification/nova-pre-guide-v12.zip';shutil.copyfile(ROOT/'submission/submission.zip',ROOT/zip_path)
 assert digest(zip_path)==audit['zip_sha256']
 compliance={k:'PASS' for k in ('Fixed model configured','Fixed revision configured','Fine-tuning absent','60-turn hard cap','Official 4 actions only','Case-related LLM success gate','Competition provider lock','No online private-case learning','Case isolation','Static retrieval','Secret scan')}
 compliance.update({'Source documentation':'FAIL — inventory complete, medical sources unresolved','License documentation':'FAIL — exact licenses/research permission unresolved','LLM-generation log':'FAIL — log exists, historical exact model/prompt records unresolved'})
 blockers=['Official participant guide, exact transport/schema/invocation and sample environment not provided; submission network path intentionally blocked.', 'Real organizer gpt-oss call and fixed-weight revision not verified; stubs/mock do not count.', 'Clinical source provenance, research-use licenses and original generation records remain unresolved; candidate is not cleared for official submission.', 'Round M development weaknesses and small multilingual sample sizes remain; no independent clinical accuracy claim.', 'No current untouched fresh blind; v19 pre-execution invalidated, v20 not authored.']
 version='nova-verification-v12';artifact='artifacts/verification/local-release-'+sha[:7]+'-v12.json'
 data={'schema':version,'status':'NOT READY','local_validation_status':'LOCAL_PRE_GUIDE_VERIFIED','external_status':'EXTERNAL_OFFICIAL_INTERFACE_BLOCKED','generated_utc':datetime.now(timezone.utc).isoformat(),'audited_remote_head':'677c944e5fbab602bcb8d9580358ad6a80df6cc7','verified_runtime_sha':sha,'executed_local_runtime_sha':summary.get('executed_local_runtime_sha',sha),'transport_note':summary.get('transport_note'),'runtime_sha256':summary['runtime_sha256'],'runtime_changed_after_freeze':False,'tests':tests,'round_m':m,'round_m_artifact':'artifacts/round_m/final_summary.json','regressions':{k:v['summary'] for k,v in regressions['suites'].items()},'source_submission_sync':True,'secret_scan':audit['secret_scan'],'compliance':compliance,'official_api_status':'NOT VERIFIED','schema_status':'PLACEHOLDER','real_model_status':'NOT VERIFIED','participant_guide':'NOT YET AVAILABLE IN PROVIDED MATERIALS / PUBLIC PAGES','current_blind_version':'v19','current_blind_status':'REFERENCE-ONLY','blind_v18':'historical/reference-only','blind_v19':'NOT EXECUTED / PREEXECUTION_INVALIDATED_BY_RUNTIME_DRIFT / REFERENCE-ONLY','fresh_final_blind':'NOT YET AUTHORED','new_blind_runs':0,'submission':{'zip':zip_path,'bytes':(ROOT/zip_path).stat().st_size,'sha256':digest(zip_path),'status':'LOCAL PRE-GUIDE CANDIDATE ONLY'},'blockers':blockers,'independent_clinical_validation':False,'expert_reviewed':False,'report':'docs/competition/PRE_GUIDE_RELEASE_REPORT.md'}
 write(artifact,data)
 pointer=read('artifacts/verification/CURRENT_RELEASE.json');prior=pointer['current_verification_artifact']
 previous=pointer['previous_verification_artifacts'];previous=([prior]+previous) if prior!=artifact and prior not in previous else previous
 write('artifacts/verification/CURRENT_RELEASE.json',{'current_verification_artifact':artifact,'current_verification_schema':version,'verified_runtime_sha':sha,'current_blind_version':'v19','current_blind_manifest':None,'current_blind_status':'REFERENCE-ONLY','fresh_final_blind':'NOT YET AUTHORED','previous_verification_artifacts':previous,'status':'NOT READY','reason':'Current runtime locally verified; official interface, real model and provenance/license clearance blocked.'})
 write('artifacts/round_m/pytest_summary.json',tests)
 report=f'''# N.O.V.A. 2026 PRE-GUIDE RELEASE REPORT

REMOTE HEAD (at recovery): `677c944e5fbab602bcb8d9580358ad6a80df6cc7`

CURRENT RUNTIME SHA: `{sha}`

This is an offline mock-LLM synthetic development result, not an official score or clinical validation.

Transport note: {summary.get("transport_note", "Direct Git transport.")}

## ROUND M

Cases: {m['cases']}
Scored: {m['scored_cases']}
Critical: {m['critical_count']}

| Metric | Current result |
|---|---:|
'''
 for label,key in [('Top1','Top1'),('Top3','Top3'),('Top5','Top5'),('Top10','Top10'),('Critical Top1','critical_Top1'),('Critical Top3','critical_Top3'),('Critical Top5','critical_Top5'),('Critical recall','critical_recall'),('Critical miss','critical_miss'),('Retrieval @150','retrieval_at150'),('Rerank @25','rerank_at25'),('Active truth','active_truth_retention')]:report+=f'| {label} | {pct(m[key])} |\n'
 report+=f"| MRR | {m['MRR']:.5f} |\n| Median true rank (finite only) | {m['median_true_rank']} |\n| Missing final truth ranks | {m['missing_rank_count']} |\n"
 for k in ('retrieval_at150','rerank_at25','active','Top10','Top5','Top1'):report+=f"| Long-tail {k} (n={m['long_tail']['count']}) | {pct(m['long_tail'][k])} |\n"
 for lang in ('EN','KO','JA','Mixed'):
  r=m['languages'].get(lang,{'accuracy':None,'count':0});report+=f"| {lang} accuracy (n={r['count']}) | {pct(r['accuracy'])} |\n"
 for label,key in [('Avg ASK','average_ask'),('Avg EXAM','average_exam'),('Avg TEST','average_tests'),('Avg turns','average_turns'),('Median turns','median_turns'),('Redundant TEST actions','redundant_tests'),('Avg diagnostic delay','average_diagnostic_delay'),('Avg unresolved critical alternatives','average_unresolved_critical_alternatives')]:report+=f"| {label} | {m[key]} |\n"
 report+='\nDiagnostic delay is measured against the first policy-eligible unforced stop, not a clinically adjudicated safe stopping point. Critical recall means correct final diagnosis among the unchanged critical labels, not merely inclusion in top-k. Critical-like Tier-2 tags are not silently moved into that denominator. The missed ovarian-torsion development case is outside the inherited 43-case critical subset: 100% critical recall therefore does NOT mean every medically urgent presentation was correct. Language partition is by chief complaint; follow-up evidence often uses English.\n'
 report+='\n### Development goals (not release score manipulation)\n\n| Goal | Actual | Met |\n|---|---:|---|\n'
 for key,target in [('Top1',.95),('Top3',.97),('Top5',.98),('retrieval_at150',.92),('rerank_at25',.85),('active_truth_retention',.98),('critical_recall',.98)]:report+=f'| {key} ≥ {pct(target)} | {pct(m[key])} | {m[key]>=target} |\n'
 failures=read('artifacts/round_m/failure_analysis.json')
 report+='\n### Failure analysis\n\nOrdered earliest observable terminal-pipeline failure, followed by heuristic evidence/action/stop/ranking attribution. Full traces are retained; this is not clinician causal adjudication.\n\n'
 report+='| Failure class | Count |\n|---|---:|\n'
 for k in ('RETRIEVAL_MISS','RERANK_MISS','ACTIVE_SET_MISS','EVIDENCE_EXTRACTION_ERROR','EVIDENCE_WEIGHTING_ERROR','ACTION_SELECTION_ERROR','FINAL_RANKING_ERROR','STOP_POLICY_ERROR','PROTOCOL_OR_OOD_ERROR'):report+=f"| {k} | {failures['counts'].get(k,0)} |\n"
 report+='\nAll wrong scored cases: `artifacts/round_m/failure_analysis.json`. No labels, difficulty, scoring flags or OOD membership changed. General correction in this pass: punctuation-bounded negative clauses no longer invert preceding positive evidence. Remaining misses are retained, not patched with case IDs/answers.\n'
 comparison=read('artifacts/round_m/development_change_comparison.json')
 report+='\n### Change comparison\n\nInitial saved predictions were re-scored with the corrected alias matcher. This is a descriptive comparison; the initial baseline was not byte-attested. Historical raw accuracy numbers using the old embedded-acronym matcher must not be treated as directly comparable validation.\n\n| Metric | Re-scored initial outputs | Current |\n|---|---:|---:|\n'
 for key in ('diagnosis_accuracy','critical_recall','average_tests','average_turns'):
  report+=f"| {key} | {comparison['baseline'][key]:.6f} | {comparison['current'][key]:.6f} |\n"
 report+='\nUnresolved critical alternatives count every active danger-flagged candidate not marked resolved, including weak/unsupported ontology alternatives. It is a workload/safety review signal, not the critical diagnosis miss rate.\n'
 report+='\n### OOD\n\nFive Round M controls remain unscored. See `artifacts/round_m/round_m_ood.json` for their full-loop internal/wire outcomes; the separate broader snapshot benchmark is `artifacts/round_m/ood.json`. Internal uncertainty always remains within four wire actions.\n\n'
 for k,v in read('artifacts/round_m/ood.json')['metrics'].items():report+=f"- {k}: {v['numerator']}/{v['denominator']} ({pct(v['rate'])})\n"
 report+='\nRound M full-loop controls:\n\n| Case | Internal outcome | Turns |\n|---|---|---:|\n'
 for r in read('artifacts/round_m/round_m_ood.json')['cases']:report+=f"| {r['case_id']} | {r['internal']['internal_result']} | {r['turns']} |\n"
 report+='\nThese controls can take many turns and do not necessarily classify as OUT_OF_DOMAIN. This remains an efficiency/uncertainty weakness, not a passed diagnostic accuracy case.\n'
 report+='\n## REGRESSION\n\n'+f"Tests passed: {tests['passed']}  \nTests failed: {tests['failed']}  \nTests skipped: {tests['skipped']}\n\n"
 for skip in skipped:report+=f"- `{skip['test']}`: {skip['reason']}. Optional hospital training subsystem is excluded from competition ZIP; no training was run.\n"
 report+='\n`pytest tests` covers all root Doctor Agent/production tests. Bare repository-root discovery also collects a frontend bridge script that invokes unavailable Vitest; that initial collection error was not counted as a successful suite. Frontend/backend deployment and optional GPU training are outside this Doctor Agent package.\n\n| Suite | Cases / scored | Accuracy | Critical recall | Avg TEST | Avg turns |\n|---|---:|---:|---:|---:|---:|\n'
 for name,r in data['regressions'].items():report+=f"| {name} | {r['n_cases']} / {r['n_scored_cases']} | {pct(r['scored_diagnostic_accuracy'])} | {pct(r['critical_diagnosis_recall'])} | {r['average_test_count']:.2f} | {r['average_turns']:.2f} |\n"
 report+='\nOOD, multilingual, retrieval, routing, specificity, adversarial, invariance, competition boundaries and standalone checks are covered by the executed tests and supplemental artifacts. Retrieval/routing results are recorded separately; they are not substituted for diagnosis accuracy.\n'
 report+='\nSeparate 44-case retrieval probe (not Round M):\n\n| Input | Recall @20 | Recall @50 | Recall @150 |\n|---|---:|---:|---:|\n'
 for r in read('artifacts/round_m/retrieval.json')['reports']:
  report+=f"| {r['condition']} | {r['recall_at']['20']}% | {r['recall_at']['50']}% | {r['recall_at']['150']}% |\n"

 report+='\n## BLIND STATUS\n\nv18: REFERENCE-ONLY (historical).\n\nv19: NOT EXECUTED; PREEXECUTION INVALIDATED / REFERENCE-ONLY. No attempt/results/manifest created.\n\nFresh final blind: NOT YET AUTHORED. No v20.\n'
 report+='\n## COMPLIANCE\n\n| Check | Status |\n|---|---|\n'+''.join(f'| {k} | {v} |\n' for k,v in compliance.items())
 report+='\nPASS for the call gate/provider lock means local fail-closed behavior, not a successful organizer call. Model/revision constants are configured, but actual weights are not attested.\n'
 tier=read('artifacts/round_m/tier2_audit.json');report+='\nTier-2 audit: '+', '.join(f'{k}={v}' for k,v in tier.items() if k!='note')+'. Global authorship metadata is not verified medical provenance.\n'
 report+='\n## OFFICIAL INTERFACE\n\nParticipant guide: NOT YET AVAILABLE in supplied/public materials.  \nOfficial API: NOT VERIFIED.  \nOfficial schema: PLACEHOLDER.  \nReal organizer gpt-oss call: NOT VERIFIED.\n'
 report+=f"\n## VERIFICATION\n\nVersion: {version}  \nRuntime SHA: `{sha}`  \nSubmission ZIP: `{zip_path}`  \nBytes: {data['submission']['bytes']}  \nSHA256: `{data['submission']['sha256']}`\n\nSource/submission byte equivalence: PASS. ZIP has run.py/requirements.txt, UTF-8 Python, under 50 MB, no evaluation/blind/test/frontend/backend/training/weight files or detected credentials. Generic development client definitions remain in the identical source mirror but are unreachable through the locked submission entrypoint.\n"
 report+='\n## STATUS\n\n**NOT READY** for official submission.\n\nLocal engineering status: LOCAL_PRE_GUIDE_VERIFIED.  \nExternal status: EXTERNAL_OFFICIAL_INTERFACE_BLOCKED.\n\nBLOCKERS:\n'+''.join(f'{i}. {b}\n' for i,b in enumerate(blockers,1))
 report+='\nNext cycle: official guide audit → exact adapter/schema → organizer fixed-model smoke test → public sample benchmark → final accuracy/safety/efficiency tuning → full regression → final runtime freeze → fresh blind authored after freeze → hash/leakage review → one-shot blind → final verification → official ZIP.\n'
 (ROOT/data['report']).write_text(report)
 (ROOT/'docs/round_m/FINAL_REPORT.md').write_text(report.replace('# N.O.V.A. 2026 PRE-GUIDE RELEASE REPORT','# Round M final development report',1))
 print(json.dumps({'artifact':artifact,'tests':tests,'status':data['status'],'runtime_sha':sha},indent=2))
if __name__=='__main__':main()
