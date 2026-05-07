"""Génère les outputs emails+audits pour les prospects 6-30 du batch."""
import json
from pathlib import Path
from datetime import date

DATA_DIR = Path(__file__).parent.parent / "data"
batch = json.loads((DATA_DIR / "batch_20260417.json").read_text(encoding="utf-8"))
prospects = batch["prospects"]
today = date.today().strftime("%d/%m/%Y")
landing = "https://madmakers.fr/restaurants"
email = "contact@madmakers.fr"

EMAILS = {
    # idx: (objet, corps)
    5: (
        "La Gargouille — 301 avis et zéro site web",
        "Salut,\n\nRestaurant La Gargouille à Saint-Vincent-de-Tyrosse : 301 avis, 4.4★ — une adresse qui tourne depuis 2010 avec une vraie clientèle fidèle. Ce qui m'interpelle : avec ce volume, une personne sur deux qui te cherche en ligne repart sans info sur ta carte.\n\nJ'ai un audit 1 page prêt sur ce que ça représente en couverts perdus. Gratuit, livré en 48h.\n\nTu veux que je te l'envoie ?"
    ),
    6: (
        "Mont 2 Padel — la restauration sans site ?",
        "Salut,\n\nEn cherchant la restauration autour de Mazerolles, je suis tombé sur Mont 2 Padel — 4.7★ sur 26 avis. Un complexe sportif avec snack sans site web, ça veut dire que les équipes qui réservent un court ne savent pas ce qu'elles vont manger. C'est une vente facile qui ne se fait pas.\n\nJ'ai préparé un audit 1 page sur ce point précis. Gratuit.\n\nJe te l'envoie ?"
    ),
    7: (
        "La Tapia Dax — 4.9★ et pas de site, je comprends pas",
        "Salut,\n\nLa Tapia à Dax : 4.9★ sur 108 avis. C'est la deuxième meilleure note que j'ai vue en cherchant des restos dans les Landes. Cuisines espagnoles à Dax, niche avec des chercheurs actifs — et tu n'as aucun site pour les capter.\n\nJ'ai un audit 1 page prêt sur ce que ça représente. Gratuit, 10 min de lecture.\n\nTu veux que je te l'envoie ?"
    ),
    8: (
        "Le QG — 342 avis et le site reste à faire",
        "Salut,\n\nLe QG à Mont-de-Marsan : 342 avis, 4.1★. Avec ce volume tu sais que tu as une clientèle régulière. Ce que tu ne vois pas : combien de nouveaux clients potentiels passent leur chemin faute de voir ta carte en ligne avant de choisir.\n\nJ'ai un audit 1 page qui chiffre ça concrètement. Gratuit.\n\nTu veux que je te l'envoie ?"
    ),
    9: (
        "Le Béarn Bar — 93 avis, pas de site",
        "Salut,\n\nLe Béarn Bar, Place Saint-Roch à Mont-de-Marsan. 93 avis, 3.8★ — une fréquentation réelle avec des clients qui prennent le temps de noter. Le problème : quelqu'un qui cherche un bar sympa le soir ne peut pas voir tes horaires ou ta carte avant de se déplacer.\n\nJ'ai un audit court sur ce point. Gratuit.\n\nJe te l'envoie ?"
    ),
    10: (
        "Le bistrot du coin Geaune — 4.5★, bravo",
        "Salut,\n\n4.5★ sur 36 avis pour un bistrot à Geaune, c'est fort pour un village. La clientèle locale est clairement là. Mais les gens qui roulent sur la route de l'Armagnac et cherchent où déjeuner ne voient qu'une fiche Google vide, sans carte ni menu.\n\nUn audit 1 page, gratuit, pour voir ce que ça représente ?\n\nMaïck — Mad Makers"
    ),
    11: (
        "La Tetrade Côte Lac — 1379 avis sans site",
        "Salut,\n\nRestaurant La Tetrade Côte Lac à Hossegor : 1379 avis, 4.4★. C'est un des restaurants les mieux notés de la côte landaise. Et pourtant, aucun site web. Tes clients te trouvent grâce à ta réputation — imagine ce que ça donnerait avec une vraie présence en ligne pour capter les nouveaux.\n\nJ'ai un audit 1 page prêt. Gratuit.\n\nTu veux que je te l'envoie ?"
    ),
    12: (
        "La Tetrade Côte Boutique — même adresse, même manque",
        "Salut,\n\nJe t'ai déjà contacté pour La Tetrade Côte Lac — je vois que vous avez deux établissements sous la même entité à Capbreton/Hossegor. Pour les deux enseignes, l'absence de site web limite votre captation en ligne.\n\nL'audit que je vous propose couvrirait les deux points de vente. Gratuit, 10 min.\n\nJe vous l'envoie ?"
    ),
    13: (
        "Le Poisson Rouge Vieux-Boucau — 1158 avis sans site",
        "Salut,\n\nLe Poisson Rouge à Vieux-Boucau-les-Bains : 1158 avis, 4.6★. C'est un score remarquable pour une station balnéaire des Landes. Ce qui m'étonne : sans site, tous les touristes qui planifient leurs vacances ne trouvent aucune info sur ta carte avant d'arriver.\n\nJ'ai un audit 1 page sur ce que tu rates. Gratuit.\n\nTu veux que je te l'envoie ?"
    ),
    14: (
        "Rock Food Hossegor — 951 avis, toujours pas de site ?",
        "Salut,\n\nRock Food à Hossegor : 951 avis, une institution. Ce qui me frappe : avec presque 1000 avis Google et zéro site web, tu dépends entièrement de Maps pour ta visibilité. Un changement d'algorithme Google et tu disparais du radar.\n\nL'audit que j'ai préparé montre ce risque et comment diversifier. Gratuit.\n\nJe te l'envoie ?"
    ),
    15: (
        "Lhospital Poissonnerie Traiteur — 4.2★, pas de site",
        "Salut,\n\nLhospital Poissonnerie Traiteur à Lons : 102 avis, 4.2★. Un artisan de la mer avec une vraie clientèle — mais aucun site pour présenter tes produits frais, tes plateaux, tes horaires. Les clients qui cherchent un traiteur poissons dans le Béarn ne te trouvent pas.\n\nJ'ai un audit 1 page sur la visibilité digitale d'un traiteur. Gratuit.\n\nTu veux que je te l'envoie ?"
    ),
    16: (
        "Ceviche Me Pau — 4.9★ et ouvert depuis 2023",
        "Salut,\n\nCeviche Me à Pau : 4.9★ sur 55 avis, ouvert depuis 2023. Une note parfaite, un concept original (ceviche à Pau c'est rare) — et aucun site pour que les gens qui cherchent 'restaurant péruvien Pau' te trouvent.\n\nJ'ai un audit 1 page sur ton acquisition digitale actuelle. Gratuit.\n\nJe te l'envoie ?"
    ),
    17: (
        "Goia Anglet — 669 avis et invisible en ligne",
        "Salut,\n\nGoia à Anglet : 669 avis, 4.5★. C'est un score solide pour la côte basque où la concurrence est dense. Ce que je vois : sans site, tu ne captes pas les touristes qui planifient leur séjour et cherchent 'restaurant Anglet' avant d'arriver.\n\nJ'ai préparé un audit 1 page sur ce manque. Gratuit.\n\nTu veux que je te l'envoie ?"
    ),
    18: (
        "Cidrerie Beti Bai — 1039 avis sans site en 2026",
        "Salut,\n\nCidrerie Beti Bai des Platanes à Anglet : 1039 avis, 4.5★. Avec ce volume tu es clairement une référence locale. Mais une cidrerie basque sans site web, c'est un concept qui se vend tout seul — et que tu n'exploites pas en ligne.\n\nJ'ai un audit 1 page sur ce potentiel non capté. Gratuit.\n\nJe te l'envoie ?"
    ),
    19: (
        "Tavola Calda Saint-Jean-de-Luz — 507 avis sans site",
        "Salut,\n\nTavola Calda à Saint-Jean-de-Luz : 507 avis, 4.7★ pour un restaurant italien. Saint-Jean-de-Luz en saison, c'est des milliers de touristes qui cherchent où dîner chaque soir. Sans site, tu ne figuras pas dans leur processus de décision.\n\nJ'ai un audit 1 page prêt. Gratuit.\n\nTu veux que je te l'envoie ?"
    ),
    20: (
        "Au Comptoir Saint-Palais — 20 ans de qualité, pas de site",
        "Salut,\n\nAu Comptoir à Saint-Palais : 4.3★ sur 137 avis, ouvert depuis 2003. Une longévité qui prouve la qualité. Ce que je note : les randonneurs du Chemin de Saint-Jacques (qui passe par Saint-Palais) cherchent systématiquement où manger en ligne avant l'étape. Tu n'es pas dans leur recherche.\n\nJ'ai un audit 1 page sur ce flux touristique non capté. Gratuit.\n\nJe te l'envoie ?"
    ),
    21: (
        "La Chênaie Ledeuix — 4.6★ en pleine nature",
        "Salut,\n\nLa Chênaie à Ledeuix : 4.6★ sur 208 avis, un restaurant français au coeur du Béarn. Un endroit qu'on ne trouve que si on le connaît déjà — ou si on a un site qui fait le travail de te rendre visible.\n\nJ'ai un audit 1 page sur la visibilité d'un restaurant en zone rurale. Gratuit.\n\nTu veux que je te l'envoie ?"
    ),
    22: (
        "O'Gascon Pau — 918 avis, top gasconne sans site",
        "Salut,\n\nRestaurant O'Gascon à Pau : 918 avis, 4.2★. Presque 1000 personnes qui ont pris le temps de noter — c'est une base client massive. Sans site, tu ne transformes pas cette réputation en réservations de nouveaux clients qui te découvrent en ligne.\n\nJ'ai un audit 1 page prêt. Gratuit.\n\nJe te l'envoie ?"
    ),
    23: (
        "Ô-Tchanquet Oloron — 222 avis pas de site",
        "Salut,\n\nÔ-Tchanquet à Oloron-Sainte-Marie : 222 avis, 4.2★, ouvert depuis 2007. Un resto de ville avec une vraie clientèle locale. Ce que je remarque : Oloron est une porte d'entrée vers les Pyrénées — les randonneurs et skieurs cherchent en ligne avant de s'arrêter. Tu n'es pas visible pour eux.\n\nJ'ai un audit 1 page sur ce potentiel. Gratuit.\n\nTu veux que je te l'envoie ?"
    ),
    24: (
        "La Crêperie Orthez — 464 avis et pas de site",
        "Salut,\n\nLa Crêperie à Orthez : 464 avis, 4.3★. C'est une vraie référence locale. Mais une crêperie sans site web en 2026, c'est aussi la carte qu'on ne peut pas consulter avant de décider, et les groupes qui ne savent pas comment réserver.\n\nJ'ai un audit court sur ces deux points. Gratuit.\n\nJe te l'envoie ?"
    ),
    25: (
        "Grillerie du Port Saint-Jean-de-Luz — 156 avis, saison approche",
        "Salut,\n\nLA GRILLERIE DU PORT à Saint-Jean-de-Luz : 156 avis, 4.3★, fruits de mer sur le port. Avec la saison estivale qui approche, c'est exactement le type de restaurant que les touristes cherchent en ligne avant de réserver. Sans site, tu passes sous le radar de cette vague.\n\nJ'ai un audit 1 page sur l'acquisition touristique. Gratuit.\n\nTu veux que je te l'envoie ?"
    ),
    26: (
        "Xuriatea Hasparren — 4.6★ au coeur du Pays Basque",
        "Salut,\n\nXuriatea à Hasparren : 4.6★ sur 348 avis. Un restaurant basque traditionnel avec une très belle réputation. Ce qui me frappe : Hasparren est sur la route des touristes qui veulent l'authentique Pays Basque intérieur — et tu n'as pas de site pour les accueillir avant qu'ils arrivent.\n\nJ'ai un audit 1 page sur cette clientèle non captée. Gratuit.\n\nJe te l'envoie ?"
    ),
    27: (
        "Le Schuss Eaux-Bonnes — 651 avis en station",
        "Salut,\n\nLe Schuss à Eaux-Bonnes : 651 avis, 4.6★. Un restaurant de montagne avec une clientèle ski/rando importante. Ce que je note : les skieurs qui planifient leur weekend cherchent systématiquement où déjeuner en ligne. Sans site, tu n'es pas dans leur préparation.\n\nJ'ai un audit 1 page sur l'acquisition digitale en station. Gratuit.\n\nTu veux que je te l'envoie ?"
    ),
    28: (
        "Mimosa Sare — 358 avis au village basque",
        "Salut,\n\nMimosa à Sare : 4.2★ sur 358 avis, place du village. Sare est classée parmi les plus beaux villages de France — un flux touristique massif en saison. Sans site, les visiteurs qui planifient leur journée ne te trouvent pas pendant leur phase de recherche.\n\nJ'ai un audit 1 page sur ce potentiel touristique non capté. Gratuit.\n\nJe te l'envoie ?"
    ),
    29: (
        "Laniakea Anglet — 4.4★ en centre commercial",
        "Salut,\n\nLaniakea à Anglet (Bab2) : 4.4★ sur 35 avis. Un bar lounge en centre commercial — une clientèle de passage qui pourrait devenir régulière si elle pouvait te suivre en ligne. Sans site ni présence active, chaque visite reste ponctuelle.\n\nJ'ai un audit court sur fidélisation digitale. Gratuit.\n\nTu veux que je te l'envoie ?"
    ),
}

