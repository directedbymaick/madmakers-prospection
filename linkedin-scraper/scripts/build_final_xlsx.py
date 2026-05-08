"""
build_final_xlsx.py
Construit le fichier XLSX final pour la prospection Mad Makers a partir du CSV
final issue de triage_apply_manual.py.

Layout :
  - Bloc INFOS (fond bleu)         : segment + identite + entreprise + signaux site + email + LinkedIn
  - Colonne SEPARATEUR (orange)    : 1 colonne fine, vide, avec fill orange
  - Bloc TRACKING (fond vert)      : statut, contacts, notes, follow-up, interet

Tri : veillot > sans_site > recent.
"""
import csv, sys
from pathlib import Path
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import CellIsRule

DATA_DIR = Path(r"C:\Users\MAÏCK\Desktop\MadMakers Prospection\linkedin-scraper\data")
TODAY = datetime.now().strftime("%Y%m%d")
INPUT  = DATA_DIR / f"prospects_triage_final_{TODAY}.csv"
OUTPUT = DATA_DIR / f"madmakers_prospection_finale_{TODAY}.xlsx"

# ── Palette ────────────────────────────────────────────────────────────────
FILL_INFO_HEADER     = PatternFill("solid", fgColor="1F3A8A")   # bleu profond
FILL_INFO_BAND       = PatternFill("solid", fgColor="DBEAFE")   # bleu clair
FILL_SEP             = PatternFill("solid", fgColor="F97316")   # orange vif
FILL_TRACK_HEADER    = PatternFill("solid", fgColor="166534")   # vert profond
FILL_TRACK_BAND      = PatternFill("solid", fgColor="DCFCE7")   # vert clair

FILL_CAT_VEILLOT     = PatternFill("solid", fgColor="FEF3C7")   # ambre clair (priorite refonte)
FILL_CAT_SANS_SITE   = PatternFill("solid", fgColor="FEE2E2")   # rouge clair
FILL_CAT_RECENT      = PatternFill("solid", fgColor="E0E7FF")   # indigo clair (low prio)

FONT_HEADER_WHITE = Font(name="Inter", size=11, bold=True, color="FFFFFF")
FONT_BODY         = Font(name="Inter", size=10, color="111827")
FONT_LINK         = Font(name="Inter", size=10, color="1D4ED8", underline="single")

THIN_GREY = Side(style="thin", color="CBD5E1")
BORDER_CELL = Border(left=THIN_GREY, right=THIN_GREY, top=THIN_GREY, bottom=THIN_GREY)

ALIGN_LEFT  = Alignment(horizontal="left",  vertical="center", wrap_text=True)
ALIGN_CENTER= Alignment(horizontal="center",vertical="center", wrap_text=True)


# ── Colonnes (label, key dans CSV ou None pour tracking, largeur) ──────────
INFO_COLUMNS = [
    ("Categorie",         "categorie",          18),
    ("Prenom",            "prenom",             14),
    ("Nom",               "nom",                16),
    ("Titre",             "titre",              28),
    ("Entreprise",        "entreprise",         26),
    ("Site",              "site_url",           34),
    ("Email",             "email",              30),
    ("LinkedIn",          "linkedin_url",       30),
    ("Entreprise LI",     "entreprise_linkedin",30),
    ("Ville",             "ville",              22),
    ("Domaine",           "domaine",            22),
    ("Copyright",         "copyright_year",     11),
    ("Signaux veillot",   "veillot_signals",    34),
    ("Signaux recents",   "recent_signals",     34),
    ("Erreur fetch",      "fetch_error",        18),
]

TRACK_COLUMNS = [
    ("Statut",                None, 16),
    ("Date dernier contact",  None, 16),
    ("Type contact",          None, 18),
    ("Email J0 envoye",       None, 14),
    ("Email J+4 envoye",      None, 14),
    ("Email J+10 envoye",     None, 14),
    ("Email J+18 envoye",     None, 14),
    ("Appel passe",           None, 14),
    ("Notes appel",           None, 38),
    ("Notes email / LI",      None, 38),
    ("Prochain follow-up",    None, 16),
    ("Interet (1-5)",         None, 12),
    ("RDV pris",              None, 14),
    ("Devis envoye",          None, 14),
    ("Signe",                 None, 12),
]

