"""crm.ai — génération d'emails via Claude API.

Compose un prompt riche avec :
- contexte prospect (nom, entreprise, titre, site, catégorie, audit)
- contexte expéditeur (user CRM courant)
- identité Mad Makers (ton, projets réf, processus, "ce qu'on refuse")
- demande spécifique de l'utilisateur

Retourne {subject, body_html} JSON-structured.
"""
import os
import json
import logging
from typing import Optional

import anthropic

log = logging.getLogger(__name__)

DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")


# ── Système : identité Mad Makers + voix + règles ───────────

SYSTEM_PROMPT = """Tu rédiges des cold emails B2B pour **Mad Makers**, agence web française spécialisée dans la création de sites qui convertissent (pas des objets esthétiques — des outils de vente).

# ⚠️ RÈGLE ABSOLUE — ZÉRO INVENTION
Tu n'as PAS accès au web. Tu n'as PAS visité le site du prospect. Tu travailles UNIQUEMENT à partir des informations fournies dans le contexte ci-dessous.

**Tu NE DOIS JAMAIS** :
- Inventer un chiffre (LCP, taux de conversion, nombre de leads, vitesse...) qui ne te serait pas explicitement donné
- Affirmer avoir "testé", "chargé", "visité", "analysé" le site si ce n'est pas le cas
- Décrire le design, les couleurs, les images, le contenu visuel du site (tu ne les vois pas)
- Mentionner un concurrent spécifique par son nom (sauf si donné en contexte)
- Citer une statistique précise ("23% de bounce", "5 secondes de chargement") sans qu'elle soit dans le contexte
- Affirmer des faits sur l'historique du prospect sans donnée explicite

**Tu PEUX en revanche** :
- Citer EXACTEMENT les faits donnés dans le contexte audit (note sécu, technos détectées, copyright, HTTPS) — ils sont vérifiés
- Utiliser des benchmarks GÉNÉRAUX et reconnus, présentés comme tels ("la majorité du trafic web est mobile", "les Core Web Vitals influencent le SEO")
- Faire des inférences explicites en utilisant des verbes prudents : "ça suggère que", "en règle générale", "souvent"
- Marquer ce qui est à compléter par l'humain avec `[À COMPLÉTER — précisez]` quand tu n'as pas l'info

Si tu manques d'info pour rendre l'email crédible, dis-le explicitement dans la sortie plutôt qu'inventer. Mieux vaut un placeholder `[À COMPLÉTER]` qu'un mensonge.

# Identité Mad Makers
- Tagline : "Dream it. We make it." · "On ne livre pas des sites. On livre des outils de vente."
- Livraison **10 jours** (vs 2-3 mois en agence classique)
- 2 gates de validation écrites (maquettes signées avant dev, livraison signée avant mise en ligne)
- Devis fixe au scope, acompte 40% / solde 60%
- 3 cas de référence à citer selon contexte :
  • **Riot Games — Riot MMO (2025)** : globe 3D temps réel WebGL, 13 régions, narration épique. Premium grand compte.
  • **La Papiche (2026)** : bistrot Saint-Avit (Charente), TPE locale, mobile-first, photos authentiques, réservation directe + Google/Tripadvisor.
  • **Dr. Sophie Marchand (2026)** : cabinet médical Nantes, intégration Doctolib, transparence tarifaire, 4,9/5 sur 134 avis.

# Voix Mad Makers (CRITIQUE — à respecter)
- **Direct, anti-bullshit**. Pas d'anglicismes marketing creux ("disruptif", "scaling", "synergie", "leverage").
- **Pas de formules creuses** : pas de "j'espère que ce mail vous trouve bien", pas de "j'espère vous parler bientôt".
- **Promesses chiffrées** : 10 jours, "+X leads/mois", "payback X mois", etc. (mais JAMAIS inventer un chiffre — utiliser les benchmarks réels ou laisser vide pour [À COMPLÉTER]).
- **Courts** : 120-180 mots max corps complet.
- **Pas de signature** — elle est ajoutée automatiquement par le CRM.
- **Tutoiement par défaut sauf indication contraire** dans le prompt utilisateur. (Note : si user demande vouvoiement, vouvoyer.)
- **Bullets ou phrases courtes** > paragraphes denses.
- **CTA clair** à la fin : "20 min cette semaine ?" / "Je vous envoie la maquette d'ici demain ?" / "Mardi 14h ou jeudi 10h ?"

# Format de sortie OBLIGATOIRE
Tu DOIS répondre UNIQUEMENT avec un JSON strict, sans markdown, sans préfixe :
{
  "subject": "...",
  "body_html": "<p>...</p><p>...</p>"
}

Règles HTML pour body_html :
- Wrapper chaque paragraphe dans <p>...</p>
- Listes : <ul><li>...</li></ul>
- Pas de <style>, pas de <script>, pas de couleurs/fonts inline
- Pour mettre en évidence : <b>...</b> (sobre)
- Variables CRM disponibles à utiliser tel quel (le CRM les remplira) : {{prenom}}, {{entreprise}}, {{site_short}}, {{ville}}, {{titre}}, {{calendly}}, {{today}}
- Préférer les variables aux valeurs en dur quand pertinent
- PAS de signature à la fin (ajoutée auto par le CRM)
- PAS de lien de désabonnement (ajouté auto par le CRM)
"""


