"""crm.enrich_phones — peuple les colonnes phone_* depuis les CSVs RocketReach raw.

Match par (nom_complet + entreprise) ou par LinkedIn URL.

Usage :
    python -X utf8 -m crm.enrich_phones
    python -X utf8 -m crm.enrich_phones --inputs path/to/inputs/dir
"""
import argparse
import csv
import re
import sys
from pathlib import Path

from .db import init_db, query, execute

INPUTS_DIR = Path(__file__).resolve().parent.parent / "linkedin-scraper" / "data" / "inputs"


def _clean_phone(s: str) -> str:
    """Normalise grossièrement un numéro : trim, fix séparateurs, prefix +33 si FR sans +."""
    if not s:
        return ""
    s = s.strip().replace(" ", "").replace(".", "").replace("-", "")
    if not s:
        return ""
    # 06xxxxxxxx ou 01... → +33 6xxxxxxxx
    if re.match(r"^0\d{9}$", s):
        return f"+33 {s[1]} {s[2:4]} {s[4:6]} {s[6:8]} {s[8:10]}"
    # 33xxxxxxxxx (sans +) → +33 ...
    if re.match(r"^33\d{9}$", s):
        rest = s[2:]
        return f"+33 {rest[0]} {rest[1:3]} {rest[3:5]} {rest[5:7]} {rest[7:9]}"
    # 0033... → +33...
    if s.startswith("0033"):
        rest = s[4:]
        if len(rest) == 9:
            return f"+33 {rest[0]} {rest[1:3]} {rest[3:5]} {rest[5:7]} {rest[7:9]}"
    # +33... déjà bien formé
    if s.startswith("+33"):
        rest = s[3:]
        if len(rest) == 9:
            return f"+33 {rest[0]} {rest[1:3]} {rest[3:5]} {rest[5:7]} {rest[7:9]}"
    # International ou inconnu : retourne tel quel
    return s


def find_input_csvs(inputs_dir: Path):
    return sorted(inputs_dir.glob("rocketreach_bulk_*.csv"))


def enrich(inputs_dir: Path):
    init_db()
    csvs = find_input_csvs(inputs_dir)
    if not csvs:
        sys.exit(f"ERREUR : aucun CSV RocketReach dans {inputs_dir}")

    # Index DB : (nom_complet_lower, entreprise_lower) → id  ET linkedin_url → id
    db_rows = query("SELECT id, nom_complet, entreprise, linkedin_url FROM prospects")
    by_name_company = {}
    by_linkedin = {}
    for r in db_rows:
        nc = (r.get("nom_complet") or "").strip().lower()
        ent = (r.get("entreprise") or "").strip().lower()
        if nc and ent:
            by_name_company[(nc, ent)] = r["id"]
        if nc:
            by_name_company.setdefault((nc, ""), r["id"])
        li = (r.get("linkedin_url") or "").strip().lower().rstrip("/")
        if li:
            by_linkedin[li] = r["id"]

    print(f"DB : {len(db_rows)} prospects indexés")
    print(f"Sources : {len(csvs)} CSVs RocketReach")

    updated = 0
    not_found = 0
    no_phone = 0

    for csv_path in csvs:
        with open(csv_path, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                full = (r.get("Input - Full Name") or
                        f"{r.get('First Name','')} {r.get('Last Name','')}".strip()).strip()
                ent = (r.get("Employer") or r.get("Input - Current Employer") or "").strip()
                li = (r.get("Input - LinkedIn URL") or r.get("LinkedIn") or "").strip().lower().rstrip("/")

                pid = None
                if li and li in by_linkedin:
                    pid = by_linkedin[li]
                elif full and ent and (full.lower(), ent.lower()) in by_name_company:
                    pid = by_name_company[(full.lower(), ent.lower())]
                elif full and (full.lower(), "") in by_name_company:
                    pid = by_name_company[(full.lower(), "")]

                if not pid:
                    not_found += 1
                    continue

                phone     = _clean_phone(r.get("Phone", ""))
                mobile    = _clean_phone(r.get("Mobile Phone", ""))
                office    = _clean_phone(r.get("Office Phone", ""))
                other_raw = (r.get("Other Phones") or "").strip()

                # Logique de répartition :
                # - phone_mobile = Mobile Phone si dispo, sinon Phone si pas de Mobile
                # - phone_office = Office Phone
                # - phone_other = Other Phones + (Phone si déjà mis en mobile via fallback)
                pm = mobile or (phone if phone != office else "")
                po = office
                px_parts = []
                if other_raw:
                    px_parts.extend(_clean_phone(p) for p in re.split(r"[,;]", other_raw) if p.strip())
                if phone and phone != pm and phone != po:
                    px_parts.insert(0, phone)
                px = "; ".join(p for p in px_parts if p) or None

                if not (pm or po or px):
                    no_phone += 1
                    continue

                execute(
                    """UPDATE prospects SET
                        phone_mobile = COALESCE(?, phone_mobile),
                        phone_office = COALESCE(?, phone_office),
                        phone_other  = COALESCE(?, phone_other)
                       WHERE id = ?""",
                    (pm or None, po or None, px, pid),
                )
                updated += 1

    print(f"\nEnrichissement terminé.")
    print(f"  Prospects mis à jour    : {updated}")
    print(f"  Pas trouvés en DB        : {not_found}")
    print(f"  Sans aucun phone         : {no_phone}")


def main():
    parser = argparse.ArgumentParser(description="Enrich CRM prospects with phone numbers from RocketReach raw CSVs")
    parser.add_argument("--inputs", help="Dossier contenant les rocketreach_bulk_*.csv")
    args = parser.parse_args()
    enrich(Path(args.inputs) if args.inputs else INPUTS_DIR)


if __name__ == "__main__":
    main()
