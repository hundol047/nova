#!/usr/bin/env python3
"""Competition readiness gate (spec sections 4/22/30): `python scripts/preflight_competition.py`

A hard pass/fail check meant to run BEFORE submitting (locally or in CI) -- separate from
submission/run.py's own runtime preflight, which logs a loud warning but keeps running on the
deterministic fallback so a live competition run never just stops. This script's job is the
opposite: tell a human/CI truthfully whether a real competition run would actually use a real LLM,
and refuse to say READY if it wouldn't.

Exit code 0 + "READY" only when every check below passes. Otherwise exit code 1 + "NOT READY" and
the specific reasons.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FAIL_CHECKS: list[str] = []
WARN_CHECKS: list[str] = []
PASS_CHECKS: list[str] = []


def check(name: str, ok: bool, detail: str, *, severity: str = "fail") -> None:
    line = f"{name}: {detail}"
    if ok:
        PASS_CHECKS.append(line)
    elif severity == "warn":
        WARN_CHECKS.append(line)
    else:
        FAIL_CHECKS.append(line)


def main() -> int:
    # --- Python version ---------------------------------------------------------------------
    check("python_version", sys.version_info >= (3, 9),
          f"{sys.version.split()[0]} (requires >= 3.9)")

    # --- required packages -------------------------------------------------------------------
    try:
        import pydantic  # noqa: F401
        check("package_pydantic", True, f"pydantic {pydantic.VERSION} importable")
    except Exception as exc:
        check("package_pydantic", False, f"pydantic not importable: {exc}")

    # --- submission imports ------------------------------------------------------------------
    try:
        from nova_agent.orchestrator import DoctorAgent  # noqa: F401
        from nova_agent.config import get_config
        check("nova_agent_imports", True, "nova_agent.orchestrator.DoctorAgent imports cleanly")
    except Exception as exc:
        check("nova_agent_imports", False, f"import failed: {exc}")
        print_summary()
        return 1

    try:
        from competition.adapter import NovaCompetitionAgent  # noqa: F401
        check("competition_adapter_imports", True, "competition.adapter.NovaCompetitionAgent imports cleanly")
    except Exception as exc:
        check("competition_adapter_imports", False, f"import failed: {exc}")

    cfg = get_config()

    # --- model provider / endpoint / name -----------------------------------------------------
    provider = cfg.llm_provider
    check("llm_provider_configured", provider != "mock",
          f"NOVA_LLM_PROVIDER={provider!r} -- a competition run needs a real provider "
          f"(competition/openai_compatible/local/anthropic), not the offline mock stand-in.")

    # --- LLM health (real network check) ------------------------------------------------------
    from nova_agent.llm_client import get_llm_client
    client = get_llm_client()
    endpoint = getattr(client, "base_url", "n/a (SDK-based client, no HTTP base_url)")
    model = getattr(client, "model", cfg.llm_model)
    if provider == "mock":
        check("llm_health", False, "skipped (provider=mock has no real endpoint to check)")
    else:
        ok, reason = client.preflight()
        check("llm_health", ok, f"provider={provider} model={model!r} endpoint={endpoint} -- {reason}")

    # --- structured JSON output + legal action validation + real-LLM-success gate --------------
    # Two DISTINCT checks, deliberately not folded into one: a well-formed action can come from
    # the deterministic fallback alone (that's the whole point of the fallback -- it always
    # produces something legal), so "the action looks valid" says nothing about whether the real
    # LLM actually contributed to it. A competition submission must know both, separately.
    if provider != "mock":
        try:
            from nova_agent.orchestrator import DoctorAgent
            agent = DoctorAgent(llm_client=client)
            state = agent.new_case("preflight_smoke", "chest pain", {"age": 55, "sex": "male"})
            action, llm_output, differential = agent.decide(state)
            valid_action = action.action_type in {"ASK", "EXAM", "TEST", "DIAGNOSE"} and bool(action.content)
            check("structured_output_and_action_validation", valid_action,
                  f"one live turn produced action_type={action.action_type!r}, "
                  f"used_real_llm_output={'yes' if llm_output is not None else 'no (fell back)'}")
            # NOTE: `llm_output is not None` is NOT a useful signal here -- every real client
            # (Anthropic/OpenAI-compatible/competition) absorbs a failed call internally and
            # returns a deterministic AgentTurnOutput instead of None or raising (see
            # llm_client.py's generate_turn_output()), specifically so a single bad turn never
            # kills the run. `client._last_call_succeeded` is the actual low-level signal this
            # call's response was received AND parsed successfully against a live endpoint.
            real_parse_succeeded = getattr(client, "_last_call_succeeded", None) is True
            check("structured_output_parse_success", real_parse_succeeded,
                  "the live call's response parsed into AgentTurnOutput successfully"
                  if real_parse_succeeded else
                  "the live call either failed outright or returned output that failed to parse "
                  "-- the action above came from the deterministic fallback, not the real model")
            check("real_llm_success_count_at_least_1", state.real_llm_ever_succeeded is True,
                  f"llm_call_count={state.llm_call_count} llm_success_count={state.llm_success_count} "
                  "(bounded retry already applied per call -- see NOVA_LLM_MAX_RETRIES)")
        except Exception as exc:
            check("structured_output_and_action_validation", False, f"live turn raised: {exc}")
            check("structured_output_parse_success", False, f"live turn raised: {exc}")
            check("real_llm_success_count_at_least_1", False, f"live turn raised: {exc}")
    else:
        check("structured_output_and_action_validation", False, "skipped (provider=mock)")
        check("structured_output_parse_success", False, "skipped (provider=mock)")
        check("real_llm_success_count_at_least_1", False, "skipped (provider=mock)")

    # --- RAG / knowledge files ------------------------------------------------------------------
    knowledge_dir = Path(cfg.knowledge_dir)
    disease_files = list((knowledge_dir / "diseases").glob("*.json")) if knowledge_dir.is_dir() else []
    check("knowledge_files", len(disease_files) > 0, f"{len(disease_files)} disease knowledge file(s) found in {knowledge_dir}")

    # --- run.py present -----------------------------------------------------------------------
    submission_run = ROOT / "submission" / "run.py"
    check("submission_run_py", submission_run.exists(), str(submission_run))

    # --- turn limit -----------------------------------------------------------------------------
    check("turn_limit_configured", 1 <= cfg.max_turns <= 60, f"NOVA_MAX_TURNS={cfg.max_turns}")

    # --- official adapter status (informational, never blocks) --------------------------------
    check("official_competition_schema", False,
          "competition/schema.py is a documented PLACEHOLDER -- no official N.O.V.A. 2026 API was "
          "available at implementation time. Update competition/schema.py + adapter.py once published.",
          severity="warn")

    # --- submission size ------------------------------------------------------------------------
    submission_dir = ROOT / "submission"
    if submission_dir.is_dir():
        total_bytes = sum(f.stat().st_size for f in submission_dir.rglob("*") if f.is_file())
        mb = total_bytes / (1024 * 1024)
        check("submission_size", mb < 50, f"{mb:.1f} MB (submission/ directory)")
    else:
        check("submission_size", False, "submission/ directory does not exist -- run scripts/build_nova_submission.py")

    # --- internet dependency (informational) ---------------------------------------------------
    if provider == "mock":
        check("endpoint_locality", True, "skipped (provider=mock has no endpoint)", severity="warn")
    else:
        is_local = any(host in endpoint for host in ("localhost", "127.0.0.1", "0.0.0.0")) if isinstance(endpoint, str) else True
        check("endpoint_locality", is_local,
              f"endpoint={endpoint} is "
              f"{'local/offline' if is_local else 'NOT localhost -- verify this is the official, authorized endpoint before submitting'}",
              severity="warn")

    # --- secret leakage (light static scan) -----------------------------------------------------
    # Same shape/patterns as scripts/build_nova_submission.py's own (gating) secret scan --
    # anchored regexes requiring an actual credential-shaped run of characters after the prefix,
    # not a bare substring check. A bare "sk-" substring check previously flagged ordinary English
    # text like "risk-only" or "desk-side" as a false positive; these patterns don't.
    suspicious = []
    secret_patterns = [re.compile(p) for p in (
        r"sk-[A-Za-z0-9]{16,}",
        r"sk-ant-[A-Za-z0-9\-_]{16,}",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        r"AKIA[0-9A-Z]{16}",
    )]
    for path in list((ROOT / "nova_agent").rglob("*.py")) + list((ROOT / "competition").rglob("*.py")):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pat in secret_patterns:
            if pat.search(text):
                suspicious.append(f"{path.relative_to(ROOT)} matches {pat.pattern!r}")
    check("secret_scan", not suspicious, "no suspicious credential-shaped strings found in nova_agent/competition"
          if not suspicious else "; ".join(suspicious))

    return print_summary()


def print_summary() -> int:
    print("=== Competition Preflight ===\n")
    for line in PASS_CHECKS:
        print(f"  PASS  {line}")
    for line in WARN_CHECKS:
        print(f"  WARN  {line}")
    for line in FAIL_CHECKS:
        print(f"  FAIL  {line}")

    ready = not FAIL_CHECKS
    print()
    if ready:
        print("READY")
        return 0
    print("NOT READY")
    for line in FAIL_CHECKS:
        print(f"  - {line}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
