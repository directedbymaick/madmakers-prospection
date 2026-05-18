"""enrich_ademe_csv.py — Étape 2 du pipeline Carnet Plein®.

Enrichit le CSV propre (sortie de clean_ademe_csv.py) :

A. Dirigeants — pour chaque SIRET, appelle l'API gouv officielle
   `recherche-entreprises.api.gouv.fr` qui renvoie le dirigeant officiel
   (Président, Gérant, etc). Zéro invention : si l'API ne renvoie pas
   de personne physique, on laisse vide.

B. Sites web — pour les boîtes sans site_url, recherche en 2 phases :
   1. URL guessing : on construit des slugs depuis le nom d'entreprise
      et on teste plusieurs extensions (.fr / .com / .pro / .eu / .bzh).
      Validation stricte : HTTP 200 + le HTML doit contenir au moins un
      signal fort (nom entreprise, ville, ou téléphone sans espaces).
   2. DuckDuckGo fallback : si rien trouvé en URL guess, recherche
      `"{entreprise}" {ville} site officiel` et on prend le 1er
      résultat valide (hors annuaires / réseaux sociaux).

Sortie : `qualibat_rge_carnetplein_<date>_enriched.csv` avec colonnes :
    siret, prenom, nom, dirigeant_qualite, entreprise, ville, email,
    phone_office, site_url, linkedin_url, domaine, notes,
    site_found_via, dirigeant_found_via

Usage :
    python -X utf8 scripts/enrich_ademe_csv.py [csv_clean]
    python -X utf8 scripts/enrich_ademe_csv.py --skip-sites      # juste dirigeants
    python -X utf8 scripts/enrich_ademe_csv.py --skip-dirigeants # juste sites
    python -X utf8 scripts/enrich_ademe_csv.py --limit 50        # test rapide
"""
import argparse
import asyncio
import csv
import logging
import re
import sys
import time
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

import aiohttp

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    datefmt="%H:%M:%S")

# ── API gouv officielle (dirigeants) ─────────────────────────────
GOUV_API = "https://recherche-entreprises.api.gouv.fr/search"
GOUV_RATE = 6  # req/s strict (limite officielle : 7)
GOUV_CONCURRENCY = 3  # nombre de tâches simultanées

# ── Site discovery ───────────────────────────────────────────────
URL_EXTENSIONS = [".fr", ".com", ".pro", ".eu", ".bzh", ".net"]
URL_PREFIXES = ["https://", "https://www.", "http://", "http://www."]
HTTP_TIMEOUT = aiohttp.ClientTimeout(total=8, connect=5)
HTTP_CONCURRENCY = 40

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

# Domaines exclus : annuaires, réseaux sociaux, presse
BLOCKED_DOMAINS = {
    "pagesjaunes.fr", "societe.com", "pappers.fr", "infogreffe.fr",
    "score3.fr", "verif.com", "manageo.fr", "kompass.com", "kompass.fr",
    "europages.fr", "europages.com", "leboncoin.fr",
    "facebook.com", "linkedin.com", "instagram.com", "twitter.com", "x.com",
    "indeed.fr", "indeed.com", "youtube.com", "tiktok.com",
    "data.gouv.fr", "annuaire-entreprises.data.gouv.fr", "entreprises.gouv.fr",
    "ouest-france.fr", "lemonde.fr", "lefigaro.fr",
    "mappy.com", "google.com", "google.fr",
    "qualibat.com", "qualigaz.com", "qualipac.com", "qualinergie.com",
    "rge.ademe.fr", "france-renov.gouv.fr", "ademe.fr",
    "bilanproduits.ademe.fr", "lemoniteur.fr", "batiactu.com",
    "duckduckgo.com", "bing.com",
}

# Mots-clés génériques à exclure du slug (sinon "Sarl Plomberie" donnerait sarl-plomberie.fr)
SLUG_STOPWORDS = {
    "sarl", "sas", "sasu", "eurl", "sci", "scop", "ei", "eirl", "sc", "sa",
    "snc", "ets", "etablissement", "etablissements", "entreprise", "entreprises",
    "societe", "ste", "compagnie", "cie",
    "et", "&",
    "btp", "batiment", "service", "services", "pro", "professionnel",
}


