"""Pure harness support; no credential or environment access at import time."""
import hashlib
import json
import time


def capture_response(operation, response):
    """Allowlist returned clinical/usage fields; omit headers, prompts and reasoning traces."""
    if not isinstance(response,dict):return None
    if operation=='chat':
        result={k:response[k] for k in ('model','usage','revision','model_revision','model_sha') if k in response}
        choices=response.get('choices');result['choices']=[]
        for choice in choices[:8] if isinstance(choices,list) else []:
            if not isinstance(choice,dict):continue
            message=choice.get('message') or {}
            result['choices'].append({'finish_reason':choice.get('finish_reason'),
                                      'message':{'content':message.get('content') if isinstance(message,dict) else None}})
        return result
    fields={'session':('initial','turn','turns_remaining','deadline','status','available_actions'),
            'say':('content','effective_content','turn','turns_remaining','status'),
            'exam':('result','effective_content','turn','turns_remaining','status'),
            'diagnose':('status','record_digest','turn','turns_remaining','score_status')}
    return {k:response[k] for k in fields.get(operation,()) if k in response}


def verify_runtime(root, candidate=None):
    if candidate is not None:
        if candidate != 'v42':raise SystemExit('Unknown candidate')
        import zipfile
        record = json.loads((root/'artifacts/releases/nova-v42-publication.json').read_text(encoding='utf-8'))
        archive = root/'artifacts/releases/nova-v42-submission.zip'
        if hashlib.sha256(archive.read_bytes()).hexdigest() != record['sha256']:
            raise SystemExit('Candidate archive hash mismatch')
        with zipfile.ZipFile(archive) as z:
            names=z.namelist()
            if len(names)!=len(set(names)) or any(n.startswith('/') or '\\' in n or '..' in n.split('/') for n in names):
                raise SystemExit('Unsafe candidate archive')
            actual={p.relative_to(root/'submission').as_posix() for p in (root/'submission').rglob('*')
                    if p.is_file() and '__pycache__' not in p.parts and p.name!='submission.zip' and p.suffix!='.pyc'}
            if actual != set(names):raise SystemExit('Candidate staging members differ; extract the published ZIP into submission.')
            for name in names:
                p=root/'submission'/name
                if p.is_symlink() or p.read_bytes()!=z.read(name):raise SystemExit('Candidate staging mismatch: '+name)
                if name.startswith(('competition/','nova_agent/')) and name.endswith('.py'):
                    if (root/name).read_bytes()!=z.read(name):raise SystemExit('Candidate source mismatch: '+name)
        return {'candidate':candidate,'candidate_zip_sha256':record['sha256'],
                'validation_scope':record['scope'],
                'sdk_sha256':hashlib.sha256((root/'submission/nova_sdk.py').read_bytes()).hexdigest()}
    ptr = json.loads((root/'artifacts/verification/CURRENT_RELEASE.json').read_text(encoding='utf-8'))
    record = json.loads((root/ptr['current_verification_artifact']).read_text(encoding='utf-8'))
    for name, expected in record['runtime_sha256'].items():
        packaged = root/'submission'/name.removeprefix('submission/')
        if hashlib.sha256(packaged.read_bytes()).hexdigest() != expected:
            raise SystemExit('Submission differs from verified runtime: '+name)
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=expected:
            raise SystemExit('Source differs from verified runtime: '+name)
    members=record['submission']['member_sha256']
    actual={p.relative_to(root/'submission').as_posix() for p in (root/'submission').rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.name!='submission.zip' and p.suffix!='.pyc'}
    if actual!=set(members):raise SystemExit('Unexpected/missing staging files; run pre_sample_validation first.')
    for name,h in members.items():
        p=root/'submission'/name
        if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=h:
            raise SystemExit('Exact archive member mismatch: '+name)
    return {'verified_runtime_sha': record['verified_runtime_sha'],
            'sdk_sha256': hashlib.sha256((root/'submission/nova_sdk.py').read_bytes()).hexdigest()}


class ObservedClient:
    """GET probes around natural requests recover server turns omitted by SDK errors.

    No deliberately invalid actions; no header/token access. Probe overhead is
    recorded separately and GET timeouts are bounded to two seconds each.
    """
    def __init__(self, client): self.client, self.last_observation = client, {}
    @property
    def timeout(self): return self.client.timeout
    @timeout.setter
    def timeout(self, value): self.client.timeout = value

    def _probe(self):
        started, old = time.monotonic(), self.client.timeout
        try:
            self.client.timeout = min(old, 2.0)
            state = self.client.session()
            return {k: state.get(k) for k in ('turn', 'turns_remaining', 'status')}, time.monotonic()-started
        except Exception:
            return {}, time.monotonic()-started
        finally:
            self.client.timeout = old

    def _run(self, name, fn, *args, **kw):
        before, overhead = self._probe()
        started, result = time.monotonic(), None
        try:
            result = fn(*args, **kw)
            return result
        finally:
            elapsed = time.monotonic()-started
            after = result if isinstance(result, dict) and ('turns_remaining' in result or name=='diagnose' and 'turn' in result) else None
            if after is None:
                after, more = self._probe(); overhead += more
            self.last_observation = {'operation': name, 'server_before': before,
                                     'server_after': {k: after.get(k) for k in ('turn', 'turns_remaining', 'status')},
                                     'api_latency_seconds': elapsed, 'probe_latency_seconds': overhead}

    def session(self): return self.client.session()
    def chat(self, *a, **k): return self._run('chat', self.client.chat, *a, **k)
    def say(self, *a, **k): return self._run('say', self.client.say, *a, **k)
    def exam(self, *a, **k): return self._run('exam', self.client.exam, *a, **k)
    def diagnose(self, *a, **k): return self._run('diagnose', self.client.diagnose, *a, **k)


def resolve_cases(labels, published, mappings):
    available = {str(row['case_id']) for row in published}
    mapping = dict(pair.split('=', 1) for pair in mappings)
    resolved = [(label, mapping.get(label, label)) for label in labels]
    if any(case_id not in available for _, case_id in resolved):
        raise SystemExit('Use --list, then --case-id C01=<published-case-id> for each alias. No session was created.')
    return resolved
