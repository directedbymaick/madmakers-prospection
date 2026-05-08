"""crm.briefing_data — données statiques pour le briefing cold call.

Pains, questions, objections, visuels, closes — réutilisés depuis cold_call.py
mais structurés en dicts Python pour passage Jinja → JS.
"""

# ── Pain points par catégorie ──────────────────────────────────
PAINS_SANS_SITE = [
    ("CRITIQUE", "Aucune présence digitale propriétaire",
     "Sans site, ce sont LinkedIn / annuaires / GMB qui portent seuls l'image — vous ne contrôlez ni la narration, ni le SEO, ni le tunnel de conversion."),
    ("HAUT", "Coût d'opportunité sur les recherches Google",
     "À chiffrer ENSEMBLE pendant l'appel : nombre de prospects/mois qui pourraient découvrir l'entreprise via Google × valeur d'un client moyen."),
    ("HAUT", "Aucun contenu indexable",
     "Invisibilité sur les requêtes locales et métier. Chaque mois sans site = mois où la concurrence capte la demande organique."),
    ("MOYEN", "Dépendance aux plateformes tierces",
     "Si LinkedIn change son algo ou suspend un compte, l'image de marque disparait. Un nom de domaine est inaliénable."),
    ("MOYEN", "Pas de tunnel de conversion 24/7",
     "Tout passe par appel/email manuel. Un site avec landing pages + formulaires qualifie à froid pendant que vous dormez."),
]

PAINS_VEILLOT = [
    ("CRITIQUE", "Première impression visuelle datée",
     "Le visuel actuel ne reflète plus le standard 2026. À constater ENSEMBLE pendant l'appel via partage d'écran."),
    ("HAUT", "Responsive mobile à vérifier en live",
     "La majorité du trafic web est mobile. Si le site se déforme sur smartphone, le prospect bounce avant lecture du contenu."),
    ("HAUT", "Performances probablement dégradées",
     "Sans optimisations modernes (webp/avif, lazy-loading, code-splitting), Core Web Vitals fail — pénalité SEO Google."),
    ("HAUT", "Surface d'attaque sécurité",
     "Anciennes versions de jQuery/WordPress + headers manquants = vulnérabilités CVE publiques exploitables. Risque RGPD."),
    ("MOYEN", "Tracking / analytics modernes à confirmer",
     "Sans GA4 / Plausible / Matomo, aucune visibilité chiffrée sur ce qui convertit."),
    ("MOYEN", "Signal de fraîcheur Google faible",
     "Google indexe la fréquence de mise à jour. Site figé depuis plusieurs années = perte de positions."),
    ("MOYEN", "Hiérarchie d'information & CTA à auditer en live",
     "À vérifier ENSEMBLE : un visiteur comprend-il en 5 secondes ce que vous proposez et comment entrer en contact ?"),
]

PAINS_RECENT = [
    ("BAS", "Site moderne — l'enjeu n'est pas le visuel",
     "Le site existe et est récent. La vraie question : convertit-il ? Demander les données analytics si possible."),
    ("MOYEN", "Récent != optimisé pour vendre",
     "Beaucoup de sites Framer/Webflow récents sont visuellement bons mais sans hiérarchie commerciale, sans social proof structuré, sans funnel."),
    ("MOYEN", "Production de contenu et vidéo souvent absente",
     "Mad Makers ajoute la couche contenus (SEO long-tail) et vidéo institutionnelle — c'est ce qui transforme un site vitrine en moteur d'acquisition."),
]

