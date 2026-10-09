"""Record a check atomically, preserving the command and actual exit status.

No evaluation policy changes. Child output is buffered until completion so a
workspace snapshot cannot replace an open log file partway through the run.
Runtime identity is tracked source bytes, not transient synchronization files.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]


def runtime_hashes():
    sys.path.insert(0, str(ROOT))
    from scripts.runtime_identity import tracked_runtime_hashes
    return tracked_runtime_hashes(ROOT)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    p.add_argument('command', nargs=argparse.REMAINDER)
    a = p.parse_args()
    command = a.command[1:] if a.command[:1] == ['--'] else a.command
    if not command:
        p.error('a command is required')
    before = runtime_hashes()
    started = datetime.now(timezone.utc).isoformat()
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(result.stdout)
    data = dict(command=command, exit_code=result.returncode, started_utc=started,
                finished_utc=datetime.now(timezone.utc).isoformat(), head=head,
                runtime_sha256=before, runtime_unchanged=before == runtime_hashes(),
                conditions={k:os.environ.get(k) for k in ('NOVA_LLM_PROVIDER', 'NOVA_COMPETITION_RETRIEVAL')},
                output_sha256=hashlib.sha256(out.read_bytes()).hexdigest())
    out.with_suffix('.execution.json').write_text(json.dumps(data, indent=2)+'\n')
    print(json.dumps(dict(output=str(out), exit_code=result.returncode,
                         runtime_unchanged=data['runtime_unchanged'])), flush=True)
    sys.exit(result.returncode or (0 if data['runtime_unchanged'] else 2))


if __name__ == '__main__':
    main()
