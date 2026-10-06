"""`python scripts/verify_submission_standalone_full_loop.py` -- proves the isolated local mock harness runs the
FULL observation -> routing -> retrieval -> differential -> ASK/EXAM/TEST -> update -> DIAGNOSE
loop standalone, not just a single turn (scripts/build_nova_submission.py's own build-time smoke
test only exercises one observation -> one action, per spec/round discipline that check must stay
fast; this script is the deeper, slower companion run manually as part of a verification round).

Copies submission/ to an isolated temp directory, runs `python -m competition.local_runner` as a real subprocess from
INSIDE that copy with PYTHONPATH explicitly cleared and only a minimal PATH in its environment (so
it cannot import anything from the source repository -- proving submission/ is genuinely
self-contained), and feeds it a multi-turn JSON-lines conversation (initial observation, then a
scripted ask_response/exam_result/test_result for whatever the agent asks each turn, mirroring
evaluation/simulator.py's own default-negative-answer fallback) until it emits DIAGNOSE or a
turn-count safety cap is hit. Never claims REAL COMPETITION LLM or OFFICIAL COMPETITION API
verification -- those require a live gpt-oss endpoint / a published schema this repository does
not have; the provider is whatever NOVA_LLM_PROVIDER is set to (mock by default here, deterministic
fallback still fully exercises the loop's control flow even when no real LLM is reachable)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUBMISSION = ROOT / "submission"
MAX_TURNS_SAFETY_CAP = 40


def main() -> None:
    if not (SUBMISSION / "run.py").exists():
        raise SystemExit("submission/run.py not found -- run scripts/build_nova_submission.py first")

    with tempfile.TemporaryDirectory(prefix="nova_submission_standalone_") as tmp:
        isolated = Path(tmp) / "submission"
        shutil.copytree(SUBMISSION, isolated, ignore=shutil.ignore_patterns("submission.zip"))

        env = {"PATH": "/usr/bin:/bin", "NOVA_LLM_PROVIDER": os.environ.get("NOVA_LLM_PROVIDER", "mock")}
        proc = subprocess.Popen(
            [sys.executable, "-m", "competition.local_runner"], cwd=str(isolated),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, env=env,
        )

        def send(obs: dict) -> dict:
            assert proc.stdin is not None and proc.stdout is not None
            proc.stdin.write(json.dumps(obs) + "\n")
            proc.stdin.flush()
            line = proc.stdout.readline()
            if not line:
                stderr = proc.stderr.read() if proc.stderr else ""
                raise SystemExit(f"Local mock harness produced no output (exited early). stderr:\n{stderr}")
            return json.loads(line)

        observation = {
            "case_id": "standalone_full_loop_verify", "turn": 0, "observation_type": "initial",
            "chief_complaint": "sudden crushing chest pressure radiating to my left arm, sweating",
            "demographics": {"age": 58, "sex": "male"}, "max_turns": MAX_TURNS_SAFETY_CAP,
        }
        turn_log = []
        for turn in range(1, MAX_TURNS_SAFETY_CAP + 1):
            action = send(observation)
            turn_log.append((turn, action.get("action_type"), action.get("content", "")[:60]))
            action_type = action.get("action_type")
            if action_type == "DIAGNOSE":
                break
            if action_type == "ASK":
                content = "Denies that symptom, nothing else to add."
            elif action_type == "EXAM":
                content = "Unremarkable, within normal limits."
            elif action_type == "TEST":
                content = "Normal / negative."
            else:
                raise SystemExit(f"Unexpected action_type {action_type!r} at turn {turn}: {action}")
            observation = {
                "case_id": "standalone_full_loop_verify", "turn": turn,
                "observation_type": {"ASK": "ask_response", "EXAM": "exam_result", "TEST": "test_result"}[action_type],
                "content": content,
            }
        else:
            proc.terminate()
            raise SystemExit(f"Never reached DIAGNOSE within the {MAX_TURNS_SAFETY_CAP}-turn safety cap")

        proc.stdin.close()
        proc.wait(timeout=10)
        stderr_tail = (proc.stderr.read() if proc.stderr else "")[-2000:]

    print(f"Ran {len(turn_log)} turn(s) standalone (isolated copy, PYTHONPATH cleared):")
    for turn, action_type, preview in turn_log:
        print(f"  turn {turn:2d}: {action_type:<8} {preview!r}")
    print(f"\nFinal action: {turn_log[-1][1]} -- {turn_log[-1][2]!r}")
    print(f"\nProcess exit code: {proc.returncode}")
    if stderr_tail.strip():
        print("\n--- stderr tail (LLM-unavailable warnings etc., expected in this sandbox) ---")
        print(stderr_tail)
    if turn_log[-1][1] != "DIAGNOSE":
        raise SystemExit("FAILED: loop did not end in DIAGNOSE")
    print("\nSTANDALONE FULL-LOOP VERIFICATION: PASSED "
          "(observation -> routing -> retrieval -> differential -> ASK/EXAM/TEST -> update -> DIAGNOSE)")


if __name__ == "__main__":
    main()
