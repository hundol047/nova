# Official N.O.V.A. SDK integration (preliminary round)

Status: **integrated and locally verified; NOT yet executed against the organizer server or the real gpt-oss-20b.**
This session could not reach `nova.snubhai.org` (egress proxy 403) and has no development key, so every server-backed
item below is `NOT EXECUTED`/`BLOCKED`, never claimed.

## Sources and authority

| Source | Used for | Access |
|---|---|---|
| Organizer devkit `nova-devkit` (`nova_sdk.py` 1.0.1, `nova_local.py`, `run.py`, README) | SDK contract, local simulator rules | supplied by the team, inspected 2026-10-12 |
| Organizer slides "run_agent 실행 흐름과 agent 진료 실제 예시" (2026-10-11, real server traces) | prepare/ready/consult timing, rejected-EXAM turn charge, scoring areas, container limits | supplied by the team |
| Public samples C01/C03/C10 | local plumbing checks only (never a runtime answer map) | supplied by the team, not committed |
| Guideline corpus README (recovered from an INCOMPLETE `.crdownload`) | corpus layout, `/opt/nova/guidelines`, licenses | transcribed by the team; the partial file was never used or committed |
| nova.snubhai.org docs / rules | — | **BLOCKED** from this environment; re-check before submitting |

Where the 2026-10-11 server material contradicts older wording (a rejected EXAM "uses no turn"), the newer server
behaviour is implemented: EXAM_NOT_SPECIFIC / EXAM_NOT_RECOGNIZED / server-side CONTENT_TOO_LONG use one turn.

## What changed

| Area | Before (pre-guide) | Now |
|---|---|---|
| `submission/run.py` | exited `NOT READY` via provider_lock | `run_agent(prepare, consult)` with the vendored SDK |
| SDK | none | `submission/nova_sdk.py` = organizer 1.0.1 verbatim (sha256 `c6238ac4…f00d`, test-pinned) |
| Adapter | placeholder schema | `competition/nova_sdk_adapter.py`; `competition/schema.py` stays an internal local-harness format only |
| Timing | fixed 20 min constant | `session["deadline"]` drives the encounter (`PatientState.deadline_unix`); 20 min remains a local-simulation default |
| Rejected EXAM | no turn | one turn (server 2026-10-11); never re-sent; no finding recorded |
| request_id | n/a | one id per logical action, reused on transport loss (API_UNAVAILABLE), new id after server 503 model failures (as the official baseline) |
| Doctor model | internal provider, 8 calls "÷10 cases" | `client.chat` only; hard caps 200 calls / 500k / 100k **per case session**; internal target `NOVA_DOCTOR_CALL_TARGET` (default 16) |
| gpt-oss budgets | 1024 max_tokens | consults 4096 (`medium`), phrasing 1024 (`low`); empty answers (PROVIDER_RESPONSE_INVALID) retried with backoff |
| Record | generic S/O/A/P text | exactly `RECORD_FIELDS` (15 strings) + one-line diagnosis |
| Requirements | `pydantic>=2.6,<3` | exact pins (pydantic 2.14.0 stack; cp312 manylinux wheels verified) |
| Korean inputs | vitals with Korean labels and Korean-word ages were not parsed | `혈압/맥박/호흡/체온/산소포화도` and `서른두 살` parsed |
| EXAM wording | "…해 주세요" requests | one maneuver the doctor performs, ≤30 chars ("심장 청진을 하겠습니다") |
| Guidelines | none | `nova_agent/organizer_guidelines.py`: metadata index of `NOVA_GUIDELINES_DIR` in prepare(), lazy bounded excerpts with title/organization/license/source_url; empty when absent |

## Encounter design

1. `client.session()` → opening, vitals, turns, deadline → `PatientState` (the server returns no history; the
   transcript lives in-process).
2. The deterministic engine chooses each step; every SAY/EXAM is ≤30 NFC characters; English knowledge-base feature
   questions are rephrased into Korean by one low-effort Doctor call (cached per case; failure keeps the original);
   pain-descriptor questions are skipped when nobody has mentioned pain.
3. Doctor follow-up consult (JSON): differential, ≤6 single questions, ≤3 single-maneuver exams (filtered: no
   bundled, lab/imaging, history or record-writing "exams").
4. Final consult with organizer-guideline excerpts and the engine's candidates → main diagnosis, grounded evidence,
   differential, plan. Engine-supported must-not-miss alternatives stay in A.differential; urgency = engine
   disposition OR Doctor.
5. The working diagnosis and the next step are SAID to the patient (two SAY turns) before `client.diagnose`.
6. Record: S and O are rebuilt only from the opening, initial vitals and actual server replies; Doctor "evidence"
   lines survive only if grounded in the transcript; rejected exams contribute nothing.
7. If no case-relevant Doctor call has succeeded, one bounded minimal consult is attempted before submission (a case
   without a Doctor call scores 0); the record is always submitted.

## Verification

| Check | Result |
|---|---|
| `tests/test_official_sdk_adapter.py` (fake server with official semantics) | 27 passed |
| `tests/test_organizer_guidelines.py` (synthetic corpus: KO/EN, catalog, symlink, traversal, malformed) | 5 passed |
| `scripts/smoke_official_http.py` (built ZIP, `python -I run.py`, read-only dir, unwritable HOME, real HTTP via SDK) | PASS |
| `scripts/audit_official_package.py` (≤50 MB, ≤500 MB, ≤5,000 files, root files, no symlink/encryption/traversal/dup, exact pins, secrets) | PASS |
| Organizer devkit `nova_local.Simulator` + **stub** patient/examiner/Doctor on C01/C03/C10 | completed, 0 refusals (plumbing only; stub models) |
| Real gpt-oss-20b / dev-key server samples / sample validation ZIP | **NOT EXECUTED** (no network, no key) |
| Chat-policy benchmark (8/12/16/24) | **NOT EXECUTED** (needs the real model); target is configurable |

To run the server-backed samples on a machine with access: `NOVA_API_BASE=… NOVA_DEV_KEY=… python
scripts/run_dev_samples.py C01 C03 C10`. Do not start leaderboard evaluation before sample validation is healthy.

## Licensing

The organizer corpus is used only at runtime from the read-only mount; nothing from it (text, translations,
summaries, indexes) is stored in this repository or the submission. Excerpts live only in one encounter's memory with
their license and source. Existing knowledge-base provenance is unchanged by the existence of the corpus.

## Release record (v32)

`artifacts/verification/local-release-f383b2e-v32.json` binds runtime `f383b2e` to the audited archive (members pinned
by hash; ZIP kept local). Full suite (CI exclusions): py3.12 2576 passed / 0 failed / 1 skipped, py3.11 identical.
Round M (synthetic, mock engine) unchanged from v31: Top1 0.9837, Top3 1.0, critical Top1 1.0 (123 scored).
Status stays `NOT READY` / official API and real model `NOT VERIFIED` until the dev-key samples are run.
