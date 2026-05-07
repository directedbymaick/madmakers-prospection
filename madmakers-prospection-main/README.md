# Mad Makers — Pipeline Prospection

Skill Claude Code pour automatiser la prospection cold email de Mad Makers (agence digitale).

**Cible V1** : restaurants traditionnels en Nouvelle-Aquitaine touristique (Landes, Pays Basque, Charente-Maritime, Dordogne).

**Mission** : produire 30 contacts qualifiés/jour, avec audit digital personnalisé et email cold rédigé, prêts à valider et envoyer — en 30 minutes de travail quotidien.

---

## Démarrage rapide

**Tu es Maïck et tu découvres ce repo** : lis `setup.md`. Il te prend de zéro à ton premier batch en 2-3h.

**Tu es Goudet et tu veux comprendre l'architecture** : lis `SKILL.md` (le playbook Claude) et la section suivante.

---

## Architecture

```
madmakers-prospection/
├── SKILL.md                  # playbook Claude, invoqué par /madmakers-prospection
├── setup.md                  # guide infra complet pour Maïck
├── daily_playbook.md         # routine quotidienne (30 min/jour)
├── scripts/                  # Python : appels API externes uniquement
│   ├── config.py             # chargement .env + constantes
│   ├── source_restaurants.py # INSEE SIRENE + Google Places
│   ├── fetch_site.py         # analyse site web + PageSpeed
│   ├── enrich_pappers.py     # dirigeants + CA
│   └── export_folk.py        # CSV import Folk
├── templates/                # markdown, lus par Claude en session
│   ├── email_cold.md         # cold email (3 variantes signal)
│   ├── audit_structure.md    # audit 1-pager
│   └── follow_ups.md         # relances J+4 et J+10
├── landing-page-v1/          # HTML + Tailwind, GitHub Pages
│   ├── index.html
│   ├── form-handler.md       # setup Formspree
│   └── README.md
├── config/
│   ├── icp.yaml              # scoring ICP + seuils
│   └── .env.example          # template secrets
└── data/                     # gitignored : batchs + exports + snapshots
```

## Flux quotidien

Maïck tape `/madmakers-prospection` dans Claude Code. Claude :

1. Sourcing SIRENE + Google Places → 30 restos scorés
2. Enrich sites (PageSpeed, meta) + Pappers (dirigeants)
3. Génère 30 emails + 30 audits personnalisés (en session Claude, pas de script)
4. Demande validation batch par batch
5. Crée 30 drafts Gmail prêts à envoyer
6. Exporte CSV Folk

Maïck relit, corrige, clique Send. Relances J+4 et J+10 programmées par cron.

## Stack technique

- **Python 3.11+** avec `uv` pour les 4 scripts API
- **Claude Code** (compte Maïck) pour l'orchestration + génération copy
- **Gmail MCP** pour la création de drafts (pas d'envoi auto)
- **Folk CRM** via import CSV manuel
- **INSEE + Google Places + Pappers** pour le sourcing, tous gratuits ou freemium

Coût run mensuel : ~50€ (Google Cloud) + 30€ (Folk) + 6€ (Google Workspace) = **~90€/mois**.

## Scope V1 vs V2

**V1 (ce repo aujourd'hui)** :
- Niche : restos Nouvelle-Aquitaine uniquement
- Cold + relances J+4 et J+10
- Drafts Gmail (pas d'envoi auto)
- Folk par CSV (pas d'API)
- Landing HTML statique

**V2 (après 3 mois de data)** :
- Extension Occitanie + niches secondaires (spas, hôtels)
- Auto-envoi pour les relances (après validation taux réponse sains)
- API Folk direct
- Landing Framer avec cas clients
- Reporting analytics

## Licence & confidentialité

Privé. Ne pas publier les templates email (ils sont l'actif commercial de Mad Makers).
