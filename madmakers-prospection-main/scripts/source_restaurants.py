"""
source_restaurants.py — Sourcing batch quotidien Mad Makers.

Combine INSEE SIRENE (liste d'établissements légale + SIRET) avec
Google Places (présence digitale GMB + website + reviews) pour produire
un batch scoré de restaurants prospects dans les départements ciblés.

Usage :
    python scripts/source_restaurants.py --zone 40,64 --limit 30
    python scripts/source_restaurants.py --zone 40 --limit 10 --out data/test.json

Produit : data/batch_YYYYMMDD.json (ou --out si précisé)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

from config import DATA_DIR, icp, info, warn, error, settings, ensure_key, ensure_data_dir


INSEE_SIRENE_URL = "https://api.insee.fr/api-sirene/3.11/siret"

GOOGLE_PLACES_SEARCH = "https://places.googleapis.com/v1/places:searchText"
GOOGLE_PLACE_DETAILS = "https://places.googleapis.com/v1/places/{place_id}"


# ---------------------------------------------------------------------------
# INSEE
# ---------------------------------------------------------------------------

def insee_headers() -> dict:
    """Retourne les headers d'authentification INSEE (clé directe)."""
    ensure_key("INSEE_API_KEY")
    return {
        "X-INSEE-Api-Key-Integration": settings.INSEE_API_KEY,
        "Accept": "application/json",
    }


def query_sirene(dept_code: str, ape_raw: str, limit: int) -> list[dict]:
    """Liste les établissements actifs d'un département pour un code APE donné."""
    filtres = icp["filtres"]
    dept_int = int(dept_code)
    cp_min = dept_int * 1000
    cp_max = cp_min + 999
    q = (
        f'periode(activitePrincipaleEtablissement:"{ape_raw}" AND etatAdministratifEtablissement:A) '
        f'AND codePostalEtablissement:[{cp_min} TO {cp_max}]'
    )
    params = {
        "q": q,
        "nombre": min(limit, 1000),
        "tri": "dateDernierTraitementEtablissement desc",
    }
    headers = insee_headers()
    resp = requests.get(INSEE_SIRENE_URL, params=params, headers=headers, timeout=30)
    if resp.status_code == 404:
        warn(f"Aucun établissement INSEE pour département {dept_code}")
        return []
    if resp.status_code != 200:
        error(f"INSEE SIRENE erreur {resp.status_code} : {resp.text[:300]}")
        return []

    etabs = resp.json().get("etablissements", [])
    results = []
    for e in etabs:
        unite = e.get("uniteLegale", {})
        adresse = e.get("adresseEtablissement", {})
        tranche = unite.get("trancheEffectifsUniteLegale") or ""
        # Filtrage effectif : on exclut uniquement les très grandes structures (>50)
        # "NN" = non employeur déclaré mais peut être indépendant avec staff informel → on garde
        if tranche in {"21", "22", "31", "32", "41", "42", "51", "52", "53"}:  # >50 salariés
            continue
        # Filtrage âge : date de création > 12 mois
        creation = unite.get("dateCreationUniteLegale")
        if creation:
            try:
                dt = datetime.fromisoformat(creation)
                if (datetime.now() - dt).days < filtres["age_entreprise_min_mois"] * 30:
                    continue
            except ValueError:
                pass

        results.append({
            "siret": e.get("siret"),
            "siren": e.get("siren"),
            "raison_sociale": unite.get("denominationUniteLegale")
                or f"{unite.get('prenom1UniteLegale', '')} {unite.get('nomUniteLegale', '')}".strip(),
            "nom_commercial": e.get("periodesEtablissement", [{}])[0].get("enseigne1Etablissement"),
            "adresse": format_adresse(adresse),
            "code_postal": adresse.get("codePostalEtablissement"),
            "ville": adresse.get("libelleCommuneEtablissement"),
            "departement": dept_code,
            "tranche_effectif": tranche,
            "date_creation": creation,
            "source_sirene": True,
        })
    return results


def format_adresse(a: dict) -> str:
    parts = [
        str(a.get("numeroVoieEtablissement") or "").strip(),
        a.get("typeVoieEtablissement") or "",
        a.get("libelleVoieEtablissement") or "",
    ]
    voie = " ".join(p for p in parts if p).strip()
    cp = a.get("codePostalEtablissement") or ""
    ville = a.get("libelleCommuneEtablissement") or ""
    return f"{voie}, {cp} {ville}".strip(", ")


# ---------------------------------------------------------------------------
# GOOGLE PLACES
# ---------------------------------------------------------------------------

def places_search(query: str) -> list[dict]:
    """Cherche un établissement sur Google Places par texte libre."""
    ensure_key("GOOGLE_API_KEY")
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_API_KEY,
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.formattedAddress,"
            "places.nationalPhoneNumber,places.websiteUri,places.rating,"
            "places.userRatingCount,places.primaryTypeDisplayName"
        ),
    }
    resp = requests.post(
        GOOGLE_PLACES_SEARCH,
        headers=headers,
        json={"textQuery": query, "languageCode": "fr"},
        timeout=15,
    )
    if resp.status_code != 200:
        warn(f"Places search échec ({resp.status_code}) pour '{query}' : {resp.text[:200]}")
        return []
    return resp.json().get("places", [])


