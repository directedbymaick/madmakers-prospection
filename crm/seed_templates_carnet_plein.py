"""crm.seed_templates_carnet_plein — templates email pour Carnet Plein®
   (artisans BTP RGE en IDF/HDF/Grand Est).

   ⚠️ Ce script SUPPRIME tous les templates existants avant insert (--reset par défaut).

   Usage :
       python -X utf8 -m crm.seed_templates_carnet_plein              # reset + reload
       python -X utf8 -m crm.seed_templates_carnet_plein --keep       # garde l'existant, ajoute juste
"""
import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from .db import init_db, cursor, query_one
from .models import create_template


# ── Signature Carnet Plein ─────────────────────────────────────
SIG = (
    "<br><br>"
    "<b>{{user_prenom}}</b><br>"
    "Carnet Plein® — Système d'acquisition pour artisans certifiés RGE<br>"
    '<a href="https://carnetplein.mad-makers.fr">carnetplein.mad-makers.fr</a> · '
    '<a href="{{calendly}}">Audit gratuit 20 min</a>'
)


def H(text: str) -> str:
    """Convertit texte plain (avec \\n\\n paragraphes) en HTML <p>."""
    paras = text.strip().split("\n\n")
    html = "".join(f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paras if p.strip())
    return html + SIG


SEG = "F_ARTISAN_BTP_RGE"


# =============================================================
# J0 — Premier contact (4 angles d'attaque)
# =============================================================

J0_CARNET = {
    "name":        "Carnet Plein · J0 · Angle carnet vide",
    "description": "Premier contact — angle saisonnalité / carnet en dents-de-scie",
    "category":    "cold_email",
    "segment":     SEG,
    "step":        "J0",
    "subject":     "{{entreprise}} — vos chantiers en {{ville}} ?",
    "body_html":   H(
        "Bonjour {{prenom}},\n\n"
        "Question pas marketing : combien de chantiers fermes pour {{entreprise}} sur les 2 prochains mois ?\n\n"
        "Si la réponse vous donne envie de pleurer (la majorité des plombiers RGE qu'on rencontre nous disent <5 fermes en H1), c'est pas votre faute. Le bouche-à-oreille et un site fantôme, c'est pas un système — c'est de la roulette russe.\n\n"
        "Nous on fournit un **système d'acquisition de chantiers** clés en main aux artisans RGE en {{ville}} et région. Site + Google + avis + reporting + cohort coaching. **Tarif public** : 5 000 € + 800 €/mois. **Garantie écrite** : si on n'atteint pas 80% de l'objectif à 12 mois, on continue gratuitement jusqu'à 6 mois.\n\n"
        "20 min en visio pour voir si ça matche {{entreprise}} ? {{calendly}}"
    ),
}

J0_GBP = {
    "name":        "Carnet Plein · J0 · Angle Google invisible",
    "description": "Premier contact — angle GBP / Local Pack page 4",
    "category":    "cold_email",
    "segment":     SEG,
    "step":        "J0",
    "subject":     "{{entreprise}} sur Google — page 4 ou page 1 ?",
    "body_html":   H(
        "Bonjour {{prenom}},\n\n"
        "J'ai tapé « plombier RGE {{ville}} » sur Google ce matin. {{entreprise}} apparaît [À COMPLÉTER — page X]. Vos confrères sur le Local Pack récupèrent <b>80 % des leads</b> de la zone — c'est mécanique.\n\n"
        "3 trucs qui font basculer une fiche de page 4 à top 3 :\n"
        "1. Fiche Google Business Profile renseignée à 100% (catégories, services, photos hebdo)\n"
        "2. Avis clients automatisés par SMS post-chantier\n"
        "3. Pages géolocalisées sur votre site (1 page = 1 commune)\n\n"
        "C'est ce qu'on fait pour ~30 plombiers RGE en cohort. Tarif public 5 000 € + 800/mois, <b>garantie 80% KPI sinon on continue gratos</b>.\n\n"
        "Audit gratuit 20 min : {{calendly}}"
    ),
}

