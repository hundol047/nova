# Independent official-path audit — 2026-10-12

START_REMOTE_HEAD: `26091a2a4642ffeefb0836d6483dfeb160435109`.
Target: `offline/nova-competition-agent-optimization`; main is unchanged.

**LOCAL VERIFICATION ONLY — NOT OFFICIALLY READY. Real GPT-OSS, participant-key samples,
sample-validation uploads and leaderboard evaluation were NOT EXECUTED BY CODEX.**

## Authority and credentials

The supplied `nova-devkit.zip`, `nova-samples-2026.zip` and organizer presentation
dated 2026-10-11 were inspected. The supplied SDK 1.0.1 and `submission/nova_sdk.py`
have identical bytes: SHA256 `c6238ac466abc5b99b3e80de9ace2c7a54b51f7efc8d8a671d1c08bb0476f00d`.
The organizer SDK was not modified.

Public `/docs/` and `/rules/` requests were attempted on 2026-10-12 and blocked
by the environment egress proxy (CONNECT 403). Current public rules and a newer
public starter download therefore could not be independently checked. Contract
claims below are bounded to the supplied organizer SDK and presentation.
The incomplete `.crdownload` was not used: the user's audit instructions explicitly
forbid it, and its upload exceeds the executor's 32 MiB transfer limit.

The supplied devkit README still contains an older zero-turn rejected-EXAM sentence;
its executable simulator and the newer server presentation charge one turn. The
one-turn implementation was preserved. Preparation is 10 minutes; the encounter
is 30 minutes, 50 SAY/EXAM turns, and 30 NFC characters per action. The SDK record
has exactly 15 string fields and a separate primary diagnosis. No TEST is sent.

The user's explicit prohibition on using development keys in coding tools was
followed. No participant key was requested, used, logged, committed, or injected
into CI. Synthetic local server tokens are fixture data, not participant tokens.

## Reproduced defects and fixes

| Defect | Before | Fix / regression evidence |
|---|---|---|
| Assessment grounding | 10mg→40mg, left→right and present→not-present claims passed the 60% overlap guard | One observed assertion must agree in numbers, units, dose anchor, frequency, polarity, laterality and family scope; S/O still use raw observed replies |
| Last diagnostic fallback | `_minimal_consult()` ran after the note and diagnosis had been built | Last diagnostic attempt precedes arbitration, explanation and record construction; its accepted result is used |
| Phrasing hid diagnostic failures | A successful translation satisfied the only case-chat counter | Separate phrasing and parsed diagnostic-response counters; a bounded diagnostic fallback is attempted when no diagnostic response succeeded and resources permit |
| Unsupported Doctor primary | Arbitrary text such as an instruction became the final diagnosis | Normalize labels; preserve same-diagnosis aliases and supported Doctor corrections; reject unsupported/unmapped overrides of the working diagnosis; a rejected primary cannot still dictate its plan |
| Follow-up classification | Medication dose answers were placed under associated symptoms/HPI | Typed categories plus general English/Korean question classification retain medication/allergy/PMH/FH/SH in their sections |
| Duplicate follow-up | Repeated questions/exams within one Doctor response could spend multiple turns | Deduplicate proposed and attempted actions per encounter |
| Plan fallback | Treatment text was copied into both treatment and disposition | Separate conservative treatment fallback and the existing engine's urgent/routine disposition |
| Time and budgets | SDK timeout could consume submission headroom; zero remaining turns became 50; unknown transport usage was not reserved | Bounded SDK timeout without modifying SDK, zero-turn preservation, output-request clamps and conservative reservations for unresolved requests; idempotent DIAGNOSE retry uses submission-specific headroom |
| Malformed Doctor fields | Non-list questions/evidence/differential could raise exceptions | Validate collection types and preserve a submit-able engine record |
| Legacy provider contamination | `NOVA_LLM_PROVIDER=anthropic` caused `RealLLMUnavailableError` before record submission despite SDK Doctor calls | Official entry/prepare/run force the internal deterministic engine mode; actual Doctor calls remain exclusively `client.chat` |
| Guideline bounds | Document cap broke across directories; intermediate symlinks could enter the catalog; CSV collection ignored time budget | Cross-directory document/time caps, symlink rejection, bounded metadata and at most 128 index terms per document |
| Human-run script | Execution from coding tools and arbitrary response serialization were not guarded | Refuse known agent/CI environments before reading a key, require human acknowledgement, redact output, and keep results outside the checkout |

Tests: `tests/test_official_independent_audit.py`, existing SDK/guideline tests.
Normalizing a Doctor diagnosis is not clinical validation. A correction needs
positive case-specific profile support and a grounded evidence statement. Novel
unmapped diagnoses remain hypotheses rather than silently replacing a supported
engine diagnosis; this is a conservative tradeoff requiring real-model review.
Strict grounding can omit legitimate derived/translated paraphrases; raw S/O and
fallback quoted replies are retained, rather than treating inference as observation.

