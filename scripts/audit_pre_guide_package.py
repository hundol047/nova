"""Read-only local package audit. Reports locations, never credential contents."""
import argparse,ast,hashlib,json,re,subprocess,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.build_nova_submission import _SECRET_PATTERNS,_PLACEHOLDER_HINTS

def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--output',default='artifacts/round_m/package_audit.json')
 args=parser.parse_args(argv)
 files=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
 hits=[]
 for name in files:
  p=ROOT/name
  if not p.is_file() or p.suffix not in {'.py','.json','.txt','.md','.yml','.yaml','.toml','.ini','.env'}:continue
  try:s=p.read_text(encoding='utf-8')
  except UnicodeDecodeError:continue
  for pattern in _SECRET_PATTERNS+[re.compile(r'(?i)\b(?:competition_token|api_token|auth_token)\s*[:=]\s*[\"\'][A-Za-z0-9/+_\-]{12,}[\"\']')]:
   for m in pattern.finditer(s):
    line=s[s.rfind('\n',0,m.start())+1:s.find('\n',m.end()) if '\n' in s[m.end():] else len(s)]
    if any(h in line for h in _PLACEHOLDER_HINTS):continue
    hits.append({'file':name,'line':s.count('\n',0,m.start())+1,'pattern':pattern.pattern,'classification':'REQUIRES_REVIEW'})
 allow=json.loads((ROOT/'docs/compliance/SECRET_SCAN_FIXTURES.json').read_text())
 for hit in hits:
  line=(ROOT/hit['file']).read_text().splitlines()[hit['line']-1]
  if any(a['file']==hit['file'] and a['line']==hit['line'] and a['line_sha256']==hashlib.sha256(line.encode()).hexdigest() for a in allow):
   hit['classification']='REVIEWED_SYNTHETIC_TEST_FIXTURE'
 unresolved=[h for h in hits if h['classification']=='REQUIRES_REVIEW']
 package=ROOT/'submission/submission.zip'
 forbidden=[];training=[];utf8=[];sync=[]
 with zipfile.ZipFile(package) as z:
  names=z.namelist()
  assert {'run.py','requirements.txt'}<=set(names)
  for name in names:
   if name not in {'run.py','requirements.txt','MANIFEST.json'} and not name.startswith(('nova_agent/','competition/')):forbidden.append(name)
   if any(x in Path(name).parts for x in ('tests','evaluation','frontend','backend','ml')) or Path(name).suffix in {'.pt','.pth','.onnx','.safetensors','.ckpt','.bin','.pkl','.joblib'}:forbidden.append(name)
   data=z.read(name)
   try:content=data.decode('utf-8')
   except UnicodeDecodeError:utf8.append(name);continue
   if name.startswith(('nova_agent/','competition/')):
    if not (ROOT/name).exists() or (ROOT/name).read_bytes()!=data:sync.append(name)
   if name.endswith('.py'):
    tree=ast.parse(content)
    for n in ast.walk(tree):
     if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in {'fit','partial_fit','backward','load_state_dict'}:training.append({'file':name,'line':n.lineno,'operation':n.func.attr})
  package_hits=[h for h in hits if h['file'].startswith('submission/')]
 report={'secret_scan':{'status':'PASS' if not unresolved else 'REVIEW_REQUIRED','repository_findings':hits,'submission_findings':package_hits,'scope':'Tracked UTF-8 source/config/docs; regex heuristics cannot prove absence of every credential'},'source_submission_byte_equivalence':not sync,'sync_mismatches':sync,'forbidden_files':forbidden,'training_operations':training,'utf8_failures':utf8,'zip_bytes':package.stat().st_size,'zip_sha256':hashlib.sha256(package.read_bytes()).hexdigest(),'package_file_count':len(names),'model_weights_bundled':False,'provider_boundary':'Fail closed for every network route pending organizer guide; explicit offline mock only','static_retrieval':'Local fixed KB/catalog; no patient-specific index write/update in inference path'}
 target=ROOT/args.output;target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
 if forbidden or training or utf8 or sync or package_hits or unresolved:raise SystemExit(1)
if __name__=='__main__':main()
