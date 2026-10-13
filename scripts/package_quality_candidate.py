#!/usr/bin/env python3
"""Build a reproducible, unscored quality candidate from the runtime sources.

This invokes the standard allowlisted builder, then replaces its historical
pre-guide manifest with accurate candidate metadata. It makes no official
score, live-model, or release-clearance claim.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'v[0-9]+', args.version):
        parser.error('version must be v followed by digits')
    subprocess.run([sys.executable, str(ROOT / 'scripts/build_nova_submission.py')], cwd=ROOT, check=True)
    with zipfile.ZipFile(ROOT / 'submission/submission.zip') as archive:
        payload = {name: archive.read(name) for name in archive.namelist() if name != 'MANIFEST.json'}
    manifest = {
        'artifact_status': 'UNSCORED_QUALITY_CANDIDATE',
        'release': args.version,
        'base_source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'source_identity': 'The per-file hashes identify the exact runtime, including uncommitted changes.',
        'official_submission_performed': False,
        'official_score_measured': False,
        'real_model_executed': False,
        'scope': 'Local engineering candidate; validation results are recorded separately.',
        'file_count': len(payload),
        'files': {name: hashlib.sha256(data).hexdigest() for name, data in sorted(payload.items())},
    }
    payload['MANIFEST.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
    output = ROOT / f'artifacts/releases/nova-{args.version}-submission.zip'
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(payload.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    print(json.dumps({'artifact': str(output.relative_to(ROOT)), 'bytes': output.stat().st_size,
                      'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
