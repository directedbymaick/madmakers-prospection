"""
source_multi_sector.py — Batch 150 prospects sans site
Secteurs : BTP artisans, Santé libérale, Commerce local
Source : INSEE SIRENE + Google Places (vérification website)
Sortie : CSV Phantombuster + Excel de revue
"""
import json, time, requests, re, sys, os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# ── Config ──────────────────────────────────────────────────────────────────
ENV_PATH = Path(__file__).resolve().parent.parent.parent / "madmakers-prospection-main" / ".env"
load_dotenv(ENV_PATH)

INSEE_KEY  = os.getenv("INSEE_API_KEY")
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")

if not INSEE_KEY or not GOOGLE_KEY:
    print("ERREUR : INSEE_API_KEY ou GOOGLE_API_KEY manquant dans .env", file=sys.stderr)
    sys.exit(1)

INSEE_URL   = "https://api.insee.fr/api-sirene/3.11/siret"
PLACES_URL  = "https://places.googleapis.com/v1/places:searchText"

DATA_DIR = Path(r"C:\Users\MAÏCK\Desktop\MadMakers Prospection\linkedin-scraper\data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

TODAY = datetime.now().strftime("%Y%m%d")
TARGET = 150
MAX_PER_SECTOR = 12   # max prospects retenus par secteur (14 secteurs × 12 = 168 max)
MAX_PER_DEPT   = 35   # max prospects par département (~150/5 = 30, marge pour combler)

# ── Secteurs prioritaires (étude de marché Mad Makers 2026) ─────────────────
SECTORS = [
    # --- BTP / Artisans (priorité 1) ---
    {"ape": "43.21A", "label": "Électricien",          "priority": 1},
    {"ape": "43.22A", "label": "Plombier / Chauffagiste","priority": 1},
    {"ape": "43.34Z", "label": "Peintre / Vitrerie",   "priority": 1},
    {"ape": "43.32A", "label": "Menuisier",             "priority": 1},
    {"ape": "43.33Z", "label": "Carreleur / Sols",      "priority": 1},
    {"ape": "43.91A", "label": "Charpentier",           "priority": 1},
    {"ape": "43.99B", "label": "Maçon",                 "priority": 1},
    {"ape": "43.31Z", "label": "Plâtrier",              "priority": 1},
    # --- Santé libérale (priorité 1) ---
    {"ape": "86.90F", "label": "Kiné / Ostéo",         "priority": 1},
    {"ape": "86.23Z", "label": "Chirurgien-dentiste",   "priority": 1},
    {"ape": "86.21Z", "label": "Médecin généraliste",   "priority": 2},
    # --- Commerce local (priorité 2) ---
    {"ape": "96.02A", "label": "Coiffeur",              "priority": 2},
    {"ape": "45.20A", "label": "Garage / Auto",         "priority": 2},
    {"ape": "56.10A", "label": "Restaurant",            "priority": 2},
]

DEPTS = [
    {"code": "40", "nom": "Landes"},
    {"code": "64", "nom": "Pyrénées-Atlantiques"},
    {"code": "33", "nom": "Gironde"},
    {"code": "17", "nom": "Charente-Maritime"},
    {"code": "24", "nom": "Dordogne"},
]

# Exclure effectifs > 20 salariés
EXCLUDE_TRANCHES = {"21","22","31","32","41","42","51","52","53"}

# ── INSEE ────────────────────────────────────────────────────────────────────
def sirene_query(dept: str, ape: str, nombre: int = 100) -> list[dict]:
    cp_min = int(dept) * 1000
    cp_max = cp_min + 999
    q = (f'periode(activitePrincipaleEtablissement:"{ape}" '
         f'AND etatAdministratifEtablissement:A) '
         f'AND codePostalEtablissement:[{cp_min} TO {cp_max}]')
    r = requests.get(INSEE_URL,
        params={"q": q, "nombre": nombre,
                "tri": "dateDernierTraitementEtablissement desc"},
        headers={"X-INSEE-Api-Key-Integration": INSEE_KEY,
                 "Accept": "application/json"},
        timeout=20)
    if r.status_code != 200:
        return []
    etabs = r.json().get("etablissements", [])
    results = []
    for e in etabs:
        ul = e.get("uniteLegale", {})
        if ul.get("trancheEffectifsUniteLegale","") in EXCLUDE_TRANCHES:
            continue
        adr = e.get("adresseEtablissement", {})
        num   = adr.get("numeroVoieEtablissement") or ""
        typ   = adr.get("typeVoieEtablissement") or ""
        lib   = adr.get("libelleVoieEtablissement") or ""
        cp    = adr.get("codePostalEtablissement") or ""
        ville = adr.get("libelleCommuneEtablissement") or ""
        # Nom commercial prioritaire, sinon raison sociale
        nom   = (ul.get("denominationUsuelle1UniteLegale") or
                 ul.get("denominationUniteLegale") or
                 ul.get("nomUniteLegale") or "")
        results.append({
            "siret":        e.get("siret",""),
            "siren":        e.get("siren",""),
            "raison_sociale": ul.get("denominationUniteLegale",""),
            "nom_commercial": nom,
            "adresse":      f"{num} {typ} {lib}".strip(),
            "cp":           cp,
            "ville":        ville.title(),
            "date_creation": e.get("dateCreationEtablissement",""),
        })
    return results

# ── Google Places ────────────────────────────────────────────────────────────
def places_enrich(nom: str, ville: str, cp: str) -> dict:
    """Cherche l'établissement sur Google Maps, retourne phone + website + note."""
    empty = {"gmb_name": nom, "phone": "", "website": None,
             "rating": None, "reviews": 0, "type": "", "gmb_found": False}
    query = f"{nom} {ville}"
    payload = {
        "textQuery": query,
        "languageCode": "fr",
        "maxResultCount": 1,
    }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,"
                            "places.nationalPhoneNumber,places.websiteUri,"
                            "places.rating,places.userRatingCount,"
                            "places.primaryTypeDisplayName",
    }
    try:
        r = requests.post(PLACES_URL, json=payload, headers=headers, timeout=15)
        if r.status_code != 200 or not r.json().get("places"):
            return empty
        p = r.json()["places"][0]
        return {
            "gmb_name":   p.get("displayName", {}).get("text", nom),
            "phone":      p.get("nationalPhoneNumber", ""),
            "website":    p.get("websiteUri"),          # None si pas de site
            "rating":     p.get("rating"),
            "reviews":    p.get("userRatingCount", 0),
            "type":       p.get("primaryTypeDisplayName", {}).get("text", ""),
            "gmb_found":  True,
        }
    except Exception:
        return empty

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print(f"🎯 Objectif : {TARGET} prospects sans site — BTP, Santé, Commerce local")
    print(f"📍 Zones : {', '.join(d['nom'] for d in DEPTS)}\n")

    prospects = []
    seen_sirets = set()

    dept_counts = {d["code"]: 0 for d in DEPTS}
    sector_counts = {s["ape"]: 0 for s in SECTORS}

    for sector in SECTORS:
        if len(prospects) >= TARGET:
            break
        for dept in DEPTS:
            if len(prospects) >= TARGET:
                break
            if sector_counts[sector["ape"]] >= MAX_PER_SECTOR:
                break
            if dept_counts[dept["code"]] >= MAX_PER_DEPT:
                continue
            ape, label = sector["ape"], sector["label"]
            print(f"[INSEE] {label} ({ape}) — {dept['nom']}...", end=" ", flush=True)

            etabs = sirene_query(dept["code"], ape, nombre=80)
            print(f"{len(etabs)} établissements", end=" → ", flush=True)

            found_this = 0
            for e in etabs:
                if (len(prospects) >= TARGET
                        or sector_counts[ape] >= MAX_PER_SECTOR
                        or dept_counts[dept["code"]] >= MAX_PER_DEPT):
                    break
                if e["siret"] in seen_sirets:
                    continue

                # Google Places : vérification website
                gmb = places_enrich(e["nom_commercial"] or e["raison_sociale"],
                                    e["ville"], e["cp"])
                time.sleep(0.3)

                # On ne garde que les SANS SITE
                if gmb["website"]:
                    continue

                seen_sirets.add(e["siret"])
                sector_counts[ape] += 1
                dept_counts[dept["code"]] += 1
                prospects.append({
                    "num":            len(prospects) + 1,
                    "nom_commercial": gmb["gmb_name"],
                    "raison_sociale": e["raison_sociale"],
                    "siret":          e["siret"],
                    "siren":          e["siren"],
                    "secteur":        label,
                    "ape":            ape,
                    "adresse":        e["adresse"],
                    "cp":             e["cp"],
                    "ville":          e["ville"],
                    "departement":    f"{dept['nom']} ({dept['code']})",
                    "telephone":      gmb["phone"],
                    "note_google":    gmb["rating"],
                    "nb_avis":        gmb["reviews"],
                    "type_gmb":       gmb["type"],
                    "date_creation":  e["date_creation"],
                    "signal":         "sans_site",
                    "dirigeant":      "",
                    "email":          "",
                    "statut":         "À contacter",
                })
                found_this += 1

            print(f"{found_this} retenus (total : {len(prospects)})")
            time.sleep(0.5)

    print(f"\n✅ {len(prospects)} prospects sans site collectés\n")

    # ── Export JSON ──────────────────────────────────────────────────────────
    json_out = DATA_DIR / f"batch_multisector_{TODAY}.json"
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(prospects, f, ensure_ascii=False, indent=2)

    # ── Export CSV Phantombuster ─────────────────────────────────────────────
    import csv
    csv_out = DATA_DIR / f"phantombuster_input_{TODAY}.csv"
    with open(csv_out, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "companyName", "firstName", "lastName",
            "city", "country", "industry",
            "siret", "phone"
        ])
        writer.writeheader()
        for p in prospects:
            writer.writerow({
                "companyName": p["nom_commercial"],
                "firstName":   "",
                "lastName":    "",
                "city":        p["ville"],
                "country":     "France",
                "industry":    p["secteur"],
                "siret":       p["siret"],
                "phone":       p["telephone"],
            })

    # ── Export Excel ─────────────────────────────────────────────────────────
    make_excel(prospects)

    print(f"📁 JSON    : {json_out}")
    print(f"📁 CSV     : {csv_out}")
    print(f"📁 Excel   : {DATA_DIR / f'prospects_sans_site_{TODAY}.xlsx'}")


