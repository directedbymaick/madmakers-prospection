"""
find_linkedin_profiles.py
Pour chaque entreprise sans site, cherche si un décisionnaire est trouvable
sur LinkedIn via Bing (site:linkedin.com) — sans login, 100% automatique.

Usage : python -X utf8 scripts/find_linkedin_profiles.py
"""
import json, time, re, sys
from pathlib import Path
from urllib.parse import quote_plus

try:
    import requests
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    print("pip install requests openpyxl")
    sys.exit(1)

DATA_DIR   = Path(r"C:\Users\MAÏCK\Desktop\MadMakers Prospection\linkedin-scraper\data")
INPUT_JSON = DATA_DIR / "companies_to_check.json"   # liste brute des prospects
OUTPUT_XLS = DATA_DIR / "prospects_linkedin_verified.xlsx"
OUTPUT_JSON= DATA_DIR / "prospects_linkedin_verified.json"

HDR = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9",
}

ROLES = "fondateur OR pdg OR \"directeur général\" OR gérant OR président OR CEO"

def bing_linkedin_search(company: str) -> dict:
    """
    Cherche sur Bing : site:linkedin.com/in "{company}" (fondateur OR pdg ...)
    Retourne l'URL du premier profil trouvé ou None.
    """
    # 1. Cherche un profil individuel (décisionnaire)
    q_person  = f'site:linkedin.com/in "{company}" ({ROLES})'
    # 2. Cherche la page entreprise LinkedIn
    q_company = f'site:linkedin.com/company "{company}"'

    result = {"person_url": None, "person_name": None,
              "company_url": None, "found": False}

    for q, key_url, key_name in [
        (q_person,  "person_url",  "person_name"),
        (q_company, "company_url", None),
    ]:
        try:
            url = f"https://www.bing.com/search?q={quote_plus(q)}&mkt=fr-FR&setlang=fr"
            r = requests.get(url, headers=HDR, timeout=10)
            html = r.text

            # Extrait les URLs linkedin.com des résultats Bing
            li_urls = re.findall(
                r'href="(https://(?:www\.)?linkedin\.com/(?:in|company)/[^"?&]{3,80})"',
                html
            )
            # Déduplique en gardant l'ordre
            seen, clean = set(), []
            for u in li_urls:
                u2 = u.split("?")[0].rstrip("/")
                if u2 not in seen:
                    seen.add(u2)
                    clean.append(u2)

            if clean:
                result[key_url] = clean[0]
                result["found"] = True

                # Essaie d'extraire le nom depuis le titre Bing
                if key_name:
                    titles = re.findall(r'<h2[^>]*>.*?<a[^>]*>([^<]{5,80})</a>', html)
                    if titles:
                        result[key_name] = titles[0].strip()

        except Exception as e:
            pass

        time.sleep(1.2)  # rate limit Bing

    return result