# Listes pour data validation
STATUT_OPTIONS = ["A contacter", "Email envoye", "Relance 1", "Relance 2", "Relance 3", "Repondu", "RDV pris", "Devis envoye", "Signe", "Pas interesse", "Dormant"]
TYPE_CONTACT_OPTIONS = ["Email J0", "Email J+4", "Email J+10", "Email J+18", "Appel", "LinkedIn DM", "Reponse entrante"]
OUI_NON = ["Oui", "Non"]
INTERET_OPTIONS = ["1", "2", "3", "4", "5"]

CAT_FILL = {
    "avec_site_veillot": FILL_CAT_VEILLOT,
    "sans_site":          FILL_CAT_SANS_SITE,
    "avec_site_recent":   FILL_CAT_RECENT,
}
CAT_LABEL = {
    "avec_site_veillot": "VEILLOT (refonte)",
    "sans_site":          "SANS SITE",
    "avec_site_recent":   "RECENT (low prio)",
}


def main():
    if not INPUT.exists():
        print(f"ERREUR: {INPUT} introuvable")
        sys.exit(1)

    with open(INPUT, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    print(f"Charge : {len(rows)} prospects")

    wb = Workbook()
    ws = wb.active
    ws.title = "Prospects Mad Makers"
    ws.sheet_view.showGridLines = False

    # ─── Bandeau titre fusionne ────────────────────────────────────────────
    total_cols = len(INFO_COLUMNS) + 1 + len(TRACK_COLUMNS)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=total_cols)
    title_cell = ws.cell(row=1, column=1, value=f"Mad Makers — Prospection ({len(rows)} prospects) — {TODAY}")
    title_cell.fill = PatternFill("solid", fgColor="111827")
    title_cell.font = Font(name="Inter", size=14, bold=True, color="FFFFFF")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 32

    # ─── Bandeau de bloc (row 2) : INFOS / SEP / TRACKING ──────────────────
    info_start, info_end = 1, len(INFO_COLUMNS)
    sep_col = info_end + 1
    track_start, track_end = sep_col + 1, sep_col + len(TRACK_COLUMNS)

    ws.merge_cells(start_row=2, start_column=info_start, end_row=2, end_column=info_end)
    band_info = ws.cell(row=2, column=info_start, value="INFOS PROSPECT")
    band_info.fill = FILL_INFO_HEADER
    band_info.font = FONT_HEADER_WHITE
    band_info.alignment = ALIGN_CENTER

    sep_band = ws.cell(row=2, column=sep_col, value="")
    sep_band.fill = FILL_SEP

    ws.merge_cells(start_row=2, start_column=track_start, end_row=2, end_column=track_end)
    band_track = ws.cell(row=2, column=track_start, value="TRACKING (a remplir)")
    band_track.fill = FILL_TRACK_HEADER
    band_track.font = FONT_HEADER_WHITE
    band_track.alignment = ALIGN_CENTER

    ws.row_dimensions[2].height = 24

    # ─── Header columns (row 3) ────────────────────────────────────────────
    for idx, (label, _, width) in enumerate(INFO_COLUMNS, start=1):
        c = ws.cell(row=3, column=idx, value=label)
        c.fill = FILL_INFO_HEADER
        c.font = FONT_HEADER_WHITE
        c.alignment = ALIGN_CENTER
        c.border = BORDER_CELL
        ws.column_dimensions[get_column_letter(idx)].width = width

    sep_c = ws.cell(row=3, column=sep_col, value="")
    sep_c.fill = FILL_SEP
    ws.column_dimensions[get_column_letter(sep_col)].width = 2.2

    for idx, (label, _, width) in enumerate(TRACK_COLUMNS, start=track_start):
        c = ws.cell(row=3, column=idx, value=label)
        c.fill = FILL_TRACK_HEADER
        c.font = FONT_HEADER_WHITE
        c.alignment = ALIGN_CENTER
        c.border = BORDER_CELL
        ws.column_dimensions[get_column_letter(idx)].width = width

    ws.row_dimensions[3].height = 32

    # ─── Lignes de donnees ─────────────────────────────────────────────────
    start_row = 4
    for r_idx, row in enumerate(rows, start=start_row):
        cat = row.get("categorie", "")
        cat_fill = CAT_FILL.get(cat, FILL_INFO_BAND)

        for c_idx, (label, key, _) in enumerate(INFO_COLUMNS, start=1):
            if key == "categorie":
                value = CAT_LABEL.get(cat, cat)
            else:
                value = row.get(key, "")
            cell = ws.cell(row=r_idx, column=c_idx, value=value)
            cell.font = FONT_BODY
            cell.alignment = ALIGN_LEFT
            cell.border = BORDER_CELL
            # Categorie -> couleur dediee, sinon fond bleu clair
            if key == "categorie":
                cell.fill = cat_fill
                cell.font = Font(name="Inter", size=10, bold=True, color="111827")
            else:
                cell.fill = FILL_INFO_BAND
            # Hyperliens
            if key in ("site_url", "linkedin_url", "entreprise_linkedin") and value:
                url = value if value.startswith("http") else "https://" + value
                cell.hyperlink = url
                cell.font = FONT_LINK
            elif key == "email" and value:
                cell.hyperlink = f"mailto:{value}"
                cell.font = FONT_LINK

        # Separateur
        sep_cell = ws.cell(row=r_idx, column=sep_col, value="")
        sep_cell.fill = FILL_SEP

        # Bloc tracking : vide, fond vert clair
        for c_idx in range(track_start, track_end + 1):
            cell = ws.cell(row=r_idx, column=c_idx, value="")
            cell.fill = FILL_TRACK_BAND
            cell.font = FONT_BODY
            cell.alignment = ALIGN_LEFT
            cell.border = BORDER_CELL

    end_row = start_row + len(rows) - 1

    # ─── Data validation : listes deroulantes ──────────────────────────────
    def col_letter(idx): return get_column_letter(idx)

    # Map track label -> col index
    track_col_idx = {label: track_start + i for i, (label, _, _) in enumerate(TRACK_COLUMNS)}

    def add_dv(label, options):
        col = track_col_idx[label]
        rng = f"{col_letter(col)}{start_row}:{col_letter(col)}{end_row}"
        dv = DataValidation(type="list", formula1='"' + ",".join(options) + '"', allow_blank=True)
        dv.add(rng)
        ws.add_data_validation(dv)

    add_dv("Statut", STATUT_OPTIONS)
    add_dv("Type contact", TYPE_CONTACT_OPTIONS)
    add_dv("Email J0 envoye", OUI_NON)
    add_dv("Email J+4 envoye", OUI_NON)
    add_dv("Email J+10 envoye", OUI_NON)
    add_dv("Email J+18 envoye", OUI_NON)
    add_dv("Appel passe", OUI_NON)
    add_dv("Interet (1-5)", INTERET_OPTIONS)
    add_dv("RDV pris", OUI_NON)
    add_dv("Devis envoye", OUI_NON)
    add_dv("Signe", OUI_NON)

    # ─── Conditional formatting (interet >=4 highlight, signe = vert) ──────
    # Interet
    interet_col = col_letter(track_col_idx["Interet (1-5)"])
    interet_rng = f"{interet_col}{start_row}:{interet_col}{end_row}"
    ws.conditional_formatting.add(
        interet_rng,
        CellIsRule(operator="greaterThanOrEqual", formula=["4"],
                   fill=PatternFill("solid", fgColor="FCD34D"),
                   font=Font(name="Inter", size=10, bold=True, color="78350F")),
    )
    # Signe = Oui
    signe_col = col_letter(track_col_idx["Signe"])
    signe_rng = f"{signe_col}{start_row}:{signe_col}{end_row}"
    ws.conditional_formatting.add(
        signe_rng,
        CellIsRule(operator="equal", formula=['"Oui"'],
                   fill=PatternFill("solid", fgColor="22C55E"),
                   font=Font(name="Inter", size=10, bold=True, color="FFFFFF")),
    )

    # ─── Freeze : titre + bandeau + header + 1ere col ──────────────────────
    ws.freeze_panes = "C4"

    # ─── AutoFilter sur la zone INFOS ──────────────────────────────────────
    ws.auto_filter.ref = f"A3:{col_letter(info_end)}{end_row}"

    # ─── Onglet README ─────────────────────────────────────────────────────
    readme = wb.create_sheet("README")
    readme.column_dimensions["A"].width = 110
    readme.sheet_view.showGridLines = False
    readme_lines = [
        ("Mad Makers — Prospection finale", "title"),
        ("", None),
        (f"Total prospects : {len(rows)} — Tri : VEILLOT > SANS_SITE > RECENT", "h2"),
        ("", None),
        ("CATEGORIES", "h2"),
        ("• VEILLOT (ambre)   : site existant mais date — cible refonte Mad Makers (priorite 1)", None),
        ("• SANS SITE (rouge) : aucun site detecte — cible creation (priorite 2)", None),
        ("• RECENT (indigo)   : site moderne — low prio, on les contacte en dernier", None),
        ("", None),
        ("LECTURE DU FICHIER", "h2"),
        ("• Bandeau bleu  : infos prospect (statiques, ne pas editer sauf pour corriger une donnee)", None),
        ("• Bande orange  : separateur visuel entre infos et tracking", None),
        ("• Bandeau vert  : zone de saisie (statut, dates, notes, follow-up)", None),
        ("", None),
        ("WORKFLOW DE TRACKING", "h2"),
        ("1. Statut         : choisir dans la liste (A contacter, Email envoye, Relance 1, etc.)", None),
        ("2. Date           : ajouter date au format JJ/MM/AAAA quand contact pris", None),
        ("3. Email J0/J4... : cocher Oui/Non quand chaque etape envoyee", None),
        ("4. Notes          : zone libre (objections, contexte, demandes)", None),
        ("5. Interet (1-5)  : note auto-eval — >=4 ressort en jaune (chaud)", None),
        ("6. Signe = Oui    : ligne ressort en vert (deal closed)", None),
        ("", None),
        ("PRIORISATION HEBDO RECOMMANDEE", "h2"),
        ("• Lundi   : envoyer 20 J0 sur VEILLOT (priorite 1)", None),
        ("• Mardi   : envoyer 20 J0 sur SANS_SITE", None),
        ("• Mercredi: relance J+4 sur les J0 du lundi precedent", None),
        ("• Jeudi   : appels chauds sur prospects Interet >=3", None),
        ("• Vendredi: relance J+10 + J+18 sur stock + reporting", None),
    ]
    for r_i, (text, kind) in enumerate(readme_lines, start=1):
        c = readme.cell(row=r_i, column=1, value=text)
        if kind == "title":
            c.font = Font(name="Inter", size=18, bold=True, color="111827")
        elif kind == "h2":
            c.font = Font(name="Inter", size=12, bold=True, color="1F3A8A")
        else:
            c.font = Font(name="Inter", size=10, color="111827")
        c.alignment = Alignment(wrap_text=True, vertical="top")

    wb.save(OUTPUT)

    # Stats
    counts = {}
    for r in rows:
        counts[r.get("categorie", "")] = counts.get(r.get("categorie", ""), 0) + 1
    print(f"\n=== Distribution finale ===")
    print(f"Sans site            : {counts.get('sans_site', 0)}")
    print(f"Avec site veillot    : {counts.get('avec_site_veillot', 0)}  <-- cible refonte Mad Makers")
    print(f"Avec site recent     : {counts.get('avec_site_recent', 0)}")
    print(f"\nXLSX final : {OUTPUT}")


if __name__ == "__main__":
    main()
