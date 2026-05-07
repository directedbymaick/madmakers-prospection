# CLAUDE.md — Mad Makers Prospection Pipeline

## Contexte

**Mad Makers** est une agence digitale dirigée par Maïck (COO).  
Ce projet est un pipeline de prospection cold email ciblant les **restaurants traditionnels en Nouvelle-Aquitaine** (Landes 40, Pays Basque 64, Charente-Maritime 17, Dordogne 24) sans site web, ticket 1 000–1 500 €.

L'objectif final : produire des **fichiers Excel de prospects enrichis** (nom, SIRET, téléphone, note Google, dirigeant, email) prêts à importer dans Google Sheets ou Folk CRM.

---

## Structure du projet

```
madmakers-prospection-main/
├── .env                        ← Clés API (ne jamais commiter)
├── config/icp.yaml             ← Critères de ciblage (APE, départements, note min…)
├── scripts/
│   ├── source_restaurants.py   ← Scrape INSEE SIRENE + enrichit via Google Places
│   ├── gen_outputs.py          ← Génère cold emails + audits 1-pager (Markdown)
│   ├── make_excel.py           ← Génère le fichier Excel final (openpyxl)
│   └── recalc.py               ← Recalcule les formules Excel via LibreOffice
├── data/
│   ├── batch_YYYYMMDD.json     ← Données brutes scrappées
│   ├── outputs_YYYYMMDD.md     ← Cold emails + audits générés
│   ├── folk_import_YYYYMMDD.csv← Export pour Folk CRM
│   └── madmakers_prospects_YYYYMMDD.xlsx ← Fichier Excel final
├── templates/
│   └── audit_structure.md      ← Template audit 1-pager
└── CLAUDE.md                   ← Ce fichier
```

---

## Clés API configurées (.env)

| Variable | Usage |
|---|---|
| `INSEE_API_KEY` | SIRENE v3.11 — auth header `X-INSEE-Api-Key-Integration` |
| `GOOGLE_API_KEY` | Google Places API (New) — enrichissement GMB |
| `PAPPERS_API_KEY` | Dirigeants (crédits épuisés — utiliser societe.com à la place) |
| `MADMAKERS_FROM_EMAIL` | contact@madmakers.fr |
| `MADMAKERS_LANDING_URL` | https://madmakers.fr/restaurants |

---

## Workflow complet — Produire un Excel de prospects

### Étape 1 — Scraper les restaurants (INSEE + Google Places)

```bash
python -X utf8 scripts/source_restaurants.py --dept 40 --limit 30
```

- Résultats dans `data/batch_YYYYMMDD.json`
- `--dept` accepte plusieurs valeurs : `40 64 17 24`
- Fixer la date du jour dans le nom de fichier si nécessaire

