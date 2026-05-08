"""crm.import_prospects — charge les 500 prospects du CSV triage dans la DB.

Usage :
    python -X utf8 -m crm.import_prospects
    python -X utf8 -m crm.import_prospects --csv path/to/file.csv --reset
"""
import argparse
import csv
import sys
from pathlib import Path
from datetime import datetime

from .db import init_db, execute, query_one
from .models import upsert_prospect, create_activity

DATA_DIR = Path(__file__).resolve().parent.parent / "linkedin-scraper" / "data"


def find_default_csv():
    """Le CSV final le plus récent."""
    candidates = sorted(DATA_DIR.glob("prospects_triage_final_*.csv"), reverse=True)
    if not candidates:
        candidates = sorted(DATA_DIR.glob("prospects_triage_strict_*_recheck.csv"), reverse=True)
    if not candidates:
        candidates = sorted(DATA_DIR.glob("prospects_triage_strict_*.csv"), reverse=True)
    if not candidates:
        sys.exit(f"ERREUR : aucun CSV triage trouvé dans {DATA_DIR}")
    return candidates[0]


def import_csv(csv_path: Path, reset: bool = False):
    init_db()

    if reset:
        from .db import cursor
        with cursor() as c:
            c.execute("DELETE FROM emails")
            c.execute("DELETE FROM activities")
            c.execute("DELETE FROM calls")
            c.execute("DELETE FROM audits")
            c.execute("DELETE FROM prospects")
            c.execute("DELETE FROM sqlite_sequence")
        print("RESET : toutes les tables vidées.")

    with open(csv_path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    print(f"Lecture : {csv_path.name} ({len(rows)} lignes)")

    inserted = 0
    updated = 0
    for r in rows:
        nom_complet = (r.get("nom_complet") or "").strip()
        if not nom_complet:
            continue

        # Existence avant upsert pour compter
        existing = query_one(
            "SELECT id FROM prospects WHERE nom_complet = ? AND entreprise = ?",
            (nom_complet, (r.get("entreprise") or "").strip()),
        )

        data = {
            "nom_complet":         nom_complet,
            "prenom":              (r.get("prenom") or "").strip(),
            "nom":                 (r.get("nom") or "").strip(),
            "titre":               (r.get("titre") or "").strip(),
            "entreprise":          (r.get("entreprise") or "").strip(),
            "ville":               (r.get("ville") or "").strip(),
            "email":               (r.get("email") or "").strip(),
            "linkedin_url":        (r.get("linkedin_url") or "").strip(),
            "entreprise_linkedin": (r.get("entreprise_linkedin") or "").strip(),
            "site_url":            (r.get("site_url") or "").strip(),
            "domaine":             (r.get("domaine") or "").strip(),
            "categorie":           (r.get("categorie") or "sans_site").strip(),
            "veillot_signals":     (r.get("veillot_signals") or "").strip(),
            "recent_signals":      (r.get("recent_signals") or "").strip(),
            "copyright_year":      (r.get("copyright_year") or "").strip(),
            "fetch_error":         (r.get("fetch_error") or "").strip(),
            "source":              "rocketreach",
        }
        # Default stage : a_contacter pour les nouveaux
        if not existing:
            data["stage"] = "a_contacter"

        pid = upsert_prospect(data)

        if existing:
            updated += 1
        else:
            inserted += 1
            create_activity(
                pid, "note",
                f"Import RocketReach — catégorie : {data['categorie']}",
                f"Importé depuis {csv_path.name} le {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            )

    print(f"\nImport terminé.")
    print(f"  Insérés : {inserted}")
    print(f"  Mis à jour : {updated}")

    # Distribution finale
    from .models import stats_overview
    s = stats_overview()
    print(f"\nDistribution finale :")
    for cat, n in s["by_cat"].items():
        print(f"  {cat:25s} : {n}")
    print(f"\nTotal en base : {s['total']} prospects")


def main():
    parser = argparse.ArgumentParser(description="Import prospects CSV → SQLite CRM")
    parser.add_argument("--csv", help="CSV triage à importer (par défaut : le plus récent)")
    parser.add_argument("--reset", action="store_true",
                        help="Vide TOUTE la base avant import (destructif)")
    args = parser.parse_args()

    csv_path = Path(args.csv) if args.csv else find_default_csv()
    if not csv_path.exists():
        sys.exit(f"ERREUR : {csv_path} introuvable")

    if args.reset:
        if input("Reset complet de la base ? [y/N] ").lower() != "y":
            print("Annulé.")
            return

    import_csv(csv_path, reset=args.reset)


if __name__ == "__main__":
    main()
