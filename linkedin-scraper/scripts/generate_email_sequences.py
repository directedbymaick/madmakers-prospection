"""
generate_email_sequences.py
Pour chaque prospect du CSV rocket_reach_ready, classifie son segment (A/B/C/D/E)
puis genere les 4 emails de la sequence multicanal (J0, J+4, J+10, J+18).

INPUT  : data/rocket_reach_ready_<date>.csv (avec colonnes website_url + signal)
OUTPUT : data/prospection_emails_<date>.csv (colonnes nettoyees, prets pour Lemlist/RR)

Segments :
  A : sans_site (priorite absolue, ecrase autres regles)
  B : DG / Founder / President / CEO / COO (avec site)
  C : DAF / CFO (avec site)
  D : Marketing / CMO (avec site)
  E : autres decideurs

Variables auto-remplies : {prenom}, {entreprise}, {ville}, {secteur}, [SITE]
Placeholders restants pour personnalisation manuelle :
  [LCP], [CONCURRENT_1/2], [POINT_1/2/3], [FUITE_1/2/3],
  [CLIENT_SIMILAIRE], [LEVIER_TECHNIQUE], [STATS_CONCURRENT],
  [LIEN_DRIVE], [CALENDLY], [LIEN]
"""
import csv, re, sys, unicodedata
from pathlib import Path
from datetime import datetime
import requests

DATA_DIR = Path(r"C:\Users\MAÏCK\Desktop\MadMakers Prospection\linkedin-scraper\data")
TODAY = datetime.now().strftime("%Y%m%d")


def find_latest_input() -> Path:
    """Cherche le rocket_reach_ready_YYYYMMDD.csv le plus recent (sans variantes _sans_site)."""
    candidate = DATA_DIR / f"rocket_reach_ready_{TODAY}.csv"
    if candidate.exists():
        return candidate
    # Filtre uniquement les fichiers de la forme rocket_reach_ready_<8 chiffres>.csv
    matches = [p for p in DATA_DIR.glob("rocket_reach_ready_*.csv")
               if re.match(r"^rocket_reach_ready_\d{8}\.csv$", p.name)]
    return sorted(matches)[-1] if matches else candidate


INPUT = find_latest_input()
OUTPUT = DATA_DIR / f"prospection_emails_{TODAY}.csv"

# ── Patterns de classification ─────────────────────────────────────────────
PAT_B = re.compile(
    r"\b(fondateur|fondatrice|founder|founding|cofondateur|co-?fondateur|cofounder|"
    r"ceo|chief executive|president|président|présidente|pdg|"
    r"directeur général|directrice générale|directeur-général|directrice-générale|"
    r"director general|managing director|general manager|"
    r"\bdg\b|gérant|gerant|owner|propriétaire|"
    r"directeur-fondateur|directrice-fondatrice|chef d'entreprise|chairman|chairwoman)\b",
    re.IGNORECASE)

PAT_B_OPS = re.compile(
    r"\b(coo|chief operating|directeur opérationnel|directrice opérationnelle|"
    r"directeur des opérations|directrice des opérations|"
    r"director of operations|head of operations|vp operations)\b",
    re.IGNORECASE)

PAT_C = re.compile(
    r"\b(daf|cfo|directeur financier|directrice financière|directrice financiere|"
    r"directeur administratif|directrice administrative|"
    r"chief financial|finance director|finance manager|head of finance|"
    r"administratif et financier|administrative et financière|"
    r"controleur financier|controleuse financiere|controleur de gestion)\b",
    re.IGNORECASE)

PAT_D = re.compile(
    r"\b(cmo|chief marketing|directeur marketing|directrice marketing|"
    r"head of marketing|marketing manager|director of marketing|"
    r"directeur communication|directrice communication|"
    r"\bgrowth\b|brand manager|chief growth|"
    r"responsable marketing|head of growth|head of communication)\b",
    re.IGNORECASE)

