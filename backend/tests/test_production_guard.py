"""environment_label() (spec section 20: a real, config-derived DEMO/FHIR_SANDBOX/STAGING/PRODUCTION
indicator -- never a hardcoded frontend string). Derived from exactly the same NOVA_ENV/EMR_MODE/
NOVA_ALLOW_DEMO_EMR variables validate_production_startup() reads, so these two functions are tested
side by side to keep that in sync."""
from app.services.production_guard import environment_label


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
