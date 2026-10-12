#!/usr/bin/env python3
"""Audit a submission ZIP against the official N.O.V.A. package rules (organizer material / devkit, 2026-10-11).

  * ZIP <= 50,000,000 bytes, uncompressed <= 500 MB, <= 5,000 files
  * run.py, requirements.txt and nova_sdk.py at the ZIP root
  * no symlinks, encrypted entries, absolute paths, '..' components or duplicate paths
  * requirements.txt: exact `package==version` pins only (PyPI wheels; no URLs, VCS, local paths or options)
  * no secret-shaped strings, no organizer guideline corpus, no model weights

    python scripts/audit_official_package.py submission/submission.zip [--output report.json]
"""
import argparse
import hashlib
import json
import re
import stat
import sys
import zipfile
from pathlib import Path

ZIP_LIMIT = 50_000_000
UNCOMPRESSED_LIMIT = 500_000_000
FILE_LIMIT = 5_000
ROOT_FILES = ("run.py", "requirements.txt", "nova_sdk.py")
PIN = re.compile(r"^[A-Za-z0-9_.\-]+==[0-9][A-Za-z0-9.\-+]*$")
SECRET = re.compile(r"nova_[A-Za-z0-9]{30,}|nvr_[A-Za-z0-9]{16,}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|"
                    r"AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----")
# Organizer corpus markers: its 16 source folders (KR_*/US_*) and its catalog files. It is mounted read-only at
# /opt/nova/guidelines at runtime and must never be packaged.
CORPUS = re.compile(r"(^|/)(?:KR|US)_[A-Za-z\-]+/|(^|/)catalog\.(?:csv|xlsx)$|(^|/)opt/nova/")
WEIGHTS = re.compile(r"\.(pt|pth|bin|ckpt|safetensors|onnx|gguf|npy|npz|pkl|pickle|h5)$", re.I)


def audit(path: Path) -> dict:
    checks, problems = {}, []
    size = path.stat().st_size
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        files = [i for i in infos if not i.is_dir()]
        uncompressed = sum(i.file_size for i in files)
        checks["zip_bytes"] = size
        checks["uncompressed_bytes"] = uncompressed
        checks["files"] = len(files)
        if size > ZIP_LIMIT:
            problems.append("zip too large")
        if uncompressed > UNCOMPRESSED_LIMIT:
            problems.append("uncompressed too large")
        if len(files) > FILE_LIMIT:
            problems.append("too many files")
        for name in ROOT_FILES:
            checks[f"root:{name}"] = name in names
            if name not in names:
                problems.append(f"missing root {name}")
        if len(set(names)) != len(names):
            problems.append("duplicate paths")
        for info in infos:
            name = info.filename
            if name.startswith(("/", "\\")) or ".." in Path(name).parts or re.match(r"^[A-Za-z]:", name):
                problems.append(f"unsafe path {name}")
            if stat.S_ISLNK(info.external_attr >> 16):
                problems.append(f"symlink {name}")
            if info.flag_bits & 0x1:
                problems.append(f"encrypted {name}")
            if WEIGHTS.search(name) or CORPUS.search(name):
                problems.append(f"forbidden content {name}")
        secrets = []
        for info in files:
            if info.filename.endswith((".py", ".txt", ".json", ".md", ".csv", ".yaml", ".yml", ".cfg", ".toml")):
                text = z.read(info).decode("utf-8", errors="ignore")
                if SECRET.search(text):
                    secrets.append(info.filename)
                if info.filename.endswith((".py", ".txt", ".md", ".json")):
                    try:
                        z.read(info).decode("utf-8")
                    except UnicodeDecodeError:
                        problems.append(f"not UTF-8 {info.filename}")
        checks["secret_hits"] = secrets
        if secrets:
            problems.append("secret-shaped strings")
        requirements = z.read("requirements.txt").decode("utf-8") if "requirements.txt" in names else ""
        lines = [l.strip() for l in requirements.splitlines() if l.strip() and not l.strip().startswith("#")]
        bad = [l for l in lines if not PIN.match(l)]
        checks["requirements"] = lines
        if bad or not lines:
            problems.append(f"requirements not exact pins: {bad}")
    checks["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"zip": str(path), "checks": checks, "problems": problems, "all_pass": not problems}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("zip")
    p.add_argument("--output")
    a = p.parse_args()
    report = audit(Path(a.zip))
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if a.output:
        Path(a.output).write_text(text + "\n", encoding="utf-8")
    print(text)
    sys.exit(0 if report["all_pass"] else 1)


if __name__ == "__main__":
    main()