# ── Detection concurrents Mad Makers (filtre large) ────────────────────────
# Industries qui correspondent a des concurrents directs (agences digitales,
# marketing, publicite, relations publiques, design)
INDUSTRIES_CONCURRENT = {
    "services de marketing",
    "services de publicité",
    "services de publicite",
    "services de relations publiques et communication",
    "services de design",
    "services de design graphique",
    "audiovisuel et médias en ligne",
    "production audiovisuelle",
}

# Mots-cles SPECIFIQUES aux agences digitales/com dans le nom de l'entreprise.
# On EVITE volontairement "agence" et "studio" tout courts car ils matchent trop
# de cas non-concurrents (agence de developpement regional, agence de banque,
# studio de yoga, agence interim, etc.) - on s'appuie sur l'industrie pour ceux-la.
PAT_CONCURRENT_NOM = re.compile(
    r"\b(digital|digitale|digitales|"
    r"\bmedia\b|médias?|"
    r"\bcomm\b|"
    r"creative|créatif|créative|créatives|créatifs|"
    r"branding|brand studio|"
    r"interactive|interactif|"
    r"\bseo\b|growth hacking|"
    r"production house|maison de production|"
    r"web agency|digital agency)\b",
    re.IGNORECASE)

# Titres revelant ULTRA-clairement un role d'agence digitale/creative.
# On exclut "Directeur d'agence" tout court car c'est du branch management generique.
PAT_CONCURRENT_TITRE = re.compile(
    r"(directeur de création|directrice de création|"
    r"directeur artistique|directrice artistique|"
    r"creative director|art director|"
    r"directeur de marque|brand director|"
    r"directeur d['’]agence (?:digital|digitale|web|créative|créatif|marketing|media|comm)|"
    r"directrice d['’]agence (?:digital|digitale|web|créative|créatif|marketing|media|comm)|"
    r"head of digital agency|head of creative)",
    re.IGNORECASE)


def is_concurrent(row: dict) -> bool:
    industry = (row.get("industry") or "").strip().lower()
    title = (row.get("title") or "").strip()
    # IMPORTANT : on teste le pattern sur le NOM NETTOYE (sans suffix Sales Nav).
    # Sans cleaning, "BS Experts - Expert-comptable digital" matcherait "digital"
    # alors que le vrai nom de l'entreprise est juste "BS Experts" (cabinet compta).
    company_clean = get_entreprise(row)

    if industry in INDUSTRIES_CONCURRENT:
        return True
    if PAT_CONCURRENT_NOM.search(company_clean):
        return True
    if PAT_CONCURRENT_TITRE.search(title):
        return True
    return False


def classify_segment(row: dict) -> str:
    signal = (row.get("signal") or "").strip()
    title = (row.get("title") or "").strip()

    if signal == "ferme":
        return "EXCLUS_ferme"
    if is_concurrent(row):
        return "EXCLUS_concurrent"
    if signal == "sans_site":
        return "A"
    if PAT_B.search(title) or PAT_B_OPS.search(title):
        return "B"
    if PAT_C.search(title):
        return "C"
    if PAT_D.search(title):
        return "D"
    return "E"


# ── Helpers d'extraction ───────────────────────────────────────────────────
SN_SEPARATORS = (" - ", " — ", " – ", " | ", " · ", " / ", " @ ")


def get_prenom(row: dict) -> str:
    p = (row.get("firstName") or "").strip()
    if p:
        return p
    full = (row.get("fullName") or "").strip()
    if full:
        return full.split()[0]
    return ""


def get_entreprise(row: dict) -> str:
    name = (row.get("companyName") or "").strip()
    for sep in SN_SEPARATORS:
        idx = name.find(sep)
        if idx > 2:
            name = name[:idx]
            break
    return name.strip()


def get_ville(row: dict) -> str:
    loc = (row.get("companyLocation") or "").strip()
    if not loc:
        return ""
    return loc.split(",")[0].strip()


