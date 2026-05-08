"""
reclassify_triage.py
Re-classifie les prospects sur des regles plus strictes (le scoring initial
etait trop favorable au "recent" car html5_semantic + modern_css + viewport_responsive
sont devenus universels en 2026).

Nouvelles regles :
  RECENT  = au moins 1 signal FORT (framework moderne, copyright >= annee-1,
            Tailwind/Webflow/Framer/Shopify, PWA manifest)
  VEILLOT = signal veillot fort (table_layout, frameset, jquery_v1, no_https)
            OU copyright old (< annee-4)
            OU absence de signal recent fort (defaut)
"""
import csv, re, sys
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(r"C:\Users\MAÏCK\Desktop\MadMakers Prospection\linkedin-scraper\data")
TODAY = datetime.now().strftime("%Y%m%d")
INPUT  = DATA_DIR / f"prospects_triage_{TODAY}.csv"
OUTPUT = DATA_DIR / f"prospects_triage_strict_{TODAY}.csv"

# Signaux RECENT forts (au moins 1 = recent)
SIGNAUX_RECENT_FORTS = {
    "nextjs", "nuxtjs", "react", "gatsby", "astro",
    "tailwind", "pwa_manifest",
    "webflow", "framer", "shopify",
}

# Signaux VEILLOT forts (au moins 1 = veillot)
SIGNAUX_VEILLOT_FORTS = {
    "table_layout", "font_tag", "center_tag", "frameset",
    "jquery_v1", "wp_old", "iso_charset", "no_https",
}


def has_recent_fort(signals: list) -> bool:
    return any(s in SIGNAUX_RECENT_FORTS for s in signals)


def has_veillot_fort(signals: list) -> bool:
    return any(s in SIGNAUX_VEILLOT_FORTS for s in signals)


def has_copyright_recent(signals: list, current_year: int) -> bool:
    """Cherche un signal 'copyright_recent_YYYY' avec YYYY >= current_year - 1."""
    for s in signals:
        m = re.match(r"copyright_recent_(\d{4})", s)
        if m and int(m.group(1)) >= current_year - 1:
            return True
    return False


def has_copyright_old(signals: list, current_year: int) -> bool:
    """Cherche un signal 'copyright_old_YYYY' (deja verifie < current_year - 4 par triage_sites)."""
    return any(s.startswith("copyright_old_") for s in signals)


def reclassify(veillot_signals: list, recent_signals: list, current_year: int) -> str:
    """Returns 'avec_site_veillot' or 'avec_site_recent'."""
    # 1. Veillot fort (table layout / frameset / no HTTPS / jquery v1...) -> veillot
    if has_veillot_fort(veillot_signals):
        return "avec_site_veillot"
    # 2. Copyright old detecte -> veillot
    if has_copyright_old(veillot_signals, current_year):
        return "avec_site_veillot"
    # 3. Signal recent fort (framework moderne, copyright recent, Tailwind, etc) -> recent
    if has_recent_fort(recent_signals):
        return "avec_site_recent"
    if has_copyright_recent(recent_signals, current_year):
        return "avec_site_recent"
    # 4. Defaut : pas de signaux discriminants -> veillot (Mad Makers cible cette zone grise)
    return "avec_site_veillot"


def main():
    if not INPUT.exists():
        print(f"ERREUR: {INPUT} introuvable")
        sys.exit(1)

    current_year = datetime.now().year
    rows = []
    with open(INPUT, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    counts = {"sans_site": 0, "avec_site_veillot": 0, "avec_site_recent": 0}
    output = []

    for r in rows:
        cat = r.get("categorie", "")
        if cat == "sans_site":
            new_cat = "sans_site"
        else:
            v_signals = [s.strip() for s in (r.get("veillot_signals", "") or "").split(";") if s.strip()]
            r_signals = [s.strip() for s in (r.get("recent_signals", "") or "").split(";") if s.strip()]
            new_cat = reclassify(v_signals, r_signals, current_year)

        counts[new_cat] = counts.get(new_cat, 0) + 1
        new_row = dict(r)
        new_row["categorie"] = new_cat
        output.append(new_row)

    # Sort par priorite Mad Makers : veillot > sans_site > recent
    sort_order = {"avec_site_veillot": 0, "sans_site": 1, "avec_site_recent": 2}
    output.sort(key=lambda x: (sort_order.get(x["categorie"], 9), x.get("nom_complet", "")))

    with open(OUTPUT, "w", encoding="utf-8-sig", newline="") as f:
        if output:
            w = csv.DictWriter(f, fieldnames=list(output[0].keys()))
            w.writeheader()
            w.writerows(output)

    print(f"=== Reclassification stricte ===")
    print(f"Sans site            : {counts.get('sans_site', 0)}")
    print(f"Avec site veillot    : {counts.get('avec_site_veillot', 0)}  <-- cible refonte Mad Makers")
    print(f"Avec site recent     : {counts.get('avec_site_recent', 0)}")
    print(f"\nCSV strict : {OUTPUT}")


if __name__ == "__main__":
    main()
