"""
enrich_pappers.py — Ajoute les dirigeants + CA via Pappers API.

Pour chaque prospect du batch, appelle Pappers par SIREN pour récupérer :
  - Nom du ou des dirigeants
  - Fonction (président, gérant, etc.)
  - Date de naissance (facultatif, pour personnaliser intro)
  - CA publié (si dispo, pour contextualiser le pitch)

Usage :
    python scripts/enrich_pappers.py data/batch_20260416.json

Plan gratuit Pappers = 500 req/mois.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import requests

from config import info, warn, settings, ensure_key


PAPPERS_URL = "https://api.pappers.fr/v2/entreprise"


def enrich(siren: str) -> dict:
    ensure_key("PAPPERS_API_KEY")
    params = {"api_token": settings.PAPPERS_API_KEY, "siren": siren}
    try:
        resp = requests.get(PAPPERS_URL, params=params, timeout=15)
    except requests.exceptions.RequestException as e:
        warn(f"Pappers erreur réseau pour {siren} : {e}")
        return {}

    if resp.status_code == 429:
        warn(f"Pappers rate limit, pause 10s...")
        time.sleep(10)
        return enrich(siren)
    if resp.status_code == 404:
        warn(f"SIREN {siren} non trouvé sur Pappers")
        return {}
    if resp.status_code != 200:
        warn(f"Pappers HTTP {resp.status_code} pour {siren} : {resp.text[:200]}")
        return {}

    data = resp.json()

    # Dirigeants (on prend le premier "actif")
    dirigeants = data.get("representants", [])
    dirigeant = None
    for d in dirigeants:
        if not d.get("date_fin_mandat"):
            dirigeant = d
            break
    if not dirigeant and dirigeants:
        dirigeant = dirigeants[0]

    # Finances publiées (on prend le dernier exercice dispo)
    finances = data.get("finances", [])
    last_ca = None
    last_year = None
    if finances:
        # Pappers renvoie les finances par ordre chronologique variable, on trie
        valid = [f for f in finances if f.get("chiffre_affaires") is not None]
        if valid:
            valid.sort(key=lambda f: f.get("annee", 0), reverse=True)
            last_ca = valid[0].get("chiffre_affaires")
            last_year = valid[0].get("annee")

    result = {
        "pappers_found": True,
        "dirigeant_nom": (
            f"{dirigeant.get('prenom', '')} {dirigeant.get('nom', '')}".strip()
            if dirigeant else None
        ),
        "dirigeant_fonction": dirigeant.get("qualite") if dirigeant else None,
        "dirigeant_age": dirigeant.get("age") if dirigeant else None,
        "ca_dernier": last_ca,
        "ca_annee": last_year,
        "capital": data.get("capital"),
        "forme_juridique": data.get("forme_juridique"),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrichissement Pappers Mad Makers")
    parser.add_argument("batch_file", type=str, help="Chemin vers le batch JSON")
    args = parser.parse_args()

    batch_path = Path(args.batch_file)
    if not batch_path.exists():
        print(f"[ERROR] Fichier introuvable : {batch_path}", file=sys.stderr)
        sys.exit(1)

    with open(batch_path, "r", encoding="utf-8") as f:
        batch = json.load(f)

    prospects = batch.get("prospects", [])
    info(f"Enrichissement Pappers sur {len(prospects)} prospects...")

    for i, p in enumerate(prospects, start=1):
        siren = p.get("siren")
        if not siren:
            warn(f"Prospect sans SIREN : {p.get('raison_sociale')}")
            continue
        data = enrich(siren)
        p.update(data)
        info(
            f"  {i}/{len(prospects)} : {p.get('raison_sociale', '?')[:40]} → "
            f"{data.get('dirigeant_nom') or 'dirigeant inconnu'}"
        )
        time.sleep(0.3)  # Gentle rate limiting

    with open(batch_path, "w", encoding="utf-8") as f:
        json.dump(batch, f, ensure_ascii=False, indent=2)

    info(f"Batch mis à jour : {batch_path}")


if __name__ == "__main__":
    main()
