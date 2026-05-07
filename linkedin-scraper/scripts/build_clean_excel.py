"""
build_clean_excel.py — Excel propre avec SIRET via INSEE SIRENE
"""
import pandas as pd
import requests
import time
import re
import os
import sys
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from pathlib import Path
from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent.parent.parent / "madmakers-prospection-main" / ".env"
load_dotenv(ENV_PATH)

INSEE_KEY = os.getenv("INSEE_API_KEY")
if not INSEE_KEY:
    print("ERREUR : INSEE_API_KEY manquant dans .env", file=sys.stderr)
    sys.exit(1)

INPUT     = r"C:\Users\MAÏCK\Desktop\MadMakers Prospection\linkedin-scraper\data\prospects_sans_site.xlsx"
OUTPUT    = r"C:\Users\MAÏCK\Desktop\MadMakers Prospection\linkedin-scraper\data\madmakers_prospects_final.xlsx"

def parse_etab(e: dict) -> dict:
    adr = e.get("adresseEtablissement", {})
    num   = adr.get("numeroVoieEtablissement") or ""
    typ   = adr.get("typeVoieEtablissement") or ""
    lib   = adr.get("libelleVoieEtablissement") or ""
    return {
        "siret":   e.get("siret", ""),
        "siren":   e.get("siren", ""),
        "adresse": f"{num} {typ} {lib}".strip(),
        "cp":      adr.get("codePostalEtablissement") or "",
        "ville":   adr.get("libelleCommuneEtablissement") or "",
        "ape":     e.get("activitePrincipaleEtablissement", ""),
    }

def search_sirene(nom: str) -> dict:
    """Cherche SIRET/SIREN via INSEE SIRENE — essaie plusieurs champs."""
    empty = {"siret": "", "siren": "", "adresse": "", "cp": "", "ville": "", "ape": ""}
    # Nettoie le nom : retire accents parasites, guillemets, parenthèses
    raw = re.sub(r"[\"'()\[\]]", " ", nom).strip()
    # Premier mot significatif (souvent suffit)
    first = re.sub(r"[^a-zA-Z0-9\u00C0-\u017E]", "", raw.split()[0]) if raw.split() else ""

    url = "https://api.insee.fr/api-sirene/3.11/siret"
    hdrs = {"X-INSEE-Api-Key-Integration": INSEE_KEY, "Accept": "application/json"}
    base = {"nombre": 1, "champs": "siret,siren,denominationUniteLegale,adresseEtablissement,activitePrincipaleEtablissement"}

    queries = [
        f'denominationUniteLegale:"{raw}" AND periode(etatAdministratifEtablissement:A)',
        f'denominationUsuelleUniteLegale:"{raw}" AND periode(etatAdministratifEtablissement:A)',
        f'denominationUniteLegale:{first}* AND periode(etatAdministratifEtablissement:A)',
        f'denominationUsuelleUniteLegale:{first}* AND periode(etatAdministratifEtablissement:A)',
    ]

    for q in queries:
        if not first:
            continue
        try:
            r = requests.get(url, params={**base, "q": q}, headers=hdrs, timeout=10)
            if r.status_code == 200:
                etabs = r.json().get("etablissements", [])
                if etabs:
                    return parse_etab(etabs[0])
        except Exception:
            pass
        time.sleep(0.1)

    return empty


