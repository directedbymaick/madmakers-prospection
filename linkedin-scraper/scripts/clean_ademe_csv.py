"""clean_ademe_csv.py — Étape 1 du pipeline Carnet Plein®.

Prend un CSV brut produit par scrape_rge_ademe.py et sort une version propre :
- Colonnes utiles uniquement : siret, prenom, nom, entreprise, ville, email,
  phone_office, site_url, linkedin_url, domaine, notes
- Tentative de split prenom/nom quand le nom_complet ressemble à une personne
  physique (artisan en EI). Heuristique conservative : si on n'est pas sûr,
  on laisse vide → l'enrichissement via API gouv prendra le relai.
- linkedin_url ajouté vide pour Phantom Buster.

Usage :
    python -X utf8 scripts/clean_ademe_csv.py [csv_input]
"""
import argparse
import csv
import logging
import re
import sys
from pathlib import Path

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    datefmt="%H:%M:%S")

# Tokens qui révèlent une entreprise → pas une personne physique
ENTREPRISE_TOKENS = {
    # Formes juridiques
    "SARL", "SAS", "SASU", "EURL", "SCI", "SCOP", "EI", "EIRL", "SC", "SA",
    "SNC", "GIE", "SCM", "SELARL",
    # Mots clés génériques
    "ETS", "ETABLISSEMENT", "ETABLISSEMENTS",
    "ENTREPRISE", "ENTREPRISES", "SOCIETE", "STE", "COMPAGNIE", "GROUPE",
    "FRERES", "FRERE", "FILS", "FILLE", "CIE",
    # BTP / artisanat
    "BTP", "BATIMENT", "BATIMENTS", "BAT", "ARTISAN", "ARTISANS",
    "CONSTRUCTION", "CONSTRUCTIONS", "RENOVATION", "RENOV", "RENO",
    "MAINTENANCE", "DEPANNAGE", "REPARATION", "INSTALLATION",
    "INSTALLATIONS", "SERVICE", "SERVICES", "TECHNIQUE", "TECHNIQUES",
    "PROFESSIONNEL", "EXPERT", "PRO",
    # Métiers chauffage / plomberie / énergie
    "CHAUFFAGE", "CHAUFFAGISTE", "PLOMBERIE", "PLOMBIER", "PLOMB",
    "GAZ", "FIOUL", "FUEL", "POMPE", "PAC", "POMPES",
    "CHAUDIERE", "CHAUDIERES", "POELE", "POELES", "INSERT",
    "SOLAIRE", "THERMIQUE", "THERMIQUES", "SANITAIRE", "SANITAIRES",
    "ENERGIE", "ENERGIES", "CLIMATISATION", "CLIM", "VENTILATION",
    "ELEC", "ELECTRICITE", "ELECTRICIEN", "CARRELAGE", "MENUISERIE",
    "MENUISIER", "ISOLATION", "COUVERTURE", "ZINGUERIE",
    # Géo (souvent dans les raisons sociales)
    "FRANCE", "PARIS", "IDF", "GRAND", "EST", "OUEST", "NORD", "SUD",
    "EURO", "EUROPE",
    # Connecteurs
    "ET", "&", "+", "ASSOCIES", "ASSOCIATIONS", "COOPERATIVE", "COOPERATIF",
}

# Mots ignorés pour les checks (articles, prépositions, prefixes nobiliaires)
SMALL_WORDS = {"DE", "DU", "DES", "LE", "LA", "LES", "L", "D", "AL", "EL"}


def looks_like_person(name: str) -> bool:
    """Heuristique conservative : renvoie True si name ressemble à une
    personne physique (peu de tokens, aucun mot-clé entreprise)."""
    if not name:
        return False
    tokens = [t for t in re.split(r"[\s'\-]+", name.upper()) if t]
    if len(tokens) < 2 or len(tokens) > 4:
        return False
    if any(t in ENTREPRISE_TOKENS for t in tokens):
        return False
    # rejette si un token n'a que des chiffres
    if any(t.isdigit() for t in tokens):
        return False
    # rejette si un token contient un chiffre (Schmidt2000)
    if any(any(c.isdigit() for c in t) for t in tokens):
        return False
    return True


