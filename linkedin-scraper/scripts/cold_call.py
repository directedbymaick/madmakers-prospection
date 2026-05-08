"""
cold_call.py
Genere un brief HTML autonome pour un cold call Mad Makers.

Usage :
  python -X utf8 scripts/cold_call.py --name "Daniel Schemla"
  python -X utf8 scripts/cold_call.py --index 12
  python -X utf8 scripts/cold_call.py --name "Marchand" --no-fetch

Le brief contient :
  - Identite prospect (nom, titre, entreprise, ville, LinkedIn, email)
  - Audit live du site (HTTPS, security headers, technos, copyright, PageSpeed link)
  - Pain points probables (deduits de la categorie + titre + signaux)
  - Script d'ouverture adapte (sans_site / veillot / recent)
  - Questions de decouverte (4 themes, cochables)
  - Demande de visuels a recolter
  - Pitch transition vers RDV 2 (maquette)
  - Objections + reponses pre-redigees
  - Zone notes editable (persistee en localStorage)
  - Outcome (RDV pris, date, prochaine etape)

Output : data/briefings/<slug>_<date>.html (autonome, imprimable)
"""
import argparse, csv, re, sys, html as htmllib, ssl, socket
import unicodedata, webbrowser
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import requests

DATA_DIR = Path(r"C:\Users\MAÏCK\Desktop\MadMakers Prospection\linkedin-scraper\data")
BRIEFINGS_DIR = DATA_DIR / "briefings"
TODAY = datetime.now().strftime("%Y%m%d")

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

# ── Detection technos (reuse triage patterns) ──────────────────────────────
TECH_PATTERNS = [
    (re.compile(r'__NEXT_DATA__|next/script|/_next/', re.I),         "Next.js"),
    (re.compile(r'window\.__NUXT__|/_nuxt/', re.I),                  "Nuxt.js"),
    (re.compile(r'react-dom|/static/js/main\.[a-f0-9]+\.js', re.I),  "React"),
    (re.compile(r'astro-island|/_astro/', re.I),                     "Astro"),
    (re.compile(r'gatsby-app|/page-data/', re.I),                    "Gatsby"),
    (re.compile(r'tailwindcss|/tailwind\.', re.I),                   "Tailwind CSS"),
    (re.compile(r'\.webflow\.', re.I),                               "Webflow"),
    (re.compile(r'framer\.com/m/|framer-motion', re.I),              "Framer"),
    (re.compile(r'cdn\.shopify\.com', re.I),                         "Shopify"),
    (re.compile(r'wp-content/|wp-includes/', re.I),                  "WordPress"),
    (re.compile(r'elementor', re.I),                                 "Elementor"),
    (re.compile(r'/wix-thunderbolt/|static\.wixstatic\.com', re.I),  "Wix"),
    (re.compile(r'squarespace', re.I),                               "Squarespace"),
    (re.compile(r'jquery[/-]1\.\d', re.I),                           "jQuery 1.x (vetuste)"),
    (re.compile(r'jquery[/-]3\.', re.I),                             "jQuery 3"),
    (re.compile(r'bootstrap[/-]', re.I),                             "Bootstrap"),
    (re.compile(r'<table[^>]*\s(?:width|cellpadding)=', re.I),       "Layout en table HTML (vetuste)"),
    (re.compile(r'<frameset|<frame\s', re.I),                        "Frameset (90s)"),
    (re.compile(r'fonts\.googleapis\.com', re.I),                    "Google Fonts"),
]

VEILLOT_TAGS_HUMAN = {
    "table_layout":    "Layout en tableau HTML (annees 2000)",
    "font_tag":        "Balise <font> obsolete",
    "center_tag":      "Balise <center> obsolete",
    "frameset":        "Frameset (annees 90)",
    "jquery_v1":       "jQuery 1.x (insecurise)",
    "no_https":        "Pas de HTTPS",
    "iso_charset":     "Encodage ISO (charset legacy)",
}

# ── Pain points par categorie (FAITS UNIQUEMENT, jamais d'invention chiffree)
PAINS_SANS_SITE = [
    ("CRITIQUE", "Aucune presence digitale proprietaire",
     "Sans site, ce sont LinkedIn / annuaires / Google My Business qui portent seuls l'image — vous ne controlez ni la narration, ni le SEO, ni le tunnel de conversion."),
    ("HAUT",     "Cout d'opportunite sur les recherches Google",
     "À chiffrer ENSEMBLE pendant l'appel : nombre de prospects/mois qui pourraient decouvrir l'entreprise via Google × valeur d'un client moyen. Ne JAMAIS avancer un chiffre invente."),
    ("HAUT",     "Aucun contenu indexable",
     "Invisibilite sur les requetes locales et metier. Chaque mois sans site = mois ou la concurrence capte la demande organique."),
    ("MOYEN",    "Dependance aux plateformes tierces",
     "Si LinkedIn change son algo ou suspend un compte, l'image de marque disparait. Un nom de domaine est inalienable."),
    ("MOYEN",    "Pas de tunnel de conversion 24/7",
     "Tout passe par appel/email manuel. Un site avec landing pages + formulaires qualifie a froid pendant que vous dormez."),
]

PAINS_VEILLOT = [
    ("CRITIQUE", "Premiere impression visuelle datee",
     "Le visuel actuel ne reflete plus le standard 2026. À constater ENSEMBLE pendant l'appel via partage d'ecran."),
    ("HAUT",     "Responsive mobile a verifier en live",
     "La majorite du trafic web est mobile. Si le site se deforme sur smartphone, le prospect bounce avant lecture du contenu. À tester en live (devtools mobile)."),
    ("HAUT",     "Performances probablement degradees",
     "Sans optimisations modernes (compression d'images webp/avif, lazy-loading, code-splitting), les Core Web Vitals fail — Google penalise activement le SEO."),
    ("HAUT",     "Surface d'attaque securite",
     "Anciennes versions de jQuery / WordPress / absence de headers HTTP de securite = vulnerabilites CVE publiques exploitables. Risque RGPD si fuite de donnees."),
    ("MOYEN",    "Tracking / analytics modernes a confirmer",
     "Sans GA4 / Plausible / Matomo configure, aucune visibilite chiffree sur ce qui convertit. Question a poser."),
    ("MOYEN",    "Signal de fraicheur Google faible",
     "Google indexe la frequence de mise a jour. Un site fige depuis plusieurs annees perd des positions au profit de concurrents qui publient regulierement."),
    ("MOYEN",    "Hierarchie d'information & CTA a auditer en live",
     "À verifier ENSEMBLE : un visiteur comprend-il en 5 secondes ce que vous proposez et comment entrer en contact ?"),
]

PAINS_RECENT = [
    ("BAS",      "Site moderne — l'enjeu n'est pas le visuel",
     "Le site existe et est recent. La vraie question : convertit-il ? Demander les donnees analytics si possible."),
    ("MOYEN",    "Recent != optimise pour vendre",
     "Beaucoup de sites Framer/Webflow recents sont visuellement bons mais sans hierarchie commerciale, sans social proof structure, sans funnel."),
    ("MOYEN",    "Production de contenu et video souvent absente",
     "Mad Makers ajoute la couche contenus (SEO long-tail) et video institutionnelle — c'est ce qui transforme un site vitrine en moteur d'acquisition."),
]

# Pain points par titre
PAINS_BY_TITLE = {
    r"\b(ceo|founder|fondat|directeur|directrice|dg|patron|gerant|président)\b": [
        ("HAUT", "Charge mentale du fondateur sur l'outil web",
         "Vous ne devriez pas avoir a gerer le site vous-meme. Mad Makers prend le pilotage de bout en bout, vous validez seulement aux 2 gates."),
    ],
    r"\b(daf|cfo|finance)\b": [
        ("HAUT", "ROI digital probablement non mesure",
         "Quel est le cout d'acquisition actuel via le digital ? Sans tracking moderne c'est rarement instrumente — point d'entree naturel pour parler ROI."),
    ],
    r"\b(marketing|commerciale?|cmo|growth)\b": [
        ("HAUT", "Conversion des landing pages",
         "Pages produit sans hierarchie, sans social proof, sans CTA fort = leads froids. Refonte ciblee conversion = gain mesurable AVANT/APRÈS."),
    ],
    r"\b(rh|hr|recrutement|talent)\b": [
        ("MOYEN", "Marque employeur sous-investie",
         "Une page carriere bricolee ou un PDF = sous-attractivite talent. Le site est aussi un canal de recrutement passif."),
    ],
}

# ── Questions decouverte (Belfort intelligence gathering, micro-commitments)
QUESTIONS = [
    {
        "theme": "1. Activite & cible",
        "items": [
            "Quel est votre coeur de metier en 1 phrase ?",
            "Vous vivez principalement de B2B ou de B2C ? Quelle proportion ?",
            "Qui est votre client type ideal aujourd'hui (taille, secteur, geo) ?",
            "Comment vous differenciez-vous de vos 2-3 concurrents principaux ?",
            "Quels concurrents admirez-vous le plus (meme hors secteur) ?",
        ],
    },
    {
        "theme": "2. Acquisition actuelle (CRUCIAL pour ROI)",
        "items": [
            "D'ou viennent vos clients aujourd'hui ? (bouche-a-oreille, salon, Google, LinkedIn, autre)",
            "Quel canal marche le mieux en %, a votre feeling ?",
            "Combien de leads / RDV par mois en moyenne ?",
            "Combien vaut un client moyen pour vous (panier moyen × recurrence) ? <i>[chiffre crucial pour calcul ROI]</i>",
            "Combien de temps entre 1er contact et signature en moyenne ?",
            "Vous avez deja fait du Google Ads, Meta Ads, du SEO ? Resultats ?",
        ],
    },
    {
        "theme": "3. Site web actuel",
        "items": [
            "Qui a fait votre site, et quand exactement ?",
            "Vous avez la main pour modifier, ou vous passez par quelqu'un ?",
            "Sur 10, vous mettez combien a votre site aujourd'hui ? Pourquoi pas plus ?",
            "Qu'est-ce qui vous fait honte / ce que vous ne montrez pas a un client ?",
            "Vous savez combien de visiteurs il fait par mois (analytics) ?",
            "Avez-vous deja mesure le taux de conversion (visiteur → contact) ?",
        ],
    },
    {
        "theme": "4. Objectifs & visuels (preparation maquette RDV 2)",
        "items": [
            "Si vous pouviez doubler 1 metrique en 6 mois, ce serait quoi ?",
            "Quels visuels avez-vous : photos pro, logos, identite ? <b>(DEMANDER L'ENVOI POST-APPEL)</b>",
            "Vous avez une charte graphique / palette / fonts existantes ?",
            "Quelles refs / sites trouvez-vous bien faits dans votre secteur (ou ailleurs) ?",
            "Quel est votre budget de reference pour un site de qualite ?",
        ],
    },
]

# ── Demande de visuels ─────────────────────────────────────────────────────
VISUELS_CHECKLIST = [
    "Logo (PNG haute def, SVG si possible)",
    "Photos equipe / dirigeants (HD)",
    "Photos lieu / locaux / atelier (HD)",
    "Photos produits / realisations (HD)",
    "Charte graphique / palette si existante",
    "Brochure commerciale PDF (s'il y en a une)",
    "Liens vers reseaux sociaux actifs (Insta, LI, FB)",
    "Liens vers Google My Business / Tripadvisor / avis",
    "Acces analytics actuel si possible (lecture seule)",
]

