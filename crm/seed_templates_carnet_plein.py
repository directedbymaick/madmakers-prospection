"""crm.seed_templates_carnet_plein — 15 templates email Carnet Plein®
   pour la cohorte Vague Pilote 2026 (artisans BTP RGE en IDF / HDF / Grand Est).

   ⚠️ Ce script SUPPRIME tous les templates existants avant insert (--reset par défaut).

   Tous les templates intègrent l'offre fondateur :
     • Tarif Vague Pilote : 1 500 € HT setup + 250 € HT/mois × 12 mois (vs 5 000 + 800)
     • Garantie 80% KPI sinon on continue gratis
     • 5 places ouvertes, fermeture une fois remplies
     • Founder's case Mad Makers (on mange notre propre cuisine, dashboard public)

   Style : HTML "plain-text-look" — pas de boutons stylisés, pas d'images, une seule
   font, max 580px de large. C'est ce qui passe l'onglet Promotions de Gmail et
   conserve l'illusion "lettre du fondateur".

   Usage :
       python -X utf8 -m crm.seed_templates_carnet_plein            # reset + reload
       python -X utf8 -m crm.seed_templates_carnet_plein --keep     # ajoute seulement
"""
import argparse
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from .db import init_db, cursor, query_one
from .models import create_template


SEG = "F_ARTISAN_BTP_RGE"


# ── Signature plain-text-look ─────────────────────────────────
SIG = (
    "<p>À très vite,<br>"
    "{{user_prenom}}<br>"
    "Fondateur Mad Makers · Carnet Plein®<br>"
    '<a href="mailto:{{user_email}}" style="color:#0066cc;">{{user_email}}</a></p>'
)


def H(text: str) -> str:
    """Convertit du texte plain (paragraphes séparés par \\n\\n, sauts de ligne par \\n)
    en HTML plain-text-look (sans-serif, max 580px, signature ajoutée)."""
    paras = text.strip().split("\n\n")
    body = "".join(
        f"<p>{p.replace(chr(10), '<br>')}</p>"
        for p in paras if p.strip()
    )
    return (
        '<div style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\','
        'Roboto,Arial,sans-serif;font-size:15px;line-height:1.55;color:#1a1a1a;'
        'max-width:580px;">'
        + body + SIG +
        '</div>'
    )


# =============================================================
# J0 — Premier contact (4 angles d'attaque pour A/B testing)
# =============================================================

J0_PILOTE_EXPLICATION = {
    "name":        "Carnet Plein · J0 · Vague Pilote — explication (principal)",
    "description": "Premier contact — angle direct lettre du fondateur, offre fondateur transparente",
    "category":    "cold_email",
    "segment":     SEG,
    "step":        "J0",
    "subject":     "Une offre fondateur pour 5 chauffagistes RGE — explication",
    "body_html":   H(
        "Bonjour {{prenom}},\n\n"
        "Je vais être direct : 9 artisans RGE sur 10 que je vois passer ont exactement le même problème — leur prospection dépend du bouche-à-oreille local et de quelques chantiers MaPrimeRénov' qui arrivent par hasard. Quand le hasard ralentit, le carnet se vide.\n\n"
        "Ce qu'on fait chez Mad Makers : un système d'acquisition complet pour artisans RGE. Selon votre situation de départ — refonte de site existant, création from scratch ou simple optimisation — plus Google Business Profile, avis clients automatisés et campagne d'acquisition ciblée IDF / HDF / Grand Est. Un seul objectif contractuel : remplir votre carnet sur 12 mois.\n\n"
        "Le hic honnête : nous démarrons Carnet Plein® cette année. Nous n'avons pas encore d'études de cas chiffrées sur des artisans RGE. Donc plutôt que d'en inventer, on a fait l'inverse — une <strong>offre fondateur volontairement sacrifiée pour 5 artisans</strong> qui acceptent d'être documentés publiquement (nom, ville, chiffres, vidéo à M+3 / M+6 / M+12).\n\n"
        "L'offre <strong>Vague Pilote 2026</strong> :\n"
        "• 1 500 € HT setup (au lieu de 5 000 €)\n"
        "• 250 € HT / mois pendant 12 mois (au lieu de 800 €)\n"
        "• Soit 4 500 € HT sur 12 mois — <strong>67 % de remise</strong> sur le tarif standard\n"
        "• Garantie écrite : si à 12 mois vous n'avez pas atteint 80 % de l'objectif convenu, on continue à travailler sans facturer\n"
        "• <strong>5 places ouvertes</strong>. Fermeture une fois remplies.\n\n"
        "Pour montrer qu'on mange notre propre cuisine, on documente publiquement l'application de la méthode à Mad Makers lui-même — chiffres mis à jour le 1<sup>er</sup> de chaque mois sur <a href=\"https://carnetplein.mad-makers.fr/methodologie-mad-makers\" style=\"color:#0066cc;\">carnetplein.mad-makers.fr/methodologie-mad-makers</a>.\n\n"
        "Si vous voulez en discuter sans engagement, je bloque 30 minutes avec vous — audit gratuit de votre situation actuelle, et si l'une des 5 places vous intéresse, on signe. Sinon vous repartez avec l'audit, gracieusement.\n\n"
        "Réservez ici : <a href=\"{{calendly}}\" style=\"color:#0066cc;\">{{calendly}}</a>"
    ),
}