def get_secteur(row: dict) -> str:
    return (row.get("industry") or "").strip()


def get_site(row: dict) -> str:
    """URL du site web depuis Places (peut etre vide)."""
    return (row.get("website_url") or "").strip()


def short_url(url: str) -> str:
    """Pour un affichage plus lisible dans les emails (ex: 'monsite.fr' au lieu de 'https://www.monsite.fr/')."""
    if not url:
        return ""
    u = url.replace("https://", "").replace("http://", "")
    if u.startswith("www."):
        u = u[4:]
    return u.rstrip("/")


# ── Fallback : devine l'URL d'un site quand Places n'en a pas ──────────────
HTTP_HEAD_HDR = {
    "User-Agent": "Mozilla/5.0 (compatible; MadMakersBot/1.0; +https://mad-makers.fr)"
}


def guess_website(name: str, timeout: float = 3.0) -> str:
    """Tente de deviner le site web d'une entreprise par essai d'URLs candidates.
    Utilise pour rattraper les cas type NumWorks (fiche GMB sans URL renseignee
    mais le site existe vraiment). Retourne l'URL trouvee ou ''."""
    if not name or len(name) < 3:
        return ""
    base = unicodedata.normalize("NFKD", name.lower()).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9 ]", "", base).strip()
    base = re.sub(r"\s+", " ", base)
    if len(base) < 3:
        return ""

    # Variantes : sans espaces (numworks) et avec tirets (mad-makers)
    nospace = base.replace(" ", "")
    dashed = base.replace(" ", "-")
    variants = list(dict.fromkeys([nospace, dashed]))
    variants = [v for v in variants if 3 <= len(v) <= 30]

    # On essaie .fr en premier (cible francophone), puis .com
    for variant in variants:
        for tld in ("fr", "com"):
            url = f"https://{variant}.{tld}"
            try:
                r = requests.head(url, timeout=timeout, allow_redirects=True,
                                  headers=HTTP_HEAD_HDR)
                if 200 <= r.status_code < 400:
                    return r.url
            except requests.RequestException:
                continue
    return ""


# ── Mentions RGPD signature ────────────────────────────────────────────────
SIG_COURT = "Maïck — Mad Makers\nmad-makers.fr"

SIG_LEGAL = """\

— — —
Vous recevez ce message car votre profil professionnel correspond à notre cible (décideurs PME). Données issues de votre profil LinkedIn public, traitement basé sur l'intérêt légitime (Art. 6.1.f RGPD). Pour vous opposer à toute relance, répondez "STOP"."""


# ── Templates Segment A — Sans site ────────────────────────────────────────
def tpl_A1(prenom, entreprise, ville, secteur):
    salut = f"Bonjour {prenom}," if prenom else "Bonjour,"
    secteur_txt = secteur or "votre secteur"
    ville_txt = ville or "votre ville"
    objet = f"{entreprise} sur Google — invisible"
    corps = (
        f"{salut}\n\n"
        f"J'ai cherché \"{secteur_txt} à {ville_txt}\" sur Google — {entreprise} n'apparaît "
        f"nulle part. Vos concurrents [CONCURRENT_1] et [CONCURRENT_2] occupent les 3 "
        f"premières places.\n\n"
        f"Sans site, vous perdez chaque mois entre 5 et 20 prospects qui auraient pu vous "
        f"appeler. À votre niveau d'activité, c'est un manque à gagner réel.\n\n"
        f"J'aide des structures comme la vôtre à monter un site qui convertit en 7-10 "
        f"jours. Si l'idée vous parle, je vous prépare une maquette gratuite de ce que "
        f"ça donnerait pour {entreprise}.\n\n"
        f"20 minutes cette semaine pour en parler ?\n\n"
        f"{SIG_COURT}"
        f"{SIG_LEGAL}"
    )
    return objet, corps


