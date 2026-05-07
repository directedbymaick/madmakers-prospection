from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from urllib.parse import quote_plus

wb = Workbook()
ws = wb.active
ws.title = "Prospects Sante Mad Makers"

headers = [
    "#", "Nom commercial", "Raison sociale", "SIRET", "SIREN",
    "Ville", "Departement", "Adresse", "Code postal",
    "Telephone", "Note Google", "Nb avis", "Type etablissement",
    "Site web", "Signal", "Score ICP", "Date creation",
    "Email prospect", "Dirigeant", "LinkedIn (a verifier)", "Statut"
]

header_fill = PatternFill("solid", fgColor="1a3c6e")
header_font = Font(bold=True, color="FFFFFF", name="Arial", size=10)
alt_fill    = PatternFill("solid", fgColor="EEF2FA")
white_fill  = PatternFill("solid", fgColor="FFFFFF")
green_fill  = PatternFill("solid", fgColor="C8E6C9")
orange_fill = PatternFill("solid", fgColor="FFE0B2")
yellow_fill = PatternFill("solid", fgColor="FFF3CD")
thin   = Side(style="thin", color="CCCCCC")
border = Border(left=thin, right=thin, top=thin, bottom=thin)
center = Alignment(horizontal="center", vertical="center")
left   = Alignment(horizontal="left", vertical="center", wrap_text=True)

for col, h in enumerate(headers, 1):
    cell = ws.cell(row=1, column=col, value=h)
    cell.font      = header_font
    cell.fill      = header_fill
    cell.alignment = center
    cell.border    = border

# Format: (#, nom_commercial, raison_sociale, siret, siren, ville, dept,
#          adresse, cp, tel, note, avis, type, site, signal, score,
#          date_creation, email, dirigeant, linkedin_search, statut)
# Note: praticiens individuels => dirigeant = leur propre nom
# LinkedIn = lien de recherche pre-formate a verifier manuellement

def li(nom, specialite, ville):
    q = quote_plus(f"{nom} {specialite} {ville}")
    return f"https://www.linkedin.com/search/results/people/?keywords={q}"