# ── Objections / reponses (Belfort looping : agree → bridge → reinforce → close)
# Pattern : 1) Acknowledge sans combattre 2) Bridge / reframe 3) Reinforce 3-tens
# (produit / vous / boite) 4) Alternative-choice close (RDV 2 = obtenu)
OBJECTIONS = [
    {
        "objection": "« C'est combien ? »",
        "reponse": (
            "[AGREE] Excellente question, et je vais etre tres honnete avec vous. "
            "[BRIDGE] Entre un one-page rapide et un sur-mesure avec animations 3D, "
            "le tarif varie d'un facteur 5. Si je vous balance un chiffre maintenant je "
            "vous fais soit fuir avec un haut de fourchette, soit mentir avec un bas. "
            "Aucun des deux ne nous sert. "
            "[REINFORCE] Voici ce qu'on fait avec nos clients serieux : RDV 2, je vous "
            "presente une maquette construite SPECIFIQUEMENT pour votre boite, on chiffre "
            "AU SCOPE EXACT, vous avez le devis sous 48h. Pas de TJM ouvert, pas de "
            "scope creep, pas de surprise. La maquette c'est gratuit, vous decidez apres. "
            "[CLOSE] Vous preferez le RDV 2 mardi 14h ou jeudi 10h ?"
        ),
    },
    {
        "objection": "« On a deja un site / on est en train de le refaire »",
        "reponse": (
            "[AGREE] Excellent — et c'est exactement pour ca que je vous appelle, vous avez "
            "DEJA pris la decision qu'un site est strategique. "
            "[BRIDGE] La vraie question maintenant c'est : ce site qui existe, il fait QUOI "
            "pour vous concretement ? Combien de leads par mois, quel taux de conversion "
            "visiteur → contact ? "
            "[REINFORCE] Si vous me donnez les chiffres et qu'ils sont bons, je raccroche en "
            "moins de 30 secondes — promis. Mais 9 fois sur 10 quand je pose ces questions, "
            "on me repond 'je ne sais pas exactement'. Et c'est ca le vrai probleme, pas le "
            "visuel. Mad Makers refait le visuel ET le tracking ET la hierarchie commerciale. "
            "[CLOSE] Avant que je raccroche : vous voulez qu'on regarde votre site ensemble "
            "5 minutes, je vous dis ce que JE ferais differemment, sans engagement ?"
        ),
    },
    {
        "objection": "« Je n'ai pas le temps »",
        "reponse": (
            "[AGREE] Je vous crois totalement, et c'est exactement la phrase que mes meilleurs "
            "clients m'ont dite avant de bosser avec nous. "
            "[BRIDGE] Mais laissez-moi vous demander : vous passez combien de temps par "
            "semaine a expliquer votre activite au telephone a des prospects qui auraient pu "
            "se pre-qualifier sur un bon site ? "
            "[REINFORCE] C'est exactement pour ca qu'on existe. Mad Makers prend tout en charge. "
            "Vous nous donnez UNE HEURE au total, repartie sur 10 jours. Une heure pour un "
            "outil qui va travailler 24h/24 pendant 5 ans pour vous. "
            "[CLOSE] Le RDV 2 c'est 30 minutes en visio. Mardi 14h ou jeudi 10h, qu'est-ce "
            "qui vous arrange le plus ?"
        ),
    },
    {
        "objection": "« On n'a pas de budget pour ca cette annee »",
        "reponse": (
            "[AGREE] Je comprends totalement, le budget c'est toujours tendu — surtout quand "
            "on n'a pas chiffre le ROI. "
            "[BRIDGE] Mais laissez-moi vous demander quelque chose : aujourd'hui, sans site "
            "qui vend correctement, combien de prospects par mois decouvrent un concurrent "
            "au lieu de vous decouvrir vous ? Disons meme UN SEUL par mois. Quel est votre "
            "panier moyen client ? Multipliez par 12. Vous arrivez sur quel chiffre ? "
            "[REINFORCE] Ce n'est pas une depense que je vous propose, c'est un investissement "
            "dont le payback se mesure en MOIS, pas en annees. Et si au RDV 2 vous trouvez le "
            "payback trop long, vous me dites non sans probleme — c'est noir sur blanc. "
            "Mais ne PAS faire le RDV 2, c'est continuer a perdre cet argent invisible. "
            "[CLOSE] Vous preferez voir la maquette mardi ou jeudi ?"
        ),
    },
    {
        "objection": "« On va voir avec Wix / Webflow / un freelance »",
        "reponse": (
            "[AGREE] Reponse honnete : si votre besoin c'est juste une vitrine simple sans "
            "enjeu commercial, prenez Wix ou un freelance. Vraiment. Je ne vais pas vous "
            "vendre une Ferrari pour aller chercher le pain. "
            "[BRIDGE] MAIS — et c'est pour ca que je vous appelle, pas par hasard — quand je "
            "regarde votre boite et votre poste, j'ai du mal a croire que votre site est juste "
            "une 'vitrine simple'. C'est un OUTIL COMMERCIAL. "
            "[REINFORCE] Et la, Wix vous limite : pas de SEO serieux, pas de tracking conversion "
            "fin, pas de design unique, pas de strategie. Vous payez 30€/mois pour avoir "
            "exactement le meme site que 200 000 autres entreprises francaises. Mad Makers a "
            "fait Riot Games sur leur dernier MMO, La Papiche a Saint-Avit, le cabinet du "
            "Dr Marchand a Nantes — 3 univers totalement differents, 3 designs uniques. "
            "[CLOSE] La vraie question : votre site doit faire QUOI pour vous dans 12 mois ? "
            "On en parle 15 minutes au RDV 2, vous decidez apres. Mardi ou jeudi ?"
        ),
    },
    {
        "objection": "« On va voir avec d'autres prestataires »",
        "reponse": (
            "[AGREE] Parfait, c'est exactement ce qu'il faut faire — comparer. "
            "[BRIDGE] Je vais vous donner la grille de comparaison que les agences classiques "
            "n'aiment pas qu'on diffuse. Demandez a chacun TROIS choses tres precises : "
            "[REINFORCE] UN — combien de jours de la signature a la mise en ligne ? Nous c'est "
            "10. DEUX — combien de series de corrections incluses dans le devis avant que ca "
            "devienne du payant ? Nous c'est 2. TROIS — qui valide quoi par ecrit, et a quel "
            "moment ? Nous c'est 2 gates de validation signees. Faites ca avec 3 agences, "
            "vous allez voir, 90% sont vagues sur les 3. Et la vous saurez quoi choisir. "
            "[CLOSE] On fait quand meme le RDV 2 pour que vous ayez UNE reference solide dans "
            "votre comparaison — mardi 14h ou jeudi 10h ?"
        ),
    },
    {
        "objection": "« Comment je sais que ca va me rapporter de l'argent ? »",
        "reponse": (
            "[AGREE] Question legitime, c'est exactement la question a se poser. "
            "[BRIDGE] Voici la verite operationnelle : un site rapporte de l'argent a 3 "
            "conditions, pas plus, pas moins. UN — la hierarchie de la page est concue pour "
            "la conversion (CTA clair, social proof, friction reduite). DEUX — il y a du "
            "trafic qualifie dessus (SEO ou ads ou referencement). TROIS — il y a un tracking "
            "pour mesurer et iterer. "
            "[REINFORCE] Si on coche les 3, le payback est mesurable et demontrable AVANT/APRES. "
            "Si on coche que la 1, c'est un gain image et trust mais pas en cash, et je vous "
            "le dirai franchement. C'est exactement pour ca qu'au RDV 2 je ne vous presente "
            "PAS qu'une maquette — je vous presente une maquette + un plan d'acquisition + "
            "un plan de tracking. "
            "[CLOSE] Vous voulez voir ce package mardi 14h ou jeudi 10h ?"
        ),
    },
    {
        "objection": "« Envoyez-moi un email avec les infos »",
        "reponse": (
            "[AGREE] Bien sur, je peux le faire. "
            "[BRIDGE] Mais soyons honnetes 30 secondes : un email generique va finir a la "
            "corbeille a 9h45 demain matin. "
            "[REINFORCE] Ce qui rend Mad Makers utile pour vous, c'est qu'on construit une "
            "maquette SPECIFIQUEMENT pour votre boite — donc pour faire un email pertinent, "
            "j'ai besoin de 15 minutes pour comprendre votre activite. Apres ce 2eme echange, "
            "je vous envoie un email AVEC la maquette dedans. Comparez les deux options : un "
            "email standard ou un email avec une maquette de votre futur site dedans. "
            "[CLOSE] Mardi 14h ou jeudi 10h, quel creneau marche le mieux pour 30 minutes ?"
        ),
    },
]

# ── Arguments financiers (Belfort : pain de l'inaction > plaisir de l'action)
ARGUMENTS_FINANCIERS = {
    "actifs_mesurables": [
        ("Gain de conversion mesurable AVANT/APRES",
         "Une refonte avec hierarchie commerciale + mobile-first augmente le ratio "
         "visiteur→contact. À mesurer avec analytics avant/apres — c'est ca, du "
         "ROI demontrable et non du marketing creux."),
        ("Capter la demande organique (SEO)",
         "Un article SEO bien positionne continue a ramener des leads pendant des "
         "annees, sans cout marginal. Compound interest applique au trafic web."),
        ("Reduction du CAC publicitaire",
         "Si la boite paie du Google/Meta Ads, une landing mieux construite reduit "
         "le cout par lead immediat. Economie directe et chiffrable des le 1er mois."),
        ("Acceleration du cycle de vente",
         "Un site qui pre-qualifie (FAQ, pricing, cas client visibles) raccourcit "
         "le temps entre 1er contact et signature — donc cash-flow plus rapide."),
    ],
    "passifs_long_terme": [
        ("Vitrine 24/7",
         "Le site travaille la nuit, le week-end, pendant les vacances. Vendeur "
         "silencieux qui ne dort jamais et ne demande pas de salaire."),
        ("Credibilite instantanee (the pre-call)",
         "Avant un appel ou une signature, la majorite des prospects vont sur "
         "Google verifier. Le site EST le pre-call commercial que vous ne donnez "
         "pas vous-meme."),
        ("Marque employeur",
         "Recrutement passif : les talents qualifies verifient le site avant de "
         "postuler. Site date = candidat rebute, donc embauche plus longue, donc "
         "cout de recrutement plus eleve."),
        ("Levier presse / partenariats",
         "Les medias et partenaires demandent le site avant tout contact. Sans "
         "site moderne, vous etes filtre en amont sans que vous le sachiez."),
        ("Independance plateforme",
         "Votre nom de domaine est inalienable. LinkedIn, Insta, GMB peuvent "
         "tomber, changer leurs regles, vous suspendre. Pas votre site."),
    ],
    # Promesse Mad Makers (specifique, jamais inventee — chiffres officiels portfolio)
    "promesse_madmakers": [
        ("Livraison en 10 jours",
         "vs 2-3 mois en agence classique. Moins de risque de perdre du momentum "
         "commercial, et le site travaille pour vous 2 mois plus tot."),
        ("2 gates de validation ecrites",
         "Maquettes signees AVANT dev, livraison signee AVANT mise en ligne. "
         "Aucune surprise, aucun 'ah on n'avait pas compris ca comme ca'."),
        ("Devis fixe au scope",
         "Pas de TJM ouvert ni de scope creep. Vous savez exactement ce que vous "
         "payez avant de signer. Acompte 40% / solde 60%."),
        ("Design unique par marche",
         "Pas de templates recycles. Vous payez pour de la differenciation reelle, "
         "pas pour le meme Wix que 200 000 autres boites francaises."),
        ("Outils de suivi installes/configures",
         "GA4, Search Console, monitoring perf — pas de 'site sans analytics' chez "
         "nous. Vous mesurez ce qui convertit des le J+1 de mise en ligne."),
        ("Consultation initiale 30 min gratuite",
         "Calendly direct : calendly.com/directedbymaick/30min. Vous decidez "
         "apres la maquette du RDV 2."),
    ],
}

# ── Authority drops Belfort (a placer en intro et au milieu de l'echange)
AUTHORITY_DROPS = {
    "sans_site":          "On a fait La Papiche (bistrot Saint-Avit, TPE locale) et le cabinet du Dr Sophie Marchand a Nantes — exactement votre profil de boite ou on construit a partir de zero.",
    "avec_site_veillot":  "On a fait La Papiche (bistrot Saint-Avit) qui avait zero site, le cabinet du Dr Marchand a Nantes en sante liberale, et Riot Games sur leur dernier MMO en B2C premium. 3 univers totalement differents, 3 designs uniques.",
    "avec_site_recent":   "On a fait Riot Games sur leur dernier MMO — globe 3D temps reel WebGL, narration cinematique. C'est exactement ce niveau d'exigence qu'on apporte aux boites qui considerent leur site comme un actif strategique et pas une vitrine.",
}

# ── Future pacing Belfort (visualisation a deployer mid-call)
FUTURE_PACING = (
    "Imaginez 3 minutes : un prospect qualifie cherche votre activite sur Google. "
    "Il tombe sur VOTRE site. En 5 secondes il comprend ce que vous faites, il voit "
    "3 cas clients similaires au sien, il voit votre methodologie en 4 etapes, et "
    "il prend RDV via un calendrier integre. Vous, vous etiez en reunion. Le RDV "
    "est dans votre calendrier au reveil. Et ce prospect, sans Mad Makers, serait "
    "alle chez votre concurrent qui a un site qui convertit. Voila ce qu'on "
    "construit — pas une vitrine, un actif commercial."
)

