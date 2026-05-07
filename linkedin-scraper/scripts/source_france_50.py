"""
source_france_50.py — Batch 50 prospects sans site, France entiere.
Adapte de source_multi_sector.py mais :
  - TARGET = 50
  - DEPTS etendus a ~25 departements representatifs (metropoles + ruralite)
  - Filtre activite renforce : etat A sur etablissement ET unite legale
  - Exclut explicitement les unites legales en cessation (dateCessationUniteLegale)
"""
import json, time, requests, sys, os, re
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

CP_RE = re.compile(r'\b(\d{5})\b')

def extract_cp(addr: str) -> str:
    if not addr:
        return ""
    m = CP_RE.search(addr)
    return m.group(1) if m else ""

# ── Config ──────────────────────────────────────────────────────────────────
ENV_PATH = Path(r"C:\Users\MAÏCK\Desktop\MadMakers Prospection\madmakers-prospection-main\.env")
load_dotenv(ENV_PATH)

INSEE_KEY  = os.getenv("INSEE_API_KEY")
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")

if not INSEE_KEY or not GOOGLE_KEY:
    print("ERREUR : INSEE_API_KEY ou GOOGLE_API_KEY manquant dans .env")
    sys.exit(1)

INSEE_URL  = "https://api.insee.fr/api-sirene/3.11/siret"
PLACES_URL = "https://places.googleapis.com/v1/places:searchText"

