"""The competition submission package must never include the hospital/research learning/ package
(training, continual-learning, embedding-index-building infrastructure) or any of its heavier
dependencies -- competition retrieval runs entirely on nova_agent.retrieval_pipeline +
nova_agent.open_world, which are dependency-light by construction (see those modules' docstrings).
scripts/build_nova_submission.py only ever copies nova_agent/ and competition/; this test asserts
that stays true by construction, not just by convention."""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_build_script_never_references_the_learning_package():
    build_script = (_REPO_ROOT / "scripts" / "build_nova_submission.py").read_text(encoding="utf-8")
    assert not re.search(r"\blearning\b", build_script), (
        "scripts/build_nova_submission.py must never reference the learning/ package"
    )


def test_submission_directory_never_contains_a_learning_subdirectory():
    submission_dir = _REPO_ROOT / "submission"
    if not submission_dir.exists():
        return  # nothing to assert if the submission/ build artifact isn't present
    assert not (submission_dir / "learning").exists(), "submission/ must never contain a learning/ subdirectory"


def test_submission_requirements_never_pull_in_torch_or_embedding_deps():
    req = _REPO_ROOT / "submission" / "requirements.txt"
    if not req.exists():
        return
    dependency_lines = [line for line in req.read_text(encoding="utf-8").splitlines()
                         if line.strip() and not line.strip().startswith("#")]
    installed = "\n".join(dependency_lines).lower()
    for forbidden in ("torch", "clinicalbert", "sentence-transformers", "transformers"):
        assert forbidden not in installed, f"submission/requirements.txt must never pull in {forbidden!r}"
