"""
scrape.py — Extraction Sales Navigator via Playwright + profil Chrome existant
Lance : python -X utf8 scripts/scrape.py
"""
import asyncio, json, shutil, tempfile, sys
from datetime import datetime
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Lance : pip install playwright && python -m playwright install chromium")
    sys.exit(1)

CHROME_EXE   = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PROFILE_SRC  = r"C:\Users\MAÏCK\AppData\Local\Google\Chrome\User Data\Profile 3"
OUTPUT_DIR   = Path(r"C:\Users\MAÏCK\Desktop\MadMakers Prospection\linkedin-scraper\data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

async def extract_prospects(page) -> list[dict]:
    await page.wait_for_timeout(2500)
    return await page.evaluate("""() => {
        const out = [];
        // Approche universelle : trouve tous les liens /sales/lead/
        const links = Array.from(document.querySelectorAll('a[href*="/sales/lead/"], a[href*="/sales/people/"]'));
        links.forEach(link => {
            const name = link.innerText.trim();
            if (!name || name.length < 2) return;
            const url = link.href.split('?')[0];

            // Remonte jusqu'au container (li ou div suffisamment grand)
            let container = link;
            for (let i = 0; i < 10; i++) {
                container = container.parentElement;
                if (!container) break;
                const tag = container.tagName.toLowerCase();
                if (tag === 'li' || container.offsetHeight > 80) break;
            }
            if (!container) return;

            // Extrait tous les textes du container
            const allTexts = Array.from(container.querySelectorAll('span, a'))
                .map(el => el.innerText.trim())
                .filter(t => t.length > 1 && t.length < 200 && t !== name
                          && !t.match(/^(Enregistré|Retirer|liste|relation|post|Voir plus|\\.\\.\\.)/i));

            // Les premiers textes distincts = titre, entreprise, localisation
            const seen = new Set([name]);
            const texts = [];
            for (const t of allTexts) {
                if (!seen.has(t)) { seen.add(t); texts.push(t); }
                if (texts.length >= 3) break;
            }

            out.push({
                name,
                title:    texts[0] ?? '',
                company:  texts[1] ?? '',
                location: texts[2] ?? '',
                linkedin_url: url,
            });
        });
        return out;
    }""")

async def click_next(page) -> bool:
    for sel in ['button[aria-label="Suivant"]', 'button[aria-label="Next"]',
                'button.artdeco-pagination__button--next']:
        btn = await page.query_selector(sel)
        if btn:
            disabled = await btn.get_attribute("disabled")
            if disabled is None:
                await btn.click()
                await page.wait_for_timeout(3000)
                return True
    return False

async def main():
    # Copier le profil dans un dossier temp pour éviter les conflits
    print("Copie du profil Chrome (quelques secondes)...")
    tmp_dir = tempfile.mkdtemp(prefix="li_scrape_")
    profile_copy = Path(tmp_dir) / "Profile 3"
    shutil.copytree(PROFILE_SRC, str(profile_copy),
                    ignore=shutil.ignore_patterns("*.ldb","*.log","LOCK","Lock",
                                                  "SingletonLock","SingletonCookie"))
    print(f"Profil copié dans {tmp_dir}")

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            user_data_dir=tmp_dir,
            channel="chrome",
            executable_path=CHROME_EXE,
            headless=False,
            args=["--profile-directory=Profile 3", "--no-first-run",
                  "--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        print("\nOuvre Sales Navigator dans la fenêtre Chrome qui vient de s'ouvrir.")
        print("Va sur ta liste ou ta recherche filtrée, puis reviens ici et appuie sur ENTRÉE.")
        input(">>> Appuie sur ENTRÉE quand Sales Navigator est ouvert et la liste visible...")

        all_prospects, page_num, seen = [], 1, set()

        while page_num <= 200:
            print(f"Page {page_num}...", end=" ", flush=True)
            prospects = await extract_prospects(page)

            new = [p for p in prospects if p["linkedin_url"] not in seen]
            for p in new: seen.add(p["linkedin_url"])
            all_prospects.extend(new)
            print(f"{len(new)} nouveaux — total : {len(all_prospects)}")

            if not new and page_num > 1:
                print("Plus de nouveaux résultats — arrêt.")
                break

            has_next = await click_next(page)
            if not has_next:
                print("Dernière page atteinte.")
                break
            page_num += 1

        await ctx.close()

    # Sauvegarde
    today = datetime.now().strftime("%Y%m%d")
    out_json = OUTPUT_DIR / f"leads_{today}.json"
    out_csv  = OUTPUT_DIR / f"leads_{today}.csv"

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(all_prospects, f, ensure_ascii=False, indent=2)

    with open(out_csv, "w", encoding="utf-8-sig") as f:
        f.write("Nom,Titre,Entreprise,Localisation,LinkedIn URL\n")
        for p in all_prospects:
            row = [p.get(k,"").replace('"',"'") for k in ("name","title","company","location","linkedin_url")]
            f.write(",".join(f'"{v}"' for v in row) + "\n")

    shutil.rmtree(tmp_dir, ignore_errors=True)

    print(f"\n{'='*50}")
    print(f"✅ {len(all_prospects)} prospects — {page_num} pages")
    print(f"📁 {out_csv}")
    print(f"{'='*50}")

if __name__ == "__main__":
    asyncio.run(main())
