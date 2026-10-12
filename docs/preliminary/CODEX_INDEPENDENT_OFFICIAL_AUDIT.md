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
