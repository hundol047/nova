#!/usr/bin/env python3
"""HUMAN-RUN ONLY: run this agent on server-backed public samples on your own computer.

DO NOT RUN FROM CODEX / CLAUDE CODE / CURSOR. Participant development keys
and credits must not be connected to coding tools. This program requires an
explicit --human-run acknowledgement and refuses known coding-agent environments
BEFORE accessing the development-key variable.

The code runs on your machine; the virtual patient, the examiner and the Doctor model (gpt-oss-20b) are the organizer's.
Requires network access to the organizer API and the development key in the environment (never on the command line,
never printed, never written to disk):

    export NOVA_API_BASE=https://<organizer API origin from the participant guide>
    export NOVA_DEV_KEY=...            # your personal development key
    python scripts/run_dev_samples.py --human-run C01 C03 C10 --output ~/nova-sample-results

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


def require_human_run(acknowledged, environ):
    ci = {'CI', 'GITHUB_ACTIONS', 'GITLAB_CI', 'CIRCLECI', 'TRAVIS', 'BUILDKITE', 'JENKINS_URL', 'TF_BUILD', 'TEAMCITY_VERSION', 'CLAUDECODE'}
    if not acknowledged or any(k.upper().startswith(("CODEX_", "CLAUDE_CODE_", "CURSOR_")) or k.upper() in ci for k in environ):
        raise SystemExit("HUMAN-RUN ONLY. Execute on your own computer, outside Codex/Claude Code/Cursor; no key was read.")


def redact(value, secret=''):
    from scripts.official_result_tools import redact as sanitize
    return sanitize(value, secret)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cases", nargs="*")
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--candidate', choices=['v42', 'v43', 'v44', 'v45', 'v46', 'v47', 'v48'], help='Verify the exact published candidate ZIP instead of the historical full-suite release')
    parser.add_argument('--case-id', action='append', default=[])
    parser.add_argument("--human-run", action="store_true", help="Human execution on your own computer only")
    parser.add_argument("--output", default=str(Path.home() / "nova-sample-results"))
    args = parser.parse_args()
    require_human_run(args.human_run, os.environ)
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "submission"))
    from scripts.human_sample_capture import verify_runtime, ObservedClient, resolve_cases, capture_response
    from scripts.official_result_tools import LABEL, digest
    identity = verify_runtime(ROOT, candidate=args.candidate)
    out = Path(args.output).resolve()
    if out.is_relative_to(ROOT):
        raise SystemExit('Raw sample results must be outside the repository.')
    os.environ.setdefault("NOVA_COMPETITION_RETRIEVAL", "1")
    os.environ.setdefault("NOVA_PRELIMINARY_RULES", "1")
    os.environ.setdefault("NOVA_LLM_PROVIDER", "mock")
    base = os.environ.get("NOVA_API_BASE")
    if base != 'https://nova.snubhai.org':
        raise SystemExit('Human development keys may only be sent to https://nova.snubhai.org.')
    import re
    if len(set(args.cases))!=len(args.cases) or any(not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',label) for label in args.cases):
        raise SystemExit('Duplicate or unsafe output case label; no key was read.')
    if any((out/(label+'.json')).exists() or (out/(label+'.json')).is_symlink() for label in args.cases):
        raise SystemExit('Use a new output directory; existing result files are preserved.')
    key = os.environ.get("NOVA_DEV_KEY")
    if not key or not base:
        raise SystemExit("Set NOVA_API_BASE and NOVA_DEV_KEY in the environment (the key is never passed as an argument).")
    import nova_sdk
    from competition.nova_sdk_adapter import prepare
    import competition.nova_sdk_adapter as adapter
    if not Path(adapter.__file__).resolve().is_relative_to(ROOT/'submission'):
        raise SystemExit('Exact submission runtime required; cached source import refused.')
    catalog = nova_sdk.Client(api_base=base, token=key, sample=True)._request('GET', '/v1/sample/cases')['cases']
    if args.list:
        for row in catalog:
            print(json.dumps(redact({'case_id': row['case_id'], 'opening': row.get('initial', {}).get('opening', '')[:100]}, key), ensure_ascii=False))
        return
    if not args.cases:
        raise SystemExit('Supply cases and published ID mappings, or --list.')
    resolved = resolve_cases(args.cases, catalog, args.case_id)
    out.mkdir(parents=True, exist_ok=True)
    for case, published_id in resolved:
        started = time.monotonic()
        prepared = prepare()
        raw_client = nova_sdk.Client(api_base=base, token=key, sample=True)
        raw_client.ready()
        created = raw_client.create_sample(published_id)
        client = ObservedClient(raw_client)
        events = []
        def observe(event):
            import unicodedata
            if len(events) >= 2000:
                raise ValueError('Observation bound exceeded')
            event = dict(event)
            if 'response' in event:event['response']=capture_response(event['operation'],event['response'])
            if event['operation'] == client.last_observation.get('operation'):
                event.update(client.last_observation)
            if isinstance(event.get('text'), str):
                event['nfc_length'] = len(unicodedata.normalize('NFC', event['text']))
            events.append(redact(event, key))
        # Historical archives predate the shared factory. Their own consult
        # used OfficialEncounter; newer archives use their packaged factory.
        factory = getattr(adapter, 'make_encounter', None)
        if factory is None:
            if hasattr(adapter, 'consult') and 'AdaptiveEncounter' in adapter.consult.__code__.co_names:
                from competition.adaptive_encounter import AdaptiveEncounter
                factory = AdaptiveEncounter
            else:
                factory = adapter.OfficialEncounter
        encounter = factory(client, prepared, observer=observe, log=lambda _: None)
        row = {'label': LABEL, 'mode': 'HUMAN_RUN', "case": case, "sdk_version": nova_sdk.__version__,
               'runtime': identity, 'session_id': '[REDACTED]', 'created': redact(capture_response('session',created), key)}
        try:
            row["diagnose_response"] = capture_response('diagnose',encounter.run())
            row["status"] = row['diagnose_response'].get('status', 'UNKNOWN')
        except nova_sdk.NovaError as exc:
            row["status"] = f"error:{exc.code}"
        except Exception:
            row['status'] = 'error:LOCAL_EXECUTION_ERROR'
        row["seconds"] = time.monotonic() - started
        row['prepare_seconds'] = prepared.get('prepare_seconds')
        row['initial'] = {'opening': getattr(encounter, 'opening', ''), 'vital_signs': getattr(encounter, 'vitals', ''),
                          'deadline': encounter.deadline}
        row['events'] = events
        row['observer_failures'] = encounter.observer_failures
        note = next((e.get('note') for e in reversed(events) if e['operation']=='diagnose'), None)
        row['record_digest_local'] = digest(note) if note else None
        row['record_digest_server'] = row.get('diagnose_response',{}).get('record_digest')
        row["doctor"] = encounter.stats.as_dict()
        row["turns"] = [{"kind": t.kind, "text": t.text, "reply": t.reply, "rejected": t.rejected, "turn": t.turn}
                        for t in encounter.turns]
        row["exam_rejections"] = encounter.exam_rejections
        try:
            row["session_after"] = capture_response('session',client.session())
        except nova_sdk.NovaError as exc:
            row["session_after"] = {"error": exc.code}
        with (out / f"{case}.json").open('x',encoding='utf-8') as f:
            f.write(json.dumps(redact(row, key), ensure_ascii=False, indent=1) + "\n")
        print(json.dumps(redact({k: row[k] for k in ("case", "status", "seconds", "exam_rejections")} | row["doctor"], key),
                         ensure_ascii=False))


if __name__ == "__main__":
    main()
