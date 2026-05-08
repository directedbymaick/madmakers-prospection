"""
triage_recheck.py
Re-traite les prospects classes 'sans_site' dans prospects_triage_strict_<date>.csv
avec une strategie de URL discovery beaucoup plus aggressive :

  1. Extraction URL depuis le champ Employer si il a la forme "www.X.tld" ou "X.tld"
  2. Domaine de l'email pro (en filtrant les providers generiques gmail/wanadoo/etc)
  3. Auto TLD-switch : si echec sur .fr essaie .com et inversement
  4. Guess depuis Input - Current Employer en plus de Employer
  5. TLDs etendus : fr, com, io, co, net, eu, agency, studio, org, biz
  6. Variantes nom : sans-espaces, avec-tirets, premier-mot-seul

Re-charge aussi le RocketReach raw input pour avoir tous les champs (email, etc).
Output : prospects_triage_strict_<date>_recheck.csv
"""
import csv, re, sys, time, unicodedata
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import requests

DATA_DIR = Path(r"C:\Users\MAÏCK\Desktop\MadMakers Prospection\linkedin-scraper\data")
INPUTS_DIR = DATA_DIR / "inputs"
TODAY = datetime.now().strftime("%Y%m%d")

INPUT_TRIAGE = DATA_DIR / f"prospects_triage_strict_{TODAY}.csv"
INPUT_ROCKET = [
    INPUTS_DIR / "rocketreach_bulk_100_20260507_v9RvazD.csv",
    INPUTS_DIR / "rocketreach_bulk_101-200_20260507_0V5m28t.csv",
    INPUTS_DIR / "rocketreach_bulk_201-300_20260507_KuL8LKU.csv",
    INPUTS_DIR / "rocketreach_bulk_301-400_20260507_w4WrqtK.csv",
    INPUTS_DIR / "rocketreach_bulk_401-500_20260507_6XU85OQ.csv",
]
OUTPUT = DATA_DIR / f"prospects_triage_strict_{TODAY}_recheck.csv"

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

GENERIC_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "yahoo.fr", "hotmail.com", "hotmail.fr",
    "outlook.com", "outlook.fr", "laposte.net", "wanadoo.fr", "orange.fr",
    "free.fr", "live.fr", "live.com", "icloud.com", "me.com", "msn.com",
    "aol.com", "protonmail.com", "proton.me", "sfr.fr", "neuf.fr",
    "noos.fr", "club-internet.fr", "voila.fr", "tiscali.fr", "numericable.fr",
    "bbox.fr", "skynet.be", "yandex.com", "mail.com", "fastmail.com", "gmx.fr",
    "gmx.com", "gmx.de", "videotron.ca",
}

# Domaines a bannir : annuaires, plateformes, generic - jamais le site d'un prospect
BANNED_DOMAINS = {
    "societe.com", "pagesjaunes.fr", "pages-jaunes.fr", "linkedin.com",
    "wikipedia.org", "wikidata.org", "welcometothejungle.com", "crunchbase.com",
    "bloomberg.com", "facebook.com", "instagram.com", "twitter.com", "x.com",
    "youtube.com", "yelp.fr", "yelp.com", "indeed.fr", "indeed.com", "glassdoor.com",
    "glassdoor.fr", "kompass.com", "manageo.fr", "verif.com", "infogreffe.fr",
    "pappers.fr", "score3.fr", "infonet.fr", "annuaire-mairie.fr", "appvizer.fr",
    "leboncoin.fr", "tiktok.com", "github.com", "medium.com", "substack.com",
    "notion.so", "notion.site", "calendly.com", "typeform.com", "google.com",
    "bing.com", "duckduckgo.com", "yahoo.com", "lemonde.fr", "lefigaro.fr",
    "lesechos.fr", "labcorp.com", "institut.fr", "union.fr", "cafe.com",
    "mare.net", "philippe.io", "space.fr", "lsr.co",
}


def is_banned(url):
    """Check if URL belongs to a banned generic domain."""
    if not url: return False
    d = domain_from_url_string(url)
    return d in BANNED_DOMAINS or any(d.endswith("." + b) for b in BANNED_DOMAINS)

# Patterns repris de triage_sites.py
VEILLOT_PATTERNS = [
    (re.compile(r'<table[^>]*\s(?:width|cellpadding|cellspacing|border)=', re.I), "table_layout"),
    (re.compile(r'<font\s+(?:color|face|size)=', re.I), "font_tag"),
    (re.compile(r'<center>', re.I), "center_tag"),
    (re.compile(r'<frameset|<frame\s', re.I), "frameset"),
    (re.compile(r'jquery[/-]1\.\d', re.I), "jquery_v1"),
]

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