def tpl_A2(prenom, entreprise):
    objet = f"Re: {entreprise} sur Google — invisible"
    corps = (
        (f"{prenom},\n\n" if prenom else "")
        + f"Petit suivi — j'ai pris 15 minutes ce matin pour regarder ce que font vos "
        f"concurrents en ligne. [CONCURRENT_1] a investi son site il y a ~2 ans, ils ont "
        f"aujourd'hui [STATS_CONCURRENT].\n\n"
        f"Si vous voulez voir une première version de ce qu'on pourrait faire pour "
        f"{entreprise}, je vous envoie ça d'ici demain. Aucune obligation derrière.\n\n"
        f"Maïck"
    )
    return objet, corps


def tpl_A3_breakup(prenom):
    objet = "Dernier message"
    corps = (
        (f"{prenom},\n\n" if prenom else "")
        + "Je n'insiste pas — si la création de votre site n'est pas prioritaire en ce "
        "moment, c'est ok.\n\n"
        "Je laisse l'analyse à votre disposition ici : [LIEN_DRIVE]\n"
        "Et mon agenda pour plus tard : [CALENDLY]\n\n"
        "Belle suite à vous,\n"
        "Maïck"
    )
    return objet, corps


# ── Templates Segment B — DG / Founder / CEO ───────────────────────────────
def tpl_B1(prenom, entreprise, site):
    salut = f"Bonjour {prenom}," if prenom else "Bonjour,"
    site_txt = short_url(site) if site else "[SITE]"
    objet = f"Page d'accueil de {entreprise} — 1 question"
    corps = (
        f"{salut}\n\n"
        f"J'ai chargé {site_txt} ce matin. Mobile, 4G normale : [LCP] secondes pour afficher "
        f"le hero. 53 % des visiteurs partent au-delà de 3 secondes. Pour une boîte de "
        f"votre taille, ça fait sûrement quelques RDV perdus chaque mois.\n\n"
        f"Je dirige Mad Makers, agence qui refait des sites de PME comme la vôtre en 3 "
        f"semaines, avec un focus sur la conversion et la rapidité — pas la \"refonte "
        f"cosmétique\" classique.\n\n"
        f"Je vous prépare en 24h un audit chiffré spécifique à {entreprise} (temps de "
        f"chargement, fuites de conversion, comparaison avec 2 confrères) ?\n\n"
        f"{SIG_COURT}"
        f"{SIG_LEGAL}"
    )
    return objet, corps


def tpl_B2(prenom, entreprise, site):
    site_txt = short_url(site) if site else "[SITE]"
    objet = f"Re: Page d'accueil de {entreprise}"
    corps = (
        (f"{prenom},\n\n" if prenom else "")
        + f"Pour info, j'ai poussé l'analyse de mon côté — voici les 3 points qui "
        f"ressortent sur {site_txt} :\n\n"
        f"1. [POINT_1]\n"
        f"2. [POINT_2]\n"
        f"3. [POINT_3]\n\n"
        f"Ces 3 points = ~30 % de leads en plus en moyenne sur les sites qu'on refait. "
        f"20 minutes pour vous expliquer ?\n\n"
        f"Maïck"
    )
    return objet, corps


def tpl_B3(prenom, entreprise):
    objet = f"Cas client similaire à {entreprise}"
    corps = (
        (f"{prenom},\n\n" if prenom else "")
        + f"Je viens de finir un projet pour [CLIENT_SIMILAIRE] : de 12 leads/mois à 38 "
        f"leads/mois en 90 jours, après refonte + optimisation SEO.\n\n"
        f"Le levier principal : [LEVIER_TECHNIQUE].\n\n"
        f"Si vous voulez le déroulé complet (1 page A4), je vous l'envoie. Et si ça vous "
        f"paraît applicable à {entreprise}, on s'appelle 20 minutes.\n\n"
        f"Maïck"
    )
    return objet, corps