AUDITS = {}
# Generate audit bodies for all remaining prospects
for i in range(5, 30):
    p = prospects[i]
    nom = p.get("gmb_name") or p.get("nom_commercial") or p["raison_sociale"]
    ville = p["ville"]
    rating = p.get("gmb_rating", "N/A")
    reviews = p.get("gmb_reviews_count", 0)
    typ = p.get("gmb_type", "Restaurant")
    dept_name = {"40": "Landes", "64": "Pays Basque", "17": "Charente-Maritime", "24": "Dordogne"}.get(p["departement"], p["departement"])

    audit = f"""# Audit digital — {nom}

**Réalisé le {today} par Maïck, Mad Makers**
**Durée de lecture : 10 minutes**

---

## Ce que vous faites déjà bien

### 1. Réputation Google établie
{reviews} avis, {rating}★ sur Google Maps — une base de confiance réelle que le digital doit amplifier.

### 2. Ancrage local fort en {dept_name}
{ville} est dans notre zone cible (niche pré-saison été) — le timing pour investir en visibilité digitale est optimal.

### 3. Activité continue confirmée
L'établissement est actif et référencé, ce qui facilite le travail de référencement local.

---

## Ce qui coûte des couverts aujourd'hui

### 1. Absence de site web
**Impact estimé** : 40-50% des clients cherchent le menu en ligne avant de choisir. Sans site, cette décision se fait en faveur d'un concurrent qui a une carte visible.

### 2. Pas de menu ou carte consultable
**Impact estimé** : les groupes, touristes et clients en déplacement ont besoin de voir la carte avant de se déplacer. Ce frein coûte 10-20 couverts/semaine.

### 3. Dépendance totale à Google Maps
**Impact estimé** : un seul canal de visibilité = un seul point de défaillance. Un site diversifie et sécurise.

---

## Ce que je ferais en priorité

### Priorité 1 — Site vitrine 1 page
- **Ce qu'il faut faire** : carte, horaires, contact, bouton réservation
- **Effort** : 3-4 jours
- **Gain estimé** : +15 à 25 couverts/mois

### Priorité 2 — Menu visible sur GMB
- **Ce qu'il faut faire** : ajouter menu + 10 photos de plats sur la fiche Google
- **Effort** : 2h
- **Gain estimé** : +20% de clics depuis Maps

### Priorité 3 — Intégration réservation en ligne
- **Ce qu'il faut faire** : TheFork ou formulaire simple
- **Effort** : 1 jour
- **Gain estimé** : -30 min de gestion téléphone/jour

---

## En résumé

L'urgence est simple : avoir un site avant la saison estivale. Avec {reviews} avis et {rating}★, {nom} a tout ce qu'il faut pour convertir en ligne — il manque juste la page.

Maïck — Mad Makers
{email} · {landing}"""

    AUDITS[i] = audit


