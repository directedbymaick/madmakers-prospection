"""crm.db — connection PostgreSQL (Supabase) avec helpers compatibles
   l'ancien style SQLite (utilise '?' comme placeholder).

   On garde le `?` partout dans les queries du codebase et on convertit
   en `%s` au moment de l'exécution. Ça minimise les modifications dans
   models.py et garde le code lisible.
"""
import os
import logging
import threading
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from .config import SCHEMA_PATH

log = logging.getLogger(__name__)

# Thread-local : si une `session()` est ouverte, toutes les ops execute/query
# dans le thread réutilisent sa connection au lieu d'en rouvrir une.
_session_local = threading.local()


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
    """Context manager : yields cursor + commits on exit, rolls back on error.

    Si une `session()` est active dans le thread courant, on réutilise sa
    connection (pas de open/close/commit) — le caller de session() gère
    la transaction globale. C'est ce qui fait passer un bulk import de 2h
    à 5 min : on n'ouvre plus une connection à chaque query."""
    sess_cur = getattr(_session_local, "cursor", None)
    if sess_cur is not None:
        yield sess_cur
        return
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


@contextmanager
def session(autocommit: bool = True):
    """Maintient UNE connection partagée pour toutes les ops execute/query
    dans le bloc — divise par 4-5 le temps des bulk imports en évitant
    d'ouvrir une nouvelle connection au pooler Supabase par opération.

    Avec autocommit=True (défaut) : chaque execute() commit immédiatement.
    Plus de risque de "transaction aborted" après une erreur SQL. Idéal
    pour les bulk imports où chaque ligne est indépendante.

    Avec autocommit=False : transaction unique pour le bloc entier (utile
    pour des ops liées qui doivent être atomiques).

    Usage :
        with session() as s:                # autocommit
            for row in big_list:
                try:
                    M.upsert_prospect(row)  # commit auto après chaque op
                except Exception:
                    pass                    # connection reste utilisable
    """
    conn = get_conn()
    if autocommit:
        conn.autocommit = True
    cur = conn.cursor()
    _session_local.cursor = cur
    _session_local.conn = conn
    try:
        yield _SessionHandle(conn, cur, autocommit)
        if not autocommit:
            conn.commit()
    except Exception:
        if not autocommit:
            conn.rollback()
        raise
    finally:
        _session_local.cursor = None
        _session_local.conn = None
        conn.close()


