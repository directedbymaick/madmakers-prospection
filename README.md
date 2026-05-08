# Mad Makers — Prospection toolkit + CRM

Pipeline de prospection cold email + cold call B2B + CRM local Mad Makers.

## Setup rapide (collaborateur)

### 1. Cloner le repo

```bash
git clone https://github.com/darthmaick/mad-makers-prospection.git
cd mad-makers-prospection
```

### 2. Récupérer les données prospects

⚠️ Les CSVs RocketReach (~500 prospects) **ne sont PAS dans le repo** (RGPD : emails + téléphones nominatifs). Demande à Maïck le lien **Google Drive / WeTransfer privé**.

Place les fichiers comme suit :
- `linkedin-scraper/data/inputs/rocketreach_bulk_*.csv` — 5 CSVs RocketReach
- `linkedin-scraper/data/prospects_triage_strict_*_recheck.csv` — CSV triage final

### 3. Lancer le setup automatique

**Linux / Mac / Git Bash sur Windows :**
```bash
./setup.sh
```

**Windows cmd :**
```cmd
setup.bat
```

Le script installe les deps Python, importe les 500 prospects dans le CRM SQLite local, enrichit avec les téléphones, et te dit comment lancer.

### 4. Lancer le CRM

```bash
python -X utf8 -m crm.run
# → ouvre http://127.0.0.1:8000
```

## Structure du projet

```
mad-makers-prospection/
├── crm/                        # CRM Flask + SQLite (CŒUR DU PROJET)
│   ├── app.py                  # Routes Flask
│   ├── briefing_data.py        # Données statiques briefing (pains, objections...)
│   ├── config.py               # Stages, catégories, types activité
│   ├── db.py                   # Connection SQLite + migrations
│   ├── enrich_phones.py        # Script CLI : peuple les téléphones depuis RocketReach
│   ├── import_prospects.py     # Script CLI : import depuis CSV triage
│   ├── models.py               # Queries SQLite
│   ├── run.py                  # Entry point serveur
│   ├── schema.sql              # DDL SQLite
│   ├── static/css/             # Styles Mad Makers (noir + jaune)
│   ├── templates/              # Jinja2 (dashboard, prospects, briefing, pipeline...)
│   └── README.md               # Doc CRM détaillée
│
├── linkedin-scraper/           # Pipeline triage / scraping
│   ├── data/
│   │   ├── .gitkeep            # Dossier ignoré, juste le marqueur en git
│   │   ├── inputs/             # CSVs RocketReach (NON commités, RGPD)
│   │   └── *.csv               # CSVs triage générés (NON commités)
│   └── scripts/
│       ├── triage_sites.py            # Catégorise sites (sans/veillot/récent)
│       ├── reclassify_triage.py       # Reclass strict
│       ├── triage_recheck.py          # URL discovery v2 sur sans-site
│       ├── triage_apply_manual.py     # Applique URLs trouvées via WebSearch
│       ├── cold_call.py               # Briefing HTML standalone (legacy)
│       └── ...                        # Autres scripts du pipeline
│
├── madmakers-prospection-main/ # Toolkit prospection initial (legacy)
│
├── setup.sh / setup.bat        # Setup automatique collaborateur
├── .gitignore                  # Ignore .env, data/*, briefings/, *.db
└── README.md                   # Ce fichier
```

## Pipeline complet (depuis 0)

Si tu veux re-générer le pipeline depuis zéro avec un nouveau batch RocketReach :

```bash
cd linkedin-scraper

# 1. Place les nouveaux CSVs dans data/inputs/

# 2. Triage HTML scoring
python -X utf8 scripts/triage_sites.py

# 3. Reclassification stricte (recent/veillot)
python -X utf8 scripts/reclassify_triage.py

# 4. URL discovery v2 sur les sans-site
python -X utf8 scripts/triage_recheck.py

# 5. (optionnel) WebSearch + apply manual URLs
python -X utf8 scripts/triage_apply_manual.py

# 6. Import dans le CRM
cd ..
python -X utf8 -m crm.import_prospects --reset

# 7. Enrichissement téléphones
python -X utf8 -m crm.enrich_phones

# 8. Lance le CRM
python -X utf8 -m crm.run
```

## Le CRM en bref

- **Dashboard** — KPIs (500 prospects par catégorie/stage), calls semaine, RDV 2 calés, payback moyen
- **Prospects** — table filtrable + recherche + bouton 📞 cold call (téléphone cliquable `tel:`)
- **Prospect Detail** — identité éditable + audit live + timeline complète
- **Briefing live** — port complet du cold call (audit + ROI calculator interactif + Belfort objections + save direct DB)
- **Pipeline kanban** — drag & drop pour changer stage
- **Activités** — RDV à venir, relances dues

Voir [`crm/README.md`](crm/README.md) pour les détails techniques.

## Mutualisation entre collaborateurs

⚠️ Le CRM est **local-first** (SQLite). Chacun a sa propre base, **les données ne sont pas mutualisées** entre toi et tes collègues.

Pour collab temps réel, migration vers Supabase Postgres prévue (3-4h de travail). En attendant :
- Le **code** est synchronisé via GitHub
- Les **données** (prospects bruts) sont partagées via Drive privé (RGPD-safe)
- Les **calls/notes/stages** restent locaux à chacun

Voir issue / TODO pour Supabase migration.

## Données sensibles

Le `.gitignore` exclut **scrupuleusement** :
- `.env` (clés API)
- `**/data/*.csv` `*.json` `*.xlsx` (prospect data RGPD)
- `**/data/inputs/*` (RocketReach raw RGPD)
- `**/data/briefings/*` (notes de call)
- `crm/data/*.db` (base SQLite avec emails + tel)
- `__pycache__/`, `*.pyc`, `.venv/`

**Ne JAMAIS désactiver ces règles sur un repo public.**

## Stack

- **Python 3.11+**
- **Flask 3** (CRM)
- **SQLite** (DB locale)
- **Jinja2** (templates)
- **htmx** (interactivité, CDN)
- **requests** (audits live)
- Custom CSS (palette Mad Makers : noir profond + jaune chaud)

## Repos GitHub

- Principal : https://github.com/darthmaick/mad-makers-prospection
- Mirror : https://github.com/directedbymaick/madmakers-prospection