def _build_prospect_context(prospect: dict, audit: dict = None) -> str:
    """Construit le bloc de contexte sur le prospect."""
    p = prospect or {}
    lines = ["# Contexte prospect"]
    if p.get("nom_complet"):
        lines.append(f"- **Nom** : {p['nom_complet']}")
    if p.get("titre"):
        lines.append(f"- **Titre** : {p['titre']}")
    if p.get("entreprise"):
        lines.append(f"- **Entreprise** : {p['entreprise']}")
    if p.get("ville"):
        lines.append(f"- **Ville** : {p['ville']}")
    if p.get("site_url"):
        lines.append(f"- **Site** : {p['site_url']}")
    else:
        lines.append(f"- **Site** : aucun (cat. SANS SITE)")
    if p.get("categorie"):
        cat_label = {
            "sans_site": "SANS SITE — angle création from scratch",
            "avec_site_veillot": "VEILLOT — site existant mais daté, angle refonte",
            "avec_site_recent": "RÉCENT — site moderne, angle optimisation conversion",
        }.get(p["categorie"], p["categorie"])
        lines.append(f"- **Catégorie Mad Makers** : {cat_label}")

    # Audit data si dispo — TOUS ces faits sont VÉRIFIÉS, Claude peut les citer
    if audit and audit.get("ok") is not False:
        a_lines = ["", "# AUDIT FACTUEL DU SITE (faits vérifiés — tu peux citer sans crainte)"]
        if audit.get("final_url"):
            a_lines.append(f"- URL finale : {audit['final_url']}")
        if audit.get("title"):
            a_lines.append(f"- Title du site : « {audit['title']} »")
        if audit.get("h1"):
            a_lines.append(f"- H1 principal : « {audit['h1']} »")
        if audit.get("description"):
            a_lines.append(f"- Meta description : « {audit['description']} »")
        else:
            a_lines.append(f"- Meta description : ABSENTE (problème SEO réel)")
        if audit.get("security_grade"):
            a_lines.append(f"- Note sécurité headers HTTP : **{audit['security_grade']}** (échelle A-F)")
        if audit.get("https") is False:
            a_lines.append(f"- ⚠ Pas de HTTPS")
        elif audit.get("https"):
            a_lines.append(f"- HTTPS : oui (TLS {audit.get('tls_version', '?')})")
        if audit.get("technos"):
            a_lines.append(f"- Technos détectées dans le HTML : {audit['technos']}")
        if audit.get("veillot_tags"):
            a_lines.append(f"- Signaux de vétusté détectés : {audit['veillot_tags']}")
        if audit.get("copyright_year"):
            a_lines.append(f"- Copyright affiché : {audit['copyright_year']}")
        ic = audit.get("image_count")
        mic = audit.get("modern_image_count")
        if ic is not None:
            a_lines.append(f"- Images : {ic} sur la page d'accueil dont {mic or 0} en format moderne (WebP/AVIF)")
        if audit.get("html_size_kb"):
            a_lines.append(f"- Taille HTML : {audit['html_size_kb']} KB")
        lines.extend(a_lines)
    elif p.get("site_url"):
        lines.append("\n# Audit du site : NON DISPONIBLE (le site n'a pas été audité)")
        lines.append("- Ne fais aucune affirmation technique précise sur le site (vitesse, technos, etc.)")
        lines.append("- Tu peux mentionner l'URL et faire des hypothèses générales en restant prudent")

    return "\n".join(lines)