def tpl_B4(prenom, entreprise):
    objet = "J'arrête de vous écrire"
    corps = (
        (f"{prenom},\n\n" if prenom else "")
        + "Promis, dernier message — pas envie d'être lourd.\n\n"
        "Si la performance de votre site n'est pas un sujet en ce moment, je comprends. "
        "Si elle redevient prioritaire dans 3 ou 6 mois, mon agenda est ici : [CALENDLY].\n\n"
        "L'analyse complète reste disponible : [LIEN_DRIVE].\n\n"
        f"Bonne suite à {entreprise},\n"
        "Maïck"
    )
    return objet, corps


# ── Templates Segment C — DAF ──────────────────────────────────────────────
def tpl_C1(prenom, entreprise, site):
    salut = f"Bonjour {prenom}," if prenom else "Bonjour,"
    site_txt = short_url(site) if site else "[SITE]"
    objet = f"Coût d'acquisition site web — {entreprise}"
    corps = (
        f"{salut}\n\n"
        f"Question rapide : quel est aujourd'hui votre coût d'acquisition par lead via "
        f"{site_txt} ?\n\n"
        f"90 % des DAF que je rencontre n'ont pas la réponse — pas par négligence, mais "
        f"parce que le site n'a pas été pensé comme un canal mesurable. Et pendant ce "
        f"temps, le budget Google Ads grimpe.\n\n"
        f"J'aide des structures de votre taille à reprendre la main : tracking propre, "
        f"conversion mesurée, et souvent une refonte ciblée qui fait baisser le CPL de "
        f"30 à 50 %.\n\n"
        f"Vous avez 20 minutes la semaine prochaine pour qu'on regarde vos chiffres ?\n\n"
        f"{SIG_COURT}"
        f"{SIG_LEGAL}"
    )
    return objet, corps


def tpl_C2(prenom):
    objet = "Re: Coût d'acquisition site web"
    corps = (
        (f"{prenom},\n\n" if prenom else "")
        + "Pour vous donner un repère concret avant notre échange éventuel : sur "
        "[CLIENT_SIMILAIRE], on est passé d'un CPL de 87 € (Google Ads) à un CPL de 24 € "
        "(organique + site refondu) en 6 mois. Investissement initial : 2 800 €. "
        "Payback : 4 mois.\n\n"
        "Je peux vous envoyer le calcul détaillé en 1 page ?\n\n"
        "Maïck"
    )
    return objet, corps


def tpl_C3_breakup(prenom):
    objet = "Je vous laisse tranquille"
    corps = (
        (f"{prenom},\n\n" if prenom else "")
        + "Je n'insiste pas plus — je sais que la fin de trimestre est chargée côté DAF.\n\n"
        "Le calcul de ROI dont je parlais : [LIEN]\n"
        "Si on peut en reparler en septembre/octobre, c'est noté.\n\n"
        "Bon courage pour la clôture,\n"
        "Maïck"
    )
    return objet, corps


# ── Templates Segment D — Marketing ────────────────────────────────────────
def tpl_D1(prenom, entreprise, site):
    salut = f"Bonjour {prenom}," if prenom else "Bonjour,"
    site_txt = short_url(site) if site else "[SITE]"
    objet = f"Conversion {site_txt} — 3 fuites identifiées"
    corps = (
        f"{salut}\n\n"
        f"J'ai analysé le tunnel de conversion de {site_txt} — 3 fuites visibles qui pèsent "
        f"sur vos KPI :\n\n"
        f"1. [FUITE_1]\n"
        f"2. [FUITE_2]\n"
        f"3. [FUITE_3]\n\n"
        f"Je dirige une agence qui se spécialise dans ces optimisations (post-Google Ads, "
        f"post-LinkedIn Ads). Sur les sites qu'on refond, le taux de conversion progresse "
        f"en moyenne de 1,8 % à 4,2 %.\n\n"
        f"Vous avez 20 minutes pour qu'on en discute appliqué à {entreprise} ?\n\n"
        f"{SIG_COURT}"
        f"{SIG_LEGAL}"
    )
    return objet, corps


