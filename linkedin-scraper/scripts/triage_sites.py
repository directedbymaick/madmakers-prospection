"""
triage_sites.py
Categorise les prospects RocketReach en 3 buckets :
  1. sans_site            : aucun site web detectable apres verification thorough
  2. avec_site_veillot    : site existe mais design/tech datee (cible Mad Makers refonte)
  3. avec_site_recent     : site moderne (HTTPS, mobile-responsive, framework moderne)

Heuristique de scoring :
  Veillot : pas HTTPS, pas viewport mobile, table layout, copyright < 2022,
            jQuery 1.x, frameset, WordPress < 5
  Recent  : viewport responsive, framework JS moderne (Next/React/Nuxt/Vue/Astro),
            Tailwind, copyright recent (>= annee-1), HTML5 semantic, PWA, fonts Google,
            Webflow / Framer / Shopify

Input : 3 CSV RocketReach dans data/inputs/
Output : data/prospects_triage_<date>.csv (trie par priorite Mad Makers)
"""
import csv, re, sys, time, unicodedata
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import requests

DATA_DIR = Path(r"C:\Users\MAÏCK\Desktop\MadMakers Prospection\linkedin-scraper\data")
INPUTS_DIR = DATA_DIR / "inputs"
TODAY = datetime.now().strftime("%Y%m%d")
OUTPUT = DATA_DIR / f"prospects_triage_{TODAY}.csv"

INPUT_FILES = [
    INPUTS_DIR / "rocketreach_bulk_100_20260507_v9RvazD.csv",
    INPUTS_DIR / "rocketreach_bulk_101-200_20260507_0V5m28t.csv",
    INPUTS_DIR / "rocketreach_bulk_201-300_20260507_KuL8LKU.csv",
    INPUTS_DIR / "rocketreach_bulk_301-400_20260507_w4WrqtK.csv",
    INPUTS_DIR / "rocketreach_bulk_401-500_20260507_6XU85OQ.csv",
]

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

# ── Patterns veillot (signaux de site daté) ────────────────────────────────
VEILLOT_PATTERNS = [
    (re.compile(r'<table[^>]*\s(?:width|cellpadding|cellspacing|border)=', re.I), "table_layout"),
    (re.compile(r'<font\s+(?:color|face|size)=', re.I), "font_tag"),
    (re.compile(r'<center>', re.I), "center_tag"),
    (re.compile(r'<frameset|<frame\s', re.I), "frameset"),
    (re.compile(r'jquery[/-]1\.\d', re.I), "jquery_v1"),
    (re.compile(r'powered by\s*wordpress\s*[34]\.\d', re.I), "wp_old"),
    (re.compile(r'<meta\s+http-equiv=["\']?Content-Type["\']?[^>]*charset=iso', re.I), "iso_charset"),
]

# ── Patterns récent (signaux de site moderne) ──────────────────────────────
RECENT_PATTERNS = [
    (re.compile(r'<meta[^>]+name=["\']?viewport["\']?[^>]+width=device-width', re.I), "viewport_responsive"),
    (re.compile(r'__NEXT_DATA__|next/script|/_next/', re.I), "nextjs"),
    (re.compile(r'window\.__NUXT__|/_nuxt/', re.I), "nuxtjs"),
    (re.compile(r'react-root|react-dom|/static/js/main\.[a-f0-9]+\.js', re.I), "react"),
    (re.compile(r'gatsby-app|/page-data/', re.I), "gatsby"),
    (re.compile(r'astro-island|astro:|/_astro/', re.I), "astro"),
    (re.compile(r'tailwindcss|/tailwind\.', re.I), "tailwind"),
    (re.compile(r'<link[^>]+rel=["\']?manifest["\']?', re.I), "pwa_manifest"),
    (re.compile(r'fonts\.googleapis\.com|fonts\.gstatic\.com', re.I), "google_fonts"),
    (re.compile(r'<script[^>]+src=["\'][^"\']*\.webflow\.', re.I), "webflow"),
    (re.compile(r'framer\.com/m/|framer-motion', re.I), "framer"),
    (re.compile(r'cdn\.shopify\.com', re.I), "shopify"),
    (re.compile(r'\.webp[?"\'\s]|\.avif[?"\'\s]', re.I), "modern_images"),
    (re.compile(r'class=["\'][^"\']*\b(?:flex|grid|md:|lg:|sm:|xl:)\b', re.I), "modern_css"),
    (re.compile(r'<(?:header|main|footer|nav|article|section|aside)[\s>]', re.I), "html5_semantic"),
]

