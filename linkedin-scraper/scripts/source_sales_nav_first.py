"""
source_sales_nav_first.py — Pipeline LinkedIn-first (canal cold email)

Workflow :
  1. Tu fais ta recherche Sales Navigator avec tes filtres (taille, geo, role)
  2. Phantombuster "Sales Navigator Search Export" produit un CSV
  3. Ce script ingere le CSV, enrichit chaque ligne via INSEE (SIRET, raison sociale,
     effectif, forme juridique, age entreprise) puis (optionnel) verifie l'absence
     de site via Google Places
  4. Output : CSV "rocket_reach_ready_YYYYMMDD.csv" pret pour Rocket Reach
     (toutes les colonnes Phantombuster + colonnes d'enrichissement)

Usage :
    python -X utf8 scripts/source_sales_nav_first.py \\
        --input "C:/path/to/phantombuster_export.csv" \\
        --check-website

Options :
    --input PATH        : CSV Phantombuster Sales Nav (obligatoire)
    --check-website     : verifie l'absence de site web via Google Places (recommande)
    --limit N           : limiter aux N premieres lignes (test)
    --only-no-site      : ne garder que les prospects sans site dans l'output
    --min-effectif N    : filtrer par effectif min (1, 5, 10...) ; 0 = tous
"""
import argparse, csv, os, re, sys, time, unicodedata
from datetime import datetime
from pathlib import Path
import requests
from dotenv import load_dotenv

ENV_PATH = Path(r"C:\Users\MAÏCK\Desktop\MadMakers Prospection\madmakers-prospection-main\.env")
load_dotenv(ENV_PATH)

INSEE_KEY  = os.getenv("INSEE_API_KEY")
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")

INSEE_URL  = "https://api.insee.fr/api-sirene/3.11/siret"
PLACES_URL = "https://places.googleapis.com/v1/places:searchText"