def make_excel(prospects: list):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Prospects sans site"

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

    headers = [
        "#", "Nom commercial", "Raison sociale", "SIRET", "SIREN",
        "Secteur", "APE", "Adresse", "CP", "Ville", "Département",
        "Téléphone", "Note Google", "Nb avis", "Type",
        "Date création", "Signal", "Dirigeant", "Email", "Statut"
    ]
    col_w = [4, 28, 28, 16, 12, 18, 8, 30, 7, 18, 20,
             14, 10, 8, 18, 12, 10, 22, 26, 13]

    for col, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=col, value=h)
        c.font = hdr_font; c.fill = hdr_fill
        c.alignment = center; c.border = border

    for i, p in enumerate(prospects):
        r = i + 2
        base = alt_fill if r % 2 == 1 else wht_fill
        rating = p.get("note_google")

        vals = [
            p["num"], p["nom_commercial"], p["raison_sociale"],
            p["siret"], p["siren"], p["secteur"], p["ape"],
            p["adresse"], p["cp"], p["ville"], p["departement"],
            p["telephone"], rating, p["nb_avis"], p["type_gmb"],
            p["date_creation"], p["signal"],
            p["dirigeant"], p["email"], p["statut"],
        ]

        for col, val in enumerate(vals, 1):
            cell = ws.cell(row=r, column=col, value=val)
            cell.border = border
            cell.font = Font(name="Arial", size=9)
            cell.alignment = center if col in [1,4,5,7,9,13,14,16] else left_al

            if col == 13 and isinstance(val, float) and val >= 4.5:
                cell.fill = grn_fill
            elif col == 14 and isinstance(rating, float) and rating >= 4.5:
                cell.fill = grn_fill
            elif col == 18:   # Dirigeant
                cell.fill = org_fill
            elif col == 19:   # Email
                cell.fill = org_fill
            elif col == 20:   # Statut
                cell.fill = ylw_fill
            else:
                cell.fill = base

    for i, w in enumerate(col_w, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[1].height = 30
    for r in range(2, len(prospects) + 2):
        ws.row_dimensions[r].height = 18
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(prospects)+1}"

    out = DATA_DIR / f"prospects_sans_site_{TODAY}.xlsx"
    wb.save(out)


if __name__ == "__main__":
    main()
