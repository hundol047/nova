#!/usr/bin/env python3
"""Official submission entrypoint: blocked until the organizer contract is integrated.

No environment variable or CLI argument enables a mock or arbitrary network provider.
For offline local testing only: python -m competition.local_runner.
"""
import sys
from pathlib import Path

# The packages (nova_agent/, competition/) sit next to this file. Do not rely on the launcher putting the
# script directory on sys.path (it does not under `python -I`, nor when started from another cwd).
sys.path.insert(0, str(Path(__file__).resolve().parent))


def main():
    from competition.provider_lock import enforce_submission_provider
    try:
        enforce_submission_provider()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
