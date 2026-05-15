"""crm.seed_templates — peuple la table email_templates avec les templates
   initiaux (J0/J+4/J+10/J+18 par segment) inspirés de
   linkedin-scraper/scripts/generate_email_sequences.py.

   Usage :
       python -X utf8 -m crm.seed_templates           # ajoute si manquant
       python -X utf8 -m crm.seed_templates --reset   # vide + reload (destructif)
"""
import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from .db import init_db, cursor, query_one
from .models import create_template


# ── Signature commune (insérée dans tous les templates) ──────
SIG = (
    "<br><br>"
    "<b>{{user_prenom}}</b><br>"
    "Mad Makers — Direction artistique &amp; production<br>"
    '<a href="https://mad-makers.fr">mad-makers.fr</a> · '
    '<a href="{{calendly}}">Réserver 30 min</a>'
)


# Helper pour wrapper le corps en HTML simple avec retours à la ligne
def H(text: str) -> str:
    """Convertit un texte plain (avec \\n\\n paragraphes) en HTML <p>."""
    paras = text.strip().split("\n\n")
    html = "".join(f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paras if p.strip())
    return html + SIG


# ============================================================
# SEGMENT A — Sans site (création from scratch)
# ============================================================

A_J0 = {
    "name":        "A — Sans site · J0",
    "description": "Premier contact prospect sans site web — invisibilité Google",
    "category":    "cold_email",
    "segment":     "A_SANS_SITE",
    "step":        "J0",
    "subject":     "{{entreprise}} sur Google — invisible",
    "body_html":   H(
        "Bonjour {{prenom}},\n\n"
        "J'ai cherché \"{{entreprise}}\" sur Google ce matin — vous n'apparaissez "
        "nulle part. Vos concurrents occupent les 3 premières places.\n\n"
        "Sans site, vous perdez chaque mois entre 5 et 20 prospects qui auraient "
        "pu vous appeler. À votre niveau d'activité, c'est un manque à gagner réel.\n\n"
        "J'aide des structures comme la vôtre à monter un site qui convertit en "
        "10 jours. Si l'idée vous parle, je vous prépare une maquette gratuite "
        "de ce que ça donnerait pour {{entreprise}}.\n\n"
        "20 minutes cette semaine pour en parler ?"
    ),
}

A_J4 = {
    "name":        "A — Sans site · J+4",
    "description": "Relance 1 — concurrents qui ont investi",
    "category":    "follow_up",
    "segment":     "A_SANS_SITE",
    "step":        "J+4",
    "subject":     "Re: {{entreprise}} sur Google — invisible",
    "body_html":   H(
        "{{prenom}},\n\n"
        "Petit suivi — j'ai pris 15 minutes pour regarder ce que font vos "
        "concurrents en ligne. Plusieurs ont investi leur site il y a quelques "
        "années et captent aujourd'hui la majorité des recherches sur votre métier.\n\n"
        "Si vous voulez voir une première version de ce qu'on pourrait faire pour "
        "{{entreprise}}, je vous envoie une maquette d'ici demain. Aucune obligation derrière."
    ),
}

A_J10 = {
    "name":        "A — Sans site · J+10",
    "description": "Relance 2 — cas client similaire",
    "category":    "follow_up",
    "segment":     "A_SANS_SITE",
    "step":        "J+10",
    "subject":     "Cas client similaire à {{entreprise}}",
    "body_html":   H(
        "{{prenom}},\n\n"
        "Je viens de finir un projet pour une boîte similaire à {{entreprise}} : "
        "de 0 site à 25 leads/mois en 3 mois après mise en ligne.\n\n"
        "Le levier : un site one-page conçu pour la conversion locale + un "
        "référencement Google Business + 4 articles SEO ciblés.\n\n"
        "Si vous voulez le déroulé complet (1 page A4), je vous l'envoie. "
        "Et si ça vous paraît applicable, on s'appelle 20 minutes."
    ),
}

A_J18 = {
    "name":        "A — Sans site · J+18 (Breakup)",
    "description": "Dernier message — laisser la porte ouverte",
    "category":    "breakup",
    "segment":     "A_SANS_SITE",
    "step":        "J+18",
    "subject":     "Dernier message",
    "body_html":   H(
        "{{prenom}},\n\n"
        "Je n'insiste pas — si la création de votre site n'est pas prioritaire "
        "en ce moment, c'est ok.\n\n"
        "Mon agenda reste à votre disposition pour plus tard : {{calendly}}\n\n"
        "Belle suite à {{entreprise}}."
    ),
}


# ============================================================
# SEGMENT B — DG / Founder / CEO
# ============================================================