J0_CARNET = {
    "name":        "Carnet Plein · J0 · Angle carnet vide",
    "description": "Premier contact — angle saisonnalité / carnet en dents-de-scie",
    "category":    "cold_email",
    "segment":     SEG,
    "step":        "J0",
    "subject":     "{{entreprise}} — vos 2 prochains mois en {{ville}} ?",
    "body_html":   H(
        "Bonjour {{prenom}},\n\n"
        "Question pas marketing : combien de chantiers fermes pour {{entreprise}} sur les 2 prochains mois ?\n\n"
        "Si la réponse vous donne envie de pleurer (la majorité des plombiers RGE qu'on rencontre nous disent moins de 5 fermes en H1), c'est pas votre faute. Le bouche-à-oreille et un site fantôme, c'est pas un système — c'est de la roulette russe.\n\n"
        "Nous on fournit un système d'acquisition de chantiers clés en main aux artisans RGE en {{ville}} et région. Site + Google + avis + reporting + cohort coaching.\n\n"
        "On vient de lancer la <strong>Vague Pilote 2026</strong> : 1 500 € HT setup + 250 € HT/mois sur 12 mois (au lieu de 5 000 + 800), en échange d'un droit de communication publique sur les résultats. <strong>5 places, ouvertes maintenant.</strong>\n\n"
        "Garantie écrite : si à 12 mois on n'a pas atteint 80 % de l'objectif, on continue gratuitement.\n\n"
        "20 min en visio pour voir si ça matche {{entreprise}} ? <a href=\"{{calendly}}\" style=\"color:#0066cc;\">{{calendly}}</a>"
    ),
}

J0_GBP = {
    "name":        "Carnet Plein · J0 · Angle Google invisible",
    "description": "Premier contact — angle Local Pack / SEO local",
    "category":    "cold_email",
    "segment":     SEG,
    "step":        "J0",
    "subject":     "{{entreprise}} sur Google — vraiment visible ?",
    "body_html":   H(
        "Bonjour {{prenom}},\n\n"
        "Quand un particulier de {{ville}} tape « plombier RGE » ou « pompe à chaleur » sur Google, les 3 fiches du Local Pack récupèrent <strong>80 % des leads</strong> de la zone. C'est mécanique.\n\n"
        "3 leviers qui font basculer une fiche de page 4 à top 3 :\n"
        "1. Fiche Google Business Profile à 100 % (catégories, services, photos hebdo)\n"
        "2. Avis clients automatisés par SMS post-chantier\n"
        "3. Pages géolocalisées sur votre site (1 page = 1 commune)\n\n"
        "C'est exactement ce qu'on fait pour les artisans RGE qu'on accompagne. On vient de lancer la <strong>Vague Pilote 2026</strong> — 5 places à tarif fondateur (1 500 € + 250 €/mois sur 12 mois au lieu de 5 000 + 800), en échange d'un droit de communication sur les résultats.\n\n"
        "Garantie écrite : 80 % de l'objectif à 12 mois sinon on continue gratis.\n\n"
        "Audit gratuit 20 min de votre présence locale : <a href=\"{{calendly}}\" style=\"color:#0066cc;\">{{calendly}}</a>"
    ),
}