J0_LEAD_MAGNET = {
    "name":        "Carnet Plein · J0 · Angle PDF bonus (réciprocité)",
    "description": "Cold soft — offre directe d'un PDF Fiche Google Parfaite, sans pitch",
    "category":    "cold_email",
    "segment":     SEG,
    "step":        "J0",
    "subject":     "Cadeau pour {{entreprise}} (60 secondes max)",
    "body_html":   H(
        "Bonjour {{prenom}},\n\n"
        "Vous êtes sur chantier 8h+/jour, je vais être bref.\n\n"
        "J'ai un PDF <b>« Fiche Google Parfaite — 12 points concrets »</b> que j'envoie aux artisans RGE qui m'écrivent. C'est ce que je fais payer à mes clients Carnet Plein® — je vous le donne gratuit.\n\n"
        "Avec 12 ajustements de votre GBP (15 min de boulot), vous remontez en moyenne de 4 à 7 places sur Google. Suffisant pour ramener 2-3 demandes de devis en plus par mois.\n\n"
        "Je vous l'envoie ? Répondez juste <b>« OK »</b> à ce mail."
    ),
}

J0_GARANTIE = {
    "name":        "Carnet Plein · J0 · Angle garantie d'abord (Hormozi)",
    "description": "Cold — mettre la garantie en avant tout de suite pour lever la méfiance",
    "category":    "cold_email",
    "segment":     SEG,
    "step":        "J0",
    "subject":     "Si on vous trouvait pas de chantier, on continuerait gratuit",
    "body_html":   H(
        "Bonjour {{prenom}},\n\n"
        "Vous avez sûrement déjà entendu :<br>"
        "« Donnez-nous 3 000 € et on vous fait un site génial. »<br>"
        "Et 6 mois plus tard : zéro chantier en plus.\n\n"
        "Chez Carnet Plein®, on a écrit la garantie suivante en clair dans le contrat (article 1231-1 du Code civil) :\n\n"
        "👉 <b>Si à 12 mois on n'a pas atteint au moins 80 % de votre objectif chantiers, on continue gratuitement jusqu'à 6 mois supplémentaires.</b>\n\n"
        "Pas de petites lignes. Pas de \"sauf si\". On a le couteau sous la gorge, et c'est précisément pour ça que les 30 artisans RGE qu'on accompagne nous font confiance.\n\n"
        "Audit gratuit 20 min pour voir si {{entreprise}} matche : {{calendly}}\n\n"
        "(On ne prend que 3 nouveaux artisans par mois — pour qu'on puisse vraiment livrer.)"
    ),
}


# =============================================================
# J+4 — Relance 1
# =============================================================

J4_CAS_CLIENT = {
    "name":        "Carnet Plein · J+4 · Cas client chiffré",
    "description": "Relance 1 — preuve sociale d'un artisan similaire",
    "category":    "follow_up",
    "segment":     SEG,
    "step":        "J+4",
    "subject":     "Re: {{entreprise}} — chantiers en {{ville}}",
    "body_html":   H(
        "{{prenom}},\n\n"
        "Petit suivi de mon mail précédent.\n\n"
        "Pour vous donner du concret : <b>[À COMPLÉTER — Prénom Nom du cas client]</b>, plombier RGE comme vous dans [VILLE], 4 salariés. Avant Carnet Plein® :\n"
        "• 3-5 leads/mois via bouche-à-oreille\n"
        "• Page 4 sur Google « plombier [VILLE] »\n"
        "• 0 avis Google\n\n"
        "Après 90 jours avec nous :\n"
        "• <b>14 leads/mois entrants</b> (Google + GBP)\n"
        "• Page 1, Local Pack position 3\n"
        "• <b>23 avis Google 4,9 / 5</b> (SMS auto post-chantier)\n\n"
        "Le déroulé complet en 1 page A4, je peux vous l'envoyer. Répondez « cas client » et je l'attache."
    ),
}

J4_PDF_BONUS = {
    "name":        "Carnet Plein · J+4 · Envoi PDF bonus comme relance",
    "description": "Relance 1 — réciprocité, sans pitch direct",
    "category":    "follow_up",
    "segment":     SEG,
    "step":        "J+4",
    "subject":     "PDF pour {{entreprise}} — sans pitch",
    "body_html":   H(
        "{{prenom}},\n\n"
        "Comme promis, je vous laisse le PDF « Fiche Google Parfaite ».\n\n"
        "[À COMPLÉTER — joindre le PDF en pièce jointe au moment de l'envoi]\n\n"
        "12 points qui prennent 15 min à appliquer. Pas de blabla, juste la checklist exacte.\n\n"
        "Si après l'avoir lu, vous vous dites « OK ça serait bien que quelqu'un me fasse ça <i>plus</i> tout le reste (avis, copywriting, reporting, site SEO local) », on peut en parler 20 min : {{calendly}}\n\n"
        "Sinon, gardez le PDF, ça vaut son poids. Aucune relance derrière."
    ),
}