**Points critiques INSEE SIRENE v3.11 :**
- URL : `https://api.insee.fr/api-sirene/3.11/siret`
- Auth : header `X-INSEE-Api-Key-Integration: {INSEE_API_KEY}` (pas d'OAuth2)
- Syntaxe Lucene : `periode(activitePrincipaleEtablissement:"56.10A" AND etatAdministratifEtablissement:A) AND codePostalEtablissement:[40000 TO 40999]`
- Le code APE **doit inclure le point** : `"56.10A"` pas `"5610A"`
- Filtre effectif : exclure uniquement les tranches > 50 salariés (garder "NN" = non déclaré)

### Étape 2 — Enrichir les dirigeants (societe.com)

Pappers API épuisée. Utiliser **WebFetch sur societe.com** pour chaque SIREN :

```
URL : https://www.societe.com/cgi-bin/recherche?rncs={SIREN}
Prompt : "Trouve le nom du dirigeant (gérant, président) de cette entreprise."
```

Lancer en parallèle par batch de 10 pour les 30 SIRENs.

### Étape 3 — Rechercher les emails

Sources accessibles (dans l'ordre de fiabilité) :
1. **societe.com** — a les emails mais derrière un bouton "Révéler" (non scrapable automatiquement)
2. **Pages Jaunes** → bloqué 403
3. **Facebook** → nécessite login
4. **Google Search** → utiliser WebSearch si disponible : `"{nom resto}" "{ville}" email contact`
5. **Annuaires locaux** (tourisme landes, tourisme64, etc.)

Pour les restos sans site web, les emails sont rares. Noter ce qu'on trouve et laisser la colonne vide sinon.

### Étape 4 — Mettre à jour et générer l'Excel

Editer `scripts/make_excel.py` : remplir les champs `email` (index 17) et `dirigeant` (index 18) dans chaque tuple de la liste `prospects`.

Format de chaque ligne :
```python
(#, "Nom commercial", "Raison sociale", "SIRET", "SIREN",
 "Ville", "Dept (XX)", "Adresse", "CP", "Telephone",
 note_float, nb_avis_int, "Type", "site_web", "signal",
 score_int, "YYYY-MM-DD", "email@example.com", "PRENOM NOM", "A contacter")
```

Puis régénérer :
```bash
python -X utf8 scripts/make_excel.py
```

Fichier produit : `data/madmakers_prospects_YYYYMMDD.xlsx`

### Étape 5 — Importer dans Google Sheet

Google Sheets est **inaccessible via le navigateur Claude** (domaine bloqué).  
→ Donner le fichier Excel à Maïck pour import manuel :  
**Fichier → Importer → Remplacer la feuille de calcul**

---

## Format du fichier Excel (20 colonnes)

| Col | Champ | Notes |
|---|---|---|
| A | # | Numéro |
| B | Nom commercial | Nom Google Maps |
| C | Raison sociale | Nom légal SIRENE |
| D | SIRET | 14 chiffres |
| E | SIREN | 9 chiffres |
| F | Ville | |
| G | Departement | ex: "Landes (40)" |
| H | Adresse | |
| I | Code postal | |
| J | Telephone | |
| K | Note Google | Float — vert si ≥ 4.5 |
| L | Nb avis | Int — vert si note ≥ 4.5 |
| M | Type etablissement | |
| N | Site web | Vide si sans site |
| O | Signal | "sans_site" ou autre |
| P | Score ICP | 0–100 |
| Q | Date creation | YYYY-MM-DD |
| R | Email prospect | Orange — à remplir |
| S | Dirigeant | Orange — à remplir |
| T | Statut | Jaune — "A contacter" par défaut |

**Style :** en-tête bleu foncé (#1a3c6e), lignes alternées blanc/bleu clair, filtre auto, ligne 1 figée.

---

## Alertes à vérifier sur chaque batch

Avant de livrer l'Excel, vérifier via societe.com :
- Entreprise **en liquidation** → marquer dans Statut : "Liquidation — vérifier"
- Dirigeant **parti récemment** → noter "(ancien)" dans la colonne Dirigeant
- Établissement **fermé** (état "F" dans SIRENE) → ne pas inclure

---

## Domaines accessibles via navigateur Claude (Claude in Chrome)

- ✅ Google Search (via onglet déjà ouvert — ne pas naviguer vers nouvelle URL)
- ✅ societe.com (WebFetch)
- ✅ WebFetch sur la plupart des sites publics
- ❌ docs.google.com (bloqué)
- ❌ pappers.fr (rendu JS, non scrapable sans navigateur)
- ❌ pagesjaunes.fr (403)
- ❌ facebook.com (login requis)

---

## Commandes clés

```bash
# Lancer le scraping complet (dept 40 = Landes, 30 prospects)
python -X utf8 scripts/source_restaurants.py --dept 40 --limit 30

# Générer cold emails + audits
python -X utf8 scripts/gen_outputs.py

# Générer l'Excel
python -X utf8 scripts/make_excel.py

# Toujours utiliser -X utf8 sur Windows (évite UnicodeEncodeError)
```

---

## Ce que Maïck attend à chaque session

1. **"Lance un batch [département]"** → Scraper + enrichir dirigeants + chercher emails + générer Excel
2. **"Ajoute les dirigeants"** → WebFetch societe.com sur tous les SIRENs du batch courant
3. **"Génère les emails de prospection"** → `gen_outputs.py` sur le batch JSON du jour
4. **"Mets à jour le Sheet"** → Générer Excel + donner instructions d'import (Google Sheets inaccessible directement)

**Date du jour** : toujours utiliser la date réelle pour nommer les fichiers (`batch_YYYYMMDD.json`, etc.)
