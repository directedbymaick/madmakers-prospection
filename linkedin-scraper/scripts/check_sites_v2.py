"""
check_sites_v2.py — Détection fiable de sites web via Google Search
Pour chaque entreprise : cherche "{nom entreprise}" sur Google, vérifie si le 1er résultat est leur site propre.
"""
import pandas as pd
import requests
import re
import time
from googlesearch import search
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from pathlib import Path

INPUT  = r"C:\Users\MAÏCK\Downloads\result.csv"
OUTPUT = r"C:\Users\MAÏCK\Desktop\MadMakers Prospection\linkedin-scraper\data\madmakers_prospects_final.xlsx"

ANNUAIRES = [
    "linkedin.com", "facebook.com", "instagram.com", "twitter.com",
    "societe.com", "pappers.fr", "infogreffe.fr", "verif.com",
    "pages-jaunes.fr", "kompass.com", "manageo.fr", "corporama.com",
    "leboncoin.fr", "youtube.com", "tiktok.com", "welcometothejungle.com",
    "indeed.com", "glassdoor.fr", "crunchbase.com", "appvizer.fr",
]

def is_annuaire(url: str) -> bool:
    return any(a in url for a in ANNUAIRES)

def find_website(company_name: str) -> dict:
    """Cherche le site web d'une entreprise via Google."""
    query = f'"{company_name}" site officiel'
    try:
        results = list(search(query, num_results=5, lang="fr", sleep_interval=2))
        for url in results:
            if not is_annuaire(url):
                # C'est probablement leur site propre
                return {"has_site": True, "url": url}
        # Tous les résultats sont des annuaires = pas de site propre
        return {"has_site": False, "url": ""}
    except Exception as e:
        return {"has_site": None, "url": "", "error": str(e)}

def main():
    df = pd.read_csv(INPUT)
    # Déduplique par entreprise
    companies = df.drop_duplicates(subset=["companyName"]).reset_index(drop=True)

    # Filtres : exclure associations, administrations, hors France
    exclude_sectors = ["Organisations civiques et sociales", "Administration publique",
                       "Services gouvernementaux", "Enseignement primaire et secondaire"]
    exclude_words   = ["CCI ", "VAINCRE", "Championnat", "Ambassadeurs", "Chaine YouTube"]
    companies = companies[~companies["industry"].isin(exclude_sectors)]
    for w in exclude_words:
        companies = companies[~companies["companyName"].str.contains(w, case=False, na=False)]
    companies = companies.reset_index(drop=True)

    total = len(companies)
    print(f"🔍 Vérification de {total} entreprises sur Google...\n")

    sans_site = []
    avec_site = []

    for i, row in companies.iterrows():
        nom = str(row.get("companyName", ""))
        print(f"[{i+1}/{total}] {nom[:50]}", end=" ... ", flush=True)

        result = find_website(nom)

        entry = {
            "Nom":        str(row.get("fullName", "")),
            "Titre":      str(row.get("title", "")),
            "Entreprise": nom,
            "Secteur":    str(row.get("industry", "")) if pd.notna(row.get("industry")) else "",
            "Localisation": str(row.get("companyLocation", "")) or str(row.get("location", "")),
            "LinkedIn":   str(row.get("linkedInProfileUrl", "")) or str(row.get("defaultProfileUrl", "")),
            "Site trouvé": result.get("url", ""),
        }

        if result["has_site"] is True:
            print(f"🟢 {result['url'][:60]}")
            avec_site.append(entry)
        elif result["has_site"] is False:
            print("🔴 Sans site")
            sans_site.append(entry)
        else:
            print(f"⚪ Erreur: {result.get('error','')}")
            sans_site.append(entry)  # Doute → inclure

    print(f"\n{'='*60}")
    print(f"🔴 Sans site propre : {len(sans_site)}")
    print(f"🟢 Avec site       : {len(avec_site)}")
    print(f"{'='*60}\n")

    # Génère l'Excel uniquement avec les sans-site
    make_excel(sans_site)
    print(f"📁 {OUTPUT}")

def make_excel(prospects):
    wb = Workbook()
    ws = wb.active
    ws.title = "Prospects sans site"

    hdr_fill   = PatternFill("solid", fgColor="1a3c6e")
    hdr_font   = Font(bold=True, color="FFFFFF", name="Arial", size=10)
    alt_fill   = PatternFill("solid", fgColor="EEF2FA")
    white_fill = PatternFill("solid", fgColor="FFFFFF")
    orange_fill= PatternFill("solid", fgColor="FFE0B2")
    yellow_fill= PatternFill("solid", fgColor="FFF9C4")
    thin       = Side(style="thin", color="CCCCCC")
    border     = Border(left=thin, right=thin, top=thin, bottom=thin)
    center     = Alignment(horizontal="center", vertical="center")
    left_al    = Alignment(horizontal="left", vertical="center", wrap_text=False)

    headers    = ["#", "Prénom Nom", "Poste", "Entreprise", "Secteur", "Ville", "LinkedIn", "Email", "Statut"]
    col_widths = [4, 22, 28, 30, 25, 28, 45, 28, 14]

    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = hdr_font
        cell.fill = hdr_fill
        cell.alignment = center
        cell.border = border

    for i, p in enumerate(prospects):
        r = i + 2
        base = alt_fill if r % 2 == 1 else white_fill
        loc = p.get("Localisation", "")
        ville = loc.split(",")[0].strip() if loc else ""

        vals = [
            i + 1,
            p.get("Nom", ""),
            p.get("Titre", ""),
            p.get("Entreprise", ""),
            p.get("Secteur", ""),
            ville,
            p.get("LinkedIn", ""),
            "",           # Email vide
            "À contacter",
        ]

        for col, val in enumerate(vals, 1):
            cell = ws.cell(row=r, column=col, value=val)
            cell.border = border
            cell.font = Font(name="Arial", size=9)
            cell.alignment = center if col == 1 else left_al

            if col == 7 and str(val).startswith("http"):
                cell.hyperlink = str(val)
                cell.font = Font(name="Arial", size=9, color="0563C1", underline="single")
                cell.fill = base
            elif col == 8:
                cell.fill = orange_fill
            elif col == 9:
                cell.fill = yellow_fill
            else:
                cell.fill = base

    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[1].height = 30
    for r in range(2, len(prospects) + 2):
        ws.row_dimensions[r].height = 18
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(prospects)+1}"
    wb.save(OUTPUT)

if __name__ == "__main__":
    main()