COPYRIGHT_RE = re.compile(r'(?:copyright|©|&copy;)\s*(?:[a-z\s\.&]+\s)?(\d{4})(?:\s*[-–—]\s*(\d{4}))?', re.I)


def normalize_url(url):
    if not url:
        return ""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def has_https(url):
    return urlparse(url).scheme == "https"


def fetch_html(url, timeout=8):
    """Fetch HTML, return (status, final_url, html, error)."""
    try:
        r = requests.get(url, timeout=timeout, allow_redirects=True, headers=UA)
        return (r.status_code, r.url, r.text, None)
    except requests.exceptions.SSLError:
        # Try HTTP fallback
        if url.startswith("https://"):
            try:
                r = requests.get(url.replace("https://", "http://"), timeout=timeout,
                                 allow_redirects=True, headers=UA)
                return (r.status_code, r.url, r.text, "ssl_fallback_http")
            except requests.RequestException as e2:
                return (None, None, None, f"ssl_then_http_failed")
        return (None, None, None, "ssl_error")
    except requests.RequestException as e:
        return (None, None, None, type(e).__name__)


def score_site(url, html):
    """Returns dict {veillot_hits, recent_hits, copyright_year}."""
    if not html:
        return None

    veillot_hits = []
    recent_hits = []

    for pat, tag in VEILLOT_PATTERNS:
        if pat.search(html):
            veillot_hits.append(tag)
    for pat, tag in RECENT_PATTERNS:
        if pat.search(html):
            recent_hits.append(tag)

    # HTTPS
    if has_https(url):
        recent_hits.append("https")
    else:
        veillot_hits.append("no_https")

    # Copyright year
    current_year = datetime.now().year
    copyright_year = None
    m = COPYRIGHT_RE.search(html)
    if m:
        years = [int(y) for y in m.groups() if y]
        if years:
            copyright_year = max(years)
            if copyright_year >= current_year - 1:
                recent_hits.append(f"copyright_recent_{copyright_year}")
            elif copyright_year < current_year - 4:
                veillot_hits.append(f"copyright_old_{copyright_year}")

    return {
        "veillot_hits": list(dict.fromkeys(veillot_hits)),
        "recent_hits": list(dict.fromkeys(recent_hits)),
        "copyright_year": copyright_year,
    }


def classify(score):
    if not score:
        return "unknown"
    v = len(score["veillot_hits"])
    r = len(score["recent_hits"])
    # Strong recent : >=3 signaux et <=1 veillot
    if r >= 3 and v <= 1:
        return "recent"
    # Strong veillot : >=2 signaux et <=1 recent
    if v >= 2 and r <= 1:
        return "veillot"
    # Default majorite
    if r > v:
        return "recent"
    if v > r:
        return "veillot"
    # Egalite : par defaut veillot (plus prudent pour Mad Makers)
    return "veillot"


def candidate_urls(domain, company_name=""):
    """Returns list of URLs to try."""
    candidates = []
    if domain:
        d = domain.strip()
        if d.startswith("http"):
            d = urlparse(d).netloc
        d = d.lstrip("www.").rstrip("/")
        if d:
            candidates.append(f"https://www.{d}")
            candidates.append(f"https://{d}")
    if company_name and not domain:
        base = unicodedata.normalize("NFKD", company_name.lower()).encode("ascii", "ignore").decode()
        base = re.sub(r"[^a-z0-9 ]", "", base).strip()
        nospace = base.replace(" ", "")
        dashed = base.replace(" ", "-")
        for variant in dict.fromkeys([nospace, dashed]):
            if 3 <= len(variant) <= 30:
                for tld in ("fr", "com"):
                    candidates.append(f"https://{variant}.{tld}")
    return list(dict.fromkeys(candidates))


def get_field(row, *keys):
    """Get first non-empty value from row for any of the keys."""
    for k in keys:
        v = row.get(k, "").strip()
        if v:
            return v
    return ""