DATA_DIR = Path(r"C:\Users\MAÏCK\Desktop\MadMakers Prospection\linkedin-scraper\data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

TODAY = datetime.now().strftime("%Y%m%d")
TARGET = 50
MAX_PER_SECTOR = 6   # 14 secteurs x 6 = 84 max, marge confortable
MAX_PER_DEPT   = 5   # bonne diversite geo (50/5 = 10 dept differents minimum)

# ── Secteurs (large : BTP / Sante / Commerce local) ────────────────────────
SECTORS = [
    {"ape": "43.21A", "label": "Electricien"},
    {"ape": "43.22A", "label": "Plombier / Chauffagiste"},
    {"ape": "43.34Z", "label": "Peintre / Vitrerie"},
    {"ape": "43.32A", "label": "Menuisier"},
    {"ape": "43.33Z", "label": "Carreleur / Sols"},
    {"ape": "43.91A", "label": "Charpentier"},
    {"ape": "43.99B", "label": "Macon"},
    {"ape": "43.31Z", "label": "Platrier"},
    {"ape": "86.90F", "label": "Kine / Osteo"},
    {"ape": "86.23Z", "label": "Chirurgien-dentiste"},
    {"ape": "86.21Z", "label": "Medecin generaliste"},
    {"ape": "96.02A", "label": "Coiffeur"},
    {"ape": "45.20A", "label": "Garage / Auto"},
    {"ape": "56.10A", "label": "Restaurant"},
]

# ── Departements : couverture France metropolitaine ─────────────────────────
DEPTS = [
    {"code": "75", "nom": "Paris"},
    {"code": "92", "nom": "Hauts-de-Seine"},
    {"code": "93", "nom": "Seine-Saint-Denis"},
    {"code": "13", "nom": "Bouches-du-Rhone"},
    {"code": "69", "nom": "Rhone"},
    {"code": "31", "nom": "Haute-Garonne"},
    {"code": "33", "nom": "Gironde"},
    {"code": "59", "nom": "Nord"},
    {"code": "44", "nom": "Loire-Atlantique"},
    {"code": "67", "nom": "Bas-Rhin"},
    {"code": "06", "nom": "Alpes-Maritimes"},
    {"code": "35", "nom": "Ille-et-Vilaine"},
    {"code": "38", "nom": "Isere"},
    {"code": "76", "nom": "Seine-Maritime"},
    {"code": "21", "nom": "Cote-d'Or"},
    {"code": "37", "nom": "Indre-et-Loire"},
    {"code": "63", "nom": "Puy-de-Dome"},
    {"code": "51", "nom": "Marne"},
    {"code": "49", "nom": "Maine-et-Loire"},
    {"code": "17", "nom": "Charente-Maritime"},
    {"code": "29", "nom": "Finistere"},
    {"code": "34", "nom": "Herault"},
    {"code": "57", "nom": "Moselle"},
    {"code": "71", "nom": "Saone-et-Loire"},
    {"code": "84", "nom": "Vaucluse"},
]

# Exclure effectifs > 20 salaries (cible TPE/PME)
EXCLUDE_TRANCHES = {"21","22","31","32","41","42","51","52","53"}

# ── INSEE ────────────────────────────────────────────────────────────────────
def sirene_query(dept: str, ape: str, nombre: int = 50) -> list[dict]:
    cp_min = int(dept) * 1000
    cp_max = cp_min + 999
    # Filtre fort : etat A sur etablissement ET unite legale (exclut cessations / fermes)
    q = (f'periode(activitePrincipaleEtablissement:"{ape}" '
         f'AND etatAdministratifEtablissement:A) '
         f'AND etatAdministratifUniteLegale:A '
         f'AND codePostalEtablissement:[{cp_min:05d} TO {cp_max:05d}]')
    try:
        r = requests.get(INSEE_URL,
            params={"q": q, "nombre": nombre,
                    "tri": "dateDernierTraitementEtablissement desc"},
            headers={"X-INSEE-Api-Key-Integration": INSEE_KEY,
                     "Accept": "application/json"},
            timeout=20)
    except requests.RequestException as e:
        print(f"[INSEE error] {e}")
        return []
    if r.status_code != 200:
        return []
    etabs = r.json().get("etablissements", [])
    results = []
    for e in etabs:
        ul = e.get("uniteLegale", {})
        # Exclusion supplementaire : unite legale en cessation
        if ul.get("etatAdministratifUniteLegale") != "A":
            continue
        if ul.get("dateCessationUniteLegale"):
            continue
        if ul.get("trancheEffectifsUniteLegale","") in EXCLUDE_TRANCHES:
            continue
        adr = e.get("adresseEtablissement", {})
        num   = adr.get("numeroVoieEtablissement") or ""
        typ   = adr.get("typeVoieEtablissement") or ""
        lib   = adr.get("libelleVoieEtablissement") or ""
        cp    = adr.get("codePostalEtablissement") or ""
        ville = adr.get("libelleCommuneEtablissement") or ""
        nom = (ul.get("denominationUsuelleUniteLegale") or
               ul.get("denominationUsuelle1UniteLegale") or
               ul.get("denominationUniteLegale") or
               ul.get("nomUniteLegale") or "")
        results.append({
            "siret":          e.get("siret",""),
            "siren":          e.get("siren",""),
            "raison_sociale": ul.get("denominationUniteLegale","") or nom,
            "nom_commercial": nom,
            "adresse":        f"{num} {typ} {lib}".strip(),
            "cp":             cp,
            "ville":          ville.title() if ville else "",
            "date_creation":  e.get("dateCreationEtablissement",""),
        })
    return results

# ── Google Places ────────────────────────────────────────────────────────────
def places_enrich(nom: str, ville: str, cp: str) -> dict:
    empty = {"gmb_name": nom, "phone": "", "website": None,
             "rating": None, "reviews": 0, "type": "",
             "formatted_address": "", "gmb_found": False}
    if not nom:
        return empty
    query = f"{nom} {ville}".strip()
    payload = {"textQuery": query, "languageCode": "fr", "maxResultCount": 1}
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,"
                            "places.nationalPhoneNumber,places.websiteUri,"
                            "places.rating,places.userRatingCount,"
                            "places.primaryTypeDisplayName,"
                            "places.businessStatus",
    }
    try:
        r = requests.post(PLACES_URL, json=payload, headers=headers, timeout=15)
        if r.status_code != 200:
            return empty
        data = r.json()
        if not data.get("places"):
            return empty
        p = data["places"][0]
        # Exclure les fermes/temporairement fermes
        biz_status = p.get("businessStatus", "OPERATIONAL")
        if biz_status in ("CLOSED_PERMANENTLY", "CLOSED_TEMPORARILY"):
            return {**empty, "gmb_found": True, "biz_status": biz_status}
        return {
            "gmb_name":   p.get("displayName", {}).get("text", nom),
            "phone":      p.get("nationalPhoneNumber", ""),
            "website":    p.get("websiteUri"),
            "rating":     p.get("rating"),
            "reviews":    p.get("userRatingCount", 0),
            "type":       p.get("primaryTypeDisplayName", {}).get("text", ""),
            "formatted_address": p.get("formattedAddress", ""),
            "gmb_found":  True,
            "biz_status": biz_status,
        }
    except requests.RequestException:
        return empty

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print(f"Objectif : {TARGET} prospects sans site - France entiere")
    print(f"Secteurs : {len(SECTORS)} | Departements : {len(DEPTS)}\n")

    prospects = []
    seen_sirets = set()
    dept_counts   = {d["code"]: 0 for d in DEPTS}
    sector_counts = {s["ape"]: 0 for s in SECTORS}

    excluded_ferme = 0
    excluded_mismatch = 0

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
            print(f"[INSEE] {label:30s} {dept['nom']:25s}", end=" ", flush=True)

            etabs = sirene_query(dept["code"], ape, nombre=40)
            print(f"-> {len(etabs):3d} etabs", end=" ", flush=True)

            found_this = 0
            for e in etabs:
                if (len(prospects) >= TARGET
                        or sector_counts[ape] >= MAX_PER_SECTOR
                        or dept_counts[dept["code"]] >= MAX_PER_DEPT):
                    break
                if e["siret"] in seen_sirets:
                    continue

                insee_nom = e["nom_commercial"] or e["raison_sociale"]
                gmb = places_enrich(insee_nom, e["ville"], e["cp"])
                time.sleep(0.25)

                # Validation : si Places a trouve un resultat, il doit etre au meme CP
                # qu'INSEE. Sinon c'est un homonyme (ex : Restaurant Chez Aicha vs
                # electricien meme nom, ou SK BAT MONTPELLIER trouve a Montpellier
                # alors qu'INSEE l'a a Drancy). On rejette pour eviter contamination.
                gmb_cp = extract_cp(gmb.get("formatted_address", ""))
                gmb_valid = gmb["gmb_found"] and gmb_cp == e["cp"]

                if gmb["gmb_found"] and not gmb_valid:
                    excluded_mismatch += 1
                    continue

                # Si Places a valide : appliquer ses filtres (ferme, site web)
                if gmb_valid:
                    if gmb.get("biz_status") in ("CLOSED_PERMANENTLY", "CLOSED_TEMPORARILY"):
                        excluded_ferme += 1
                        continue
                    if gmb["website"]:
                        continue

                # On garde le prospect : INSEE = source de verite (nom, secteur, ville, CP)
                # Places n'enrichit que si valide (telephone, note, type GMB)
                seen_sirets.add(e["siret"])
                sector_counts[ape] += 1
                dept_counts[dept["code"]] += 1
                nom_final = insee_nom or "(sans nom commercial)"
                prospects.append({
                    "num":            len(prospects) + 1,
                    "nom_commercial": nom_final,
                    "raison_sociale": e["raison_sociale"],
                    "siret":          e["siret"],
                    "siren":          e["siren"],
                    "secteur":        label,
                    "ape":            ape,
                    "adresse":        e["adresse"],
                    "cp":             e["cp"],
                    "ville":          e["ville"],
                    "departement":    f"{dept['nom']} ({dept['code']})",
                    "telephone":      gmb["phone"]   if gmb_valid else "",
                    "note_google":    gmb["rating"]  if gmb_valid else None,
                    "nb_avis":        gmb["reviews"] if gmb_valid else 0,
                    "type_gmb":       gmb["type"]    if gmb_valid else "",
                    "date_creation":  e["date_creation"],
                    "signal":         "sans_site" if gmb_valid else "sans_gmb",
                    "dirigeant":      "",
                    "email":          "",
                    "statut":         "A contacter",
                })
                found_this += 1

            print(f"=> +{found_this} (total {len(prospects)})")
            time.sleep(0.3)

    print(f"\nResultat : {len(prospects)} prospects sans site retenus")
    print(f"Exclus (entreprises fermees Google) : {excluded_ferme}")
    print(f"Exclus (homonyme - CP Places != CP INSEE) : {excluded_mismatch}\n")

    # Repartition
    from collections import Counter
    by_sector = Counter(p["secteur"] for p in prospects)
    by_dept   = Counter(p["departement"] for p in prospects)
    print("Par secteur :")
    for k,v in by_sector.most_common():
        print(f"  {v:2d}  {k}")
    print("\nPar departement :")
    for k,v in by_dept.most_common():
        print(f"  {v:2d}  {k}")

    # Exports
    json_out = DATA_DIR / f"batch_france50_{TODAY}.json"
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(prospects, f, ensure_ascii=False, indent=2)

    import csv
    csv_out = DATA_DIR / f"phantombuster_france50_{TODAY}.csv"
    with open(csv_out, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "companyName","firstName","lastName","city","country","industry","siret","phone"])
        writer.writeheader()
        for p in prospects:
            writer.writerow({
                "companyName": p["nom_commercial"],
                "firstName": "", "lastName": "",
                "city": p["ville"], "country": "France",
                "industry": p["secteur"],
                "siret": p["siret"], "phone": p["telephone"],
            })

    make_excel(prospects)
    print(f"\nJSON  : {json_out}")
    print(f"CSV   : {csv_out}")
    print(f"Excel : {DATA_DIR / f'prospects_france50_{TODAY}.xlsx'}")


