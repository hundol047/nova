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


# Blind / held-out / generalization data-file identifiers the learning pipeline must NEVER read as
# TRAINING input (reading them would train a model on the very cases used to judge it). We scan for
# CODE references (imports, path/glob literals), skipping comments and docstrings so prose that
# merely describes this rule doesn't trip it.
_EVAL_DATA_TOKENS = ("blind_cases", "blind_benchmark", "generalization_cases", "held_out_cases")


def _strip_comments_and_docstrings(source: str) -> str:
    """Return source with comments and string literals blanked out (best-effort via tokenize) so we
    match only real code references, not prose in docstrings/comments."""
    import io
    import tokenize

    out_lines = source.splitlines()
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError):
        return source
    for tok in toks:
        if tok.type in (tokenize.COMMENT, tokenize.STRING):
            (srow, scol), (erow, ecol) = tok.start, tok.end
            for r in range(srow, erow + 1):
                line = out_lines[r - 1]
                a = scol if r == srow else 0
                b = ecol if r == erow else len(line)
                out_lines[r - 1] = line[:a] + (" " * (b - a)) + line[b:]
    return "\n".join(out_lines)


def test_learning_never_references_eval_data_sources():
    """Beyond imports: no learning/ module may reference blind/held-out/generalization data files
    in CODE (docstrings/comments describing the rule are fine)."""
    offenders = []
    for py in LEARNING.rglob("*.py"):
        code = _strip_comments_and_docstrings(py.read_text(encoding="utf-8", errors="ignore"))
        low = code.lower()
        for tok in _EVAL_DATA_TOKENS:
            if tok in low:
                offenders.append(f"{py.relative_to(ROOT)}: references {tok!r} in code")
    assert not offenders, ("learning/ must not reference blind/held-out/generalization data as a "
                           "source:\n" + "\n".join(offenders))