SIGNAUX_RECENT_FORTS = {"nextjs", "nuxtjs", "react", "gatsby", "astro",
                       "tailwind", "pwa_manifest", "webflow", "framer", "shopify"}
SIGNAUX_VEILLOT_FORTS = {"table_layout", "font_tag", "center_tag", "frameset",
                        "jquery_v1", "no_https"}


def normalize_url(url):
    if not url: return ""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def domain_from_url_string(s):
    """Extract clean domain from URL/domain-like string."""
    if not s: return ""
    s = s.strip()
    s = re.sub(r"^https?://", "", s)
    s = s.split("/", 1)[0]
    s = re.sub(r"^www\.", "", s)
    return s.lower()


def looks_like_domain(s):
    """True if string looks like a domain (has TLD, no spaces in main part)."""
    if not s: return False
    s = s.strip()
    if " " in s.replace("www.", ""):
        return False
    return bool(re.search(r"\.[a-z]{2,10}(?:/|$)", s, re.I))


def has_https(url):
    return urlparse(url).scheme == "https"


def fetch_html(url, timeout=8):
    try:
        r = requests.get(url, timeout=timeout, allow_redirects=True, headers=UA)
        return (r.status_code, r.url, r.text, None)
    except requests.exceptions.SSLError:
        if url.startswith("https://"):
            try:
                r = requests.get(url.replace("https://", "http://"), timeout=timeout,
                                 allow_redirects=True, headers=UA)
                return (r.status_code, r.url, r.text, "ssl_fallback_http")
            except requests.RequestException:
                return (None, None, None, "ssl_then_http_failed")
        return (None, None, None, "ssl_error")
    except requests.RequestException as e:
        return (None, None, None, type(e).__name__)


def score_site(url, html):
    if not html: return None
    veillot, recent = [], []
    for pat, tag in VEILLOT_PATTERNS:
        if pat.search(html): veillot.append(tag)
    for pat, tag in RECENT_PATTERNS:
        if pat.search(html): recent.append(tag)
    if has_https(url): recent.append("https")
    else: veillot.append("no_https")

    cy = datetime.now().year
    copyright_year = None
    m = COPYRIGHT_RE.search(html)
    if m:
        years = [int(y) for y in m.groups() if y]
        if years:
            copyright_year = max(years)
            if copyright_year >= cy - 1:
                recent.append(f"copyright_recent_{copyright_year}")
            elif copyright_year < cy - 4:
                veillot.append(f"copyright_old_{copyright_year}")

    return {"veillot_hits": list(dict.fromkeys(veillot)),
            "recent_hits": list(dict.fromkeys(recent)),
            "copyright_year": copyright_year}


def classify_strict(score):
    """Same logic as reclassify_triage : recent only if strong signal."""
    if not score: return "avec_site_veillot"
    v_signals = score["veillot_hits"]
    r_signals = score["recent_hits"]
    cy = datetime.now().year

    # Veillot fort
    if any(s in SIGNAUX_VEILLOT_FORTS for s in v_signals):
        return "avec_site_veillot"
    if any(s.startswith("copyright_old_") for s in v_signals):
        return "avec_site_veillot"
    # Recent fort
    if any(s in SIGNAUX_RECENT_FORTS for s in r_signals):
        return "avec_site_recent"
    for s in r_signals:
        m = re.match(r"copyright_recent_(\d{4})", s)
        if m and int(m.group(1)) >= cy - 1:
            return "avec_site_recent"
    return "avec_site_veillot"


def normalize_for_url(text):
    base = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9 ]", "", base).strip()
    base = re.sub(r"\s+", " ", base)
    return base


def guess_from_text(text, max_len=40, min_word_len=4):
    """Generate URL candidates from a name. NO 'first word only' to eviter les faux
    positifs comme 'union.fr' venant de 'Union Regionale BGE-PACA'."""
    base = normalize_for_url(text)
    if len(base) < 3: return []
    nospace = base.replace(" ", "")
    dashed = base.replace(" ", "-")
    # 2 premiers mots concatenes (pour les noms multi-mots)
    words = base.split()
    two_first = ""
    if len(words) >= 2 and len(words[0]) >= min_word_len and len(words[1]) >= 2:
        two_first = words[0] + words[1]
    variants = [v for v in dict.fromkeys([nospace, dashed, two_first])
                if v and 5 <= len(v) <= max_len]
    candidates = []
    for v in variants:
        for tld in ("fr", "com", "io", "co", "net", "eu", "agency", "studio", "org"):
            candidates.append(f"https://www.{v}.{tld}")
    return candidates


