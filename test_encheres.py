import asyncio
import json
import os
from playwright.async_api import async_playwright

os.makedirs("cache", exist_ok=True)

SITES = [
    {
        "nom": "licitor.fr",
        "url": "https://www.licitor.com/?dept=51",
    },
    {
        "nom": "immobilier.notaires.fr",
        "url": "https://www.immobilier.notaires.fr/fr/encheres-immobilieres?departement=51",
    },
    {
        "nom": "encheres-publiques.com",
        "url": "https://www.encheres-publiques.com/immobilier/departement/51-marne",
    },
]

async def tester_site(page, site):
    print(f"\n--- Test : {site['nom']} ---")
    try:
        await page.goto(site["url"], wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(2000)

        title = await page.title()
        contenu = await page.inner_text("body")
        html = await page.content()

        print(f"✅ Status OK")
        print(f"Titre : {title}")
        print(f"Contenu ({len(contenu)} chars) :\n{contenu[:400]}")

        fichier = f"cache/{site['nom'].replace('.','_')}.html"
        with open(fichier, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"💾 Sauvegardé : {fichier}")

        # Cherche des annonces
        for selector in ["article", ".bien", ".vente", ".property", ".card", ".annonce", "li", "tr"]:
            elements = await page.query_selector_all(selector)
            if 1 <= len(elements) <= 100:
                print(f"  Sélecteur '{selector}' → {len(elements)} éléments")

    except Exception as e:
        print(f"❌ Erreur : {str(e)[:100]}")

async def main():
    print("Test des sites d'enchères immobilières...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="fr-FR",
        )
        page = await context.new_page()

        for site in SITES:
            await tester_site(page, site)

        await browser.close()

asyncio.run(main())