B_J0 = {
    "name":        "B — DG/Founder · J0",
    "description": "Page d'accueil lente — question conversion",
    "category":    "cold_email",
    "segment":     "B_DG",
    "step":        "J0",
    "subject":     "Page d'accueil de {{entreprise}} — 1 question",
    "body_html":   H(
        "Bonjour {{prenom}},\n\n"
        "J'ai chargé {{site_short}} ce matin. Mobile, 4G normale : quelques "
        "secondes pour afficher le hero. 53 % des visiteurs partent au-delà de "
        "3 secondes. Pour une boîte de votre taille, ça fait sûrement quelques "
        "RDV perdus chaque mois.\n\n"
        "Je dirige Mad Makers, agence qui refait des sites de PME comme la vôtre "
        "en 10 jours, avec un focus sur la conversion et la rapidité — pas la "
        "« refonte cosmétique » classique.\n\n"
        "Je vous prépare en 48h un audit chiffré spécifique à {{entreprise}} "
        "(temps de chargement, fuites de conversion, comparaison avec 2 confrères) ?"
    ),
}

B_J4 = {
    "name":        "B — DG/Founder · J+4",
    "description": "3 points d'optimisation identifiés",
    "category":    "follow_up",
    "segment":     "B_DG",
    "step":        "J+4",
    "subject":     "Re: Page d'accueil de {{entreprise}}",
    "body_html":   H(
        "{{prenom}},\n\n"
        "Pour info, j'ai poussé l'analyse de mon côté — voici les 3 points qui "
        "ressortent sur {{site_short}} :\n\n"
        "1. [À COMPLÉTER — point technique #1]<br>"
        "2. [À COMPLÉTER — point technique #2]<br>"
        "3. [À COMPLÉTER — point technique #3]\n\n"
        "Ces 3 points = ~30 % de leads en plus en moyenne sur les sites qu'on "
        "refait. 20 minutes pour vous expliquer ?"
    ),
}

B_J10 = {
    "name":        "B — DG/Founder · J+10",
    "description": "Cas client similaire avec chiffres",
    "category":    "follow_up",
    "segment":     "B_DG",
    "step":        "J+10",
    "subject":     "Cas client similaire à {{entreprise}}",
    "body_html":   H(
        "{{prenom}},\n\n"
        "Je viens de finir un projet pour une boîte similaire : de 12 leads/mois "
        "à 38 leads/mois en 90 jours, après refonte + optimisation SEO.\n\n"
        "Le levier principal : refonte du tunnel home → contact + tracking GA4 + "
        "4 articles SEO ciblés.\n\n"
        "Si vous voulez le déroulé complet (1 page A4), je vous l'envoie. "
        "Et si ça vous paraît applicable à {{entreprise}}, on s'appelle 20 minutes."
    ),
}

B_J18 = {
    "name":        "B — DG/Founder · J+18 (Breakup)",
    "description": "Dernier message — laisser la porte ouverte",
    "category":    "breakup",
    "segment":     "B_DG",
    "step":        "J+18",
    "subject":     "J'arrête de vous écrire",
    "body_html":   H(
        "{{prenom}},\n\n"
        "Promis, dernier message — pas envie d'être lourd.\n\n"
        "Si la performance de {{site_short}} n'est pas un sujet en ce moment, "
        "je comprends. Si elle redevient prioritaire dans 3 ou 6 mois, mon "
        "agenda est ici : {{calendly}}.\n\n"
        "Bonne suite à {{entreprise}}."
    ),
}


# ============================================================
# SEGMENT C — DAF / CFO
# ============================================================

C_J0 = {
    "name":        "C — DAF/CFO · J0",
    "description": "Angle CPL et coût d'acquisition",
    "category":    "cold_email",
    "segment":     "C_DAF",
    "step":        "J0",
    "subject":     "Coût d'acquisition site web — {{entreprise}}",
    "body_html":   H(
        "Bonjour {{prenom}},\n\n"
        "Question rapide : quel est aujourd'hui votre coût d'acquisition par "
        "lead via {{site_short}} ?\n\n"
        "90 % des DAF que je rencontre n'ont pas la réponse — pas par négligence, "
        "mais parce que le site n'a pas été pensé comme un canal mesurable. "
        "Et pendant ce temps, le budget Google Ads grimpe.\n\n"
        "J'aide des structures de votre taille à reprendre la main : tracking "
        "propre, conversion mesurée, et souvent une refonte ciblée qui fait "
        "baisser le CPL de 30 à 50 %.\n\n"
        "Vous avez 20 minutes la semaine prochaine pour qu'on regarde vos chiffres ?"
    ),
}

C_J4 = {
    "name":        "C — DAF/CFO · J+4",
    "description": "Repère concret CPL avant/après",
    "category":    "follow_up",
    "segment":     "C_DAF",
    "step":        "J+4",
    "subject":     "Re: Coût d'acquisition site web",
    "body_html":   H(
        "{{prenom}},\n\n"
        "Pour vous donner un repère concret avant notre échange éventuel : sur "
        "un client comparable, on est passé d'un CPL de 87 € (Google Ads) à un "
        "CPL de 24 € (organique + site refondu) en 6 mois. "
        "Investissement initial : 2 800 €. Payback : 4 mois.\n\n"
        "Je peux vous envoyer le calcul détaillé en 1 page ?"
    ),
}