The regression locations are explicit: `official_evidence.grounded_in` is covered
by `test_evidence_preserves_numbers_polarity_and_laterality`; `OfficialEncounter.chat`
by the phrasing/garbage-JSON and input/output-budget tests; `run` by the last-chance,
legacy-provider and zero-turn tests; `_validated_primary` by unsupported-primary
and supported-correction tests; `_followup_phase` by the medication-retention test;
`_engine_plan` by the treatment/disposition test; `_call` by lost-DIAGNOSE replay;
`build_index` by the cross-directory and intermediate-symlink tests; and
`require_human_run` by the agent-environment guard test. The before/after assertion
examples are saved under `artifacts/independent_official_audit/local/`.

The diagnostic-response counter is a structural response check, not proof of
medical correctness. A parsed diagnosis or nonempty diagnostic task list counts;
the separate primary arbitration and evidence guards govern the actual record.
Synthetic counter success must never be reported as meaningful live-model success.

## Correct behavior preserved

`submission/run.py -> nova_sdk.run_agent -> prepare -> ready -> consult -> session
-> client.chat / SAY / EXAM -> patient explanation -> diagnose` remains the official
path. Preparation makes no patient request. No old wire schema or provider lock
reaches the SDK server. The transcript, request IDs and Doctor statistics are
encounter-local. Transport replays reuse an ID; provider retries use a new ID.
Rejected exams supply no findings and are not sent again. The engine's supported
dangerous alternatives remain visible. The actual Doctor model is selected by
the organizer server; declaring its revision is not proof of a live revision.

Official hard caps are 200 calls / 500k input / 100k output tokens per case.
Local reservations conservatively bound sent requests; the server remains the
authority for exact token accounting. Internal call targets are engineering policy,
not an additional organizer rule. Missing/malformed deadlines use a bounded local
30-minute fallback and are logged; valid server deadlines take precedence.

Guidelines are loaded from `NOVA_GUIDELINES_DIR` only at runtime. No corpus download,
protected text, derived summaries or weights are packaged. Excerpts stay in encounter
memory with source URL and license. Real corpus retrieval quality is NOT VERIFIED;
synthetic path, bounds and retrieval tests do not establish clinical relevance.
Preparation caps index collection at 240 seconds and 30,000 documents, with at
most 128 title/path terms per document. It does not read entire bodies into an
index; retrieval reads bounded excerpts. Root/intermediate symlinks and traversal
are rejected. This is a memory bound by construction and synthetic regression,
not an 8 GB measurement with the organizer's full corpus.

EXAM rejection charges one turn without adding objective findings. Attempted
maneuvers, including refusals, are remembered only inside the current encounter.
Actions are NFC-normalized and checked against the 30-character bound before
transmission; each accepted proposed EXAM is one maneuver. Unsupported EXAM
templates fall back to other available information rather than TEST.

## Final validation evidence

Final results, interpreter versions, exact command outcomes, benchmark comparison,
ZIP member hashes and fresh-container results are recorded in the verification
artifact referenced by `artifacts/verification/CURRENT_RELEASE.json` after completion.
Historical records are preserved. The single release-binding test is run after
the new runtime commit and record exist; it is not waived or counted as passed
before that stage. Additional repository CI is triggered by the ordinary target
branch push; no competition credentials are added.

The official grading rubric includes information collection, diagnostic reasoning,
tests/follow-up, safety, communication and efficiency. Mock Top-1 accuracy is not
the official 100-point competition score. Uploaded reference records are examples,
not scoring oracles, and are never production answer maps.

Fresh final-source functional checks passed: official package limits/secret scan,
repository package scan, source/mirror equivalence, fake official HTTP smoke,
fresh-directory package smoke, adversarial checks and 3-run/4-case stability
(100% diagnosis and action-sequence agreement). The final runtime is
`ea0decf` (resolve the full SHA through the current verification record).
Rebuilding twice at this runtime produced the same ZIP SHA256:
`14e34a4629e252da9089689b13842921b384eabfec7355cd52f3ebfe3a14a0e8`.
ZIP: 887,744 bytes; uncompressed: 3,381,816 bytes; 107 members including manifest.

All five exact runtime pins were downloaded as binary-only CPython 3.12
manylinux x86_64 wheels. A `python:3.12-slim` container installed them using
`--no-index --find-links`; the final archive then passed fake HTTP smoke under
`--network none --read-only --cpus 2 --memory 8g`, dropped capabilities and a
256 MB writable `/tmp`. The fake server runs on loopback inside that container:
22 turns, 5 fake Doctor responses, 2 parsed diagnostic responses, 3 phrasing
responses, zero TEST, maximum 25 action characters and all 15 record fields.
This establishes package/transport behavior, not real GPT-OSS execution.

The supplied official simulator separately completed C01/C03/C10 with explicitly
named deterministic Doctor/patient stubs and a child environment without inherited
credentials: 15/15/18 turns, two Doctor calls each, and 15 record fields each.
No sample-specific production logic was added. These are plumbing checks with
unknown/generic stub answers; no clinical score is assigned to these results.

