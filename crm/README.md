# Mad Makers CRM

CRM local-first pour la prospection Mad Makers — pipeline 500 prospects + briefing cold call temps réel + tracking calls/RDV/devis.

## Setup

```bash
# 1. Installer les deps Python
pip install -r crm/requirements.txt

# 2. Importer les 500 prospects depuis le CSV triage le plus récent
python -X utf8 -m crm.import_prospects

# 3. Lancer le serveur local
python -X utf8 -m crm.run

# → http://127.0.0.1:8000
```

## Pages

- **Dashboard** (`/`) — KPIs, pipeline overview, activité récente, à faire aujourd'hui
- **Prospects** (`/prospects`) — table filtrable (catégorie / stage / ville) + recherche
- **Prospect Detail** (`/prospects/<id>`) — identité éditable + audit + timeline + calls
- **Briefing live** (`/prospects/<id>/call/<id>`) — port complet du cold call avec :
  - Audit factuel du site
  - Arguments financiers
  - Questions découverte (4 thèmes)
  - Pain points cochables (variables selon catégorie + audit)
  - **ROI Calculator interactif** (gain mensuel + payback en mois, verdict couleur)
  - Future pacing
  - Demande visuels
  - Pitch RDV 2 (assumed close Belfort)
  - Objections Belfort (Loop : Agree → Bridge → Reinforce → Close)
  - Closing patterns
  - Outcome Call 1 + préparation Call 2
  - **Save → DB direct** (plus de download HTML/JSON)
- **Pipeline** (`/pipeline`) — kanban drag & drop pour changer le stage
- **Activités** (`/activities`) — RDV à venir, relances dues, timeline complète

## Stack

- **Backend** : Flask 3 + SQLite (single-file DB, zéro infra)
- **Frontend** : Jinja templates + htmx (CDN) + vanilla JS pour le briefing live + custom CSS
- **Audit live** : réutilise la fonction `audit_site()` de `linkedin-scraper/scripts/cold_call.py`
- **Import** : depuis les CSVs du pipeline triage Mad Makers

## Pipeline stages

`a_contacter` → `email_envoye` → `en_relance` → `rdv_1_calé` → `rdv_1_fait` → `rdv_2_calé` → `rdv_2_fait` → `devis_envoyé` → `signé` (ou `perdu` / `dormant`)

Chaque cold call sauvegardé met à jour automatiquement le stage selon le statut choisi.

## Structure

```
crm/
  app.py                  # Flask app + routes + API endpoints
  models.py               # Queries SQLite (prospects, calls, activities, audits, emails)
  db.py                   # Connection helpers + auto-init
  config.py               # Stages, catégories, types d'activité
  briefing_data.py        # Données statiques briefing (pains, questions, objections, etc.)
  schema.sql              # DDL SQLite
  import_prospects.py     # CLI d'import depuis CSV triage
  run.py                  # Entry point serveur
  templates/              # Jinja2 (base, dashboard, prospects, briefing, pipeline, activities, imports)
  static/css/styles.css   # Mad Makers visual identity
  data/crm.db             # SQLite (gitignored)
```

## Notes

- **Local-first** : tourne sur `127.0.0.1`, données dans `crm/data/crm.db` (jamais commit)
- **Auto-save** du briefing toutes les ~600ms d'inactivité (POST sur `/api/calls/<id>/save`)
- **Stage update** automatique sur sauvegarde finale du call
- Pas d'auth pour le MVP (single-user)

## Améliorations à venir (next iterations)

- Envoi automatique d'emails (Gmail/SMTP integration)
- OAuth Calendly pour caler RDV depuis le CRM
- Génération mail récap auto post-call
- Multi-user / auth si déploiement cloud
- Mode mobile responsive avancé