def validate_match(html, company_name, person_name, person_lastname):
    """Verifie que le HTML appartient bien a l'entreprise/personne attendue.
    Retourne True si match plausible, False sinon."""
    if not html: return False
    # Extraire le contenu visible discriminant
    title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I)
    h1_match = re.search(r"<h1[^>]*>([^<]+)</h1>", html, re.I)
    og_title = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', html, re.I)
    og_site = re.search(r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\']([^"\']+)', html, re.I)

    haystack = " ".join([
        title_match.group(1) if title_match else "",
        h1_match.group(1) if h1_match else "",
        og_title.group(1) if og_title else "",
        og_site.group(1) if og_site else "",
    ])
    haystack = normalize_for_url(haystack)

    # Tokens a chercher : nom entreprise (>=4 chars) + nom famille personne
    tokens = []
    for source in (company_name, person_name, person_lastname):
        if source:
            words = normalize_for_url(source).split()
            for w in words:
                if len(w) >= 4:  # ignore mots courts (le, la, de, du, etc.)
                    tokens.append(w)

    if not tokens: return True  # pas de signal -> bypass validation
    if not haystack: return False  # pas de contenu -> can't validate

    # Au moins 1 token doit apparaitre dans le contenu visible
    return any(t in haystack for t in tokens)


def candidates_from_row(row):
    """V2 multi-source URL discovery."""
    cands = []

    # 1. Employer Website
    website = row.get("Employer Website", "").strip()
    if website:
        cands.append(normalize_url(website))

    # 2. Employer Domain
    edomain = row.get("Employer Domain", "").strip()
    if edomain:
        d = domain_from_url_string(edomain)
        if d:
            cands.extend([f"https://www.{d}", f"https://{d}"])

    # 3. Employer field as URL (case Angelique)
    employer = row.get("Employer", "").strip()
    if employer and looks_like_domain(employer):
        d = domain_from_url_string(employer)
        if d:
            cands.extend([f"https://www.{d}", f"https://{d}"])
            # Auto TLD-switch
            if d.endswith(".fr"):
                base = d[:-3]
                cands.extend([f"https://www.{base}.com", f"https://{base}.com"])
            elif d.endswith(".com"):
                base = d[:-4]
                cands.extend([f"https://www.{base}.fr", f"https://{base}.fr"])
            elif d.endswith(".net"):
                base = d[:-4]
                cands.extend([f"https://www.{base}.com", f"https://www.{base}.fr"])

    # 4. Email work domain (filter generic providers)
    for k in ("Recommended Work Email", "Recommended Email"):
        em = row.get(k, "").strip()
        if em and "@" in em:
            ed = em.split("@", 1)[1].strip().lower()
            if ed and ed not in GENERIC_EMAIL_DOMAINS:
                cands.extend([f"https://www.{ed}", f"https://{ed}"])

    # 5. Guess from company names (Employer + Input - Current Employer if different)
    employers_to_guess = []
    if employer and not looks_like_domain(employer):
        employers_to_guess.append(employer)
    inp_emp = row.get("Input - Current Employer", "").strip()
    if inp_emp and inp_emp.lower() != employer.lower():
        employers_to_guess.append(inp_emp)
    for emp in employers_to_guess:
        cands.extend(guess_from_text(emp))

    # 6. Guess from full name UNIQUEMENT pour brand personnelle (cas Angelique Zettor).
    #    On ne guess QUE le "prenomnom" complet, jamais le prenom seul.
    full = row.get("Input - Full Name", "").strip()
    if full:
        normalized = normalize_for_url(full)
        words = normalized.split()
        if len(words) >= 2:  # exige prenom + nom
            both = "".join(words)
            dashed = "-".join(words)
            if 6 <= len(both) <= 40:
                for tld in ("fr", "com", "io", "co"):
                    cands.append(f"https://www.{both}.{tld}")
                    cands.append(f"https://www.{dashed}.{tld}")

    # Filtre final : retire les URLs vers domaines bannis
    out = []
    for c in cands:
        if c and not is_banned(c):
            out.append(c)
    return list(dict.fromkeys(out))