output_path = DATA_DIR / "outputs_20260417.md"

with open(output_path, "a", encoding="utf-8") as f:
    for i in range(5, 30):
        p = prospects[i]
        nom = p.get("gmb_name") or p.get("nom_commercial") or p["raison_sociale"]
        ville = p["ville"]

        if i in EMAILS:
            objet, corps = EMAILS[i]
        else:
            objet = f"{nom} — pas de site web"
            corps = f"Salut,\n\nJe suis tombé sur {nom} en cherchant où manger à {ville}. {p.get('gmb_reviews_count',0)} avis Google et {p.get('gmb_rating','N/A')}★ — et aucun site en vue.\n\nJ'ai un audit 1 page prêt sur ce que ça te coûte. Gratuit.\n\nTu veux que je te l'envoie ?"

        f.write(f"""## Prospect {i+1} — {nom} ({ville})

**SIRET**: {p['siret']}
**Dirigeant**: [à enrichir]
**Email**: [à enrichir]
**Signal**: sans_site
**Score**: {p['score']}

### Email cold
**Objet**: {objet}

{corps}

Maïck — Mad Makers
{landing}

### Audit (à envoyer après OK)

{AUDITS[i]}

---

""")

print(f"OK — {len(range(5,30))} prospects ajoutés dans outputs_20260417.md")
