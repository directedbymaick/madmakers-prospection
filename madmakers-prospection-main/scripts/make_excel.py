from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = Workbook()
ws = wb.active
ws.title = "Prospects Mad Makers"

headers = [
    "#", "Nom commercial", "Raison sociale", "SIRET", "SIREN",
    "Ville", "Departement", "Adresse", "Code postal",
    "Telephone", "Note Google", "Nb avis", "Type etablissement",
    "Site web", "Signal", "Score ICP", "Date creation",
    "Email prospect", "Dirigeant", "Statut"
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

prospects = [
    (1,  "Le Touring Cafe",               "SESAME",                         "89132308100028","891323081", "Soorts-Hossegor",          "Landes (40)",        "515 Av. du Touring Club",       "40150","05 58 43 92 89",4.1, 652, "Cafe",               "","sans_site",70,"2020-11-24","","Benoit MARTIN-NOGARO","A contacter"),
    (2,  "Au Bastignac",                  "AU BASTIGNAC",                   "83012438400017","830124384", "Labastide-d'Armagnac",    "Landes (40)",        "29 Place Royale",               "40240","05 58 75 11 24",4.6,  93, "Restaurant",         "","sans_site",70,"2017-06-08","alain.baillou@laposte.net","Alain BAILLOU","A contacter"),
    (3,  "Zoo Bar Tapas",                 "EL GATO",                        "39343080600041","393430806", "Moliets-et-Maa",          "Landes (40)",        "21 Rue de la Bastide",          "40660","",             4.7, 193, "Bar",                "","sans_site",70,"1993-12-01","","Martin DOMERGUE","A contacter"),
    (4,  "Midi & Tartes",                 "LE COQ ET LA POULE",             "91948450100029","919484501", "Mont-de-Marsan",          "Landes (40)",        "1 Place Stanislas Baron",       "40000","05 58 06 41 98",4.9,  11, "Restaurant",         "","sans_site",70,"2022-09-21","","Elodie VIGNIER","A contacter"),
    (5,  "La Papiche",                    "LA PAPICHE",                     "95203510300011","952035103", "Saint-Avit",              "Landes (40)",        "50 Av. Etienne Labrit",         "40090","",             4.7,  62, "Restaurant",         "","sans_site",70,"2023-05-05","","Timael LASSARRE","A contacter"),
    (6,  "Restaurant La Gargouille",      "LOGAVANDA",                      "52196158100019","521961581", "Saint-Vincent-de-Tyrosse","Landes (40)",        "40 Av. Cote d'Argent",          "40230","05 58 77 02 80",4.4, 301, "Restaurant",         "","sans_site",70,"2010-04-21","","Sebastien GARAT","A contacter"),
    (7,  "Mont 2 Padel",                  "EOVEST RESTAURATION",            "50328653600019","503286536", "Mazerolles",              "Landes (40)",        "587 Ch. de la Pouillique",      "40090","06 76 21 85 30",4.7,  26, "Complexe sportif",   "","sans_site",70,"2008-03-21","","Audrey MATHIO","A contacter"),
    (8,  "La Tapia",                      "CHAPITELA",                      "90427480000013","904274800", "Dax",                     "Landes (40)",        "30 Pl. de la Fontaine Chaude",  "40100","06 71 95 18 62",4.9, 108, "Restaurant espagnol","","sans_site",70,"2021-10-08","","Alain BAGNERES","A contacter"),
    (9,  "Le QG",                         "SBUC",                           "82788365300038","827883653", "Mont-de-Marsan",          "Landes (40)",        "3 Rue Paul Cassou",             "40000","05 64 72 28 30",4.1, 342, "Bar",                "","sans_site",70,"2017-02-22","","Alexandre RICAUD","A contacter"),
    (10, "Le Bearn Bar",                  "BEARN CAFE",                     "81741737100025","817417371", "Mont-de-Marsan",          "Landes (40)",        "34 Rue Leon Gambetta",          "40000","05 58 75 18 28",3.8,  93, "Bar",                "","sans_site",70,"2015-12-16","","Christophe BAGULHO","A contacter"),
    (11, "Le Bistrot du Coin",            "LELONG CRIMET",                  "87770898200013","877708982", "Geaune",                  "Landes (40)",        "32 Place de l'Hotel de Ville",  "40320","05 58 45 36 78",4.5,  36, "Restaurant",         "","sans_site",70,"2019-09-23","","Julien LELONG","A contacter"),
    (12, "La Tetrade Cote Port",          "EURL PECHERIES DUCAMP III",      "49515887500049","495158875", "Capbreton",               "Landes (40)",        "85 Av. Georges Pompidou",       "40130","05 58 43 51 48",4.4,1379, "Restaurant francais","","sans_site",70,"2007-03-27","","Frederic DULUD","A contacter"),
    (13, "La Tetrade Cote Boutique",      "EURL PECHERIES DUCAMP III",      "49515887500031","495158875", "Capbreton",               "Landes (40)",        "85 Av. Georges Pompidou",       "40130","05 58 43 51 48",4.4,1379, "Restaurant francais","","sans_site",70,"2007-03-27","","Frederic DULUD","A contacter"),
    (14, "Le Poisson Rouge",              "PEIRO",                          "83324948500016","833249485", "Vieux-Boucau-les-Bains",  "Landes (40)",        "1 Av. du Gao, Pl. du Levant",   "40480","05 58 48 19 86",4.6,1158, "Restaurant",         "","sans_site",70,"2017-11-07","","Sylvie PEIXOTO DA SILVA","A contacter"),
    (15, "Rock Food",                     "ROCK FOOD SARL",                 "38045124500027","380451245", "Soorts-Hossegor",          "Landes (40)",        "109 Rue des Landais",           "40150","05 58 43 43 27",3.7, 951, "Restaurant",         "","sans_site",70,"1991-01-08","","Francois-Xavier LECOCQ","A contacter"),
    (16, "Lhospital Poissonnerie Traiteur","LHOSPITAL JULIEN",              "83515463400017","835154634", "Lons",                    "Pays Basque (64)",   "12 Av. des Freres Montgolfier", "64140","05 59 02 50 62",4.2, 102, "Traiteur/Poissonnerie","","sans_site",70,"2018-02-05","","Julien LHOSPITAL","A contacter"),
    (17, "Ceviche Me",                    "CEVICHE ME",                     "95147380000013","951473800", "Pau",                     "Pays Basque (64)",   "7 Rue Leon Daran",              "64000","05 59 33 05 83",4.9,  55, "Restaurant",         "","sans_site",70,"2023-04-11","","Arnauld SOUBIES","A contacter"),
    (18, "Goia",                          "BIAK-BAT",                       "45374658800046","453746588", "Anglet",                  "Pays Basque (64)",   "32 Av. des Dauphins",           "64600","",             4.5, 669, "Restaurant",         "","sans_site",70,"2004-05-01","","Philippe DUFOURCQ","A contacter"),
    (19, "Cidrerie Beti Bai des Platanes","TXIN",                           "94927533300027","949275333", "Anglet",                  "Pays Basque (64)",   "7 Bd de la Mer",                "64600","05 59 03 75 59",4.5,1039, "Restaurant",         "","sans_site",70,"2023-03-01","","Mickael JUMELLE-GAQUIERE","A contacter"),
    (20, "Tavola Calda",                  "TXIN",                           "94927533300019","949275333", "Saint-Jean-de-Luz",       "Pays Basque (64)",   "2 Rue Dornaldeguy",             "64500","05 59 24 84 48",4.7, 507, "Restaurant italien", "","sans_site",70,"2023-03-01","","Mickael JUMELLE-GAQUIERE","A contacter"),
    (21, "Au Comptoir",                   "FRANCK DENCAUSSE",               "45155938900023","451559389", "Saint-Palais",            "Pays Basque (64)",   "1 Av. de Garris",               "64120","05 59 65 72 36",4.3, 137, "Restaurant",         "","sans_site",70,"2003-10-22","","Franck DENCAUSSE","A contacter"),
    (22, "La Chenaie",                    "SOCIETE LA CHENAIE",             "48096480800012","480964808", "Ledeuix",                 "Pays Basque (64)",   "2 Rue de Lamarque",             "64400","",             4.6, 208, "Restaurant francais","","sans_site",70,"2005-02-17","","Rene BOSOM","A contacter"),
    (23, "Restaurant O'Gascon",           "SAS O'GASCON",                   "81939720900019","819397209", "Pau",                     "Pays Basque (64)",   "13 Rue du Chateau",             "64000","05 59 81 51 78",4.2, 918, "Restaurant",         "","sans_site",70,"2016-03-24","","Rocco D'ADDETTA","A contacter"),
    (24, "O-TCHANQUET",                   "L ENTR ACTE",                    "49397095800010","493970958", "Oloron-Sainte-Marie",     "Pays Basque (64)",   "19 Bd de l'Aragon",             "64400","05 59 34 93 38",4.2, 222, "Restaurant",         "","sans_site",70,"2007-02-01","","Marianne BAGES-LIMOGES","A contacter"),
    (25, "La Creperie",                   "LA CREPERIE",                    "91290284800015","912902848", "Orthez",                  "Pays Basque (64)",   "14 Rue Roarie",                 "64300","05 47 73 18 29",4.3, 464, "Restaurant",         "","sans_site",70,"2022-04-13","","Frederic SENTENAC","A contacter"),
    (26, "LA GRILLERIE DU PORT",          "ST-JEAN-DE-LUZ ANIMATIONS",      "78236685000058","782366850", "Saint-Jean-de-Luz",       "Pays Basque (64)",   "Quai du Marechal Leclerc",      "64500","",             4.3, 156, "Fruits de mer",      "","sans_site",70,"1900-01-01","","Frederic CADET","A contacter"),
    (27, "Xuriatea",                      "TXALAPARTA",                     "43044440600010","430444406", "Hasparren",               "Pays Basque (64)",   "4 Rue Francis Jammes",          "64240","05 59 29 60 76",4.6, 348, "Restaurant",         "","sans_site",70,"2000-04-18","","Philippe SAINT ESTEBEN","A contacter"),
    (28, "Le Schuss",                     "LE BEACH",                       "91983618900028","919836189", "Eaux-Bonnes",             "Pays Basque (64)",   "Rte du Col d'Aubisque",         "64440","05 35 53 94 56",4.6, 651, "Restaurant",         "","sans_site",70,"2022-09-29","","Nicolas BEAUCHAMPS","A contacter"),
    (29, "Mimosa",                        "MIMOSA",                         "88110397200017","881103972", "Sare",                    "Pays Basque (64)",   "Place du village",              "64310","05 59 26 57 66",4.2, 358, "Restaurant",         "","sans_site",70,"2020-01-22","","Mathieu THOMAS","A contacter"),
    (30, "Laniakea Anglet",               "THE HOOKER",                     "51094525600020","510945256", "Anglet",                  "Pays Basque (64)",   "Centre Commercial Bab2",        "64600","05 59 63 96 56",4.4,  35, "Bar lounge",         "","sans_site",70,"2009-03-06","","Yannik ALZINE","A contacter"),
]

for row_idx, row in enumerate(prospects, 2):
    is_alt   = (row_idx % 2 == 1)
    base_fill = alt_fill if is_alt else white_fill
    rating   = row[10]
    for col_idx, val in enumerate(row, 1):
        cell = ws.cell(row=row_idx, column=col_idx, value=val)
        cell.border = border
        cell.font   = Font(name="Arial", size=9)
        cell.alignment = center if col_idx in [1, 11, 12, 16] else left
        if col_idx == 11 and isinstance(val, float) and val >= 4.5:
            cell.fill = green_fill
        elif col_idx == 12 and isinstance(rating, float) and rating >= 4.5:
            cell.fill = green_fill
        elif col_idx in [18, 19]:
            cell.fill = orange_fill
        elif col_idx == 20:
            cell.fill = yellow_fill
        else:
            cell.fill = base_fill

widths = [4, 28, 28, 18, 12, 22, 15, 32, 11, 16, 11, 9, 22, 12, 11, 10, 13, 24, 18, 14]
for i, w in enumerate(widths, 1):
    ws.column_dimensions[get_column_letter(i)].width = w

ws.row_dimensions[1].height = 32
for r in range(2, 32):
    ws.row_dimensions[r].height = 20

ws.freeze_panes = "A2"
ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}31"

out = "C:/Users/MAÏCK/Desktop/MadMakers Prospection/madmakers-prospection-main/data/madmakers_prospects_20260417.xlsx"
wb.save(out)
print("Fichier cree :", out)
