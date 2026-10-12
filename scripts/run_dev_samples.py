#!/usr/bin/env python3
"""HUMAN-RUN ONLY: run this agent on server-backed public samples on your own computer.

DO NOT RUN FROM CODEX / CLAUDE CODE / CURSOR. Participant development keys
and credits must not be connected to coding tools. This program requires an
explicit --human-run acknowledgement and refuses known coding-agent environments
BEFORE accessing the development-key variable.

The code runs on your machine; the virtual patient, the examiner and the Doctor model (gpt-oss-20b) are the organizer's.
Requires network access to the organizer API and the development key in the environment (never on the command line,
never printed, never written to disk):

    export NOVA_API_BASE=https://<organizer API origin from the participant guide>
    export NOVA_DEV_KEY=...            # your personal development key
    python scripts/run_dev_samples.py --human-run C01 C03 C10 --output ~/nova-sample-results

Each case writes <output>/<case>.json: completion status, model string(s) returned, Doctor calls and tokens, turns,
EXAM refusals, wall time, the submitted record and diagnosis, and the session view the server returns afterwards
(sample sessions may include a reference score). The key is read from NOVA_DEV_KEY only.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require_human_run(acknowledged, environ):
    if not acknowledged or any(k.startswith(("CODEX_", "CLAUDE_CODE_", "CURSOR_")) or k in {"CLAUDECODE", "GITHUB_ACTIONS"} for k in environ):
        raise SystemExit("HUMAN-RUN ONLY. Execute on your own computer, outside Codex/Claude Code/Cursor; no key was read.")


def redact(value, secret):
    if isinstance(value, dict):
        return {k: "[REDACTED]" if k.lower() in {"token", "run_token", "dev_key", "api_key", "authorization", "access_token",
                                                            "nova_run_token", "nova_dev_key", "session_token", "development_key"}
                else redact(v, secret) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, secret) for v in value]
    return value.replace(secret, "[REDACTED]") if isinstance(value, str) and secret else value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cases", nargs="+")
    parser.add_argument("--human-run", action="store_true", help="Human execution on your own computer only")
    parser.add_argument("--output", default=str(Path.home() / "nova-sample-results"))
    args = parser.parse_args()
    require_human_run(args.human_run, os.environ)
    sys.path.insert(0, str(ROOT / "submission"))
    sys.path.insert(0, str(ROOT))
    os.environ.setdefault("NOVA_COMPETITION_RETRIEVAL", "1")
    os.environ.setdefault("NOVA_PRELIMINARY_RULES", "1")
    os.environ.setdefault("NOVA_LLM_PROVIDER", "mock")
    key = os.environ.get("NOVA_DEV_KEY")
    base = os.environ.get("NOVA_API_BASE")
    if not key or not base:
        raise SystemExit("Set NOVA_API_BASE and NOVA_DEV_KEY in the environment (the key is never passed as an argument).")
    import nova_sdk
    from competition.nova_sdk_adapter import OfficialEncounter, prepare
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    prepared = prepare()
    for case in args.cases:
        client = nova_sdk.Client(api_base=base, token=key, sample=True)
        client.create_sample(case)
        started = time.time()
        encounter = OfficialEncounter(client, prepared)
        row = {"case": case, "sdk_version": nova_sdk.__version__}
        try:
            row["diagnose_response"] = encounter.run()
            row["status"] = "completed"
        except nova_sdk.NovaError as exc:
            row["status"] = f"error:{exc.code}"
        row["seconds"] = round(time.time() - started, 1)
        row["doctor"] = encounter.stats.as_dict()
        row["turns"] = [{"kind": t.kind, "text": t.text, "reply": t.reply, "rejected": t.rejected, "turn": t.turn}
                        for t in encounter.turns]
        row["exam_rejections"] = encounter.exam_rejections
        try:
            row["session_after"] = client.session()  # sample sessions report events / record / score fields
        except nova_sdk.NovaError as exc:
            row["session_after"] = {"error": exc.code}
        (out / f"{case}.json").write_text(json.dumps(redact(row, key), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(json.dumps(redact({k: row[k] for k in ("case", "status", "seconds", "exam_rejections")} | row["doctor"], key),
                         ensure_ascii=False))


if __name__ == "__main__":
    main()
