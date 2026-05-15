"""crm.db — connection PostgreSQL (Supabase) avec helpers compatibles
   l'ancien style SQLite (utilise '?' comme placeholder).

   On garde le `?` partout dans les queries du codebase et on convertit
   en `%s` au moment de l'exécution. Ça minimise les modifications dans
   models.py et garde le code lisible.
"""
import os
import logging
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from .config import SCHEMA_PATH

log = logging.getLogger(__name__)


def _database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL non défini dans .env. "
            "Récupère-le depuis Supabase Dashboard → Connect → Session Pooler."
        )
    return url


def _qmarks_to_pyformat(sql: str) -> str:
    """Remplace les '?' SQLite par '%s' Postgres, en ignorant ceux dans les strings."""
    if "?" not in sql:
        return sql
    out = []
    in_str = None  # None, "'" ou '"'
    i = 0
    while i < len(sql):
        c = sql[i]
        if in_str:
            out.append(c)
            if c == in_str:
                # check escape (SQL doubles le quote pour échapper)
                if i + 1 < len(sql) and sql[i + 1] == in_str:
                    out.append(sql[i + 1])
                    i += 2
                    continue
                in_str = None
            i += 1
            continue
        if c in ("'", '"'):
            in_str = c
            out.append(c)
            i += 1
            continue
        if c == "?":
            out.append("%s")
            i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def get_conn():
    """Get a psycopg connection avec dict rows."""
    return psycopg.connect(_database_url(), row_factory=dict_row, connect_timeout=15)


@contextmanager
def cursor():
    """Context manager : yields cursor + commits on exit, rolls back on error."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Apply schema.sql to create tables if not exist + run migrations."""
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            _run_migrations(cur)
        conn.commit()
        log.info("Schema appliqué.")
    finally:
        conn.close()


def _run_migrations(cur):
    """ALTER TABLE idempotent pour ajouter colonnes manquantes sur DB existante."""
    additions = [
        # created_by_user_id sur activities, calls, audits, emails
        ("activities", "created_by_user_id", "BIGINT REFERENCES users(id) ON DELETE SET NULL"),
        ("calls",      "created_by_user_id", "BIGINT REFERENCES users(id) ON DELETE SET NULL"),
        ("audits",     "created_by_user_id", "BIGINT REFERENCES users(id) ON DELETE SET NULL"),
        ("emails",     "created_by_user_id", "BIGINT REFERENCES users(id) ON DELETE SET NULL"),
        # Email composer extensions
        ("emails", "from_email",       "TEXT"),
        ("emails", "from_name",        "TEXT"),
        ("emails", "to_email",         "TEXT"),
        ("emails", "reply_to",         "TEXT"),
        ("emails", "body_html",        "TEXT"),
        ("emails", "attachments_json", "TEXT"),
        ("emails", "resend_message_id","TEXT"),
        ("emails", "error_message",    "TEXT"),
    ]
    for tbl, col, typ in additions:
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema='public' AND table_name=%s AND column_name=%s
        """, (tbl, col))
        if not cur.fetchone():
            cur.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {typ}")
            log.info(f"Migration : {tbl}.{col} ajouté")

    # sequence_step doit avoir un default (pour les sends manuels qui n'ont pas de step)
    cur.execute("""
        SELECT column_default FROM information_schema.columns
        WHERE table_schema='public' AND table_name='emails' AND column_name='sequence_step'
    """)
    row = cur.fetchone()
    if row and not row.get("column_default"):
        cur.execute("ALTER TABLE emails ALTER COLUMN sequence_step SET DEFAULT 'manual'")

    # Table unsubscribes (RGPD)
    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema='public' AND table_name='unsubscribes'
    """)
    if not cur.fetchone():
        cur.execute("""
            CREATE TABLE unsubscribes (
                id              BIGSERIAL PRIMARY KEY,
                email           TEXT NOT NULL UNIQUE,
                prospect_id     BIGINT REFERENCES prospects(id) ON DELETE SET NULL,
                reason          TEXT,
                user_agent      TEXT,
                unsubscribed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("CREATE INDEX idx_unsubs_email ON unsubscribes(email)")
        log.info("Table unsubscribes créée")

    # Index emails scheduled (pour cron worker)
    cur.execute("""
        SELECT indexname FROM pg_indexes
        WHERE schemaname='public' AND indexname='idx_emails_scheduled'
    """)
    if not cur.fetchone():
        cur.execute("CREATE INDEX idx_emails_scheduled ON emails(scheduled_at) WHERE status='scheduled'")


def query(sql, params=()):
    """Run SELECT, return list of dicts."""
    sql = _qmarks_to_pyformat(sql)
    with cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def query_one(sql, params=()):
    """Run SELECT, return single dict or None."""
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql, params=()):
    """Run INSERT/UPDATE/DELETE. Pour INSERT, retourne l'id (si la query
    contient déjà RETURNING id, sinon ajoute-le automatiquement)."""
    sql = _qmarks_to_pyformat(sql).rstrip().rstrip(";")
    sql_upper = sql.upper().lstrip()
    is_insert = sql_upper.startswith("INSERT")
    has_returning = "RETURNING" in sql_upper

    if is_insert and not has_returning:
        sql = sql + " RETURNING id"

    with cursor() as cur:
        cur.execute(sql, params)
        if is_insert:
            row = cur.fetchone()
            return row["id"] if row else None
        return cur.rowcount


def execute_many(sql, params_list):
    """Bulk insert/update."""
    sql = _qmarks_to_pyformat(sql)
    with cursor() as cur:
        cur.executemany(sql, params_list)
        return cur.rowcount