J0_GARANTIE = {
    "name":        "Carnet Plein · J0 · Angle garantie d'abord (Hormozi)",
    "description": "Premier contact — angle risk reversal en accroche",
    "category":    "cold_email",
    "segment":     SEG,
    "step":        "J0",
    "subject":     "Si on vous trouvait pas de chantier, on continuerait gratis",
    "body_html":   H(
        "Bonjour {{prenom}},\n\n"
        "Vous avez sûrement déjà entendu : « Donnez-nous 3 000 € et on vous fait un site génial. » Six mois plus tard, zéro chantier en plus. C'est exactement pour ça que je vous écris.\n\n"
        "Chez Carnet Plein®, on assume une <strong>garantie écrite</strong> : si à 12 mois on n'a pas atteint 80 % de l'objectif convenu sur signature, on continue à travailler sans facturer. Pas d'avenant, pas de pirouette, pas d'astérisque.\n\n"
        "Concrètement, l'offre fondateur <strong>Vague Pilote 2026</strong> :\n"
        "• 1 500 € HT setup (vs 5 000 € en standard)\n"
        "• 250 € HT/mois pendant 12 mois (vs 800)\n"
        "• Soit 4 500 € HT sur 12 mois, garantie 80 % KPI incluse\n"
        "• <strong>5 places ouvertes</strong>, contrepartie : droit de communication publique sur les résultats\n\n"
        "L'offre est sacrifiée parce qu'on démarre la méthode sur l'écosystème RGE et qu'on préfère 5 vraies études de cas chiffrées à 5 témoignages bidons. Honnêteté radicale plutôt que faux social proof.\n\n"
        "20 min sans engagement pour voir si {{entreprise}} matche : <a href=\"{{calendly}}\" style=\"color:#0066cc;\">{{calendly}}</a>"
    ),
}


# =============================================================
# J+4 — Relance 1 (offre toujours dispo, ajoute valeur)
# =============================================================

J4_QUESTION_DIRECTE = {
    "name":        "Carnet Plein · J+4 · Question directe",
    "description": "Relance courte avec 1 question oui/non",
    "category":    "follow_up",
    "segment":     SEG,
    "step":        "J+4",
    "subject":     "Re: {{entreprise}} — 1 question",
    "body_html":   H(
        "{{prenom}},\n\n"
        "Je sais que vous êtes sur chantier, donc une seule question :\n\n"
        "Pour {{entreprise}}, l'acquisition de nouveaux chantiers, c'est :\n"
        "A) Un problème — j'aimerais plus de leads, fiables, sans dépendre du bouche-à-oreille\n"
        "B) Pas un problème — le carnet est plein 12 mois d'avance\n"
        "C) Pas la priorité maintenant — on regardera plus tard\n\n"
        "Si A, je vous propose 20 min en visio pour discuter de la <strong>Vague Pilote 2026</strong> (5 places à 1 500 € + 250 €/mois sur 12 mois, garantie 80 % KPI) : <a href=\"{{calendly}}\" style=\"color:#0066cc;\">{{calendly}}</a>\n\n"
        "Si B ou C, répondez juste « B » ou « C », je vous raie de ma liste sans relancer."
    ),
}

J4_FOUNDERS_CASE = {
    "name":        "Carnet Plein · J+4 · Founder's case Mad Makers",
    "description": "Relance — partage chiffres réels du founder's case",
    "category":    "follow_up",
    "segment":     SEG,
    "step":        "J+4",
    "subject":     "Re: {{entreprise}} — comment je mange ma propre cuisine",
    "body_html":   H(
        "{{prenom}},\n\n"
        "Petit suivi de mon message précédent. Vous avez peut-être eu envie de me dire : « OK c'est joli sur le papier, mais ça marche vraiment ? »\n\n"
        "Réponse honnête : je n'ai pas encore 5 études de cas chiffrées sur des artisans RGE — c'est la raison de la <strong>Vague Pilote 2026</strong>.\n\n"
        "Mais ce que je peux montrer, c'est qu'on applique la même méthode à Mad Makers lui-même. Tous les chiffres réels de notre prospection (sourcing, taux d'ouverture, RDV pris, contrats signés) sont mis à jour le 1<sup>er</sup> de chaque mois sur :\n\n"
        "<a href=\"https://carnetplein.mad-makers.fr/methodologie-mad-makers\" style=\"color:#0066cc;\">carnetplein.mad-makers.fr/methodologie-mad-makers</a>\n\n"
        "C'est public, daté, et personne ne peut faire semblant.\n\n"
        "Si ces chiffres vous parlent — et que vous avez envie de voir comment on transposerait à {{entreprise}} en {{ville}} — 20 minutes en visio, sans engagement :\n\n"
        "<a href=\"{{calendly}}\" style=\"color:#0066cc;\">{{calendly}}</a>"
    ),
}

