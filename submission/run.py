#!/usr/bin/env python3
"""N.O.V.A. 2026 Doctor Agent -- standalone submission entrypoint (spec section 16/24I).

This file, plus the nova_agent/ and competition/ packages copied alongside it by
scripts/build_submission.py, are everything needed to run the Doctor Agent: no backend/,
frontend/, docs/, tests/, or any other part of the source repository is required. Only
`requirements.txt` in this directory needs to be installed (pydantic; `openai` only if
NOVA_LLM_PROVIDER selects an OpenAI-compatible/local/competition runtime).

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
import sys
from pathlib import Path

# Make the co-located nova_agent/ and competition/ packages importable regardless of the current
# working directory this script is invoked from -- this is what makes `submission/` runnable on
# its own, copied anywhere, with nothing else from the source repository present.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from competition.adapter import NovaCompetitionAgent  # noqa: E402


def run_jsonlines(agent: NovaCompetitionAgent) -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            observation = json.loads(line)
            action = agent.act(observation)
        except Exception as exc:  # a single malformed line must never kill the whole run
            action = {"error": str(exc), "action_type": "ASK",
                      "content": "Unable to process the previous observation; please resend."}
        sys.stdout.write(json.dumps(action, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def run_interactive() -> None:
    agent = NovaCompetitionAgent()
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

    if args.interactive:
        run_interactive()
    else:
        run_jsonlines(NovaCompetitionAgent())


if __name__ == "__main__":
    main()
