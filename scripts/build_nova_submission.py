#!/usr/bin/env python3
"""Regenerates submission/nova_agent/ and submission/competition/ from the real nova_agent/ and
competition/ packages at the repository root (the single source of truth) -- spec section 16/24I.

submission/run.py and submission/requirements.txt are hand-authored and NOT touched by this
script. Run this after any change to nova_agent/ or competition/:

    python scripts/build_nova_submission.py

Deliberately excludes everything NOT needed to run the agent (spec section 16): no frontend/, no
3D anatomy assets, no Jetson-specific scripts, no dev docs, no pytest, no large research/ assets --
only the two packages the Doctor Agent actually imports at runtime.
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUBMISSION = ROOT / "submission"
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")


def _copy_package(name: str) -> None:
    src = ROOT / name
    dst = SUBMISSION / name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=IGNORE)
    print(f"copied {src} -> {dst}")


def main() -> None:
    SUBMISSION.mkdir(exist_ok=True)
    _copy_package("nova_agent")
    _copy_package("competition")
    for required in ("run.py", "requirements.txt"):
        if not (SUBMISSION / required).exists():
            raise SystemExit(f"submission/{required} is missing -- it is hand-authored and must "
                              "exist before running this script.")
    print("submission/ is ready.")


if __name__ == "__main__":
    main()