# ── Closing patterns Belfort
CLOSE_PATTERNS = [
    ("Alternative-choice (default close)",
     "« Pour le RDV 2 — vous preferez mardi 14h ou jeudi 10h ? »"),
    ("Assumed close (apres signaux d'achat)",
     "« Parfait, je vous envoie l'invit Calendly dans la foulee — vous voulez "
     "que je copie quelqu'un de votre cote en cc ? »"),
    ("Summary close (recap rapide avant RDV)",
     "« Donc pour resumer : 30 minutes mardi, je vous montre une maquette de "
     "votre futur site, devis sous 48h apres, vous decidez. C'est bien ca ? »"),
    ("Direct close apres derniere objection levee",
     "« Bon — il reste UNE seule chose entre nous et le RDV 2 : vous voulez "
     "qu'on le fasse mardi ou jeudi ? »"),
    ("Soft close (si hesitation legitime)",
     "« Si ce n'est vraiment pas le bon moment, dites-le moi sans probleme, "
     "je vous laisse tranquille. Mais si c'est juste un doute, on peut le lever "
     "en 15 minutes au RDV 2. Qu'est-ce qui se passe vraiment ? »"),
    ("Hard close (apres 'envoyez un email')",
     "« Ok, donc je vous envoie l'invit pour mardi 14h, et je mets en piece "
     "jointe les 3 cas qui ressemblent le plus a votre boite. Ca marche ? »"),
]


# ──────────────────────────────────────────────────────────────────────────
def slugify(text):
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return text or "prospect"


def find_csv(explicit=None):
    if explicit:
        p = Path(explicit)
        if p.exists():
            return p
        sys.exit(f"ERREUR: {explicit} introuvable")
    candidates = sorted(DATA_DIR.glob("prospects_triage_final_*.csv"), reverse=True)
    if not candidates:
        candidates = sorted(DATA_DIR.glob("prospects_triage_strict_*_recheck.csv"), reverse=True)
    if not candidates:
        sys.exit("ERREUR: aucun CSV de triage trouve dans data/. Lance le pipeline d'abord.")
    return candidates[0]


def load_prospects(csv_path):
    with open(csv_path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def find_prospect(rows, name=None, index=None):
    if index is not None:
        if not (1 <= index <= len(rows)):
            sys.exit(f"ERREUR: index {index} hors bornes (1-{len(rows)})")
        return rows[index - 1]
    if not name:
        sys.exit("ERREUR: --name ou --index requis")
    needle = name.lower().strip()
    # Match exact d'abord
    for r in rows:
        if r.get("nom_complet", "").lower().strip() == needle:
            return r
    # Match contains
    matches = [r for r in rows if needle in r.get("nom_complet", "").lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        print(f"AMBIGU : {len(matches)} matches pour '{name}' :")
        for m in matches[:10]:
            print(f"   - {m.get('nom_complet','')} | {m.get('entreprise','')}")
        sys.exit("Affine ton --name")
    sys.exit(f"ERREUR: aucun prospect ne matche '{name}'")


def _tls_version(host, timeout=4):
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as s:
                return s.version()
    except Exception:
        return None


def audit_site(url):
    """Returns dict with audit info."""
    out = {
        "ok": False,
        "url": url,
        "final_url": "",
        "status": None,
        "https": False,
        "tls_version": None,
        "headers": {},
        "title": "",
        "description": "",
        "h1": "",
        "technos": [],
        "copyright_year": None,
        "html_size_kb": None,
        "image_count": 0,
        "modern_image_count": 0,
        "veillot_signals": [],
        "security_grade": "?",
        "security_findings": [],
        "pagespeed_url": "",
        "error": None,
    }
    if not url:
        return out

    try:
        r = requests.get(url, timeout=8, allow_redirects=True, headers=UA)
    except requests.RequestException as e:
        out["error"] = f"{type(e).__name__}: {e}"
        return out

    out["ok"] = True
    out["status"] = r.status_code
    out["final_url"] = r.url
    out["https"] = urlparse(r.url).scheme == "https"
    out["headers"] = {k.lower(): v for k, v in r.headers.items()}

    parsed = urlparse(r.url)
    if out["https"]:
        out["tls_version"] = _tls_version(parsed.hostname)

    html = r.text or ""
    out["html_size_kb"] = round(len(html) / 1024, 1)

    # Title
    m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I | re.S)
    if m:
        out["title"] = htmllib.unescape(m.group(1).strip())

    # Meta description
    m = re.search(r'<meta\s+name=["\']?description["\']?\s+content=["\']([^"\']+)', html, re.I)
    if m:
        out["description"] = htmllib.unescape(m.group(1).strip())

    # H1
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.I | re.S)
    if m:
        clean = re.sub(r"<[^>]+>", " ", m.group(1))
        out["h1"] = re.sub(r"\s+", " ", htmllib.unescape(clean)).strip()

    # Technos
    detected = []
    for pat, label in TECH_PATTERNS:
        if pat.search(html):
            detected.append(label)
    out["technos"] = list(dict.fromkeys(detected))

    # Veillot signals
    v_signs = []
    if not out["https"]:
        v_signs.append("no_https")
    for tag, _label in VEILLOT_TAGS_HUMAN.items():
        if tag == "no_https":
            continue
        from_pattern = {
            "table_layout":   r"<table[^>]*\s(?:width|cellpadding|cellspacing|border)=",
            "font_tag":       r"<font\s+(?:color|face|size)=",
            "center_tag":     r"<center>",
            "frameset":       r"<frameset|<frame\s",
            "jquery_v1":      r"jquery[/-]1\.\d",
            "iso_charset":    r'charset=iso',
        }.get(tag)
        if from_pattern and re.search(from_pattern, html, re.I):
            v_signs.append(tag)
    out["veillot_signals"] = v_signs

    # Copyright
    m = re.search(r"(?:copyright|©|&copy;)\s*(?:[a-z\s\.&]+\s)?(\d{4})(?:\s*[-–—]\s*(\d{4}))?", html, re.I)
    if m:
        years = [int(y) for y in m.groups() if y]
        out["copyright_year"] = max(years) if years else None

    # Images
    imgs = re.findall(r"<img[^>]+>", html, re.I)
    out["image_count"] = len(imgs)
    out["modern_image_count"] = sum(1 for tag in imgs if re.search(r"\.(webp|avif)", tag, re.I))

    # Security findings (headers)
    h = out["headers"]
    findings = []
    sec_score = 0
    sec_max = 6
    if out["https"]:
        sec_score += 1
    else:
        findings.append("BLOQUANT : pas de HTTPS")
    if "strict-transport-security" in h:
        sec_score += 1
    else:
        findings.append("Manque header HSTS (force HTTPS)")
    if "content-security-policy" in h:
        sec_score += 1
    else:
        findings.append("Manque header CSP (anti-XSS)")
    if "x-frame-options" in h or "frame-ancestors" in h.get("content-security-policy", ""):
        sec_score += 1
    else:
        findings.append("Manque header X-Frame-Options (anti-clickjacking)")
    if "x-content-type-options" in h:
        sec_score += 1
    else:
        findings.append("Manque header X-Content-Type-Options")
    if "referrer-policy" in h:
        sec_score += 1
    else:
        findings.append("Manque header Referrer-Policy")
    out["security_findings"] = findings

    grades = ["F", "F", "E", "D", "C", "B", "A"]
    out["security_grade"] = grades[min(sec_score, 6)]

    # PageSpeed link (manuel, pas d'API key)
    out["pagespeed_url"] = f"https://pagespeed.web.dev/report?url={r.url}"

    return out


def detect_pains(prospect, audit):
    """Returns list of (severity, label, evidence) triples."""
    cat = prospect.get("categorie", "")
    if cat == "sans_site":
        pains = list(PAINS_SANS_SITE)
    elif cat == "avec_site_veillot":
        pains = list(PAINS_VEILLOT)
    elif cat == "avec_site_recent":
        pains = list(PAINS_RECENT)
    else:
        pains = []

    title = prospect.get("titre", "").lower()
    for pat, ps in PAINS_BY_TITLE.items():
        if re.search(pat, title, re.I):
            pains.extend(ps)

    # Pains supplementaires depuis l'audit
    if audit.get("ok"):
        if not audit.get("https"):
            pains.append(("CRITIQUE", "Pas de HTTPS sur le site",
                          "Chrome marque le site 'non securise', perte de trust + SEO."))
        if audit.get("security_grade") in ("E", "F"):
            pains.append(("HAUT", f"Note securite {audit['security_grade']} (headers manquants)",
                          "; ".join(audit.get("security_findings", [])[:3])))
        if not audit.get("description"):
            pains.append(("MOYEN", "Pas de meta description",
                          "Affichage dans les SERP non controle, taux de clic faible."))
        if audit.get("image_count", 0) > 0 and audit.get("modern_image_count", 0) == 0:
            pains.append(("MOYEN", "Aucune image en WebP/AVIF",
                          f"{audit['image_count']} images en JPG/PNG = poids inutile = lenteur."))
        cy = datetime.now().year
        if audit.get("copyright_year") and audit["copyright_year"] < cy - 2:
            pains.append(("HAUT", f"Copyright {audit['copyright_year']} (site fige)",
                          "Aucun update recent, signal d'abandon visible par les visiteurs."))

    return pains


def build_intro(prospect, audit):
    """Returns dict {scenario, hook} — Belfort 4-second crack:
    Position + Energy + Authority + Reason + Alternative-choice close."""
    cat = prospect.get("categorie", "")
    prenom = prospect.get("prenom", "").strip() or "Bonjour"
    boite = prospect.get("entreprise", "").strip() or "votre boite"
    authority = AUTHORITY_DROPS.get(cat, AUTHORITY_DROPS["avec_site_veillot"])

    if cat == "sans_site":
        hook = (
            f"« Bonjour {prenom}, Maïck — Mad Makers. Vous allez bien ? »\n"
            f"  [PAUSE — laisser repondre, ton enthousiaste]\n"
            f"« Excellent. Je vais etre tres direct avec vous : j'ai cherche "
            f"{boite} sur Google ce matin avant de vous appeler. J'ai trouve votre "
            f"LinkedIn, j'ai trouve deux annuaires d'entreprise, je n'ai PAS trouve "
            f"de site web. C'est volontaire ou c'est un projet en attente ? »\n"
            f"  [ECOUTER — note la reponse, c'est crucial pour la suite]\n"
            f"« OK, je vous comprends. Ecoutez : {authority} Je ne vais pas vous "
            f"prendre 30 minutes maintenant. 90 secondes pour vous dire pourquoi "
            f"je vous appelle PRECISEMENT, et si ca vous parle on cale 15 minutes "
            f"plus tard cette semaine pour creuser. Ca vous va ? »\n"
            f"  [Premier 'oui' Belfort — lance la suite]"
        )
        scenario = "SANS SITE — angle invisibilite Google + creation a partir de zero"
    elif cat == "avec_site_veillot":
        site = audit.get("final_url", "") or prospect.get("site_url", "")
        sigs = audit.get("veillot_signals", [])
        if sigs:
            sig_human = VEILLOT_TAGS_HUMAN.get(sigs[0], sigs[0])
            sig_phrase = f"j'ai vu {sig_human.lower()}"
        else:
            sig_phrase = "le design n'est plus aux standards 2026"
        sec_grade = audit.get("security_grade", "?")
        sec_phrase = f", note de securite headers : {sec_grade}" if sec_grade in ("D","E","F") else ""
        hook = (
            f"« Bonjour {prenom}, Maïck — Mad Makers. Vous allez bien ? »\n"
            f"  [PAUSE — ton enthousiaste, sourire dans la voix]\n"
            f"« Excellent. Je vais etre direct avec vous : j'ai regarde {site} "
            f"ce matin avant de vous appeler — {sig_phrase}{sec_phrase}. "
            f"Concretement, ca veut dire qu'aujourd'hui votre site fait perdre de "
            f"la confiance aux prospects qui le voient avant un appel commercial — "
            f"et ce, sans que vous le sachiez. »\n"
            f"« {authority} »\n"
            f"« Je ne vous appelle PAS pour vous vendre quoi que ce soit aujourd'hui. "
            f"Je veux juste comprendre 2-3 choses sur votre activite, et si on est "
            f"d'accord sur le diagnostic, on cale un 2eme RDV ou on vous montre une "
            f"maquette refaite SPECIFIQUEMENT pour {boite}. C'est gratuit, vous "
            f"decidez apres. Ca vous va ? »\n"
            f"  [Premier 'oui' Belfort — enchaine]"
        )
        scenario = "VEILLOT — audit visuel + securite + maquette gratuite RDV 2"
    else:  # recent
        hook = (
            f"« Bonjour {prenom}, Maïck — Mad Makers. Vous allez bien ? »\n"
            f"  [PAUSE — ton sharp, energique]\n"
            f"« Parfait. Je vais aller droit au but : votre site est recent, "
            f"il est correct visuellement — je ne vous appelle PAS pour le refaire. »\n"
            f"« {authority} »\n"
            f"« Je vous appelle parce qu'un site recent != un site qui VEND. "
            f"Et c'est exactement notre angle d'expertise : prendre un site qui a "
            f"deja un visuel correct et le transformer en outil commercial mesurable. "
            f"90 secondes pour vous dire de quoi il s'agit, et vous me dites si on "
            f"en parle 15 minutes plus tard cette semaine. Ca vous va ? »"
        )
        scenario = "RECENT — angle conversion / SEO / video / tracking"

    return {"scenario": scenario, "hook": hook}


