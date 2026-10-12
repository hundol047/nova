"""Credential-free helpers for local, human-run evidence; no environment reads."""
import hashlib
import json
import math
import re
from pathlib import Path

LABEL = 'HUMAN-RUN OFFICIAL PUBLIC SAMPLE'
SECRET_KEY = re.compile(r'authorization|password|secret|token|api.?key|dev.?key|session.?id|request.?id|headers', re.I)
SECRET_VALUE = re.compile(r'\bBearer\s+\S+|\b(?:sk-|sk-ant-|ghp_|github_pat_)[A-Za-z0-9_-]{12,}', re.I)


def redact(value, secret=''):
    if isinstance(value, dict):
        counts={'prompt_tokens','completion_tokens','total_tokens','cached_tokens','reasoning_tokens','max_tokens',
                'input_tokens','output_tokens','prompt_tokens_details','completion_tokens_details',
                'latency_tokens','tokens','mean_reported_total_tokens_per_call','token_usage_missing_calls'}
        return {str(k): '[REDACTED]' if SECRET_KEY.search(str(k)) and str(k).lower() not in counts
                else redact(v, secret) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, secret) for v in value]
    if isinstance(value, str):
        return SECRET_VALUE.sub('[REDACTED]', value.replace(secret, '[REDACTED]') if secret else value)
    return value


def safe_files(root):
    root = Path(root).resolve()
    for p in sorted(root.glob('*.json')):
        if p.is_symlink() or p.stat().st_size > 25_000_000:
            raise ValueError('Result symlink or oversized JSON rejected')
        yield p, json.loads(p.read_text(encoding='utf-8'))


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def file_sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def distribution(values):
    values = sorted(float(v) for v in values if isinstance(v, (float, int)) and math.isfinite(v) and v >= 0)
    if not values:
        return {'n': 0, 'mean': None, 'median': None, 'p95': None, 'max': None}
    n = len(values)
    return {'n': n, 'mean': sum(values)/n, 'median': (values[(n-1)//2]+values[n//2])/2,
            'p95': values[max(0, math.ceil(n*.95)-1)], 'max': values[-1]}
