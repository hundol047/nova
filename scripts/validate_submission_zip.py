#!/usr/bin/env python3
"""Clean-room validation of a submission ZIP (preliminary-round package rules).

Extracts the archive into a NEW EMPTY temporary directory (the repository is not on the path), checks the
package rules, then runs the extracted code with an isolated interpreter (``-I``: no cwd, no PYTHONPATH, no
user site) against the declared requirements only:

  * ``run.py`` and ``requirements.txt`` at the ZIP root; archive < 50,000,000 bytes (the organizers' 50 MB);
  * every member is valid UTF-8 text (code/data); no member is a symlink or an absolute/parent path;
  * no evaluation cases, answers, keys/tokens, web server, training code or weights are shipped;
  * requirements.txt names only packages the runtime imports (pydantic) and no ML/server stack;
  * a full offline mock encounter runs from the extracted tree under the preliminary rules;
  * ``run.py`` still FAILS CLOSED (exit code != 0, "NOT READY" message): no organizer transport is integrated.

A pass proves the package is self-contained and well-formed. It does NOT prove official-interface
compatibility, real-model behaviour, or licence clearance, and the report says so.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 50_000_000
FORBIDDEN_PARTS = re.compile(r"(^|/)(evaluation|tests?|backend|frontend|web|production|docker|learning|training|artifacts|research)(/|$)", re.I)
FORBIDDEN_NAMES = re.compile(r"(\.env|\.pem|\.key|id_rsa|credentials|secret|token)|\.(pt|pth|bin|ckpt|safetensors|onnx|gguf|npy|npz|pkl|pickle|h5|sqlite3?|db)$", re.I)
FORBIDDEN_IMPORTS = re.compile(r"^\s*(?:import|from)\s+(?:torch|transformers|sentence_transformers|fastapi|flask|uvicorn|django|peft|tensorflow|sklearn|numpy|pandas)\b", re.M)
ALLOWED_REQUIREMENTS = {"pydantic"}

ENCOUNTER = r"""
import json, sys
sys.path.insert(0, ".")
from competition.submission_profile import build_submission_agent
from nova_agent.llm_client import MockLLMClient
from nova_agent.orchestrator import DoctorAgent
agent = build_submission_agent(DoctorAgent(llm_client=MockLLMClient()))
obs = {"case_id": "cleanroom-1", "observation_type": "initial", "chief_complaint": "Belly pain began near my navel yesterday and moved to the right lower side.",
       "demographics": {"age": 24, "sex": "male"}, "vital_signs": "BP 120/78, HR 98, Temp 38.0"}
actions = []
for _ in range(70):
    act = agent.act(obs); actions.append(act)
    if act["action_type"] == "DIAGNOSE":
        break
    pending = agent._pending_actions["cleanroom-1"]
    kind = "say_response" if act["action_type"] == "SAY" else "exam_result"
    obs = {"case_id": "cleanroom-1", "observation_type": kind, "content": "No, nothing like that."}
kinds = [a["action_type"] for a in actions]
print(json.dumps({"kinds": sorted(set(kinds)), "turns": len(actions) - 1, "final": kinds[-1],
                  "say_max_chars": max([len(a["content"]) for a in actions if a["action_type"] == "SAY"] or [0]),
                  "has_soap": bool(actions[-1].get("soap")), "primary_diagnosis": actions[-1].get("primary_diagnosis")}))
"""


def validate(zip_path: Path, python: str) -> dict:
    report = {"zip": str(zip_path), "bytes": zip_path.stat().st_size, "sha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(), "checks": {}}
    ok = report["checks"]
    with zipfile.ZipFile(zip_path) as zf, tempfile.TemporaryDirectory(prefix="nova-cleanroom-") as tmp:
        names = zf.namelist()
        ok["root_has_run_py_and_requirements"] = "run.py" in names and "requirements.txt" in names
        ok["under_50MB"] = report["bytes"] < LIMIT
        bad_paths = [n for n in names if n.startswith("/") or ".." in Path(n).parts]
        ok["no_absolute_or_parent_paths"] = not bad_paths
        symlinks = [i.filename for i in zf.infolist() if (i.external_attr >> 16) & 0o170000 == 0o120000]
        ok["no_symlinks"] = not symlinks
        non_utf8 = []
        for n in names:
            try:
                zf.read(n).decode("utf-8")
            except UnicodeDecodeError:
                non_utf8.append(n)
        ok["all_members_utf8"] = not non_utf8
        ok["no_forbidden_directories"] = not [n for n in names if FORBIDDEN_PARTS.search(n)]
        ok["no_forbidden_file_names_or_weights"] = not [n for n in names if FORBIDDEN_NAMES.search(Path(n).name)]
        zf.extractall(tmp)
        tmp_path = Path(tmp)
        ok["no_forbidden_imports"] = not [str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*.py")
                                          if FORBIDDEN_IMPORTS.search(p.read_text(encoding="utf-8"))]
        requirements = [re.split(r"[<>=!~\[;\s]", line.strip(), 1)[0].lower()
                        for line in (tmp_path / "requirements.txt").read_text(encoding="utf-8").splitlines()
                        if line.strip() and not line.strip().startswith("#")]
        ok["requirements_only_declared_runtime_deps"] = set(requirements) <= ALLOWED_REQUIREMENTS
        report["requirements"] = requirements
        # Isolated interpreter, empty cwd = the extracted tree, no repository on any path.
        run = subprocess.run([python, "-I", "-c", ENCOUNTER], cwd=tmp, capture_output=True, text=True, timeout=300)
        ok["offline_mock_encounter_runs"] = run.returncode == 0
        if run.returncode == 0:
            encounter = json.loads(run.stdout.strip().splitlines()[-1])
            report["encounter"] = encounter
            ok["encounter_obeys_preliminary_actions"] = set(encounter["kinds"]) <= {"SAY", "EXAM", "DIAGNOSE"}
            ok["encounter_within_50_turns_and_30_char_say"] = encounter["turns"] <= 50 and encounter["say_max_chars"] <= 30
            ok["encounter_ends_with_soap_and_one_diagnosis"] = encounter["final"] == "DIAGNOSE" and encounter["has_soap"] and bool(encounter["primary_diagnosis"])
        else:
            report["encounter_error"] = run.stderr[-800:]
        gate = subprocess.run([python, "-I", "run.py"], cwd=tmp, capture_output=True, text=True, timeout=120)
        ok["run_py_fails_closed_until_official_interface"] = gate.returncode != 0 and "NOT READY" in gate.stderr
        report["run_py_gate_message"] = gate.stderr.strip()[:300]
    report["all_pass"] = all(ok.values())
    report["scope"] = ("Package well-formedness and offline self-containment only. NOT evidence of official-interface "
                       "compatibility, real gpt-oss-20b behaviour, accuracy, or source/licence clearance.")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("zip", nargs="?", type=Path, default=ROOT / "submission/submission.zip")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = validate(args.zip, args.python)
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text)
    raise SystemExit(0 if report["all_pass"] else 1)


if __name__ == "__main__":
    main()
