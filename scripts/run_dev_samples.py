#!/usr/bin/env python3
"""Run THIS submission's agent on the organizer's server-backed public samples with a development key.

The code runs on your machine; the virtual patient, the examiner and the Doctor model (gpt-oss-20b) are the organizer's.
Requires network access to the organizer API and the development key in the environment (never on the command line,
never printed, never written to disk):

    export NOVA_API_BASE=https://<organizer API origin from the participant guide>
    export NOVA_DEV_KEY=...            # your personal development key
    python scripts/run_dev_samples.py C01 C03 C10 --output artifacts/official_samples/devkey

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
sys.path.insert(0, str(ROOT / "submission"))
sys.path.insert(0, str(ROOT))
os.environ.setdefault("NOVA_COMPETITION_RETRIEVAL", "1")
os.environ.setdefault("NOVA_PRELIMINARY_RULES", "1")
os.environ.setdefault("NOVA_LLM_PROVIDER", "mock")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cases", nargs="+")
    parser.add_argument("--output", default="artifacts/official_samples/devkey")
    args = parser.parse_args()
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
        (out / f"{case}.json").write_text(json.dumps(row, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({k: row[k] for k in ("case", "status", "seconds", "exam_rejections")} | row["doctor"],
                         ensure_ascii=False))


if __name__ == "__main__":
    main()
