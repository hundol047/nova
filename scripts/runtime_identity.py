"""Runtime identity is tracked source, excluding transient workspace copies.

This changes verification bookkeeping only, never a case, response or scorer.
Final release recording additionally checks every byte against a commit and ZIP.
"""
import hashlib
from pathlib import Path
import subprocess


def tracked_runtime_hashes(checkout):
    root = Path(checkout)
    names = subprocess.check_output(['git', 'ls-files', 'nova_agent', 'competition'], cwd=root, text=True).splitlines()
    return {name:hashlib.sha256((root/name).read_bytes()).hexdigest()
            for name in sorted(names) if Path(name).suffix in {'.py', '.json', '.md'}}