# ── Helpers ──────────────────────────────────────────────────────


def _normalize(s: str) -> str:
    """Strip accents + lowercase."""
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def _slugs(entreprise: str) -> list[str]:
    """Génère des slugs candidats depuis le nom d'entreprise.

    Retourne plusieurs variantes :
    - slug complet (tous les mots utiles)
    - slug compact (sans tirets)
    - slug premier mot significatif uniquement
    - slug deux premiers mots
    """
    if not entreprise:
        return []
    norm = _normalize(entreprise)
    words = [w for w in re.split(r"[^a-z0-9]+", norm) if w and w not in SLUG_STOPWORDS]
    if not words:
        return []

    slugs = []
    # Slug complet (kebab) : plomberie-dupont
    slugs.append("-".join(words))
    # Slug compact (sans séparateur) : plomberiedupont
    slugs.append("".join(words))
    # Premier mot significatif (souvent le nom de famille / marque)
    if len(words) >= 1:
        slugs.append(words[0])
    # Deux premiers mots
    if len(words) >= 2:
        slugs.append("-".join(words[:2]))
        slugs.append("".join(words[:2]))
    # Dernier mot (parfois la marque est en dernier : "Cheminées Philippe" → philippe)
    if len(words) >= 2:
        slugs.append(words[-1])

    # Dédup en gardant l'ordre
    seen = set()
    out = []
    for s in slugs:
        if len(s) < 3:
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def _candidate_urls(entreprise: str) -> list[str]:
    """Construit la liste des URLs à tester."""
    urls = []
    for slug in _slugs(entreprise):
        for ext in URL_EXTENSIONS:
            # Pour les slugs simples (1 mot), on génère www et non-www
            urls.append(f"https://{slug}{ext}")
            urls.append(f"https://www.{slug}{ext}")
    # Dédup
    return list(dict.fromkeys(urls))


def _phone_digits(phone: str) -> str:
    """Garde uniquement les chiffres d'un numéro de tel."""
    return re.sub(r"\D", "", phone or "")


def _validate_html_match(html: str, entreprise: str, phone_digits: str) -> bool:
    """Renvoie True si le HTML contient au moins un signal fort matchant la boîte.
    Signaux acceptés (un seul suffit) :
      - 8 derniers chiffres du téléphone présents dans le HTML
      - au moins 1 mot significatif (≥ 4 chars) du nom d'entreprise présent
    """
    if not html or len(html) < 500:
        return False

    # Signal 1 : téléphone (sans espaces) — très fort si match
    if phone_digits and len(phone_digits) >= 8:
        last8 = phone_digits[-8:]
        if last8 in re.sub(r"\D", "", html):
            return True

    # Signal 2 : nom d'entreprise — il faut au moins 1 mot ≥ 4 chars
    if entreprise:
        ent_norm = _normalize(entreprise)
        ent_words = [w for w in re.split(r"[^a-z0-9]+", ent_norm)
                     if len(w) >= 4 and w not in SLUG_STOPWORDS]
        if ent_words:
            h_norm = _normalize(html)
            if any(w in h_norm for w in ent_words):
                return True

    return False


def _domain(url: str) -> str:
    """Extrait le domaine racine (sans www, sans port)."""
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def _domain_blocked(url: str) -> bool:
    d = _domain(url)
    if not d:
        return True
    return any(d == b or d.endswith("." + b) for b in BLOCKED_DOMAINS)


# ── Phase A — dirigeants via API gouv ────────────────────────────


