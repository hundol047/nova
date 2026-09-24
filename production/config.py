"""Production runtime configuration (spec: dev/staging/production separation, fail-fast on missing
required settings in production -- never silently degrade to a default that would be wrong in a
real deployment).

Deliberately separate from `nova_agent/config.py` (which stays competition/dev-focused and
untouched by this file): this module only adds the settings the PRODUCTION API/persistence/auth
layer itself needs, layered on top of the existing nova_agent config rather than replacing it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


class ProductionConfigError(RuntimeError):
    """Raised at startup when a required production setting is missing -- fail fast, never start
    serving requests with an unsafe/undefined configuration."""


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class ProductionConfig:
    env: str = field(default_factory=lambda: _env("NOVA_ENV", "development"))
    api_keys_raw: str = field(default_factory=lambda: _env("NOVA_API_KEYS", ""))
    database_url: str = field(default_factory=lambda: _env("NOVA_DATABASE_URL", "sqlite:///./nova_production.db"))
    require_auth: bool = field(default_factory=lambda: _bool_env("NOVA_REQUIRE_AUTH", True))
    audit_retention_days: int = field(default_factory=lambda: int(_env("NOVA_AUDIT_RETENTION_DAYS", "2555")))  # ~7y
    clinical_event_retention_days: int = field(default_factory=lambda: int(_env("NOVA_CLINICAL_EVENT_RETENTION_DAYS", "2555")))
    debug_log_retention_days: int = field(default_factory=lambda: int(_env("NOVA_DEBUG_LOG_RETENTION_DAYS", "30")))
    log_raw_chief_complaint_text: bool = field(default_factory=lambda: _bool_env("NOVA_LOG_RAW_TEXT", False))
    circuit_breaker_failure_threshold: int = field(default_factory=lambda: int(_env("NOVA_CB_FAILURE_THRESHOLD", "5")))
    circuit_breaker_cooldown_seconds: float = field(default_factory=lambda: float(_env("NOVA_CB_COOLDOWN_SECONDS", "30")))

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"

    @property
    def api_keys(self) -> dict[str, str]:
        """Maps API key -> role. Format: NOVA_API_KEYS="key1:clinician,key2:admin,key3:service"."""
        keys: dict[str, str] = {}
        for entry in self.api_keys_raw.split(","):
            entry = entry.strip()
            if not entry:
                continue
            if ":" not in entry:
                continue
            key, role = entry.split(":", 1)
            keys[key.strip()] = role.strip()
        return keys

    def validate(self) -> None:
        """Fail-fast validation (spec: production must not silently start with an unsafe config).
        Called explicitly at application startup, not import time, so tests can construct a
        ProductionConfig with placeholder values without triggering this."""
        if not self.is_production:
            return
        problems = []
        if self.require_auth and not self.api_keys:
            problems.append("NOVA_REQUIRE_AUTH=true but NOVA_API_KEYS is empty -- no one could "
                             "ever authenticate")
        if self.database_url.startswith("sqlite:///./") or self.database_url == "sqlite:///:memory:":
            problems.append("NOVA_DATABASE_URL is a local/in-memory SQLite path in production -- "
                             "case data would not survive a container restart or be shared across "
                             "replicas; point this at a real persistent database")
        if problems:
            raise ProductionConfigError(
                "Production configuration failed validation:\n" + "\n".join(f"  - {p}" for p in problems)
            )


_config: ProductionConfig | None = None


def get_production_config() -> ProductionConfig:
    global _config
    if _config is None:
        _config = ProductionConfig()
    return _config


def reset_production_config_cache() -> None:
    """Test-only: forces the next get_production_config() call to re-read the environment."""
    global _config
    _config = None
