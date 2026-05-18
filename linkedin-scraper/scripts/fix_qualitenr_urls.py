"""fix_qualitenr_urls.py — nettoie les site_url qualit-enr.org pour les
remplacer par le vrai site web de l'entreprise (extrait du slug + email).

Logique :
1. Pour chaque prospect dont site_url contient qualit-enr.org/entreprises/<slug> :
   - extraire <slug>
   - construire des URLs candidates depuis le slug ET le domaine de l'email
     du prospect (si l'email est pro, pas un free provider)
2. Tester chaque candidate en HTTP : 200 + signal (mot d'entreprise dans le HTML)
3. Update DB :
   - site_url = nouvelle URL si trouvée + categorie = avec_site_veillot
   - sinon site_url = NULL + categorie = sans_site (l'URL qualit-enr n'était pas
     un vrai site)

Run :
    python -X utf8 scripts/fix_qualitenr_urls.py [--dry-run]
"""
import argparse
import asyncio
import logging
import re
import sys
import time
import unicodedata
from pathlib import Path

import aiohttp

# Charge .env de la racine du projet
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from crm.db import query, execute

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    datefmt="%H:%M:%S")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
HTTP_TIMEOUT = aiohttp.ClientTimeout(total=8, connect=5)
CONCURRENCY = 40

FREE_EMAIL_DOMAINS = {
    "gmail.com", "googlemail.com",
    "orange.fr", "wanadoo.fr", "free.fr", "sfr.fr", "bbox.fr", "laposte.net",
    "hotmail.fr", "hotmail.com", "outlook.fr", "outlook.com", "live.fr", "live.com",
    "yahoo.fr", "yahoo.com", "ymail.com", "aol.com", "aol.fr",
    "neuf.fr", "club-internet.fr", "voila.fr", "9online.fr",
    "msn.com", "icloud.com", "me.com",
}


def _normalize(s: str) -> str:
    if not s:
        return ""
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c)).lower()


def extract_slug(qualit_url: str) -> str | None:
    """https://www.qualit-enr.org/entreprises/mepac/ → 'mepac'"""
    m = re.search(r"qualit-enr\.org/entreprises/([a-z0-9-]+)", qualit_url or "", re.I)
    return m.group(1).lower() if m else None


def email_pro_domain(email: str) -> str | None:
    """Renvoie le domaine de l'email si pro (pas free provider), sinon None."""
    if not email or "@" not in email:
        return None
    domain = email.split("@", 1)[1].strip().lower()
    if domain in FREE_EMAIL_DOMAINS:
        return None
    return domain


def candidate_urls(slug: str, email: str | None) -> list[str]:
    """Liste ordonnée d'URLs à tester (la 1ère est la plus probable)."""
    urls = []

    # 1. Si email pro → domaine direct (priorité absolue)
    pro_domain = email_pro_domain(email or "")
    if pro_domain:
        urls.append(f"https://{pro_domain}")
        urls.append(f"https://www.{pro_domain}")

    # 2. Slug avec tirets (renovo-group → renovo-group.fr)
    for ext in (".fr", ".com", ".pro", ".eu"):
        urls.append(f"https://{slug}{ext}")
        urls.append(f"https://www.{slug}{ext}")

    # 3. Slug compact (renovo-group → renovogroup.fr)
    compact = slug.replace("-", "")
    if compact != slug:
        for ext in (".fr", ".com", ".pro", ".eu"):
            urls.append(f"https://{compact}{ext}")
            urls.append(f"https://www.{compact}{ext}")

    # Dédup en gardant l'ordre
    seen, out = set(), []
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def validate_html(html: str, slug: str, email: str | None, entreprise: str) -> bool:
    """Vérifie qu'un signal de match est présent dans le HTML."""
    if not html or len(html) < 500:
        return False
    h = _normalize(html)

    # Signal 1 : slug (avec ou sans tirets) dans le HTML
    if slug and len(slug) >= 4:
        if slug in h or slug.replace("-", "") in h.replace("-", ""):
            return True

    # Signal 2 : nom d'entreprise (1 mot ≥ 4 chars)
    if entreprise:
        for w in re.split(r"[^a-z0-9]+", _normalize(entreprise)):
            if len(w) >= 4 and w in h:
                return True

    # Signal 3 : domaine d'email pro dans le HTML
    pro = email_pro_domain(email or "")
    if pro and pro in h:
        return True

    return False


async def fetch(session, sem, url):
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


async def find_real_site(session, sem, slug, email, entreprise):
    """Renvoie la 1ère URL candidate qui valide, sinon None."""
    for url in candidate_urls(slug, email)[:8]:  # cap 8 candidats
        final_url, body = await fetch(session, sem, url)
        if not body:
            continue
        # rejette si redirigé vers qualit-enr ou autre annuaire
        if "qualit-enr.org" in final_url or "pagesjaunes.fr" in final_url:
            continue
        if validate_html(body, slug, email, entreprise):
            return final_url
    return None


async def process_all(prospects, dry_run=False):
    sem = asyncio.Semaphore(CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=CONCURRENCY, ssl=False, limit_per_host=4)
    async with aiohttp.ClientSession(connector=connector, headers=UA) as session:
        total = len(prospects)
        log.info(f"À traiter : {total} prospects avec URL qualit-enr.org")
        t0 = time.time()
        stats = {"resolved": 0, "no_site": 0, "skipped": 0}

        async def worker(p):
            slug = extract_slug(p["site_url"])
            if not slug:
                stats["skipped"] += 1
                return
            real_url = await find_real_site(session, sem, slug, p.get("email"), p.get("entreprise") or "")
            if real_url:
                stats["resolved"] += 1
                if not dry_run:
                    execute(
                        "UPDATE prospects SET site_url = ?, categorie = 'avec_site_veillot' WHERE id = ?",
                        (real_url, p["id"]),
                    )
            else:
                stats["no_site"] += 1
                if not dry_run:
                    execute(
                        "UPDATE prospects SET site_url = NULL, categorie = 'sans_site' WHERE id = ?",
                        (p["id"],),
                    )

        # Process en batches de 50 pour progress
        BATCH = 50
        for i in range(0, total, BATCH):
            batch = prospects[i:i+BATCH]
            await asyncio.gather(*[worker(p) for p in batch])
            done = min(i + BATCH, total)
            elapsed = time.time() - t0
            rate = done / max(elapsed, 0.1)
            eta = (total - done) / max(rate, 0.1)
            log.info(f"  {done}/{total} — résolu : {stats['resolved']} · "
                     f"sans site : {stats['no_site']} · skip : {stats['skipped']} — "
                     f"{rate:.1f}/s — ETA {eta:.0f}s")

        log.info("")
        log.info(f"TERMINÉ — résolu : {stats['resolved']} ({100*stats['resolved']//total}%)")
        log.info(f"         sans site (URL effacée) : {stats['no_site']} ({100*stats['no_site']//total}%)")
        log.info(f"         skipped : {stats['skipped']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Affiche les stats sans modifier la DB")
    args = parser.parse_args()

    prospects = query(
        "SELECT id, nom_complet, email, entreprise, site_url "
        "FROM prospects WHERE site_url LIKE ?",
        ("%qualit-enr.org%",),
    )
    if not prospects:
        log.info("Aucun prospect avec qualit-enr.org. Rien à faire.")
        return

    asyncio.run(process_all(prospects, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