def split_person_name(name: str) -> tuple[str, str]:
    """Split `Prenom Nom` ou `Nom Prenom`. Renvoie (prenom, nom).

    Heuristique : si tout en MAJ → first = nom, last = prenom (convention
    française des annuaires). Sinon : first = prenom, last = nom.
    """
    if not name:
        return "", ""
    # Strip prefixes Mr/Mme/M.
    cleaned = re.sub(r"^(M\.|Mme|Mr|Monsieur|Madame|Mlle)\s+", "", name.strip(),
                     flags=re.IGNORECASE)
    parts = re.split(r"\s+", cleaned.strip())
    parts = [p for p in parts if p]
    if len(parts) < 2:
        return "", cleaned.title()

    is_all_upper = name == name.upper()
    # Convention française annuaire : NOM Prenom (NOM en MAJ tout)
    if is_all_upper:
        # On suppose : 1er = nom de famille (ex : "DUPONT JEAN")
        # Sauf si 2+ mots significatifs : "DE LA FONTAINE PAUL" → nom = "DE LA FONTAINE", prenom = "PAUL"
        # Implémentation simple : dernier mot = prénom, le reste = nom
        prenom = parts[-1].title()
        nom = " ".join(parts[:-1]).title()
    else:
        # Mixed case : 1er = prénom, reste = nom
        prenom = parts[0].title()
        nom = " ".join(parts[1:]).title()
    return prenom, nom


def clean_csv(input_path: Path, output_path: Path):
    """Lit input_path (sortie de scrape_rge_ademe.py) et écrit une version propre."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    out_cols = ["siret", "prenom", "nom", "entreprise", "ville", "email",
                "phone_office", "site_url", "linkedin_url", "domaine", "notes"]

    n_total = 0
    n_split = 0
    n_with_email = 0
    n_with_phone = 0
    n_with_site = 0

    with open(input_path, "r", encoding="utf-8-sig", newline="") as fin, \
         open(output_path, "w", encoding="utf-8-sig", newline="") as fout:

        reader = csv.DictReader(fin)
        writer = csv.DictWriter(fout, fieldnames=out_cols)
        writer.writeheader()

        for row in reader:
            n_total += 1
            nom_complet = (row.get("nom_complet") or "").strip()
            entreprise = (row.get("entreprise") or "").strip() or nom_complet

            # Pas de split heuristique : trop de faux positifs ("Renovo Group" →
            # "Renovo / Group"). L'enrichissement étape 2 récupère le vrai
            # dirigeant via l'API recherche-entreprises.api.gouv.fr (officielle,
            # zero invention).
            prenom = ""
            nom = ""

            out = {
                "siret":        (row.get("siret") or "").strip(),
                "prenom":       prenom,
                "nom":          nom,
                "entreprise":   entreprise,
                "ville":        (row.get("ville") or "").strip(),
                "email":        (row.get("email") or "").strip().lower(),
                "phone_office": (row.get("phone_office") or "").strip(),
                "site_url":     (row.get("site_url") or "").strip(),
                "linkedin_url": "",  # vide pour Phantom Buster
                "domaine":      (row.get("domaine") or "").strip(),
                "notes":        (row.get("notes") or "").strip(),
            }

            if out["email"]:
                n_with_email += 1
            if out["phone_office"]:
                n_with_phone += 1
            if out["site_url"]:
                n_with_site += 1

            writer.writerow(out)

    log.info(f"Total          : {n_total}")
    log.info(f"  split person : {n_split} ({100*n_split//max(n_total,1)}%)")
    log.info(f"  avec email   : {n_with_email} ({100*n_with_email//max(n_total,1)}%)")
    log.info(f"  avec phone   : {n_with_phone} ({100*n_with_phone//max(n_total,1)}%)")
    log.info(f"  avec site    : {n_with_site} ({100*n_with_site//max(n_total,1)}%)")
    log.info(f"  sans site    : {n_total - n_with_site} (à enrichir étape 2)")
    log.info(f"CSV propre écrit : {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?",
                        help="CSV ADEME brut (par défaut : dernier fichier qualibat_rge_carnetplein_*.csv)")
    parser.add_argument("--output", help="Chemin du CSV nettoyé")
    args = parser.parse_args()

    inputs_dir = Path(__file__).resolve().parent.parent / "data" / "inputs"

    if args.input:
        input_path = Path(args.input)
    else:
        # Auto-pick le plus récent
        candidates = sorted(inputs_dir.glob("qualibat_rge_carnetplein_*.csv"),
                            key=lambda p: p.stat().st_mtime, reverse=True)
        # Exclure ceux qui finissent par _clean ou _enriched
        candidates = [p for p in candidates
                      if not p.stem.endswith(("_clean", "_enriched"))]
        if not candidates:
            log.error(f"Aucun CSV trouvé dans {inputs_dir}")
            sys.exit(1)
        input_path = candidates[0]
        log.info(f"Input auto-détecté : {input_path}")

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_name(input_path.stem + "_clean.csv")

    clean_csv(input_path, output_path)


if __name__ == "__main__":
    main()