J4_QUESTION_DIRECTE = {
    "name":        "Carnet Plein · J+4 · Question directe",
    "description": "Relance 1 — question fermée pour forcer une réponse",
    "category":    "follow_up",
    "segment":     SEG,
    "step":        "J+4",
    "subject":     "Re: {{entreprise}} — 1 question",
    "body_html":   H(
        "{{prenom}},\n\n"
        "Je sais que vous êtes occupé, donc 1 seule question :\n\n"
        "<b>Pour {{entreprise}}, l'acquisition de nouveaux chantiers c'est :</b><br>"
        "A) Un problème — j'ai besoin de plus de leads<br>"
        "B) Ça va, le bouche-à-oreille suffit pour l'instant<br>"
        "C) Pas le moment d'y penser<br>\n\n"
        "Une lettre, un mail. Je vous laisse tranquille selon la réponse."
    ),
}


# =============================================================
# J+10 — Relance 2
# =============================================================

J10_COHORT = {
    "name":        "Carnet Plein · J+10 · Cohort qui se ferme (scarcité)",
    "description": "Relance 2 — urgence de la cohort mensuelle 3 places max",
    "category":    "follow_up",
    "segment":     SEG,
    "step":        "J+10",
    "subject":     "{{entreprise}} — cohort de [MOIS] : 1 place restante",
    "body_html":   H(
        "{{prenom}},\n\n"
        "Petite info : on accepte <b>3 artisans RGE par mois</b> dans Carnet Plein®. Pas une de plus, pour qu'on puisse vraiment tenir les délais et la qualité.\n\n"
        "La cohort de [À COMPLÉTER — mois] est ouverte, il reste <b>1 place</b>. Si je ne reçois pas un signe de votre part avant [DATE], elle part au prochain candidat sur ma liste — la suivante c'est dans 30 jours.\n\n"
        "Je ne vous force pas la main. Si vous savez déjà que ce n'est pas le bon timing, dites « pas maintenant » et je vous écris en [MOIS+1].\n\n"
        "Si au contraire le sujet redevient prioritaire pour {{entreprise}}, audit 20 min ici : {{calendly}}"
    ),
}

J10_PRIX = {
    "name":        "Carnet Plein · J+10 · Levée d'objection prix",
    "description": "Relance 2 — ROI sur le tarif 5k + 800/mois",
    "category":    "follow_up",
    "segment":     SEG,
    "step":        "J+10",
    "subject":     "13 800 € sur 12 mois — beaucoup ou pas tant que ça ?",
    "body_html":   H(
        "{{prenom}},\n\n"
        "Je vais être franc sur le tarif Carnet Plein® : <b>5 000 € setup + 800 €/mois × 11 = 13 800 € HT sur l'année</b>.\n\n"
        "Question retournée : votre <b>marge moyenne par chantier</b> chez {{entreprise}}, c'est combien ?\n\n"
        "Disons 800 € (chiffre conservateur sur un dépannage + intervention). Si Carnet Plein® vous ramène <b>2 chantiers de plus par mois</b> sur 12 mois → 24 chantiers × 800 € = <b>19 200 € de marge supplémentaire</b>. ROI net : +5 400 € minimum.\n\n"
        "Et si on rate cet objectif, vous avez la garantie 80% KPI — on continue gratos.\n\n"
        "Vous voulez qu'on fasse le calcul ensemble pour VOS chiffres ? 20 min : {{calendly}}"
    ),
}

J10_STORY = {
    "name":        "Carnet Plein · J+10 · Storytelling artisan terrain",
    "description": "Relance 2 — récit émotionnel + technique",
    "category":    "follow_up",
    "segment":     SEG,
    "step":        "J+10",
    "subject":     "Pourquoi on fait Carnet Plein® uniquement pour artisans",
    "body_html":   H(
        "{{prenom}},\n\n"
        "Je vous raconte vite pourquoi on a créé Carnet Plein® :\n\n"
        "Il y a 6 mois, un plombier de Pontoise m'appelle. 22 ans de métier, RGE, du boulot bien fait. Mais en juin il a 4 chantiers fermes pour septembre. Il m'explique : « Les bons artisans, on connaît le métier, pas le marketing. Et les agences web qu'on a essayées, c'est 3 000 € pour un joli site qui fait rien ». Il avait pas tort.\n\n"
        "Du coup on a productisé : <b>site SEO local + GBP + avis + reporting + cohort entre artisans, prix public, garantie écrite</b>. Pas de \"on en parle, on chiffre\". Tout est cadré.\n\n"
        "Aujourd'hui ce plombier de Pontoise est passé de 5 à 14 leads/mois. Il vient de signer pour 12 mois supplémentaires.\n\n"
        "Si {{entreprise}} est dans la même situation, on peut en parler : {{calendly}}"
    ),
}


