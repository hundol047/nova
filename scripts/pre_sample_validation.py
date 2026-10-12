#!/usr/bin/env python3
"""Local preparation only. Never uploads, calls participant APIs or reads keys."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.audit_official_package import audit
from scripts.validate_runtime_provenance import validate

PUBLIC_SDK_SHA256='fdd65302e82791ed862c22fe5a014ef443ab331d8986ec7c72b3923add6bc871'


def preflight(output_dir, wheels=None, corpus_root=None):
    output=Path(output_dir).resolve();output.mkdir(parents=True,exist_ok=True)
    # Allowlist process environment; do not copy or inspect participant variables.
    env={k:os.environ[k] for k in ('PATH','HTTPS_PROXY','HTTP_PROXY','NO_PROXY') if k in os.environ}
    env.update(NOVA_LLM_PROVIDER='mock',NOVA_COMPETITION_RETRIEVAL='1',PYTHONDONTWRITEBYTECODE='1')
    ptr=json.loads((ROOT/'artifacts/verification/CURRENT_RELEASE.json').read_text(encoding='utf-8'))
    env['SOURCE_DATE_EPOCH']=subprocess.check_output(['git','show','-s','--format=%ct',ptr['verified_runtime_sha']],cwd=ROOT,text=True).strip()
    checks={};commands=[]
    def run(name,args):
        result=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True)
        (output/(name+'.log')).write_text(result.stdout+result.stderr)
        checks[name]=result.returncode==0;commands.append({'name':name,'exit_code':result.returncode})
        return result.returncode==0
    run('fresh_build',[sys.executable,'scripts/build_nova_submission.py'])
    package=audit(ROOT/'submission/submission.zip');checks['package']=package['all_pass']
    checks['official_sdk_exact']=hashlib.sha256((ROOT/'submission/nova_sdk.py').read_bytes()).hexdigest()==PUBLIC_SDK_SHA256
    run('secret_sync_scan',[sys.executable,'scripts/audit_pre_guide_package.py','--output',str(output/'package_scan.json')])
    run('leakage_scan',[sys.executable,'scripts/check_eval_leakage.py'])
    run('fake_http_readonly',[sys.executable,'scripts/smoke_official_http.py','submission/submission.zip'])
    run('fresh_directory',[sys.executable,'scripts/smoke_fresh_package.py'])
    provenance=validate(ROOT);checks['provenance_inventory']=not provenance['errors']
    docker_available=shutil.which('docker') is not None
    with tempfile.TemporaryDirectory(prefix='nova-resource-preflight-') as temp:
        context=Path(temp);wheel_dir=context/'wheels';wheel_dir.mkdir()
        if wheels:
            for p in Path(wheels).glob('*.whl'):shutil.copyfile(p,wheel_dir/p.name)
        else:
            run('binary_wheel_download',[sys.executable,'-m','pip','download','--only-binary=:all:','--python-version','3.12',
                '--implementation','cp','--abi','cp312','--platform','manylinux_2_17_x86_64',
                '--index-url','https://pypi.org/simple','--dest',str(wheel_dir),'-r','submission/requirements.txt'])
        checks['wheels_present']=len(list(wheel_dir.glob('*.whl')))==len(package['checks']['requirements'])
        if docker_available:
            env['DOCKER_CONFIG']=str(context/'docker-config')
            shutil.copyfile(ROOT/'submission/submission.zip',context/'submission.zip')
            shutil.copyfile(ROOT/'scripts/smoke_official_http.py',context/'smoke_official_http.py')
            shutil.copyfile(ROOT/'submission/requirements.txt',context/'requirements.txt')
            (context/'Dockerfile').write_text('FROM python:3.12-slim\nCOPY wheels /wheels\nCOPY requirements.txt /audit/requirements.txt\nRUN pip install --no-index --only-binary=:all: --find-links=/wheels -r /audit/requirements.txt\nCOPY submission.zip smoke_official_http.py /audit/\nWORKDIR /audit\nCMD ["python","-B","smoke_official_http.py","submission.zip"]\n')
            built=run('docker_offline_install',['docker','build','--network','none','-t','nova-human-validation-local',str(context)])
            if built:run('docker_offline_readonly_2cpu_8gb',['docker','run','--rm','--network','none','--read-only','--cpus','2','--memory','8g',
                '--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,size=256m','nova-human-validation-local'])
            if built and corpus_root:
                code="import sys,zipfile,json,resource; zipfile.ZipFile('/audit/submission.zip').extractall('/tmp/pkg'); sys.path.insert(0,'/tmp/pkg'); from competition.nova_sdk_adapter import prepare; s=prepare(); print(json.dumps({'guidelines':s['guidelines'].stats(),'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})); assert len(s['guidelines'].docs)==15904"
                run('docker_full_corpus_prepare',['docker','run','--rm','--network','none','--read-only','--cpus','2','--memory','8g',
                    '--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,size=256m',
                    '-v',str(Path(corpus_root).resolve())+':/opt/nova/guidelines:ro','-e','NOVA_GUIDELINES_DIR=/opt/nova/guidelines',
                    'nova-human-validation-local','python','-B','-c',code])
        else:
            checks['docker_offline_readonly_2cpu_8gb']=False
    technical=all(checks.values())
    rights=provenance['permission_status']!='BLOCKED'
    result={'READY_FOR_HUMAN_SAMPLE_VALIDATION':'YES' if technical and rights else 'NO',
            'LOCAL_TECHNICAL_CHECKS':'PASS' if technical else 'FAIL','checks':checks,'commands':commands,'package':package,
            'provenance_permission_status':provenance['permission_status'],
            'blockers':(['Unresolved source/license rights; no automatic clearance'] if not rights else [])+
                       ([] if technical else ['Local technical checks incomplete/failed']),
            'real_gpt_oss':'NOT EXECUTED BY CODEX','participant_key_samples':'NOT EXECUTED BY CODEX',
            'sample_validation_upload':'NOT EXECUTED BY CODEX'}
    (output/'pre_sample_validation.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',required=True);p.add_argument('--wheels');p.add_argument('--corpus-root');a=p.parse_args()
    result=preflight(a.output_dir,a.wheels,a.corpus_root);print(json.dumps(result,indent=2))
    if result['READY_FOR_HUMAN_SAMPLE_VALIDATION']=='NO':raise SystemExit(2)

if __name__=='__main__':main()
