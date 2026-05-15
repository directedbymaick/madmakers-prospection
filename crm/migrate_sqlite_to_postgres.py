"""crm.migrate_sqlite_to_postgres — transfère le contenu de la DB SQLite
   locale (crm/data/crm.db) vers Supabase Postgres.

Usage :
    python -X utf8 -m crm.migrate_sqlite_to_postgres
    python -X utf8 -m crm.migrate_sqlite_to_postgres --reset

Stratégie :
- Source : sqlite3 sur crm/data/crm.db
- Cible  : DATABASE_URL (Postgres Supabase via Session Pooler)
- Pour chaque table : SELECT * → INSERT en batch
- Préserve les ids (pour garder les FK cohérentes audits/calls/activities/emails → prospects)
- Réaligne les séquences Postgres après import (sinon prochain INSERT crash)
"""
import argparse
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env BEFORE importing crm modules
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from .db import get_conn, init_db

SQLITE_PATH = Path(__file__).resolve().parent / "data" / "crm.db"

# Tables dans l'ordre des dépendances (parents avant enfants)
TABLES = [
    "users",
    "prospects",
    "audits",
    "calls",
    "activities",
    "emails",
]

# Colonnes à transférer par table (exclut celles qui n'existent pas en SQLite)
COLUMNS = {
    "users": [
        "id", "email", "password_hash", "full_name", "role",
        "email_verified", "is_active",
        "created_at", "updated_at", "last_login_at", "verification_sent_at",
    ],
    "prospects": [
        "id", "nom_complet", "prenom", "nom", "titre", "entreprise", "ville",
        "email", "phone_mobile", "phone_office", "phone_other",
        "linkedin_url", "entreprise_linkedin", "site_url", "domaine",
        "categorie", "veillot_signals", "recent_signals",
        "copyright_year", "fetch_error",
        "stage", "interet", "notes",
        "last_contacted_at", "next_action", "next_action_due",
        "source", "created_at", "updated_at",
    ],
    "audits": [
        "id", "prospect_id", "final_url", "https", "tls_version",
        "security_grade", "technos", "veillot_tags",
        "title", "description", "h1", "copyright_year",
        "html_size_kb", "image_count", "modern_image_count",
        "findings", "raw_data", "created_at",
    ],
    "calls": [
        "id", "prospect_id", "call_number", "state", "statut",
        "summary", "next_action", "rdv2_date", "rdv2_heure", "interet",
        "roi_valeur_client", "roi_leads", "roi_conversion", "roi_devis",
        "roi_gain_mensuel", "roi_payback_mois",
        "visuels_promis", "budget_recu",
        "started_at", "completed_at",
    ],
    "activities": [
        "id", "prospect_id", "type", "title", "body", "metadata",
        "due_at", "completed_at", "created_at",
    ],
    "emails": [
        "id", "prospect_id", "sequence_step", "subject", "body", "status",
        "scheduled_at", "sent_at", "opened_at", "replied_at", "created_at",
    ],
}

# Colonnes booléennes : SQLite stocke 0/1 (INTEGER), Postgres veut TRUE/FALSE
BOOLEAN_COLS = {
    "users": {"email_verified", "is_active"},
    "audits": {"https"},
}

# Colonnes INTEGER (Postgres) : empty string "" doit devenir NULL
INTEGER_COLS = {
    "prospects": {"interet"},
    "audits": {"copyright_year", "image_count", "modern_image_count"},
    "calls": {"call_number", "interet"},
}

# Colonnes REAL/NUMERIC : empty string "" doit devenir NULL
REAL_COLS = {
    "audits": {"html_size_kb"},
    "calls": {"roi_valeur_client", "roi_leads", "roi_conversion", "roi_devis",
              "roi_gain_mensuel", "roi_payback_mois"},
}


def _convert_value(table: str, col: str, value):
    """Convertit une valeur SQLite en valeur Postgres."""
    if value is None:
        return None
    # Bools : INTEGER 0/1 → True/False
    if col in BOOLEAN_COLS.get(table, set()):
        return bool(value)
    # INTEGER : "" → NULL
    if col in INTEGER_COLS.get(table, set()):
        if isinstance(value, str) and value.strip() == "":
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    # REAL : "" → NULL
    if col in REAL_COLS.get(table, set()):
        if isinstance(value, str) and value.strip() == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    # Strings TIMESTAMPTZ : SQLite stocke "" pour vide → NULL côté Postgres
    if (col.endswith("_at") or col.endswith("_due")) and isinstance(value, str) and value.strip() == "":
        return None
    return value


def migrate(reset: bool = False):
    if not SQLITE_PATH.exists():
        sys.exit(f"ERREUR : SQLite source introuvable : {SQLITE_PATH}")

    init_db()  # idempotent
    print(f"Source SQLite : {SQLITE_PATH}")

    # Reset Postgres si demandé
    if reset:
        from . import db as PG
        conn = PG.get_conn()
        try:
            with conn.cursor() as cur:
                # TRUNCATE CASCADE pour respecter les FK
                cur.execute("TRUNCATE TABLE emails, activities, calls, audits, prospects, users RESTART IDENTITY CASCADE")
            conn.commit()
            print("RESET : toutes les tables Postgres vidées.")
        finally:
            conn.close()

    src = sqlite3.connect(SQLITE_PATH)
    src.row_factory = sqlite3.Row

    pg = get_conn()
    pg.autocommit = False

    try:
        totals = {}
        for table in TABLES:
            cols = COLUMNS[table]
            placeholders = ", ".join(["%s"] * len(cols))
            col_list = ", ".join(cols)
            insert_sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING"

            # Lit toutes les rows SQLite
            try:
                src_cur = src.execute(f"SELECT {col_list} FROM {table}")
                rows = src_cur.fetchall()
            except sqlite3.OperationalError as e:
                # Table n'existe pas dans la SQLite source (ex: users si DB ancienne)
                print(f"  ⚠ {table:12s} : skip ({e})")
                continue

            if not rows:
                print(f"  ø {table:12s} : 0 rows")
                totals[table] = 0
                continue

            # Convertir et insérer
            batch = []
            for r in rows:
                row_vals = tuple(_convert_value(table, c, r[c]) for c in cols)
                batch.append(row_vals)

            with pg.cursor() as cur:
                cur.executemany(insert_sql, batch)
                inserted = cur.rowcount

            print(f"  ✓ {table:12s} : {inserted}/{len(rows)} rows")
            totals[table] = inserted

        # Réaligne les séquences (sinon prochain INSERT crash avec duplicate key)
        with pg.cursor() as cur:
            for table in TABLES:
                cur.execute(f"""
                    SELECT setval(
                        pg_get_serial_sequence('{table}', 'id'),
                        COALESCE((SELECT MAX(id) FROM {table}), 1)
                    )
                """)
        print("✓ Séquences réalignées (max(id) de chaque table)")

        pg.commit()
        print(f"\n=== Migration terminée. Totaux Postgres ===")
        for t, n in totals.items():
            print(f"  {t:12s} : {n}")

    except Exception:
        pg.rollback()
        raise
    finally:
        src.close()
        pg.close()


def main():
    parser = argparse.ArgumentParser(description="Migrate SQLite → Postgres (Supabase)")
    parser.add_argument("--reset", action="store_true",
                        help="Vide les tables Postgres avant import (destructif)")
    args = parser.parse_args()

    if args.reset:
        ans = input("Reset complet des tables Postgres avant import ? [y/N] ").strip().lower()
        if ans != "y":
            print("Annulé.")
            return

    migrate(reset=args.reset)


if __name__ == "__main__":
    main()
