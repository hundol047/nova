"""Lazy, optional torch loader.

torch is an OPTIONAL dependency (requirements-learning.txt). Importing the learning package must
never fail because torch is absent. Any code path that genuinely needs torch calls require_torch(),
which raises a clear, actionable error if it is missing — rather than an opaque ImportError deep in
a model file.
"""

from __future__ import annotations

from typing import Any


def torch_available() -> bool:
    try:
        import torch  # noqa: F401
        return True
    except Exception:
        return False


def require_torch() -> Any:
    try:
        import torch
        return torch
    except Exception as exc:  # pragma: no cover - exercised only when torch is absent
        raise RuntimeError(
            "This operation requires PyTorch, which is an OPTIONAL learning-only dependency. "
            "Install it with `pip install -r backend/requirements-learning.txt` (or `pip install "
            "torch`). torch is intentionally NOT part of the competition submission or the core "
            "runtime."
        ) from exc
