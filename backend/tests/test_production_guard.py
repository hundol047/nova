"""environment_label() (spec section 20: a real, config-derived DEMO/FHIR_SANDBOX/STAGING/PRODUCTION
indicator -- never a hardcoded frontend string). Derived from exactly the same NOVA_ENV/EMR_MODE/
NOVA_ALLOW_DEMO_EMR variables validate_production_startup() reads, so these two functions are tested
side by side to keep that in sync."""
import pytest

from app.services.production_guard import ProductionConfigError, environment_label, validate_production_startup


def test_default_development_demo_emr_is_demo(monkeypatch):
    monkeypatch.delenv('NOVA_ENV', raising=False)
    monkeypatch.delenv('EMR_MODE', raising=False)
    assert environment_label() == 'demo'


def test_development_with_fhir_emr_is_fhir_sandbox(monkeypatch):
    monkeypatch.delenv('NOVA_ENV', raising=False)
    monkeypatch.setenv('EMR_MODE', 'fhir')
    assert environment_label() == 'fhir_sandbox'


def test_production_with_fhir_emr_is_production(monkeypatch):
    monkeypatch.setenv('NOVA_ENV', 'production')
    monkeypatch.setenv('EMR_MODE', 'fhir')
    assert environment_label() == 'production'


def test_production_with_demo_emr_is_staging_not_production(monkeypatch):
    # A NOVA_ENV=production deployment intentionally left on demo data (NOVA_ALLOW_DEMO_EMR=true,
    # e.g. a staging/sandbox instance) must never claim to be a real hospital-production instance.
    monkeypatch.setenv('NOVA_ENV', 'production')
    monkeypatch.setenv('EMR_MODE', 'demo')
    assert environment_label() == 'staging'


def test_label_never_drifts_from_is_production(monkeypatch):
    from app.services.production_guard import is_production
    for nova_env in ('development', 'test', 'production'):
        for emr_mode in ('demo', 'fhir'):
            monkeypatch.setenv('NOVA_ENV', nova_env)
            monkeypatch.setenv('EMR_MODE', emr_mode)
            label = environment_label()
            if is_production():
                assert label in ('production', 'staging')
            else:
                assert label in ('demo', 'fhir_sandbox')


def _configure_otherwise_valid_production_env(monkeypatch):
    """Every OTHER production-startup requirement satisfied, so a test can isolate exactly one
    missing piece and see it (and only it) show up in the raised problems list."""
    monkeypatch.setenv('NOVA_ENV', 'production')
    monkeypatch.setenv('AUTH_MODE', 'oidc')
    monkeypatch.setenv('OIDC_ISSUER', 'https://issuer.example')
    monkeypatch.setenv('OIDC_AUDIENCE', 'synex-api')
    monkeypatch.setenv('NOVA_LLM_PROVIDER', 'anthropic')
    monkeypatch.setenv('EMR_MODE', 'fhir')
    monkeypatch.setenv('FHIR_BASE_URL', 'https://fhir.example/r4')
    monkeypatch.setenv('CDS_AUTH_MODE', 'bearer')
    monkeypatch.setenv('SYNEX_AUDIT_PATH', '/mnt/data/audit.sqlite3')
    monkeypatch.setenv('NOVA_POSTGRES_URL', 'postgresql://user:pass@db.example/nova')


def test_production_startup_requires_nova_postgres_url_never_silently_in_memory(monkeypatch):
    _configure_otherwise_valid_production_env(monkeypatch)
    monkeypatch.delenv('NOVA_POSTGRES_URL', raising=False)
    with pytest.raises(ProductionConfigError) as exc_info:
        validate_production_startup()
    assert 'NOVA_POSTGRES_URL' in str(exc_info.value)


def test_production_startup_passes_with_nova_postgres_url_set(monkeypatch):
    _configure_otherwise_valid_production_env(monkeypatch)
    validate_production_startup()  # must not raise


def test_production_startup_accepts_nova_postgres_url_alone_for_audit_persistence(monkeypatch):
    # NOVA_POSTGRES_URL alone (no SYNEX_AUDIT_PATH/SYNEX_REDIS_URL) satisfies the audit-persistence
    # requirement too, since build_audit_store() picks PostgresAuditStore whenever it's set.
    _configure_otherwise_valid_production_env(monkeypatch)
    monkeypatch.delenv('SYNEX_AUDIT_PATH', raising=False)
    validate_production_startup()  # must not raise