def tpl_D2(prenom, site):
    site_txt = short_url(site) if site else "[SITE]"
    objet = f"Re: Conversion {site_txt}"
    corps = (
        (f"{prenom},\n\n" if prenom else "")
        + "Pour donner du concret : le point #2 que je signalais, c'est exactement ce "
        "qu'on a corrigé chez [CLIENT_SIMILAIRE]. Résultat : +47 % de soumissions de "
        "formulaire en 6 semaines, sans toucher au budget Ads.\n\n"
        "Si vous voulez le before/after et le détail technique (utile pour remonter à "
        "votre direction), je vous envoie en réponse ?\n\n"
        "Maïck"
    )
    return objet, corps


# ── Generation de la sequence par segment ──────────────────────────────────
def generate_emails(segment, prenom, entreprise, ville, secteur, site):
    empty = ("", "")
    if segment.startswith("EXCLUS"):
        return [empty, empty, empty, empty]

    if segment == "A":
        return [
            tpl_A1(prenom, entreprise, ville, secteur),
            tpl_A2(prenom, entreprise),
            tpl_A3_breakup(prenom),
            empty,
        ]
    if segment == "B":
        return [
            tpl_B1(prenom, entreprise, site),
            tpl_B2(prenom, entreprise, site),
            tpl_B3(prenom, entreprise),
            tpl_B4(prenom, entreprise),
        ]
    if segment == "C":
        return [
            tpl_C1(prenom, entreprise, site),
            tpl_C2(prenom),
            tpl_C3_breakup(prenom),
            empty,
        ]
    if segment == "D":
        return [
            tpl_D1(prenom, entreprise, site),
            tpl_D2(prenom, site),
            tpl_C3_breakup(prenom),
            empty,
        ]
    # Segment E : utilise B
    return [
        tpl_B1(prenom, entreprise, site),
        tpl_B2(prenom, entreprise, site),
        tpl_B3(prenom, entreprise),
        tpl_B4(prenom, entreprise),
    ]


# ── Main ───────────────────────────────────────────────────────────────────
# Colonnes utiles pour la prospection (toutes les autres sont droppees)
OUTPUT_COLUMNS = [
    "segment",
    "prenom",
    "nom",
    "nom_complet",
    "linkedin_url",
    "titre",
    "entreprise",
    "entreprise_linkedin",
    "ville",
    "secteur",
    "site_web",
    "telephone_gmb",
    "signal",
    "email_J0_objet",   "email_J0_corps",
    "email_J4_objet",   "email_J4_corps",
    "email_J10_objet",  "email_J10_corps",
    "email_J18_objet",  "email_J18_corps",
]


