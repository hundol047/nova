"""Unit tests for the smaller production/ modules: config fail-fast validation, redaction,
versions/reproducibility, auth roles, input validation, and metrics."""

from __future__ import annotations

import pytest

from production.auth import Principal, authenticate, authorize, known_roles
from production.config import ProductionConfig, ProductionConfigError
from production.errors import AuthenticationError, AuthorizationError, ValidationError
from production.metrics import MetricsRegistry
from production.redaction import redact, redact_dict
from production.validation import validate_action_type, validate_free_text, validate_identifier
from production.versions import kb_fingerprint, model_version


# --- config -----------------------------------------------------------------------------------

def test_dev_config_never_raises_even_when_unsafe():
    cfg = ProductionConfig(env="development", require_auth=True, api_keys_raw="", database_url="sqlite:///./x.db")
    cfg.validate()  # must not raise -- validation is production-only


def test_production_config_requires_api_keys_when_auth_required():
    cfg = ProductionConfig(env="production", require_auth=True, api_keys_raw="", database_url="postgres://real/db")
    with pytest.raises(ProductionConfigError):
        cfg.validate()


def test_production_config_rejects_local_sqlite():
    cfg = ProductionConfig(env="production", require_auth=False, database_url="sqlite:///./nova_production.db")
    with pytest.raises(ProductionConfigError):
        cfg.validate()


def test_production_config_passes_with_real_settings():
    cfg = ProductionConfig(env="production", require_auth=True, api_keys_raw="k1:clinician",
                            database_url="postgresql://user:pass@host/db")
    cfg.validate()  # must not raise


def test_api_keys_parses_role_map():
    cfg = ProductionConfig(api_keys_raw="key1:clinician, key2:admin ,key3:service")
    assert cfg.api_keys == {"key1": "clinician", "key2": "admin", "key3": "service"}


# --- redaction ----------------------------------------------------------------------------------

def test_redact_email_and_phone_and_id_shaped_digits():
    text = "Contact patient at jane.doe@example.com or 555-123-4567, ID 901231-1234567"
    out = redact(text)
    assert "jane.doe@example.com" not in out
    assert "901231-1234567" not in out
    assert "[REDACTED_EMAIL]" in out


def test_redact_dict_only_touches_named_free_text_keys():
    data = {"chief_complaint": "call me at 555-123-4567", "case_id": "555-123-4567", "nested": {"message": "555-123-4567"}}
    out = redact_dict(data)
    assert out["chief_complaint"] != data["chief_complaint"]
    assert out["case_id"] == data["case_id"]  # not a free-text key -- untouched
    assert out["nested"]["message"] != data["nested"]["message"]


def test_redact_empty_string_is_a_noop():
    assert redact("") == ""


# --- versions -----------------------------------------------------------------------------------

def test_kb_fingerprint_is_deterministic_across_calls():
    assert kb_fingerprint() == kb_fingerprint()


def test_model_version_returns_mock_under_mock_provider(monkeypatch):
    monkeypatch.setenv("NOVA_LLM_PROVIDER", "mock")
    assert model_version() == "mock"


# --- auth ---------------------------------------------------------------------------------------

def test_authenticate_rejects_missing_key_when_required():
    cfg = ProductionConfig(require_auth=True, api_keys_raw="k1:clinician")
    with pytest.raises(AuthenticationError):
        authenticate(None, config=cfg)


def test_authenticate_rejects_unknown_key():
    cfg = ProductionConfig(require_auth=True, api_keys_raw="k1:clinician")
    with pytest.raises(AuthenticationError):
        authenticate("wrong-key", config=cfg)


def test_authenticate_accepts_known_key_and_resolves_role():
    cfg = ProductionConfig(require_auth=True, api_keys_raw="k1:clinician")
    principal = authenticate("k1", config=cfg)
    assert principal.role == "clinician"


def test_authorize_enforces_least_privilege():
    reviewer = Principal(api_key_suffix="abcd", role="reviewer")
    with pytest.raises(AuthorizationError):
        authorize(reviewer, "decide")
    authorize(reviewer, "read_case")  # must not raise


def test_known_roles_cover_the_spec_role_set():
    assert set(known_roles()) == {"clinician", "reviewer", "admin", "service"}


# --- validation -----------------------------------------------------------------------------------

def test_validate_free_text_rejects_oversized_input():
    with pytest.raises(ValidationError):
        validate_free_text("x" * 100, field_name="f", max_length=10)


def test_validate_free_text_rejects_control_characters():
    with pytest.raises(ValidationError):
        validate_free_text("hello\x01world", field_name="f")


def test_validate_free_text_allows_ordinary_clinical_prose():
    text = "Patient reports sudden onset chest pain radiating to the left arm."
    assert validate_free_text(text, field_name="f") == text


def test_validate_identifier_rejects_spaces_and_symbols():
    with pytest.raises(ValidationError):
        validate_identifier("not a valid id!", field_name="f")


def test_validate_identifier_accepts_typical_case_ids():
    assert validate_identifier("case-2026-001", field_name="f") == "case-2026-001"


def test_validate_action_type_rejects_unknown_type():
    with pytest.raises(ValidationError):
        validate_action_type("EXECUTE")


# --- metrics -----------------------------------------------------------------------------------

def test_metrics_derived_rates_are_none_until_denominator_present():
    reg = MetricsRegistry()
    snap = reg.snapshot()
    assert snap["derived"]["llm_success_rate"] is None


def test_metrics_percentiles_reflect_observed_latencies():
    reg = MetricsRegistry()
    for v in [10, 20, 30, 40, 50]:
        reg.observe_latency("x", v)
    snap = reg.snapshot()
    assert snap["latencies_ms"]["x"]["count"] == 5
    assert snap["latencies_ms"]["x"]["p50"] == 30
