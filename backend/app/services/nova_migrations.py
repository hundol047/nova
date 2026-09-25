"""Lightweight, dependency-free ordered SQL migration runner for the N.O.V.A. Postgres schema.

Design (see .kiro/specs/nova-hospital-grade/design.md 3.2): a long-lived production schema must be
managed by a versioned migration system with a migration version + upgrade path + schema history,
not only ad-hoc `CREATE TABLE IF NOT EXISTS`. Alembic was deliberately NOT adopted, to avoid adding
a heavy migration framework (and its own metadata/config surface) to the backend runtime for a
schema this small. Instead:

  - `MIGRATIONS` is an ordered list of (version, description, sql) steps. Version numbers are
    strictly increasing integers; the ordered list IS the schema history.
  - `schema_migrations(version INT PRIMARY KEY, description TEXT, applied_at TIMESTAMPTZ)` records
    which versions have been applied.
  - `apply_migrations(conn)` is idempotent: it applies (inside a transaction, each step atomically)
    exactly the versions not yet recorded, in order, and records each. Running it twice is a no-op.
  - It is safe to run at startup and in CI; concurrent callers race only on the advisory lock below,
    so a second caller waits and then sees the work already done.

The very first migration (0001) reproduces the previous `CREATE TABLE IF NOT EXISTS` schema so an
existing database created by the old `_init_schema` transparently adopts the migration baseline
(the CREATE ... IF NOT EXISTS statements are no-ops there, and 0001 is then recorded). Subsequent
migrations add columns/tables going forward -- e.g. 0002 adds state_schema_version.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, List, Optional, Tuple

# The current PatientState/case-record schema version persisted on each case row (R5.2). Bump this
# (and add a migration) when the persisted case shape changes in a way future code must detect.
CURRENT_STATE_SCHEMA_VERSION = 1

# Advisory lock key (arbitrary constant) so two processes starting at once don't both try to apply
# the same migration; the second blocks until the first commits, then finds nothing to do.
_ADVISORY_LOCK_KEY = 947_310_021


# (version, description, list-of-SQL-statements). Statements in one step run in one transaction.
MIGRATIONS: List[Tuple[int, str, List[str]]] = [
    (
        1,
        "baseline: nova_cases + nova_case_observations (matches the pre-migration schema)",
        [
            """
            CREATE TABLE IF NOT EXISTS nova_cases (
                case_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                encounter_id TEXT,
                state TEXT NOT NULL,
                status TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                agent_version TEXT NOT NULL,
                kb_version TEXT NOT NULL,
                closed_at TEXT,
                close_reason TEXT NOT NULL DEFAULT '',
                version INTEGER NOT NULL DEFAULT 0
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_nova_cases_patient_id ON nova_cases(patient_id)",
            """
            CREATE TABLE IF NOT EXISTS nova_case_observations (
                case_id TEXT NOT NULL REFERENCES nova_cases(case_id),
                observation_id TEXT NOT NULL,
                PRIMARY KEY (case_id, observation_id)
            )
            """,
        ],
    ),
    (
        2,
        "add state_schema_version to nova_cases (forward-compatibility marker, R5.2)",
        [
            "ALTER TABLE nova_cases ADD COLUMN IF NOT EXISTS state_schema_version INTEGER NOT NULL DEFAULT 1",
        ],
    ),
]


def _ensure_migrations_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TIMESTAMPTZ NOT NULL
        )
        """
    )


def _applied_versions(conn) -> set:
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    return {r[0] for r in rows}


def apply_migrations(conn, *, migrations: Optional[List[Tuple[int, str, List[str]]]] = None) -> List[int]:
    """Apply all not-yet-applied migrations in order. Returns the list of versions applied this call
    (empty if the schema was already current). Idempotent and safe to call at startup."""
    steps = sorted(migrations if migrations is not None else MIGRATIONS, key=lambda m: m[0])
    # Serialize concurrent migrators with a session-level advisory lock.
    try:
        conn.execute("SELECT pg_advisory_lock(%s)", (_ADVISORY_LOCK_KEY,))
    except Exception:
        # Non-Postgres or lock unsupported -- proceed without it (single-writer contexts / tests).
        pass
    applied_now: List[int] = []
    try:
        _ensure_migrations_table(conn)
        done = _applied_versions(conn)
        for version, description, statements in steps:
            if version in done:
                continue
            with conn.transaction():
                for sql in statements:
                    conn.execute(sql)
                conn.execute(
                    "INSERT INTO schema_migrations (version, description, applied_at) VALUES (%s, %s, %s)",
                    (version, description, datetime.now(timezone.utc)),
                )
            applied_now.append(version)
    finally:
        try:
            conn.execute("SELECT pg_advisory_unlock(%s)", (_ADVISORY_LOCK_KEY,))
        except Exception:
            pass
    return applied_now


def schema_history(conn) -> List[dict]:
    """The applied-migration history (for a /ready or ops surface)."""
    _ensure_migrations_table(conn)
    rows = conn.execute(
        "SELECT version, description, applied_at FROM schema_migrations ORDER BY version"
    ).fetchall()
    return [{"version": r[0], "description": r[1], "applied_at": str(r[2])} for r in rows]