def _parse_dirigeants(dirigeants: list) -> dict:
    """Sélectionne la 1ère personne physique et renvoie {prenom, nom, qualite}.
    Si rien → strings vides."""
    for d in dirigeants:
        if d.get("type_dirigeant") != "personne physique":
            continue
        nom_raw = (d.get("nom") or "").strip()
        prenoms_raw = (d.get("prenoms") or "").strip()
        qualite = (d.get("qualite") or "").strip()
        # "DURAND (DUPONT)" → "DURAND" (nom usuel d'abord)
        nom_clean = re.split(r"\s*\(", nom_raw)[0].strip()
        prenom_clean = " ".join(p.capitalize() for p in prenoms_raw.split())
        nom_clean = " ".join(p.capitalize() for p in nom_clean.split())
        if not nom_clean and not prenom_clean:
            continue
        return {"prenom": prenom_clean, "nom": nom_clean, "qualite": qualite}
    return {"prenom": "", "nom": "", "qualite": ""}


async def fetch_dirigeant(session: aiohttp.ClientSession, siret: str,
                          retry: int = 1) -> dict:
    """Appelle l'API gouv pour un SIRET. Retry 1× sur 429/5xx."""
    empty = {"prenom": "", "nom": "", "qualite": "", "found_via": ""}
    if not siret or len(siret) < 9:
        return empty

    siren = siret[:9]
    for attempt in range(retry + 1):
        try:
            async with session.get(GOUV_API,
                                   params={"q": siren, "per_page": 1},
                                   timeout=HTTP_TIMEOUT) as r:
                if r.status == 429 or r.status >= 500:
                    if attempt < retry:
                        await asyncio.sleep(2.0)
                        continue
                    return empty
                if r.status != 200:
                    return empty
                data = await r.json()
                break
        except Exception:
            if attempt < retry:
                await asyncio.sleep(1.0)
                continue
            return empty
    else:
        return empty

    results = data.get("results", [])
    if not results:
        return empty
    parsed = _parse_dirigeants(results[0].get("dirigeants", []) or [])
    if not parsed["nom"] and not parsed["prenom"]:
        return empty
    return {**parsed, "found_via": "recherche_entreprises_gouv"}


async def enrich_dirigeants(rows: list[dict]) -> dict:
    """Appelle l'API gouv en respectant strictement GOUV_RATE req/sec.

    Stratégie : on traite par batches de GOUV_RATE requêtes en parallèle,
    et on attend ≥ 1s entre chaque batch. Concurrence limitée par la taille
    du batch → pas de débordement du quota officiel (7 req/s).
    """
    out = {}
    sirets = [r.get("siret", "").strip() for r in rows]
    sirets = [s for s in sirets if s]
    total = len(sirets)
    log.info(f"Phase A — dirigeants : {total} SIREN via API gouv (rate {GOUV_RATE}/s)")

    connector = aiohttp.TCPConnector(limit=GOUV_RATE * 2, ssl=False)
    async with aiohttp.ClientSession(connector=connector, headers=UA) as session:
        t0 = time.time()
        for i in range(0, total, GOUV_RATE):
            batch = sirets[i:i + GOUV_RATE]
            batch_t0 = time.time()
            results = await asyncio.gather(*[fetch_dirigeant(session, s) for s in batch])
            for siret, res in zip(batch, results):
                out[siret] = res
            # Respecte le rate limit : 1s par batch de GOUV_RATE
            elapsed = time.time() - batch_t0
            if elapsed < 1.0:
                await asyncio.sleep(1.0 - elapsed)
            done = min(i + GOUV_RATE, total)
            # Log tous les ~200
            if done % 200 < GOUV_RATE or done >= total:
                global_elapsed = time.time() - t0
                rate = done / max(global_elapsed, 0.1)
                eta = (total - done) / max(rate, 0.1)
                found = sum(1 for v in out.values() if v.get("found_via"))
                log.info(f"  {done}/{total} — trouvés : {found} "
                         f"({100*found//max(done,1)}%) — rate {rate:.1f}/s — "
                         f"ETA {eta:.0f}s")
    return out


# ── Phase B — site discovery ─────────────────────────────────────


