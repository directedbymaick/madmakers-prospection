"""
export_folk.py — Export batch JSON → CSV prêt à importer dans Folk CRM.

Folk accepte un CSV avec des champs personnalisés. On produit un CSV
avec les colonnes standard + des champs custom propres à Mad Makers
(score, audit URL, niche, zone).

Usage :
    python scripts/export_folk.py data/batch_20260416.json

Produit : data/folk_import_YYYYMMDD.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

from config import DATA_DIR, info


# Mapping colonnes Folk (renomme selon la convention du workspace Mad Makers)
FOLK_COLUMNS = [
    "Full Name",        # Dirigeant
    "Company",          # Raison sociale
    "Job Title",        # Fonction dirigeant
    "Email",            # (vide, à enrichir)
    "Phone",            # GMB phone ou SIRENE
    "Website",          # Site actuel (si existe)
    "Address",          # Adresse complète
    "City",             # Ville
    "Notes",            # Contexte prospection (structuré)
    "Tags",             # "resto, dept-40, score-XX, sans-site"
    # Champs custom Mad Makers
    "SIRET",
    "Score ICP",
    "Signal",           # "sans_site" / "site_obsolete" / "gmb_actif"
    "Séquence",         # "cold-resto-v1"
    "Étape",            # "J0-cold"
    "Statut",           # "à contacter"
    "Date ajout",
]


def build_note(p: dict) -> str:
    """Construit le bloc Notes structuré pour Folk."""
    audit = p.get("site_audit", {})
    parts = [
        f"SIGNAL : {signal_label(p)}",
        f"SOURCE : SIRENE + Google Places",
        f"DATE AJOUT : {datetime.now():%Y-%m-%d}",
        f"SCORE ICP : {p.get('score', 0)}/100",
    ]
    if p.get("gmb_reviews_count"):
        parts.append(f"GMB : {p.get('gmb_rating')} ★ ({p.get('gmb_reviews_count')} reviews)")
    if audit.get("has_site"):
        perf = (audit.get("performance") or {}).get("mobile_score")
        parts.append(f"SITE : {audit.get('url')} (perf mobile : {perf}/100)")
        if audit.get("generator"):
            parts.append(f"TECH : {audit.get('generator')}")
    else:
        parts.append("SITE : AUCUN site référencé")
    if p.get("ca_dernier"):
        parts.append(f"CA {p.get('ca_annee')} : {p.get('ca_dernier'):,}€".replace(",", " "))
    if p.get("tranche_effectif"):
        parts.append(f"EFFECTIF (tranche INSEE) : {p.get('tranche_effectif')}")
    parts.append("")
    parts.append("OFFRE VISÉE : Site vitrine + SEO local (1000-1500€)")
    parts.append("SÉQUENCE : cold-resto-v1")
    parts.append("ÉTAPE : J0-cold")
    parts.append("STATUT : à contacter")
    return "\n".join(parts)


def signal_label(p: dict) -> str:
    audit = p.get("site_audit", {})
    if not audit.get("has_site"):
        return "sans_site"
    perf = (audit.get("performance") or {}).get("mobile_score")
    if perf is not None and perf < 40:
        return "site_obsolete"
    if not audit.get("has_ssl"):
        return "site_obsolete_http"
    return "gmb_actif_site_moyen"


def build_tags(p: dict) -> str:
    tags = ["resto", f"dept-{p.get('departement', 'XX')}"]
    tags.append(f"score-{p.get('score', 0)}")
    tags.append(signal_label(p).replace("_", "-"))
    return ", ".join(tags)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Folk Mad Makers")
    parser.add_argument("batch_file", type=str, help="Chemin vers le batch JSON")
    parser.add_argument("--out", type=str, default=None, help="CSV sortie")
    args = parser.parse_args()

    batch_path = Path(args.batch_file)
    if not batch_path.exists():
        print(f"[ERROR] Fichier introuvable : {batch_path}", file=sys.stderr)
        sys.exit(1)

    with open(batch_path, "r", encoding="utf-8") as f:
        batch = json.load(f)

    prospects = batch.get("prospects", [])
    out_path = Path(args.out) if args.out else DATA_DIR / f"folk_import_{datetime.now():%Y%m%d}.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FOLK_COLUMNS)
        writer.writeheader()
        for p in prospects:
            writer.writerow({
                "Full Name": p.get("dirigeant_nom") or "",
                "Company": p.get("nom_commercial") or p.get("raison_sociale") or "",
                "Job Title": p.get("dirigeant_fonction") or "",
                "Email": "",  # à enrichir, V1 = vide
                "Phone": p.get("gmb_phone") or "",
                "Website": (p.get("site_audit", {}) or {}).get("url") or p.get("website") or "",
                "Address": p.get("adresse") or "",
                "City": p.get("ville") or "",
                "Notes": build_note(p),
                "Tags": build_tags(p),
                "SIRET": p.get("siret") or "",
                "Score ICP": p.get("score", 0),
                "Signal": signal_label(p),
                "Séquence": "cold-resto-v1",
                "Étape": "J0-cold",
                "Statut": "à contacter",
                "Date ajout": today,
            })

    info(f"CSV écrit : {out_path} ({len(prospects)} lignes)")
    info("Import dans Folk : Contacts → ⋯ → Import CSV → glisser le fichier.")


if __name__ == "__main__":
    main()