# ── Questions découverte ───────────────────────────────────────
QUESTIONS = [
    {"theme": "1. Activité & cible", "items": [
        "Quel est votre cœur de métier en 1 phrase ?",
        "Vous vivez principalement de B2B ou de B2C ? Quelle proportion ?",
        "Qui est votre client type idéal aujourd'hui (taille, secteur, géo) ?",
        "Comment vous différenciez-vous de vos 2-3 concurrents principaux ?",
        "Quels concurrents admirez-vous le plus (même hors secteur) ?",
    ]},
    {"theme": "2. Acquisition (CRUCIAL pour ROI)", "items": [
        "D'où viennent vos clients aujourd'hui ?",
        "Quel canal marche le mieux en %, à votre feeling ?",
        "Combien de leads / RDV par mois en moyenne ?",
        "Combien vaut un client moyen pour vous (panier × récurrence) ? [chiffre crucial]",
        "Combien de temps entre 1er contact et signature ?",
        "Vous avez déjà fait du Google/Meta Ads, du SEO ? Résultats ?",
    ]},
    {"theme": "3. Site web actuel", "items": [
        "Qui a fait votre site, et quand exactement ?",
        "Vous avez la main pour modifier, ou vous passez par quelqu'un ?",
        "Sur 10, vous mettez combien à votre site aujourd'hui ? Pourquoi pas plus ?",
        "Qu'est-ce qui vous fait honte / que vous ne montrez pas à un client ?",
        "Vous savez combien de visiteurs il fait par mois ?",
        "Avez-vous déjà mesuré le taux de conversion (visiteur → contact) ?",
    ]},
    {"theme": "4. Objectifs & visuels", "items": [
        "Si vous pouviez doubler 1 métrique en 6 mois, ce serait quoi ?",
        "Quels visuels avez-vous : photos pro, logos, identité ?",
        "Vous avez une charte graphique / palette / fonts existantes ?",
        "Quelles refs / sites trouvez-vous bien faits ?",
        "Quel est votre budget de référence pour un site de qualité ?",
    ]},
]

# ── Visuels ────────────────────────────────────────────────────
VISUELS = [
    "Logo (PNG haute def, SVG si possible)",
    "Photos équipe / dirigeants (HD)",
    "Photos lieu / locaux / atelier (HD)",
    "Photos produits / réalisations (HD)",
    "Charte graphique / palette si existante",
    "Brochure commerciale PDF (s'il y en a une)",
    "Liens vers réseaux sociaux actifs",
    "Liens vers Google My Business / Tripadvisor / avis",
    "Accès analytics actuel (lecture seule)",
]

