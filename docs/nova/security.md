# Security

## Authentication and authorization

Every clinically-facing endpoint requires an `X-API-Key` header (`production/auth.py`). There is
no anonymous public endpoint for case creation, observation entry, decide, or case reads. `/health`
is deliberately exempt (infrastructure liveness probes; carries no PHI). `/ready` is also exempt
(infrastructure readiness probes) but reveals only boolean check names, never case data. `/metrics`
requires auth and the `read_metrics` permission (admin/service roles).

Keys are compared with `hmac.compare_digest` against every configured key (not a short-circuiting
dict lookup) to avoid a timing side-channel, and only the last 4 characters of a presented key are
ever retained on the resulting `Principal` object -- a full key is never logged or echoed back.

Roles and their permissions (least-privilege, `production/auth.py`):

| Role | create_case | add_observation | decide | read_case | read_metrics |
|---|---|---|---|---|---|
| clinician | yes | yes | yes | yes | no |
| admin | yes | yes | yes | yes | yes |
| service | yes | yes | no | yes | yes |
| reviewer | no | no | no | yes | no |

`service` is for machine-to-machine callers (e.g. an internal system posting lab results as
observations) and is deliberately excluded from `decide` -- the clinical decision step requires a
human-attributable clinician/admin credential.

## Input validation / injection defense

`production/validation.py` rejects, at the API boundary, before anything reaches the reasoning
pipeline:
- Free text over 4000 characters (`validate_free_text`).
- Disallowed control characters (anything except `\t`/`\n`/`\r` in the C0/C1 ranges).
- Unicode code points in the surrogate/private-use/unassigned categories.
- Identifiers (`case_id`, `observation_id`, action `key`) that don't match
  `^[A-Za-z0-9_.:-]{1,128}$`.
- Unknown `action_type` values.
- Unexpected request fields -- every request schema in `production/schemas.py` sets
  `model_config = ConfigDict(extra="forbid")`.

Patient-authored free text (chief complaint, observation results) is never treated as executable
instructions anywhere in the pipeline: the deterministic reasoning layers only ever run regex/
keyword matching over it (`nova_agent/matching.py`), and the one place free text does reach an LLM
(`nova_agent/llm_client.py`'s `build_reasoning_prompt()`), the prompt explicitly frames the patient
summary and retrieved knowledge as **untrusted clinical data**, instructing the model that any
text resembling a command inside that data is itself a symptom to evaluate, never something to
obey.

## Secrets

No secret is ever baked into the `production/Dockerfile` image (`NOVA_API_KEYS`,
`NOVA_DATABASE_URL`, and any real LLM provider credential are runtime environment variables only).
`scripts/build_nova_submission.py`'s existing secret scan (checked in CI) covers the competition
submission artifact; it does not scan `production/`, which never ships credentials in its own
source in the first place -- `production/config.py` only ever reads secret material from the
process environment.

## Dependency surface

`production/requirements.txt` adds exactly two packages on top of `requirements-nova.txt`:
`fastapi` and `uvicorn[standard]`, both version-range-pinned (`>=X,<Y`). No dependency-audit or SBOM
tooling has been wired into CI yet for this package -- see Remaining blockers.

## Known NOT VERIFIED items

- No institutional/external security review has been performed on this code. "Production-grade
  code" here means the practices above are implemented and tested, not that a security review has
  signed off on them.
- No dependency vulnerability scan (e.g. `pip-audit`) or SBOM generation is wired into CI yet.
- No JWT/OAuth identity provider integration -- the static API-key map is the current auth
  mechanism, explicitly designed to be swappable for a real IdP later without call sites changing
  (every endpoint depends on `auth.Principal`, never the key format).
