"""Audit persistence. Two backends implement the identical record()/save_analysis()/get_analysis()/
list() interface -- the same dual-backend shape services/idempotency.py and
services/nova_repository.py already use: `AuditStore` is SQLite-backed (the default -- already
real, restart-surviving persistence, unlike a bare in-memory list), and `PostgresAuditStore` is a
genuinely multi-instance-safe backend for production (set NOVA_POSTGRES_URL -- see
build_audit_store() at the bottom of this file; reuses the same env var as
nova_repository.build_nova_case_repository() rather than adding a second Postgres URL to
configure, since a production deployment durable enough to need one is durable enough to need
both). main.py's `app.state.audit` is the only call site that picks a backend; every other user of
AuditStore/PostgresAuditStore in this codebase (endpoints, tests) treats it as this interface."""
import json,os,sqlite3
from contextlib import contextmanager
from datetime import datetime,timezone
from pathlib import Path

DEFAULT=Path(__file__).resolve().parents[2]/'data'/'audit.sqlite3'
class AuditStore:
    def __init__(self,path=None):
        self.path=str(path or os.getenv('SYNEX_AUDIT_PATH',DEFAULT))
        Path(self.path).parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id TEXT NOT NULL, timestamp TEXT NOT NULL, event TEXT NOT NULL, detail TEXT NOT NULL)')
            db.execute('CREATE INDEX IF NOT EXISTS idx_events_patient_id_id ON events(patient_id,id)')
            db.execute('CREATE TABLE IF NOT EXISTS analyses (id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, payload TEXT NOT NULL)')
            # Append-only additions for user-linked audit (who did this, under which role). Nullable
            # so every event recorded before this column existed still reads back fine.
            for col in ('user_id','role'):
                try:db.execute(f'ALTER TABLE events ADD COLUMN {col} TEXT')
                except sqlite3.OperationalError:pass  # column already exists
    @contextmanager
    def connect(self):
        # A plain `sqlite3.connect(...)` returned here and used only via the connection's own
        # `with db:` (which commits/rolls back but does NOT close) would leak a file descriptor
        # every call -- confirmed under a repeated-request smoke test before this fix (fd count
        # climbed steadily under load). Wrapping the whole thing as its own context manager keeps
        # every existing call site's `with self.connect() as db:` syntax and commit/rollback
        # semantics identical, and guarantees the connection is actually closed afterward.
        db=sqlite3.connect(self.path,timeout=15)
        try:
            with db:
                yield db
        finally:
            db.close()
    def record(self,pid,event,detail,user_id=None,role=None):
        with self.connect() as db:
            db.execute('INSERT INTO events(patient_id,timestamp,event,detail,user_id,role) VALUES(?,?,?,?,?,?)',
                       (pid,datetime.now(timezone.utc).isoformat(),event,json.dumps(detail,ensure_ascii=False),user_id,role))
    def save_analysis(self,payload):
        with self.connect() as db:
            db.execute('INSERT INTO analyses VALUES(?,?,?)',(payload['analysis_id'],payload['patient_id'],json.dumps(payload,ensure_ascii=False)))
    def get_analysis(self,aid):
        with self.connect() as db:
            row=db.execute('SELECT payload FROM analyses WHERE id=?',(aid,)).fetchone()
        return json.loads(row[0]) if row else None
    def list(self,pid):
        with self.connect() as db:
            rows=db.execute('SELECT id,timestamp,event,detail,user_id,role FROM events WHERE patient_id=? ORDER BY id DESC LIMIT 200',(pid,)).fetchall()
        return [{'id':r[0],'timestamp':r[1],'event':r[2],'detail':json.loads(r[3]),'user_id':r[4],'role':r[5]} for r in rows]


class PostgresAuditStore:
    """See this module's docstring. Lazy-imports psycopg (same reasoning as services/auth.py's own
    lazy `import redis`: a process that never sets NOVA_POSTGRES_URL should never pay an
    import-time cost for a driver it doesn't use)."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self._init_schema()

    def _connect(self):
        import psycopg
        return psycopg.connect(self.dsn)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS audit_events (
                    id BIGSERIAL PRIMARY KEY, patient_id TEXT NOT NULL, timestamp TEXT NOT NULL,
                    event TEXT NOT NULL, detail TEXT NOT NULL, user_id TEXT, role TEXT)"""
            )
            conn.execute('CREATE INDEX IF NOT EXISTS idx_audit_events_patient_id_id ON audit_events(patient_id,id)')
            conn.execute(
                """CREATE TABLE IF NOT EXISTS audit_analyses (
                    id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, payload TEXT NOT NULL)"""
            )

    def record(self,pid,event,detail,user_id=None,role=None):
        with self._connect() as conn:
            conn.execute('INSERT INTO audit_events(patient_id,timestamp,event,detail,user_id,role) VALUES(%s,%s,%s,%s,%s,%s)',
                         (pid,datetime.now(timezone.utc).isoformat(),event,json.dumps(detail,ensure_ascii=False),user_id,role))

    def save_analysis(self,payload):
        with self._connect() as conn:
            conn.execute('INSERT INTO audit_analyses VALUES(%s,%s,%s)',
                         (payload['analysis_id'],payload['patient_id'],json.dumps(payload,ensure_ascii=False)))

    def get_analysis(self,aid):
        with self._connect() as conn:
            row=conn.execute('SELECT payload FROM audit_analyses WHERE id=%s',(aid,)).fetchone()
        return json.loads(row[0]) if row else None

    def list(self,pid):
        with self._connect() as conn:
            rows=conn.execute('SELECT id,timestamp,event,detail,user_id,role FROM audit_events WHERE patient_id=%s ORDER BY id DESC LIMIT 200',(pid,)).fetchall()
        return [{'id':r[0],'timestamp':r[1],'event':r[2],'detail':json.loads(r[3]),'user_id':r[4],'role':r[5]} for r in rows]


def build_audit_store():
    """Backend selector: NOVA_POSTGRES_URL set -> PostgresAuditStore (durable across restarts AND
    shared correctly across multiple backend instances -- SQLite's WAL file is neither, once more
    than one process/container is involved); unset -> the SQLite-backed AuditStore (dev/test
    default, matching every existing test's expectations, and already real persistence for a
    single-instance deployment)."""
    dsn = os.getenv('NOVA_POSTGRES_URL')
    if dsn:
        return PostgresAuditStore(dsn)
    return AuditStore()