def _build_user_context(user: dict) -> str:
    """Bloc de contexte sur le signataire."""
    u = user or {}
    name = u.get("full_name") or u.get("email", "").split("@")[0].title()
    return (
        f"# Contexte expéditeur (le signataire)\n"
        f"- **Nom** : {name}\n"
        f"- **Email** : {u.get('email', '')}\n"
        f"L'email part au nom de cette personne, mais NE PAS inclure de signature "
        f"(le CRM l'ajoute automatiquement)."
    )


def draft_email(
    prospect: dict,
    user: dict,
    user_prompt: str,
    audit: Optional[dict] = None,
    base_template: Optional[dict] = None,
) -> dict:
    """Génère un email via Claude.

    Args:
        prospect : dict {nom_complet, titre, entreprise, ville, site_url, categorie, ...}
        user     : dict {full_name, email, ...}
        user_prompt : ce que l'user veut spécifiquement (ex: "relance après no-reply, plus direct")
        audit    : dict optionnel — résultat de audit_site() si dispo
        base_template : dict optionnel — template DB existant à reprendre/améliorer

    Returns:
        {"subject": str, "body_html": str}
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY non défini dans .env")

    client = anthropic.Anthropic(api_key=api_key)

    # Compose le user message
    parts = [
        _build_prospect_context(prospect, audit),
        "",
        _build_user_context(user),
        "",
        "# Demande spécifique",
        user_prompt.strip() if user_prompt else "Cold email Mad Makers, ton direct.",
    ]
    if base_template:
        parts += [
            "",
            "# Template de base à raffiner (subject + body_html ci-dessous)",
            f"**Subject de base** : {base_template.get('subject', '')}",
            f"**Body de base** :\n{base_template.get('body_html', '')}",
            "",
            "Utilise ce template comme point de départ — améliore-le selon la demande spécifique ci-dessus.",
        ]

    parts += [
        "",
        "Maintenant rédige l'email. Réponds UNIQUEMENT avec le JSON {subject, body_html}, sans markdown.",
    ]

    user_message = "\n".join(parts)

    log.info(f"AI draft request : prospect={prospect.get('nom_complet')}, model={DEFAULT_MODEL}")

    response = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = "".join(block.text for block in response.content if block.type == "text").strip()
    # Strip code fence if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
        if raw.startswith("json"):
            raw = raw[4:].lstrip("\n")
        raw = raw.rstrip("`").rstrip()
        if raw.endswith("```"):
            raw = raw[:-3].rstrip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback : essaie d'extraire le JSON entre accolades
        import re as _re
        m = _re.search(r"\{[\s\S]*\}", raw)
        if not m:
            log.error(f"Failed to parse JSON from Claude response: {raw[:300]}")
            raise RuntimeError("Réponse Claude non parsable (pas de JSON)")
        data = json.loads(m.group(0))

    subject = (data.get("subject") or "").strip()
    body = (data.get("body_html") or "").strip()
    if not subject or not body:
        raise RuntimeError("Claude a retourné un JSON vide ou incomplet")

    return {"subject": subject, "body_html": body}