# ── Objections Belfort ─────────────────────────────────────────
OBJECTIONS = [
    {"objection": "« C'est combien ? »", "reponse":
     "[AGREE] Excellente question, et je vais être très honnête avec vous. "
     "[BRIDGE] Entre un one-page rapide et un sur-mesure avec animations 3D, le tarif varie d'un facteur 5. Si je vous balance un chiffre maintenant je vous fais soit fuir, soit mentir. "
     "[REINFORCE] Voici ce qu'on fait : RDV 2, je vous présente une maquette construite SPECIFIQUEMENT pour votre boîte, on chiffre AU SCOPE EXACT, devis sous 48h. Pas de TJM ouvert, pas de scope creep. "
     "[CLOSE] Mardi 14h ou jeudi 10h pour le RDV 2 ?"},
    {"objection": "« On a déjà un site / on est en train de le refaire »", "reponse":
     "[AGREE] Excellent — vous avez DÉJÀ pris la décision qu'un site est stratégique. "
     "[BRIDGE] La vraie question : ce site, il fait QUOI pour vous concrètement ? Combien de leads/mois, quel taux de conversion ? "
     "[REINFORCE] Si vous me donnez les chiffres et qu'ils sont bons, je raccroche en 30 secondes — promis. Mais 9 fois sur 10 on me répond 'je sais pas'. C'est ÇA le vrai problème. "
     "[CLOSE] Avant que je raccroche : on regarde votre site ensemble 5 minutes, je vous dis ce que JE ferais différemment, sans engagement ?"},
    {"objection": "« Je n'ai pas le temps »", "reponse":
     "[AGREE] Je vous crois totalement. C'est exactement la phrase que mes meilleurs clients m'ont dite. "
     "[BRIDGE] Mais laissez-moi vous demander : combien de temps par semaine vous expliquez votre activité au téléphone à des prospects qui auraient pu pré-qualifier sur un bon site ? "
     "[REINFORCE] Mad Makers prend tout en charge. Vous nous donnez UNE HEURE répartie sur 10 jours. Une heure pour un outil qui travaille 24h/24 pendant 5 ans pour vous. "
     "[CLOSE] RDV 2 c'est 30 minutes en visio. Mardi 14h ou jeudi 10h ?"},
    {"objection": "« On n'a pas de budget cette année »", "reponse":
     "[AGREE] Je comprends totalement, le budget c'est toujours tendu — surtout sans ROI chiffré. "
     "[BRIDGE] Mais : aujourd'hui sans site qui vend, combien de prospects/mois découvrent un concurrent au lieu de vous ? Disons UN SEUL par mois × votre panier moyen × 12. Vous arrivez sur quel chiffre ? "
     "[REINFORCE] Ce n'est pas une dépense, c'est un investissement dont le payback se mesure en MOIS, pas en années. Si au RDV 2 vous trouvez le payback trop long, vous me dites non sans problème. "
     "[CLOSE] Vous préférez voir la maquette mardi ou jeudi ?"},
    {"objection": "« On va voir avec Wix / Webflow / un freelance »", "reponse":
     "[AGREE] Réponse honnête : si votre besoin c'est juste une vitrine simple, prenez Wix ou un freelance. Vraiment. "
     "[BRIDGE] MAIS — quand je regarde votre boîte et votre poste, j'ai du mal à croire que c'est juste une vitrine simple. C'est un OUTIL COMMERCIAL. "
     "[REINFORCE] Wix vous limite : pas de SEO sérieux, pas de tracking conversion, pas de design unique. Mad Makers a fait Riot Games sur leur dernier MMO, La Papiche bistrot Saint-Avit, Dr Marchand cabinet Nantes — 3 univers, 3 designs uniques. "
     "[CLOSE] Votre site doit faire QUOI dans 12 mois ? On en parle 15 minutes au RDV 2 — mardi ou jeudi ?"},
    {"objection": "« On va voir avec d'autres prestataires »", "reponse":
     "[AGREE] Parfait, c'est exactement ce qu'il faut faire — comparer. "
     "[BRIDGE] Voici la grille de comparaison que les agences classiques n'aiment pas qu'on diffuse. Demandez à chacun : "
     "[REINFORCE] UN — combien de jours signature → mise en ligne ? Nous c'est 10. DEUX — combien de séries de corrections incluses ? Nous c'est 2. TROIS — qui valide quoi par écrit ? Nous c'est 2 gates signées. Faites ça avec 3 agences, 90% sont vagues. "
     "[CLOSE] On fait quand même le RDV 2 pour que vous ayez UNE référence solide — mardi 14h ou jeudi 10h ?"},
    {"objection": "« Comment je sais que ça va me rapporter ? »", "reponse":
     "[AGREE] Question légitime, c'est exactement la question à se poser. "
     "[BRIDGE] Un site rapporte à 3 conditions : UN — hiérarchie de la page conçue pour la conversion. DEUX — trafic qualifié dessus (SEO/ads/réf). TROIS — tracking pour mesurer et itérer. "
     "[REINFORCE] Si on coche les 3, payback mesurable. Si on coche que la 1, c'est gain image+trust mais pas en cash, et je vous le dirai. C'est pour ça qu'au RDV 2 je vous présente PAS qu'une maquette : maquette + plan d'acquisition + plan de tracking. "
     "[CLOSE] Vous voulez voir ce package mardi 14h ou jeudi 10h ?"},
    {"objection": "« Envoyez-moi un email avec les infos »", "reponse":
     "[AGREE] Bien sûr, je peux le faire. "
     "[BRIDGE] Mais soyons honnêtes 30 secondes : un email générique va finir à la corbeille à 9h45 demain. "
     "[REINFORCE] Ce qui rend Mad Makers utile pour vous, c'est qu'on construit une maquette SPECIFIQUEMENT pour votre boîte. Pour un email pertinent j'ai besoin de 15 minutes. Après je vous envoie un email AVEC la maquette dedans. "
     "[CLOSE] Mardi 14h ou jeudi 10h, quel créneau marche le mieux ?"},
]