Known limits remain: strict grounding and mapped-primary arbitration need real
model review; true novel diagnoses can be rejected; actual guideline retrieval
and model revision are unverified; source-license permission remains BLOCKED.
The previous closing-set spot review also exposed a hypoglycemia urgency omission
and an asthma-to-PE error. The deterministic clinical engine was preserved here;
these are unresolved clinical review items, not fixes claimed by this SDK audit.
No fresh final blind set was authored or run, and no 95/100 or official score is
claimed. Current public docs and hosted CI results could not be checked through
the proxy; Git fetch/push access is separate from that blocked HTTP access.

Reusable cloud installation/start instructions were refreshed in the environment
draft, including production test dependencies and the HUMAN-RUN ONLY boundary.
Public `nova.snubhai.org` and `api.github.com` domain requirements are saved;
no secret requirement was added. The draft is saved, not applied/published.
Review, save and publish it in environment settings for future-task reuse.

### Completed test and benchmark results

| Interpreter | Passed | Failed | Skipped |
|---|---:|---:|---:|
| CPython 3.11.16 / pydantic 2.14.0 | 2,688 | 0 | 1 |
| CPython 3.12.14 / pydantic 2.14.0 | 2,688 | 0 | 1 |

These are unique test totals from the full suites plus the deferred release-binding
test. Python 3.11 initially skipped the ZIP-content test in its isolated source
copy because no ZIP had been built there; that test was subsequently executed
against the final ZIP and passed. The only remaining skip on either interpreter
is optional Torch training (`IMPLEMENTED_BUT_NOT_EXECUTED`). It is outside the
competition runtime. Consolidated JUnit hashes, original full-run hashes and skip
reasons are in `artifacts/independent_official_audit/local/test_summary.json`.
The new source/commit/mirror/archive binding passed on both interpreters.

The completed preliminary-only benchmark ran 230 development cases (222 scored),
with 85 critical scored cases: Top-1 219/222 = 98.6486%; Top-3/5 220/222 = 99.0991%;
critical recall 85/85 = 100%, critical miss 0; mean interactions 19.6435; exact
duplicate-action rate 0; SOAP retention/completeness 100%; unsupported-information
rate 0; rule violations 0; all gates passed. Every per-case row and every suite
summary equals the independently rerun baseline, so there is no measured clinical
engine regression. These are the legacy preliminary simulation harness's metrics,
not real Doctor/SOAP scoring. Semantic duplicate-question rate is 0.6342%, premature
diagnosis rate 0.8696%, and unresolved-critical-alternative rate 55.6522% under its
heuristic definition; the high latter value requires clinical interpretation.

The v33 Round M evidence is derived from the completed 128-case preliminary-only
subset (123 scored, 43 critical), not from the historical TEST-enabled trace
harness: Top-1 121/123 = 98.3740%, Top-3/5 122/123 = 99.1870%, critical recall
43/43 = 100%. Two scored misses are preserved in the failure artifact without
inventing causal attribution. An extra TEST-enabled detailed trace was started,
then interrupted and discarded from completion evidence; it is not counted as
a passing run. Both the complete subset and full development comparison are
committed under `artifacts/independent_official_audit/`. No blind cases were run.

Leakage scan: 807 reference cases / 16 modules / 170 core files, no obvious leakage
detected. The scan is a heuristic, not a guarantee. Provenance inventory coverage
passed; permission status remains BLOCKED. The ordinary offline-branch push triggers
the repository workflow, including its independent backend/frontend/database jobs.
Hosted CI results remain NOT VERIFIED because GitHub API access is blocked; no
competition key is added. Historical v32 and older verification records are intact.

## Human-run next step (own computer only)

Do not run these commands from Codex, Claude Code, Cursor or a CI environment.
Use the API origin from the current participant guide. Do not paste a key into
chat or save it in a repository file. Three server-backed samples incur team credit.

### Bash

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-nova.txt
read -r -p 'Official API origin URL: ' NOVA_API_BASE
read -r -s -p 'Development key (hidden): ' NOVA_DEV_KEY
export NOVA_API_BASE NOVA_DEV_KEY
python scripts/run_dev_samples.py --human-run C01 C03 C10 --output "$HOME/nova-sample-results"
unset NOVA_DEV_KEY
```

### PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-nova.txt
$env:NOVA_API_BASE = Read-Host 'Official API origin URL'
$secure = Read-Host 'Development key' -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
  $env:NOVA_DEV_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
  python scripts/run_dev_samples.py --human-run C01 C03 C10 --output "$HOME/nova-sample-results"
} finally {
  Remove-Item Env:NOVA_DEV_KEY -ErrorAction SilentlyContinue
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
}
```

Inspect real Doctor counters, numeric/medication retention, EXAM refusals, completed
records and latency before human-run ZIP sample validation. Leaderboard evaluation
was not performed. SDK integration and fake-server success are not official readiness.
