"""The competition submission package must never include the browser development/demo workspace
(web/), its dependencies, or any other non-competition surface. scripts/build_nova_submission.py
only ever _copy_package()s nova_agent/ and competition/ -- this test asserts that stays true by
construction, not just by convention."""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_build_script_never_references_the_web_workspace():
    build_script = (_REPO_ROOT / "scripts" / "build_nova_submission.py").read_text(encoding="utf-8")
    assert not re.search(r"\bweb\b", build_script, re.IGNORECASE), (
        "scripts/build_nova_submission.py must never reference the web/ workspace directory"
    )


def test_submission_requirements_never_include_streamlit_or_web_deps():
    req = (_REPO_ROOT / "submission" / "requirements.txt")
    if not req.exists():
        return  # not yet built in this environment -- nothing to assert
    # Only actual dependency lines matter here -- the file's own comments explain (in prose) which
    # packages are deliberately NOT required, which would otherwise false-positive a naive
    # whole-file substring search.
    dependency_lines = [line for line in req.read_text(encoding="utf-8").splitlines()
                         if line.strip() and not line.strip().startswith("#")]
    installed = "\n".join(dependency_lines).lower()
    for forbidden in ("streamlit", "fastapi", "uvicorn", "psycopg", "redis"):
        assert forbidden not in installed, f"submission/requirements.txt must never pull in {forbidden!r}"


def test_submission_directory_never_contains_a_web_subdirectory():
    submission_dir = _REPO_ROOT / "submission"
    if not submission_dir.exists():
        return  # nothing to assert if the submission/ build artifact isn't present
    assert not (submission_dir / "web").exists(), "submission/ must never contain a web/ subdirectory"
