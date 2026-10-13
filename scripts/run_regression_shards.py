"""Run each test module once in isolated pytest subprocesses, then merge JUnit.

Optional prior durations balance scheduling only; no tests are selected away.
Release-binding and rights artifacts have a separate post-record invocation.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
DEFERRED={'test_current_pre_guide_release.py','test_rights_and_review_evidence.py'}
EXCLUSIVE={'test_safety_regression.py','test_submission_zip_clean_room.py'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--python',default=sys.executable);p.add_argument('--output',required=True)
    p.add_argument('--timings');p.add_argument('--workers',type=int,default=3);a=p.parse_args()
    out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True)
    files=sorted(p for p in (ROOT/'tests').rglob('test_*.py') if p.name not in DEFERRED)
    estimates={str(p.relative_to(ROOT)):1.0 for p in files}
    if a.timings:
        durations={}
        for t in ET.parse(a.timings).getroot().iter('testcase'):
            key='/'.join(t.get('classname','').split('.')[:2])+'.py'
            durations[key]=durations.get(key,0)+float(t.get('time','0'))
        estimates.update({k:v for k,v in durations.items() if k in estimates})
    groups=[[] for _ in range(a.workers)];totals=[0.0]*a.workers
    exclusive=[n for n in estimates if Path(n).name in EXCLUSIVE]
    for name in sorted((n for n in estimates if n not in exclusive),key=estimates.get,reverse=True):
        i=min(range(a.workers),key=totals.__getitem__);groups[i].append(name);totals[i]+=estimates[name]
    if exclusive:groups.append(exclusive)
    assert sorted(n for g in groups for n in g)==sorted(estimates)
    (out/'modules.json').write_text(json.dumps({'deferred':sorted(DEFERRED),'groups':groups},indent=2)+'\n')
    def run(i):
        with (out/f'part-{i}.log').open('w') as log:
            return subprocess.call([a.python,'-m','pytest','-q',*groups[i],
                                    '--junitxml='+str(out/f'part-{i}.xml')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    with ThreadPoolExecutor(max_workers=a.workers) as pool:codes=list(pool.map(run,range(a.workers)))
    # Run mutation tests after all read-only shards. Use separate checkouts
    # when invoking two interpreters concurrently.
    if exclusive:codes.append(run(a.workers))
    combined=ET.Element('testsuites');seen=set()
    for i in range(len(groups)):
        for suite in ET.parse(out/f'part-{i}.xml').getroot().iter('testsuite'):
            for case in suite.iter('testcase'):
                identity=(case.get('classname'),case.get('name'))
                assert identity not in seen,identity
                seen.add(identity)
            combined.append(suite)
    ET.ElementTree(combined).write(out/'core.xml',encoding='utf-8',xml_declaration=True)
    print(json.dumps({'modules':len(files),'tests':len(seen),'exit_codes':codes}))
    raise SystemExit(max(codes))


if __name__=='__main__':main()