DATA_DIR = Path(r"C:\Users\MAÏCK\Desktop\MadMakers Prospection\linkedin-scraper\data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

TODAY = datetime.now().strftime("%Y%m%d")

# Mapping codes INSEE -> formes juridiques courantes
CATEGORIES_JURIDIQUES = {
    "1000": "Entrepreneur individuel",
    "5202": "SNC",
    "5203": "SNC",
    "5306": "SCS",
    "5307": "SCA",
    "5410": "SARL",
    "5415": "SARL unipersonnelle",
    "5422": "SARL",
    "5426": "SARL d'expertise",
    "5430": "SARL associations",
    "5431": "SARL coopérative",
    "5432": "SARL union",
    "5442": "SARL d'attribution",
    "5443": "SARL coopérative",
    "5451": "SARL",
    "5453": "SARL",
    "5454": "SARL",
    "5455": "SARL",
    "5458": "SARL d'investissement",
    "5459": "SARL",
    "5460": "SARL",
    "5470": "SARL",
    "5485": "EURL",
    "5498": "SARL",
    "5499": "SARL",
    "5505": "SA",
    "5510": "SA",
    "5515": "SA",
    "5520": "SA",
    "5530": "SA",
    "5531": "SA d'attribution",
    "5532": "SA coopérative",
    "5542": "SA",
    "5543": "SA",
    "5546": "SA",
    "5547": "SA",
    "5548": "SA",
    "5551": "SA",
    "5552": "SA",
    "5553": "SA",
    "5554": "SA",
    "5555": "SA",
    "5558": "SA",
    "5559": "SA",
    "5560": "SA",
    "5570": "SA",
    "5585": "SA d'investissement",
    "5599": "SA",
    "5710": "SAS",
    "5720": "SASU",
    "5800": "SAS",
}

# Tranches d'effectifs INSEE (codes officiels)
TRANCHES_EFFECTIFS = {
    "":   ("inconnu", 0),
    "NN": ("non declare", 0),
    "00": ("0 salarie", 0),
    "01": ("1-2", 1),
    "02": ("3-5", 3),
    "03": ("6-9", 6),
    "11": ("10-19", 10),
    "12": ("20-49", 20),
    "21": ("50-99", 50),
    "22": ("100-199", 100),
    "31": ("200-249", 200),
    "32": ("250-499", 250),
    "41": ("500-999", 500),
    "42": ("1000-1999", 1000),
    "51": ("2000-4999", 2000),
    "52": ("5000-9999", 5000),
    "53": ("10000+", 10000),
}


def short_forme(code: str) -> str:
    return CATEGORIES_JURIDIQUES.get(code or "", code or "")


def normalize(s: str) -> str:
    """Uppercase, strip accents, collapse whitespace, remove punctuation."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^\w\s]", " ", s).upper().strip()
    s = re.sub(r"\s+", " ", s)
    return s


# Suffixes courants ajoutes par Sales Nav apres le nom de la societe
SN_SEPARATORS = [" - ", " — ", " – ", " | ", " · ", " / ", " @ "]
# Suffixes legaux a stripper en derniere position
LEGAL_SUFFIXES = re.compile(r"\s+(SARL|SAS|SASU|EURL|SA|SCI|SCP|SCM|EI|SNC|SCS|SCA)$",
                            re.IGNORECASE)


def clean_company_name(name: str) -> str:
    """Nettoie le nom commercial Sales Nav pour maximiser le match INSEE."""
    if not name:
        return ""
    # Coupe au premier separateur (ex : "SNAKKAR - Marcus Detrez" -> "SNAKKAR")
    for sep in SN_SEPARATORS:
        idx = name.find(sep)
        if idx > 0:
            name = name[:idx]
    # Strippe parentheses en fin (ex : "Bcg (Boston Consulting Group)")
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name)
    # Strippe forme juridique en fin (ex : "DUPONT SARL" -> "DUPONT")
    name = LEGAL_SUFFIXES.sub("", name)
    return name.strip()


# Rate limit INSEE free plan : 30 req/min => 2.1s entre appels min
_LAST_INSEE_CALL = 0.0
INSEE_MIN_INTERVAL = 2.1


def _sirene_query(q: str, nombre: int = 10) -> list:
    """Helper pour appel INSEE avec rate-limit respect."""
    global _LAST_INSEE_CALL
    elapsed = time.time() - _LAST_INSEE_CALL
    if elapsed < INSEE_MIN_INTERVAL:
        time.sleep(INSEE_MIN_INTERVAL - elapsed)
    try:
        r = requests.get(INSEE_URL,
            params={"q": q, "nombre": nombre},
            headers={"X-INSEE-Api-Key-Integration": INSEE_KEY,
                     "Accept": "application/json"},
            timeout=20)
    except requests.RequestException:
        _LAST_INSEE_CALL = time.time()
        return []
    _LAST_INSEE_CALL = time.time()
    # Si 429 inattendu (concurrence ou window tres serree), retry une fois apres pause
    if r.status_code == 429:
        time.sleep(5)
        try:
            r = requests.get(INSEE_URL,
                params={"q": q, "nombre": nombre},
                headers={"X-INSEE-Api-Key-Integration": INSEE_KEY,
                         "Accept": "application/json"},
                timeout=20)
            _LAST_INSEE_CALL = time.time()
        except requests.RequestException:
            return []
    if r.status_code != 200:
        return []
    return r.json().get("etablissements", [])


def insee_match(company_name: str, city: str = "") -> dict | None:
    """Cherche l'entreprise dans INSEE. Strategie multi-passe :
       1. Nom nettoye (sans suffixes Sales Nav) sur denominationUsuelle puis denominationUniteLegale
       2. Premier mot seul si nom multi-mots (pour les marques type "KeyWe", "AKTAN")
       3. Filtre prioritaire par ville si fournie."""
    if not company_name or not INSEE_KEY:
        return None

    # Genere les noms candidats a essayer
    cleaned = clean_company_name(company_name)
    candidates = []
    if cleaned:
        candidates.append(normalize(cleaned))
    # Premier mot seul (souvent la marque pour les noms type "AKTAN International")
    words = cleaned.split() if cleaned else []
    if len(words) > 1 and len(words[0]) >= 3:
        candidates.append(normalize(words[0]))
    # Original au cas ou le cleaning a coupe trop
    if cleaned != company_name:
        candidates.append(normalize(company_name))
    # Dedup en gardant l'ordre
    candidates = list(dict.fromkeys(c for c in candidates if c and len(c) >= 2))

    city_norm = normalize(city) if city else ""

    # Une seule query INSEE qui combine TOUS les candidats dans denominationUniteLegale
    # (le champ usuelleUniteLegale n'existe pas sur l'endpoint /siret)
    # Lucene OR fonctionne uniquement entre valeurs du meme champ.
    # On filtre sur etatAdministratifUniteLegale (pas etablissement, qui doit etre dans periode())
    quoted = " OR ".join(f'"{c}"' for c in candidates)
    full_q = (f'denominationUniteLegale:({quoted}) '
              f'AND etatAdministratifUniteLegale:A')

    etabs = _sirene_query(full_q, nombre=20)
    if not etabs:
        return None
    # Filtrage post-fetch : etablissement actif aussi (pas qu'unite legale)
    etabs = [e for e in etabs
             if e.get("uniteLegale", {}).get("etatAdministratifUniteLegale") == "A"]
    if not etabs:
        return None

    # Prefere un etablissement dont la ville matche
    if city_norm:
        for e in etabs:
            etab_city = normalize(
                e.get("adresseEtablissement", {}).get("libelleCommuneEtablissement", "")
            )
            if etab_city and (city_norm in etab_city or etab_city in city_norm):
                return _format_etab(e)
    # Resultat unique = on prend
    if len(etabs) == 1:
        return _format_etab(etabs[0])
    # Plusieurs resultats sans match ville = on prend le 1er mais on signale
    return {**_format_etab(etabs[0]), "_match_quality": "ambigu"}


def _format_etab(e: dict) -> dict:
    ul = e.get("uniteLegale", {})
    adr = e.get("adresseEtablissement", {})
    cat = ul.get("categorieJuridiqueUniteLegale", "") or ""
    eff = ul.get("trancheEffectifsUniteLegale", "") or ""
    eff_label, eff_min = TRANCHES_EFFECTIFS.get(eff, (eff, 0))
    return {
        "siret":             e.get("siret", ""),
        "siren":             e.get("siren", ""),
        "raison_sociale":    ul.get("denominationUniteLegale", "") or "",
        "nom_usuel":         ul.get("denominationUsuelleUniteLegale", "") or "",
        "effectif_tranche":  eff,
        "effectif_label":    eff_label,
        "effectif_min":      eff_min,
        "forme_juridique":   short_forme(cat),
        "categorie_juridique": cat,
        "date_creation":     e.get("dateCreationEtablissement", ""),
        "ville_insee":       (adr.get("libelleCommuneEtablissement", "") or "").title(),
        "cp_insee":          adr.get("codePostalEtablissement", "") or "",
        "_match_quality":    "ok",
    }


def places_check(name: str, city: str) -> dict:
    """Returns dict {status, url, phone}.
    status in 'yes' (a un site), 'no' (sans site), 'unknown', 'closed'."""
    empty = {"status": "unknown", "url": "", "phone": ""}
    if not GOOGLE_KEY or not name:
        return empty
    payload = {"textQuery": f"{name} {city}".strip(),
               "languageCode": "fr", "maxResultCount": 1}
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,"
                            "places.websiteUri,places.businessStatus,"
                            "places.nationalPhoneNumber",
    }
    try:
        r = requests.post(PLACES_URL, json=payload, headers=headers, timeout=15)
    except requests.RequestException:
        return empty
    if r.status_code != 200:
        return empty
    places = r.json().get("places", [])
    if not places:
        return empty
    p = places[0]
    if p.get("businessStatus") in ("CLOSED_PERMANENTLY", "CLOSED_TEMPORARILY"):
        return {"status": "closed", "url": "", "phone": ""}
    url = p.get("websiteUri", "") or ""
    return {
        "status": "yes" if url else "no",
        "url": url,
        "phone": p.get("nationalPhoneNumber", "") or "",
    }


def pick_col(cols: list, candidates: list) -> str | None:
    """Trouve la premiere colonne qui matche (case-insensitive)."""
    cols_low = {c.lower(): c for c in cols}
    for c in candidates:
        if c.lower() in cols_low:
            return cols_low[c.lower()]
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True,
                    help="CSV Phantombuster Sales Nav export")
    ap.add_argument("--check-website", action="store_true",
                    help="Verifier absence de site via Google Places")
    ap.add_argument("--skip-insee", action="store_true",
                    help="Skip enrichissement INSEE (~10x plus rapide, pas de SIRET/effectif)")
    ap.add_argument("--only-no-site", action="store_true",
                    help="Ne garder que les prospects sans site (implique --check-website)")
    ap.add_argument("--min-effectif", type=int, default=0,
                    help="Filtrer par effectif min (1, 5, 10...) ; 0 = tous")
    ap.add_argument("--limit", type=int, default=0,
                    help="Limiter aux N premieres lignes")
    args = ap.parse_args()

    if args.only_no_site:
        args.check_website = True

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"ERREUR: {in_path} introuvable")
        sys.exit(1)

    rows = []
    # Detection de l'encodage : Phantombuster sort en UTF-8 BOM ou UTF-8
    for enc in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            with open(in_path, encoding=enc) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            break
        except UnicodeDecodeError:
            continue
    if not rows:
        print("ERREUR: CSV vide ou illisible")
        sys.exit(1)

    if args.limit:
        rows = rows[:args.limit]

    cols = list(rows[0].keys())
    col_url     = pick_col(cols, ["profileUrl", "linkedInProfileUrl",
                                   "linkedinProfileUrl", "linkedInUrl",
                                   "linkedinUrl", "defaultProfileUrl"])
    col_first   = pick_col(cols, ["firstName", "first_name"])
    col_last    = pick_col(cols, ["lastName", "last_name"])
    col_full    = pick_col(cols, ["fullName", "full_name", "name"])
    col_company = pick_col(cols, ["companyName", "company"])
    col_company_url = pick_col(cols, ["companyUrl", "companyLinkedInUrl"])
    col_title   = pick_col(cols, ["title", "currentJob", "jobTitle"])
    # Priorite a companyLocation (siege entreprise) sur location (lieu personne)
    col_city    = pick_col(cols, ["companyLocation", "jobLocation", "location", "city"])
    col_industry = pick_col(cols, ["industry", "sector"])

    print(f"Colonnes detectees ({len(cols)}) :")
    print(f"  URL profil   : {col_url}")
    print(f"  Nom complet  : {col_full or f'{col_first} + {col_last}'}")
    print(f"  Entreprise   : {col_company}")
    print(f"  URL societe  : {col_company_url}")
    print(f"  Titre        : {col_title}")
    print(f"  Ville        : {col_city}")
    print(f"  Industrie    : {col_industry}")
    print()

    if not col_company:
        print("ERREUR: colonne entreprise (companyName) introuvable. Verifie le CSV.")
        sys.exit(1)

    print(f"Traitement de {len(rows)} prospects...\n")

    enriched = []
    n_matched = 0
    n_no_site = 0
    n_kept    = 0

    for i, row in enumerate(rows, 1):
        if col_full:
            full = row.get(col_full, "")
        else:
            full = f"{row.get(col_first,'')} {row.get(col_last,'')}".strip()
        company = row.get(col_company, "") or ""
        city_raw = row.get(col_city, "") if col_city else ""
        city = city_raw.split(",")[0].strip() if city_raw else ""

        print(f"[{i:>3}/{len(rows)}] {full[:22]:22s} @ {company[:28]:28s}",
              end=" | ", flush=True)

        # 1. INSEE match (sauf si skip)
        if args.skip_insee:
            insee = None
        else:
            insee = insee_match(company, city)
            if insee:
                n_matched += 1
                quality = insee.get("_match_quality", "ok")
                tag = "INSEE" if quality == "ok" else "INSEE?"
                print(f"{tag} {insee['siret']:14s} {insee['forme_juridique'][:6]:6s} "
                      f"({insee['effectif_label'][:8]:8s})", end=" | ", flush=True)
            else:
                print(f"INSEE -                              ", end=" | ", flush=True)

        # 2. Places (optionnel)
        site_status = "skipped"
        site_url = ""
        site_phone = ""
        if args.check_website:
            places = places_check(company, city)
            site_status = places["status"]
            site_url = places["url"]
            site_phone = places["phone"]
            if site_status == "no":
                n_no_site += 1
            print(f"site={site_status}", end="", flush=True)
            if site_url:
                print(f" {site_url[:40]}", end="", flush=True)
        print()

        # Build enriched row : passthrough Phantombuster + enrichissement
        new_row = dict(row)  # copy all original columns
        new_row.update({
            "siret":              insee["siret"] if insee else "",
            "siren":              insee["siren"] if insee else "",
            "raison_sociale":     insee["raison_sociale"] if insee else "",
            "nom_usuel_insee":    insee["nom_usuel"] if insee else "",
            "effectif_tranche":   insee["effectif_tranche"] if insee else "",
            "effectif_label":     insee["effectif_label"] if insee else "",
            "effectif_min":       insee["effectif_min"] if insee else 0,
            "forme_juridique":    insee["forme_juridique"] if insee else "",
            "date_creation_insee": insee["date_creation"] if insee else "",
            "ville_insee":        insee["ville_insee"] if insee else "",
            "cp_insee":           insee["cp_insee"] if insee else "",
            "match_insee":        "yes" if insee else "no",
            "match_quality":      insee.get("_match_quality", "") if insee else "",
            "has_website":        site_status,
            "website_url":        site_url,
            "phone_gmb":          site_phone,
            "signal":             ("sans_site" if site_status == "no" else
                                   "site_existant" if site_status == "yes" else
                                   "ferme" if site_status == "closed" else
                                   "site_unknown"),
        })

        # Filtres
        if args.only_no_site and site_status != "no":
            continue
        if args.min_effectif and insee and insee["effectif_min"] < args.min_effectif:
            continue
        if args.min_effectif and not insee:
            continue  # pas d'INSEE = pas de filtre possible = exclu

        enriched.append(new_row)
        n_kept += 1
        time.sleep(0.4)

    if not enriched:
        print("\nAucun prospect retenu apres filtres.")
        sys.exit(0)

    # Output CSV
    suffix = ""
    if args.only_no_site:
        suffix += "_sans_site"
    if args.min_effectif:
        suffix += f"_eff{args.min_effectif}"

    out = DATA_DIR / f"rocket_reach_ready{suffix}_{TODAY}.csv"
    fieldnames = list(enriched[0].keys())
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(enriched)

    print(f"\n=== Resume ===")
    print(f"Total prospects en entree : {len(rows)}")
    if not args.skip_insee:
        print(f"Match INSEE trouve        : {n_matched} ({100*n_matched//max(len(rows),1)}%)")
    if args.check_website:
        print(f"Sans site (Places)        : {n_no_site} ({100*n_no_site//max(len(rows),1)}%)")
    print(f"Prospects retenus (output): {n_kept}")
    print(f"\nCSV pret pour Rocket Reach :")
    print(f"  {out}")
    print()
    print("Astuce : tu peux maintenant importer ce CSV dans Rocket Reach")
    print("        ou filtrer avant dans Excel (signal=sans_site, forme_juridique=SAS, etc.)")


if __name__ == "__main__":
    main()
