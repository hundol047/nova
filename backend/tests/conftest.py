import os
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.main import app


# --- Postgres-in-CI enforcement (R14.2) -----------------------------------------------------------
# The Postgres-backed test modules mark themselves skipif(not _postgres_available()). That skip is
# correct for a local dev machine without Postgres, but in CI a *silent* skip would let a broken
# Postgres integration pass unnoticed and be mistaken for "production-ready" persistence. When
# NOVA_CI_REQUIRE_POSTGRES=1 (set only by the postgres-integration CI job), a Postgres test that
# would otherwise skip is turned into a hard FAILURE instead -- so the build goes red if the real
# database integration did not actually run. Locally (flag unset) the skip behavior is unchanged.
_POSTGRES_TEST_FILES = {
    "test_nova_postgres_repository.py",
    "test_nova_postgres_concurrency.py",
    "test_audit_postgres.py",
    "test_nova_migrations.py",
}


def _require_postgres_in_ci() -> bool:
    return os.getenv("NOVA_CI_REQUIRE_POSTGRES", "").strip() in ("1", "true", "True", "yes")


def pytest_collection_modifyitems(config, items):
    if not _require_postgres_in_ci():
        return
    for item in items:
        if Path(str(item.fspath)).name not in _POSTGRES_TEST_FILES:
            continue
        # Drop any module-level skip marker so the test is forced to run; if Postgres is genuinely
        # unreachable the test body/fixture will raise and the build fails (the intended signal).
        item.own_markers = [m for m in item.own_markers if m.name != "skipif"]
        if hasattr(item, "add_marker"):
            item.add_marker(pytest.mark.postgres_required)
@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('SYNEX_AUDIT_PATH',str(tmp_path/'audit.sqlite3'))
    # IdempotencyStore is instantiated fresh per app lifespan (see main.py), so this env var IS
    # effective per-test. SYNEX_SMART_LAUNCH_PATH/SYNEX_SESSION_PATH/SYNEX_AUTH_SESSION_PATH are NOT
    # -- smart_launch.py/auth.py build their stores once as module-level singletons at import time,
    # before any test's monkeypatch runs, so tests needing an isolated launch/session store construct
    # one directly (e.g. _LaunchStore(path=tmp_path/...) -- see test_launch_state_survives_a_process_restart).
    monkeypatch.setenv('SYNEX_IDEMPOTENCY_PATH',str(tmp_path/'idempotency.sqlite3'))
    with TestClient(app) as c:yield c
