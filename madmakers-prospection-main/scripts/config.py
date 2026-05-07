"""
Config centrale Mad Makers Prospection.

Charge le fichier .env à la racine du projet et expose les variables
d'environnement + les constantes de config (ICP, zones).

Usage dans les autres scripts :

    from config import settings, icp, ensure_key

    ensure_key("INSEE_API_KEY")
    api_key = settings.INSEE_API_KEY
    zones = icp["zones_prioritaires"]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import yaml
from dotenv import load_dotenv


# ----- Chemins projet ------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
ICP_PATH = ROOT / "config" / "icp.yaml"
DATA_DIR = ROOT / "data"
TEMPLATES_DIR = ROOT / "templates"


# ----- Chargement .env -----------------------------------------------------

if not ENV_PATH.exists():
    print(
        f"[WARN] Pas de fichier .env trouvé à {ENV_PATH}.\n"
        "       Copie config/.env.example vers .env et remplis les clés.\n"
        "       Les scripts vont échouer sur les appels API tant que les clés manquent.",
        file=sys.stderr,
    )
else:
    load_dotenv(ENV_PATH)


# ----- Settings (variables d'env) ------------------------------------------

settings = SimpleNamespace(
    # APIs
    INSEE_API_KEY=os.getenv("INSEE_API_KEY", ""),
    INSEE_API_SECRET=os.getenv("INSEE_API_SECRET", ""),
    GOOGLE_API_KEY=os.getenv("GOOGLE_API_KEY", ""),
    PAPPERS_API_KEY=os.getenv("PAPPERS_API_KEY", ""),
    # Branding Mad Makers
    FROM_NAME=os.getenv("MADMAKERS_FROM_NAME", "Mad Makers"),
    FROM_EMAIL=os.getenv("MADMAKERS_FROM_EMAIL", "contact@madmakers.fr"),
    LANDING_URL=os.getenv("MADMAKERS_LANDING_URL", "https://madmakers.fr/restaurants"),
    PHONE=os.getenv("MADMAKERS_PHONE", ""),
)


# ----- ICP (config/icp.yaml) -----------------------------------------------

def _load_icp() -> dict:
    if not ICP_PATH.exists():
        print(f"[ERROR] Pas de config ICP trouvée à {ICP_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(ICP_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


icp = _load_icp()


# ----- Helpers -------------------------------------------------------------

def ensure_key(name: str) -> None:
    """Plante proprement avec message clair si une clé manque."""
    value = getattr(settings, name, None)
    if not value:
        print(
            f"[ERROR] La clé {name} est manquante.\n"
            f"        Édite ton fichier .env et ajoute : {name}=xxxx\n"
            f"        (template : config/.env.example)",
            file=sys.stderr,
        )
        sys.exit(1)


def info(msg: str) -> None:
    print(f"[INFO] {msg}")


def warn(msg: str) -> None:
    print(f"[WARN] {msg}", file=sys.stderr)


def error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "site_snapshots").mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    # Petit debug : affiche la config chargée (sans les secrets)
    print("ROOT:", ROOT)
    print("ENV loaded:", ENV_PATH.exists())
    print("ICP niche:", icp["niche"]["libelle"])
    print("ICP zones:", [z["nom"] for z in icp["zones_prioritaires"]])
    print("FROM:", settings.FROM_NAME, "<" + settings.FROM_EMAIL + ">")
    for k in ("INSEE_API_KEY", "GOOGLE_API_KEY", "PAPPERS_API_KEY"):
        v = getattr(settings, k)
        print(f"{k}:", "OK" if v else "MANQUANT")
