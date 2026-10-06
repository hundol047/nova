# Preliminary round -- fixed-LLM pipeline: rule -> evidence

Rules quoted from the organizers' briefing text supplied by the team (2026-10-06). "Evidence" means something
that runs in this repository; "NOT VERIFIED" means it cannot be shown without the official interface/credentials.

| Rule | Status | Evidence / limit |
| --- | --- | --- |
| Fixed model `openai/gpt-oss-20b`, revision `4d7ae498...` | CONFIGURED, NOT VERIFIED | `EXPECTED_COMPETITION_MODEL/REVISION` in `nova_agent/config.py`; `CompetitionLLMClient` rejects another model name and a mismatching reported revision; the weights themselves cannot be attested from the client |
| Model is prepared on the server; no model file submitted | MET | ZIP validator: no weights/checkpoints, `requirements.txt` = `pydantic` only |
| No fine-tuning / adapters / weights loaded or submitted | MET | no training code in the ZIP (`learning/` excluded; `tests/test_submission_excludes_learning.py`, `tests/test_learning_eval_isolation.py`); `ml_ranker_enabled`/`ml_model_path` make `provider_lock` refuse |
| No extra embedding model supplied; own index must run on CPU/RAM in time | MET | retrieval is lexical/rule based (`nova_agent/retrieval_pipeline.py`); no torch |
| At least one NORMAL fixed-LLM call per case, with the case's information in the prompt | MET against a local stub; NOT VERIFIED on the real model | `build_reasoning_prompt` carries the case summary; first call of a case is mandatory (`_preliminary_llm_call_due`); `RealLLMUnavailableError` instead of a fallback-only DIAGNOSE; `tests/test_fixed_llm_usage_and_isolation.py` |
| Post-processing / rule-based correction of model output allowed | USED | `SafetyValidator`, deterministic differential, abstention guards |
| Model-call and token limits per session (200 calls, 500k input, 100k output per the slides) | ACCOUNTED, NOT VERIFIED | every HTTP request incl. retries is counted (`state.llm_http_attempts`); tokens are server-reported, else estimated and flagged (`llm_tokens_estimated`) |
| 8 requests per case | INTERNAL operating policy, NOT an organizer limit | `PRELIMINARY_MAX_LLM_CALLS_PER_CASE` (+ per-case token ceilings); sized so 10 cases stay inside the session caps; fixed per case, never derived from other cases |
| No external LLM / external API from the submitted inference code | MET by construction | only `nova_agent/llm_client.py` opens a connection and `CompetitionLLMClient` talks to the configured organizer URL only (no redirects); `test_no_network_calls_outside_the_llm_client` |
| External data/models/tools: research-publishable licence, source cited | PARTLY MET | NLM/Orphanet references (attributed), opt-in DO (CC0) and Mondo (CC BY 4.0) synonyms; the repository's own clinical heuristics are `UNRESOLVED` in the inventory and block submission eligibility |
| Self-labelling / LLM-made labels need code, prompt, model version and the label data | NOT MET for history | `clinical_asset_inventory.json` records generation fields as `UNRESOLVED` where the historical prompt/model record does not exist; nothing is back-filled |
| Cases independent: no information, prediction or statistic from another case | MET | per-case `PatientState`; budgets are fixed per case; `test_cases_do_not_influence_each_other`; the adapter drops a case's state on completion |
| No learning / tuning on private evaluation cases | MET | no write path from case data to knowledge files; scripts under `scripts/` are never imported at run time |
| Winners reproducible from provided + submitted material | PARTLY MET | deterministic build and tests; sidecar builders are scripted; historical clinical-text provenance is unrecorded (see above) |

## Connecting the real fixed model (needs organizer-provided material)

Set outside Git and never print them: `NOVA_LLM_PROVIDER=competition`, `NOVA_COMPETITION_BASE_URL`,
`NOVA_COMPETITION_API_KEY`, `NOVA_COMPETITION_MODEL=openai/gpt-oss-20b`. Then `python scripts/preflight_competition.py`
and `python scripts/smoke_real_llm.py`. The transport is an OpenAI-compatible `POST {base}/chat/completions`
ASSUMPTION; the organizers' participant guide has not been seen, so the route, headers, observation/action JSON
and `run.py` invocation stay PLACEHOLDER and `submission/run.py` stays fail-closed.