def main():
    rows = []
    for path in INPUT_FILES:
        if not path.exists():
            print(f"WARN: {path.name} introuvable, skip")
            continue
        with open(path, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                rows.append(r)

    print(f"Total prospects en input : {len(rows)}")

    # Dedup par Profile ID ou LinkedIn URL
    seen = set()
    unique = []
    for r in rows:
        key = r.get("Profile ID", "").strip() or r.get("Input - LinkedIn URL", "").strip()
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        unique.append(r)
    print(f"Apres dedup                : {len(unique)}\n")

    output = []
    counts = {"sans_site": 0, "avec_site_veillot": 0, "avec_site_recent": 0}

    for i, r in enumerate(unique, 1):
        prenom = get_field(r, "First Name", "Input - First Name")
        nom = get_field(r, "Last Name", "Input - Last Name")
        full = get_field(r, "Input - Full Name") or f"{prenom} {nom}".strip()
        company = get_field(r, "Employer", "Input - Current Employer")
        domain = get_field(r, "Employer Domain")
        website = get_field(r, "Employer Website")
        title = get_field(r, "Title", "Input - Current Title")
        location = get_field(r, "Location", "Input - Location")
        email = get_field(r, "Recommended Email", "Recommended Work Email")
        linkedin = get_field(r, "Input - LinkedIn URL", "LinkedIn")
        company_li = get_field(r, "Input - Company LinkedIn URL", "Employer LinkedIn")

        # Build candidates: prefer Employer Website > Employer Domain > guess from name
        candidates = []
        if website:
            candidates.append(normalize_url(website))
        candidates.extend(candidate_urls(domain, company))
        candidates = list(dict.fromkeys(candidates))

        category = "sans_site"
        site_url = ""
        veillot_signals = []
        recent_signals = []
        copyright_year = ""
        fetch_error = ""

        for url in candidates:
            status, final_url, html, err = fetch_html(url)
            if status and 200 <= status < 400 and html and len(html) > 500:
                score = score_site(final_url, html)
                if score:
                    cls = classify(score)
                    site_url = final_url
                    veillot_signals = score["veillot_hits"]
                    recent_signals = score["recent_hits"]
                    copyright_year = score["copyright_year"] or ""
                    if cls == "recent":
                        category = "avec_site_recent"
                    else:
                        category = "avec_site_veillot"
                    break
            elif err:
                fetch_error = err
            time.sleep(0.2)

        counts[category] = counts.get(category, 0) + 1

        output.append({
            "categorie":           category,
            "prenom":              prenom,
            "nom":                 nom,
            "nom_complet":         full,
            "titre":               title,
            "entreprise":          company,
            "domaine":             domain,
            "site_url":            site_url,
            "email":               email,
            "linkedin_url":        linkedin,
            "entreprise_linkedin": company_li,
            "ville":               location,
            "copyright_year":      copyright_year,
            "veillot_signals":     "; ".join(veillot_signals),
            "recent_signals":      "; ".join(recent_signals),
            "fetch_error":         fetch_error if category == "sans_site" else "",
        })

        if i % 10 == 0 or i == len(unique):
            print(f"[{i:>3}/{len(unique)}] {full[:25]:25s} {company[:22]:22s} -> {category}")

    # Sort par priorite Mad Makers : veillot > sans_site > recent
    sort_order = {"avec_site_veillot": 0, "sans_site": 1, "avec_site_recent": 2}
    output.sort(key=lambda x: (sort_order.get(x["categorie"], 9), x["nom_complet"]))

    with open(OUTPUT, "w", encoding="utf-8-sig", newline="") as f:
        if output:
            w = csv.DictWriter(f, fieldnames=list(output[0].keys()))
            w.writeheader()
            w.writerows(output)

    print(f"\n=== Resume ===")
    print(f"Sans site            : {counts.get('sans_site', 0)}")
    print(f"Avec site veillot    : {counts.get('avec_site_veillot', 0)}  <-- cible refonte Mad Makers")
    print(f"Avec site recent     : {counts.get('avec_site_recent', 0)}")
    print(f"\nCSV trie : {OUTPUT}")


if __name__ == "__main__":
    main()
