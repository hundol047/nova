#!/usr/bin/env python3
"""N.O.V.A. 2026 preliminary-round submission entrypoint (official SDK flow).

The organizer server runs `python run.py` once per case in a fresh, offline, read-only container:
    run_agent(prepare, consult): Client() -> prepare() -> client.ready() -> consult(client, state) -> client.diagnose()
nova_sdk.py next to this file is the organizer SDK, vendored verbatim. The encounter logic lives in
competition/nova_sdk_adapter.py (deterministic clinical engine + the official gpt-oss-20b Doctor via client.chat).
"""
import os
import sys
from pathlib import Path

# The packages (nova_agent/, competition/) and nova_sdk.py sit next to this file; do not rely on the launcher's cwd or
# on `python -I` keeping the script directory on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
# Engine configuration for the official encounter (set before any nova_agent import reads it).
os.environ.setdefault("NOVA_COMPETITION_RETRIEVAL", "1")
os.environ.setdefault("NOVA_PRELIMINARY_RULES", "1")
os.environ.setdefault("NOVA_LLM_PROVIDER", "mock")  # engine reasons deterministically; Doctor calls go via client.chat
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True  # the root filesystem is read-only

from nova_sdk import run_agent  # noqa: E402

from competition.nova_sdk_adapter import consult, prepare  # noqa: E402

if __name__ == "__main__":
    run_agent(prepare, consult)
