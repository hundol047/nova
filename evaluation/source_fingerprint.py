"""Fingerprint code/input knowledge, excluding reports and accumulated evaluation archives."""
import hashlib
from pathlib import Path


def source_sha256(root=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    for directory in ('nova_agent', 'evaluation'):
        for path in sorted((root / directory).rglob('*')):
            if not path.is_file():
                continue
            included = path.suffix == '.py' or (directory == 'nova_agent' and path.suffix in {'.json', '.txt'})
            if included:
                digest.update(str(path.relative_to(root)).encode())
                digest.update(path.read_bytes())
    return digest.hexdigest()
