"""
triage_apply_manual.py
Applique les URLs decouvertes via WebSearch sur les 'sans_site' restants.
Re-fetch + re-score chaque URL et met a jour la classification.

Usage : python -X utf8 scripts/triage_apply_manual.py
"""
import csv, re, sys, time
from pathlib import Path
from datetime import datetime
import requests

# Reuse logic from triage_recheck
sys.path.insert(0, str(Path(__file__).parent))
from triage_recheck import (
    fetch_html, score_site, classify_strict, has_https,
    UA, COPYRIGHT_RE, VEILLOT_PATTERNS, RECENT_PATTERNS,
)

DATA_DIR = Path(r"C:\Users\MAÏCK\Desktop\MadMakers Prospection\linkedin-scraper\data")
TODAY = datetime.now().strftime("%Y%m%d")
INPUT  = DATA_DIR / f"prospects_triage_strict_{TODAY}_recheck.csv"
OUTPUT = DATA_DIR / f"prospects_triage_final_{TODAY}.csv"

# URLs trouvees via WebSearch (octobre 2026)
MANUAL_URLS = {
    "Audrey ARNAUD":               "https://solucir.org/",
    "Augustin Joveneaux":          "https://www.trpj.com/",
    "Bertrand Porquet":            "https://concretesteelpartners.com/",
    "Bonnet Laurent":              "https://www.bge-provencealpesmediterranee.fr/",
    "Daniel Schemla":              "https://www.gruissan-mediterranee.com/",
    "Florent Vernet":              "https://fidflix.io/",
    "Florian Malivoir - Café Crème Club": "https://www.cafe-creme.club/",
    "Frederic Demarez":            "https://agroasis.fr/",
    "Madani IHMAD":                "https://www.renko.fr/",
    "Malik Sersar":                "https://green-office.com/",
    "Nicolas Ducoux":              "https://www.cfnews.net/",
    "Nicolas Fontaine":            "https://www.mipisepaymentservices.com/",
    "Philippe GASSER":             "https://www.lusini.com/",
}


def main():
    if not INPUT.exists():
        print(f"ERREUR: {INPUT} introuvable")
        sys.exit(1)

    with open(INPUT, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    # Index by nom_complet
    name_to_url = {k.lower().strip(): v for k, v in MANUAL_URLS.items()}

    updated_count = 0
    for row in rows:
        nom = row.get("nom_complet", "").lower().strip()
        if nom not in name_to_url:
            continue
        url = name_to_url[nom]
        print(f"[{updated_count+1}] {row['nom_complet'][:30]:30s} -> {url}")

        status, final_url, html, err = fetch_html(url, timeout=8)
        if not (status and 200 <= status < 400 and html):
            print(f"     fetch failed: {err}")
            continue

        score = score_site(final_url, html)
        if score:
            new_cat = classify_strict(score)
            row["categorie"] = new_cat
            row["site_url"] = final_url
            row["fetch_error"] = ""
            row["veillot_signals"] = "; ".join(score["veillot_hits"])
            row["recent_signals"] = "; ".join(score["recent_hits"])
            row["copyright_year"] = score["copyright_year"] or ""
            print(f"     -> {new_cat}")
            updated_count += 1
        time.sleep(0.3)

    # Re-sort
    sort_order = {"avec_site_veillot": 0, "sans_site": 1, "avec_site_recent": 2}
    rows.sort(key=lambda x: (sort_order.get(x.get("categorie", ""), 9),
                              x.get("nom_complet", "")))

    with open(OUTPUT, "w", encoding="utf-8-sig", newline="") as f:
        if rows:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    counts = {}
    for r in rows:
        counts[r["categorie"]] = counts.get(r["categorie"], 0) + 1

    print(f"\n=== Mises a jour ===")
    print(f"Sites manuels appliques  : {updated_count}/{len(MANUAL_URLS)}")
    print(f"\n=== Distribution finale ===")
    print(f"Sans site            : {counts.get('sans_site', 0)}")
    print(f"Avec site veillot    : {counts.get('avec_site_veillot', 0)}  <-- cible refonte Mad Makers")
    print(f"Avec site recent     : {counts.get('avec_site_recent', 0)}")
    print(f"\nCSV final : {OUTPUT}")


if __name__ == "__main__":
    main()
