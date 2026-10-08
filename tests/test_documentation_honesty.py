"""CURRENT documentation must not overclaim: status, coverage vocabulary, the 8-call budget, mock-vs-real model."""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURRENT_DOCS = ["README.md", "docs/CURRENT_STATUS.md", "docs/competition/OFFICIAL_INTERFACE_AUDIT.md"]


def _text(name):
    return (ROOT / name).read_text(encoding="utf-8")


def test_fixed_model_constants_are_exact():
    from nova_agent.config import EXPECTED_COMPETITION_MODEL, EXPECTED_COMPETITION_REVISION
    assert EXPECTED_COMPETITION_MODEL == "openai/gpt-oss-20b"
    assert EXPECTED_COMPETITION_REVISION == "4d7ae4984b7db7de8f8457170b3f1a419ee76d52"
    for name in ("README.md", "docs/CURRENT_STATUS.md"):
        assert "openai/gpt-oss-20b" in _text(name) and "4d7ae4984b7db7de8f8457170b3f1a419ee76d52" in _text(name)


def test_status_pages_say_pre_guide_candidate_not_ready_and_mock_only():
    for name in ("README.md", "docs/CURRENT_STATUS.md"):
        text = _text(name)
        assert "PRE-GUIDE CANDIDATE" in text and "NOT OFFICIALLY READY" in text
        assert "NOT VERIFIED" in text and "mock" in text.lower()
    assert "LOCAL DEVELOPMENT / PRELIMINARY SIMULATION" in _text("docs/CURRENT_STATUS.md")


def test_no_inflated_disease_claims_in_current_docs():
    banned = [r"accurately diagnos\w*\s+(?:over\s+)?5,?000", r"diagnos\w*\s+5,?000\+?\s+(?:diseases|conditions)\b",
              r"5,?000\+?\s+(?:fully\s+)?(?:clinically\s+)?curated", r"(?:all|every)\s+diseases?\s+(?:accurately|reliably)"]
    for name in CURRENT_DOCS + ["README_NOVA.md", "docs/MODEL_CARD.md", "docs/ARCHITECTURE.md"]:
        path = ROOT / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in banned:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                before = text[max(0, match.start() - 90):match.start()].lower()
                assert re.search(r"\bnot\b|\bnever\b|\bno\b|do(?:es)? n['o]t", before), (name, match.group(0))


def test_stated_coverage_numbers_match_the_actual_catalog():
    out = subprocess.run([sys.executable, str(ROOT / "scripts/report_disease_coverage.py")], capture_output=True, text=True, cwd=ROOT).stdout
    tier1 = int(re.search(r"Tier-1 deep\s*:\s*(\d+)", out).group(1))
    tier2 = int(re.search(r"Tier-2 structured\s*:\s*(\d+)", out).group(1))
    tier3 = int(re.search(r"Tier-3 ontology-only\s*:\s*(\d+)", out).group(1))
    status = _text("docs/CURRENT_STATUS.md")
    assert tier3 == 0, "Tier-3 must stay empty in the bundled/submission runtime"
    for number in (f"{tier1}", f"{tier2:,}", f"{tier1 + tier2:,}"):
        assert number in status, number


def test_eight_calls_is_labelled_an_internal_budget_never_an_organizer_requirement():
    for name in CURRENT_DOCS:
        for line in _text(name).splitlines():
            if re.search(r"\b8 (?:model|LLM) calls\b|MAX_LLM_CALLS_PER_CASE", line):
                assert re.search(r"INTERNAL|internal|engineering budget", line), (name, line)
            assert not re.search(r"organizer[^.\n]*requires?[^.\n]*8 (?:model|LLM) calls", line, re.IGNORECASE), (name, line)


def test_official_run_py_is_fail_closed():
    run = subprocess.run([sys.executable, str(ROOT / "submission/run.py")], capture_output=True, text=True, cwd=ROOT, timeout=60,
                         env={"PATH": "/usr/bin:/bin", "NOVA_LLM_PROVIDER": "mock", "PYTHONPATH": str(ROOT / "submission")})
    assert run.returncode != 0 and "NOT READY" in run.stderr and run.stdout.strip() == ""