# ── Closing patterns Belfort ───────────────────────────────────
CLOSES = [
    ["Alternative-choice (default)", "« Pour le RDV 2 — vous préférez mardi 14h ou jeudi 10h ? »"],
    ["Assumed close (signaux d'achat)", "« Parfait, je vous envoie l'invit Calendly dans la foulée — vous voulez que je copie quelqu'un en cc ? »"],
    ["Summary close", "« Donc pour résumer : 30 minutes mardi, je vous montre une maquette de votre futur site, devis sous 48h, vous décidez. C'est bien ça ? »"],
    ["Direct close (dernière objection levée)", "« Bon — il reste UNE seule chose entre nous et le RDV 2 : vous voulez qu'on le fasse mardi ou jeudi ? »"],
    ["Soft close (hésitation)", "« Si ce n'est vraiment pas le bon moment, dites-le-moi sans problème. Mais si c'est juste un doute, on peut le lever en 15 minutes. Qu'est-ce qui se passe vraiment ? »"],
    ["Hard close (après 'envoyez un email')", "« Ok, donc je vous envoie l'invit pour mardi 14h, et je mets en pièce jointe les 3 cas qui ressemblent le plus à votre boîte. Ça marche ? »"],
]

# ── Authority drops ────────────────────────────────────────────
AUTHORITY_DROPS = {
    "sans_site":          "On a fait La Papiche (bistrot Saint-Avit, TPE locale) et le cabinet du Dr Sophie Marchand à Nantes — exactement votre profil de boîte où on construit à partir de zéro.",
    "avec_site_veillot":  "On a fait La Papiche (bistrot Saint-Avit), Dr Marchand à Nantes en santé libérale, et Riot Games sur leur dernier MMO en B2C premium. 3 univers totalement différents, 3 designs uniques.",
    "avec_site_recent":   "On a fait Riot Games sur leur dernier MMO — globe 3D temps réel WebGL, narration cinématique. C'est exactement ce niveau d'exigence qu'on apporte aux boîtes qui considèrent leur site comme un actif stratégique.",
}


def build_pains(category, audit=None):
    """Return list of dicts {sev, label, evidence}."""
    if category == "sans_site":
        base = list(PAINS_SANS_SITE)
    elif category == "avec_site_veillot":
        base = list(PAINS_VEILLOT)
    elif category == "avec_site_recent":
        base = list(PAINS_RECENT)
    else:
        base = []

    out = [{"sev": s, "label": l, "evidence": e} for s, l, e in base]

    # Pains dérivés de l'audit (faits réels)
    if audit:
        if audit.get("https") == 0 or (isinstance(audit.get("https"), bool) and not audit["https"]):
            out.append({"sev": "CRITIQUE", "label": "Pas de HTTPS sur le site",
                        "evidence": "Chrome marque le site 'non sécurisé', perte de trust + SEO."})
        grade = audit.get("security_grade")
        if grade in ("E", "F"):
            findings = audit.get("findings", "") or ""
            out.append({"sev": "HAUT", "label": f"Note sécurité {grade} (headers manquants)",
                        "evidence": findings.split("\n")[0] if findings else "Headers de sécurité manquants."})
        if not audit.get("description"):
            out.append({"sev": "MOYEN", "label": "Pas de meta description",
                        "evidence": "Affichage dans les SERP non contrôlé, taux de clic faible."})
        if audit.get("image_count", 0) > 0 and audit.get("modern_image_count", 0) == 0:
            out.append({"sev": "MOYEN", "label": "Aucune image en WebP/AVIF",
                        "evidence": f"{audit['image_count']} images en JPG/PNG = poids inutile = lenteur."})
        cy = audit.get("copyright_year")
        if cy and isinstance(cy, int) and cy < 2024:
            out.append({"sev": "HAUT", "label": f"Copyright {cy} (site figé)",
                        "evidence": "Aucun update récent, signal d'abandon visible."})
    return out