def main():
    if not INPUT.exists():
        print(f"ERREUR : {INPUT} introuvable")
        print(f"Lance d'abord source_sales_nav_first.py pour generer ce fichier")
        sys.exit(1)

    with open(INPUT, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    print(f"Traitement {len(rows)} prospects...")
    print(f"(fallback URL guess actif sur les sans-site Places)\n")

    counter = {}
    out_rows = []
    n_guessed = 0

    # 1ere passe : fallback URL guess pour les prospects sans site_web
    # (NumWorks etc. : fiche GMB sans URL liee mais site existe)
    print("== Phase 1/2 : URL guess sur les sans-site ==")
    for i, row in enumerate(rows, 1):
        signal = (row.get("signal") or "").strip()
        site_existing = (row.get("website_url") or "").strip()
        if not site_existing and signal not in ("ferme",):
            entreprise_clean = get_entreprise(row)
            if entreprise_clean and len(entreprise_clean) >= 3:
                guessed = guess_website(entreprise_clean)
                if guessed:
                    n_guessed += 1
                    row["website_url"] = guessed
                    row["signal"] = "site_existant"  # on reclasse
                    print(f"[{i:>4}/{len(rows)}] guess: {entreprise_clean[:30]:30s} -> {guessed[:60]}")
    print(f"Total URLs devinees : {n_guessed}\n")

    print("== Phase 2/2 : Classification + generation emails ==")
    for row in rows:
        seg = classify_segment(row)
        counter[seg] = counter.get(seg, 0) + 1

        prenom = get_prenom(row)
        entreprise = get_entreprise(row) or "votre entreprise"
        ville = get_ville(row)
        secteur = get_secteur(row)
        site = get_site(row)

        emails = generate_emails(seg, prenom, entreprise, ville, secteur, site)

        # Output row : colonnes nettoyees + emails
        out_rows.append({
            "segment":             seg,
            "prenom":              prenom,
            "nom":                 (row.get("lastName") or "").strip(),
            "nom_complet":         (row.get("fullName") or "").strip(),
            "linkedin_url":        (row.get("profileUrl") or "").strip(),
            "titre":               (row.get("title") or "").strip(),
            "entreprise":          entreprise,
            "entreprise_linkedin": (row.get("companyUrl") or "").strip(),
            "ville":               ville,
            "secteur":             secteur,
            "site_web":            site,
            "telephone_gmb":       (row.get("phone_gmb") or "").strip(),
            "signal":              (row.get("signal") or "").strip(),
            "email_J0_objet":      emails[0][0],
            "email_J0_corps":      emails[0][1],
            "email_J4_objet":      emails[1][0],
            "email_J4_corps":      emails[1][1],
            "email_J10_objet":     emails[2][0],
            "email_J10_corps":     emails[2][1],
            "email_J18_objet":     emails[3][0],
            "email_J18_corps":     emails[3][1],
        })

    if not out_rows:
        print("Aucun prospect a traiter")
        sys.exit(0)

    with open(OUTPUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        w.writeheader()
        w.writerows(out_rows)

    print("=== Distribution segments ===")
    order = ["A", "B", "C", "D", "E", "EXCLUS_ferme", "EXCLUS_concurrent"]
    labels = {
        "A": "Sans site (priorite absolue)",
        "B": "DG / Founder / CEO / COO",
        "C": "DAF / CFO",
        "D": "Marketing / CMO",
        "E": "Autres decideurs",
        "EXCLUS_ferme": "Exclus - entreprise fermee",
        "EXCLUS_concurrent": "Exclus - concurrent direct",
    }
    for seg in order:
        if seg in counter:
            print(f"  {seg:25s} {counter[seg]:>5d}  {labels.get(seg, seg)}")

    # Stats sites web trouves
    n_with_site = sum(1 for r in out_rows if r["site_web"] and not r["segment"].startswith("EXCLUS"))
    n_with_phone = sum(1 for r in out_rows if r["telephone_gmb"] and not r["segment"].startswith("EXCLUS"))
    print(f"\nURLs site web auto-injectees     : {n_with_site}")
    print(f"Telephones Google auto-injectees : {n_with_phone}")

    print(f"\nCSV final ({len(OUTPUT_COLUMNS)} colonnes) : {OUTPUT}")
    print(f"\nVariables encore a remplir manuellement avant envoi :")
    print(f"  [LCP]                = temps de chargement mobile")
    print(f"  [CONCURRENT_1/2]     = concurrents locaux")
    print(f"  [POINT_1/2/3]        = 3 points specifiques observes")
    print(f"  [FUITE_1/2/3]        = 3 fuites de conversion")
    print(f"  [CLIENT_SIMILAIRE]   = nom d'un client servi du meme secteur")
    print(f"  [LEVIER_TECHNIQUE]   = leverage applique")
    print(f"  [STATS_CONCURRENT]   = stats concurrent")
    print(f"  [LIEN_DRIVE], [CALENDLY], [LIEN] = tes URLs personnelles")


if __name__ == "__main__":
    main()
