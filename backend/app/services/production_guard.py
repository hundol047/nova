"""Production environment gating (spec: a real deployment must never silently start in a demo-shaped
configuration). NOVA_ENV=development (default) or NOVA_ENV=test never trigger any check here -- this
module is a no-op outside NOVA_ENV=production, exactly like production/config.py's
ProductionConfig.validate() in the standalone production/ package (see docs/NOVA_DEPLOYMENT.md for
how the two relate): dev/test must never be blocked by a production-only check.

validate_production_startup() is called once, from main.py's lifespan(), BEFORE the app starts
accepting requests -- fail fast, never serve a single request on a configuration this module
considers unsafe for a real deployment.
"""

from __future__ import annotations

import os


class ProductionConfigError(RuntimeError):
    pass


def is_production() -> bool:
    return os.getenv("NOVA_ENV", "development").lower() == "production"


def environment_label() -> str:
    """A real, config-derived environment indicator (spec: DEMO / FHIR SANDBOX / STAGING /
    PRODUCTION -- never a hardcoded frontend string). Derived purely from the same NOVA_ENV/
    EMR_MODE/NOVA_ALLOW_DEMO_EMR variables validate_production_startup() already reads, so it can
    never drift out of sync with what that function actually enforces:

      - NOVA_ENV=production + EMR_MODE=fhir              -> "production"
      - NOVA_ENV=production + EMR_MODE=demo (allowed)     -> "staging" (real production infra,
        intentionally demo-data-only, per NOVA_ALLOW_DEMO_EMR -- see validate_production_startup())
      - NOVA_ENV!=production + EMR_MODE=fhir              -> "fhir_sandbox"
      - NOVA_ENV!=production + EMR_MODE=demo              -> "demo"
    """
    emr_mode = os.getenv("EMR_MODE", "demo").lower()
    if is_production():
        return "production" if emr_mode == "fhir" else "staging"
    return "fhir_sandbox" if emr_mode == "fhir" else "demo"


def validate_production_startup() -> None:
    if not is_production():
        return
    problems = []

    auth_mode = os.getenv("AUTH_MODE", "demo").lower()
    if auth_mode == "demo":
        problems.append(
            "AUTH_MODE=demo -- every request would authenticate as the same fixed demo identity. "
            "Set AUTH_MODE=oidc with OIDC_ISSUER/OIDC_AUDIENCE configured."
        )
    elif auth_mode == "oidc":
        if not os.getenv("OIDC_ISSUER"):
            problems.append("AUTH_MODE=oidc but OIDC_ISSUER is not set.")
        if not os.getenv("OIDC_AUDIENCE"):
            problems.append("AUTH_MODE=oidc but OIDC_AUDIENCE is not set.")

    nova_provider = os.getenv("NOVA_LLM_PROVIDER", "mock").lower()
    if nova_provider == "mock":
        problems.append(
            "NOVA_LLM_PROVIDER=mock -- N.O.V.A. would run entirely on the deterministic offline "
            "fallback, never a real AI-augmented differential. Set NOVA_LLM_PROVIDER to a real "
            "provider (anthropic/openai_compatible/local) with its endpoint/model/key configured."
        )

    emr_mode = os.getenv("EMR_MODE", "demo").lower()
    if emr_mode == "demo" and os.getenv("NOVA_ALLOW_DEMO_EMR", "false").lower() != "true":
        problems.append(
            "EMR_MODE=demo -- every patient would be the bundled synthetic demo roster, not a real "
            "hospital record. Set EMR_MODE=fhir with FHIR_BASE_URL configured, or explicitly set "
            "NOVA_ALLOW_DEMO_EMR=true if this production deployment is intentionally demo-data-only "
            "(e.g. a staging/sandbox instance under NOVA_ENV=production for infra testing)."
        )
    elif emr_mode == "fhir" and not os.getenv("FHIR_BASE_URL"):
        problems.append("EMR_MODE=fhir but FHIR_BASE_URL is not set.")

    cds_auth_mode = os.getenv("CDS_AUTH_MODE", "none").lower()
    if cds_auth_mode == "none":
        problems.append(
            "CDS_AUTH_MODE=none -- the CDS Hooks execution endpoint would accept unauthenticated "
            "calls. Set CDS_AUTH_MODE=bearer for a production deployment that exposes CDS Hooks to "
            "a hospital EMR."
        )

    if not os.getenv("SYNEX_AUDIT_PATH") and not os.getenv("SYNEX_REDIS_URL"):
        problems.append(
            "Neither SYNEX_AUDIT_PATH nor SYNEX_REDIS_URL is set -- the audit log would default to "
            "an in-container SQLite path that does not survive a container replacement. Set "
            "SYNEX_AUDIT_PATH to a mounted persistent volume path."
        )

    if problems:
        raise ProductionConfigError(
            "Production startup validation failed (NOVA_ENV=production):\n"
            + "\n".join(f"  - {p}" for p in problems)
        )