# ──── HTML rendering ──────────────────────────────────────────────────────
def render_html(prospect, audit, pains, intro, initial_state=None):
    import json as _json
    cat = prospect.get("categorie", "")
    cat_label = {
        "avec_site_veillot": ("VEILLOT", "#92400E", "#FEF3C7"),
        "sans_site":          ("SANS SITE", "#991B1B", "#FEE2E2"),
        "avec_site_recent":   ("RECENT", "#3730A3", "#E0E7FF"),
    }.get(cat, ("?", "#374151", "#F3F4F6"))

    full = htmllib.escape(prospect.get("nom_complet", ""))
    titre = htmllib.escape(prospect.get("titre", ""))
    boite = htmllib.escape(prospect.get("entreprise", ""))
    ville = htmllib.escape(prospect.get("ville", ""))
    email = htmllib.escape(prospect.get("email", ""))
    linkedin = htmllib.escape(prospect.get("linkedin_url", ""))
    site = htmllib.escape(prospect.get("site_url", ""))

    # JSON-encoded fields for safe injection in JS (handles quotes, accents)
    def _js(s):
        return _json.dumps(s if s is not None else "", ensure_ascii=False)

    prospect_json_name     = _js(prospect.get("nom_complet", ""))
    prospect_json_boite    = _js(prospect.get("entreprise", ""))
    prospect_json_titre    = _js(prospect.get("titre", ""))
    prospect_json_ville    = _js(prospect.get("ville", ""))
    prospect_json_email    = _js(prospect.get("email", ""))
    prospect_json_linkedin = _js(prospect.get("linkedin_url", ""))
    prospect_json_site     = _js(prospect.get("site_url", ""))
    prospect_json_cat      = _js(cat)
    slug = slugify(prospect.get("nom_complet", "prospect"))
    initial_state_json = _json.dumps(initial_state or {}, ensure_ascii=False)

    # ── Audit summary HTML ────────────────────────────────────────────────
    if audit.get("ok"):
        sec_grade = audit["security_grade"]
        grade_color = {"A": "#22C55E", "B": "#84CC16", "C": "#EAB308", "D": "#F97316", "E": "#EF4444", "F": "#B91C1C"}.get(sec_grade, "#6B7280")
        technos_html = ", ".join(htmllib.escape(t) for t in audit["technos"]) or "<i>aucune detectee</i>"
        veillot_html = ", ".join(htmllib.escape(VEILLOT_TAGS_HUMAN.get(s, s)) for s in audit["veillot_signals"]) or "<i>aucun</i>"
        sec_findings_html = "<br>".join(htmllib.escape(f) for f in audit["security_findings"]) or "<i>aucun probleme detecte</i>"
        copyright_y = audit.get("copyright_year") or "?"
        title_html = htmllib.escape(audit.get("title", "")) or "<i>aucun</i>"
        desc_html = htmllib.escape(audit.get("description", "")) or "<i>aucune meta description</i>"
        h1_html = htmllib.escape(audit.get("h1", "")) or "<i>aucun H1</i>"

        audit_block = f"""
        <div class="audit-grid">
            <div class="audit-row"><span class="lab">URL finale</span><span class="val"><a href="{audit['final_url']}" target="_blank">{audit['final_url']}</a></span></div>
            <div class="audit-row"><span class="lab">Status</span><span class="val">{audit['status']}</span></div>
            <div class="audit-row"><span class="lab">HTTPS / TLS</span><span class="val">{'Oui' if audit['https'] else '<b style=color:#B91C1C>NON</b>'} / {audit.get('tls_version') or '?'}</span></div>
            <div class="audit-row"><span class="lab">Note securite headers</span><span class="val"><span class="grade" style="background:{grade_color}">{sec_grade}</span></span></div>
            <div class="audit-row"><span class="lab">Technos detectees</span><span class="val">{technos_html}</span></div>
            <div class="audit-row"><span class="lab">Signaux veillot</span><span class="val">{veillot_html}</span></div>
            <div class="audit-row"><span class="lab">Copyright</span><span class="val">{copyright_y}</span></div>
            <div class="audit-row"><span class="lab">Title</span><span class="val">{title_html}</span></div>
            <div class="audit-row"><span class="lab">H1</span><span class="val">{h1_html}</span></div>
            <div class="audit-row"><span class="lab">Meta description</span><span class="val">{desc_html}</span></div>
            <div class="audit-row"><span class="lab">Taille HTML</span><span class="val">{audit['html_size_kb']} KB</span></div>
            <div class="audit-row"><span class="lab">Images / modernes (webp/avif)</span><span class="val">{audit['image_count']} / {audit['modern_image_count']}</span></div>
            <div class="audit-row"><span class="lab">PageSpeed Insights</span><span class="val"><a href="{audit['pagespeed_url']}" target="_blank">Lancer le test &rarr;</a></span></div>
        </div>
        <div class="sec-findings">
            <h4>Findings securite</h4>
            <p>{sec_findings_html}</p>
        </div>
        """
    elif prospect.get("site_url"):
        audit_block = f"<p class='warn'>Le site <code>{site}</code> n'a pas pu etre fetche : {htmllib.escape(audit.get('error', '') or 'unknown')}</p>"
    else:
        audit_block = "<p class='no-site'><b>Aucun site detecte.</b> Le prospect est dans la categorie SANS SITE — angle creation a partir de zero.</p>"

    # ── Pain points HTML ──────────────────────────────────────────────────
    sev_colors = {"CRITIQUE": "#B91C1C", "HAUT": "#EA580C", "MOYEN": "#CA8A04", "BAS": "#6B7280"}
    pains_html = ""
    for sev, label, evidence in pains:
        color = sev_colors.get(sev, "#374151")
        pains_html += f"""
        <li>
            <label>
                <input type="checkbox" data-key="pain_{slugify(label)}">
                <span class="sev" style="background:{color}">{sev}</span>
                <span class="pain-label">{htmllib.escape(label)}</span>
            </label>
            <div class="pain-ev">{htmllib.escape(evidence)}</div>
        </li>
        """

    # ── Questions HTML ────────────────────────────────────────────────────
    questions_html = ""
    for theme in QUESTIONS:
        items = "".join(
            f'<li><label><input type="checkbox" data-key="q_{slugify(theme["theme"])}_{i}">'
            f'<span class="q-text">{htmllib.escape(q)}</span></label>'
            f'<textarea data-key="qn_{slugify(theme["theme"])}_{i}" placeholder="reponse..." rows="2"></textarea></li>'
            for i, q in enumerate(theme["items"])
        )
        questions_html += f'<div class="theme-block"><h3>{htmllib.escape(theme["theme"])}</h3><ul class="q-list">{items}</ul></div>'

    # ── Visuels checklist ─────────────────────────────────────────────────
    visuels_html = "".join(
        f'<li><label><input type="checkbox" data-key="vis_{i}"><span>{htmllib.escape(v)}</span></label></li>'
        for i, v in enumerate(VISUELS_CHECKLIST)
    )

    # ── Objections (Belfort looping displayed structurally) ──────────────
    obj_html = ""
    for o in OBJECTIONS:
        # Decouper la reponse selon les marqueurs [AGREE]/[BRIDGE]/[REINFORCE]/[CLOSE]
        rep = o['reponse']
        parts = re.split(r'\[(AGREE|BRIDGE|REINFORCE|CLOSE)\]\s*', rep)
        # parts = ['', 'AGREE', 'text...', 'BRIDGE', 'text...', ...]
        steps_html = ""
        if len(parts) > 1:
            for i in range(1, len(parts), 2):
                tag = parts[i]
                text = parts[i+1].strip() if i+1 < len(parts) else ""
                tag_color = {"AGREE": "#0EA5E9", "BRIDGE": "#8B5CF6",
                             "REINFORCE": "#22C55E", "CLOSE": "#DC2626"}.get(tag, "#6B7280")
                steps_html += (f'<div class="loop-step">'
                               f'<span class="loop-tag" style="background:{tag_color}">{tag}</span>'
                               f'<span class="loop-text">{htmllib.escape(text)}</span></div>')
        else:
            steps_html = f'<p>{htmllib.escape(rep)}</p>'
        obj_html += f"""
        <details>
            <summary>{htmllib.escape(o['objection'])}</summary>
            {steps_html}
        </details>
        """

    # ── Arguments financiers (post-audit) ────────────────────────────────
    actifs_html = "".join(
        f'<li><b>{htmllib.escape(t)}.</b> {htmllib.escape(d)}</li>'
        for t, d in ARGUMENTS_FINANCIERS["actifs_mesurables"]
    )
    passifs_html = "".join(
        f'<li><b>{htmllib.escape(t)}.</b> {htmllib.escape(d)}</li>'
        for t, d in ARGUMENTS_FINANCIERS["passifs_long_terme"]
    )
    promesse_html = "".join(
        f'<li><b>{htmllib.escape(t)}.</b> {htmllib.escape(d)}</li>'
        for t, d in ARGUMENTS_FINANCIERS["promesse_madmakers"]
    )

    # ── Closing patterns ─────────────────────────────────────────────────
    closes_html = "".join(
        f'<li><b>{htmllib.escape(t)}</b><br><span class="close-line">{htmllib.escape(c)}</span></li>'
        for t, c in CLOSE_PATTERNS
    )

    # ── Final HTML ────────────────────────────────────────────────────────
    storage_key = slugify(full + "_" + TODAY)
    cat_text, cat_color, cat_bg = cat_label

    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Cold call brief — {full}</title>
