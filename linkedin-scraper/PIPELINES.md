# Mad Makers — Stratégie deux-canaux (cold call vs cold email)

Ce dossier `linkedin-scraper/scripts/` contient deux pipelines distincts, à lancer
selon le canal de prospection visé. Ne pas mélanger.

## Constat

Tous les ICP ne sont pas atteignables par cold email :

| Segment | Présence LinkedIn | Email pro identifiable | Canal optimal |
|---|---:|---:|---|
| Artisan BTP / TPE 1-3p | <20% | Très rare | **Téléphone** |
| Resto traditionnel | 20-40% | Rare | Email + téléphone |
| Cabinet santé libéral | 30-50% | Variable | Email + téléphone |
| Agences immo | 60-80% | Bonne | **Email** |
| PME 5-50 salariés | 70-90% | Quasi systématique | **Email** |

Donc on route les ICP vers le bon canal au lieu de chercher des emails là où il
n'y en a pas.

---

## Canal A — Cold call (INSEE-first)

**Quand l'utiliser** : artisans BTP, TPE solo, micro-entreprises, segments où les
dirigeants ne sont pas sur LinkedIn.

**Pipeline** :
1. `source_france_50_active.py` (ou variante) → scrape INSEE par APE+département
2. Enrichit via Google Places → garde uniquement ceux **avec téléphone Google
   et sans site web**
3. Output : Excel avec téléphone direct

**Workflow ensuite** : démarchage téléphonique manuel, pas d'enrichissement
LinkedIn ni email.

```bash
python -X utf8 scripts/source_france_50_active.py
# -> data/prospects_france50_active_YYYYMMDD.xlsx
```

**Output type** : Excel avec colonnes Téléphone, Note Google, Effectif, Forme juridique,
Adresse complète. Les colonnes Email/Dirigeant/LinkedIn sont laissées vides.

---

## Canal B — Cold email (LinkedIn-first)

**Quand l'utiliser** : agences immo, PME 5-50, cabinets groupés, secteurs avec
forte présence LinkedIn.

**Pipeline** :
1. **Toi (manuel)** : tu construis ta search Sales Navigator avec les filtres
   pertinents (industry, geo, company size, function = Owner / CEO / Founder /
   Gérant), copie l'URL.
2. **Phantombuster "Sales Navigator Search Export"** → tu lances le Phantom
   avec l'URL → il produit un CSV avec profileUrl, fullName, companyName,
   companyUrl, title, location, etc.
3. `source_sales_nav_first.py` → ingère le CSV, matche chaque entreprise sur
   INSEE (par nom + ville), enrichit avec SIRET / raison sociale / effectif /
   forme juridique / âge entreprise. Optionnel : check Google Places pour
   filtrer les sans-site.
4. Output : CSV "rocket_reach_ready" avec toutes les colonnes Phantombuster +
   enrichissement INSEE + signal sans_site / site_existant.
5. **Toi (manuel)** : import dans Rocket Reach → emails extraits.
6. **Toi (manuel)** : cold email + audit personnalisé via le pipeline
   `madmakers-prospection-main/`.

```bash
python -X utf8 scripts/source_sales_nav_first.py \
    --input "C:/path/to/phantombuster_export.csv" \
    --check-website \
    --only-no-site
# -> data/rocket_reach_ready_sans_site_YYYYMMDD.csv
```

**Options** :
- `--check-website` : vérifie chaque entreprise via Google Places (~0.4s/ligne)
- `--only-no-site` : ne garde que les sans-site dans l'output (implique
  --check-website)
- `--min-effectif N` : filtre par effectif minimum (1, 5, 10...)
- `--limit N` : limite aux N premières lignes (utile pour tests)

**Output type** : CSV avec toutes les colonnes Phantombuster d'origine + colonnes
ajoutées : `siret`, `siren`, `raison_sociale`, `effectif_label`, `forme_juridique`,
`date_creation_insee`, `has_website`, `signal`, `match_insee`, `match_quality`.

---

## Cas particuliers / edge cases

**Match INSEE ambigu** (`match_quality = "ambigu"`) : plusieurs entreprises
INSEE matchent le nom commercial sans correspondance exacte avec la ville.
Le script prend le premier résultat mais la valeur est marquée — à vérifier
manuellement avant de cibler.

**Pas de match INSEE** (`match_insee = "no"`) : l'entreprise existe sur
LinkedIn mais pas trouvable dans INSEE par son nom commercial. Causes :
- Nom commercial très différent de la raison sociale (ex. "Le Bistrot du Coin"
  alors que la SIREN est "SARL DUPONT MARTIN")
- Entreprise étrangère
- Auto-entrepreneur sans raison sociale formalisée

→ On garde le prospect dans le CSV (Rocket Reach n'a pas besoin du SIRET pour
trouver l'email) mais on ne peut pas valider le signal sans-site.

**Société active mais ferme Google** (`signal = "ferme"`) : Google indique
CLOSED_PERMANENTLY/TEMPORARILY → à exclure.

---

## Quel script pour quel usage

| Tu veux... | Script |
|---|---|
| Liste artisans/TPE sans site avec téléphone direct | `source_france_50_active.py` |
| Liste sans site multi-secteur Nouvelle-Aquitaine | `source_multi_sector.py` |
| Convertir ton export Sales Nav en CSV Rocket Reach-ready | **`source_sales_nav_first.py`** |
| Trouver les dirigeants d'un batch INSEE existant | `enrich_dirigeants_linkedin.py` |
| Vérifier l'absence de site sur une liste de noms | `check_sites_v2.py` |

---

## Pour le pipeline officiel (`madmakers-prospection-main/`)

Ce dossier `linkedin-scraper/` est complémentaire. Le pipeline officiel
(`madmakers-prospection-main/`) reste la référence pour :
- Génération des cold emails (templates strictes)
- Génération des audits 1-pager
- Création des drafts Gmail
- Export Folk CRM
- Cron des relances J+4 et J+10

Workflow combiné typique :
1. Sourcing par canal (un des scripts ci-dessus)
2. Si Sales Nav-first : Rocket Reach pour les emails
3. Import des prospects + emails dans le batch JSON du pipeline officiel
4. `/madmakers-prospection` pour la génération + Gmail drafts + Folk
