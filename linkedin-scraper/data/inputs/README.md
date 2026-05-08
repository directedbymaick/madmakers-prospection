# Dossier `inputs/` — sources RocketReach (NON commitées)

Ce dossier doit contenir les CSVs **RocketReach bulk export** servant de source au pipeline triage.

## Contenu attendu

Format : `rocketreach_bulk_<range>_<date>_<id>.csv`

Exemple :
```
rocketreach_bulk_100_20260507_v9RvazD.csv
rocketreach_bulk_101-200_20260507_0V5m28t.csv
rocketreach_bulk_201-300_20260507_KuL8LKU.csv
rocketreach_bulk_301-400_20260507_w4WrqtK.csv
rocketreach_bulk_401-500_20260507_6XU85OQ.csv
```

## Pourquoi pas en git ?

Ces fichiers contiennent **des données personnelles** (emails, noms, téléphones, LinkedIn URL de prospects français nominatifs). Les push sur un repo public est une **violation RGPD** (art. 5, 32, 35).

## Comment les obtenir (collaborateur)

1. Demander à Maïck le **lien Google Drive / WeTransfer privé** où sont stockés les CSVs Mad Makers
2. Télécharger les 5 fichiers `rocketreach_bulk_*.csv`
3. Les placer dans ce dossier (`linkedin-scraper/data/inputs/`)
4. Récupérer aussi le triage final : `prospects_triage_strict_<date>_recheck.csv` à placer dans `linkedin-scraper/data/`
5. Lancer le setup CRM (voir racine `setup.sh` ou `setup.bat`)

## Source originale (Maïck)

Export RocketReach via UI :
- Sélection bulk de 100 prospects max par export
- Format CSV avec toutes les colonnes (Phone, Mobile Phone, Office Phone, Other Phones inclus)
- Export depuis l'onglet "Bulk lookup" après avoir uploadé une liste de profils LinkedIn (depuis Phantombuster Sales Navigator search export)