J4_PDF_BONUS = {
    "name":        "Carnet Plein · J+4 · Envoi PDF checklist",
    "description": "Relance — envoie un PDF utile en valeur pure (réciprocité Cialdini)",
    "category":    "follow_up",
    "segment":     SEG,
    "step":        "J+4",
    "subject":     "PDF pour {{entreprise}} — sans pitch",
    "body_html":   H(
        "{{prenom}},\n\n"
        "Comme promis, je vous laisse la checklist <strong>« 12 points : votre site convertit-il un client RGE ? »</strong> que j'envoie aux artisans qui prennent 30 secondes pour me répondre.\n\n"
        "Lien direct (sans formulaire ni inscription) : <a href=\"https://carnetplein.mad-makers.fr/checklist\" style=\"color:#0066cc;\">carnetplein.mad-makers.fr/checklist</a>\n\n"
        "12 points qui prennent 15 minutes à appliquer sur votre site existant. Aucun produit à acheter pour les mettre en œuvre.\n\n"
        "Si après lecture vous voulez qu'on regarde ensemble votre site comme cas concret, j'ai 20 min pour vous — la <strong>Vague Pilote 2026</strong> est encore ouverte (5 places à 1 500 € + 250 €/mois, garantie 80 % KPI).\n\n"
        "<a href=\"{{calendly}}\" style=\"color:#0066cc;\">{{calendly}}</a>\n\n"
        "Sinon : profitez de la checklist, et bonne semaine en chantier."
    ),
}


# =============================================================
# J+10 — Relance 2 (scarcity, levée d'objection)
# =============================================================

J10_COHORT = {
    "name":        "Carnet Plein · J+10 · Places restantes (scarcity)",
    "description": "Relance — rappel scarcity réelle sur la Vague Pilote",
    "category":    "follow_up",
    "segment":     SEG,
    "step":        "J+10",
    "subject":     "{{entreprise}} — Vague Pilote ferme bientôt",
    "body_html":   H(
        "{{prenom}},\n\n"
        "Petite info : la <strong>Vague Pilote 2026</strong> a 5 places et on en a déjà bloqué quelques-unes. Le compteur à jour est ici : <a href=\"https://carnetplein.mad-makers.fr/vague-pilote\" style=\"color:#0066cc;\">carnetplein.mad-makers.fr/vague-pilote</a>\n\n"
        "Pour rappel, à 1 500 € HT + 250 €/mois sur 12 mois (vs 5 000 + 800 en standard), avec garantie 80 % KPI, c'est <strong>67 % de remise</strong> contre un seul engagement de votre côté : qu'on puisse documenter publiquement les résultats à M+3 / M+6 / M+12. Nom, ville, chiffres, vidéo.\n\n"
        "Une fois les 5 places fermées, on bascule sur tarif standard et on rouvre une vague seulement après avoir publié les 5 études de cas — probablement Q3 / Q4 2026.\n\n"
        "Si {{entreprise}} fait partie des candidats sérieux, 20 min en visio avant que ça parte :\n\n"
        "<a href=\"{{calendly}}\" style=\"color:#0066cc;\">{{calendly}}</a>"
    ),
}