def make_excel(prospects: list):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Prospects France sans site"

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

    headers = ["#", "Nom commercial", "Raison sociale", "SIRET", "SIREN",
               "Secteur", "APE", "Adresse", "CP", "Ville", "Departement",
               "Telephone", "Note Google", "Nb avis", "Type",
               "Date creation", "Signal", "Dirigeant", "Email", "Statut"]
    col_w = [4, 28, 28, 16, 12, 22, 8, 30, 7, 18, 22,
             14, 10, 8, 18, 12, 10, 22, 26, 13]

    for col, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=col, value=h)
        c.font = hdr_font; c.fill = hdr_fill
        c.alignment = center; c.border = border

    for i, p in enumerate(prospects):
        r = i + 2
        base = alt_fill if r % 2 == 1 else wht_fill
        rating = p.get("note_google")
        vals = [p["num"], p["nom_commercial"], p["raison_sociale"],
                p["siret"], p["siren"], p["secteur"], p["ape"],
                p["adresse"], p["cp"], p["ville"], p["departement"],
                p["telephone"], rating, p["nb_avis"], p["type_gmb"],
                p["date_creation"], p["signal"], p["dirigeant"],
                p["email"], p["statut"]]
        for col, val in enumerate(vals, 1):
            cell = ws.cell(row=r, column=col, value=val)
            cell.border = border
            cell.font = Font(name="Arial", size=9)
            cell.alignment = center if col in [1,4,5,7,9,13,14,16] else left_al
            if col == 13 and isinstance(val, float) and val >= 4.5:
                cell.fill = grn_fill
            elif col == 14 and isinstance(rating, float) and rating >= 4.5:
                cell.fill = grn_fill
            elif col == 18: cell.fill = org_fill
            elif col == 19: cell.fill = org_fill
            elif col == 20: cell.fill = ylw_fill
            else: cell.fill = base

    for i, w in enumerate(col_w, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[1].height = 30
    for r in range(2, len(prospects) + 2):
        ws.row_dimensions[r].height = 18
    ws.freeze_panes = "A2"
    if prospects:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(prospects)+1}"

    out = DATA_DIR / f"prospects_france50_{TODAY}.xlsx"
    wb.save(out)


if __name__ == "__main__":
    main()
