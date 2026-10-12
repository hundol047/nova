# Human-run official verification preparation — 2026-10-12 (KST)

**LOCAL VERIFICATION ONLY / NOT OFFICIALLY READY.** This report prepares official public sample testing on a human's own computer. Codex did not access participant credentials, call the real Doctor, create official sample sessions, upload a package or run a leaderboard evaluation. No official/private score is claimed. See `artifacts/verification/CURRENT_RELEASE.json` for the verified runtime commit and exact archive members; the ZIP remains local.

## Current public contract and repository baseline

Accessed the public [development guide](https://nova.snubhai.org/docs/), [rules](https://nova.snubhai.org/rules/) and [Q&A](https://nova.snubhai.org/qna/) on 2026-10-12 KST. Retrieval hashes and contract differences are in `artifacts/human_release_preparation/current_public_docs.json`.

Starting remote/local HEAD: `1b19a700fd5679b9422a2e8820f5675551ab432c`, branch `offline/nova-competition-agent-optimization`. Explicitly fetched this branch because the default fetch refspec did not refresh its tracking ref. Changes from the previously verified runtime `ea0decf2e0e0c955d26cba6b05ffb49b6de52e32` to the starting HEAD were documentation and evidence only; runtime bytes matched that verification. Earlier changes since `26091a2a4642ffeefb0836d6483dfeb160435109` were reviewed through the previous independent audit and source differences. This release changes actual runtime bytes and records a new v34 verification; older records remain historical.

Current docs **and rules now both say** `EXAM_NOT_SPECIFIC` and `EXAM_NOT_RECOGNIZED` consume one turn. They agree with the supplied 2026-10-11 server-trace presentation. Older zero-turn claims are superseded. The harness still measures natural current server before/after turn values rather than asserting that documentation equals a new server observation. It sends no deliberately invalid probe actions.

The public SDK in [starter.zip](https://nova.snubhai.org/docs/starter.zip) is version **1.0.1**, SHA256 **`fdd65302e82791ed862c22fe5a014ef443ab331d8986ec7c72b3923add6bc871`**. Vendored `submission/nova_sdk.py` matches it byte for byte. Compared with the previously supplied SDK, only the default client timeout changed **120 → 240 seconds**, despite the unchanged version string. The adapter follows 240 seconds while preserving the encounter deadline and submission reserve.

Current preliminary contract: 50 turns, 30 NFC code points per SAY/EXAM, no TEST, 30 minutes per encounter, 10-minute prepare, 200 Doctor calls, 500,000 input and 100,000 output tokens. Package limits are exactly 50,000,000 compressed bytes, 500,000,000 uncompressed bytes and 5,000 files. The old auditor's binary-MB allowance was tightened to the documented decimal limit. O.tests stays empty in preliminary records. Recorded EXAM findings include the actual server turn if returned. The synthetic preliminary benchmark still embeds historical organizer-assumption labels; it does not simulate current wall-clock limits or establish the official server contract.

Public sample IDs may be UUIDs. `--list` plus explicit `--case-id C01=published-id` mapping replaces the assumption that `C01` itself is always a valid server ID. Mapping is chosen by the human from the public list; runtime inference contains no public-case answer map. API origin is `https://nova.snubhai.org`.

## Confirmed fixes and limits

- SOAP grounding previously accepted four reproduced contradictions: opposite polarity in a conjunction, mg/L versus mg/dL, g/L versus g/dL, and mother versus father. Clause-local assertion matching, compound-unit preservation and relative-role matching now reject them. Question text remains context, and unknown/no answers cannot become positive observations. Existing numeric dose, laterality, frequency and duration guards remain. This is conservative lexical grounding, not comprehensive semantic or clinical adjudication.
- Malformed Doctor task lists containing numbers/null/empty dictionaries no longer satisfy the successful diagnostic-response shape gate. Phrasing, diagnostic reasoning and actual applied effects have separate counters. Structural JSON success does not establish clinical usefulness.
- Optional per-request telemetry cannot interrupt DIAGNOSE if an observer fails. The harness reports capture failures, physical retry attempts, actual usage/model/finish reason, action content, notes/digests, turn values and ranking changes. Request/session identifiers, headers, prompts and hidden reasoning traces are omitted or redacted.
- Retrieved guideline text is structured as untrusted `GUIDELINE_REFERENCE_DATA`, separate from patient evidence, engine differential and instructions. An instruction-like fixture cannot directly provide an unsupported final primary. Real-model injection resistance remains untested.
- Sixteen new development counterfactuals cover measured/suspected hypoglycemia, historical/family/other-analyte/normal/resolved controls, asthma, PE with wheeze and dangerous vital signs. The same frozen fixture improved **11/16 → 16/16** by repairing five hypoglycemia urgency omissions. Current glucose must be actual unambiguous supplied mg/dL evidence; no lab is invented. Suspected hypoglycemia requires supported acute symptoms plus glucose-lowering medication context. The new asthma/PE controls already passed before the change, so no case-specific ranking patch was made. These tests were authored with code access and are not blind clinical validation. Some inherited differential/disposition behavior remains imperfect; passing these assertions does not establish overall false-positive control.
- Doctor budgets/token caps/effort were not tuned from fixture latency. Real latency, token use and A/I/K clinical annotations are needed for policy changes. Existing defaults remain a 16-call soft target, 4,096 consult tokens and 1,024 phrasing tokens, with the configured reasoning effort.

New tests and the existing official SDK/adversarial audit suites exercise retry replay, deadline fallback, last-chance ordering, primary arbitration, malformed lists, duplicate actions, category mapping and record safety. Test environment restoration is explicit: fake encounters set competition-only process settings that must not leak into later development tests.

## Full public guideline audit

Downloaded [the public corpus](https://nova.snubhai.org/downloads/nova-guidelines-2026.zip) to a scratch directory. Verified SHA256 **`ef58c2f4369750af382f2706dcc1c9c7a85e3a93c261d880f7470d695eaf30d5` before extraction/use**. The corpus is not committed or packaged; no corpus excerpts, document summaries or full texts are in the audit outputs.

| Measurement | Result |
|---|---:|
| Documents / English / Korean | 15,904 / 14,398 / 1,506 |
| Skipped / missing source URL / missing license metadata | 0 / 0 / 0 |
| Index build | 2.566 seconds |
| Peak RSS, fresh local evaluation process | 55,024 KiB (~53.7 MiB) |
| Terms / postings | 33,761 / 212,831 |
| Query median / p95 | 0.955 / 3.310 ms |
| Generic query count | 36 (12 English, 12 Korean, 12 mixed) |
| Topical hit@3 before → after | 80.56% → 100% |
| Topical hit@5 before → after | 88.89% → 100% |
| First topical reciprocal-rank mean after | 0.9861 |

The requested Recall@3/5 labels are explicitly **topical metadata proxies**, not exhaustive document recall, clinician-rated relevance or real Doctor benefit. Expected topics were declared before the final measurements; general bilingual synonym expansion and title/filename/organization/type ranking were improved against those development queries. Fresh unseen queries and human medical review remain necessary. Fixes also preserve the official Korean `출처 URL` column: previously all 15,904 source URLs were blank despite being present in the catalog. Body excerpts are bounded and transient. The Docker preflight separately tests actual packaged prepare against the complete read-only corpus under 2 CPUs/8 GB; its measured figures are reported in final local checks.

Evidence: `artifacts/human_release_preparation/rag-before.json`, `rag-after.json`, and `evaluation/official_rag_queries.json`. Reproduce without credentials:

```bash
python scripts/evaluate_official_rag.py --corpus-root /absolute/path/guidelines \
  --source-zip /absolute/path/nova-guidelines-2026.zip --output /tmp/nova-rag-audit.json
```

## Provenance remains a separate submission blocker

`artifacts/compliance_hardening/clinical_asset_inventory.json` inventories 96 nova_agent assets: **3 verified, 90 unresolved, 3 optional snapshots not used**. The additional `runtime_asset_classification.json` classifies **every ZIP member**: B=3 licensed references, C=1 organizer SDK, D=2 build/dependency metadata, E=101 unresolved inherited code/data/document assets, A=0 substantiated original-team authorship. B assets are also reproducibly generated (D) but primary counts avoid double counting. The 15,904-document organizer corpus is external C, never redistributed in the package. Five pinned dependencies have actual wheel MIT license texts and extraction hashes; they are installed separately, not embedded as runtime package members.

DOID features were reproduced from the actual CC0 publisher file with the recorded source hash. Licensed references reproduced byte-identically from the retained permitted field snapshot; original live publishers were not newly authenticated. Current MONDO publisher bytes had changed. The current CC BY 4.0 source reproduces all **518 synonym entries exactly**; runtime provenance metadata was rebuilt with the actual new source hash, rather than claiming the old publisher bytes were downloaded. Source/license/rebuild receipts are committed as metadata only.

For each E member, the classification records history/source/license/transformation searches, unavailable licensed inputs, replacement limits and exclusion impact. No historical generation prompt/model/date was invented. Staging removal of all 101 E members in a separate temporary candidate makes the encounter runtime fail import; accuracy cannot responsibly be compared for an unrunnable package. Important assets were retained in the local candidate with **permission BLOCKED**. Substantiated original ownership/licensing records or a separately validated licensed replacement are required; a Git commit or engineering test cannot establish redistribution rights. This is why `READY_FOR_HUMAN_SAMPLE_VALIDATION` remains **NO** even if every technical preflight check passes.

## Human-run workflow — own computer only

Do not run these authenticated commands inside Codex, Claude Code, Cursor or CI. The harness refuses known agent/CI markers **before any key lookup**. Keep the key solely on your own computer. No key should be pasted into an agent conversation. These commands are preparation instructions; none were executed by Codex with credentials.

1. Check out the target branch and install Python 3.12 runtime requirements. The final verification pointer must match source and mirror files. Use a fresh output directory outside the checkout.
2. Optionally download the public corpus on your computer, verify its SHA256 before extraction, and set `NOVA_GUIDELINES_DIR` to the extracted `guidelines` directory. The human runner reads the same optional mounted corpus as the packaged runtime. Without it, report RAG unavailable rather than claiming full-corpus runtime use.

```bash
curl -fL https://nova.snubhai.org/downloads/nova-guidelines-2026.zip -o /tmp/nova-guidelines-2026.zip
printf '%s  %s\n' ef58c2f4369750af382f2706dcc1c9c7a85e3a93c261d880f7470d695eaf30d5 /tmp/nova-guidelines-2026.zip | sha256sum -c -
unzip /tmp/nova-guidelines-2026.zip -d /tmp/nova-guideline-corpus
export NOVA_GUIDELINES_DIR=/tmp/nova-guideline-corpus/guidelines
python scripts/pre_sample_validation.py --output-dir /tmp/nova-local-preflight --corpus-root "$NOVA_GUIDELINES_DIR"
```

Preflight has no credentials or upload capability. It builds using the verified runtime commit timestamp, checks SDK bytes, exact pins, package/secret/source sync and evaluation leakage, fake HTTP and fresh-directory operation, offline wheel installation and Docker resource/read-only execution. Docker is needed for the resource gate. **Exit 2 is expected while provenance is BLOCKED**; inspect `LOCAL_TECHNICAL_CHECKS`, individual checks and blockers. Never treat a technical failure as the license-only block. Resolve rights before official submission/sample-validation upload.

3. On your own terminal, set the documented API origin and enter your own key without echo or command-line arguments. List public IDs, then replace the three ID placeholders below using that list. The public alias mapping is metadata for session selection, never an inference answer map.

```bash
export NOVA_API_BASE=https://nova.snubhai.org
read -rs -p 'Development API key: ' NOVA_DEV_KEY
export NOVA_DEV_KEY
python scripts/run_dev_samples.py --human-run --list
python scripts/run_dev_samples.py --human-run C01 C03 C10 \
  --case-id C01=PUBLIC_ID_FROM_LIST \
  --case-id C03=PUBLIC_ID_FROM_LIST \
  --case-id C10=PUBLIC_ID_FROM_LIST \
  --output "$HOME/nova-public-sample-results"
unset NOVA_DEV_KEY
```

The runner verifies the current recorded source, SDK and every archive member before key access. It executes the packaged encounter, snapshots current server turn/remaining values around natural requests, and separates monitoring overhead from API latency. Failed monitoring is explicit. Missing token usage is unknown, never zero. Zero natural EXAM rejections means no rejected-turn measurement, not proof that failures cost zero. Capture failure means the observation gate fails even when DIAGNOSE succeeded.

4. Analyze outside the checkout with no credentials, optionally add manual per-call A–M clinical annotations, then import only seven allowlisted analytical summaries:

```bash
python scripts/analyze_official_samples.py "$HOME/nova-public-sample-results" --output /tmp/nova-public-analysis.json
python scripts/import_human_official_results.py "$HOME/nova-public-sample-results"
# If reviewed annotations exist, add: --annotations /absolute/path/annotations.json
```

Annotations format: `{"C01":{"1":{"A":true,"I":false,"K":false}}}` (case alias → Doctor request number → reviewed A–M booleans). Useful-response rate remains null without complete A/I/K review. Automated clinical categories are marked manual-review required; lexical field/topic checks are not medical adjudication. The importer rejects FIXTURE mode, keeps raw files outside the repository, scans all summaries before writing, and labels origin **HUMAN-RUN OFFICIAL PUBLIC SAMPLE / user-supplied claim, not independently authenticated**. No private-evaluation claim is possible.

5. Only after rights and technical readiness are resolved, a human may visit the documented [submissions UI](https://nova.snubhai.org/submissions/), upload `submission/submission.zip` and choose **샘플 검증**. No upload API or CLI has been invented. Keep this separate from public development samples and leaderboard evaluation.

## Analysis acceptance and files to return

Posthoc public references C01 sedative-hypnotic use disorder, C03 constitutional growth delay, and C10 Graves hyperthyroidism exist only in the analyzer. It checks requested history/exam topic coverage and exact SOAP reply retention while leaving clinical correctness to a reviewer. It does not add them to production inference. Request-level categories A–M cover useful discriminators, redundancy, irrelevance, malformed output, hallucination, unsafe advice, broad questions, invalid EXAM, supported corrections, unsupported overrides, guideline usefulness, injection susceptibility and empty/truncated responses.

Return these **seven analytical JSONs** from `artifacts/human_official_review/`: `official_sample_summary.json`, `doctor_quality.json`, `latency_tokens.json`, `exam_metrics.json`, `record_grounding.json`, `model_identity.json`, `rag_metrics.json`; also return reviewed annotation JSON if available. For clinical response review, separately return redacted C01/C03/C10 files after inspecting them for identifiers/secrets. Do not return keys, environment dumps, headers, raw prompts, guideline excerpts or hidden reasoning traces.

Actual returned model ID, organizer-declared revision and actual exposed revision are separate evidence. Expected model is `openai/gpt-oss-20b`; declared revision is `4d7ae4984b7db7de8f8457170b3f1a419ee76d52`. Unless the runtime response exposes a real revision, record **NOT EXPOSED / NOT DIRECTLY VERIFIED**. Comparing a config constant is not verification.

Real GPT-OSS, all three official server samples and official sample-validation upload: **NOT EXECUTED BY CODEX**. Real Doctor usefulness, server latency/tokens, natural rejection semantics, public-case success, medical RAG usefulness and clinical generalization remain awaiting human evidence. Final local results follow.


## Final measured local checks

Verified runtime commit: `b8cb431f6840f5431ee855b597bce9125d30bb22`. Evidence pointer: `artifacts/verification/CURRENT_RELEASE.json`, schema v34. Two full interpreter suites passed **2,723 tests each**, with only the release-binding test deferred and Torch skipped. That one binding check subsequently passed under both interpreters against the new v34 record. Consolidated totals: **Python 3.11: 2,724 passed / 0 failed / 1 skipped; Python 3.12: 2,724 passed / 0 failed / 1 skipped; 0 tests left deselected**. New fixture isolation and licensed-reference checks passed 44/44; final record/document/provenance checks passed 16/16. These supplementary overlaps are not added to the full-suite totals. Dependency `pip check` passed.

The complete 230-case synthetic preliminary benchmark remains **219/222 Top1 (98.65%), 220/222 Top3/Top5 (99.10%), critical 85/85, SOAP retention 100%, unsupported information 0, rule violations 0**, average 19.643 interactions. Paired comparison found **0 new wrong answers / 0 new critical misses**. Round M's complete 128 cases / 123 scored are derived from this same preliminary-only run; its two wrong scored primaries remain documented with attribution NOT ADJUDICATED. No TEST-enabled result is presented as preliminary performance.

Final ZIP: **891,779 bytes**, 107 files, SHA256 **`72c6fb5ebd3d6a4033ff7aada540bb03308b182fd3ce7ab015f79188241f2f17`**. Official decimal size/path/encoding/entry/pin checks pass. No corpus, evaluation cases, model weights, secrets or runtime training operations are bundled; source/mirror/archive bytes match. Five binary CPython 3.12 / manylinux-compatible wheels install offline; their hashes were checked against current public PyPI metadata. Leakage scan compared 807 reference cases across 16 modules with 170 agent-core files and found no obvious leakage (a static scan cannot establish all possible semantic leakage).

The actual final preflight passes **all 12 technical checks**, including offline, read-only, no-network Docker under 2 CPUs/8 GB and complete-corpus packaged prepare. Initial full-corpus Docker validation exposed scratch extraction permissions (0700/0600); only the public extracted scratch corpus was made readable, and the complete final preflight was rerun. Repository/runtime bytes were not changed by that correction. The final ZIP is built using SOURCE_DATE_EPOCH from the verified runtime commit, and the record pins this audited archive including its normalized manifest metadata. Both interpreter release checks and the exact human-run staging check were rerun after archive binding. The preflight exits 2 solely because inherited source/license rights remain BLOCKED: **LOCAL_TECHNICAL_CHECKS=PASS; READY_FOR_HUMAN_SAMPLE_VALIDATION=NO**. Actual server authentication, real Doctor calls, public sample encounters and sample-validation upload remain unexecuted.

Packaged full-corpus Docker prepare: index build **2.823 seconds**, peak process RSS **65216 KiB**, documents **15904**. This includes package/engine preparation rather than only the standalone index; fake-server latencies are not real-model latency evidence.