async def fetch_url(session: aiohttp.ClientSession, sem: asyncio.Semaphore,
                    url: str) -> tuple[str, str]:
    """GET sur url. Renvoie (final_url, body) ou ('', '') si échec."""
    async with sem:
        try:
            async with session.get(url, allow_redirects=True,
                                   timeout=HTTP_TIMEOUT, ssl=False) as r:
                if r.status != 200:
                    return "", ""
                ct = r.headers.get("content-type", "").lower()
                if "html" not in ct and "text" not in ct:
                    return "", ""
                body = await r.text(errors="ignore")
                return str(r.url), body
        except Exception:
            return "", ""


async def discover_site(session, sem, row: dict) -> dict:
    """Tente de trouver un site web pour cette row.
    Renvoie {site_url, site_found_via}."""
    entreprise = row.get("entreprise", "")
    ville = row.get("ville", "")
    phone_digits = _phone_digits(row.get("phone_office", ""))

    if not entreprise:
        return {"site_url": "", "site_found_via": "no_entreprise"}

    # Phase B1 : URL guessing
    candidates = _candidate_urls(entreprise)[:20]  # cap à 20 URLs/boîte
    for url in candidates:
        final_url, body = await fetch_url(session, sem, url)
        if not body:
            continue
        if _domain_blocked(final_url):
            continue
        if _validate_html_match(body, entreprise, phone_digits):
            return {"site_url": final_url, "site_found_via": "url_guess"}

    # Phase B2 : DuckDuckGo HTML search
    q = f'"{entreprise}" {ville}'.strip()
    ddg_url = "https://html.duckduckgo.com/html/"
    try:
        async with sem:
            async with session.post(ddg_url, data={"q": q},
                                    timeout=HTTP_TIMEOUT, ssl=False) as r:
                if r.status == 200:
                    ddg_html = await r.text(errors="ignore")
                else:
                    ddg_html = ""
    except Exception:
        ddg_html = ""

    # Parse top results (DDG HTML uses class="result__a" anchor)
    result_urls = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"', ddg_html)
    # DDG retourne parfois des liens redirect : on extrait le param uddg
    cleaned = []
    for u in result_urls[:10]:
        m = re.search(r"uddg=([^&]+)", u)
        if m:
            from urllib.parse import unquote
            u = unquote(m.group(1))
        cleaned.append(u)

    for url in cleaned:
        if _domain_blocked(url):
            continue
        final_url, body = await fetch_url(session, sem, url)
        if not body:
            continue
        if _domain_blocked(final_url):
            continue
        if _validate_html_match(body, entreprise, phone_digits):
            return {"site_url": final_url, "site_found_via": "ddg_search"}

    return {"site_url": "", "site_found_via": "confirmed_no_site"}


async def enrich_sites(rows_no_site: list[dict]) -> dict:
    """Renvoie un dict {siret: {site_url, site_found_via}}."""
    out = {}
    sem = asyncio.Semaphore(HTTP_CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=HTTP_CONCURRENCY, ssl=False,
                                      limit_per_host=4)
    async with aiohttp.ClientSession(connector=connector, headers=UA) as session:
        total = len(rows_no_site)
        log.info(f"Phase B — site discovery : {total} boîtes sans site")
        t0 = time.time()

        async def _worker(r):
            res = await discover_site(session, sem, r)
            out[r["siret"]] = res

        tasks = [_worker(r) for r in rows_no_site]
        chunk = 50
        for i in range(0, total, chunk):
            await asyncio.gather(*tasks[i:i+chunk])
            done = min(i + chunk, total)
            elapsed = time.time() - t0
            found = sum(1 for v in out.values() if v.get("site_url"))
            via = {}
            for v in out.values():
                via[v.get("site_found_via", "")] = via.get(v.get("site_found_via", ""), 0) + 1
            log.info(f"  {done}/{total} — sites trouvés : {found} — "
                     f"via {via} — elapsed {elapsed:.0f}s")
    return out


# ── Main ─────────────────────────────────────────────────────────


