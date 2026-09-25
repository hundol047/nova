"""Guard: the learning subsystem must NEVER import from evaluation/ (blind/held-out sets).

If training could import evaluation.blind_cases_* / held-out data, a model could be trained on the
very cases used to judge it — invalidating the blind evaluation. This is a STATIC source scan of the
learning/ package (dependency-free): it fails if any learning module references the evaluation
package. It also confirms the competition submission does not bundle the learning package or torch.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEARNING = ROOT / "learning"
SUBMISSION = ROOT / "submission"

_EVAL_IMPORT = re.compile(r"^\s*(from|import)\s+evaluation\b", re.MULTILINE)


def test_learning_never_imports_evaluation():
    offenders = []
    for py in LEARNING.rglob("*.py"):
        text = py.read_text(encoding="utf-8", errors="ignore")
        if _EVAL_IMPORT.search(text):
            offenders.append(str(py.relative_to(ROOT)))
    assert not offenders, f"learning/ must not import evaluation/: {offenders}"


def test_submission_excludes_learning_and_torch():
    # The learning package must not be copied into the submission.
    assert not (SUBMISSION / "learning").exists(), "submission/ must not contain the learning package"
    # No submission file may import torch or the learning package.
    torch_import = re.compile(r"^\s*(from|import)\s+(torch|learning)\b", re.MULTILINE)
    offenders = []
    for py in SUBMISSION.rglob("*.py"):
        text = py.read_text(encoding="utf-8", errors="ignore")
        if torch_import.search(text):
            offenders.append(str(py.relative_to(ROOT)))
    assert not offenders, f"submission/ must not import torch or learning: {offenders}"
    # requirements must not declare torch.
    req = (SUBMISSION / "requirements.txt").read_text(encoding="utf-8")
    assert "torch" not in req.lower(), "submission/requirements.txt must not depend on torch"


def test_nova_agent_does_not_import_learning_or_torch():
    """The core reasoning package must not depend on the optional learning subsystem or torch."""
    bad = re.compile(r"^\s*(from|import)\s+(torch|learning)\b", re.MULTILINE)
    offenders = []
    for py in (ROOT / "nova_agent").rglob("*.py"):
        text = py.read_text(encoding="utf-8", errors="ignore")
        if bad.search(text):
            offenders.append(str(py.relative_to(ROOT)))
    assert not offenders, f"nova_agent/ must not import torch or learning: {offenders}"