def build_hook(prospect, audit=None):
    """Returns dict {scenario, hook_text}."""
    cat = prospect.get("categorie", "")
    prenom = (prospect.get("prenom") or "").strip() or "Bonjour"
    boite = (prospect.get("entreprise") or "").strip() or "votre boîte"
    authority = AUTHORITY_DROPS.get(cat, AUTHORITY_DROPS["avec_site_veillot"])

    if cat == "sans_site":
        scenario = "SANS SITE — angle invisibilité Google + création"
        hook = (
            f"« Bonjour {prenom}, Maïck — Mad Makers. Vous allez bien ? »\n"
            f"  [PAUSE — laisser répondre, ton enthousiaste]\n"
            f"« Excellent. Je vais être très direct : j'ai cherché {boite} sur Google ce matin avant de vous appeler. "
            f"J'ai trouvé votre LinkedIn, deux annuaires d'entreprise, je n'ai PAS trouvé de site web. C'est volontaire ou c'est un projet en attente ? »\n"
            f"  [ÉCOUTER — note la réponse]\n"
            f"« OK. Écoutez : {authority} Je ne vais pas vous prendre 30 minutes. 90 secondes pour vous dire pourquoi je vous appelle PRÉCISÉMENT, et si ça vous parle on cale 15 minutes plus tard cette semaine. Ça vous va ? »"
        )
    elif cat == "avec_site_veillot":
        scenario = "VEILLOT — audit visuel + sécurité + maquette gratuite"
        site = (audit.get("final_url") if audit else "") or prospect.get("site_url", "")
        sigs = (audit.get("veillot_tags", "") or "").split(", ") if audit else []
        sig_phrase = f"j'ai vu {sigs[0].lower()}" if sigs and sigs[0] else "le design n'est plus aux standards 2026"
        sec = audit.get("security_grade", "?") if audit else "?"
        sec_phrase = f", note de sécurité headers : {sec}" if sec in ("D", "E", "F") else ""
        hook = (
            f"« Bonjour {prenom}, Maïck — Mad Makers. Vous allez bien ? »\n"
            f"  [PAUSE — sourire dans la voix]\n"
            f"« Excellent. Je vais être direct : j'ai regardé {site} ce matin avant de vous appeler — {sig_phrase}{sec_phrase}. "
            f"Concrètement, ça veut dire qu'aujourd'hui votre site fait perdre de la confiance aux prospects qui le voient avant un appel commercial — sans que vous le sachiez. »\n"
            f"« {authority} »\n"
            f"« Je ne vous appelle PAS pour vous vendre quoi que ce soit aujourd'hui. Je veux juste comprendre 2-3 choses sur votre activité, et si on est d'accord sur le diagnostic, on cale un 2e RDV où on vous montre une maquette refaite SPECIFIQUEMENT pour {boite}. C'est gratuit, vous décidez après. Ça vous va ? »"
        )
    else:
        scenario = "RÉCENT — angle conversion / SEO / vidéo"
        hook = (
            f"« Bonjour {prenom}, Maïck — Mad Makers. Vous allez bien ? »\n"
            f"  [PAUSE — ton sharp]\n"
            f"« Parfait. Je vais aller droit au but : votre site est récent, correct visuellement — je ne vous appelle PAS pour le refaire. »\n"
            f"« {authority} »\n"
            f"« Je vous appelle parce qu'un site récent != un site qui VEND. Et c'est exactement notre angle : prendre un site avec un visuel correct et le transformer en outil commercial mesurable. 90 secondes ? »"
        )
    return {"scenario": scenario, "hook_text": hook}


def briefing_payload(prospect, audit):
    """Return dict for Jinja → JSON injection."""
    return {
        "questions": QUESTIONS,
        "pains": build_pains(prospect["categorie"], audit),
        "visuels": VISUELS,
        "objections": OBJECTIONS,
        "closes": CLOSES,
    }