class _SessionHandle:
    """Handle retourné par session()."""

    def __init__(self, conn, cur, autocommit):
        self._conn = conn
        self._cur = cur
        self._autocommit = autocommit

    def rollback(self):
        """Force un rollback si la transaction est en état aborted
        (utile en mode non-autocommit si une erreur SQL a leak)."""
        if not self._autocommit:
            self._conn.rollback()


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
        # ADEME RGE imports (Carnet Plein®) : conserve le SIRET pour dédup + audit
        ("prospects", "siret",         "TEXT"),
        # Daily send rate-limit pour campagnes bulk (warm-up domaine,
        # éviter d'envoyer 5000 emails d'un coup). NULL = pas de limite.
        ("campaigns",  "daily_send_limit", "INTEGER"),
        # Niche métier : plombier_chauffagiste / electricien / couvreur / ...
        # NULL = inconnu. Permet de filtrer la base par cœur de cible.
        ("prospects",  "metier",          "TEXT"),
    ]
    for tbl, col, typ in additions:
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema='public' AND table_name=%s AND column_name=%s
        """, (tbl, col))
        if not cur.fetchone():
            cur.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {typ}")
            log.info(f"Migration : {tbl}.{col} ajouté")

    # Index siret (créé après l'ALTER pour que la colonne existe sur les DB upgraded)
    cur.execute("""
        SELECT indexname FROM pg_indexes
        WHERE schemaname='public' AND indexname='idx_prospects_siret'
    """)
    if not cur.fetchone():
        cur.execute("CREATE INDEX idx_prospects_siret ON prospects(siret) WHERE siret IS NOT NULL")
        log.info("Index idx_prospects_siret créé")

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

    # Table email_templates
    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema='public' AND table_name='email_templates'
    """)
    if not cur.fetchone():
        cur.execute("""
            CREATE TABLE email_templates (
                id              BIGSERIAL PRIMARY KEY,
                name            TEXT NOT NULL,
                description     TEXT,
                category        TEXT,
                segment         TEXT,
                step            TEXT,
                subject         TEXT NOT NULL,
                body_html       TEXT NOT NULL,
                variables_used  TEXT,
                is_archived     BOOLEAN NOT NULL DEFAULT FALSE,
                created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("CREATE INDEX idx_tpls_segment ON email_templates(segment)")
        cur.execute("CREATE INDEX idx_tpls_step ON email_templates(step)")
        cur.execute("CREATE INDEX idx_tpls_active ON email_templates(is_archived)")
        log.info("Table email_templates créée")

    # ── Tables campagnes ──────────────────────────────────────
    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema='public' AND table_name='campaigns'
    """)
    if not cur.fetchone():
        cur.execute("""
            CREATE TABLE campaigns (
                id              BIGSERIAL PRIMARY KEY,
                name            TEXT NOT NULL,
                description     TEXT,
                status          TEXT NOT NULL DEFAULT 'draft',
                from_user_id    BIGINT REFERENCES users(id) ON DELETE SET NULL,
                created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
                started_at      TIMESTAMPTZ,
                completed_at    TIMESTAMPTZ,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("CREATE INDEX idx_campaigns_status ON campaigns(status)")
        log.info("Table campaigns créée")

    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema='public' AND table_name='campaign_steps'
    """)
    if not cur.fetchone():
        cur.execute("""
            CREATE TABLE campaign_steps (
                id              BIGSERIAL PRIMARY KEY,
                campaign_id     BIGINT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
                step_number     INTEGER NOT NULL,
                delay_days      INTEGER NOT NULL DEFAULT 0,
                delay_hours     INTEGER NOT NULL DEFAULT 0,
                template_id     BIGINT REFERENCES email_templates(id) ON DELETE SET NULL,
                custom_subject  TEXT,
                custom_body     TEXT,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("CREATE INDEX idx_steps_campaign ON campaign_steps(campaign_id)")
        log.info("Table campaign_steps créée")

    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema='public' AND table_name='campaign_targets'
    """)
    if not cur.fetchone():
        cur.execute("""
            CREATE TABLE campaign_targets (
                id              BIGSERIAL PRIMARY KEY,
                campaign_id     BIGINT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
                prospect_id     BIGINT NOT NULL REFERENCES prospects(id) ON DELETE CASCADE,
                status          TEXT NOT NULL DEFAULT 'active',
                stop_reason     TEXT,
                started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                completed_at    TIMESTAMPTZ,
                last_step_sent  INTEGER NOT NULL DEFAULT 0,
                UNIQUE (campaign_id, prospect_id)
            )
        """)
        cur.execute("CREATE INDEX idx_targets_campaign ON campaign_targets(campaign_id)")
        cur.execute("CREATE INDEX idx_targets_prospect ON campaign_targets(prospect_id)")
        cur.execute("CREATE INDEX idx_targets_status   ON campaign_targets(status)")
        log.info("Tables campaign_steps + campaign_targets créées")

    # Lien emails → campagne (optionnel : un email peut venir d'une campagne)
    for col, typ in [
        ("campaign_id",      "BIGINT REFERENCES campaigns(id) ON DELETE SET NULL"),
        ("campaign_step_id", "BIGINT REFERENCES campaign_steps(id) ON DELETE SET NULL"),
    ]:
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema='public' AND table_name='emails' AND column_name=%s
        """, (col,))
        if not cur.fetchone():
            cur.execute(f"ALTER TABLE emails ADD COLUMN {col} {typ}")
            log.info(f"Migration : emails.{col} ajouté")


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
