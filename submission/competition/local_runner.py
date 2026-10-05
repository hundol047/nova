"""Explicit offline mock development harness: python -m competition.local_runner.

This PLACEHOLDER protocol is not an organizer transport or official invocation.
The official run.py never imports or invokes this module.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Make the co-located nova_agent/ and competition/ packages importable regardless of the current
# working directory this script is invoked from -- this is what makes `submission/` runnable on
# its own, copied anywhere, with nothing else from the source repository present.


from nova_agent.config import get_config  # noqa: E402
from nova_agent.llm_client import get_llm_client  # noqa: E402
from nova_agent.orchestrator import DoctorAgent  # noqa: E402

from competition.adapter import NovaCompetitionAgent, RealLLMUnavailableError  # noqa: E402

def _build_agent() -> DoctorAgent:
    """Offline local harness, never an official competition execution."""
    from nova_agent.llm_client import MockLLMClient
    if get_config().llm_provider != "mock":
        raise RealLLMUnavailableError("LOCAL DEVELOPMENT ONLY: this harness permits mock only.")
    print("Runtime preflight passed: explicit local mock; official execution NOT VERIFIED", file=sys.stderr)
    return DoctorAgent(llm_client=MockLLMClient())


def run_jsonlines(agent: NovaCompetitionAgent) -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            observation = json.loads(line)
            action = agent.act(observation)
        except RealLLMUnavailableError as exc:
            # Deliberately NOT caught by the generic handler below: this is not a malformed-line
            # hiccup that a resend could fix -- it means the competition-mode case just reached
            # its final answer with zero successful real-LLM calls, even after bounded retry
            # (spec section 12). Disguising it as a normal recoverable-ASK response would be
            # exactly the "silent deterministic-only success" the adapter's raise exists to
            # prevent, so this must actually stop the run, loudly, on stderr.
            print(f"FATAL: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
        except Exception as exc:
            print(f"LOCAL PROTOCOL FAILURE: {type(exc).__name__}", file=sys.stderr)
            raise SystemExit(1) from exc
        sys.stdout.write(json.dumps(action, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def run_interactive(agent: NovaCompetitionAgent) -> None:
    case_id = input("case_id [demo]: ").strip() or "demo"
    chief_complaint = input("chief complaint: ").strip()
    age_raw = input("age (optional): ").strip()
    sex = input("sex (optional): ").strip()
    demographics = {}
    if age_raw:
        demographics["age"] = int(age_raw)
    if sex:
        demographics["sex"] = sex

    observation = {"case_id": case_id, "observation_type": "initial",
                    "chief_complaint": chief_complaint, "demographics": demographics}
    while True:
        action = agent.act(observation)
        print(f"\n[{action['action_type']}] {action['content']}")
        if action["action_type"] in {"DIAGNOSE", "INSUFFICIENT_INFORMATION"}:
            print("\n--- Case complete ---")
            break
        answer = input("your answer/result: ").strip()
        observation = {"case_id": case_id, "observation_type": "ask_response", "content": answer}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--interactive", action="store_true",
                         help="Run an interactive terminal demo instead of reading JSON lines from stdin.")
    args = parser.parse_args()

    try:
        competition_agent = NovaCompetitionAgent(agent=_build_agent())
    except RealLLMUnavailableError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    if args.interactive:
        run_interactive(competition_agent)
    else:
        run_jsonlines(competition_agent)


if __name__ == "__main__":
    main()