# =============================================================
# J+18 — Breakup
# =============================================================

J18_BREAKUP = {
    "name":        "Carnet Plein · J+18 · Breakup classique",
    "description": "Dernier mail — laisser la porte ouverte sans relancer",
    "category":    "breakup",
    "segment":     SEG,
    "step":        "J+18",
    "subject":     "Dernier message pour {{entreprise}}",
    "body_html":   H(
        "{{prenom}},\n\n"
        "Promis, dernier mail — pas envie d'être lourd.\n\n"
        "Si Carnet Plein® n'est pas le bon truc pour {{entreprise}} en ce moment, c'est ok. Le bouche-à-oreille fonctionne pour beaucoup d'artisans, et tant que ça tourne, c'est très bien.\n\n"
        "Si dans 3 ou 6 mois ça redevient prioritaire (ralentissement, départ d'un commercial, agrandissement de l'équipe...) : {{calendly}}\n\n"
        "Bonne suite à {{entreprise}}."
    ),
}

J18_BRIDGE = {
    "name":        "Carnet Plein · J+18 · Breakup + cadeau PDF",
    "description": "Dernier mail — offre le PDF gratuit comme cadeau de départ",
    "category":    "breakup",
    "segment":     SEG,
    "step":        "J+18",
    "subject":     "Je vous laisse tranquille — petit cadeau avant",
    "body_html":   H(
        "{{prenom}},\n\n"
        "OK, je n'insiste plus.\n\n"
        "Avant de vous laisser tranquille, je vous joins quand même le PDF <b>« Devis qui Close à 70% »</b>. C'est 4 leviers psychologiques que mes clients Carnet Plein® utilisent pour passer leur taux de signature de 30-40% à 65-75%.\n\n"
        "[À COMPLÉTER — joindre le PDF Devis 70%]\n\n"
        "Pas de relance après ça. Si vous voulez bosser ensemble un jour, vous savez où me trouver : {{calendly}}\n\n"
        "Bonne continuation."
    ),
}


# =============================================================
# Utilitaires (post-audit, signature, kick-off)
# =============================================================

POST_AUDIT = {
    "name":        "Carnet Plein · Post-audit · Récap + devis",
    "description": "Email envoyé 1-3j après l'audit Calendly visio 20 min",
    "category":    "rdv_recap",
    "segment":     SEG,
    "step":        "custom",
    "subject":     "Récap de notre audit + devis Carnet Plein® pour {{entreprise}}",
    "body_html":   H(
        "Bonjour {{prenom}},\n\n"
        "Merci pour le temps qu'on a passé ensemble [À COMPLÉTER — jour]. Voici ce que je retiens de l'audit pour {{entreprise}} :\n\n"
        "<b>3 axes prioritaires identifiés :</b>\n"
        "1. [À COMPLÉTER — axe 1, ex: GBP catégories incomplètes, manque 5 points]\n"
        "2. [À COMPLÉTER — axe 2, ex: Site sans pages géolocalisées, 0 chance Local Pack]\n"
        "3. [À COMPLÉTER — axe 3, ex: Aucun avis Google récent, frein conversion]\n\n"
        "<b>Objectif que je vous propose pour 12 mois :</b> [À COMPLÉTER — ex: passer de 5 à 15 leads/mois]\n\n"
        "Le devis Carnet Plein® Intégral est en pièce jointe (5 000 € setup + 800 €/mois × 11, paiement 3× sans frais, garantie 80% KPI écrite).\n\n"
        "Le contrat est en pièce jointe aussi. Cohort de [MOIS] : il reste [X] places. Si vous validez, signature Yousign dans la foulée.\n\n"
        "Une question avant signature ? Répondez ici ou rappel express : {{calendly}}"
    ),
}

