# Official interface audit — 2026-10-03

Primary sources inspected: [overview](https://nova.snubhai.org/),
[evaluation](https://nova.snubhai.org/evaluation/), [rules](https://nova.snubhai.org/rules/),
[FAQ](https://nova.snubhai.org/faq/). Public links and searches for participant API/starter/example
material did not locate an executable interface specification. FAQ Q9 says the participant
guide will be announced before the preliminary round. This does not prove that private
participant mail contains no additional material; no such material was supplied here.

Each row has exactly one status. An official action name does not establish its JSON encoding.

| Element | Status | Evidence or current boundary |
| --- | --- | --- |
| ASK / EXAM / TEST / DIAGNOSE names | CONFIRMED_OFFICIAL | Evaluation: 진행 방식 |
| ASK meaning | CONFIRMED_OFFICIAL | Questions for history and symptoms |
| EXAM meaning | CONFIRMED_OFFICIAL | Physical examination selection |
| TEST meaning | CONFIRMED_OFFICIAL | Public Evaluation page: laboratory / imaging selection. **Not available in the preliminary round** per the 2026-10-06 briefing |
| DIAGNOSE meaning | CONFIRMED_OFFICIAL | Final diagnosis submission |
| Initial information scope | CONFIRMED_OFFICIAL | Basic patient information and initial symptoms |
| Required observation JSON | PLACEHOLDER | `CompetitionObservation` is our local contract |
| Required action JSON | PLACEHOLDER | `CompetitionAction` is our local contract |
| Per-action payload encoding | PLACEHOLDER | Current key/content/metadata fields are not documented officially |
| case_id semantics | PLACEHOLDER | Local per-case key only |
| turn field semantics | PLACEHOLDER | Local protocol convention only |
| Maximum interactions | CONFIRMED_OFFICIAL | Public Evaluation page: 60 turns. **Superseded for the preliminary round** by the 2026-10-06 briefing: 50 turns (see section below) |
| LLM endpoint and route | NOT_AVAILABLE | `/chat/completions` is a provisional transport assumption |
| Authentication method / token delivery | NOT_AVAILABLE | Rules mention issued API credits/tokens, not header syntax |
| JSON model-selection field | PLACEHOLDER | Current OpenAI-compatible `model` field |
| Preliminary model identifier | CONFIRMED_OFFICIAL | Rules: `openai/gpt-oss-20b` |
| Expected model revision | CONFIRMED_OFFICIAL | Rules: `4d7ae4984b7db7de8f8457170b3f1a419ee76d52` |
| Revision parameter / response field | NOT_AVAILABLE | No request revision parameter is sent |
| Abstention legality | NOT_AVAILABLE | No published INSUFFICIENT_INFORMATION / OOD action found |
| stdout/stderr framing | PLACEHOLDER | JSON-lines stdout and diagnostics stderr are local assumptions |
| ZIP contents | CONFIRMED_OFFICIAL | Evaluation: run.py and requirements.txt |
| ZIP maximum | CONFIRMED_OFFICIAL | Evaluation: 50 MB; local gate conservatively uses < 50,000,000 bytes |
| run.py callable/CLI interface | NOT_AVAILABLE | Filename confirmed, invocation signature unavailable |
| requirements.txt package rules | DOCUMENTED_BUT_AMBIGUOUS | Rules allow open-source libraries; installer/version/platform limits unavailable |
| Submission encoding / language | CONFIRMED_OFFICIAL | Rules: UTF-8 and Python |
| Network boundary | CONFIRMED_OFFICIAL | Submitted inference must not call external APIs/LLMs |
| Fixed-model case call requirement | CONFIRMED_OFFICIAL | Rules: at least one response to a case-containing prompt per case |
| Case isolation | CONFIRMED_OFFICIAL | Other cases' information/predictions/statistics must not influence a case |
| Official starter / submission example | NOT_AVAILABLE | None linked in inspected public pages or returned by targeted search |

No official observation/action contract was found: `OFFICIAL_API = NOT VERIFIED` and
`SCHEMA_STATUS = PLACEHOLDER`. Only the adapter boundary may be updated when that contract arrives.
The stricter local success gate additionally requires parseable structured output. Probe success
is not credited to any case. Fine-tuning or loading adapters for the preliminary fixed model is
prohibited; this submission includes neither learned weights nor training dependencies.

Optional response fields `revision` / `model_revision` are compatibility checks, not confirmed
official field names. If present they must match the expected revision; if absent the result is
`NOT_VERIFIABLE_FROM_RUNTIME`. Server model/revision strings do not attest the actual weights.

## 2026-10-06 organizer briefing (preliminary round) — supplied by the team as slide photos

Source: eleven photographs of the organizer briefing slides given to the team. They are NOT on the
public pages above and carry no machine-readable contract, so the wire encoding stays `PLACEHOLDER`.
Implemented as state flags (`PatientState.preliminary_rules`, ON by default only for the
`competition` provider; `competition.submission_profile` builds an always-ON adapter), never as a
global change, so the development benchmarks keep their behaviour.

| Rule | Status | Implementation / boundary |
| --- | --- | --- |
| 50 turns per case | CONFIRMED_BRIEFING | `PRELIMINARY_MAX_TURNS`; `effective_max_turns()` |
| 20 minutes per case | CONFIRMED_BRIEFING | `PRELIMINARY_CASE_SECONDS`; forced DIAGNOSE with a closing reserve; real latency NOT VERIFIED |
| No TEST action | CONFIRMED_BRIEFING | filtered in action selection and adapter; never emitted |
| Vital signs delivered at the start (turn 0) | CONFIRMED_BRIEFING | `record_initial_vitals`; wire field name is a placeholder |
| Patient statement carries age/sex | CONFIRMED_BRIEFING | `parse_first_statement`; heuristic text parsing |
| SAY: one question, at most 30 characters | CONFIRMED_BRIEFING | `fit_say` guarantees the limit in every language; templates exist for ko/en/ja/zh, other scripts fall back to English |
| EXAM: one maneuver per request | CONFIRMED_BRIEFING | single-maneuver exam text |
| SOAP note on DIAGNOSE with turn numbers; only asked/examined content counts | CONFIRMED_BRIEFING | `nova_agent/soap.py` rebuilt from the turn log; field names PLACEHOLDER |
| At most 8 model calls per case (first, final, every 4th turn) | CONFIRMED_BRIEFING | `PRELIMINARY_MAX_LLM_CALLS_PER_CASE`; verified only against the mock model |
| Closing dialogue (core history, diagnosis SAY, next-step SAY) | CONFIRMED_BRIEFING | adapter `_closing_action` |
| Rejected examination requests | NOT_AVAILABLE | rejection wording unpublished; detected by a documented heuristic (below) |

Open boundaries: real `gpt-oss-20b` latency and call accounting, the JSON encoding of SAY/EXAM/
DIAGNOSE/vitals/SOAP, and how SOAP is scored are all unknown until the participant guide arrives.
Accuracy numbers under these rules are synthetic development results, not an official score.

## Configuration and external blockers

Set these only from the organizer's authorized configuration:

```sh
export NOVA_LLM_PROVIDER=competition
export NOVA_COMPETITION_BASE_URL="<organizer-provided base URL>"
export NOVA_COMPETITION_API_KEY="<organizer-provided token, if required>"
export NOVA_COMPETITION_MODEL=openai/gpt-oss-20b
python scripts/preflight_competition.py
python scripts/smoke_real_llm.py
```

Do not paste real credentials into git, issue comments or logs. An unset URL produces
NOT_CONFIGURED without a network request. A local configured stub can verify wiring but never
establishes official readiness. Nonlocal endpoints must be those authorized by the organizer;
the public documents do not yet provide an allowlist. Redirects are rejected to avoid forwarding
credentials elsewhere. Official schema readiness is not an environment-variable override.

After official documentation arrives: implement its JSON/call interface in `competition/` and
`submission/run.py`, add official-example contract tests, update evidence-backed schema constants,
then re-run preflight and a short case. Mere environment configuration cannot resolve an unknown
wire contract; this remains an explicit external blocker.