def main():
    if not INPUT_TRIAGE.exists():
        print(f"ERREUR: {INPUT_TRIAGE} introuvable")
        sys.exit(1)

    # Load triage CSV (already classified)
    with open(INPUT_TRIAGE, encoding="utf-8-sig") as f:
        triage_rows = list(csv.DictReader(f))

    # Load original RocketReach CSVs to recover all input fields
    rocket_index = {}  # key = LinkedIn URL or full name -> raw row
    for path in INPUT_ROCKET:
        if not path.exists(): continue
        with open(path, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                key = (r.get("Input - LinkedIn URL", "").strip()
                       or r.get("Input - Full Name", "").strip())
                if key:
                    rocket_index[key] = r

    # Process only sans_site rows
    sans_site_rows = [r for r in triage_rows if r["categorie"] == "sans_site"]
    print(f"Reprocessing {len(sans_site_rows)} prospects classes sans_site...")
    print(f"(URL discovery v2 : email domain, TLD switch, employer URL detection, etc.)\n")

    recovered = 0
    new_classifications = {}  # nom_complet -> (new_cat, site_url, signals)

    for i, trow in enumerate(sans_site_rows, 1):
        # Trouver la row RocketReach correspondante
        full = trow.get("nom_complet", "").strip()
        linkedin = trow.get("linkedin_url", "").strip()
        rraw = rocket_index.get(linkedin) or rocket_index.get(full) or {}

        # Combine triage row + raw rocket data for candidate generation
        merged = {**rraw, **{k: v for k, v in trow.items() if v}}

        cands = candidates_from_row(merged)
        print(f"[{i:>3}/{len(sans_site_rows)}] {full[:30]:30s} -> {len(cands)} candidats")

        company_for_validation = (rraw.get("Employer", "")
                                   or rraw.get("Input - Current Employer", "")
                                   or trow.get("entreprise", ""))
        person_lastname = rraw.get("Last Name", "") or trow.get("nom", "")

        found_url = None
        score = None
        new_cat = "sans_site"

        for url in cands:
            # Ban check (deja filtre dans candidates mais double check)
            if is_banned(url):
                continue
            status, final_url, html, err = fetch_html(url, timeout=6)
            if status and 200 <= status < 400 and html and len(html) > 500:
                # Reject URL if final URL ends up on a banned domain (redirections)
                if is_banned(final_url):
                    continue
                # Reject parking/error pages
                html_lower = html.lower()
                if any(p in html_lower for p in ("domain for sale", "this domain is for sale",
                                                  "godaddy.com/domain", "buy this domain",
                                                  "ce nom de domaine est a vendre")):
                    continue
                # VALIDATION : le contenu doit contenir le nom de l'entreprise OU de la personne
                if not validate_match(html, company_for_validation, full, person_lastname):
                    continue
                s = score_site(final_url, html)
                if s:
                    found_url = final_url
                    score = s
                    new_cat = classify_strict(s)
                    print(f"     FOUND: {final_url[:70]} -> {new_cat}")
                    recovered += 1
                    break
            time.sleep(0.15)

        if not found_url:
            print(f"     no valid match")

        new_classifications[full] = (new_cat, found_url or "", score)

    # Update triage rows
    updated = []
    for trow in triage_rows:
        full = trow.get("nom_complet", "").strip()
        if full in new_classifications:
            new_cat, site_url, score = new_classifications[full]
            new = dict(trow)
            new["categorie"] = new_cat
            if site_url:
                new["site_url"] = site_url
                new["fetch_error"] = ""
                if score:
                    new["veillot_signals"] = "; ".join(score["veillot_hits"])
                    new["recent_signals"] = "; ".join(score["recent_hits"])
                    new["copyright_year"] = score["copyright_year"] or ""
            updated.append(new)
        else:
            updated.append(trow)

    # Re-sort
    sort_order = {"avec_site_veillot": 0, "sans_site": 1, "avec_site_recent": 2}
    updated.sort(key=lambda x: (sort_order.get(x["categorie"], 9), x.get("nom_complet", "")))

    with open(OUTPUT, "w", encoding="utf-8-sig", newline="") as f:
        if updated:
            w = csv.DictWriter(f, fieldnames=list(updated[0].keys()))
            w.writeheader()
            w.writerows(updated)

    # Stats
    counts = {}
    for r in updated:
        counts[r["categorie"]] = counts.get(r["categorie"], 0) + 1

    print(f"\n=== Recovery ===")
    print(f"Sites trouves          : {recovered}/{len(sans_site_rows)}")
    print(f"\n=== Distribution finale ===")
    print(f"Sans site            : {counts.get('sans_site', 0)}")
    print(f"Avec site veillot    : {counts.get('avec_site_veillot', 0)}")
    print(f"Avec site recent     : {counts.get('avec_site_recent', 0)}")
    print(f"\nCSV : {OUTPUT}")


if __name__ == "__main__":
    main()
