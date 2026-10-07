"""Tripwires: the competition package can neither import nor activate learning / persistence / network use.

Evaluated inference must not learn from, store, or phone home with patient cases. These tests run a full
preliminary encounter in a clean subprocess under an audit hook that records file writes and sockets."""
import ast
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_TOP_LEVEL = {"learning", "backend", "production", "frontend", "torch", "tensorflow", "sklearn", "scipy", "numpy",
                       "transformers", "sentence_transformers", "onnxruntime", "peft", "bitsandbytes", "datasets",
                       "anthropic", "openai", "requests", "httpx", "aiohttp", "fastapi", "sqlalchemy", "psycopg", "joblib"}
PACKAGES = ("nova_agent", "competition", "submission/nova_agent", "submission/competition")


def _imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split(".")[0], node.lineno
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            yield node.module.split(".")[0], node.lineno


def test_no_competition_module_imports_a_learning_or_heavy_ml_or_web_package():
    offenders = []
    for package in PACKAGES:
        base = ROOT / package
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            for top, line in _imports(path):
                if top in FORBIDDEN_TOP_LEVEL:
                    offenders.append(f"{path.relative_to(ROOT)}:{line} imports {top}")
    # `anthropic` is a documented OPTIONAL development provider imported lazily inside one client class.
    allowed = {o for o in offenders if "nova_agent/llm_client.py" in o and ("anthropic" in o)}
    assert [o for o in offenders if o not in allowed] == []


def test_ml_ranker_and_training_are_off_by_default_and_blocked_for_submission(monkeypatch):
    from nova_agent.config import get_config
    cfg = get_config(reload=True)
    assert cfg.ml_ranker_enabled is False and not cfg.ml_model_path
    monkeypatch.setenv("NOVA_ML_RANKER_ENABLED", "true")
    from competition.provider_lock import enforce_submission_provider
    with pytest.raises(RuntimeError, match="NOT READY"):
        enforce_submission_provider()
    monkeypatch.delenv("NOVA_ML_RANKER_ENABLED")
    get_config(reload=True)


def test_no_training_or_online_adaptation_entry_points_exist_in_the_package():
    banned = ("partial_fit", "fine_tune", "finetune", "retrain", "online_learning", "pseudo_label", "update_index",
              "append_case", "persist_case", "save_case")
    hits = []
    for package in ("nova_agent", "competition"):
        for path in (ROOT / package).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                name = getattr(node, "name", None) if isinstance(node, (ast.FunctionDef, ast.ClassDef)) else None
                if name and any(b in name.lower() for b in banned):
                    hits.append(f"{path.relative_to(ROOT)}:{name}")
    assert hits == []


_PROBE = textwrap.dedent('''
    import json, sys
    sys.path.insert(0, {root!r})
    events = {{"writes": [], "net": []}}
    def hook(event, args):
        if event == "open":
            path, mode = args[0], (args[1] or "") if len(args) > 1 else ""
            if isinstance(path, str) and any(c in str(mode) for c in "wax+") and "__pycache__" not in path and not path.startswith("/dev/"):
                events["writes"].append(path)
        elif event in ("socket.connect", "socket.getaddrinfo", "socket.bind"):
            events["net"].append(event)
    sys.addaudithook(hook)
    from competition.submission_profile import build_submission_agent
    from nova_agent.llm_client import MockLLMClient
    from nova_agent.orchestrator import DoctorAgent
    from evaluation.preliminary_dev_cases import PRELIM_KO_CASES
    from evaluation.preliminary_driver import run_episode
    agent = build_submission_agent(DoctorAgent(llm_client=MockLLMClient()))
    for case in PRELIM_KO_CASES[:2]:
        run_episode(case, agent=agent)
    loaded = sorted({{m.split(".")[0] for m in sys.modules}})
    print(json.dumps({{"events": events, "loaded": loaded}}))
''')


@pytest.fixture(scope="module")
def probe():
    out = subprocess.run([sys.executable, "-I", "-c", _PROBE.format(root=str(ROOT))], capture_output=True, text=True,
                         timeout=300, cwd=ROOT, env={"PATH": "/usr/bin:/bin", "HOME": "/nonexistent", "PYTHONDONTWRITEBYTECODE": "1"})
    assert out.returncode == 0, out.stderr[-2000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_a_full_encounter_writes_no_files_and_opens_no_sockets(probe):
    assert probe["events"]["writes"] == [] and probe["events"]["net"] == []


def test_a_full_encounter_loads_no_learning_or_training_stack(probe):
    assert not (set(probe["loaded"]) & (FORBIDDEN_TOP_LEVEL - {"anthropic"}))


def test_submission_zip_contains_no_learning_training_or_private_artifacts():
    manifest = ROOT / "submission" / "MANIFEST.json"
    if not manifest.exists():
        pytest.skip("submission not built")
    import zipfile
    with zipfile.ZipFile(ROOT / "submission" / "submission.zip") as z:
        names = z.namelist()
    bad = [n for n in names if n.split("/")[0] in {"learning", "backend", "frontend", "production", "docker", "evaluation", "tests", "artifacts"}
           or n.endswith((".pt", ".pth", ".safetensors", ".onnx", ".ckpt", ".bin", ".gguf", ".npy", ".pkl", ".joblib"))]
    assert bad == [] and "run.py" in names and "requirements.txt" in names