def make_excel(prospects: list[dict]):
    wb = Workbook()
    ws = wb.active
    ws.title = "Prospects Mad Makers"

    # Styles
    hdr_fill   = PatternFill("solid", fgColor="1a3c6e")
    hdr_font   = Font(bold=True, color="FFFFFF", name="Arial", size=10)
    alt_fill   = PatternFill("solid", fgColor="EEF2FA")
    white_fill = PatternFill("solid", fgColor="FFFFFF")
    red_fill   = PatternFill("solid", fgColor="FFCCCC")
    orange_fill= PatternFill("solid", fgColor="FFE0B2")
    yellow_fill= PatternFill("solid", fgColor="FFF9C4")
    thin       = Side(style="thin", color="CCCCCC")
    border     = Border(left=thin, right=thin, top=thin, bottom=thin)
    center     = Alignment(horizontal="center", vertical="center", wrap_text=False)
    left       = Alignment(horizontal="left", vertical="center", wrap_text=False)

    headers = [
        "#", "Prénom Nom", "Poste", "Entreprise",
        "SIRET", "SIREN", "APE",
        "Adresse", "CP", "Ville",
        "Secteur LinkedIn", "Localisation",
        "Signal", "Score",
        "LinkedIn Dirigeant",
        "Email", "Statut"
    ]
    col_widths = [4, 22, 26, 28, 16, 12, 9, 30, 8, 18, 25, 25, 12, 8, 42, 26, 14]

    # En-tête
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = hdr_font
        cell.fill = hdr_fill
        cell.alignment = center
        cell.border = border

    # Données
    for i, p in enumerate(prospects):
        r = i + 2
        base = alt_fill if r % 2 == 1 else white_fill

        vals = [
            i + 1,
            p.get("nom", ""),
            p.get("titre", ""),
            p.get("entreprise", ""),
            p.get("siret", ""),
            p.get("siren", ""),
            p.get("ape", ""),
            p.get("adresse", ""),
            p.get("cp", ""),
            p.get("ville", "") or p.get("localisation_ville", ""),
            p.get("secteur", ""),
            p.get("localisation", ""),
            p.get("signal", ""),
            p.get("score", 0),
            p.get("linkedin", ""),
            "",   # Email
            "À contacter",
        ]

        for col, val in enumerate(vals, 1):
            cell = ws.cell(row=r, column=col, value=val)
            cell.border = border
            cell.font = Font(name="Arial", size=9)
            cell.alignment = center if col in [1, 5, 6, 7, 9, 14] else left

            if col == 13:   # Signal
                cell.fill = red_fill
            elif col == 15: # LinkedIn
                if str(val).startswith("http"):
                    cell.hyperlink = str(val)
                    cell.font = Font(name="Arial", size=9, color="0563C1", underline="single")
                cell.fill = base
            elif col == 16: # Email
                cell.fill = orange_fill
            elif col == 17: # Statut
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


def main():
    df = pd.read_excel(INPUT)
    df = df[df["Signal"] == "sans_site"].copy()

    # Filtres qualité
    exclude_sectors = ["Organisations civiques et sociales", "Administration publique",
                       "Services gouvernementaux", "Enseignement primaire et secondaire"]
    exclude_words   = ["CCI", "Association", "Fédération", "CITOYENS ET JUSTICE"]
    df = df[~df["Secteur"].isin(exclude_sectors)]
    for w in exclude_words:
        df = df[~df["Entreprise"].str.contains(w, case=False, na=False)]

    # Score bonus Nouvelle-Aquitaine
    def bonus(row):
        s = int(row["Score"])
        loc = str(row.get("Localisation", ""))
        if "Nouvelle-Aquitaine" in loc: s += 20
        if any(x in loc for x in ["Bordeaux", "Landes", "Pays Basque", "Bayonne", "Pau", "Périgueux", "Arcachon"]): s += 10
        return s

    df["Score"] = df.apply(bonus, axis=1)
    df = df.sort_values("Score", ascending=False).reset_index(drop=True)

    total = len(df)
    print(f"🔍 Enrichissement SIRET pour {total} entreprises...\n")

    prospects = []
    for i, row in df.iterrows():
        nom_entreprise = str(row.get("Entreprise", ""))
        print(f"[{i+1}/{total}] {nom_entreprise[:45]}", end=" ... ", flush=True)

        sirene = search_sirene(nom_entreprise)

        # Extrait la ville depuis localisation si pas trouvé via SIRENE
        loc = str(row.get("Localisation", ""))
        loc_ville = loc.split(",")[0].strip() if loc else ""

        p = {
            "nom":            str(row.get("Nom", "")),
            "titre":          str(row.get("Titre", "")),
            "entreprise":     nom_entreprise,
            "siret":          sirene["siret"],
            "siren":          sirene["siren"],
            "ape":            sirene["ape"],
            "adresse":        sirene["adresse"],
            "cp":             sirene["cp"],
            "ville":          sirene["ville"] or loc_ville,
            "secteur":        str(row.get("Secteur", "")) if pd.notna(row.get("Secteur")) else "",
            "localisation":   loc,
            "signal":         str(row.get("Signal", "")),
            "score":          int(row.get("Score", 0)),
            "linkedin":       str(row.get("LinkedIn", "")),
        }
        prospects.append(p)
        found = "✅ SIRET trouvé" if sirene["siret"] else "⚪ non trouvé"
        print(found)
        time.sleep(0.3)  # respect rate limit INSEE

    make_excel(prospects)
    siret_found = sum(1 for p in prospects if p["siret"])
    print(f"\n{'='*55}")
    print(f"✅ Excel généré : {total} prospects")
    print(f"   SIRET trouvés : {siret_found}/{total}")
    print(f"📁 {OUTPUT}")
    print(f"{'='*55}")


if __name__ == "__main__":
    main()
