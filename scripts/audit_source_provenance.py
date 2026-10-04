import json,subprocess,hashlib,sys
sys.path.insert(0,str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from pathlib import Path
from nova_agent.ontology.registry import get_default_catalog
assets=sorted(Path('nova_agent/knowledge').rglob('*.json'))+ [Path('nova_agent')/n for n in ('lay_language.py','concept_normalizer.py','chief_complaint.py','taxonomy.py','objective_evidence.py','syndrome_relationships.py','severity_evidence.py','evidence_assessment.py') if (Path('nova_agent')/n).exists()]
# Include every Python runtime file conservatively: several embed clinical mappings.
assets=sorted(set(assets)|set(Path('nova_agent').rglob('*.py')))
rows=[];logs=[]
for p in assets:
 hist=subprocess.check_output(['git','log','-1','--format=%H|%aI','--',str(p)],text=True).strip().split('|')
 rows.append({'file':str(p),'purpose':'Runtime clinical data / mapping / heuristic or supporting code; per-file inventory', 'original_source':'Repository internal implementation; specific medical source UNRESOLVED','source_version':hist[0],'license':'UNRESOLVED','research_publication_use_allowed':'UNRESOLVED','derived_or_modified':True,'ai_assisted_generation':'Known for enrichment/lay-language/multilingual; otherwise not independently recoverable','bundled_in_submission':True,'review_status':'No documented clinical/source-license signoff','sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 if p.suffix=='.json' or p.name in ('lay_language.py','concept_normalizer.py','multilingual_concepts.py'):
  logs.append({'output_file':str(p),'tool_model':'UNRESOLVED: historical engineering-agent attribution is not an exact model/version','date':hist[1] if len(hist)>1 else 'UNRESOLVED','date_definition':'Last repository commit, not proven generation time','instruction_prompt':'UNRESOLVED: original verbatim generation prompt not present','source_material':'General knowledge claimed; no auditable medical source supplied','manual_review_status':'UNREVIEWED / no documented clinician signoff','commit':hist[0]})
for p in sorted(Path('evaluation').glob('*cases*.py')):
 if 'blind' in p.name:continue
 logs.append({'output_file':str(p),'tool_model':'UNRESOLVED','date':'UNRESOLVED','instruction_prompt':'UNRESOLVED; scripts/ and case source retain construction code, not original chat prompt','source_material':'Synthetic development hypotheses, not patient evidence','manual_review_status':'Not independently clinician-adjudicated','bundled_in_submission':False})
Path('artifacts/round_m/source_inventory.json').write_text(json.dumps(rows,indent=2)+'\n')
Path('artifacts/round_m/generation_inventory.json').write_text(json.dumps(logs,indent=2)+'\n')
head='''# Sources and licenses

Audit date: 2026-10-05 Asia/Seoul. Status: UNRESOLVED — NOT CLEARED FOR OFFICIAL SUBMISSION.

AI generation is not a medical source. Internal authorship, “standard clinical references”,
“engineering-agent general knowledge” and `unreviewed_general_knowledge` do not prove provenance,
clinical validity, ownership or research-publication permission. No license has been inferred.

The complete file/version/hash inventory is `artifacts/round_m/source_inventory.json`.
All listed runtime assets are included only in the LOCAL PRE-GUIDE candidate for engineering review.
They must receive source/license and clinical review before an official release. Documentation
completion does not turn an unresolved license into PASS.

| File | Purpose | Original source/version | License / research use | Derived | AI-assisted | Bundled | Review |
|---|---|---|---|---|---|---|---|
'''
for r in rows:head+=f"| `{r['file']}` | {r['purpose']} | Internal; `{r['source_version'][:7]}`; medical source UNRESOLVED | UNRESOLVED / UNRESOLVED | yes | See generation log | yes | unreviewed |\n"
head+='''
## Dependencies and non-bundled assets

- `submission/requirements.txt`: Pydantic >=2.6,<3 installed externally. Installed version and license metadata are recorded below; a version range is not a locked final official environment.
- `nova_agent/ontology/providers/{snomed,icd10,icd11}.py`: import adapters only. No licensed terminology snapshots are bundled. Future supplied snapshots require their own exact licenses and permission review.
- Synthetic evaluation sets, answers, tests, archives, frontend, backend, training artifacts: NOT bundled.
- Fixed organizer model is configured as `openai/gpt-oss-20b`, revision `4d7ae4984b7db7de8f8457170b3f1a419ee76d52`; no weights are bundled. Actual organizer model execution remains NOT VERIFIED.

## Remediation

Recover original generation records and source materials from their authors; resolve ownership and
research-publication licenses; replace or remove assets that cannot be cleared. Validate selected
clinical profiles with identifiable sources and qualified review. Do not manufacture citations or
populate the remaining Tier-2 concepts with generated facts.
'''
import importlib.metadata as im
for name in ('pydantic','pydantic-core','annotated-types','typing-extensions','typing-inspection'):
 try:
  m=im.metadata(name);head+=f"\n- Installed dependency `{name}` {im.version(name)}: metadata license `{m.get('License-Expression') or m.get('License') or 'UNRESOLVED'}`; metadata source {m.get('Project-URL','UNRESOLVED')}. License text review/research-use clearance pending.\n"
 except im.PackageNotFoundError:pass
Path('docs/compliance/SOURCES_AND_LICENSES.md').write_text(head)
text='''# LLM generation log

Historical generation records are incomplete. The exact tool/model, original prompt and source
material are UNRESOLVED unless explicitly stated below. A commit timestamp is not a generation
receipt. This log records gaps; it does not reconstruct invented provenance.

Machine-readable inventory: `artifacts/round_m/generation_inventory.json`.

| Output | Tool/model | Date | Prompt/instruction | Source material | Manual review |
|---|---|---|---|---|---|
'''
for r in logs:text+=f"| `{r['output_file']}` | {r['tool_model']} | {r['date']} | {r['instruction_prompt']} | {r['source_material']} | {r['manual_review_status']} |\n"
text+='''
## This pass

Tool: ChatGPT Work / Codex coding assistant; exact underlying model build is not exposed, so no
model version is claimed. Date: 2026-10-05 KST. Instruction: user-supplied current-state recovery,
Round M validation, competition compliance, pre-guide release hardening; preserve v19 unused,
no v20, no guessed organizer API, local regression, commit/push. Output: boundary code/tests,
provenance inventories, evaluation summaries and release documentation. Source: current repository,
public rules/evaluation/FAQ. General code corrections: comma-bounded negation scope and whole-word alias matching. No new clinical facts, development labels or private evaluation labels
were generated in this pass. Code reviewed through local tests; no clinician review claimed.
'''
Path('docs/compliance/LLM_GENERATION_LOG.md').write_text(text)
e=json.loads(Path('nova_agent/knowledge/tier2_enrichment.json').read_text());entries={r['id']:r for r in e['entries']}
tier2=[c for c in get_default_catalog().all_concepts() if c.tier.value=='TIER2_STRUCTURED']
r={'tier2_total':len(tier2),'tier2_enriched':len(entries),'tier2_unenriched':len(tier2)-len(entries),'tier2_with_confirmatory_findings':sum(bool(x.get('confirmatory_findings')) for x in entries.values()),'tier2_with_provenance_metadata':len(entries) if e.get('provenance') else 0,'tier2_with_verified_medical_provenance':0,'note':'Global authorship metadata is not an original medical source; exact entry intersection audited separately. No mass fill.'}
Path('artifacts/round_m/tier2_audit.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