C_J18 = {
    "name":        "C — DAF/CFO · J+18 (Breakup)",
    "description": "Breakup avec rappel ROI",
    "category":    "breakup",
    "segment":     "C_DAF",
    "step":        "J+18",
    "subject":     "Je vous laisse tranquille",
    "body_html":   H(
        "{{prenom}},\n\n"
        "Je n'insiste pas plus — je sais que la fin de trimestre est chargée "
        "côté DAF.\n\n"
        "Le calcul de ROI dont je parlais reste disponible. "
        "Si on peut en reparler dans 2-3 mois, c'est noté.\n\n"
        "Bon courage pour la clôture."
    ),
}


# ============================================================
# SEGMENT D — Marketing / Growth
# ============================================================

D_J0 = {
    "name":        "D — Marketing · J0",
    "description": "3 fuites de conversion identifiées",
    "category":    "cold_email",
    "segment":     "D_MARKETING",
    "step":        "J0",
    "subject":     "Conversion {{site_short}} — 3 fuites identifiées",
    "body_html":   H(
        "Bonjour {{prenom}},\n\n"
        "J'ai analysé le tunnel de conversion de {{site_short}} — 3 fuites "
        "visibles qui pèsent sur vos KPI :\n\n"
        "1. [À COMPLÉTER — fuite #1]<br>"
        "2. [À COMPLÉTER — fuite #2]<br>"
        "3. [À COMPLÉTER — fuite #3]\n\n"
        "Je dirige une agence qui se spécialise dans ces optimisations (post-Google "
        "Ads, post-LinkedIn Ads). Sur les sites qu'on refond, le taux de conversion "
        "progresse en moyenne de 1,8 % à 4,2 %.\n\n"
        "Vous avez 20 minutes pour qu'on en discute appliqué à {{entreprise}} ?"
    ),
}

D_J4 = {
    "name":        "D — Marketing · J+4",
    "description": "Before/After conversion",
    "category":    "follow_up",
    "segment":     "D_MARKETING",
    "step":        "J+4",
    "subject":     "Re: Conversion {{site_short}}",
    "body_html":   H(
        "{{prenom}},\n\n"
        "Pour donner du concret : le point #2 que je signalais, c'est exactement "
        "ce qu'on a corrigé chez un client similaire. Résultat : +47 % de "
        "soumissions de formulaire en 6 semaines, sans toucher au budget Ads.\n\n"
        "Si vous voulez le before/after et le détail technique (utile pour "
        "remonter à votre direction), je vous envoie en réponse ?"
    ),
}


# ============================================================
# GENERIC — Récap RDV / utilitaires
# ============================================================

RECAP_RDV2 = {
    "name":        "Récap post-call · RDV 2 calé",
    "description": "Email récap après call 1 quand RDV 2 calé",
    "category":    "rdv_recap",
    "segment":     "GENERIC",
    "step":        "custom",
    "subject":     "{{entreprise}} — récap de notre échange",
    "body_html":   H(
        "Bonjour {{prenom}},\n\n"
        "Comme convenu, voici un récap rapide :\n\n"
        "• Ce que j'ai compris de vos besoins : [À COMPLÉTER]<br>"
        "• Notre prochain RDV : [DATE/HEURE]<br>"
        "• Visuels à m'envoyer d'ici là : [LISTE]\n\n"
        "Je te prépare une maquette spécifique à {{entreprise}} d'ici notre prochaine séance.\n\n"
        "Pour confirmer le RDV : {{calendly}}"
    ),
}

ALL_TEMPLATES = [
    A_J0, A_J4, A_J10, A_J18,
    B_J0, B_J4, B_J10, B_J18,
    C_J0, C_J4, C_J18,
    D_J0, D_J4,
    RECAP_RDV2,
]


def seed(reset: bool = False):
    init_db()

    if reset:
        with cursor() as c:
            c.execute("DELETE FROM email_templates")
            c.execute("ALTER SEQUENCE email_templates_id_seq RESTART WITH 1")
        print("RESET : table email_templates vidée.")

    inserted = 0
    skipped = 0
    for tpl in ALL_TEMPLATES:
        # Check if already exists by name
        existing = query_one(
            "SELECT id FROM email_templates WHERE name = ?",
            (tpl["name"],),
        )
        if existing:
            skipped += 1
            print(f"  ↪  skip (existe déjà) : {tpl['name']}")
            continue

        create_template(
            name=tpl["name"], subject=tpl["subject"], body_html=tpl["body_html"],
            description=tpl.get("description", ""), category=tpl.get("category"),
            segment=tpl.get("segment"), step=tpl.get("step"),
        )
        inserted += 1
        print(f"  ✓  {tpl['name']}")

    print(f"\n=== Seed terminé ===")
    print(f"  Insérés  : {inserted}")
    print(f"  Skip     : {skipped}")
    print(f"  Total    : {len(ALL_TEMPLATES)}")


def main():
    parser = argparse.ArgumentParser(description="Seed email templates")
    parser.add_argument("--reset", action="store_true",
                        help="Vide la table avant seed (destructif)")
    args = parser.parse_args()

    if args.reset:
        ans = input("Reset complet email_templates ? [y/N] ").strip().lower()
        if ans != "y":
            print("Annulé.")
            return
    seed(reset=args.reset)


if __name__ == "__main__":
    main()