<style>
* {{ box-sizing: border-box; }}
html, body {{ margin:0; padding:0; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, system-ui, sans-serif;
    background: #F5F5F4;
    color: #111827;
    line-height: 1.5;
    font-size: 14px;
    padding: 24px 32px 64px;
    max-width: 1100px;
    margin: 0 auto;
}}
h1, h2, h3, h4 {{ margin: 0 0 8px; color: #111827; }}
h1 {{ font-size: 26px; letter-spacing: -0.02em; }}
h2 {{ font-size: 18px; margin-top: 28px; padding-top: 16px; border-top: 2px solid #111827; }}
h3 {{ font-size: 14px; text-transform: uppercase; letter-spacing: 0.06em; color: #4B5563; margin-top: 16px; }}
h4 {{ font-size: 13px; color: #6B7280; }}
a {{ color: #1D4ED8; }}
.card {{ background: #fff; border: 1px solid #E5E7EB; border-radius: 8px; padding: 16px 20px; margin-bottom: 14px; }}

/* Header card */
.header-card {{ display: flex; flex-direction: column; gap: 6px; }}
.cat-badge {{ display:inline-block; padding: 4px 10px; border-radius: 4px;
              font-size: 11px; font-weight: 700; letter-spacing: 0.06em;
              background: {cat_bg}; color: {cat_color}; }}
.id-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px 24px; margin-top: 12px; }}
.id-grid div {{ font-size: 13px; }}
.id-grid b {{ color: #6B7280; font-weight: 500; margin-right: 8px; }}

/* Hook box */
.hook-box {{ background: #FEF3C7; border-left: 4px solid #D97706; padding: 12px 16px;
             font-style: italic; margin-bottom: 8px; white-space: pre-wrap; }}
.scenario {{ font-size: 12px; color: #6B7280; margin-bottom: 4px; }}

/* Audit */
.audit-grid {{ display: grid; grid-template-columns: 1fr; gap: 4px; }}
.audit-row {{ display: grid; grid-template-columns: 200px 1fr; gap: 12px;
              padding: 4px 0; border-bottom: 1px dashed #E5E7EB; font-size: 13px; }}
.audit-row .lab {{ color: #6B7280; }}
.audit-row .val {{ color: #111827; word-break: break-word; }}
.grade {{ display:inline-block; min-width: 24px; text-align:center; padding: 1px 6px;
          color: white; font-weight: 700; border-radius: 3px; font-size: 12px; }}
.sec-findings {{ margin-top: 12px; padding: 8px 12px; background: #F3F4F6; border-radius: 4px;
                 font-size: 12px; line-height: 1.6; }}
.warn {{ color: #B91C1C; font-style: italic; }}
.no-site {{ background: #FEE2E2; padding: 8px 12px; border-radius: 4px; }}

/* Pains */
ul.pains {{ list-style: none; padding: 0; margin: 0; }}
ul.pains li {{ padding: 8px 0; border-bottom: 1px dashed #E5E7EB; }}
ul.pains label {{ display: flex; align-items: center; gap: 8px; cursor: pointer; }}
.sev {{ display:inline-block; padding: 1px 6px; color: white; font-size: 10px;
        font-weight: 700; border-radius: 2px; min-width: 60px; text-align: center; }}
.pain-label {{ font-weight: 600; }}
.pain-ev {{ margin-left: 92px; font-size: 12px; color: #6B7280; margin-top: 2px; }}

/* Questions */
.theme-block {{ margin-bottom: 16px; }}
ul.q-list {{ list-style: none; padding: 0; margin: 0; }}
ul.q-list li {{ padding: 6px 0; border-bottom: 1px dashed #E5E7EB; }}
ul.q-list label {{ display: flex; align-items: flex-start; gap: 8px; cursor: pointer; }}
.q-text {{ flex: 1; }}
ul.q-list textarea {{ width: 100%; margin-top: 4px; padding: 6px 8px; border: 1px solid #D1D5DB;
                      border-radius: 4px; font-family: inherit; font-size: 13px; resize: vertical; }}

/* Visuels */
ul.visuels {{ list-style: none; padding: 0; margin: 0; columns: 2; column-gap: 24px; }}
ul.visuels li {{ break-inside: avoid; padding: 4px 0; }}
ul.visuels label {{ display: flex; align-items: center; gap: 8px; cursor: pointer; }}

/* Objections (Belfort loop) */
details {{ margin-bottom: 8px; padding: 8px 14px; background: #F9FAFB; border-radius: 4px;
           border-left: 3px solid #DC2626; }}
details summary {{ cursor: pointer; font-weight: 700; color: #991B1B; }}
details p {{ margin: 8px 0 0; color: #374151; }}
.loop-step {{ display: flex; gap: 10px; align-items: flex-start; margin: 10px 0; padding-left: 4px;
              border-left: 2px solid #E5E7EB; padding-left: 12px; }}
.loop-tag {{ display: inline-block; padding: 2px 8px; color: white; font-size: 10px;
             font-weight: 700; border-radius: 3px; min-width: 70px; text-align: center;
             flex-shrink: 0; margin-top: 2px; }}
.loop-text {{ flex: 1; color: #1F2937; line-height: 1.55; }}

/* Arguments financiers */
ul.arg-list {{ list-style: none; padding: 0; margin: 0 0 8px; }}
ul.arg-list li {{ padding: 6px 0; border-bottom: 1px dashed #E5E7EB;
                  font-size: 13px; line-height: 1.5; }}
ul.arg-list b {{ color: #111827; }}
.roi-box {{ background: #F0FDF4; border: 1px solid #86EFAC; border-radius: 6px;
            padding: 16px 18px; margin: 12px 0; }}
.roi-box p {{ margin: 6px 0; font-size: 13px; }}

/* ROI Calculator interactive */
.roi-form {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin: 14px 0; }}
.roi-form label {{ display: flex; flex-direction: column; font-size: 12px;
                   color: #166534; gap: 4px; font-weight: 600; }}
.roi-form input {{ padding: 10px 12px; border: 2px solid #86EFAC; border-radius: 6px;
                   font-family: inherit; font-size: 18px; font-weight: 700; color: #052e16;
                   background: white; }}
.roi-form input:focus {{ outline: none; border-color: #22C55E; box-shadow: 0 0 0 3px rgba(34,197,94,0.15); }}
.roi-result {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px;
               padding: 18px 20px; background: #052e16; border-radius: 8px; margin-top: 8px; }}
.roi-metric {{ color: white; }}
.roi-label {{ display: block; font-size: 11px; opacity: 0.7; text-transform: uppercase;
              letter-spacing: 0.08em; font-weight: 600; }}
.roi-value {{ display: block; font-size: 32px; font-weight: 800; margin-top: 4px;
              letter-spacing: -0.02em; }}
.roi-verdict {{ grid-column: span 2; padding: 12px 14px; border-radius: 6px;
                font-weight: 700; text-align: center; font-size: 14px; line-height: 1.4; }}
.roi-verdict.idle {{ background: #1f2937; color: #9CA3AF; }}
.roi-verdict.green {{ background: #16a34a; color: white; }}
.roi-verdict.amber {{ background: #f59e0b; color: white; }}
.roi-verdict.red {{ background: #dc2626; color: white; }}

/* Closing patterns */
ul.close-list {{ list-style: none; padding: 0; margin: 0; }}
ul.close-list li {{ padding: 8px 0; border-bottom: 1px dashed #E5E7EB; font-size: 13px; }}
ul.close-list b {{ color: #DC2626; font-size: 12px; text-transform: uppercase;
                   letter-spacing: 0.04em; }}
.close-line {{ display: block; margin-top: 4px; padding: 6px 10px; background: #FEF2F2;
               border-left: 3px solid #DC2626; border-radius: 3px; font-style: italic;
               color: #1F2937; }}

/* Notes */
.notes-area {{ width: 100%; min-height: 120px; padding: 10px; border: 1px solid #D1D5DB;
               border-radius: 4px; font-family: inherit; font-size: 13px; resize: vertical; }}

/* Outcome */
.outcome-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }}
.outcome-grid label {{ display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: #6B7280; }}
.outcome-grid input, .outcome-grid select {{ padding: 6px 8px; border: 1px solid #D1D5DB; border-radius: 4px;
                                              font-family: inherit; font-size: 14px; }}

/* Toolbar */
.toolbar {{ position: sticky; top: 0; background: #111827; color: white; padding: 10px 16px;
            margin: -24px -32px 0; border-radius: 0 0 8px 8px; display: flex;
            justify-content: space-between; align-items: center; z-index: 11; }}
.toolbar .brand {{ font-weight: 700; letter-spacing: -0.02em; }}
.toolbar button {{ background: white; color: #111827; border: 0; padding: 6px 14px;
                   border-radius: 4px; font-weight: 600; cursor: pointer; font-size: 13px; }}
.toolbar .saved {{ font-size: 11px; opacity: 0.6; margin-left: 12px; }}

/* Phase navigation (sticky) */
.phase-nav {{ position: sticky; top: 50px; z-index: 9; display: flex; gap: 4px;
              padding: 6px; background: white; border: 1px solid #E5E7EB; border-radius: 8px;
              margin: 12px -8px 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.04); }}
.phase-link {{ flex: 1; padding: 10px 12px; text-align: center; font-size: 13px;
                color: #6B7280; text-decoration: none; border-radius: 5px; font-weight: 600;
                transition: all 0.15s; line-height: 1.3; }}
.phase-link:hover {{ background: #F3F4F6; color: #111827; }}
.phase-link.active {{ background: #111827; color: white; }}
.phase-link small {{ display: block; font-weight: 500; opacity: 0.7; font-size: 10px; margin-top: 2px; }}
.phase-link.active small {{ opacity: 0.9; }}

/* Phase banners */
.phase-banner {{ margin: 32px -8px 16px; padding: 14px 18px;
                 border-radius: 6px; color: white; }}
.phase-banner h2 {{ border: 0; padding: 0; margin: 0 0 4px; color: white; font-size: 20px;
                    text-transform: uppercase; letter-spacing: 0.04em; }}
.phase-banner p {{ margin: 0; font-size: 13px; opacity: 0.85; }}
.phase-A {{ background: #4338CA; }}
.phase-B {{ background: #DC2626; }}
.phase-C {{ background: #166534; }}
.phase-D {{ background: #7C2D12; }}

/* Section sub-headers (under phase banner) */
h2.sec {{ font-size: 17px; margin-top: 20px; padding-top: 12px;
         border-top: 1px solid #E5E7EB; }}
h2.sec .num {{ display: inline-block; min-width: 28px; text-align: center;
              background: #111827; color: white; padding: 2px 6px; border-radius: 4px;
              font-size: 13px; margin-right: 8px; vertical-align: middle; }}

/* Save block */
.save-block {{ margin: 32px -8px 16px; padding: 24px; border-radius: 10px;
               background: linear-gradient(135deg, #064e3b 0%, #166534 100%); color: white;
               text-align: center; box-shadow: 0 8px 24px rgba(22,101,52,0.25); }}
.save-block h2 {{ color: white; border: 0; padding: 0; margin: 0 0 8px; font-size: 20px; }}
.save-block p {{ margin: 0 0 16px; opacity: 0.9; font-size: 14px; }}
.big-save {{ background: white; color: #166534; border: 0; padding: 14px 28px;
             border-radius: 8px; font-weight: 700; cursor: pointer; font-size: 16px;
             letter-spacing: -0.01em; box-shadow: 0 4px 12px rgba(0,0,0,0.15);
             transition: transform 0.1s; }}
.big-save:hover {{ transform: translateY(-1px); box-shadow: 0 6px 16px rgba(0,0,0,0.2); }}
.big-save:active {{ transform: translateY(0); }}
.save-feedback {{ margin-top: 14px; font-size: 13px; opacity: 0.85; min-height: 18px; }}

/* Loaded state banner */
.loaded-banner {{ background: #DBEAFE; border-left: 4px solid #2563EB; padding: 10px 14px;
                  border-radius: 4px; font-size: 13px; color: #1E3A8A; margin-bottom: 14px; }}

/* Call 2 section uses phase-D color */
.call2-prep-note {{ background: #FFEDD5; border-left: 4px solid #EA580C; padding: 10px 14px;
                    border-radius: 4px; font-size: 13px; color: #7C2D12; }}

/* Print */
@media print {{
    body {{ background: white; padding: 16px; max-width: 100%; }}
    .toolbar {{ display: none; }}
    .card {{ break-inside: avoid; box-shadow: none; border: 1px solid #ddd; }}
    details {{ break-inside: avoid; background: white; }}
    details summary {{ list-style: none; }}
    /* Force open all details, deplier les loops Belfort */
    details > p, details > .loop-step {{ display: flex !important; }}
    details > p {{ display: block !important; }}
    a {{ color: black; text-decoration: none; }}
    .roi-box {{ background: white; border-color: #999; }}
    .hook-box {{ background: #FEF8E1; }}
}}
</style>
</head>
<body>

<div class="toolbar">
    <span class="brand">Mad Makers — Cold call brief</span>
    <span>
        <button onclick="window.print()">Imprimer / PDF</button>
        <button onclick="resetForm()">Reset</button>
        <span class="saved" id="saved">Auto-save active</span>
    </span>
</div>

<!-- PHASE NAVIGATION -->
<nav class="phase-nav">
    <a href="#phase-A" class="phase-link active" data-phase="A">A. Préparation<small>avant l'appel</small></a>
    <a href="#phase-B" class="phase-link" data-phase="B">B. CALL 1<small>découverte + RDV 2</small></a>
    <a href="#phase-C" class="phase-link" data-phase="C">C. Fin Call 1<small>outcome + résumé</small></a>
    <a href="#phase-D" class="phase-link" data-phase="D">D. CALL 2<small>maquette + closing</small></a>
</nav>

<div id="loaded-banner-host"></div>

<!-- HEADER -->
<div class="card header-card">
    <span class="cat-badge">{cat_text}</span>
    <h1>{full}</h1>
    <div class="id-grid">
        <div><b>Titre</b>{titre}</div>
        <div><b>Entreprise</b>{boite}</div>
        <div><b>Ville</b>{ville}</div>
        <div><b>Email</b><a href="mailto:{email}">{email}</a></div>
        <div><b>LinkedIn</b><a href="{linkedin}" target="_blank">{linkedin or '—'}</a></div>
        <div><b>Site</b>{f'<a href="{site}" target="_blank">{site}</a>' if site else '—'}</div>
    </div>
</div>

<!-- ============ PHASE A : PRÉPARATION ============ -->
<div class="phase-banner phase-A" id="phase-A">
    <h2>Phase A — Préparation (avant l'appel)</h2>
    <p>Audit factuel + arguments financiers à mobiliser. À lire avant de décrocher.</p>
</div>

<!-- AUDIT -->
<h2 class="sec"><span class="num">1</span>Audit express du site <span style="font-size:12px;font-weight:400;color:#6B7280">— données factuelles uniquement, ZERO invention</span></h2>
<div class="card">{audit_block}</div>

<!-- ARGUMENTS FINANCIERS -->
<h2 class="sec"><span class="num">2</span>Arguments financiers — pourquoi c'est un INVESTISSEMENT</h2>
<div class="card">
    <h3>Gains actifs (mesurables AVANT/APRÈS)</h3>
    <ul class="arg-list">{actifs_html}</ul>

    <h3>Gains passifs (effets long-terme)</h3>
    <ul class="arg-list">{passifs_html}</ul>

    <h3>Promesse Mad Makers (différenciants à mobiliser)</h3>
    <ul class="arg-list">{promesse_html}</ul>
</div>

<!-- ============ PHASE B : CALL 1 LIVE ============ -->
<div class="phase-banner phase-B" id="phase-B">
    <h2>Phase B — Call 1 (en direct — qualif + caler RDV 2)</h2>
    <p>Suivez l'ordre. Cochez ce qui est confirmé. Remplissez ce qui est dit. ROI calculé en LIVE pendant l'appel.</p>
</div>

<!-- HOOK -->
<h2 class="sec"><span class="num">3</span>Ouverture / Hook (Belfort 4-second crack — 60-90s)</h2>
<div class="card">
    <div class="scenario">{htmllib.escape(intro['scenario'])}</div>
    <div class="hook-box">{htmllib.escape(intro['hook'])}</div>
    <h4>Phrase de validation à obtenir (Belfort : premier "oui")</h4>
    <p>« OK, je vous écoute » / « 5 minutes ok » → vous enchaînez. Sinon : « Vous préférez que je rappelle quand ? Demain matin ou en fin d'après-midi ? » (alternative-choice).</p>
</div>

<!-- DECOUVERTE -->
<h2 class="sec"><span class="num">4</span>Découverte (intelligence gathering — questions à poser)</h2>
<div class="card">{questions_html}</div>

<!-- PAINS -->
<h2 class="sec"><span class="num">5</span>Pain points probables (à confirmer en live, pas à affirmer)</h2>
<div class="card">
    <ul class="pains">{pains_html}</ul>
    <h4 style="margin-top:14px">Notes additionnelles sur les pains évoqués par le prospect</h4>
    <textarea class="notes-area" data-key="pains_notes" placeholder="ce que le prospect a évoqué comme douleurs réelles..."></textarea>
</div>

<!-- ROI CALCULATOR INTERACTIVE -->
<h2 class="sec"><span class="num">6</span>ROI Calculator <span style="font-size:12px;font-weight:400;color:#6B7280">— interactif, calcul en LIVE pendant l'appel</span></h2>
<div class="card">
    <p style="margin-top:0;color:#4B5563"><b>Méthode Belfort :</b> faire calculer le prospect, pas vous. Posez chaque question, entrez le chiffre qu'il vous donne, le payback s'affiche en temps réel. <b>Communiquez le résultat directement au client.</b></p>

    <div class="roi-form">
        <label>(1) Valeur client moyen (€)
            <input type="number" id="roi_valeur_client" data-key="roi_valeur_client" placeholder="ex : 5000" min="0" step="100">
        </label>
        <label>(2) Leads supplémentaires/mois estimés
            <input type="number" id="roi_leads" data-key="roi_leads" placeholder="ex : 5" min="0" step="1">
        </label>
        <label>(3) Taux de conversion lead → client (%)
            <input type="number" id="roi_conversion" data-key="roi_conversion" placeholder="ex : 20" min="0" max="100" step="1">
        </label>
        <label>(4) Montant devis Mad Makers (€)
            <input type="number" id="roi_devis" data-key="roi_devis" placeholder="ex : 8000" min="0" step="100">
        </label>
    </div>

    <div class="roi-result">
        <div class="roi-metric">
            <span class="roi-label">Gain mensuel estimé</span>
            <span class="roi-value" id="roi_gain">— €</span>
        </div>
        <div class="roi-metric">
            <span class="roi-label">Payback de l'investissement</span>
            <span class="roi-value" id="roi_payback">— mois</span>
        </div>
        <div class="roi-verdict idle" id="roi_verdict">Entrez les 4 chiffres pour calculer le payback en temps réel.</div>
    </div>

    <p style="margin-top:14px;font-size:12px;color:#374151"><i><b>Règle d'or :</b> ces chiffres viennent du PROSPECT, jamais inventés. Si le prospect ne sait pas, on note "à mesurer" et on construit la mesure dans le RDV 2 (tracking GA4 inclus dans la livraison).</i></p>
</div>

<!-- FUTURE PACING -->
<h2 class="sec"><span class="num">7</span>Future Pacing (Belfort) — visualisation à déployer mid-call</h2>
<div class="card">
    <p style="margin-top:0;color:#4B5563"><b>Quand placer cette phrase :</b> après avoir confirmé 2-3 pains + après avoir calculé le ROI ensemble, juste avant le pitch RDV 2. Effet : projeter le client dans la possession du résultat.</p>
    <div class="hook-box">{htmllib.escape(FUTURE_PACING)}</div>
</div>

<!-- VISUELS -->
<h2 class="sec"><span class="num">8</span>Demande de visuels (CRUCIAL — base de la maquette RDV 2)</h2>
<div class="card">
    <p style="margin-top:0;color:#4B5563"><i>Phrase a placer : « Pour qu'on vous prepare une maquette LE PLUS JUSTE possible, pouvez-vous nous envoyer ce qu'il y a sur cette liste avant la fin de la semaine ? Plus c'est complet, plus la maquette sera proche de votre marque reelle. »</i></p>
    <ul class="visuels">{visuels_html}</ul>
</div>

<!-- PITCH RDV2 -->
<h2>8. Pitch transition vers RDV 2 (assumed close Belfort)</h2>
<div class="card">
    <p><b>Phrase de bascule (presupposition close) :</b></p>
    <div class="hook-box">« Voila ce que je vous propose, et c'est tres simple : vous m'envoyez les visuels qu'on vient de lister, je vous bloque 30 minutes en visio mardi prochain a 14h ou jeudi a 10h — vous me dites lequel des deux marche le mieux. À ce RDV 2, je vous montre une maquette CONSTRUITE SPECIFIQUEMENT pour {boite}, on regarde le devis precis, et la VOUS decidez si on travaille ensemble ou pas. Aucun engagement de votre cote tant que vous n'avez pas vu la maquette. Mardi 14h ou jeudi 10h ? »</div>
    <h4>Engagement attendu (3 points concrets)</h4>
    <ol style="padding-left:20px">
        <li><b>Date du RDV 2 obtenue</b> (alternative-choice : mardi OU jeudi). Calendly direct : <a href="https://calendly.com/directedbymaick/30min" target="_blank">calendly.com/directedbymaick/30min</a></li>
        <li><b>Mail recap envoye dans la foulee</b> (max 2h apres l'appel) avec la liste de visuels demandes + invit Calendly</li>
        <li><b>Mad Makers prepare la maquette</b> (1 page hero + breakdown sections) sous 5 jours ouvres</li>
    </ol>
</div>

<!-- OBJECTIONS -->
<h2 class="sec"><span class="num">10</span>Objections — réponses Belfort (Loop : Agree → Bridge → Reinforce → Close)</h2>
<div class="card">
    <p style="margin-top:0;color:#4B5563;font-size:13px"><b>Méthode Belfort :</b> ne JAMAIS contredire frontalement. On reconnaît l'objection (AGREE), on la reframe avec une question (BRIDGE), on renforce la certitude (3 tens : produit / vous / boîte) [REINFORCE], on ferme en alternative-choice [CLOSE]. Cliquez chaque objection pour déplier la réponse structurée.</p>
    {obj_html}
</div>

<!-- CLOSING PATTERNS -->
<h2 class="sec"><span class="num">11</span>Closing patterns — bibliothèque à piocher en live</h2>
<div class="card">
    <ul class="close-list">{closes_html}</ul>
    <p style="margin-top:12px;color:#4B5563;font-size:13px"><i>Règle Belfort : on ferme TOUJOURS en alternative-choice ou en assumed close, jamais en oui/non.</i></p>
</div>

<!-- NOTES LIVE -->
<h2 class="sec"><span class="num">12</span>Notes live (à remplir pendant l'appel)</h2>
<div class="card">
    <h4>Contexte business / activité</h4>
    <textarea class="notes-area" data-key="notes_business"></textarea>

    <h4>Concurrents cités</h4>
    <textarea class="notes-area" data-key="notes_concurrents"></textarea>

    <h4>Refs / sites qu'il aime</h4>
    <textarea class="notes-area" data-key="notes_refs"></textarea>

    <h4>Budget évoqué / fourchette</h4>
    <textarea class="notes-area" data-key="notes_budget"></textarea>

    <h4>Autres notes / signaux</h4>
    <textarea class="notes-area" data-key="notes_other"></textarea>
</div>

<!-- ============ PHASE C : FIN CALL 1 + RÉSUMÉ ============ -->
<div class="phase-banner phase-C" id="phase-C">
    <h2>Phase C — Fin Call 1 : outcome + génération du résumé</h2>
    <p>Remplissez l'outcome dès la fin de l'appel, puis cliquez sur le bouton vert tout en bas pour générer un résumé HTML + JSON automatiquement.</p>
</div>

<!-- OUTCOME -->
<h2 class="sec"><span class="num">13</span>Outcome de l'appel 1</h2>
<div class="card">
    <div class="outcome-grid">
        <label>Statut
            <select data-key="out_statut">
                <option value="">—</option>
                <option>RDV 2 calé</option>
                <option>À relancer (envoyer mail récap)</option>
                <option>Pas intéressé</option>
                <option>Pas le bon moment</option>
                <option>Refus poli</option>
                <option>Répondeur / pas joignable</option>
            </select>
        </label>
        <label>Date RDV 2
            <input type="date" data-key="out_rdv2_date">
        </label>
        <label>Heure RDV 2
            <input type="time" data-key="out_rdv2_heure">
        </label>
        <label>Intérêt (1-5)
            <input type="number" min="1" max="5" data-key="out_interet">
        </label>
        <label>Visuels promis ?
            <select data-key="out_visuels_promis">
                <option value="">—</option>
                <option>Oui — déjà reçus</option>
                <option>Oui — à envoyer</option>
                <option>Partiellement</option>
                <option>Non / à voir</option>
            </select>
        </label>
        <label>Budget évoqué (€)
            <input type="text" data-key="out_budget_recu" placeholder="ex : 5-10K, ou 'pas dit'">
        </label>
        <label style="grid-column: span 2">Prochaine action concrète
            <input type="text" data-key="out_next" placeholder="ex : envoyer mail récap + Calendly avant 18h">
        </label>
        <label style="grid-column: span 2">Résumé express en 1-2 phrases
            <input type="text" data-key="out_summary" placeholder="ex : Boîte sympa, RDV 2 jeudi 10h, intéressé par one-page + SEO local">
        </label>
    </div>
</div>

<!-- ============ PHASE D : CALL 2 (RDV maquette) ============ -->
<div class="phase-banner phase-D" id="phase-D">
    <h2>Phase D — Call 2 (RDV maquette + closing devis)</h2>
    <p>À remplir pendant et après le RDV 2. Préparation : maquette présentée, devis envoyé, signature.</p>
</div>

<h2 class="sec"><span class="num">14</span>Préparation maquette (entre Call 1 et Call 2)</h2>
<div class="card">
    <p class="call2-prep-note"><b>Checklist avant Call 2 :</b> visuels reçus du prospect ? Maquette construite (1 page hero + breakdown) ? Devis chiffré au scope ? Drive partagé prêt à montrer ?</p>

    <h4 style="margin-top:12px">Visuels reçus (lien Drive ou notes)</h4>
    <textarea class="notes-area" data-key="call2_visuels_recus" placeholder="ex : drive.google.com/... — logo SVG OK, photos lieu OK, photos équipe manquantes"></textarea>

    <h4>Notes pour la maquette (axes de positionnement, refs trouvées)</h4>
    <textarea class="notes-area" data-key="call2_maquette_notes" placeholder="ex : positionnement haut de gamme, refs riot/airbnb, hero avec vidéo bg, palette bleu nuit + ocre..."></textarea>

    <h4>Devis chiffré préparé</h4>
    <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px">
        <label style="font-size:12px;color:#6B7280">Montant devis (€)<input type="number" data-key="call2_devis_montant" placeholder="ex : 8500" style="width:100%;padding:6px 10px;border:1px solid #D1D5DB;border-radius:4px;font-size:14px"></label>
        <label style="font-size:12px;color:#6B7280">Délai (jours)<input type="number" data-key="call2_devis_delai" value="10" style="width:100%;padding:6px 10px;border:1px solid #D1D5DB;border-radius:4px;font-size:14px"></label>
    </div>
</div>

<h2 class="sec"><span class="num">15</span>Présentation maquette + réactions client</h2>
<div class="card">
    <h4>Réactions à chaud du prospect (verbatim)</h4>
    <textarea class="notes-area" data-key="call2_reactions" placeholder="« j'aime le hero », « les couleurs c'est pas trop ça », « je verrais plutôt... »"></textarea>

    <h4>Modifications demandées (à inclure dans la v2)</h4>
    <textarea class="notes-area" data-key="call2_modifs" placeholder="liste des changements demandés, par priorité"></textarea>

    <h4>Objections sur le devis (prix / délai / scope)</h4>
    <textarea class="notes-area" data-key="call2_objections" placeholder="ce que le prospect a soulevé sur le devis"></textarea>
</div>

<h2 class="sec"><span class="num">16</span>Outcome Call 2 (signature)</h2>
<div class="card">
    <div class="outcome-grid">
        <label>Statut Call 2
            <select data-key="call2_statut">
                <option value="">—</option>
                <option>Signé — acompte versé</option>
                <option>Signé — en attente acompte</option>
                <option>OK verbal, attend devis v2</option>
                <option>À retravailler (modifs maquette)</option>
                <option>Pas signé — pas le bon moment</option>
                <option>Pas signé — concurrent choisi</option>
                <option>Pas signé — budget</option>
                <option>Pas signé — pas convaincu</option>
            </select>
        </label>
        <label>Date signature prévue
            <input type="date" data-key="call2_signature_date">
        </label>
        <label>Acompte 40% (€)
            <input type="number" data-key="call2_acompte" placeholder="40% du devis">
        </label>
        <label>Date kickoff projet
            <input type="date" data-key="call2_kickoff">
        </label>
        <label style="grid-column: span 2">Prochaine action après Call 2
            <input type="text" data-key="call2_next" placeholder="ex : envoyer devis v2 + planning précis">
        </label>
        <label style="grid-column: span 2">Résumé final du deal
            <input type="text" data-key="call2_summary" placeholder="ex : Signé 8500€ HT, kickoff lundi, livraison J+10">
        </label>
    </div>
</div>

<!-- SAVE BLOCK -->
<div class="save-block">
    <h2>Enregistrer le call & générer le résumé automatique</h2>
    <p>Génère un résumé HTML lisible + un JSON rechargeable. Les 2 fichiers se téléchargent dans votre dossier <code>Downloads</code> — déplacez-les ensuite dans <code>linkedin-scraper/data/briefings/</code>. Pour préparer le Call 2, rechargez le JSON via <code>python -X utf8 scripts/cold_call.py --name "..." --load &lt;json&gt;</code>.</p>
    <button class="big-save" onclick="saveAndDownload()">📞 Enregistrer le call & générer le résumé</button>
    <div class="save-feedback" id="save_feedback"></div>
</div>

<script>
const STORAGE_KEY = "mm_briefing_{storage_key}";
const PROSPECT = {{
    nom_complet: {prospect_json_name},
    entreprise: {prospect_json_boite},
    titre: {prospect_json_titre},
    ville: {prospect_json_ville},
    email: {prospect_json_email},
    linkedin_url: {prospect_json_linkedin},
    site_url: {prospect_json_site},
    categorie: {prospect_json_cat},
    slug: "{slug}"
}};
const INITIAL_STATE = {initial_state_json};

function getState() {{
    const state = {{}};
    document.querySelectorAll("[data-key]").forEach(el => {{
        const key = el.getAttribute("data-key");
        if (el.type === "checkbox") state[key] = el.checked;
        else state[key] = el.value;
    }});
    return state;
}}

function applyState(state) {{
    if (!state) return;
    document.querySelectorAll("[data-key]").forEach(el => {{
        const key = el.getAttribute("data-key");
        if (state[key] === undefined) return;
        if (el.type === "checkbox") el.checked = !!state[key];
        else el.value = state[key];
    }});
    updateROI();
}}

function save() {{
    localStorage.setItem(STORAGE_KEY, JSON.stringify(getState()));
    const s = document.getElementById("saved");
    if (s) {{
        s.textContent = "Auto-save " + new Date().toLocaleTimeString();
        s.style.opacity = "1";
        setTimeout(() => s.style.opacity = "0.6", 1200);
    }}
}}

function resetForm() {{
    if (!confirm("Reset toutes les donnees saisies pour ce prospect ?")) return;
    localStorage.removeItem(STORAGE_KEY);
    document.querySelectorAll("[data-key]").forEach(el => {{
        if (el.type === "checkbox") el.checked = false;
        else el.value = "";
    }});
    updateROI();
}}

// ─── ROI Calculator live ────────────────────────────────────────────────
function updateROI() {{
    const vc = parseFloat(document.getElementById('roi_valeur_client').value) || 0;
    const leads = parseFloat(document.getElementById('roi_leads').value) || 0;
    const conv = (parseFloat(document.getElementById('roi_conversion').value) || 0) / 100;
    const devis = parseFloat(document.getElementById('roi_devis').value) || 0;

    const gain = vc * leads * conv;
    const payback = (gain > 0 && devis > 0) ? (devis / gain) : null;

    const fmtEur = n => n > 0 ? n.toLocaleString('fr-FR', {{maximumFractionDigits: 0}}) + ' €' : '— €';

    document.getElementById('roi_gain').textContent = fmtEur(gain);
    document.getElementById('roi_payback').textContent = payback ? payback.toFixed(1) + ' mois' : '— mois';

    const v = document.getElementById('roi_verdict');
    v.classList.remove('idle', 'green', 'amber', 'red');
    if (!payback) {{
        v.classList.add('idle');
        v.textContent = 'Entrez les 4 chiffres pour calculer le payback en temps réel.';
    }} else if (payback < 6) {{
        v.classList.add('green');
        v.textContent = `Payback ${{payback.toFixed(1)}} mois — ROI fort, communiquez ce chiffre au client : "vous récupérez l'investissement en moins de 6 mois". Closez le RDV 2.`;
    }} else if (payback < 12) {{
        v.classList.add('amber');
        v.textContent = `Payback ${{payback.toFixed(1)}} mois — ROI acceptable, c'est défendable. Renforcez avec les gains passifs (image, trust, recrutement).`;
    }} else {{
        v.classList.add('red');
        v.textContent = `Payback ${{payback.toFixed(1)}} mois — argumentez sur les gains passifs et le coût d'opportunité. Le ROI cash n'est pas le bon angle ici.`;
    }}
}}

// ─── Phase nav scroll-spy ──────────────────────────────────────────────
function initPhaseNav() {{
    const links = document.querySelectorAll('.phase-link');
    const targets = ['phase-A', 'phase-B', 'phase-C', 'phase-D'];
    function setActive(phase) {{
        links.forEach(l => l.classList.toggle('active', l.dataset.phase === phase));
    }}
    window.addEventListener('scroll', () => {{
        let current = 'A';
        for (const id of targets) {{
            const el = document.getElementById(id);
            if (el && el.getBoundingClientRect().top < 200) current = id.split('-')[1];
        }}
        setActive(current);
    }});
}}

// ─── Save + download summary ───────────────────────────────────────────
function escapeHtml(s) {{
    if (s === null || s === undefined) return '';
    return String(s).replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}})[c]);
}}

function nowStamp() {{
    const d = new Date();
    const pad = n => String(n).padStart(2, '0');
    return `${{d.getFullYear()}}${{pad(d.getMonth()+1)}}${{pad(d.getDate())}}_${{pad(d.getHours())}}${{pad(d.getMinutes())}}`;
}}

function getCheckedLabels(prefix) {{
    const out = [];
    document.querySelectorAll(`[data-key^="${{prefix}}"]`).forEach(el => {{
        if (el.type === 'checkbox' && el.checked) {{
            const label = el.closest('label');
            if (label) out.push(label.innerText.trim());
        }}
    }});
    return out;
}}

function getQuestionsAnswered() {{
    // qn_* = answers, q_* = checkbox per question
    const out = [];
    document.querySelectorAll('[data-key^="qn_"]').forEach(el => {{
        const ans = (el.value || '').trim();
        if (!ans) return;
        const li = el.closest('li');
        const q = li ? li.querySelector('.q-text') : null;
        out.push({{ question: q ? q.innerText.trim() : '', reponse: ans }});
    }});
    return out;
}}

function computeNextActions(state) {{
    const acts = [];
    const statut = state.out_statut || '';
    const date2 = state.out_rdv2_date || '';
    const heure2 = state.out_rdv2_heure || '';

    if (statut === 'RDV 2 calé') {{
        if (date2) acts.push(`Envoyer l'invit Calendly pour le RDV 2 du ${{date2}}${{heure2 ? ' à ' + heure2 : ''}} dans les 2h`);
        acts.push('Envoyer mail récap dans la foulée avec lien Drive pour upload des visuels');
        acts.push('Préparer la maquette (1 page hero + breakdown) sous 5 jours ouvrés');
        if (state.out_visuels_promis && state.out_visuels_promis.startsWith('Oui')) {{
            acts.push('Suivre la réception des visuels promis (relancer J+2 si rien reçu)');
        }}
    }} else if (statut === 'À relancer (envoyer mail récap)') {{
        acts.push('Envoyer mail récap personnalisé dans les 2h (audit + 3 cas réf)');
        acts.push('Mettre en suivi pour relance J+7 si pas de réponse');
    }} else if (statut === 'Pas le bon moment') {{
        acts.push('Mettre en pause, relance prévue dans 1-3 mois selon contexte');
        acts.push('Noter la raison du timing dans le CRM/XLSX');
    }} else if (statut === 'Pas intéressé' || statut === 'Refus poli') {{
        acts.push('Marquer prospect dormant. Relance possible dans 6 mois si contexte change');
    }} else if (statut === 'Répondeur / pas joignable') {{
        acts.push('Re-tenter rappel J+1 puis J+3 puis J+7');
        acts.push('Envoyer email court avec invitation à rappeler');
    }}

    // ROI inclus dans recap
    const vc = parseFloat(state.roi_valeur_client) || 0;
    const leads = parseFloat(state.roi_leads) || 0;
    const conv = (parseFloat(state.roi_conversion) || 0) / 100;
    const devis = parseFloat(state.roi_devis) || 0;
    const gain = vc * leads * conv;
    const payback = (gain > 0 && devis > 0) ? (devis / gain) : null;
    if (payback) {{
        acts.push(`Inclure dans mail récap : payback calculé = ${{payback.toFixed(1)}} mois (gain mensuel ~${{Math.round(gain).toLocaleString('fr-FR')}}€)`);
    }}

    if (state.notes_concurrents && state.notes_concurrents.trim().length > 5) {{
        acts.push('Préparer une slide comparative avec les concurrents cités pour le RDV 2');
    }}

    if (state.notes_refs && state.notes_refs.trim().length > 5) {{
        acts.push('Intégrer les refs du prospect comme inspiration dans la maquette');
    }}

    return acts.length ? acts : ['(remplissez le statut pour générer les actions auto)'];
}}

function buildSummaryHTML(state) {{
    const today = new Date();
    const dateStr = today.toLocaleDateString('fr-FR') + ' ' + today.toLocaleTimeString('fr-FR', {{hour:'2-digit',minute:'2-digit'}});
    const pains = getCheckedLabels('pain_');
    const visuels = getCheckedLabels('vis_');
    const qa = getQuestionsAnswered();
    const acts = computeNextActions(state);

    const vc = parseFloat(state.roi_valeur_client) || 0;
    const leads = parseFloat(state.roi_leads) || 0;
    const conv = (parseFloat(state.roi_conversion) || 0) / 100;
    const devis = parseFloat(state.roi_devis) || 0;
    const gain = vc * leads * conv;
    const payback = (gain > 0 && devis > 0) ? (devis / gain) : null;
    const fmtEur = n => n > 0 ? n.toLocaleString('fr-FR', {{maximumFractionDigits:0}}) + ' €' : '—';

    const sec = (title, body) => body && body.trim() ? `<h2>${{escapeHtml(title)}}</h2><div class="body">${{body}}</div>` : '';

    const painsHtml = pains.length ? '<ul>' + pains.map(p => `<li>${{escapeHtml(p)}}</li>`).join('') + '</ul>' : '<p><i>aucun confirmé</i></p>';
    const visuelsHtml = visuels.length ? '<ul>' + visuels.map(p => `<li>${{escapeHtml(p)}}</li>`).join('') + '</ul>' : '<p><i>aucun coché</i></p>';
    const qaHtml = qa.length ? qa.map(({{question, reponse}}) => `<div class="qa"><div class="q">${{escapeHtml(question)}}</div><div class="r">${{escapeHtml(reponse)}}</div></div>`).join('') : '<p><i>aucune réponse remplie</i></p>';
    const actsHtml = '<ol>' + acts.map(a => `<li>${{escapeHtml(a)}}</li>`).join('') + '</ol>';

    return `<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Résumé call — ${{escapeHtml(PROSPECT.nom_complet)}}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, system-ui, sans-serif; color: #111827; max-width: 900px; margin: 0 auto; padding: 32px; background: #F5F5F4; line-height: 1.55; font-size: 14px; }}
h1 {{ font-size: 26px; margin: 0 0 4px; letter-spacing: -0.02em; }}
h2 {{ font-size: 16px; margin: 24px 0 8px; padding: 8px 12px; background: #111827; color: white; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.06em; }}
.card {{ background: white; border: 1px solid #E5E7EB; border-radius: 8px; padding: 16px 20px; margin-bottom: 14px; }}
.body {{ background: white; border: 1px solid #E5E7EB; padding: 14px 18px; border-radius: 6px; }}
.id-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px 18px; font-size: 13px; }}
.id-grid b {{ color: #6B7280; font-weight: 500; margin-right: 6px; }}
.kpi {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 8px 0; }}
.kpi .k {{ background: white; border: 1px solid #E5E7EB; padding: 10px 12px; border-radius: 6px; }}
.kpi .lab {{ font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em; color: #6B7280; }}
.kpi .val {{ font-size: 18px; font-weight: 700; margin-top: 2px; }}
.actions {{ background: #052e16; color: white; padding: 18px 22px; border-radius: 8px; }}
.actions h2 {{ background: transparent; padding: 0 0 10px; color: white; }}
.actions ol {{ margin: 0; padding-left: 22px; }}
.actions li {{ margin: 6px 0; line-height: 1.5; }}
.qa {{ margin-bottom: 10px; }}
.qa .q {{ font-weight: 600; color: #4B5563; font-size: 13px; }}
.qa .r {{ color: #111827; padding-left: 10px; border-left: 2px solid #D1D5DB; margin-top: 2px; }}
.cat {{ display: inline-block; padding: 3px 10px; border-radius: 4px; font-weight: 700; font-size: 11px; letter-spacing: 0.06em; text-transform: uppercase; }}
.payback-good {{ color: #16a34a; }}
.payback-mid {{ color: #f59e0b; }}
.payback-bad {{ color: #dc2626; }}
@media print {{ body {{ background: white; }} .card, .body {{ break-inside: avoid; box-shadow: none; }} }}
</style></head><body>

<h1>Résumé du call — ${{escapeHtml(PROSPECT.nom_complet)}}</h1>
<p style="color:#6B7280;margin:0 0 16px"><b>Date du call :</b> ${{dateStr}} &nbsp;·&nbsp; <b>Catégorie :</b> ${{escapeHtml(PROSPECT.categorie)}}</p>

<div class="card">
    <div class="id-grid">
        <div><b>Entreprise</b>${{escapeHtml(PROSPECT.entreprise)}}</div>
        <div><b>Titre</b>${{escapeHtml(PROSPECT.titre)}}</div>
        <div><b>Ville</b>${{escapeHtml(PROSPECT.ville)}}</div>
        <div><b>Email</b>${{escapeHtml(PROSPECT.email)}}</div>
        <div><b>LinkedIn</b><a href="${{escapeHtml(PROSPECT.linkedin_url)}}" target="_blank">${{escapeHtml(PROSPECT.linkedin_url)}}</a></div>
        <div><b>Site</b>${{PROSPECT.site_url ? '<a href="'+escapeHtml(PROSPECT.site_url)+'" target="_blank">'+escapeHtml(PROSPECT.site_url)+'</a>' : '—'}}</div>
    </div>
</div>

<h2>Outcome de l'appel 1</h2>
<div class="body">
    <p><b>Statut :</b> ${{escapeHtml(state.out_statut) || '—'}}</p>
    <p><b>Intérêt :</b> ${{escapeHtml(state.out_interet) || '—'}}/5 &nbsp;·&nbsp; <b>RDV 2 :</b> ${{escapeHtml(state.out_rdv2_date) || '—'}} ${{escapeHtml(state.out_rdv2_heure) || ''}}</p>
    <p><b>Visuels promis :</b> ${{escapeHtml(state.out_visuels_promis) || '—'}} &nbsp;·&nbsp; <b>Budget évoqué :</b> ${{escapeHtml(state.out_budget_recu) || '—'}}</p>
    <p><b>Résumé express :</b> ${{escapeHtml(state.out_summary) || '—'}}</p>
    <p><b>Prochaine action :</b> ${{escapeHtml(state.out_next) || '—'}}</p>
</div>

<h2>ROI calculé pendant l'appel</h2>
<div class="kpi">
    <div class="k"><div class="lab">Valeur client</div><div class="val">${{fmtEur(vc)}}</div></div>
    <div class="k"><div class="lab">Leads/mois</div><div class="val">${{leads || '—'}}</div></div>
    <div class="k"><div class="lab">Conversion</div><div class="val">${{(conv*100).toFixed(0) + ' %' || '—'}}</div></div>
    <div class="k"><div class="lab">Devis</div><div class="val">${{fmtEur(devis)}}</div></div>
</div>
<div class="kpi" style="grid-template-columns: 1fr 1fr">
    <div class="k"><div class="lab">Gain mensuel estimé</div><div class="val">${{fmtEur(gain)}}</div></div>
    <div class="k"><div class="lab">Payback</div><div class="val ${{payback ? (payback < 6 ? 'payback-good' : payback < 12 ? 'payback-mid' : 'payback-bad') : ''}}">${{payback ? payback.toFixed(1) + ' mois' : '—'}}</div></div>
</div>

<h2>Pain points confirmés en live</h2>
<div class="body">${{painsHtml}}</div>

<h2>Réponses découverte</h2>
<div class="body">${{qaHtml}}</div>

<h2>Visuels promis / cochés</h2>
<div class="body">${{visuelsHtml}}</div>

${{sec('Notes business', state.notes_business ? '<p>'+escapeHtml(state.notes_business).replace(/\\n/g,'<br>')+'</p>' : '')}}
${{sec('Concurrents cités', state.notes_concurrents ? '<p>'+escapeHtml(state.notes_concurrents).replace(/\\n/g,'<br>')+'</p>' : '')}}
${{sec('Refs / sites qu\\'il aime', state.notes_refs ? '<p>'+escapeHtml(state.notes_refs).replace(/\\n/g,'<br>')+'</p>' : '')}}
${{sec('Budget évoqué', state.notes_budget ? '<p>'+escapeHtml(state.notes_budget).replace(/\\n/g,'<br>')+'</p>' : '')}}
${{sec('Autres notes', state.notes_other ? '<p>'+escapeHtml(state.notes_other).replace(/\\n/g,'<br>')+'</p>' : '')}}

<div class="actions">
    <h2 style="color:white">Prochaines actions (auto)</h2>
    ${{actsHtml}}
</div>

</body></html>`;
}}

function downloadFile(filename, content, mime) {{
    const blob = new Blob([content], {{type: mime + ';charset=utf-8'}});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}}

function saveAndDownload() {{
    const state = getState();
    const stamp = nowStamp();
    const slug = PROSPECT.slug;

    // 1. HTML résumé
    const summary = buildSummaryHTML(state);
    downloadFile(`${{slug}}_resume_${{stamp}}.html`, summary, 'text/html');

    // 2. JSON pour rechargement
    const payload = {{
        prospect: PROSPECT,
        saved_at: new Date().toISOString(),
        state: state
    }};
    downloadFile(`${{slug}}_call_data_${{stamp}}.json`, JSON.stringify(payload, null, 2), 'application/json');

    const fb = document.getElementById('save_feedback');
    if (fb) {{
        fb.innerHTML = `✓ Résumé téléchargé : <code>${{slug}}_resume_${{stamp}}.html</code> + <code>${{slug}}_call_data_${{stamp}}.json</code><br>Déplacez les 2 fichiers dans <code>linkedin-scraper/data/briefings/</code>`;
    }}
}}

// ─── Init ────────────────────────────────────────────────────────────────
document.querySelectorAll("[data-key]").forEach(el => {{
    el.addEventListener("input", save);
    el.addEventListener("change", save);
}});

// Hook ROI inputs to update calc
['roi_valeur_client', 'roi_leads', 'roi_conversion', 'roi_devis'].forEach(id => {{
    const el = document.getElementById(id);
    if (el) el.addEventListener('input', updateROI);
}});

// 1. Apply localStorage state if any
let loadedFromInitial = false;
try {{
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    if (stored) applyState(stored);
}} catch (e) {{}}

// 2. If --load was used, INITIAL_STATE has data → apply over (priority)
if (INITIAL_STATE && Object.keys(INITIAL_STATE).length > 0) {{
    applyState(INITIAL_STATE);
    loadedFromInitial = true;
    const host = document.getElementById('loaded-banner-host');
    if (host) {{
        host.innerHTML = '<div class="loaded-banner">📁 Données chargées depuis le JSON précédent (Call 1). Vous êtes en préparation Call 2.</div>';
    }}
}}

// 3. Init ROI calc + phase nav
updateROI();
initPhaseNav();
</script>

</body>
</html>"""


def main():
    import json as _json
    parser = argparse.ArgumentParser(description="Genere un brief HTML de cold call.")
    parser.add_argument("--name", help="Nom complet du prospect (match contains, casse insensible)")
    parser.add_argument("--index", type=int, help="Index 1-based dans le CSV")
    parser.add_argument("--csv", help="CSV de prospection (par defaut le dernier final)")
    parser.add_argument("--no-fetch", action="store_true", help="Ne pas re-fetcher le site")
    parser.add_argument("--open", action="store_true", help="Ouvre le HTML dans le browser")
    parser.add_argument("--load", help="Charge un JSON sauvegarde du Call 1 pour preparer le Call 2")
    args = parser.parse_args()

    # Charger l'etat depuis JSON precedent si --load
    initial_state = {}
    loaded_prospect = None
    if args.load:
        load_path = Path(args.load)
        if not load_path.exists():
            sys.exit(f"ERREUR: {load_path} introuvable")
        try:
            payload = _json.loads(load_path.read_text(encoding="utf-8"))
            initial_state = payload.get("state", {}) or {}
            loaded_prospect = payload.get("prospect", {}) or None
            print(f"État chargé depuis {load_path.name} ({len(initial_state)} champs)")
        except Exception as e:
            sys.exit(f"ERREUR lecture JSON: {e}")

    csv_path = find_csv(args.csv)
    rows = load_prospects(csv_path)
    print(f"CSV charge : {csv_path.name} ({len(rows)} prospects)")

    # Si --load fournit un prospect, on peut auto-resoudre le nom
    if loaded_prospect and not args.name and not args.index:
        args.name = loaded_prospect.get("nom_complet", "")
        print(f"Auto-match prospect depuis JSON : {args.name}")

    prospect = find_prospect(rows, name=args.name, index=args.index)
    print(f"Prospect : {prospect.get('nom_complet','?')} | {prospect.get('entreprise','?')}")

    audit = {"ok": False}
    site = prospect.get("site_url", "").strip()
    if site and not args.no_fetch:
        print(f"Audit live de {site}...")
        audit = audit_site(site)
        if audit.get("ok"):
            print(f"  -> HTTPS={audit['https']} | securite={audit['security_grade']} | technos={', '.join(audit['technos']) or 'none'}")
        else:
            print(f"  -> echec: {audit.get('error')}")
    elif site:
        print("(--no-fetch active, audit ignore)")
    else:
        print("Pas de site dans le CSV — categorie SANS_SITE.")

    pains = detect_pains(prospect, audit)
    intro = build_intro(prospect, audit)
    html = render_html(prospect, audit, pains, intro, initial_state=initial_state)

    BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)
    slug = slugify(prospect.get("nom_complet", "prospect"))
    suffix = "_call2" if args.load else ""
    out_path = BRIEFINGS_DIR / f"{slug}{suffix}_{TODAY}.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"\nBrief genere : {out_path}")

    if args.open:
        webbrowser.open(out_path.as_uri())


if __name__ == "__main__":
    main()