def make_excel(prospects: list):
    wb = Workbook()
    ws = wb.active
    ws.title = "Prospects LinkedIn vérifiés"

    hdr_fill = PatternFill("solid", fgColor="1a3c6e")
    hdr_font = Font(bold=True, color="FFFFFF", name="Arial", size=10)
    alt_fill = PatternFill("solid", fgColor="EEF2FA")
    wht_fill = PatternFill("solid", fgColor="FFFFFF")
    grn_fill = PatternFill("solid", fgColor="C8E6C9")
    org_fill = PatternFill("solid", fgColor="FFE0B2")
    ylw_fill = PatternFill("solid", fgColor="FFF9C4")
    thin     = Side(style="thin", color="CCCCCC")
    border   = Border(left=thin, right=thin, top=thin, bottom=thin)
    center   = Alignment(horizontal="center", vertical="center")
    left_al  = Alignment(horizontal="left", vertical="center")

    headers    = ["#", "Entreprise", "Secteur", "Ville",
                  "LinkedIn Décisionnaire", "Nom détecté",
                  "LinkedIn Entreprise",
                  "Email", "Statut"]
    col_widths = [4, 32, 25, 22, 48, 22, 45, 28, 14]

    for col, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=col, value=h)
        c.font = hdr_font; c.fill = hdr_fill
        c.alignment = center; c.border = border

    for i, p in enumerate(prospects):
        r = i + 2
        base = alt_fill if r % 2 == 1 else wht_fill
        loc = str(p.get("location", ""))
        ville = loc.split(",")[0].strip() if "," in loc else loc

        vals = [
            i + 1,
            p.get("companyName", ""),
            p.get("industry", ""),
            ville,
            p.get("person_url") or "",
            p.get("person_name") or "",
            p.get("company_url") or "",
            "",
            "À contacter",
        ]

        for col, val in enumerate(vals, 1):
            cell = ws.cell(row=r, column=col, value=str(val) if val else "")
            cell.border = border
            cell.font = Font(name="Arial", size=9)
            cell.alignment = center if col == 1 else left_al

            # Hyper-liens LinkedIn
            if col in (5, 7) and str(val).startswith("http"):
                cell.hyperlink = str(val)
                cell.font = Font(name="Arial", size=9,
                                 color="0563C1", underline="single")
                cell.fill = grn_fill if col == 5 else base
            elif col == 8:
                cell.fill = org_fill
            elif col == 9:
                cell.fill = ylw_fill
            else:
                cell.fill = grn_fill if (col == 5 and val) else base

    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[1].height = 30
    for r in range(2, len(prospects) + 2):
        ws.row_dimensions[r].height = 18
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(prospects)+1}"
    wb.save(OUTPUT_XLS)


def main():
    # Charge la liste des entreprises sans site
    if not INPUT_JSON.exists():
        print(f"Fichier introuvable : {INPUT_JSON}")
        print("Lance d'abord check_sites_v2.py pour générer la liste.")
        sys.exit(1)

    with open(INPUT_JSON, encoding="utf-8") as f:
        all_companies = json.load(f)

    # Garde uniquement les sans-site (results_*.json)
    results_files = sorted(DATA_DIR.glob("results_*.json"))
    if results_files:
        websites = {}
        for rf in results_files:
            with open(rf, encoding="utf-8") as f:
                for item in json.load(f):
                    websites[item["idx"]] = item.get("website", "SANS_SITE")

        sans_site = [
            c for c in all_companies
            if websites.get(c["idx"], "SANS_SITE").upper() == "SANS_SITE"
               or not websites.get(c["idx"])
        ]
    else:
        sans_site = all_companies

    total = len(sans_site)
    print(f"🔍 Recherche LinkedIn pour {total} entreprises sans site...\n")

    enriched = []
    found_count = 0

    for i, company in enumerate(sans_site):
        nom = company.get("companyName", "")
        print(f"[{i+1}/{total}] {nom[:45]:<45}", end=" ", flush=True)

        li = bing_linkedin_search(nom)
        company.update(li)
        enriched.append(company)

        if li["person_url"]:
            found_count += 1
            print(f"✅ {li['person_url'][:55]}")
        elif li["company_url"]:
            print(f"🏢 page entreprise seulement")
        else:
            print("⚪ non trouvé")

    # Trie : profil personne trouvé en premier
    enriched.sort(key=lambda x: (
        0 if x.get("person_url") else
        1 if x.get("company_url") else 2
    ))

    # Sauvegarde JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)

    # Génère Excel
    make_excel(enriched)

    with_person  = sum(1 for e in enriched if e.get("person_url"))
    with_company = sum(1 for e in enriched if e.get("company_url") and not e.get("person_url"))
    nothing      = total - with_person - with_company

    print(f"\n{'='*60}")
    print(f"✅ {total} entreprises sans site analysées")
    print(f"   🟢 Décisionnaire LinkedIn trouvé : {with_person}")
    print(f"   🏢 Page entreprise seulement     : {with_company}")
    print(f"   ⚪ Aucune présence LinkedIn       : {nothing}")
    print(f"\n📁 {OUTPUT_XLS}")
    print(f"{'='*60}")
    print(f"\n→ Les {with_person} prospects avec décisionnaire LinkedIn")
    print(f"  sont tes cibles prioritaires : sans site MAIS digital-aware.")


if __name__ == "__main__":
    main()
