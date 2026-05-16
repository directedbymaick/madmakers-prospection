"""scrape_rge_ademe.py
Récupère les entreprises RGE depuis l'API officielle ADEME (dataset
`liste-des-entreprises-rge-2`, 164 500 entreprises mises à jour quotidiennement).

Filtre Carnet Plein® : plombiers/chauffagistes en IDF + HDF + Grand Est.

Domaines RGE ciblés (plomberie / chauffage / énergies renouvelables thermique) :
- Pompe à chaleur : chauffage (PAC)
- Chaudière condensation ou micro-cogénération gaz ou fioul
- Chauffe-Eau Thermodynamique
- Chaudière bois
- Chauffage et/ou eau chaude solaire
- Poêle ou insert bois

Output : CSV dans `linkedin-scraper/data/inputs/qualibat_rge_<date>.csv` au format
prêt pour import dans le CRM (page Imports).

Usage :
    python -X utf8 scripts/scrape_rge_ademe.py                 # IDF + HDF + Grand Est
    python -X utf8 scripts/scrape_rge_ademe.py --dept 75 77    # depts custom
    python -X utf8 scripts/scrape_rge_ademe.py --domain pac    # filtre rapide

Pas besoin d'API key (open data ADEME).
"""
import argparse
import csv
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

API_BASE = "https://data.ademe.fr/data-fair/api/v1/datasets/liste-des-entreprises-rge-2/lines"

# ── Domaines ciblés Carnet Plein® (plombier/chauffagiste/PAC) ─────
TARGET_DOMAINS = [
    "Pompe à chaleur : chauffage",
    "Chaudière condensation ou micro-cogénération gaz ou fioul",
    "Chauffe-Eau Thermodynamique",
    "Chaudière bois",
    "Chauffage et/ou eau chaude solaire",
    "Poêle ou insert bois",
]

# ── Régions Carnet Plein® → departements ─────────────────────────
REGIONS = {
    "IDF":         ["75", "77", "78", "91", "92", "93", "94", "95"],
    "HDF":         ["02", "59", "60", "62", "80"],
    "GRAND_EST":   ["08", "10", "51", "52", "54", "55", "57", "67", "68", "88"],
}

DEFAULT_DEPARTMENTS = REGIONS["IDF"] + REGIONS["HDF"] + REGIONS["GRAND_EST"]

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "inputs"

UA = {"User-Agent": "Mozilla/5.0 MadMakers-CRM-scraper"}

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    datefmt="%H:%M:%S")


def _escape_phrase(s: str) -> str:
    """Escape Elasticsearch query string special chars."""
    return s.replace('"', '\\"')


def build_query(departments: list[str], domains: list[str]) -> str:
    """Build Elasticsearch query string for the API."""
    dept_clauses = " OR ".join(f"code_postal:{d}*" for d in departments)
    domain_clauses = " OR ".join(f'domaine:"{_escape_phrase(d)}"' for d in domains)
    return f"({dept_clauses}) AND ({domain_clauses})"


def fetch_page(qs: str, after: str | None = None, size: int = 1000) -> dict:
    """Fetch one page using cursor-based pagination (after param)."""
    params = {
        "qs": qs,
        "size": size,
        "sort": "siret",  # tri stable pour pagination cursor
        "select": "siret,nom_entreprise,adresse,code_postal,commune,telephone,email,"
                  "site_internet,domaine,nom_qualification,meta_domaine,_geopoint",
    }
    if after:
        params["after"] = after

    r = requests.get(API_BASE, params=params, headers=UA, timeout=20)
    r.raise_for_status()
    return r.json()


def iter_results(qs: str, max_total: int | None = None):
    """Iterator on all results, with cursor pagination."""
    after = None
    total_fetched = 0
    page_idx = 0
    while True:
        data = fetch_page(qs, after=after)
        results = data.get("results", [])
        total_estimate = data.get("total", 0)

        if page_idx == 0:
            log.info(f"Total estimate : {total_estimate} lignes (avec doublons par qualification)")

        if not results:
            break

        for row in results:
            yield row
            total_fetched += 1
            if max_total and total_fetched >= max_total:
                return

        # next cursor
        nxt = data.get("next")
        if not nxt:
            break
        # The API returns a full URL in `next` ; we just need the `after` param
        from urllib.parse import urlparse, parse_qs
        after = parse_qs(urlparse(nxt).query).get("after", [None])[0]
        if not after:
            break

        page_idx += 1
        if page_idx % 5 == 0:
            log.info(f"  ... page {page_idx}, {total_fetched} lignes lues")
        time.sleep(0.1)  # politesse


