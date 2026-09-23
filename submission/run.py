#!/usr/bin/env python3
"""N.O.V.A. 2026 Doctor Agent -- standalone submission entrypoint (spec section 16/24I).

This file, plus the nova_agent/ and competition/ packages copied alongside it by
scripts/build_nova_submission.py, are everything needed to run the Doctor Agent: no backend/,
frontend/, docs/, tests/, or any other part of the source repository is required. Only
`requirements.txt` in this directory needs to be installed (pydantic only -- the real-LLM
providers use stdlib `urllib`, not a third-party SDK; see nova_agent/llm_client.py).

Provider selection: unlike local development (where NOVA_LLM_PROVIDER defaults to `mock`), THIS
entrypoint defaults to `competition` when NOVA_LLM_PROVIDER is not explicitly set, so a submission
run actually attempts real LLM clinical reasoning by default rather than silently reasoning
entirely on the deterministic mock fallback. `competition` (nova_agent/config.py's
`competition_base_url`) defaults to `http://localhost:8000/v1` -- localhost only, never an
arbitrary remote/internet endpoint guessed on your behalf -- override every NOVA_COMPETITION_*
variable via the environment once the official competition runtime contract is known; nothing in
this file needs to change.

Before serving any observation, this script runs `preflight()` on the configured LLM client. If it
is not reachable, a loud, structured warning is printed to **stderr** (never stdout, which carries
the JSON-lines protocol) and the run *continues* using nova_agent's existing per-turn deterministic
fallback -- a crashed/exited submission produces zero diagnoses, which is worse than a degraded but
still-safe run. This is the RUNTIME policy; for a hard pass/fail gate to check BEFORE submitting
(e.g. in CI), use `scripts/preflight_competition.py` instead, which does fail loudly.

Two modes:

1. Interactive (no arguments): a terminal loop for manually driving/demoing one case. Useful for
   local sanity-checking; not how a competition harness would normally invoke this.

       python run.py --interactive

2. JSON-lines protocol (default, and the one a real harness should use until the official
   competition invocation contract is published -- spec section 16 has no confirmed API to match
   yet): reads one JSON CompetitionObservation object per line from stdin, writes one JSON
   CompetitionAction object per line to stdout. This is a provisional, documented placeholder
   protocol (see competition/schema.py) -- update this file's I/O loop, not the agent underneath
   it, once the official interface is known.

       echo '{"case_id": "c1", "observation_type": "initial", "chief_complaint": "chest pain", "demographics": {"age": 55, "sex": "male"}}' | python run.py
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
sys.path.insert(0, str(Path(__file__).resolve().parent))

from nova_agent.config import get_config  # noqa: E402
from nova_agent.llm_client import get_llm_client  # noqa: E402
from nova_agent.orchestrator import DoctorAgent  # noqa: E402

from competition.adapter import NovaCompetitionAgent, RealLLMUnavailableError  # noqa: E402

# Local development explicitly opts into NOVA_LLM_PROVIDER=mock; a submission run that never set
# it at all should default to attempting the real competition LLM, not silently reasoning on mock
# for the entire run.
if not os.environ.get("NOVA_LLM_PROVIDER"):
    os.environ["NOVA_LLM_PROVIDER"] = "competition"


def _build_agent() -> DoctorAgent:
    client = get_llm_client()
    ok, reason = client.preflight()
    provider = get_config().llm_provider
    if not ok:
        print(
            "Competition LLM unavailable\n"
            f"Provider: {provider}\n"
            f"Model: {getattr(client, 'model', '?')}\n"
            f"Endpoint: {getattr(client, 'base_url', 'n/a')}\n"
            f"Reason: {reason}\n"
            "Continuing with nova_agent's per-turn deterministic fallback -- clinical reasoning "
            "for this run will NOT use a real LLM. Run `python scripts/preflight_competition.py` "
            "before submitting to catch this ahead of time.",
            file=sys.stderr,
        )
    else:
        print(f"LLM provider ready: {provider} ({reason})", file=sys.stderr)
    return DoctorAgent(llm_client=client)


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
        except Exception as exc:  # a single malformed line must never kill the whole run
            action = {"error": str(exc), "action_type": "ASK",
                      "content": "Unable to process the previous observation; please resend."}
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
        if action["action_type"] == "DIAGNOSE":
            print("\n--- Case complete ---")
            break
        answer = input("your answer/result: ").strip()
        observation = {"case_id": case_id, "observation_type": "ask_response", "content": answer}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--interactive", action="store_true",
                         help="Run an interactive terminal demo instead of reading JSON lines from stdin.")
    args = parser.parse_args()

    competition_agent = NovaCompetitionAgent(agent=_build_agent())
    if args.interactive:
        run_interactive(competition_agent)
    else:
        run_jsonlines(competition_agent)


if __name__ == "__main__":
    main()
