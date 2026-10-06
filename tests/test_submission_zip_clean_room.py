"""The submission ZIP, built from the checked-in runtime and unpacked into an EMPTY temp directory, is a
self-contained package that obeys the organizers' packaging rules (see scripts/validate_submission_zip.py)."""

import hashlib
import subprocess
import sys
from pathlib import Path

from scripts.validate_submission_zip import validate

ROOT = Path(__file__).resolve().parents[1]


def _build():
    subprocess.run([sys.executable, str(ROOT / "scripts/build_nova_submission.py")], cwd=ROOT, check=True,
                   capture_output=True, text=True, timeout=300)
    return ROOT / "submission/submission.zip"


def test_clean_room_zip_passes_every_packaging_check():
    report = validate(_build(), sys.executable)
    failed = [name for name, passed in report["checks"].items() if not passed]
    assert not failed, (failed, report.get("encounter_error"), report.get("run_py_gate_message"))
    assert report["bytes"] < 50_000_000


def test_build_is_reproducible_byte_for_byte():
    first = hashlib.sha256(_build().read_bytes()).hexdigest()
    second = hashlib.sha256(_build().read_bytes()).hexdigest()
    assert first == second


def test_run_py_does_not_depend_on_the_launchers_sys_path():
    text = (ROOT / "submission/run.py").read_text(encoding="utf-8")
    assert "sys.path.insert(0, str(Path(__file__).resolve().parent))" in text
