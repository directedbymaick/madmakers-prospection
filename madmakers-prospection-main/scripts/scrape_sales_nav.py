"""
scrape_sales_nav.py — Extraction automatique LinkedIn Sales Navigator
======================================================================
Prérequis :
  pip install playwright
  playwright install chromium

Usage :
  1. Ferme Chrome complètement
  2. Relance Chrome avec :
     "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --profile-directory="Default"
  3. Dans Chrome, ouvre ta liste Sales Navigator (ou ta recherche filtrée)
  4. Lance ce script :
     python -X utf8 scripts/scrape_sales_nav.py
"""

import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Playwright non installé. Lance : pip install playwright && playwright install chromium")
    sys.exit(1)

CDP_URL = "http://127.0.0.1:9222"
OUTPUT_DIR = Path("C:/Users/MAÏCK/Desktop/MadMakers Prospection/madmakers-prospection-main/data")
OUTPUT_DIR.mkdir(exist_ok=True)


def clean(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


async def extract_page(page) -> list[dict]:
    """Extrait tous les prospects visibles sur la page courante."""
    await page.wait_for_timeout(2000)

    prospects = await page.evaluate("""
    () => {
        const results = [];

        // Sélecteurs Sales Navigator (liste ou recherche)
        const rows = document.querySelectorAll(
            '[data-view-name="search-results-lead-result"], ' +
            '[data-x--lead-list-item-name], ' +
            'li.artdeco-list__item'
        );

        rows.forEach(row => {
            // Nom + URL profil
            const nameLink = row.querySelector(
                'a[href*="/sales/lead/"], a[href*="/sales/people/"], ' +
                'a[data-anonymize="person-name"], a[href*="/in/"]'
            );
            const name = nameLink ? nameLink.innerText.trim() : '';
            let profileUrl = nameLink ? nameLink.href : '';
            // Nettoyer l'URL (garder jusqu'au premier ?,)
            if (profileUrl) profileUrl = profileUrl.split('?')[0];

            // Titre
            const titleEl = row.querySelector(
                '[data-anonymize="job-title"], ' +
                '.artdeco-entity-lockup__subtitle span, ' +
                '[data-view-name="search-results-lead-job-title"]'
            );

            // Entreprise
            const companyEl = row.querySelector(
                '[data-anonymize="company-name"], ' +
                '.artdeco-entity-lockup__caption a, ' +
                '[data-view-name="search-results-lead-company-name"]'
            );

            // Localisation
            const locationEl = row.querySelector(
                '[data-anonymize="location"], ' +
                '.artdeco-entity-lockup__metadata span'
            );

            if (name) {
                results.push({
                    nom: name,
                    titre: titleEl ? titleEl.innerText.trim() : '',
                    entreprise: companyEl ? companyEl.innerText.trim() : '',
                    localisation: locationEl ? locationEl.innerText.trim() : '',
                    linkedin_url: profileUrl,
                });
            }
        });

        return results;
    }
    """)
    return prospects


async def go_next_page(page) -> bool:
    """Clique sur Suivant. Retourne False si dernière page."""
    # Chercher le bouton Suivant (plusieurs libellés possibles)
    next_selectors = [
        'button[aria-label="Suivant"]',
        'button[aria-label="Next"]',
        'button.pagination__btn--next',
        'a[aria-label="Suivant"]',
    ]
    for sel in next_selectors:
        btn = await page.query_selector(sel)
        if btn:
            disabled = await btn.get_attribute("disabled")
            aria_disabled = await btn.get_attribute("aria-disabled")
            if disabled is None and aria_disabled != "true":
                await btn.click()
                await page.wait_for_timeout(2500)
                return True
    return False


async def get_current_page_number(page) -> int:
    try:
        num = await page.evaluate("""
        () => {
            const active = document.querySelector(
                '.pagination__btn--active, button[aria-current="page"], ' +
                'li.active > a, [aria-label*="Page "]'
            );
            return active ? parseInt(active.innerText || active.getAttribute('aria-label')) : 0;
        }
        """)
        return int(num) if num else 0
    except Exception:
        return 0


async def main():
    print("Connexion à Chrome (port 9222)...")

    async with async_playwright() as pw:
        try:
            browser = await pw.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            print(f"\n❌ Impossible de se connecter : {e}")
            print("\n→ As-tu bien relancé Chrome avec --remote-debugging-port=9222 ?")
            print("  Commande : \"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe\" --remote-debugging-port=9222")
            return

        # Trouver l'onglet Sales Navigator
        context = browser.contexts[0]
        target_page = None
        for p in context.pages:
            url = p.url
            if "linkedin.com/sales" in url or "linkedin.com/in/" in url:
                target_page = p
                print(f"✅ Onglet Sales Navigator trouvé : {url[:80]}")
                break

        if not target_page:
            print("❌ Aucun onglet Sales Navigator trouvé dans Chrome.")
            print("   → Ouvre ta liste/recherche Sales Navigator dans Chrome, puis relance.")
            return

        page = target_page
        all_prospects = []
        page_num = 1
        max_pages = 200  # sécurité

        print(f"\n🚀 Démarrage extraction — pagination automatique\n{'─'*50}")

        while page_num <= max_pages:
            print(f"📄 Page {page_num}...", end=" ", flush=True)

            try:
                prospects = await extract_page(page)
            except Exception as e:
                print(f"⚠️  Erreur extraction page {page_num} : {e}")
                break

            if not prospects:
                print("Aucun résultat — arrêt.")
                break

            # Dédupliquer par URL
            before = len(all_prospects)
            existing_urls = {p["linkedin_url"] for p in all_prospects}
            new = [p for p in prospects if p["linkedin_url"] not in existing_urls]
            all_prospects.extend(new)
            print(f"{len(new)} nouveaux (total : {len(all_prospects)})")

            # Passer à la page suivante
            has_next = await go_next_page(page)
            if not has_next:
                print("✅ Dernière page atteinte.")
                break

            page_num += 1

        # Sauvegarder
        today = datetime.now().strftime("%Y%m%d")
        out_json = OUTPUT_DIR / f"linkedin_salesnav_{today}.json"
        out_csv = OUTPUT_DIR / f"linkedin_salesnav_{today}.csv"

        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(all_prospects, f, ensure_ascii=False, indent=2)

        # CSV simple
        with open(out_csv, "w", encoding="utf-8-sig") as f:
            f.write("Nom,Titre,Entreprise,Localisation,LinkedIn URL\n")
            for p in all_prospects:
                row = [
                    p.get("nom", "").replace('"', "'"),
                    p.get("titre", "").replace('"', "'"),
                    p.get("entreprise", "").replace('"', "'"),
                    p.get("localisation", "").replace('"', "'"),
                    p.get("linkedin_url", ""),
                ]
                f.write(",".join(f'"{v}"' for v in row) + "\n")

        print(f"\n{'='*50}")
        print(f"✅ {len(all_prospects)} prospects extraits sur {page_num} pages")
        print(f"📁 JSON : {out_json}")
        print(f"📁 CSV  : {out_csv}")
        print(f"{'='*50}")


if __name__ == "__main__":
    asyncio.run(main())