J10_PRIX = {
    "name":        "Carnet Plein · J+10 · Levée d'objection prix",
    "description": "Relance — démonte l'objection ROI sur le tarif Vague Pilote",
    "category":    "follow_up",
    "segment":     SEG,
    "step":        "J+10",
    "subject":     "4 500 € sur 12 mois — beaucoup ou pas tant que ça ?",
    "body_html":   H(
        "{{prenom}},\n\n"
        "Je vais être franc sur le tarif Vague Pilote 2026 : <strong>1 500 € HT setup + 250 €/mois × 12 = 4 500 € HT sur l'année</strong>.\n\n"
        "Question retournée : quelle est votre <strong>marge moyenne par chantier</strong> ? Pour un plombier RGE sur PAC ou chaudière condensation, on est généralement entre 1 500 et 4 000 € de marge par chantier.\n\n"
        "Si on génère 2 chantiers en plus sur l'année grâce au système, c'est rentabilisé. L'objectif contractuel qu'on convient sur signature est largement au-dessus.\n\n"
        "Et si on n'y arrive pas — si à 12 mois on n'a pas atteint 80 % de cet objectif — on continue à bosser sans facturer jusqu'à 6 mois. C'est dans le contrat, pas un argument de vente.\n\n"
        "Comparaison utile :\n"
        "• Carnet Plein® Vague Pilote : 4 500 € HT / an, garantie 80 % KPI\n"
        "• Tarif standard (à partir de septembre) : 13 800 € HT / an\n"
        "• Pages Jaunes Pro : ~3 600 € HT / an, zéro garantie, baisse 30 % de trafic/an\n"
        "• Hellio/Effy commissionneurs : 10 à 20 % de marge en moins par chantier MaPrimeRénov'\n\n"
        "Si la math vous parle, 20 min pour discuter de {{entreprise}} : <a href=\"{{calendly}}\" style=\"color:#0066cc;\">{{calendly}}</a>"
    ),
}

J10_STORY = {
    "name":        "Carnet Plein · J+10 · Pourquoi Carnet Plein® existe",
    "description": "Relance — storytelling fondateur, raison d'être",
    "category":    "follow_up",
    "segment":     SEG,
    "step":        "J+10",
    "subject":     "Pourquoi on fait Carnet Plein® seulement pour artisans",
    "body_html":   H(
        "{{prenom}},\n\n"
        "Je vous raconte vite pourquoi on a productisé Carnet Plein® :\n\n"
        "Il y a quelques mois, un plombier de la région Hauts-de-France m'appelle. 22 ans de métier, RGE, du boulot bien fait, des clients qui le recommandent depuis toujours. Mais en juin il avait 4 chantiers fermes au lieu de 12 l'an dernier. Pas faute de compétence — faute de visibilité.\n\n"
        "Il avait déjà essayé une « agence digitale » : 4 800 €, site joli, zéro chantier généré. Site qui marche, audience qui ne le cherche pas.\n\n"
        "On a fait l'inverse : audit, refonte ciblée chauffage/PAC, Google Business Profile à jour, SMS post-chantier pour avis Google, contenu hyper-local. Quelques semaines plus tard, son carnet redémarre.\n\n"
        "C'est cette méthode qu'on industrialise dans Carnet Plein® — uniquement pour artisans RGE. Pas pour avocats, pas pour SaaS, pas pour coachs. Notre <strong>Vague Pilote 2026</strong> est la 1<sup>re</sup> cohorte officielle : 5 places à tarif fondateur (1 500 € + 250 €/mois sur 12 mois, garantie 80 % KPI).\n\n"
        "20 min sans engagement pour voir si {{entreprise}} matche : <a href=\"{{calendly}}\" style=\"color:#0066cc;\">{{calendly}}</a>"
    ),
}


# =============================================================
# J+18 — Breakup (dernier message, on lâche)
# =============================================================

J18_BREAKUP = {
    "name":        "Carnet Plein · J+18 · Breakup classique",
    "description": "Breakup — pas de relance, ouvre la porte sans insister",
    "category":    "breakup",
    "segment":     SEG,
    "step":        "J+18",
    "subject":     "Dernier message pour {{entreprise}}",
    "body_html":   H(
        "{{prenom}},\n\n"
        "Promis, dernier message. Pas envie d'être lourd.\n\n"
        "Si Carnet Plein® n'est pas le bon truc pour {{entreprise}} en ce moment, c'est ok. Le bouche-à-oreille fonctionne pour beaucoup d'artisans, surtout après 15-20 ans de métier dans la région. Vraiment pas une critique.\n\n"
        "La <strong>Vague Pilote 2026</strong> sera probablement complète dans les prochaines semaines — si la situation change pour vous, le lien Calendly reste actif : <a href=\"{{calendly}}\" style=\"color:#0066cc;\">{{calendly}}</a>\n\n"
        "Sinon, bonne route à {{entreprise}}. J'espère que les chantiers s'enchaînent bien sur la fin d'année.\n\n"
        "Et merci d'avoir lu jusqu'ici."
    ),
}