def write_enriched_csv(input_rows: list[dict], dirigeants: dict, sites: dict,
                       output_path: Path):
    out_cols = ["siret", "prenom", "nom", "dirigeant_qualite", "entreprise",
                "ville", "email", "phone_office", "site_url", "linkedin_url",
                "domaine", "notes", "site_found_via", "dirigeant_found_via"]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_cols)
        w.writeheader()
        for r in input_rows:
            siret = r.get("siret", "")
            dir_info = dirigeants.get(siret, {})
            site_info = sites.get(siret, {})

            prenom = dir_info.get("prenom") or r.get("prenom", "")
            nom = dir_info.get("nom") or r.get("nom", "")
            dir_qualite = dir_info.get("qualite", "")
            dir_via = dir_info.get("found_via", "")

            site_url = r.get("site_url", "")
            site_via = "ademe" if site_url else ""
            if not site_url and site_info:
                site_url = site_info.get("site_url", "")
                site_via = site_info.get("site_found_via", "")

            w.writerow({
                "siret":               siret,
                "prenom":              prenom,
                "nom":                 nom,
                "dirigeant_qualite":   dir_qualite,
                "entreprise":          r.get("entreprise", ""),
                "ville":               r.get("ville", ""),
                "email":               r.get("email", ""),
                "phone_office":        r.get("phone_office", ""),
                "site_url":            site_url,
                "linkedin_url":        r.get("linkedin_url", ""),
                "domaine":             r.get("domaine", ""),
                "notes":               r.get("notes", ""),
                "site_found_via":      site_via,
                "dirigeant_found_via": dir_via,
            })


async def main_async(args):
    input_path = Path(args.input) if args.input else None
    inputs_dir = Path(__file__).resolve().parent.parent / "data" / "inputs"
    if not input_path:
        candidates = sorted(inputs_dir.glob("qualibat_rge_carnetplein_*_clean.csv"),
                            key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            log.error(f"Aucun *_clean.csv trouvé dans {inputs_dir}")
            sys.exit(1)
        input_path = candidates[0]
        log.info(f"Input auto-détecté : {input_path}")

    rows = list(csv.DictReader(open(input_path, encoding="utf-8-sig")))
    if args.limit:
        rows = rows[:args.limit]
    log.info(f"Lignes à enrichir : {len(rows)}")

    dirigeants = {}
    sites = {}

    if not args.skip_dirigeants:
        dirigeants = await enrich_dirigeants(rows)
        found = sum(1 for v in dirigeants.values() if v.get("found_via"))
        log.info(f"✓ Phase A terminée : dirigeants trouvés {found}/{len(dirigeants)} "
                 f"({100*found//max(len(dirigeants),1)}%)")

    if not args.skip_sites:
        rows_no_site = [r for r in rows if not (r.get("site_url") or "").strip()]
        if rows_no_site:
            sites = await enrich_sites(rows_no_site)
            n_found = sum(1 for v in sites.values() if v.get("site_url"))
            log.info(f"✓ Phase B terminée : sites trouvés {n_found}/{len(sites)} "
                     f"({100*n_found//max(len(sites),1)}%)")

    # Output
    if args.output:
        output_path = Path(args.output)
    else:
        base = input_path.stem.replace("_clean", "")
        output_path = input_path.with_name(f"{base}_enriched.csv")
    write_enriched_csv(rows, dirigeants, sites, output_path)
    log.info(f"CSV enrichi écrit : {output_path}")

    # Stats globales
    log.info("")
    log.info("=== Stats finales ===")
    with_dir = sum(1 for r in rows if dirigeants.get(r["siret"], {}).get("found_via"))
    with_site_total = sum(1 for r in rows if (r.get("site_url") or "").strip()
                          or sites.get(r["siret"], {}).get("site_url"))
    log.info(f"Total prospects    : {len(rows)}")
    log.info(f"Avec dirigeant    : {with_dir} ({100*with_dir//max(len(rows),1)}%)")
    log.info(f"Avec site (final) : {with_site_total} ({100*with_site_total//max(len(rows),1)}%)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?")
    parser.add_argument("--output")
    parser.add_argument("--skip-dirigeants", action="store_true")
    parser.add_argument("--skip-sites", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
