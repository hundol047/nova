#!/usr/bin/env python3
"""Fresh-directory smoke test of submission/submission.zip (LOCAL PRE-GUIDE CANDIDATE check, not an official run).

Unzips the archive into an empty temporary directory (nothing from the source repository on the path), then
 1. checks run.py / requirements.txt at the ZIP root, UTF-8 text, size < 50 MB;
 2. runs ``run.py`` and requires the documented FAIL-CLOSED exit (the official interface is not integrated);
 3. drives one complete Korean preliminary encounter through the packaged adapter with the explicit offline mock
    (SAY/EXAM/DIAGNOSE only, S/O/A/P note, a mixed positive/negative answer retained verbatim).

    python scripts/smoke_fresh_package.py [--python /path/to/python-with-pydantic]
"""
import argparse
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANSWER = "아니요, 아스피린 알레르기가 있어요."


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", default=str(ROOT / "submission" / "submission.zip"))
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args()
    archive = Path(args.zip)
    assert archive.stat().st_size < 50_000_000, "ZIP exceeds 50 MB"
    with tempfile.TemporaryDirectory(prefix="nova-fresh-") as tmp:
        pkg = Path(tmp)
        with zipfile.ZipFile(archive) as z:
            names = z.namelist()
            assert "run.py" in names and "requirements.txt" in names, "run.py / requirements.txt must be at the ZIP root"
            z.extractall(pkg)
        for name in names:
            if name.endswith((".py", ".txt", ".json", ".md")):
                (pkg / name).read_bytes().decode("utf-8")
        env = {"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "NOVA_LLM_PROVIDER": "mock", "NOVA_PRELIMINARY_RULES": "1"}
        run = subprocess.run([args.python, "run.py"], cwd=pkg, env=env, capture_output=True, text=True, timeout=120)
        assert run.returncode != 0 and "NOT READY" in run.stderr and not run.stdout.strip(), (run.returncode, run.stderr)
        proc = subprocess.Popen([args.python, "-m", "competition.local_runner"], cwd=pkg, env=env, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        def send(obs: dict) -> dict:
            proc.stdin.write(json.dumps(obs, ensure_ascii=False) + "\n")
            proc.stdin.flush()
            return json.loads(proc.stdout.readline())

        action = send({"case_id": "SMOKE", "observation_type": "initial", "demographics": {"age": 42, "sex": "female"},
                       "chief_complaint": "이영희, 42세 여자예요. 식사하고 나면 명치가 타는 것처럼 쓰려요."})
        steps = 0
        while action["action_type"] != "DIAGNOSE" and steps < 60:
            assert action["action_type"] in {"SAY", "EXAM"}, action["action_type"]
            assert action["action_type"] != "SAY" or len(action["content"]) <= 30, action["content"]
            steps += 1
            kind = "say_response" if action["action_type"] == "SAY" else "exam_result"
            reply = ANSWER if "알레르기" in action["content"] else "특이 소견 없음"
            action = send({"case_id": "SMOKE", "observation_type": kind, "content": reply})
        proc.stdin.close()
        proc.wait(timeout=60)
        assert action["action_type"] == "DIAGNOSE" and set(action["soap"]) == set("SOAP") and action["primary_diagnosis"]
        assert ANSWER in action["soap"]["S"], "mixed positive/negative answer must survive into the SOAP note"
        assert steps <= 50
        print(f"fresh-directory smoke OK: run.py fail-closed; {steps} interactions -> {action['primary_diagnosis']} (offline mock; official NOT VERIFIED)")


if __name__ == "__main__":
    main()
