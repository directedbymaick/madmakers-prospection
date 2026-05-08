"""crm.db — SQLite connection helpers + auto-init."""
import sqlite3
from contextlib import contextmanager
from .config import DB_PATH, SCHEMA_PATH


def _row_factory(cursor, row):
    """Return rows as dicts (column name → value)."""
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


def get_conn():
    """Get a SQLite connection with FK enabled and dict rows.

    Note : pas de PARSE_DECLTYPES — on stocke les timestamps en strings ISO
    (format Python `datetime.isoformat()` avec T, ou date-only "YYYY-MM-DD")
    et on les reformate côté Jinja via les filtres dt/d/relative.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = _row_factory
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def cursor():
    """Context manager: yields cursor + commits on exit, rolls back on error."""
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
    """Apply schema.sql to create tables if not exist + run pending migrations."""
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn = get_conn()
    try:
        conn.executescript(sql)
        # Migrations in-place pour DB déjà créée
        _run_migrations(conn)
        conn.commit()
    finally:
        conn.close()


def _run_migrations(conn):
    """ALTER TABLE idempotent pour ajouter colonnes manquantes."""
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(prospects)")
    # row_factory returns dicts → utilise la clé "name"
    existing_cols = {r["name"] for r in cur.fetchall()}
    additions = [
        ("phone_mobile",  "TEXT"),
        ("phone_office",  "TEXT"),
        ("phone_other",   "TEXT"),
    ]
    for col, typ in additions:
        if col not in existing_cols:
            cur.execute(f"ALTER TABLE prospects ADD COLUMN {col} {typ}")


def query(sql, params=()):
    """Run SELECT, return list of dicts."""
    with cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def query_one(sql, params=()):
    """Run SELECT, return single dict or None."""
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql, params=()):
    """Run INSERT/UPDATE/DELETE, return lastrowid."""
    with cursor() as cur:
        cur.execute(sql, params)
        return cur.lastrowid


def execute_many(sql, params_list):
    """Bulk insert/update."""
    with cursor() as cur:
        cur.executemany(sql, params_list)
        return cur.rowcount
