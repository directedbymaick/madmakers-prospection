"""
fetch_site.py — Enrichit un batch avec les données du site existant des prospects.

Pour chaque prospect ayant un `website`, on :
  - fetch le HTML (timeout court, on ne veut pas bloquer sur des sites lents)
  - parse titre, meta description, présence HTTPS, mobile-friendly (meta viewport)
  - appelle PageSpeed API pour score performance mobile (0-100)
  - sauvegarde un snapshot HTML dans data/site_snapshots/{siret}.html

Usage :
    python scripts/fetch_site.py data/batch_20260416.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from config import DATA_DIR, info, warn, settings, ensure_key


PAGESPEED_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
FETCH_TIMEOUT = 10
FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    )
}


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def fetch_html(url: str) -> tuple[int, str]:
    try:
        resp = requests.get(url, headers=FETCH_HEADERS, timeout=FETCH_TIMEOUT, allow_redirects=True)
        return resp.status_code, resp.text
    except requests.exceptions.Timeout:
        warn(f"Timeout sur {url}")
        return 0, ""
    except requests.exceptions.RequestException as e:
        warn(f"Erreur fetch {url} : {e}")
        return 0, ""


def parse_meta(html: str, url: str) -> dict:
    if not html:
        return {"title": None, "description": None, "has_viewport": False, "has_ssl": False}
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    title = soup.title.string.strip() if soup.title and soup.title.string else None
    desc_tag = soup.find("meta", attrs={"name": "description"})
    desc = desc_tag.get("content", "").strip() if desc_tag else None
    viewport = soup.find("meta", attrs={"name": "viewport"}) is not None
    ssl = urlparse(url).scheme == "https"

    # Détection système (WordPress, Wix, Squarespace, Framer...)
    generator = ""
    gen_tag = soup.find("meta", attrs={"name": "generator"})
    if gen_tag:
        generator = gen_tag.get("content", "")
    else:
        html_lower = html.lower()
        if "wp-content" in html_lower:
            generator = "WordPress"
        elif "wix.com" in html_lower:
            generator = "Wix"
        elif "squarespace" in html_lower:
            generator = "Squarespace"
        elif "framer" in html_lower:
            generator = "Framer"
        elif "shopify" in html_lower:
            generator = "Shopify"

    # Présence de signaux clés pour un resto
    html_lower = html.lower()
    has_menu = "menu" in html_lower or "carte" in html_lower
    has_booking = any(
        kw in html_lower
        for kw in ["réservation", "reservation", "booking", "thefork", "resy"]
    )
    has_phone = bool(re.search(r"\+33|0[1-9]\s?(\d\s?){8}", html))

    return {
        "title": title,
        "description": desc,
        "has_viewport": viewport,
        "has_ssl": ssl,
        "generator": generator or None,
        "has_menu": has_menu,
        "has_booking": has_booking,
        "has_phone_displayed": has_phone,
        "html_size_kb": round(len(html) / 1024, 1),
    }


def pagespeed_score(url: str) -> dict | None:
    """Score PageSpeed mobile (0-100). Ne plante pas si l'API manque."""
    if not settings.GOOGLE_API_KEY:
        return None
    try:
        resp = requests.get(
            PAGESPEED_URL,
            params={"url": url, "strategy": "mobile", "key": settings.GOOGLE_API_KEY},
            timeout=60,  # PageSpeed peut être lent
        )
    except requests.exceptions.RequestException as e:
        warn(f"PageSpeed erreur réseau sur {url} : {e}")
        return None

    if resp.status_code != 200:
        warn(f"PageSpeed HTTP {resp.status_code} sur {url}")
        return None

    try:
        data = resp.json()
        lr = data.get("lighthouseResult", {})
        perf = lr.get("categories", {}).get("performance", {}).get("score")
        return {
            "mobile_score": int(perf * 100) if perf is not None else None,
            "fcp": lr.get("audits", {}).get("first-contentful-paint", {}).get("displayValue"),
            "lcp": lr.get("audits", {}).get("largest-contentful-paint", {}).get("displayValue"),
        }
    except (KeyError, ValueError, TypeError) as e:
        warn(f"PageSpeed parse erreur sur {url} : {e}")
        return None


def save_snapshot(siret: str, html: str) -> None:
    if not html:
        return
    snap_dir = DATA_DIR / "site_snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    with open(snap_dir / f"{siret}.html", "w", encoding="utf-8") as f:
        f.write(html[:500_000])  # cap à 500KB


def enrich_prospect(p: dict) -> dict:
    website = p.get("website")
    if not website:
        p["site_audit"] = {"has_site": False}
        return p

    url = normalize_url(website)
    status, html = fetch_html(url)
    meta = parse_meta(html, url)
    perf = pagespeed_score(url) if html else None
    save_snapshot(p["siret"], html)

    p["site_audit"] = {
        "has_site": True,
        "url": url,
        "http_status": status,
        "reachable": 200 <= status < 400,
        **meta,
        "performance": perf,
    }
    return p


def rescore_with_site(p: dict, icp_scoring: dict) -> int:
    """Ajuste le score avec les signaux site récupérés."""
    audit = p.get("site_audit", {})
    base = p.get("score", 0)

    if not audit.get("has_site"):
        return base

    perf = (audit.get("performance") or {}).get("mobile_score")
    # Site existe mais obsolète (perf < 40 ou pas HTTPS ou pas viewport)
    if (perf is not None and perf < 40) or not audit.get("has_ssl") or not audit.get("has_viewport"):
        base += icp_scoring["site_web_obsolete"]["points"]

    return base


def main() -> None:
    from config import icp as icp_conf  # import local pour éviter cycle

    parser = argparse.ArgumentParser(description="Enrichissement sites Mad Makers")
    parser.add_argument("batch_file", type=str, help="Chemin vers le batch JSON")
    parser.add_argument("--skip-pagespeed", action="store_true", help="Ne pas appeler PageSpeed")
    args = parser.parse_args()

    batch_path = Path(args.batch_file)
    if not batch_path.exists():
        print(f"[ERROR] Fichier introuvable : {batch_path}", file=sys.stderr)
        sys.exit(1)

    with open(batch_path, "r", encoding="utf-8") as f:
        batch = json.load(f)

    prospects = batch.get("prospects", [])
    info(f"Enrichissement sites sur {len(prospects)} prospects...")

    for i, p in enumerate(prospects, start=1):
        if args.skip_pagespeed:
            # Patch temporaire : on zappe PageSpeed en virant la clé
            settings.GOOGLE_API_KEY = ""
        enrich_prospect(p)
        p["score"] = rescore_with_site(p, icp_conf["scoring"])
        info(f"  {i}/{len(prospects)} : {p.get('raison_sociale', '?')[:40]} → score {p['score']}")

    # Re-tri par score
    batch["prospects"] = sorted(prospects, key=lambda x: x.get("score", 0), reverse=True)

    with open(batch_path, "w", encoding="utf-8") as f:
        json.dump(batch, f, ensure_ascii=False, indent=2)

    info(f"Batch mis à jour : {batch_path}")


if __name__ == "__main__":
    main()