POST_SIGNATURE = {
    "name":        "Carnet Plein · Post-signature · Bienvenue",
    "description": "Email auto envoyé à la signature Yousign + acompte payé",
    "category":    "rdv_recap",
    "segment":     SEG,
    "step":        "custom",
    "subject":     "Bienvenue dans Carnet Plein® {{entreprise}} 🎯",
    "body_html":   H(
        "{{prenom}},\n\n"
        "On vient de recevoir votre signature + acompte. <b>Bienvenue dans la cohort de [À COMPLÉTER — mois].</b>\n\n"
        "<b>Ce qui se passe maintenant :</b>\n"
        "• <b>D+1</b> : je vous envoie le questionnaire pré-kick-off (15 min à remplir)\n"
        "• <b>D+7</b> : kick-off groupé en visio avec les 2 autres artisans de la cohort (60 min, 9h)\n"
        "• <b>D+14</b> : GO LIVE — site + GBP + système avis fonctionnels\n"
        "• <b>M+1 → M+12</b> : reporting le 5 de chaque mois + call stratégique 30 min\n\n"
        "Le groupe WhatsApp privé de la cohort vient d'être créé, je vous y ajoute aujourd'hui.\n\n"
        "Question d'ici là ? Répondez à ce mail."
    ),
}

KICKOFF_J7 = {
    "name":        "Carnet Plein · Kick-off J+7 · Convocation",
    "description": "Rappel 24h avant le kick-off groupé visio 60 min",
    "category":    "rdv_recap",
    "segment":     SEG,
    "step":        "custom",
    "subject":     "Kick-off Carnet Plein® demain 9h — {{entreprise}}",
    "body_html":   H(
        "{{prenom}},\n\n"
        "Demain à 9h on lance officiellement votre cohort. Visio 60 min avec les 2 autres artisans RGE qui ont signé en même temps que vous.\n\n"
        "<b>Lien visio :</b> [À COMPLÉTER — lien Meet/Zoom]\n\n"
        "<b>Au programme :</b>\n"
        "1. Présentations express (5 min × 3 artisans)\n"
        "2. Restitution audits individuels (30 min)\n"
        "3. Plan de production J+1 → J+14 par artisan (15 min)\n"
        "4. Q&A + setup WhatsApp groupe (10 min)\n\n"
        "À avoir prêt :<br>"
        "• Vos accès Google Business Profile (mail+mot de passe — on va modifier 12 points)<br>"
        "• 5-10 photos chantiers HD si vous en avez (sinon on prend smartphone)<br>"
        "• Un café fort\n\n"
        "À demain {{prenom}}."
    ),
}


# ── Liste finale ──────────────────────────────────────────────

ALL_TEMPLATES = [
    # J0
    J0_CARNET, J0_GBP, J0_LEAD_MAGNET, J0_GARANTIE,
    # J+4
    J4_CAS_CLIENT, J4_PDF_BONUS, J4_QUESTION_DIRECTE,
    # J+10
    J10_COHORT, J10_PRIX, J10_STORY,
    # J+18
    J18_BREAKUP, J18_BRIDGE,
    # Utilitaires
    POST_AUDIT, POST_SIGNATURE, KICKOFF_J7,
]


# ── Seed runner ──────────────────────────────────────────────


def seed(reset: bool = True):
    init_db()

    if reset:
        with cursor() as c:
            c.execute("DELETE FROM email_templates")
            c.execute("ALTER SEQUENCE email_templates_id_seq RESTART WITH 1")
        print("RESET : table email_templates vidée.")

    inserted = 0
    skipped = 0
    for tpl in ALL_TEMPLATES:
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

    print(f"\n=== Seed Carnet Plein® terminé ===")
    print(f"  Insérés  : {inserted}")
    print(f"  Skip     : {skipped}")
    print(f"  Total    : {len(ALL_TEMPLATES)}")


def main():
    parser = argparse.ArgumentParser(description="Seed templates Carnet Plein® artisans BTP RGE")
    parser.add_argument("--keep", action="store_true",
                        help="Garde les templates existants (ne fait qu'ajouter)")
    args = parser.parse_args()

    reset = not args.keep
    if reset:
        ans = input("Supprimer TOUS les templates existants ET seed Carnet Plein® ? [y/N] ").strip().lower()
        if ans != "y":
            print("Annulé.")
            return
    seed(reset=reset)


if __name__ == "__main__":
    main()