J18_BRIDGE = {
    "name":        "Carnet Plein · J+18 · Breakup + invitation newsletter",
    "description": "Breakup — propose la newsletter mensuelle comme pont long-terme",
    "category":    "breakup",
    "segment":     SEG,
    "step":        "J+18",
    "subject":     "Je vous laisse tranquille — petite chose avant",
    "body_html":   H(
        "{{prenom}},\n\n"
        "OK, je n'insiste plus.\n\n"
        "Avant de vous laisser tranquille, deux choses :\n\n"
        "1. La checklist <strong>« 12 points pour qu'un site convertisse un client RGE »</strong> reste accessible librement ici : <a href=\"https://carnetplein.mad-makers.fr/checklist\" style=\"color:#0066cc;\">carnetplein.mad-makers.fr/checklist</a>. 15 minutes à appliquer sur votre site existant, aucun produit à acheter.\n\n"
        "2. Une fois par mois, je publie un état des lieux chiffré de notre propre prospection Mad Makers + 1 audit public d'un artisan RGE. Si ça vous intéresse de garder un œil sans engagement, vous pouvez vous inscrire ici : <a href=\"https://carnetplein.mad-makers.fr/newsletter\" style=\"color:#0066cc;\">carnetplein.mad-makers.fr/newsletter</a>\n\n"
        "Pas d'autres mails de prospection de ma part. Si un jour vous voulez en discuter, le Calendly reste là : <a href=\"{{calendly}}\" style=\"color:#0066cc;\">{{calendly}}</a>\n\n"
        "Bonne route à {{entreprise}}."
    ),
}


# =============================================================
# Utility — Post-RDV, Post-signature, Kick-off
# =============================================================

POST_AUDIT = {
    "name":        "Carnet Plein · Post-audit · Récap + devis",
    "description": "Envoyé après RDV d'audit — récap + devis Vague Pilote",
    "category":    "rdv_recap",
    "segment":     SEG,
    "step":        "custom",
    "subject":     "Récap de notre audit + devis Vague Pilote pour {{entreprise}}",
    "body_html":   H(
        "Bonjour {{prenom}},\n\n"
        "Merci pour le temps qu'on a passé ensemble. Voici ce que je retiens de l'audit pour {{entreprise}} :\n\n"
        "<strong>3 axes prioritaires identifiés :</strong>\n"
        "• [À COMPLÉTER — Axe 1, ex : refonte page d'accueil orientée conversion]\n"
        "• [À COMPLÉTER — Axe 2, ex : Google Business Profile + campagne avis]\n"
        "• [À COMPLÉTER — Axe 3, ex : 5 pages géolocalisées sur les communes cibles]\n\n"
        "<strong>Objectif convenu sur 12 mois :</strong> [À COMPLÉTER — ex : 18 leads qualifiés sur la zone {{ville}} + agglo]\n\n"
        "<strong>Offre Vague Pilote 2026 :</strong>\n"
        "• 1 500 € HT setup (au lieu de 5 000) → payable 50 % à signature, 50 % au déploiement validé\n"
        "• 250 € HT / mois pendant 12 mois (au lieu de 800)\n"
        "• Total : 4 500 € HT sur 12 mois\n"
        "• Garantie écrite 80 % KPI sinon on continue gratis\n"
        "• Contrepartie : droit de communication publique sur les résultats (nom, ville, chiffres, vidéos M+3 / M+6 / M+12)\n\n"
        "Devis détaillé en pièce jointe. Si tout convient, vous pouvez signer électroniquement via le lien dans le PDF. Je bloque la place 7 jours, après quoi elle repart sur la liste d'attente.\n\n"
        "Une question avant signature ? Répondez à ce mail ou rebookez 15 min ici : <a href=\"{{calendly}}\" style=\"color:#0066cc;\">{{calendly}}</a>"
    ),
}