prospects = [
    (1,  "Cabinet Gilbert Vaysse",           "GILBERT VAYSSE",                        "49404372200029","494043722", "Haut-Mauco",          "Landes (40)",      "740 Route de Benquet",           "40280","05 58 06 47 33",5.0,  10, "Sante liberale",       "","sans_site",65,"2007-02-01","","Gilbert VAYSSE",           li("Gilbert Vaysse","kinesitherapeute","Landes"),          "A contacter"),
    (2,  "Cabinet Nathalie Bolon",            "NATHALIE BOLON",                        "90034743600017","900347436", "Mont-de-Marsan",      "Landes (40)",      "138 Avenue de l'Etang",          "40000","05 54 00 01 31",3.8,  10, "Medecin",              "","sans_site",65,"2021-07-05","","Nathalie BOLON",            li("Nathalie Bolon","medecin","Mont-de-Marsan"),           "A contacter"),
    (3,  "Cabinet Ariane Gasulla",            "ARIANE GASULLA",                        "78844895900023","788448959", "Mees",                "Landes (40)",      "26 Route de la Garenne",         "40990","06 80 54 42 91",5.0,  24, "Sante liberale",       "","sans_site",65,"2012-09-10","","Ariane GASULLA",            li("Ariane Gasulla","sante","Landes"),                     "A contacter"),
    (4,  "Cabinet Virginie Zeng",             "VIRGINIE ZENG",                         "38521414300070","385214143", "Audon",               "Landes (40)",      "1 Route du Mourliou",            "40400","07 71 78 62 41",5.0,  22, "Sante liberale",       "","sans_site",65,"1992-05-18","","Virginie ZENG",             li("Virginie Zeng","kinesitherapeute","Landes"),           "A contacter"),
    (5,  "Cabinet Fabien Menard",             "FABIEN MENARD",                         "53357723500047","533577235", "Saint-Jean-de-Marsacq","Landes (40)",     "229 Route du Cricq",             "40230","06 79 20 77 52",5.0,  56, "Sante liberale",       "","sans_site",65,"2011-07-04","","Fabien MENARD",             li("Fabien Menard","kinesitherapeute osteopathe","Landes"), "A contacter"),
    (6,  "Cabinet Francoise Bauer",           "FRANCOISE BAUER",                       "90512354300019","905123543", "Seignosse",           "Landes (40)",      "2963 Avenue Charles de Gaulle",  "40510","05 58 72 89 18",4.0, 108, "Sante liberale",       "","sans_site",65,"2021-10-06","","Francoise BAUER",           li("Francoise Bauer","sante","Seignosse Landes"),          "A contacter"),
    (7,  "Cabinet Jim Wibaut",                "JIM WIBAUT",                            "53081052200025","530810522", "Capbreton",           "Landes (40)",      "54 Boulevard des Cigales",       "40130","06 71 09 42 27",5.0,  12, "Sante liberale",       "","sans_site",65,"2011-03-07","","Jim WIBAUT",                li("Jim Wibaut","sante osteopathe","Capbreton"),           "A contacter"),
    (8,  "Cabinet Helene Dicharry",           "HELENE DICHARRY",                       "91491952700012","914919527", "Peyrehorade",         "Landes (40)",      "1292 Chemin de Laregle",         "40300","05 58 73 03 25",4.7,  58, "Sante liberale",       "","sans_site",65,"2022-05-20","","Helene DICHARRY",           li("Helene Dicharry","sante","Peyrehorade Landes"),        "A contacter"),
    (9,  "Asso. Zootherapie Autonomie Eveil", "ASSOC ZOOTHERAPIE AUTONOMIE ET EVEIL",  "79433126400026","794331264", "Biscarrosse",         "Landes (40)",      "1518 Avenue de la Plage",        "40600","06 87 00 62 20",4.8,  31, "Zootherapie",          "","sans_site",65,"2013-06-26","","A identifier",             li("zootherapie autonomie eveil","association","Biscarrosse"), "A contacter"),
    (10, "Cabinet Marie-Christine Corrihons", "MARIE CHRISTINE CORRIHONS",             "83197654300015","831976543", "Tarnos",              "Landes (40)",      "11 Rue Pierre Hugues",           "40220","05 58 46 18 97",4.7, 321, "Sante liberale",       "","sans_site",65,"2017-10-01","","Marie-Christine CORRIHONS", li("Marie-Christine Corrihons","sante","Tarnos"),          "A contacter"),
    (11, "Cabinet Joelle Herbecq",            "JOELLE HELENA ISABEL HERBECQ",          "81143806800017","811438068", "Saint-Vincent-de-Paul","Landes (40)",     "136 Route d'Arnaudin",           "40990","05 58 55 97 90",4.5, 465, "Sante liberale",       "","sans_site",65,"2015-01-04","","Joelle HERBECQ",            li("Joelle Herbecq","sante","Landes"),                     "A contacter"),
    (12, "Mathilde B — Centre Reflexologie",  "MATHILDE B CENTRE DE REFLEXOLOGIE",     "90970449600019","909704496", "Saint-Jean-de-Marsacq","Landes (40)",     "2306 Route de Lurcq",            "40230","06 49 81 72 38",5.0,  24, "Reflexologie/Bien-etre","","sans_site",65,"2022-01-20","","Mathilde B.",               li("Mathilde reflexologie bien-etre","Saint-Jean-de-Marsacq","Landes"), "A contacter"),
    (13, "Cabinet Claire Larbaigt",           "CLAIRE LARBAIGT",                       "81521634600024","815216346", "Benesse-Maremne",     "Landes (40)",      "39 Impasse du Bois Vert",        "40230","06 83 53 38 00",5.0,  10, "Sante liberale",       "","sans_site",65,"2016-01-04","","Claire LARBAIGT",           li("Claire Larbaigt","sante","Landes"),                    "A contacter"),
    (14, "Cabinet Joel Baille",               "JOEL BAILLE",                           "79092015100020","790920151", "Aubagnan",            "Landes (40)",      "204 Chemin de Mounach",          "40700","05 58 79 16 32",4.5, 205, "Sante liberale",       "","sans_site",65,"2013-03-01","","Joel BAILLE",               li("Joel Baille","kinesitherapeute osteopathe","Landes"),   "A contacter"),
    (15, "Cabinet Christophe Lucido",         "CHRISTOPHE LUCIDO",                     "44489283000035","444892830", "Soorts-Hossegor",     "Landes (40)",      "178 Avenue Maitre Pierre",       "40150","06 50 83 06 03",5.0,  34, "Sante liberale",       "","sans_site",65,"2003-01-14","","Christophe LUCIDO",         li("Christophe Lucido","sante osteopathe","Hossegor"),      "A contacter"),
    (16, "Esentzia",                          "LEA CHERONNEAU",                        "93081751500024","930817515", "Cheraute",            "Pays Basque (64)", "25 Avenue Gaztelaia",            "64130","07 63 21 78 46",5.0,  14, "Sante/Bien-etre",      "","sans_site",65,"2024-07-03","","Lea CHERONNEAU",            li("Lea Cheronneau","sante bien-etre","Pays Basque"),       "A contacter"),
    (17, "Eden Tidas",                        "EDEN TIDAS",                            "94842745500019","948427455", "Charre",              "Pays Basque (64)", "2 Route de Navarre",             "64190","07 80 82 89 69",4.1,  79, "Bien-etre",            "","sans_site",65,"2023-02-01","","Eden TIDAS",               li("Eden Tidas","bien-etre","Pays Basque"),                 "A contacter"),
    (18, "Cabinet Pierre Espel",              "PIERRE ESPEL",                          "31252923300032","312529233", "Biarritz",            "Pays Basque (64)", "18 Impasse Labordotte",          "64200","05 59 23 88 38",4.7,  12, "Sante liberale",       "","sans_site",65,"1978-01-01","","Pierre ESPEL",              li("Pierre Espel","kinesitherapeute sante","Biarritz"),     "A contacter"),
    (19, "Cabinet Christian Etchepare",       "CHRISTIAN ETCHEPARE",                   "88203681700014","882036817", "Pau",                 "Pays Basque (64)", "1 Rue Blaise Pascal",            "64000","06 13 67 87 22",5.0,  16, "Sante liberale",       "","sans_site",65,"2020-02-14","","Christian ETCHEPARE",       li("Christian Etchepare","sante osteopathe","Pau"),         "A contacter"),
    (20, "Cabinet Sandrine Lade",             "SANDRINE LADE",                         "81339926800016","813399268", "Salies-de-Bearn",     "Pays Basque (64)", "Chemin de Saint Pe",             "64270","06 87 42 24 68",5.0,  35, "Sante liberale",       "","sans_site",65,"2015-08-06","","Sandrine LADE",             li("Sandrine Lade","kinesitherapeute","Salies-de-Bearn"),   "A contacter"),
    (21, "Cabinet Tiffany Girault",           "TIFFANY GIRAULT",                       "88002230600018","880022306", "Urrugne",             "Pays Basque (64)", "14 Residence Kochepe",           "64122","06 63 72 50 07",5.0,  16, "Massage/Bien-etre",    "","sans_site",65,"2019-12-23","","Tiffany GIRAULT",           li("Tiffany Girault","massage bien-etre","Urrugne"),        "A contacter"),
    (22, "Cabinet Marie Arrambide",           "MARIE ARRAMBIDE",                       "40308931100027","403089311", "Anglet",              "Pays Basque (64)", "3 Avenue Armand Toulet",         "64600","06 19 26 58 29",5.0,  13, "Sante liberale",       "","sans_site",65,"1996-01-01","","Marie ARRAMBIDE",           li("Marie Arrambide","kinesitherapeute sante","Anglet"),    "A contacter"),
    (23, "Cabinet Karine Mlakar",             "KARINE MLAKAR",                         "89469942000010","894699420", "Serres-Castet",       "Pays Basque (64)", "13 Allee du Benou",              "64121","05 59 33 18 06",5.0,  12, "Sante liberale",       "","sans_site",65,"2021-03-01","","Karine MLAKAR",             li("Karine Mlakar","sante osteopathe","Serres-Castet Pau"), "A contacter"),
    (24, "Cabinet Melanie Dirson",            "MELANIE DIRSON",                        "84366659500031","843666595", "Arbonne",             "Pays Basque (64)", "30 Chemin d'Arditegia",          "64210","07 61 27 85 98",5.0,  26, "Sante liberale",       "","sans_site",65,"2018-11-01","","Melanie DIRSON",            li("Melanie Dirson","sante kinesitherapeute","Arbonne Biarritz"), "A contacter"),
    (25, "Cabinet Sophie Pouille",            "SOPHIE POUILLE",                        "75154054300012","751540543", "Billere",             "Pays Basque (64)", "10 Place Jules Gois",            "64140","07 77 38 49 96",4.9,  21, "Sante liberale",       "","sans_site",65,"2012-05-15","","Sophie POUILLE",            li("Sophie Pouille","sante kinesitherapeute","Billere Pau"), "A contacter"),
    (26, "Cabinet Michel Gontier",            "MICHEL GONTIER",                        "35378948000038","353789480", "Castres-Gironde",     "Gironde (33)",     "5 Route de Pomarede",            "33640","05 56 67 29 86",4.3,  12, "Sante liberale",       "","sans_site",65,"1989-07-01","","Michel GONTIER",            li("Michel Gontier","kinesitherapeute sante","Gironde"),    "A contacter"),
    (27, "Cabinet Johanna Maccioni",          "JOHANNA MACCIONI",                      "92764530900026","927645309", "Bordeaux",            "Gironde (33)",     "21 Rue Servandoni",              "33000","07 49 73 48 20",5.0,  13, "Cabinet de sante",     "","sans_site",65,"2024-04-29","","Johanna MACCIONI",          li("Johanna Maccioni","sante osteopathe","Bordeaux"),       "A contacter"),
    (28, "Chiropraxie Benjamin Dauba",        "SELARL CHIROPRAXIE BENJAMIN DAUBA DC",  "82938680400027","829386804", "Gradignan",           "Gironde (33)",     "21 Avenue de la Poterie",        "33170","05 57 96 33 00",4.6,  17, "Chiropracteur",        "","sans_site",65,"2017-02-15","","Benjamin DAUBA",            li("Benjamin Dauba","chiropracteur","Bordeaux Gradignan"),  "A contacter"),
]