def enrich_with_places(prospect: dict) -> dict:
    """Cherche la fiche GMB correspondante et enrichit le prospect."""
    query = (
        f"{prospect.get('nom_commercial') or prospect['raison_sociale']} "
        f"{prospect.get('ville') or ''}"
    ).strip()
    places = places_search(query)
    if not places:
        prospect["gmb_found"] = False
        return prospect

    # Prend le premier résultat (Google classe par pertinence)
    p = places[0]
    prospect.update({
        "gmb_found": True,
        "gmb_place_id": p.get("id"),
        "gmb_name": p.get("displayName", {}).get("text"),
        "gmb_address": p.get("formattedAddress"),
        "gmb_phone": p.get("nationalPhoneNumber"),
        "website": p.get("websiteUri"),
        "gmb_rating": p.get("rating"),
        "gmb_reviews_count": p.get("userRatingCount", 0),
        "gmb_type": p.get("primaryTypeDisplayName", {}).get("text"),
    })
    return prospect


# ---------------------------------------------------------------------------
# SCORING
# ---------------------------------------------------------------------------

def score(prospect: dict) -> int:
    """Calcule le score ICP d'un prospect (0-100)."""
    s = 0
    weights = icp["scoring"]

    if not prospect.get("website"):
        s += weights["site_web_inexistant"]["points"]
    # site_web_obsolete : déterminé à l'étape fetch_site.py, on le laisse à 0 ici

    if prospect.get("gmb_reviews_count", 0) >= 10:
        s += weights["gmb_actif"]["points"]

    dept = prospect.get("departement", "")
    for z in icp["zones_prioritaires"]:
        if z["code"] == dept:
            if z["priorite"] == 1:
                s += weights["zone_priorite_1"]["points"]
            else:
                s += weights["zone_priorite_2"]["points"]
            break

    tranche = prospect.get("tranche_effectif") or ""
    # Tranches 02 (3-5), 03 (6-9), 11 (10-19) correspondent à 3-19 salariés
    if tranche in {"02", "03", "11"}:
        s += weights["effectif_5_15"]["points"]

    return s


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Sourcing restaurants Mad Makers")
    parser.add_argument(
        "--zone",
        required=True,
        help="Codes département INSEE séparés par virgule (ex: 40,64,17,24)",
    )
    parser.add_argument("--limit", type=int, default=30, help="Nombre de prospects visés")
    parser.add_argument("--out", type=str, default=None, help="Chemin fichier sortie")
    parser.add_argument("--skip-places", action="store_true", help="Ne pas appeler Google Places (test)")
    args = parser.parse_args()

    ensure_data_dir()
    depts = [d.strip() for d in args.zone.split(",") if d.strip()]
    ape_raw = icp["niche"]["code_ape"]  # "56.10A" avec le point
    min_score = icp["score_minimum"]

    info(f"Sourcing {icp['niche']['libelle']} (APE {ape_raw}) sur départements : {depts}")

    all_prospects = []
    for dept in depts:
        # On prend un peu plus que le quota pour compenser les rejets
        fetch_n = min(args.limit * 10, 1000)  # large fetch pour compenser les rejets
        batch = query_sirene(dept, ape_raw, fetch_n)
        info(f"  Dept {dept} : {len(batch)} établissements SIRENE")
        all_prospects.extend(batch)

    if not all_prospects:
        error("Aucun établissement INSEE trouvé. Arrêt.")
        sys.exit(1)

    # Enrichissement Google Places (si pas skipé)
    if args.skip_places:
        warn("Skip Google Places — le scoring sera partiel.")
    else:
        info(f"Enrichissement Google Places sur {len(all_prospects)} établissements...")
        for i, p in enumerate(all_prospects):
            enrich_with_places(p)
            if (i + 1) % 10 == 0:
                info(f"  {i + 1}/{len(all_prospects)} enrichis")

    # Scoring + filtrage
    for p in all_prospects:
        p["score"] = score(p)

    qualifies = sorted(
        [p for p in all_prospects if p["score"] >= min_score],
        key=lambda x: x["score"],
        reverse=True,
    )[: args.limit]

    info(f"Prospects qualifiés : {len(qualifies)}/{len(all_prospects)} (seuil {min_score})")

    # Output
    out_path = Path(args.out) if args.out else DATA_DIR / f"batch_{datetime.now():%Y%m%d}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "niche": icp["niche"]["libelle"],
            "zones": depts,
            "prospects": qualifies,
        }, f, ensure_ascii=False, indent=2)

    info(f"Batch écrit : {out_path}")


if __name__ == "__main__":
    main()