def normalize_row(raw: dict) -> dict:
    """Transforme une row ADEME en format CRM (compatible importer.py)."""
    nom_entreprise = (raw.get("nom_entreprise") or "").strip().title()
    siret = (raw.get("siret") or "").strip()
    commune = (raw.get("commune") or "").strip().title()
    code_postal = (raw.get("code_postal") or "").strip()
    adresse = (raw.get("adresse") or "").strip()
    telephone = (raw.get("telephone") or "").strip()
    email = (raw.get("email") or "").strip().lower()
    site = (raw.get("site_internet") or "").strip()
    domaine = (raw.get("domaine") or "").strip()
    qualification = (raw.get("nom_qualification") or "").strip()

    ville_full = f"{commune} ({code_postal})" if commune and code_postal else (commune or code_postal)

    return {
        "siret":            siret,
        "nom_complet":      nom_entreprise,   # placeholder : le dirigeant sera enrichi ultérieurement
        "prenom":           "",
        "nom":              "",
        "titre":            "Direction",
        "entreprise":       nom_entreprise,
        "ville":            ville_full,
        "email":            email,
        "phone_office":     telephone,
        "site_url":         site,
        "domaine":          domaine,
        "linkedin_url":     "",
        "source":           "ademe_rge",
        "categorie":        "sans_site" if not site else "avec_site_veillot",
        "notes":            f"RGE : {qualification} · Adresse : {adresse}",
        # raw extra fields pour usage potentiel
        "rge_qualifications": qualification,
        "code_postal":      code_postal,
    }


def dedupe_by_siret(rows: list[dict]) -> list[dict]:
    """Une entreprise peut avoir plusieurs qualifications → 1 row par qualif.
    On déduplique par SIRET en gardant la première occurrence + agrège qualifs."""
    seen = {}
    for r in rows:
        siret = r["siret"] or f"_no_siret_{r['entreprise']}_{r['ville']}"
        if siret in seen:
            # Append la qualif
            old_quals = seen[siret].get("rge_qualifications", "")
            new_qual = r.get("rge_qualifications", "")
            if new_qual and new_qual not in old_quals:
                seen[siret]["rge_qualifications"] = (
                    (old_quals + " · " + new_qual) if old_quals else new_qual
                )
        else:
            seen[siret] = r
    return list(seen.values())


def write_csv(rows: list[dict], output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        log.warning("Aucune ligne à écrire")
        return
    cols = [
        "siret", "nom_complet", "prenom", "nom", "titre", "entreprise",
        "ville", "code_postal", "email", "phone_office", "site_url",
        "domaine", "linkedin_url", "source", "categorie", "notes",
        "rge_qualifications",
    ]
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    log.info(f"CSV écrit : {output_path} ({len(rows)} lignes uniques)")


def main():
    parser = argparse.ArgumentParser(description="Scrape RGE companies from ADEME official API")
    parser.add_argument("--dept", nargs="+", help="Liste de départements (ex: 75 77 92)")
    parser.add_argument("--region", choices=["IDF", "HDF", "GRAND_EST", "ALL"],
                        help="Région prédéfinie (IDF / HDF / GRAND_EST / ALL = Carnet Plein® par défaut)")
    parser.add_argument("--domain", help="Filtre rapide sur 1 domaine (substring)")
    parser.add_argument("--max", type=int, help="Limite max de lignes brutes (avant dédup)")
    parser.add_argument("--output", help="Chemin CSV custom")
    args = parser.parse_args()

    # Resolve departments
    if args.dept:
        departments = args.dept
    elif args.region == "IDF":
        departments = REGIONS["IDF"]
    elif args.region == "HDF":
        departments = REGIONS["HDF"]
    elif args.region == "GRAND_EST":
        departments = REGIONS["GRAND_EST"]
    else:
        departments = DEFAULT_DEPARTMENTS

    # Resolve domains
    if args.domain:
        domains = [d for d in TARGET_DOMAINS if args.domain.lower() in d.lower()]
        if not domains:
            log.error(f"Aucun domaine ne matche '{args.domain}'. Disponibles : {TARGET_DOMAINS}")
            sys.exit(1)
    else:
        domains = TARGET_DOMAINS

    log.info(f"Régions/depts : {departments}")
    log.info(f"Domaines RGE : {domains}")

    qs = build_query(departments, domains)
    log.info(f"Query : {qs}")

    # Fetch all results
    raw_rows = []
    for raw in iter_results(qs, max_total=args.max):
        raw_rows.append(normalize_row(raw))

    log.info(f"Lignes brutes (avec doublons par qualif) : {len(raw_rows)}")

    # Dedupe
    unique_rows = dedupe_by_siret(raw_rows)
    log.info(f"Lignes uniques (par SIRET) : {len(unique_rows)}")

    # Stats
    with_email = sum(1 for r in unique_rows if r["email"])
    with_phone = sum(1 for r in unique_rows if r["phone_office"])
    with_site  = sum(1 for r in unique_rows if r["site_url"])
    log.info(f"  avec email   : {with_email} ({100*with_email//max(len(unique_rows),1)}%)")
    log.info(f"  avec phone   : {with_phone} ({100*with_phone//max(len(unique_rows),1)}%)")
    log.info(f"  avec site    : {with_site} ({100*with_site//max(len(unique_rows),1)}%)")

    # Output
    today = datetime.now().strftime("%Y%m%d")
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = OUTPUT_DIR / f"qualibat_rge_carnetplein_{today}.csv"

    write_csv(unique_rows, output_path)

    print(f"\n✓ Terminé. Importe le CSV dans le CRM via /imports :")
    print(f"  {output_path}")


if __name__ == "__main__":
    main()