for row_idx, row in enumerate(prospects, 2):
    is_alt   = (row_idx % 2 == 1)
    base_fill = alt_fill if is_alt else white_fill
    rating   = row[10]
    for col_idx, val in enumerate(row, 1):
        cell = ws.cell(row=row_idx, column=col_idx, value=val)
        cell.border = border
        cell.font   = Font(name="Arial", size=9)
        cell.alignment = center if col_idx in [1, 11, 12, 16, 20] else left
        if col_idx == 11 and isinstance(val, float) and val >= 4.5:
            cell.fill = green_fill
        elif col_idx == 12 and isinstance(rating, float) and rating >= 4.5:
            cell.fill = green_fill
        elif col_idx in [18, 19]:
            cell.fill = orange_fill
        elif col_idx == 20:
            # Colonne LinkedIn : lien cliquable en bleu LinkedIn
            cell.fill = PatternFill("solid", fgColor="E8F0FE")
            if val:
                cell.hyperlink = val
                cell.value = "🔎 Rechercher sur LinkedIn"
                cell.font = Font(name="Arial", size=9, color="0A66C2", underline="single")
        elif col_idx == 21:
            cell.fill = yellow_fill
        else:
            cell.fill = base_fill

widths = [4, 30, 30, 18, 12, 22, 16, 32, 11, 16, 11, 9, 22, 12, 11, 10, 13, 24, 22, 26, 14]
for i, w in enumerate(widths, 1):
    ws.column_dimensions[get_column_letter(i)].width = w

ws.row_dimensions[1].height = 32
for r in range(2, len(prospects) + 2):
    ws.row_dimensions[r].height = 20

ws.freeze_panes = "A2"
ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(prospects) + 1}"

out = "C:/Users/MAÏCK/Desktop/MadMakers Prospection/madmakers-prospection-main/data/madmakers_prospects_sante_20260423.xlsx"
wb.save(out)
print("Fichier cree :", out)
