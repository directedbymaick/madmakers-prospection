"""
check_websites.py — Vérifie si chaque entreprise a un site web
Stratégie : Google Search "nom entreprise site officiel" + test HTTP
"""
import pandas as pd
import requests
import re
import json
import time
from pathlib import Path
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor, as_completed

INPUT  = r"C:\Users\MAÏCK\Downloads\result.csv"
OUTPUT_DIR = Path(r"C:\Users\MAÏCK\Desktop\MadMakers Prospection\linkedin-scraper\data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
}

def clean_name(name: str) -> str:
    """Nettoie le nom d'entreprise pour chercher un domaine."""
    n = name.lower()
    n = re.sub(r"\b(sas|sarl|sasu|eurl|sci|sa|sl|ltd|gmbh|inc|group|groupe|france)\b", "", n)
    n = re.sub(r"[^a-z0-9]", "", n)
    return n.strip()

def check_url(url: str, timeout=5) -> dict:
    """Teste si une URL répond et si elle est HTTPS."""
    try:
        r = requests.head(url, headers=HEADERS, timeout=timeout,
                         allow_redirects=True, verify=False)
        final = r.url
        is_https = final.startswith("https://")
        return {"exists": True, "status": r.status_code, "https": is_https, "url": final}
    except Exception:
        return {"exists": False, "status": 0, "https": False, "url": url}

def find_website(company_name: str, company_url: str) -> dict:
    """Cherche le site web d'une entreprise."""
    cn = clean_name(company_name)

    # 1. Teste les domaines communs
    candidates = [
        f"https://www.{cn}.fr",
        f"https://www.{cn}.com",
        f"https://{cn}.fr",
        f"https://{cn}.com",
    ]
    for url in candidates:
        if len(cn) < 3:
            continue
        result = check_url(url)
        if result["exists"] and result["status"] < 400:
            return {**result, "source": "domain_guess"}

    # 2. Cherche via DuckDuckGo HTML (pas d'API nécessaire)
    try:
        query = quote_plus(f'"{company_name}" site officiel')
        r = requests.get(
            f"https://html.duckduckgo.com/html/?q={query}",
            headers=HEADERS, timeout=8
        )
        # Extrait les URLs des résultats
        urls = re.findall(r'href="(https?://(?!(?:www\.)?(?:linkedin|facebook|instagram|twitter|youtube|duckduckgo|google)\.)[\w\-\.]+\.(?:fr|com|io|co|net|org)[^"]*)"', r.text)
        if urls:
            url = urls[0].split("&")[0]
            result = check_url(url)
            if result["exists"]:
                return {**result, "source": "search", "url": url}
    except Exception:
        pass

    return {"exists": False, "status": 0, "https": False, "url": "", "source": "not_found"}

def process_company(row) -> dict:
    company = row["companyName"]
    company_url = str(row.get("regularCompanyUrl", ""))

    result = find_website(company, company_url)

    # Score prospect : plus le score est élevé, plus c'est une opportunité
    score = 0
    signal = ""
    if not result["exists"]:
        score = 80
        signal = "sans_site"
    elif not result["https"]:
        score = 60
        signal = "sans_https"
    else:
        score = 20
        signal = "site_ok"

    return {
        "Nom":          row["fullName"],
        "Titre":        row["title"],
        "Entreprise":   company,
        "Secteur":      row.get("industry", ""),
        "Localisation": row.get("companyLocation", "") or row.get("location", ""),
        "LinkedIn":     row.get("linkedInProfileUrl", "") or row.get("defaultProfileUrl", ""),
        "Site web":     result["url"],
        "Signal":       signal,
        "Score":        score,
        "HTTPS":        result["https"],
    }

def main():
    df = pd.read_csv(INPUT)
    # Déduplique par entreprise — garde le premier prospect de chaque société
    companies = df.drop_duplicates(subset=["companyName"]).reset_index(drop=True)
    total = len(companies)
    print(f"🔍 {total} entreprises à analyser...\n")

    results = []
    done = 0

    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(process_company, row): i
                   for i, row in companies.iterrows()}
        for fut in as_completed(futures):
            try:
                r = fut.result()
                results.append(r)
                done += 1
                signal_icon = "🔴" if r["Signal"] == "sans_site" else "🟡" if r["Signal"] == "sans_https" else "🟢"
                print(f"[{done}/{total}] {signal_icon} {r['Entreprise'][:35]:<35} {r['Signal']}")
            except Exception as e:
                done += 1
                print(f"[{done}/{total}] ⚠️  Erreur : {e}")

    # Trie par score décroissant
    out_df = pd.DataFrame(results).sort_values("Score", ascending=False)

    # Sauvegarde
    out_csv  = OUTPUT_DIR / "prospects_sans_site.csv"
    out_xlsx = OUTPUT_DIR / "prospects_sans_site.xlsx"

    out_df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    out_df.to_excel(out_xlsx, index=False)

    sans_site   = len(out_df[out_df["Signal"] == "sans_site"])
    sans_https  = len(out_df[out_df["Signal"] == "sans_https"])
    site_ok     = len(out_df[out_df["Signal"] == "site_ok"])

    print(f"\n{'='*55}")
    print(f"✅ Résultats :")
    print(f"   🔴 Sans site       : {sans_site}")
    print(f"   🟡 Site sans HTTPS : {sans_https}")
    print(f"   🟢 Site correct    : {site_ok}")
    print(f"\n📁 {out_xlsx}")
    print(f"{'='*55}")

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    main()