POST_SIGNATURE = {
    "name":        "Carnet Plein · Post-signature · Bienvenue",
    "description": "Envoyé après signature + acompte — bienvenue dans la cohort",
    "category":    "custom",
    "segment":     SEG,
    "step":        "custom",
    "subject":     "Bienvenue dans la Vague Pilote {{entreprise}}",
    "body_html":   H(
        "{{prenom}},\n\n"
        "On vient de recevoir votre signature + acompte. <strong>Bienvenue dans la Vague Pilote 2026 de Carnet Plein®.</strong>\n\n"
        "<strong>Ce qui se passe maintenant :</strong>\n"
        "• <strong>D+1</strong> : je vous envoie le questionnaire d'onboarding (positionnement, communes prioritaires, photos chantier, accès Google Business Profile)\n"
        "• <strong>D+7</strong> : kick-off visio 60 min — vous + moi + les autres artisans de la cohort\n"
        "• <strong>D+14 à D+45</strong> : phase setup (site, GBP, avis automatisés, pages géo)\n"
        "• <strong>D+45 à D+365</strong> : phase acquisition active + reporting mensuel\n\n"
        "<strong>Engagement public :</strong>\n"
        "Comme convenu, on documente les résultats publiquement à M+3 / M+6 / M+12. Première publication début juillet. Vous validez le contenu avant publication, évidemment.\n\n"
        "Je vous envoie le questionnaire demain matin. En attendant, bloquez le kick-off : [À COMPLÉTER — lien Meet ou Calendly réservé cohort].\n\n"
        "Vraiment content d'avoir {{entreprise}} dans la Pilote. On a du boulot."
    ),
}

KICKOFF_J7 = {
    "name":        "Carnet Plein · Kick-off J+7 · Convocation",
    "description": "Envoyé J+6 avant kick-off cohort visio 60 min",
    "category":    "custom",
    "segment":     SEG,
    "step":        "custom",
    "subject":     "Kick-off Vague Pilote demain 9h — {{entreprise}}",
    "body_html":   H(
        "{{prenom}},\n\n"
        "Demain à 9h on lance officiellement la cohort Vague Pilote. Visio 60 min avec les autres artisans RGE qui ont signé en même temps que vous.\n\n"
        "<strong>Lien visio :</strong> [À COMPLÉTER — lien Meet]\n\n"
        "<strong>Programme :</strong>\n"
        "• 0-10 min : tour de table rapide (qui fait quoi, où, depuis quand)\n"
        "• 10-30 min : présentation détaillée de la méthode Carnet Plein® (les 4 leviers)\n"
        "• 30-50 min : roadmap individuelle de chacun sur les 6 prochaines semaines\n"
        "• 50-60 min : Q&R + accès aux outils partagés\n\n"
        "<strong>À préparer côté {{entreprise}} :</strong>\n"
        "• Liste des 5 communes prioritaires pour l'acquisition\n"
        "• Tarif moyen / marge moyenne par chantier (pour calibrer l'objectif KPI)\n"
        "• 5-10 photos de chantiers récents (PAC, chaudière, sanitaire — en haute déf)\n"
        "• Accès Google Business Profile (je vous demanderai un access manager)\n\n"
        "Si vous avez un blocage à 9h précises, dites-moi vite — on peut décaler de 30 min mais pas plus, on est 4 sur le créneau.\n\n"
        "À demain."
    ),
}


# ── Liste finale ──────────────────────────────────────────────

ALL_TEMPLATES = [
    # J0
    J0_PILOTE_EXPLICATION, J0_CARNET, J0_GBP, J0_GARANTIE,
    # J+4
    J4_QUESTION_DIRECTE, J4_FOUNDERS_CASE, J4_PDF_BONUS,
    # J+10
    J10_COHORT, J10_PRIX, J10_STORY,
    # J+18
    J18_BREAKUP, J18_BRIDGE,
    # Utility
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

    print(f"\n=== Seed Vague Pilote 2026 terminé ===")
    print(f"  Insérés  : {inserted}")
    print(f"  Skip     : {skipped}")
    print(f"  Total    : {len(ALL_TEMPLATES)}")


def main():
    parser = argparse.ArgumentParser(description="Seed templates Carnet Plein® Vague Pilote 2026")
    parser.add_argument("--keep", action="store_true",
                        help="Garde les templates existants (ne fait qu'ajouter)")
    parser.add_argument("--yes", action="store_true",
                        help="Skip le prompt de confirmation (utile en CI / script)")
    args = parser.parse_args()

    reset = not args.keep
    if reset and not args.yes:
        ans = input("Supprimer TOUS les templates existants ET re-seeder Vague Pilote ? [y/N] ").strip().lower()
        if ans != "y":
            print("Annulé.")
            return
    seed(reset=reset)


if __name__ == "__main__":
    main()
